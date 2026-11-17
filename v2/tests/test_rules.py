import pytest

from rps.rules import CLASSIC, LIZARD_SPOCK, Outcome, Ruleset


@pytest.mark.parametrize(
    "player, cpu, expected",
    [
        ("rock", "scissors", Outcome.WIN),
        ("rock", "paper", Outcome.LOSE),
        ("paper", "paper", Outcome.DRAW),
        ("scissors", "paper", Outcome.WIN),
    ],
)
def test_classic_outcomes(player, cpu, expected):
    assert CLASSIC.outcome(player, cpu) is expected


@pytest.mark.parametrize("rules", [CLASSIC, LIZARD_SPOCK])
def test_every_move_wins_and_loses_equally(rules):
    for move in rules.moves:
        results = [rules.outcome(move, other) for other in rules.moves if other != move]
        assert results.count(Outcome.WIN) == results.count(Outcome.LOSE)


@pytest.mark.parametrize(
    "a, b, sentence",
    [
        ("spock", "rock", "Spock vaporizes rock"),
        ("rock", "spock", "Spock vaporizes rock"),
        ("lizard", "paper", "Lizard eats paper"),
        ("rock", "rock", "Both chose rock"),
    ],
)
def test_describe(a, b, sentence):
    assert LIZARD_SPOCK.describe(a, b) == sentence


def test_invalid_move_is_rejected():
    with pytest.raises(ValueError):
        CLASSIC.outcome("lizard", "rock")


def test_unbalanced_ruleset_is_rejected():
    with pytest.raises(ValueError):
        Ruleset(
            "Broken",
            ("rock", "paper", "scissors"),
            {"rock": {"scissors": "x", "paper": "y"}, "paper": {}, "scissors": {"paper": "z"}},
        )


def test_even_number_of_moves_is_rejected():
    with pytest.raises(ValueError):
        Ruleset("Even", ("a", "b"), {"a": {"b": "beats"}})
