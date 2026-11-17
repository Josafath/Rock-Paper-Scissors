"""A match: first to N points against one opponent. No UI code here."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .ai import Opponent
from .rules import Outcome, Ruleset


@dataclass(frozen=True)
class Round:
    number: int
    player: str
    cpu: str
    outcome: Outcome
    predicted: Optional[str] = None  # what the CPU thought you'd play
    confidence: Optional[float] = None

    @property
    def was_read(self) -> bool:
        """True when the CPU correctly predicted the player's move."""
        return self.predicted == self.player


@dataclass
class Match:
    rules: Ruleset
    opponent: Opponent
    target: int = 5
    rounds: list[Round] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.target < 1:
            raise ValueError("target must be at least 1")

    @property
    def player_score(self) -> int:
        return sum(r.outcome is Outcome.WIN for r in self.rounds)

    @property
    def cpu_score(self) -> int:
        return sum(r.outcome is Outcome.LOSE for r in self.rounds)

    @property
    def is_over(self) -> bool:
        return max(self.player_score, self.cpu_score) >= self.target

    @property
    def result(self) -> Optional[Outcome]:
        if not self.is_over:
            return None
        return Outcome.WIN if self.player_score > self.cpu_score else Outcome.LOSE

    @property
    def read_rate(self) -> Optional[float]:
        """Share of rounds in which the CPU guessed your move."""
        guessed = [r for r in self.rounds if r.predicted is not None]
        if not guessed:
            return None
        return sum(r.was_read for r in guessed) / len(guessed)

    def play(self, player_move: str) -> Round:
        if self.is_over:
            raise RuntimeError("The match is already over")
        if player_move not in self.rules.moves:
            raise ValueError(f"'{player_move}' is not a valid move in {self.rules.name}")
        cpu_move = self.opponent.choose()  # decided before seeing player_move
        guess = self.opponent.guess
        self.opponent.observe(player_move)
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
