"""Game rules expressed as data instead of if/else chains.

A ruleset is just a list of moves and a table of "who beats whom (and how)".
Adding a new variant means adding a new table, not new code.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Outcome(Enum):
    """Result of a round, always from the player's point of view."""

    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"

    @property
    def points(self) -> int:
        """Numeric value of the outcome, used by the AI to compare moves.

        A win is worth +1, a loss -1 and a draw 0, so adding up points over
        many rounds tells you who is ahead.
        """
        return {Outcome.WIN: 1, Outcome.LOSE: -1, Outcome.DRAW: 0}[self]


# frozen=True makes rulesets read-only: once created, nobody can change the
# rules in the middle of a game by accident.
@dataclass(frozen=True)
class Ruleset:
    """A variant of the game: its moves and who beats whom.

    Think of it as a graph: each move is a node and an arrow "a -> b" means
    "a beats b". The verb on the arrow ("crushes", "covers"...) is only used
    to describe the round to the player.
    """

    name: str
    moves: tuple[str, ...]
    # winner -> {loser: verb}, e.g. {"rock": {"scissors": "crushes"}}
    beats: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        # dataclasses call this right after __init__: reject broken rules
        # as soon as they are created instead of failing in the middle of a game.
        self._validate()

    def _validate(self) -> None:
        """Make sure the ruleset is fair; raise ValueError if it isn't.

        Fair means no move is better than another: every move wins against
        exactly half of the other moves and loses against the other half.
        """
        # With an even number of moves you can't split "the others" in two
        # equal halves, so some move would always have an advantage.
        if len(self.moves) % 2 == 0:
            raise ValueError("A fair ruleset needs an odd number of moves")

        # Every move named in the table (as winner or loser) must exist.
        unknown = set(self.beats) - set(self.moves)
        unknown |= {loser for losers in self.beats.values() for loser in losers} - set(self.moves)
        if unknown:
            raise ValueError(f"Unknown moves in rules: {sorted(unknown)}")

        # Each move must beat exactly half of the others (1 of 2 in Classic,
        # 2 of 4 in Lizard-Spock).
        half = len(self.moves) // 2
        for move in self.moves:
            wins = len(self.beats.get(move, {}))
            if wins != half:
                raise ValueError(f"'{move}' beats {wins} moves, expected {half}")

        # For every pair of different moves exactly one must win: not both
        # (contradiction) and not neither (a missing rule).
        for a in self.moves:
            for b in self.moves:
                if a != b and self.wins(a, b) == self.wins(b, a):
                    raise ValueError(f"Exactly one of '{a}' / '{b}' must win")

    def wins(self, a: str, b: str) -> bool:
        """True if move `a` beats move `b`."""
        return b in self.beats.get(a, {})

    def outcome(self, player: str, opponent: str) -> Outcome:
        """Who wins a round, seen from the player's side."""
        self._check(player)
        self._check(opponent)
        if player == opponent:
            return Outcome.DRAW
        return Outcome.WIN if self.wins(player, opponent) else Outcome.LOSE

    def describe(self, a: str, b: str) -> str:
        """Human sentence for a round, e.g. 'Paper covers rock'."""
        if a == b:
            return f"Both chose {a}"
        # The sentence always starts with the winner, whatever the order of a and b.
        winner, loser = (a, b) if self.wins(a, b) else (b, a)
        return f"{winner.capitalize()} {self.beats[winner][loser]} {loser}"

    def score(self, move: str, against: str) -> int:
        """Points (+1 / 0 / -1) that `move` earns against `against`."""
        return self.outcome(move, against).points

    def _check(self, move: str) -> None:
        """Reject moves that don't belong to this ruleset (e.g. 'spock' in Classic)."""
        if move not in self.moves:
            raise ValueError(f"'{move}' is not a valid move in {self.name}")


# The traditional game: 3 moves, each one beats 1 and loses to 1.
CLASSIC = Ruleset(
    name="Classic",
    moves=("rock", "paper", "scissors"),
    beats={
        "rock": {"scissors": "crushes"},
        "paper": {"rock": "covers"},
        "scissors": {"paper": "cuts"},
    },
)

# The Big Bang Theory variant: 5 moves, each one beats 2 and loses to 2.
LIZARD_SPOCK = Ruleset(
    name="Lizard-Spock",
    moves=("rock", "paper", "scissors", "lizard", "spock"),
    beats={
        "rock": {"scissors": "crushes", "lizard": "crushes"},
        "paper": {"rock": "covers", "spock": "disproves"},
        "scissors": {"paper": "cuts", "lizard": "decapitates"},
        "lizard": {"spock": "poisons", "paper": "eats"},
        "spock": {"scissors": "smashes", "rock": "vaporizes"},
    },
)

# Lookup by name, used by the "Mode" menu in the GUI.
RULESETS: dict[str, Ruleset] = {r.name: r for r in (CLASSIC, LIZARD_SPOCK)}
