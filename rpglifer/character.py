"""The character model — the player's evolving self.

A :class:`Character` is really just a bag of per-stat XP plus a history of the
activities that produced it. Levels are never stored; they are always derived
from XP via :mod:`rpglifer.leveling`, so the numbers can never drift out of sync
with the log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import leveling
from .activities import Activity
from .stats import STAT_KEYS

SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class LogEntry:
    """One recorded session: an activity, how long, and the XP it produced."""

    activity: str
    minutes: float
    when: str  # ISO-8601 UTC timestamp
    xp: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "activity": self.activity,
            "minutes": self.minutes,
            "when": self.when,
            "xp": dict(self.xp),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        return cls(
            activity=str(data.get("activity", "Unknown")),
            minutes=float(data.get("minutes", 0.0)),
            when=str(data.get("when", "")),
            xp={str(k): float(v) for k, v in dict(data.get("xp", {})).items()},
        )


@dataclass
class LevelUp:
    stat: str
    from_level: int
    to_level: int


@dataclass
class LogResult:
    """What happened when an activity was logged — for UI feedback."""

    activity: str
    minutes: float
    gains: dict[str, float]
    level_ups: list[LevelUp]


class Character:
    def __init__(
        self,
        name: str = "Adventurer",
        stat_xp: dict[str, float] | None = None,
        log: list[LogEntry] | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        hero_points: int = 0,
        overachiever_points: int = 0,
    ) -> None:
        self.name = name or "Adventurer"
        # Always keep an entry for every known stat so the UI can render all of
        # them, even ones never trained yet.
        self.stat_xp: dict[str, float] = {key: 0.0 for key in STAT_KEYS}
        if stat_xp:
            for key, value in stat_xp.items():
                if key in self.stat_xp:
                    self.stat_xp[key] = float(value)
        self.log: list[LogEntry] = list(log or [])
        self.created_at = created_at or _now_iso()
        self.updated_at = updated_at or self.created_at
        # Reserved for future systems (battles, weekly challenges, gear).
        self.hero_points = int(hero_points)
        self.overachiever_points = int(overachiever_points)

    # --- Derived views -----------------------------------------------------
    def progress(self, stat_key: str) -> leveling.LevelProgress:
        return leveling.level_for_xp(self.stat_xp.get(stat_key, 0.0))

    def level(self, stat_key: str) -> int:
        return self.progress(stat_key).level

    def total_xp(self) -> float:
        return sum(self.stat_xp.values())

    def overall_level(self) -> int:
        """The character's headline level: the sum of every stat's level.

        With six stats each starting at level 1, a brand-new character sits at
        level 6 — a nudge that a hero is more than any single attribute.
        """
        return sum(self.level(key) for key in STAT_KEYS)

    # --- Mutation ----------------------------------------------------------
    def log_activity(
        self, activity: Activity, minutes: float, when: str | None = None
    ) -> LogResult:
        """Record ``minutes`` of ``activity``, award XP, and report level-ups."""
        if minutes <= 0:
            raise ValueError("minutes must be positive")

        before = {key: self.level(key) for key in STAT_KEYS}
        gains = activity.xp_split(minutes)
        for key, amount in gains.items():
            if key in self.stat_xp:
                self.stat_xp[key] += amount

        timestamp = when or _now_iso()
        entry = LogEntry(activity=activity.name, minutes=float(minutes),
                         when=timestamp, xp=dict(gains))
        self.log.append(entry)
        self.updated_at = timestamp

        level_ups = [
            LevelUp(key, before[key], self.level(key))
            for key in STAT_KEYS
            if self.level(key) > before[key]
        ]
        return LogResult(activity.name, float(minutes), dict(gains), level_ups)

    def recent(self, count: int = 10) -> list[LogEntry]:
        return list(reversed(self.log[-count:]))

    # --- Persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "name": self.name,
            "stat_xp": dict(self.stat_xp),
            "log": [entry.to_dict() for entry in self.log],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "hero_points": self.hero_points,
            "overachiever_points": self.overachiever_points,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        return cls(
            name=str(data.get("name", "Adventurer")),
            stat_xp={str(k): float(v) for k, v in dict(data.get("stat_xp", {})).items()},
            log=[LogEntry.from_dict(d) for d in data.get("log", [])],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            hero_points=int(data.get("hero_points", 0)),
            overachiever_points=int(data.get("overachiever_points", 0)),
        )
