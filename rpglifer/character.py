"""The character model — the player's evolving self.

A :class:`Character` is really just a bag of per-stat XP plus a history of the
activities that produced it. Levels are never stored; they are always derived
from XP via :mod:`rpglifer.leveling`, so the numbers can never drift out of sync
with the log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from . import achievements as achievements_mod
from . import economy, leveling, quests
from .activities import Activity, activity_by_name
from .gear import SLOTS, Gear
from .recommend import weakest_stats
from .stats import STAT_KEYS
from .titles import title_for

SCHEMA_VERSION = 2

# Prestige: XP earned per ★. Completing a full 0→100 mastery climb (this much XP)
# resets the visible bar to 0 and grants a star; XP itself is never lost.
STAR_XP = leveling.XP_TO_MAX

# Adventure: free Arena battles refill to this each day.
ARENA_RUNS_PER_DAY = 5

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
class StarUp:
    """A stat crossed a mastery boundary and earned a ★ (prestige)."""

    stat: str
    star: int


@dataclass
class Bonus:
    """A temporary boost bought in the Shop — never a stat, always an effect.

    ``kind`` is ``"xp_mult"`` (time-limited XP multiplier) or ``"combat_power"``
    (adds to Arena Power for a limited number of fights).
    """

    id: str
    name: str
    kind: str
    magnitude: float
    expires_at: str = ""  # ISO timestamp; "" = not time-limited
    uses_left: int = -1  # -1 = unlimited (time-based bonuses)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "kind": self.kind,
                "magnitude": self.magnitude, "expires_at": self.expires_at,
                "uses_left": self.uses_left}

    @classmethod
    def from_dict(cls, d: dict) -> "Bonus":
        return cls(id=str(d.get("id", "")), name=str(d.get("name", "Bonus")),
                   kind=str(d.get("kind", "xp_mult")),
                   magnitude=float(d.get("magnitude", 0.0)),
                   expires_at=str(d.get("expires_at", "")),
                   uses_left=int(d.get("uses_left", -1)))


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
    star_ups: list[StarUp] = field(default_factory=list)
    hero_gain: int = 0
    overachiever_gain: int = 0
    quests_done: list = field(default_factory=list)
    achievements: list = field(default_factory=list)


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
        bonuses: list["Bonus"] | None = None,
        challenges_claimed: list[str] | None = None,
        arena_day: str = "",
        arena_used: int = 0,
        inventory: list["Gear"] | None = None,
        equipped: dict[str, str] | None = None,
        daily: dict | None = None,
        quests_claimed: list[str] | None = None,
        achievements: list[str] | None = None,
        counters: dict | None = None,
        owned_cosmetics: list[str] | None = None,
        ring_color: str = "",
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
        self.hero_points = int(hero_points)
        self.overachiever_points = int(overachiever_points)
        self.bonuses: list[Bonus] = list(bonuses or [])
        self.challenges_claimed: list[str] = list(challenges_claimed or [])
        self.arena_day = str(arena_day)  # ISO date of the last Arena run
        self.arena_used = int(arena_used)  # runs used on arena_day
        self.inventory: list[Gear] = list(inventory or [])
        self.equipped: dict[str, str] = dict(equipped or {})  # slot -> gear id
        # Per-day counters the log can't show (level-ups, Arena wins) + claimed
        # daily quests ("YYYY-MM-DD:questid").
        self.daily: dict[str, dict] = dict(daily or {})
        self.quests_claimed: list[str] = list(quests_claimed or [])
        self.achievements: list[str] = list(achievements or [])
        # Lifetime tallies (e.g. bosses defeated, vault chests opened).
        self.counters: dict[str, int] = {k: int(v) for k, v in dict(counters or {}).items()}
        # Cosmetics: owned unlocks + the selected level-ring color ("" = default).
        self.owned_cosmetics: list[str] = list(owned_cosmetics or [])
        self.ring_color = str(ring_color)

    def bump_counter(self, name: str, n: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + n

    # --- Derived views -----------------------------------------------------
    # Prestige: a stat's XP never resets. Each full 0→100 climb (STAR_XP worth of
    # XP) earns a ★. `progress`/`level` describe the CURRENT star's 0–99 climb
    # (the bar you're filling); `stars` and `effective_level` describe the
    # uncapped whole — so nothing is ever walled off.
    def stars(self, stat_key: str) -> int:
        return int(self.stat_xp.get(stat_key, 0.0) // STAR_XP)

    def progress(self, stat_key: str) -> leveling.LevelProgress:
        xp_in_star = self.stat_xp.get(stat_key, 0.0) % STAR_XP
        return leveling.level_for_xp(xp_in_star)

    def level(self, stat_key: str) -> int:
        """Level within the current star (0–99)."""
        return self.progress(stat_key).level

    def effective_level(self, stat_key: str) -> int:
        """Uncapped level: stars × 100 + level in the current star."""
        return self.stars(stat_key) * 100 + self.level(stat_key)

    def total_xp(self) -> float:
        return sum(self.stat_xp.values())

    def overall_level(self) -> int:
        """Headline level: the sum of every stat's *effective* level (uncapped)."""
        return sum(self.effective_level(key) for key in STAT_KEYS)

    # --- Bonuses (temporary boosts bought in the Shop) ---------------------
    def _bonus_active(self, b: "Bonus", now: datetime) -> bool:
        if b.expires_at:
            dt = _parse_dt(b.expires_at)
            return dt is None or dt > now
        if b.uses_left >= 0:
            return b.uses_left > 0
        return True

    def active_bonuses(self, now: datetime | None = None) -> list["Bonus"]:
        now = now or _now()
        return [b for b in self.bonuses if self._bonus_active(b, now)]

    def xp_multiplier(self, now: datetime | None = None) -> float:
        """Total XP multiplier from active ``xp_mult`` bonuses (1.0 = none)."""
        return 1.0 + sum(b.magnitude for b in self.active_bonuses(now)
                         if b.kind == "xp_mult")

    def combat_bonus(self, now: datetime | None = None) -> float:
        """Total Power bonus from active ``combat_power`` bonuses."""
        return sum(b.magnitude for b in self.active_bonuses(now)
                   if b.kind == "combat_power")

    def add_bonus(self, bonus: "Bonus") -> None:
        self.bonuses.append(bonus)

    def consume_combat_bonuses(self, now: datetime | None = None) -> float:
        """Spend one use of each active combat bonus (for an Arena run)."""
        now = now or _now()
        total = 0.0
        for b in self.bonuses:
            if b.kind == "combat_power" and self._bonus_active(b, now):
                total += b.magnitude
                if b.uses_left > 0:
                    b.uses_left -= 1
        self.prune_bonuses(now)
        return total

    def prune_bonuses(self, now: datetime | None = None) -> None:
        now = now or _now()
        self.bonuses = [b for b in self.bonuses if self._bonus_active(b, now)]

    # --- Adventure energy --------------------------------------------------
    def arena_energy(self, at: datetime | None = None) -> int:
        today = (at or _now()).date().isoformat()
        used = self.arena_used if self.arena_day == today else 0
        return max(0, ARENA_RUNS_PER_DAY - used)

    def spend_arena_energy(self, at: datetime | None = None) -> bool:
        today = (at or _now()).date().isoformat()
        if self.arena_day != today:
            self.arena_day = today
            self.arena_used = 0
        if self.arena_used >= ARENA_RUNS_PER_DAY:
            return False
        self.arena_used += 1
        return True

    # --- Weekly well-rounded challenge -------------------------------------
    def stats_trained_in_week(self, week: tuple[int, int]) -> set[str]:
        trained: set[str] = set()
        for e in self.log:
            dt = _parse_dt(e.when)
            if dt is not None and _week_key(dt) == week:
                trained.update(k for k, v in e.xp.items() if v > 0)
        return trained

    def stats_trained_this_week(self, at: datetime | None = None) -> set[str]:
        """The core stat keys trained so far in the current calendar week."""
        return self.stats_trained_in_week(_week_key(at or _now())) & set(STAT_KEYS)

    def weekly_wellrounded(self, at: datetime | None = None):
        """Return ``(stats_covered, target, complete, week_key_str)``."""
        wk = _week_key(at or _now())
        covered = len(self.stats_trained_in_week(wk) & set(STAT_KEYS))
        key = f"{wk[0]}-W{wk[1]:02d}"
        return covered, economy.WEEKLY_TARGET_STATS, \
            covered >= economy.WEEKLY_TARGET_STATS, key

    # --- Gear --------------------------------------------------------------
    def add_gear(self, g: "Gear") -> None:
        self.inventory.append(g)

    def gear_by_id(self, gid: str | None) -> "Gear | None":
        return next((x for x in self.inventory if x.id == gid), None)

    def equip(self, gid: str) -> bool:
        g = self.gear_by_id(gid)
        if g is None:
            return False
        self.equipped[g.slot] = g.id
        return True

    def unequip(self, slot: str) -> None:
        self.equipped.pop(slot, None)

    def equipped_gear(self) -> list["Gear"]:
        out = []
        for slot in SLOTS:
            g = self.gear_by_id(self.equipped.get(slot))
            if g is not None:
                out.append(g)
        return out

    def gear_bonuses(self) -> dict[str, int]:
        """Total flat bonus to each derived stat from equipped gear."""
        total: dict[str, int] = {}
        for g in self.equipped_gear():
            for k, v in g.bonuses.items():
                total[k] = total.get(k, 0) + int(v)
        return total

    # --- Daily quests ------------------------------------------------------
    def _bump_daily(self, at: datetime, key: str, n: int) -> None:
        d = self.daily.setdefault(at.date().isoformat(), {})
        d[key] = d.get(key, 0) + n

    def daily_metrics(self, date_str: str) -> dict:
        entries = [e for e in self.log if e.when[:10] == date_str]
        stats: set[str] = set()
        weak = set(weakest_stats(self, 3))
        weak_hit = new = False
        max_minutes = 0.0
        for e in entries:
            stats.update(k for k, v in e.xp.items() if v > 0)
            max_minutes = max(max_minutes, e.minutes)
            a = activity_by_name(e.activity)
            if a and a.primary_stats() and a.primary_stats()[0] in weak:
                weak_hit = True
            first = min((x.when for x in self.log if x.activity == e.activity),
                        default=e.when)
            if first[:10] == date_str:
                new = True
        d = self.daily.get(date_str, {})
        return {"count": len(entries), "stats": len(stats), "weak": weak_hit,
                "new": new, "max_minutes": max_minutes,
                "levelups": d.get("levelups", 0), "arena_wins": d.get("arena_wins", 0)}

    def quest_status(self, at: datetime | None = None) -> list[tuple]:
        """Today's quests as ``(quest, complete, claimed)`` triples."""
        date_str = (at or _now()).date().isoformat()
        m = self.daily_metrics(date_str)
        out = []
        for q in quests.daily_quests(date_str):
            claimed = f"{date_str}:{q.id}" in self.quests_claimed
            out.append((q, q.check(m), claimed))
        return out

    def evaluate_daily_quests(self, at: datetime | None = None) -> list:
        """Award any newly completed daily quests; return the completed list."""
        date_str = (at or _now()).date().isoformat()
        m = self.daily_metrics(date_str)
        done = []
        for q in quests.daily_quests(date_str):
            key = f"{date_str}:{q.id}"
            if key in self.quests_claimed:
                continue
            if q.check(m):
                self.hero_points += q.reward
                self.quests_claimed.append(key)
                done.append(q)
        return done

    def record_arena_win(self, at: datetime | None = None) -> list:
        self._bump_daily(at or _now(), "arena_wins", 1)
        return self.evaluate_daily_quests(at)

    # --- Achievements ------------------------------------------------------
    def check_achievements(self) -> list:
        """Unlock any newly-earned achievements; return the list unlocked now."""
        newly = []
        for a in achievements_mod.ACHIEVEMENTS:
            if a.id in self.achievements:
                continue
            try:
                if a.check(self):
                    self.achievements.append(a.id)
                    newly.append(a)
            except Exception:
                pass
        return newly

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
        """Current earned title (``None`` if none yet) — based on effective level.

        Titles top out at the capstone (level 100); beyond that the ★ count is
        the prestige signal, and the title stays maxed.
        """
        return title_for(stat_key, self.effective_level(stat_key))

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
        was_new = activity.name not in {e.activity for e in self.log}
        streak, bonus = self.consistency(activity.name, at=ref_dt)
        # XP is scaled by the streak bonus AND any active Shop XP boost.
        multiplier = (1.0 + bonus) * self.xp_multiplier(ref_dt)

        eff_before = {key: self.effective_level(key) for key in STAT_KEYS}
        star_before = {key: self.stars(key) for key in STAT_KEYS}
        gains = {k: v * multiplier for k, v in activity.xp_split(minutes).items()}
        for key, amount in gains.items():
            if key in self.stat_xp:
                self.stat_xp[key] += amount

        entry = LogEntry(activity=activity.name, minutes=float(minutes),
                         when=timestamp, xp=dict(gains), streak=streak, bonus=bonus)
        self.log.append(entry)
        self.updated_at = timestamp

        level_ups: list[LevelUp] = []
        star_ups: list[StarUp] = []
        titles: list[TitleUnlock] = []
        for key in STAT_KEYS:
            stars_after = self.stars(key)
            if stars_after > star_before[key]:
                # Crossed one (or more) mastery boundaries — that's the headline.
                star_ups.append(StarUp(key, stars_after))
            elif self.effective_level(key) > eff_before[key]:
                level_ups.append(LevelUp(key, eff_before[key] % 100,
                                         self.effective_level(key) % 100))
            old_title = title_for(key, eff_before[key])
            new_title = title_for(key, self.effective_level(key))
            if new_title is not None and new_title != old_title:
                titles.append(TitleUnlock(key, new_title, self.effective_level(key)))

        # Points — Hero for progress + reaching out, Overachiever for the weekly
        # well-rounded challenge (once per calendar week).
        hero_gain = (economy.points_for_events(level_ups, titles, star_ups)
                     + economy.reach_bonus(self, activity, was_new))
        self.hero_points += hero_gain

        overachiever_gain = 0
        _, _, complete, week_key = self.weekly_wellrounded(ref_dt)
        if complete and week_key not in self.challenges_claimed:
            overachiever_gain = economy.OVERACHIEVER_WEEKLY
            self.overachiever_points += overachiever_gain
            self.challenges_claimed.append(week_key)

        # Daily quests — record level-ups, then award any that just completed.
        self._bump_daily(ref_dt, "levelups", len(level_ups) + len(star_ups))
        quests_done = self.evaluate_daily_quests(ref_dt)
        hero_gain += sum(q.reward for q in quests_done)
        unlocked = self.check_achievements()

        self.prune_bonuses(ref_dt)

        return LogResult(activity.name, float(minutes), dict(gains), level_ups,
                         streak=streak, bonus=bonus, titles=titles, star_ups=star_ups,
                         hero_gain=hero_gain, overachiever_gain=overachiever_gain,
                         quests_done=quests_done, achievements=unlocked)

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
            "bonuses": [b.to_dict() for b in self.bonuses],
            "challenges_claimed": list(self.challenges_claimed),
            "arena_day": self.arena_day,
            "arena_used": self.arena_used,
            "inventory": [g.to_dict() for g in self.inventory],
            "equipped": dict(self.equipped),
            "daily": dict(self.daily),
            "quests_claimed": list(self.quests_claimed),
            "achievements": list(self.achievements),
            "counters": dict(self.counters),
            "owned_cosmetics": list(self.owned_cosmetics),
            "ring_color": self.ring_color,
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
            bonuses=[Bonus.from_dict(b) for b in data.get("bonuses", [])],
            challenges_claimed=[str(w) for w in data.get("challenges_claimed", [])],
            arena_day=str(data.get("arena_day", "")),
            arena_used=int(data.get("arena_used", 0)),
            inventory=[Gear.from_dict(g) for g in data.get("inventory", [])],
            equipped={str(k): str(v) for k, v in dict(data.get("equipped", {})).items()},
            daily={str(k): dict(v) for k, v in dict(data.get("daily", {})).items()},
            quests_claimed=[str(q) for q in data.get("quests_claimed", [])],
            achievements=[str(a) for a in data.get("achievements", [])],
            counters={str(k): int(v) for k, v in dict(data.get("counters", {})).items()},
            owned_cosmetics=[str(x) for x in data.get("owned_cosmetics", [])],
            ring_color=str(data.get("ring_color", "")),
        )
