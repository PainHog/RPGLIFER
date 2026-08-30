"""Milestone titles — the metered reward for chasing a single stat.

Every stat has a ladder of titles unlocked at set levels. Reaching a milestone
awards that stat's title, giving each attribute a reason to be pushed on its own
(a reader earns *Scholar*; a lifter earns *Iron-Willed*). The character's title
for a stat is simply the highest milestone reached.

Titles are data-driven — edit the ladders below and the model and UI follow.
The first rung sits at level 3 so a new player tastes a reward within the first
week or two; later rungs are spaced out to reward the long haul.
"""

from __future__ import annotations

# stat key -> ascending ladder of (level, title) on the 0–100 scale. The first
# rung (10) lands in the first week; the last (100) is mastery. Keep sorted.
TITLES: dict[str, tuple[tuple[int, str], ...]] = {
    "STR": ((10, "Gym Rookie"), (25, "Weight Hauler"), (40, "Iron-Willed"),
            (55, "Powerhouse"), (75, "Titan"), (100, "Colossus")),
    "DEX": ((10, "Fumbler No More"), (25, "Nimble"), (40, "Quick-Handed"),
            (55, "Acrobat"), (75, "Blur"), (100, "Untouchable")),
    "CON": ((10, "Steady"), (25, "Enduring"), (40, "Tireless"),
            (55, "Ironclad"), (75, "Unbreakable"), (100, "Immortal")),
    "INT": ((10, "Curious"), (25, "Bookworm"), (40, "Scholar"),
            (55, "Sage"), (75, "Genius"), (100, "Polymath")),
    "WIS": ((10, "Reflective"), (25, "Level-Headed"), (40, "Insightful"),
            (55, "Enlightened"), (75, "Guru"), (100, "Oracle")),
    "CHA": ((10, "Friendly"), (25, "Well-Liked"), (40, "Charmer"),
            (55, "Silver-Tongued"), (75, "Magnetic"), (100, "Legendary Presence")),
    "DIS": ((10, "Consistent"), (25, "Focused"), (40, "Iron Habit"),
            (55, "Unwavering"), (75, "Unstoppable"), (100, "Relentless")),
    "CRE": ((10, "Doodler"), (25, "Maker"), (40, "Artisan"),
            (55, "Visionary"), (75, "Virtuoso"), (100, "Muse")),
}


def title_for(stat_key: str, level: int) -> str | None:
    """The highest title earned in ``stat_key`` at ``level`` (``None`` if none)."""
    earned: str | None = None
    for milestone, name in TITLES.get(stat_key, ()):  # ascending
        if level >= milestone:
            earned = name
        else:
            break
    return earned


def next_title(stat_key: str, level: int) -> tuple[int, str] | None:
    """The next (level, title) milestone above ``level``, or ``None`` if maxed."""
    for milestone, name in TITLES.get(stat_key, ()):
        if level < milestone:
            return milestone, name
    return None
