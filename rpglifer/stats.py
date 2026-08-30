"""The core stats (attributes) a character develops — the "who you are" layer.

Eight stats, each meant to define a real dimension of a person. They are trained
*only* by real-life activities; the combat/shop numbers in :mod:`rpglifer.derived`
are computed from these and are never trained directly.

The short ``key`` is the stable id used in save files and the activity catalog —
never rename a key. Display ``name`` is the plain-life label the player sees.
The original six keep their D&D keys (so the 600+ catalog stays valid) but wear
plain-life names; Discipline and Creativity are the two additions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stat:
    key: str  # short, stable id (never rename) — used in saves and the catalog
    name: str  # plain-life display name
    blurb: str  # one-line description for tooltips
    color: str  # accent (used sparingly — e.g. radar hover, not the bars)


STATS: tuple[Stat, ...] = (
    Stat("STR", "Strength", "Physical power — lifting, hauling, raw force.", "#e0574f"),
    Stat("DEX", "Agility", "Coordination, precision, balance, hand skill.", "#3fae6b"),
    Stat("CON", "Endurance", "Stamina, health, and staying power.", "#d98a34"),
    Stat("INT", "Intellect", "Knowledge, analysis, and problem solving.", "#4a90d9"),
    Stat("WIS", "Wisdom", "Reflection, awareness, and good judgment.", "#8a6fd0"),
    Stat("CHA", "Charisma", "Social skill, presence, and connection.", "#d95a9e"),
    Stat("DIS", "Discipline", "Consistency, focus, and follow-through.", "#c9a24b"),
    Stat("CRE", "Creativity", "Making, expression, art, and imagination.", "#54c0c0"),
)

STAT_KEYS: tuple[str, ...] = tuple(s.key for s in STATS)
STAT_BY_KEY: dict[str, Stat] = {s.key: s for s in STATS}


def stat(key: str) -> Stat:
    """Return the :class:`Stat` for ``key`` (raises ``KeyError`` if unknown)."""
    return STAT_BY_KEY[key]
