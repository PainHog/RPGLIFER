"""Achievements — collectible trophies unlocked by milestones.

Each is a pure predicate over the character's *current* state, so unlocking is
idempotent: re-checking never double-awards, and a save from an older version
retro-unlocks anything already earned. The character model calls
``check_achievements`` after logging, Arena wins, and gear changes.

Check functions take a duck-typed character (this module must not import the
character model — that would be circular).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .stats import STAT_KEYS


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    desc: str
    check: Callable[[object], bool]


def _stars_total(c) -> int:
    return sum(c.stars(k) for k in STAT_KEYS)


def _arena_wins(c) -> int:
    return sum(int(d.get("arena_wins", 0)) for d in c.daily.values())


def _max_streak(c) -> int:
    names = {e.activity for e in c.log}
    return max((c.consistency(n)[0] for n in names), default=0)


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first_step", "First Step", "Log your first activity.",
                lambda c: len(c.log) >= 1),
    Achievement("getting_going", "Getting Going", "Log 10 activities.",
                lambda c: len(c.log) >= 10),
    Achievement("centurion", "Centurion", "Log 100 activities.",
                lambda c: len(c.log) >= 100),
    Achievement("true_lifer", "True Lifer", "Log 500 activities.",
                lambda c: len(c.log) >= 500),
    Achievement("apprentice", "Apprentice", "Reach level 10 in any stat.",
                lambda c: any(c.effective_level(k) >= 10 for k in STAT_KEYS)),
    Achievement("renaissance", "Renaissance Soul",
                "Reach level 10 in all eight stats.",
                lambda c: all(c.effective_level(k) >= 10 for k in STAT_KEYS)),
    Achievement("first_master", "First Mastery", "Earn your first ★.",
                lambda c: _stars_total(c) >= 1),
    Achievement("constellation", "Constellation", "Earn 5 ★ in total.",
                lambda c: _stars_total(c) >= 5),
    Achievement("hero", "Hero", "Reach overall level 100.",
                lambda c: c.overall_level() >= 100),
    Achievement("living_legend", "Living Legend", "Reach overall level 400.",
                lambda c: c.overall_level() >= 400),
    Achievement("gladiator", "Gladiator", "Win your first Arena battle.",
                lambda c: _arena_wins(c) >= 1),
    Achievement("champion", "Champion", "Win 25 Arena battles.",
                lambda c: _arena_wins(c) >= 25),
    Achievement("treasure_hunter", "Treasure Hunter", "Collect 10 pieces of gear.",
                lambda c: len(c.inventory) >= 10),
    Achievement("legendary_find", "Legendary Find", "Find a Legendary item.",
                lambda c: any(g.rarity == "Legendary" for g in c.inventory)),
    Achievement("fully_equipped", "Fully Equipped", "Equip all three gear slots.",
                lambda c: len(c.equipped_gear()) >= 3),
    Achievement("creature_of_habit", "Creature of Habit",
                "Keep a 4-week streak on any activity.",
                lambda c: _max_streak(c) >= 4),
    Achievement("well_rounded", "Well-Rounded",
                "Complete the weekly well-rounded challenge.",
                lambda c: len(c.challenges_claimed) >= 1),
    Achievement("boss_slayer", "Boss Slayer", "Defeat an Arena boss.",
                lambda c: c.counters.get("bosses", 0) >= 1),
    Achievement("warlord", "Warlord", "Defeat 10 Arena bosses.",
                lambda c: c.counters.get("bosses", 0) >= 10),
    Achievement("vault_raider", "Vault Raider", "Open 15 Treasure Vault chests.",
                lambda c: c.counters.get("vaults", 0) >= 15),
)
