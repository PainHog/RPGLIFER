"""The character model — the player's evolving self.

A :class:`Character` is really just a bag of per-stat XP plus a history of the
activities that produced it. Levels are never stored; they are always derived
from XP via :mod:`rpglifer.leveling`, so the numbers can never drift out of sync
with the log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from . import leveling
from .activities import Activity
from .stats import STAT_KEYS
from .titles import title_for

SCHEMA_VERSION = 1

# --- Consistency (weekly-streak) rewards -----------------------------------
# Doing the same activity in consecutive calendar weeks builds a streak. Each
# week of the streak beyond the first adds a flat bonus to the XP that activity
# earns, up to a cap — so continued dedication pays off without snowballing out
# of control.
STREAK_BONUS_PER_WEEK = 0.10  # +10% per consecutive week after the first
STREAK_BONUS_CAP = 0.50  # never more than +50% (reached at a 6-week streak)


def consistency_bonus(streak: int) -> float:
    """Fractional XP bonus for a weekly ``streak`` (0.0 = none, 0.5 = +50%)."""
    if streak <= 1:
        return 0.0
    return min((streak - 1) * STREAK_BONUS_PER_WEEK, STREAK_BONUS_CAP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat()


def _parse_dt(when: str) -> datetime | None:
    try:
        return datetime.fromisoformat(when)
    except (ValueError, TypeError):
        return None


def _week_key(dt: datetime) -> tuple[int, int]:
    """ISO (year, week) — the unit a weekly streak is counted in."""
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def _prev_week(key: tuple[int, int]) -> tuple[int, int]:
    """The (year, week) immediately before ``key`` (handles year boundaries)."""
    monday = date.fromisocalendar(key[0], key[1], 1) - timedelta(days=7)
    iso = monday.isocalendar()
    return (iso[0], iso[1])


@dataclass
class LogEntry:
    """One recorded session: an activity, how long, and the XP it produced."""

    activity: str
    minutes: float
    when: str  # ISO-8601 UTC timestamp
    xp: dict[str, float] = field(default_factory=dict)
    streak: int = 0  # weekly streak this entry was part of
    bonus: float = 0.0  # consistency bonus applied (e.g. 0.2 == +20%)

    def to_dict(self) -> dict:
        return {
            "activity": self.activity,
            "minutes": self.minutes,
            "when": self.when,
            "xp": dict(self.xp),
            "streak": self.streak,
            "bonus": self.bonus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        return cls(
            activity=str(data.get("activity", "Unknown")),
            minutes=float(data.get("minutes", 0.0)),
            when=str(data.get("when", "")),
            xp={str(k): float(v) for k, v in dict(data.get("xp", {})).items()},
            streak=int(data.get("streak", 0)),
            bonus=float(data.get("bonus", 0.0)),
        )


@dataclass
class LevelUp:
    stat: str
    from_level: int
    to_level: int


@dataclass
class TitleUnlock:
    stat: str
    title: str
    level: int


@dataclass
class LogResult:
    """What happened when an activity was logged — for UI feedback."""

    activity: str
    minutes: float
    gains: dict[str, float]
    level_ups: list[LevelUp]
    streak: int = 1
    bonus: float = 0.0
    titles: list[TitleUnlock] = field(default_factory=list)


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

    # --- Consistency -------------------------------------------------------
    def _activity_weeks(self, activity_name: str) -> set[tuple[int, int]]:
        weeks: set[tuple[int, int]] = set()
        for entry in self.log:
            if entry.activity == activity_name:
                dt = _parse_dt(entry.when)
                if dt is not None:
                    weeks.add(_week_key(dt))
        return weeks

    def consistency(
        self, activity_name: str, at: datetime | None = None
    ) -> tuple[int, float]:
        """Streak and XP bonus this activity would earn if logged at ``at``.

        The streak counts consecutive calendar weeks — ending at ``at``'s week,
        which is treated as covered because we are (or would be) logging then.
        Returns ``(streak_weeks, bonus_fraction)``.
        """
        ref = _week_key(at or _now())
        weeks = self._activity_weeks(activity_name)
        weeks.add(ref)  # logging now covers the current week
        streak = 0
        cursor = ref
        while cursor in weeks:
            streak += 1
            cursor = _prev_week(cursor)
        return streak, consistency_bonus(streak)

    def title(self, stat_key: str) -> str | None:
        """Current earned title for ``stat_key`` (``None`` if none yet)."""
        return title_for(stat_key, self.level(stat_key))

    # --- Mutation ----------------------------------------------------------
    def log_activity(
        self, activity: Activity, minutes: float, when: str | None = None
    ) -> LogResult:
        """Record ``minutes`` of ``activity``, award XP, and report what changed.

        XP is the per-stat split scaled by the activity's current consistency
        bonus. Level-ups and any newly unlocked titles are returned for the UI.
        """
        if minutes <= 0:
            raise ValueError("minutes must be positive")

        timestamp = when or _now_iso()
        ref_dt = _parse_dt(timestamp) or _now()
        streak, bonus = self.consistency(activity.name, at=ref_dt)
        multiplier = 1.0 + bonus

        before = {key: self.level(key) for key in STAT_KEYS}
        gains = {k: v * multiplier for k, v in activity.xp_split(minutes).items()}
        for key, amount in gains.items():
            if key in self.stat_xp:
                self.stat_xp[key] += amount

        entry = LogEntry(activity=activity.name, minutes=float(minutes),
                         when=timestamp, xp=dict(gains), streak=streak, bonus=bonus)
        self.log.append(entry)
        self.updated_at = timestamp

        level_ups: list[LevelUp] = []
        titles: list[TitleUnlock] = []
        for key in STAT_KEYS:
            after = self.level(key)
            if after > before[key]:
                level_ups.append(LevelUp(key, before[key], after))
                old_title = title_for(key, before[key])
                new_title = title_for(key, after)
                if new_title is not None and new_title != old_title:
                    titles.append(TitleUnlock(key, new_title, after))

        return LogResult(activity.name, float(minutes), dict(gains), level_ups,
                         streak=streak, bonus=bonus, titles=titles)

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
