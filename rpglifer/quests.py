"""Daily quests — small, rotating goals that pay Hero points.

Three quests are drawn deterministically from the date (everyone gets the same
set on a given day, and it's stable through the day). Each is a pure predicate
over the day's metrics, so completion is derived from what you actually did —
the character model tracks a couple of counters (level-ups, Arena wins) that the
log alone can't show.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

DAILY_COUNT = 3


@dataclass(frozen=True)
class Quest:
    id: str
    text: str
    reward: int  # Hero points
    check: Callable[[dict], bool]


QUEST_TEMPLATES: tuple[Quest, ...] = (
    Quest("log3", "Log 3 activities today", 8, lambda m: m["count"] >= 3),
    Quest("log5", "Log 5 activities today", 15, lambda m: m["count"] >= 5),
    Quest("weak", "Train one of your weakest stats", 10, lambda m: m["weak"]),
    Quest("new", "Try a brand-new activity", 10, lambda m: m["new"]),
    Quest("levelup", "Earn a level-up", 8, lambda m: m["levelups"] >= 1),
    Quest("arena", "Win an Arena battle", 12, lambda m: m["arena_wins"] >= 1),
    Quest("variety", "Train 4 different stats today", 12, lambda m: m["stats"] >= 4),
    Quest("focus60", "Spend 60+ minutes on one activity", 10,
          lambda m: m["max_minutes"] >= 60),
)


def daily_quests(date_str: str) -> list[Quest]:
    """The three quests for a given ISO date (stable, seeded by the date)."""
    rng = random.Random(f"rpglifer-{date_str}")
    return rng.sample(QUEST_TEMPLATES, DAILY_COUNT)
