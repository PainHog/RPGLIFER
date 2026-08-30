"""The core stats (attributes) a character develops.

Stats are data-driven: add, rename, or recolor them here and the rest of the
app follows automatically. Each activity distributes the XP it earns across one
or more of these stats.

The six below are the classic tabletop attributes — a deliberate starting point
that we expect to tune and expand as the activity catalog grows.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stat:
    key: str  # short, stable id used in save files, e.g. "STR" — never rename
    name: str  # display name, e.g. "Strength"
    blurb: str  # one-line description shown in the UI
    emoji: str  # a little flavor for cards and labels
    color: str  # hex accent color for bars and headings


STATS: tuple[Stat, ...] = (
    Stat("STR", "Strength", "Physical power — lifting, hauling, raw force.", "💪", "#e0574f"),
    Stat("DEX", "Dexterity", "Agility, coordination, and fine motor skill.", "🤸", "#3fae6b"),
    Stat("CON", "Constitution", "Endurance, health, and daily discipline.", "🛡️", "#d98a34"),
    Stat("INT", "Intelligence", "Knowledge, study, and problem solving.", "📚", "#4a90d9"),
    Stat("WIS", "Wisdom", "Reflection, mindfulness, and good judgment.", "🧘", "#8a6fd0"),
    Stat("CHA", "Charisma", "Social skill, connection, and presence.", "🎭", "#d95a9e"),
)

# Ordered tuple of keys and a lookup map — both derived from STATS so there is a
# single source of truth.
STAT_KEYS: tuple[str, ...] = tuple(s.key for s in STATS)
STAT_BY_KEY: dict[str, Stat] = {s.key: s for s in STATS}


def stat(key: str) -> Stat:
    """Return the :class:`Stat` for ``key`` (raises ``KeyError`` if unknown)."""
    return STAT_BY_KEY[key]
