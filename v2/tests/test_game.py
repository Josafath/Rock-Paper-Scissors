import random

import pytest

from rps.ai import MarkovOpponent, Opponent
from rps.game import Match
from rps.rules import CLASSIC, Outcome


class Scripted(Opponent):
    """Plays a fixed list of moves and records what it was shown."""

    name = "Scripted"

    def __init__(self, moves):
        super().__init__(CLASSIC)
        self.moves = list(moves)
        self.seen = []

    def predict(self):
        return None

    def choose(self):
        self.seen.append(("choose", len(self.seen)))
        return self.moves.pop(0)

    def observe(self, player_move):
        self.seen.append(("observe", player_move))


def test_scores_and_winner():
    match = Match(CLASSIC, Scripted(["scissors", "rock", "rock", "scissors"]), target=2)
    assert match.play("rock").outcome is Outcome.WIN
    assert match.play("scissors").outcome is Outcome.LOSE
    assert match.play("rock").outcome is Outcome.DRAW
    assert not match.is_over
    match.play("rock")
    assert (match.player_score, match.cpu_score) == (2, 1)
    assert match.is_over and match.result is Outcome.WIN


def test_cpu_chooses_before_seeing_the_player_move():
    cpu = Scripted(["paper"])
    Match(CLASSIC, cpu).play("rock")
    assert [step for step, _ in cpu.seen] == ["choose", "observe"]


def test_cannot_play_after_the_match_ends():
    match = Match(CLASSIC, Scripted(["scissors"]), target=1)
    match.play("rock")
    with pytest.raises(RuntimeError):
        match.play("rock")


def test_rejects_moves_from_another_ruleset():
    with pytest.raises(ValueError):
        Match(CLASSIC, Scripted(["rock"])).play("spock")


def test_read_rate_tracks_correct_predictions():
    match = Match(CLASSIC, MarkovOpponent(CLASSIC, random.Random(0)), target=100)
    for _ in range(20):
        match.play("rock")
    assert match.rounds[0].predicted is None  # nothing to learn from yet
    assert match.read_rate > 0.9
