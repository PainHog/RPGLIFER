"""XP-and-level math — a capped 1–100 mastery curve.

Each stat runs from 0 to 100, where 100 is mastery. The curve is deliberately
**front-loaded**: your first session is worth several levels and the bar moves
every time you log, then the climb slows as you approach mastery. That keeps
progress visible (the retention that an ever-slowing exponential kills) while
still making 100 a real, multi-month-to-year goal for a single focused stat.

    level(xp) = 100 * (xp / XP_TO_MAX) ** EXPONENT      (clamped to 100)

``EXPONENT < 1`` makes the curve concave — fast early, long tail. ``XP_TO_MAX``
is the only knob for "how much total effort is mastery"; with the default
2 XP/minute that is ~500 hours of a weight-1.0 activity.

Stats cap at 100, but the character's *overall* level (the sum of all eight,
0–800) has no practical ceiling, so there is always a number going up.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_LEVEL = 100
# Total XP (for a weight-1.0 activity) to reach level 100. At 2 XP/min that is
# ~500 hours of focused practice. Raise it to make mastery slower, lower to make
# it faster — nothing else needs to change.
XP_TO_MAX = 60_000
# Curve shape. Smaller = more front-loaded (faster early levels, longer tail).
EXPONENT = 0.40


def _cum_xp(level: int) -> float:
    """Total XP required to reach an integer ``level`` (0..MAX_LEVEL)."""
    if level <= 0:
        return 0.0
    if level >= MAX_LEVEL:
        return float(XP_TO_MAX)
    return XP_TO_MAX * (level / MAX_LEVEL) ** (1.0 / EXPONENT)


def xp_to_advance(level: int) -> int:
    """XP required to go from ``level`` to ``level + 1`` (0 at the cap)."""
    if level < 0:
        raise ValueError("level must be >= 0")
    if level >= MAX_LEVEL:
        return 0
    return int(round(_cum_xp(level + 1) - _cum_xp(level)))


@dataclass(frozen=True)
class LevelProgress:
    level: int
    xp_into_level: int
    xp_for_level: int
    total_xp: int

    @property
    def fraction(self) -> float:
        if self.xp_for_level <= 0:
            return 1.0 if self.level >= MAX_LEVEL else 0.0
        return max(0.0, min(1.0, self.xp_into_level / self.xp_for_level))


def level_for_xp(total_xp: float) -> LevelProgress:
    """Resolve total XP into a 0–100 level and progress toward the next one."""
    total = int(max(0, round(total_xp)))
    if total >= XP_TO_MAX:
        return LevelProgress(MAX_LEVEL, 1, 1, total)  # maxed: show a full bar
    level = int(MAX_LEVEL * (total / XP_TO_MAX) ** EXPONENT)
    level = max(0, min(level, MAX_LEVEL - 1))
    lo = _cum_xp(level)
    hi = _cum_xp(level + 1)
    return LevelProgress(level, int(round(total - lo)),
                         max(1, int(round(hi - lo))), total)


def level_of(total_xp: float) -> int:
    return level_for_xp(total_xp).level
