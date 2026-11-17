import json

from rps.ai import Opponent, RandomOpponent
from rps.game import Match
from rps.rules import CLASSIC
from rps.stats import StatsStore, summarize


class Always(Opponent):
    def __init__(self, move):
        super().__init__(CLASSIC)
        self.move = move

    def predict(self):
        return None

    def choose(self):
        return self.move

    def observe(self, player_move):
        pass


def finished_match(won: bool) -> Match:
    match = Match(CLASSIC, Always("scissors" if won else "paper"), target=1)
    match.play("rock")
    return match


def test_record_and_reload(tmp_path):
    path = tmp_path / "stats.json"
    store = StatsStore(path)
    store.record(finished_match(won=True))
    reloaded = StatsStore(path)
    assert len(reloaded.matches) == 1
    assert reloaded.matches[0]["result"] == "win"


def test_corrupt_file_is_backed_up_not_lost(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text("{ not json")
    store = StatsStore(path)
    assert store.matches == []
    assert (tmp_path / "stats.corrupt.json").read_text() == "{ not json"


def test_unfinished_match_is_not_recorded(tmp_path):
    store = StatsStore(tmp_path / "stats.json")
    match = Match(CLASSIC, RandomOpponent(CLASSIC), target=5)
    try:
        store.record(match)
    except ValueError:
        pass
    assert store.matches == []


def test_summary_streaks_and_rates():
    def rec(result, difficulty="Hard", rounds=()):
        return {"result": result, "difficulty": difficulty, "rounds": list(rounds)}

    rounds = [
        {"player": "rock", "cpu": "paper", "outcome": "lose", "predicted": "rock"},
        {"player": "rock", "cpu": "scissors", "outcome": "win", "predicted": "paper"},
        {"player": "paper", "cpu": "paper", "outcome": "draw", "predicted": None},
    ]
    s = summarize([rec("win", rounds=rounds), rec("win"), rec("win"), rec("lose", "Easy"), rec("win")])
    assert (s.matches, s.wins) == (5, 4)
    assert s.best_streak == 3
    assert s.current_streak == 1
    assert s.favorite_move == "rock"
    assert s.read_rate == 0.5
    assert s.by_difficulty == {"Hard": (4, 4), "Easy": (0, 1)}


def test_saved_file_is_readable_json(tmp_path):
    path = tmp_path / "stats.json"
    StatsStore(path).record(finished_match(won=False))
    data = json.loads(path.read_text())
    assert data["version"] == 1
