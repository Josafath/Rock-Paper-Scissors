import random
from itertools import cycle

import pytest

from rps.ai import AdaptiveOpponent, MarkovOpponent, RandomOpponent, best_response
from rps.rules import CLASSIC, LIZARD_SPOCK, Outcome


def play(opponent, moves):
    """Feed a sequence of player moves; return the outcomes from the player's side."""
    results = []
    for move in moves:
        cpu = opponent.choose()
        opponent.observe(move)
        results.append(opponent.rules.outcome(move, cpu))
    return results


def cpu_win_rate(results):
    return results.count(Outcome.LOSE) / len(results)


def test_best_response_counters_a_sure_guess():
    rng = random.Random(0)
    assert best_response(CLASSIC, {"rock": 1.0}, rng) == "paper"
    assert best_response(LIZARD_SPOCK, {"spock": 1.0}, rng) in {"paper", "lizard"}


def test_random_opponent_never_predicts():
    cpu = RandomOpponent(CLASSIC, random.Random(1))
    play(cpu, ["rock"] * 20)
    assert cpu.guess is None


def test_adaptive_punishes_a_favorite_move():
    cpu = AdaptiveOpponent(CLASSIC, random.Random(2))
    results = play(cpu, ["rock"] * 50)
    assert cpu_win_rate(results[5:]) > 0.9


def test_markov_learns_a_cycle_that_fools_frequency_counting():
    # Each move is used equally often, so counting alone can't exploit it...
    moves = [m for _, m in zip(range(90), cycle(["rock", "paper", "scissors"]))]
    adaptive = play(AdaptiveOpponent(CLASSIC, random.Random(3)), moves)
    markov = play(MarkovOpponent(CLASSIC, random.Random(3)), moves)
    assert cpu_win_rate(adaptive[30:]) < 0.6
    # ...but the sequence is completely predictable for the Markov chains
    assert cpu_win_rate(markov[30:]) > 0.9


def test_markov_adapts_when_the_player_changes_strategy():
    moves = ["rock"] * 30 + ["spock", "lizard"] * 30
    results = play(MarkovOpponent(LIZARD_SPOCK, random.Random(4)), moves)
    assert cpu_win_rate(results[-30:]) > 0.8


@pytest.mark.parametrize("cls", [RandomOpponent, AdaptiveOpponent, MarkovOpponent])
def test_no_edge_against_a_random_player(cls):
    rng = random.Random(5)
    moves = [rng.choice(CLASSIC.moves) for _ in range(3000)]
    results = play(cls(CLASSIC, random.Random(6)), moves)
    assert 0.28 < cpu_win_rate(results) < 0.39


def test_guess_reports_most_likely_move():
    cpu = MarkovOpponent(CLASSIC, random.Random(7))
    play(cpu, ["paper"] * 10)
    cpu.choose()
    move, confidence = cpu.guess
    assert move == "paper"
    assert confidence > 0.9
