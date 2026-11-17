"""CPU opponents.

Every opponent predicts the probability of each move the player might make
next, then plays the move with the best expected score against that guess.
They only differ in *how* they predict:

* RandomOpponent   - doesn't predict at all (pure chance, unbeatable long-term).
* AdaptiveOpponent - counts which moves you use most, favouring recent ones.
* MarkovOpponent   - learns sequences ("after rock, rock you usually play
                     paper") with several Markov chains of different lengths
                     and trusts whichever has been guessing best lately.

Fairness: `choose()` is always called *before* the player's move is known,
and the move is only revealed afterwards through `observe()`.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional

from .rules import Ruleset

Distribution = dict[str, float]


def best_response(rules: Ruleset, dist: Distribution, rng: random.Random) -> str:
    """Move with the highest expected score against a predicted distribution."""
    def expected(move: str) -> float:
        return sum(p * rules.score(move, theirs) for theirs, p in dist.items())

    values = {m: expected(m) for m in rules.moves}
    top = max(values.values())
    return rng.choice([m for m, v in values.items() if abs(v - top) < 1e-9])


class Opponent(ABC):
    name: str = "Opponent"
    description: str = ""

    def __init__(self, rules: Ruleset, rng: Optional[random.Random] = None) -> None:
        self.rules = rules
        self.rng = rng or random.Random()
        self.last_prediction: Optional[Distribution] = None

    def choose(self) -> str:
        self.last_prediction = self.predict()
        if not self.last_prediction:
            return self.rng.choice(self.rules.moves)
        return best_response(self.rules, self.last_prediction, self.rng)

    @property
    def guess(self) -> Optional[tuple[str, float]]:
        """The single move the CPU expects you to play, with its confidence."""
        if not self.last_prediction:
            return None
        move = max(self.last_prediction, key=self.last_prediction.__getitem__)
        return move, self.last_prediction[move]

    @abstractmethod
    def predict(self) -> Optional[Distribution]:
        """Probability of each player move for the next round, or None."""

    @abstractmethod
    def observe(self, player_move: str) -> None:
        """Learn from the move the player just made."""


class RandomOpponent(Opponent):
    name = "Easy"
    description = "Plays at random. Pure luck."

    def predict(self) -> Optional[Distribution]:
        return None

    def observe(self, player_move: str) -> None:
        pass


class MarkovOpponent(Opponent):
    name = "Hard"
    description = "Learns your sequences and patterns."

    def __init__(
        self,
        rules: Ruleset,
        rng: Optional[random.Random] = None,
        max_order: int = 3,
        decay: float = 0.9,
    ) -> None:
        super().__init__(rules, rng)
        self.max_order = max_order
        self.decay = decay  # < 1 lets old habits fade so it adapts to changes
        self.history: list[str] = []
        # tables[k][last k moves][next move] -> weighted count
        self.tables: list[defaultdict[tuple[str, ...], dict[str, float]]] = [
            defaultdict(dict) for _ in range(max_order + 1)
        ]
        # How well each chain length has been predicting recently
        self.scores = [0.0] * (max_order + 1)
        self._pending: list[Optional[Distribution]] = [None] * (max_order + 1)

    def _predict_order(self, k: int) -> Optional[Distribution]:
        if len(self.history) < k:
            return None
        context = tuple(self.history[-k:]) if k else ()
        counts = self.tables[k].get(context)
        if not counts:
            return None
        total = sum(counts.values())
        return {m: c / total for m, c in counts.items()}

    def predict(self) -> Optional[Distribution]:
        self._pending = [self._predict_order(k) for k in range(self.max_order + 1)]
        candidates = [k for k, d in enumerate(self._pending) if d]
        if not candidates:
            return None
        # Prefer the best scorer; on ties prefer the longer (more specific) chain
        best = max(candidates, key=lambda k: (self.scores[k], k))
        return self._pending[best]

    def observe(self, player_move: str) -> None:
        baseline = 1 / len(self.rules.moves)
        for k, dist in enumerate(self._pending):
            if dist:
                # Reward chains that gave the real move more probability than chance
                hit = dist.get(player_move, 0.0) - baseline
                self.scores[k] = self.decay * self.scores[k] + hit
        for k in range(self.max_order + 1):
            if len(self.history) < k:
                continue
            context = tuple(self.history[-k:]) if k else ()
            counts = self.tables[k][context]
            for m in counts:
                counts[m] *= self.decay
            counts[player_move] = counts.get(player_move, 0.0) + 1
        self.history.append(player_move)
        self._pending = [None] * (self.max_order + 1)


class AdaptiveOpponent(MarkovOpponent):
    """A Markov chain of order 0: only looks at how often you use each move."""

    name = "Medium"
    description = "Spots the moves you use the most."

    def __init__(self, rules: Ruleset, rng: Optional[random.Random] = None) -> None:
        super().__init__(rules, rng, max_order=0, decay=0.85)


OPPONENTS: dict[str, type[Opponent]] = {
    cls.name: cls for cls in (RandomOpponent, AdaptiveOpponent, MarkovOpponent)
}
