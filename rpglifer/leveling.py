"""XP-and-level math.

Every stat accumulates experience points (XP). A stat's *level* is derived
purely from its total XP through a growth curve: early levels come quickly and
each successive level costs a little more — the classic RPG feel.

Everything here is a pure function of the inputs (no hidden state), so it is
easy to test and safe to call from anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Curve tuning ----------------------------------------------------------
# BASE_XP is the cost of the very first level-up (level 1 -> 2). Each further
# level costs GROWTH times the one before it. Bump BASE_XP up to make the whole
# game slower; raise GROWTH to make high levels grind harder.
#
# Pacing goal: leveling a single stat should take *multiple weeks* of genuine
# dedication, not a week. With the default 2 XP/minute (see activities.py), the
# cumulative cost to reach a stat level is roughly:
#     Lv 3  ~= 240 XP   (~2 hours of the activity)   — a first title, early on
#     Lv 5  ~= 710 XP   (~6 hours)                    — a couple of weeks
#     Lv 10 ~= 4,900 XP (~41 hours)                   — a couple of months
#     Lv 20 ~= 149,000 XP                             — a long-haul grind
# The first level-up stays quick (100 XP ~ 50 min) so day one still feels good.
BASE_XP = 100
GROWTH = 1.4
# Hard ceiling so a corrupted save can never spin the loop forever.
MAX_LEVEL = 999


def xp_to_advance(level: int) -> int:
    """XP required to advance *from* ``level`` to ``level + 1`` (``level >= 1``)."""
    if level < 1:
        raise ValueError("level must be >= 1")
    return int(round(BASE_XP * (GROWTH ** (level - 1))))


@dataclass(frozen=True)
class LevelProgress:
    """A snapshot of where a given XP total lands on the curve."""

    level: int
    xp_into_level: int  # XP earned toward the next level
    xp_for_level: int  # total XP the current level costs
    total_xp: int

    @property
    def fraction(self) -> float:
        """Progress through the current level in the range ``[0.0, 1.0]``."""
        if self.xp_for_level <= 0:
            return 0.0
        return max(0.0, min(1.0, self.xp_into_level / self.xp_for_level))


def level_for_xp(total_xp: float) -> LevelProgress:
    """Resolve a total XP amount into a level and progress toward the next one."""
    total = int(max(0, round(total_xp)))
    remaining = total
    level = 1
    while level < MAX_LEVEL:
        need = xp_to_advance(level)
        if remaining < need:
            return LevelProgress(level, remaining, need, total)
        remaining -= need
        level += 1
    return LevelProgress(MAX_LEVEL, 0, xp_to_advance(MAX_LEVEL), total)


def level_of(total_xp: float) -> int:
    """Convenience: just the integer level for a total XP amount."""
    return level_for_xp(total_xp).level
