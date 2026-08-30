"""Derived stats — the "combat & shop" layer.

These are never trained directly. They are computed from the eight core stats
(:mod:`rpglifer.stats`), so real-life growth flows into your game power. Later,
gear and adventure bonuses will modify *these* numbers — keeping the core stats
a pure reflection of what you actually do.

Also here: :func:`character_class`, a fun title that evolves with your two
strongest stats (a Clever Warrior today, a Wise Artist next month).
"""

from __future__ import annotations

from dataclasses import dataclass

from .stats import STAT_KEYS


@dataclass(frozen=True)
class DerivedStat:
    key: str
    name: str
    blurb: str


DERIVED: tuple[DerivedStat, ...] = (
    DerivedStat("HP", "Vitality", "Max health — how much you can endure in a fight."),
    DerivedStat("PWR", "Power", "Raw attack strength."),
    DerivedStat("FOC", "Focus", "Accuracy and critical-hit chance."),
    DerivedStat("INS", "Insight", "Mental and magical force."),
    DerivedStat("INF", "Influence", "Barter power — better prices in the Shop."),
    DerivedStat("LCK", "Luck", "Rare finds and fortune on adventures."),
)


def compute(character) -> dict[str, int]:
    """Your **innate** adventure power, from your core stats *only*.

    Uses *effective* levels (stars × 100 + level), so prestige keeps this
    climbing past mastery. This is gear-free on purpose: it reflects the life
    you've actually lived. Gear is a separate loadout applied only inside the
    Adventure games — see :func:`with_gear`.
    """
    L = {k: character.effective_level(k) for k in STAT_KEYS}
    return {
        "HP": 20 + 6 * L["CON"] + 3 * L["STR"] + 2 * L["DIS"],
        "PWR": 5 + 2 * (L["STR"] + L["DEX"]),
        "FOC": 5 + 2 * L["DEX"] + L["INT"] + L["DIS"],
        "INS": 5 + 2 * L["INT"] + 2 * L["WIS"],
        "INF": 5 + 2 * L["CHA"] + L["WIS"],
        "LCK": 3 + L["CRE"] + L["CHA"],
    }


def with_gear(character) -> dict[str, int]:
    """Adventure loadout: innate power (:func:`compute`) plus equipped gear.

    Used **only** by the Arena / Vault / Dungeon engines. Equipped gear adds
    flat bonuses here and *nowhere else* — never to your life stats and never to
    the character sheet, so the sheet stays a pure mirror of what you do.
    """
    stats = compute(character)
    gear = getattr(character, "gear_bonuses", lambda: {})()
    for k, v in gear.items():
        if k in stats:
            stats[k] += int(v)
    return stats


# Flavor for the evolving class name.
_ADJ = {"STR": "Mighty", "DEX": "Nimble", "CON": "Stalwart", "INT": "Clever",
        "WIS": "Wise", "CHA": "Charming", "DIS": "Steadfast", "CRE": "Inventive"}
_NOUN = {"STR": "Warrior", "DEX": "Rogue", "CON": "Juggernaut", "INT": "Scholar",
         "WIS": "Sage", "CHA": "Diplomat", "DIS": "Ascetic", "CRE": "Artist"}


def character_class(character) -> str:
    """A class name from the two strongest stats, e.g. 'Clever Warrior'.

    Before any meaningful growth (everything tied at the bottom), you're a
    'Novice'. As stats diverge, the top stat picks the archetype noun and the
    runner-up colors it with an adjective.
    """
    ranked = sorted(
        STAT_KEYS,
        key=lambda k: (character.stat_xp.get(k, 0.0), k),
        reverse=True,
    )
    top, second = ranked[0], ranked[1]
    if character.stat_xp.get(top, 0.0) <= 0:
        return "Novice Adventurer"
    return f"{_ADJ[second]} {_NOUN[top]}"
