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

# A prediction: probability of each move, e.g. {"rock": 0.7, "paper": 0.3}.
# Moves that are missing have probability 0.
Distribution = dict[str, float]


def best_response(rules: Ruleset, dist: Distribution, rng: random.Random) -> str:
    """Move with the highest expected score against a predicted distribution.

    Example with {"rock": 0.6, "paper": 0.3, "scissors": 0.1}:
        paper    -> +0.6 (beats rock) - 0.1 (loses to scissors) = +0.5  <- best
        rock     -> +0.1 - 0.3 = -0.2
        scissors -> +0.3 - 0.6 = -0.3
    """
    def expected(move: str) -> float:
        # Average points `move` would earn, weighting each possible player
        # move by how likely we think it is.
        return sum(p * rules.score(move, theirs) for theirs, p in dist.items())

    values = {m: expected(m) for m in rules.moves}
    top = max(values.values())
    # Several moves can share the best value; picking one at random keeps the
    # CPU from being predictable. abs(...) < 1e-9 avoids float rounding issues.
    return rng.choice([m for m, v in values.items() if abs(v - top) < 1e-9])


class Opponent(ABC):
    """Base class for every CPU (Strategy pattern).

    Subclasses only implement two things:
      * predict(): what do I think the player will do next?
      * observe(): learn from what the player actually did.
    Turning a prediction into a move is shared code (`choose`).
    """

    name: str = "Opponent"
    description: str = ""

    def __init__(self, rules: Ruleset, rng: Optional[random.Random] = None) -> None:
        self.rules = rules
        # The random generator can be injected so tests get repeatable results
        # by passing random.Random(<fixed seed>).
        self.rng = rng or random.Random()
        # Prediction used for the last move; the GUI shows it in "CPU's mind".
        self.last_prediction: Optional[Distribution] = None

    def choose(self) -> str:
        """Pick the CPU's move for this round (before seeing the player's move)."""
        self.last_prediction = self.predict()
        if not self.last_prediction:
            # Nothing learned yet: play uniformly at random. That can't be
            # exploited, so it's the safest choice when we know nothing.
            return self.rng.choice(self.rules.moves)
        return best_response(self.rules, self.last_prediction, self.rng)

    @property
    def guess(self) -> Optional[tuple[str, float]]:
        """The single move the CPU expects you to play, with its confidence."""
        if not self.last_prediction:
            return None
        # The move with the highest probability in the last prediction.
        move = max(self.last_prediction, key=self.last_prediction.__getitem__)
        return move, self.last_prediction[move]

    @abstractmethod
    def predict(self) -> Optional[Distribution]:
        """Probability of each player move for the next round, or None."""

    @abstractmethod
    def observe(self, player_move: str) -> None:
        """Learn from the move the player just made."""


class RandomOpponent(Opponent):
    """Easy level: never predicts, so `choose()` always plays at random."""

    name = "Easy"
    description = "Plays at random. Pure luck."

    def predict(self) -> Optional[Distribution]:
        return None

    def observe(self, player_move: str) -> None:
        pass  # learns nothing on purpose


class MarkovOpponent(Opponent):
    """Hard level: several Markov chains that compete to predict the player.

    A chain of order k answers "after these k moves, what does the player
    usually play?":
        order 0 -> ignores the past, just counts favourite moves
        order 1 -> "after rock you usually play paper"
        order 2 -> "after rock, rock you usually play paper"
        order 3 -> longer cycles
    Each chain keeps a running score of how well it has predicted recently,
    and the CPU follows the one with the best score.
    """

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
        # Every move the player has made in this match, oldest first.
        self.history: list[str] = []
        # tables[k][last k moves][next move] -> weighted count
        # e.g. tables[2][("rock", "rock")] == {"paper": 1.9, "rock": 0.8}
        # defaultdict creates an empty row the first time a context is seen.
        self.tables: list[defaultdict[tuple[str, ...], dict[str, float]]] = [
            defaultdict(dict) for _ in range(max_order + 1)
        ]
        # How well each chain length has been predicting recently
        self.scores = [0.0] * (max_order + 1)
        # What each chain predicted this round, kept until observe() can
        # compare it with the real move and update the scores.
        self._pending: list[Optional[Distribution]] = [None] * (max_order + 1)

    def _predict_order(self, k: int) -> Optional[Distribution]:
        """Prediction of the order-k chain alone, or None if it has no data."""
        # Not enough moves yet to build a context of length k.
        if len(self.history) < k:
            return None
        # The context is the last k moves (empty tuple for order 0).
        context = tuple(self.history[-k:]) if k else ()
        counts = self.tables[k].get(context)
        # .get() instead of [] so that just looking doesn't create empty rows.
        if not counts:
            return None
        # Turn counts into probabilities that add up to 1.
        total = sum(counts.values())
        return {m: c / total for m, c in counts.items()}

    def predict(self) -> Optional[Distribution]:
        # Ask every chain, and remember the answers for observe().
        self._pending = [self._predict_order(k) for k in range(self.max_order + 1)]
        candidates = [k for k, d in enumerate(self._pending) if d]
        if not candidates:
            return None
        # Prefer the best scorer; on ties prefer the longer (more specific) chain
        best = max(candidates, key=lambda k: (self.scores[k], k))
        return self._pending[best]

    def observe(self, player_move: str) -> None:
        # 1) Grade each chain's prediction for this round.
        baseline = 1 / len(self.rules.moves)  # what a blind guess would get
        for k, dist in enumerate(self._pending):
            if dist:
                # Reward chains that gave the real move more probability than chance
                hit = dist.get(player_move, 0.0) - baseline
                # Old results weigh less every round (decay), recent ones more.
                self.scores[k] = self.decay * self.scores[k] + hit

        # 2) Teach every chain the move that followed its context.
        for k in range(self.max_order + 1):
            if len(self.history) < k:
                continue
            context = tuple(self.history[-k:]) if k else ()
            counts = self.tables[k][context]
            # Fade the old counts of this row first, so a strategy change
            # takes over after a few rounds instead of being drowned out.
            for m in counts:
                counts[m] *= self.decay
            counts[player_move] = counts.get(player_move, 0.0) + 1

        # 3) Remember the move and clear this round's predictions.
        self.history.append(player_move)
        self._pending = [None] * (self.max_order + 1)


class AdaptiveOpponent(MarkovOpponent):
    """A Markov chain of order 0: only looks at how often you use each move."""

    name = "Medium"
    description = "Spots the moves you use the most."

    def __init__(self, rules: Ruleset, rng: Optional[random.Random] = None) -> None:
        # Same algorithm as Hard, limited to order 0 and forgetting a bit faster.
        super().__init__(rules, rng, max_order=0, decay=0.85)


# Lookup by name, used by the "CPU" menu in the GUI: "Easy", "Medium", "Hard".
OPPONENTS: dict[str, type[Opponent]] = {
    cls.name: cls for cls in (RandomOpponent, AdaptiveOpponent, MarkovOpponent)
}
