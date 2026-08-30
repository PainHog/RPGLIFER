"""Gear — equippable loot that buffs your *derived* combat stats, never your
real-life stats.

Items drop from Arena victories (see :mod:`rpglifer.adventure`). Each piece fills
one of three slots and adds flat bonuses to derived stats (Power, Vitality,
Focus, …). Rarer drops hit harder. Generation is seedable, so it's testable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

SLOTS = ("Weapon", "Armor", "Trinket")

# (name, power multiplier, drop weight)
RARITIES = (
    ("Common", 1.0, 0.60),
    ("Rare", 1.6, 0.28),
    ("Epic", 2.4, 0.10),
    ("Legendary", 3.6, 0.02),
)
RARITY_MULT = {name: mult for name, mult, _ in RARITIES}

_NAMES = {
    "Weapon": ["Dagger", "Short Sword", "Battle Axe", "Warhammer", "Runeblade",
               "Glaive", "Halberd"],
    "Armor": ["Leather Vest", "Chainmail", "Breastplate", "Plate Armor", "Aegis",
              "Bulwark"],
    "Trinket": ["Copper Ring", "Luck Charm", "Focus Amulet", "Sigil", "Talisman",
                "Heart-Stone"],
}


@dataclass
class Gear:
    id: str
    name: str
    slot: str
    rarity: str
    bonuses: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        parts = ", ".join(f"+{v} {k}" for k, v in self.bonuses.items())
        return f"{self.rarity} {self.name} — {parts}"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "slot": self.slot,
                "rarity": self.rarity, "bonuses": dict(self.bonuses)}

    @classmethod
    def from_dict(cls, d: dict) -> "Gear":
        return cls(id=str(d.get("id", "")), name=str(d.get("name", "Trinket")),
                   slot=str(d.get("slot", "Trinket")),
                   rarity=str(d.get("rarity", "Common")),
                   bonuses={str(k): int(v) for k, v in dict(d.get("bonuses", {})).items()})


def _pick_rarity(rng: random.Random) -> str:
    r = rng.random()
    cumulative = 0.0
    for name, _mult, weight in RARITIES:
        cumulative += weight
        if r <= cumulative:
            return name
    return RARITIES[0][0]


def roll_gear(level: int, rng: random.Random | None = None,
              rarity: str | None = None) -> Gear:
    """Generate a random piece of gear scaled to ``level``."""
    rng = rng or random.Random()
    rarity = rarity or _pick_rarity(rng)
    mult = RARITY_MULT.get(rarity, 1.0)
    slot = rng.choice(SLOTS)
    base = 2 + level * 0.5
    bonuses: dict[str, int] = {}

    def amt(scale):
        return max(1, int(round(base * scale * mult * rng.uniform(0.85, 1.15))))

    if slot == "Weapon":
        bonuses["PWR"] = amt(1.2)
        if rng.random() < 0.5:
            bonuses["FOC"] = amt(0.5)
    elif slot == "Armor":
        bonuses["HP"] = amt(4.0)
        if rng.random() < 0.4:
            bonuses["PWR"] = amt(0.4)
    else:  # Trinket
        stat = rng.choice(["FOC", "LCK", "INS", "INF"])
        bonuses[stat] = amt(1.0)
        if rng.random() < 0.35:
            bonuses["LCK"] = amt(0.6)

    gid = f"{slot[:2].lower()}-{rng.getrandbits(32):08x}"
    name = rng.choice(_NAMES[slot])
    return Gear(id=gid, name=name, slot=slot, rarity=rarity, bonuses=bonuses)
