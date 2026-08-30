"""Ventures — small Adventure mini-games beyond the Arena.

The **Treasure Vault**: three chests are rolled; you pick one. Rewards are Hero
points and sometimes gear, and your derived **Luck** stat tilts the odds toward
better tiers and drops. Pure and seedable for testing; the character/UI spend a
shared Adventure-energy charge to open a chest.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from . import derived, gear
from .stats import STAT_KEYS


@dataclass
class Chest:
    tier: str  # "common" / "rare" / "jackpot"
    hero: int
    gear: object = None  # a gear.Gear, or None


def _avg_level(character) -> float:
    return sum(character.effective_level(k) for k in STAT_KEYS) / len(STAT_KEYS)


def roll_vault(character, seed: int | None = None) -> list[Chest]:
    """Roll three hidden chests. Higher Luck skews tiers and drop rates up."""
    rng = random.Random(seed)
    level = max(1, round(_avg_level(character)))
    lck = derived.with_gear(character)["LCK"]
    luck = min(0.45, lck / 300.0)
    base = 8 + level

    chests: list[Chest] = []
    for _ in range(3):
        r = rng.random()
        if r < 0.10 + luck * 0.5:
            tier, mult = "jackpot", 4.0
        elif r < 0.45 + luck:
            tier, mult = "rare", 2.0
        else:
            tier, mult = "common", 1.0
        hero = int(base * mult)
        loot = None
        if rng.random() < 0.25 + luck:
            rarity = None
            if tier == "jackpot":
                rarity = rng.choice(["Epic", "Legendary"])
            elif tier == "rare":
                rarity = rng.choice(["Rare", "Rare", "Epic"])
            loot = gear.roll_gear(level, rng, rarity=rarity)
        chests.append(Chest(tier, hero, loot))
    return chests
