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
        return {Outcome.WIN: 1, Outcome.LOSE: -1, Outcome.DRAW: 0}[self]


@dataclass(frozen=True)
class Ruleset:
    name: str
    moves: tuple[str, ...]
    # winner -> {loser: verb}, e.g. {"rock": {"scissors": "crushes"}}
    beats: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if len(self.moves) % 2 == 0:
            raise ValueError("A fair ruleset needs an odd number of moves")
        unknown = set(self.beats) - set(self.moves)
        unknown |= {loser for losers in self.beats.values() for loser in losers} - set(self.moves)
        if unknown:
            raise ValueError(f"Unknown moves in rules: {sorted(unknown)}")
        half = len(self.moves) // 2
        for move in self.moves:
            wins = len(self.beats.get(move, {}))
            if wins != half:
                raise ValueError(f"'{move}' beats {wins} moves, expected {half}")
        for a in self.moves:
            for b in self.moves:
                if a != b and self.wins(a, b) == self.wins(b, a):
                    raise ValueError(f"Exactly one of '{a}' / '{b}' must win")

    def wins(self, a: str, b: str) -> bool:
        return b in self.beats.get(a, {})

    def outcome(self, player: str, opponent: str) -> Outcome:
        self._check(player)
        self._check(opponent)
        if player == opponent:
            return Outcome.DRAW
        return Outcome.WIN if self.wins(player, opponent) else Outcome.LOSE

    def describe(self, a: str, b: str) -> str:
        """Human sentence for a round, e.g. 'Paper covers rock'."""
        if a == b:
            return f"Both chose {a}"
        winner, loser = (a, b) if self.wins(a, b) else (b, a)
        return f"{winner.capitalize()} {self.beats[winner][loser]} {loser}"

    def score(self, move: str, against: str) -> int:
        return self.outcome(move, against).points

    def _check(self, move: str) -> None:
        if move not in self.moves:
            raise ValueError(f"'{move}' is not a valid move in {self.name}")


CLASSIC = Ruleset(
    name="Classic",
    moves=("rock", "paper", "scissors"),
    beats={
        "rock": {"scissors": "crushes"},
        "paper": {"rock": "covers"},
        "scissors": {"paper": "cuts"},
    },
)

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

RULESETS: dict[str, Ruleset] = {r.name: r for r in (CLASSIC, LIZARD_SPOCK)}
