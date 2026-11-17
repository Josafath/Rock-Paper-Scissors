"""A match: first to N points against one opponent. No UI code here."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .ai import Opponent
from .rules import Outcome, Ruleset


@dataclass(frozen=True)
class Round:
    """Everything that happened in one round. Read-only once created."""

    number: int  # 1 for the first round of the match
    player: str
    cpu: str
    outcome: Outcome  # from the player's point of view
    predicted: Optional[str] = None  # what the CPU thought you'd play
    confidence: Optional[float] = None  # how sure it was, from 0.0 to 1.0

    @property
    def was_read(self) -> bool:
        """True when the CPU correctly predicted the player's move."""
        return self.predicted == self.player


@dataclass
class Match:
    """A match against one opponent: the first to reach `target` points wins.

    Scores are not stored separately; they are always computed from `rounds`,
    so they can never get out of sync with what actually happened.
    """

    rules: Ruleset
    opponent: Opponent
    target: int = 5
    # default_factory gives each match its own new list. A plain `= []` would
    # be shared between every Match instance.
    rounds: list[Round] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.target < 1:
            raise ValueError("target must be at least 1")

    @property
    def player_score(self) -> int:
        # True counts as 1 and False as 0, so sum() counts the rounds won.
        return sum(r.outcome is Outcome.WIN for r in self.rounds)

    @property
    def cpu_score(self) -> int:
        return sum(r.outcome is Outcome.LOSE for r in self.rounds)

    @property
    def is_over(self) -> bool:
        return max(self.player_score, self.cpu_score) >= self.target

    @property
    def result(self) -> Optional[Outcome]:
        """WIN or LOSE for the player once the match is over, otherwise None."""
        if not self.is_over:
            return None
        return Outcome.WIN if self.player_score > self.cpu_score else Outcome.LOSE

    @property
    def read_rate(self) -> Optional[float]:
        """Share of rounds in which the CPU guessed your move."""
        # Rounds where the CPU had no prediction (e.g. the first one) don't count.
        guessed = [r for r in self.rounds if r.predicted is not None]
        if not guessed:
            return None
        return sum(r.was_read for r in guessed) / len(guessed)

    def play(self, player_move: str) -> Round:
        """Play one round with the player's move and return what happened."""
        if self.is_over:
            raise RuntimeError("The match is already over")
        if player_move not in self.rules.moves:
            raise ValueError(f"'{player_move}' is not a valid move in {self.rules.name}")
        # The order of these three lines is what makes the game fair:
        cpu_move = self.opponent.choose()  # decided before seeing player_move
        guess = self.opponent.guess  # what it expected, saved for the GUI/stats
        self.opponent.observe(player_move)  # only now does the CPU learn the move
        rnd = Round(
            number=len(self.rounds) + 1,
            player=player_move,
            cpu=cpu_move,
            outcome=self.rules.outcome(player_move, cpu_move),
            predicted=guess[0] if guess else None,
            confidence=guess[1] if guess else None,
        )
        self.rounds.append(rnd)
        return rnd
