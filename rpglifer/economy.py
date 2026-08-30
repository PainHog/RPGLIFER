"""The points economy — how Hero and Overachiever points are earned.

Two currencies, four sources (all reward *doing more of life*, never buying stats):

* **Hero points** — from progress and reaching out: level-ups, new titles, mastery
  ★s, and a "reach" bonus for training a weak stat or trying something new. Also
  the payout from Adventure battles (see :mod:`rpglifer.adventure`).
* **Overachiever points** — from the weekly *well-rounded* challenge: cover enough
  different stats in one calendar week and you earn a lump sum, once per week.

This module is pure combinators over already-computed data; the character model
wires it into logging.
"""

from __future__ import annotations

from .recommend import weakest_stats

# Hero point payouts for progress events.
HERO_PER_LEVEL = 1
HERO_PER_TITLE = 10
HERO_PER_STAR = 50
HERO_REACH_BONUS = 3  # training a weak stat, or trying a brand-new activity

# Weekly well-rounded challenge.
WEEKLY_TARGET_STATS = 6  # distinct stats to train in one calendar week
OVERACHIEVER_WEEKLY = 30  # payout when the week's challenge completes


def points_for_events(level_ups, titles, star_ups) -> int:
    """Hero points earned from a log's progress events."""
    return (HERO_PER_LEVEL * len(level_ups)
            + HERO_PER_TITLE * len(titles)
            + HERO_PER_STAR * len(star_ups))


def reach_bonus(character, activity, was_new: bool) -> int:
    """Hero points for reaching outside your comfort zone.

    Awarded when the activity's primary stat is one of your weakest, or when it's
    an activity you've never logged before.
    """
    weak = set(weakest_stats(character, 3))
    primary = activity.primary_stats()[0] if activity.weights else None
    if was_new or (primary in weak):
        return HERO_REACH_BONUS
    return 0
