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

# stat key -> ascending ladder of (level, title). Keep each ladder sorted.
TITLES: dict[str, tuple[tuple[int, str], ...]] = {
    "STR": ((3, "Gym Rookie"), (5, "Weight Hauler"), (10, "Iron-Willed"),
            (15, "Powerhouse"), (20, "Titan"), (30, "Colossus")),
    "DEX": ((3, "Fumbler No More"), (5, "Nimble"), (10, "Quick-Handed"),
            (15, "Acrobat"), (20, "Blur"), (30, "Untouchable")),
    "CON": ((3, "Steady"), (5, "Enduring"), (10, "Tireless"),
            (15, "Ironclad"), (20, "Unbreakable"), (30, "Immortal")),
    "INT": ((3, "Curious"), (5, "Bookworm"), (10, "Scholar"),
            (15, "Sage"), (20, "Genius"), (30, "Polymath")),
    "WIS": ((3, "Reflective"), (5, "Level-Headed"), (10, "Insightful"),
            (15, "Enlightened"), (20, "Guru"), (30, "Oracle")),
    "CHA": ((3, "Friendly"), (5, "Well-Liked"), (10, "Charmer"),
            (15, "Silver-Tongued"), (20, "Magnetic"), (30, "Legendary Presence")),
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
