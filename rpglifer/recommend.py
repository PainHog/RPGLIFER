"""Suggestions that nudge the player toward a well-rounded life.

Two helpers power the "Suggested for you" panel and the stat tooltips:

* :func:`recommendations` proposes activities that would shore up the player's
  weakest stats, favoring ones they haven't tried yet (exploration) and, gently,
  categories they already dabble in (a familiar on-ramp).
* :func:`top_activities_for_stat` answers "how do I raise this?" for any stat.
"""

from __future__ import annotations

from collections import Counter

from .activities import ACTIVITIES, Activity, activity_by_name
from .stats import STAT_KEYS

EXPLORE_BONUS = 0.4  # added when an activity is new to the player
FAMILIAR_BONUS = 0.15  # added when it shares a category with recent activity
MAX_PER_CATEGORY = 2  # keep the suggestion list varied


def top_activities_for_stat(stat_key: str, n: int = 4,
                            catalog: tuple[Activity, ...] = ACTIVITIES) -> list[Activity]:
    """Activities that most strongly develop ``stat_key``, heaviest first."""
    ranked = sorted((a for a in catalog if stat_key in a.weights),
                    key=lambda a: -a.weights[stat_key])
    return ranked[:n]


def weakest_stats(character, n: int = 2) -> list[str]:
    """The player's ``n`` least-developed stats, by total XP (ascending)."""
    return sorted(STAT_KEYS, key=lambda k: character.stat_xp.get(k, 0.0))[:n]


def recommendations(character, count: int = 6,
                    catalog: tuple[Activity, ...] = ACTIVITIES) -> list[Activity]:
    """Suggest activities that round the player out — new ones for weak stats."""
    done = {e.activity for e in character.log}
    recent_categories = Counter(
        a.category
        for e in character.recent(15)
        if (a := activity_by_name(e.activity)) is not None
    )
    weak = set(weakest_stats(character, 2))

    scored: list[tuple[float, Activity]] = []
    for activity in catalog:
        help_weak = sum(activity.weights.get(k, 0.0) for k in weak)
        if help_weak <= 0:
            continue
        score = help_weak
        if activity.name not in done:
            score += EXPLORE_BONUS
        if activity.category in recent_categories:
            score += FAMILIAR_BONUS
        scored.append((score, activity))

    scored.sort(key=lambda pair: -pair[0])

    picked: list[Activity] = []
    used: Counter = Counter()
    for _, activity in scored:
        if used[activity.category] >= MAX_PER_CATEGORY:
            continue
        picked.append(activity)
        used[activity.category] += 1
        if len(picked) >= count:
            break
    return picked
