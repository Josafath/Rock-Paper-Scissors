"""Persistent match history (JSON) and the statistics derived from it."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .game import Match

SCHEMA_VERSION = 1


def default_path() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "rps-arena" / "stats.json"


def match_to_record(match: Match) -> dict[str, Any]:
    return {
        "date": match.started_at.isoformat(timespec="seconds"),
        "ruleset": match.rules.name,
        "difficulty": match.opponent.name,
        "target": match.target,
        "result": match.result.value if match.result else None,
        "player_score": match.player_score,
        "cpu_score": match.cpu_score,
        "rounds": [
            {"player": r.player, "cpu": r.cpu, "outcome": r.outcome.value, "predicted": r.predicted}
            for r in match.rounds
        ],
    }


class StatsStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else default_path()
        self.matches: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") == SCHEMA_VERSION:
                return list(data["matches"])
        except FileNotFoundError:
            return []
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
        # Unreadable or unknown format: keep a copy instead of silently losing it
        self.path.replace(self.path.with_suffix(".corrupt.json"))
        return []

    def record(self, match: Match) -> None:
        if not match.is_over:
            raise ValueError("Only finished matches are recorded")
        self.matches.append(match_to_record(match))
        self.save()

    def reset(self) -> None:
        self.matches = []
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = {"version": SCHEMA_VERSION, "matches": self.matches}
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic: never leaves a half-written file

    def summary(self) -> "Summary":
        return summarize(self.matches)


@dataclass
class Summary:
    matches: int = 0
    wins: int = 0
    rounds: Counter = field(default_factory=Counter)  # outcome -> count
    moves: Counter = field(default_factory=Counter)  # player move -> count
    best_streak: int = 0
    current_streak: int = 0  # >0 winning streak, <0 losing streak
    reads: int = 0
    predictions: int = 0
    by_difficulty: dict[str, tuple[int, int]] = field(default_factory=dict)  # name -> (wins, played)

    @property
    def win_rate(self) -> Optional[float]:
        return self.wins / self.matches if self.matches else None

    @property
    def read_rate(self) -> Optional[float]:
        return self.reads / self.predictions if self.predictions else None

    @property
    def favorite_move(self) -> Optional[str]:
        return self.moves.most_common(1)[0][0] if self.moves else None


def summarize(matches: list[dict[str, Any]]) -> Summary:
    s = Summary()
    streak = 0
    for m in matches:
        won = m["result"] == "win"
        s.matches += 1
        s.wins += won
        w, p = s.by_difficulty.get(m["difficulty"], (0, 0))
        s.by_difficulty[m["difficulty"]] = (w + won, p + 1)
        if won:
            streak = streak + 1 if streak > 0 else 1
        else:
            streak = streak - 1 if streak < 0 else -1
        s.best_streak = max(s.best_streak, streak)
        for r in m["rounds"]:
            s.rounds[r["outcome"]] += 1
            s.moves[r["player"]] += 1
            if r.get("predicted"):
                s.predictions += 1
                s.reads += r["predicted"] == r["player"]
    s.current_streak = streak
    return s
