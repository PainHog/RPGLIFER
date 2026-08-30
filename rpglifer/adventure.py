"""The Arena — a lightweight auto-battle mini-game (the first Adventure).

A run pits your **derived combat stats** (Vitality, Power, Focus — see
:mod:`rpglifer.derived`) against a foe scaled to your character. Foes come in
archetypes (tanky slimes, glass-cannon wolves, balanced bandits…), and now and
then a **boss** appears — much tougher, but worth triple Hero points and
near-guaranteed, higher-rarity loot. Winning never touches your real-life stats.

Everything here is deterministic given a seed, so battles are unit-testable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import derived, gear
from .stats import STAT_KEYS

# (name, hp multiplier, power multiplier)
ARCHETYPES = (
    ("Cave Slime", 1.3, 0.60),
    ("Goblin Scout", 0.80, 0.95),
    ("Dire Wolf", 0.70, 1.15),
    ("Bandit", 1.0, 0.90),
    ("Skeleton", 0.90, 1.0),
    ("Giant Spider", 0.80, 1.05),
    ("Ogre", 1.45, 1.0),
    ("Wraith", 0.70, 1.30),
    ("Stone Golem", 1.85, 0.70),
    ("Basilisk", 1.0, 1.20),
)
BOSSES = ("Ancient Wyrm", "The Warden", "Shadow Colossus", "Doomhorn Beast",
          "Frost Titan", "Voidmaw")

BOSS_CHANCE = 0.13
MAX_ROUNDS = 50


@dataclass
class Round:
    attacker: str  # "you" or "foe"
    damage: int
    crit: bool
    you_hp: int
    foe_hp: int


@dataclass
class Battle:
    foe_name: str
    foe_level: int
    you_max_hp: int
    foe_max_hp: int
    rounds: list = field(default_factory=list)
    won: bool = False
    reward: int = 0
    loot: object = None  # a gear.Gear dropped on victory, or None
    is_boss: bool = False


def _avg_level(character) -> float:
    return sum(character.effective_level(k) for k in STAT_KEYS) / len(STAT_KEYS)


def simulate(character, combat_bonus: float = 0.0, seed: int | None = None) -> Battle:
    """Resolve one Arena battle and return the full round-by-round record."""
    rng = random.Random(seed)
    d = derived.with_gear(character)
    you_max = max(10, d["HP"])
    you_pwr = max(2, d["PWR"]) * (1.0 + combat_bonus)
    crit_chance = min(0.4, d["FOC"] / 400.0)

    level = max(1, round(_avg_level(character)))
    is_boss = rng.random() < BOSS_CHANCE
    if is_boss:
        name = rng.choice(BOSSES)
        hp_mult, pwr_mult = 2.3, 1.35
    else:
        name, hp_mult, pwr_mult = rng.choice(ARCHETYPES)

    diff = rng.uniform(0.9, 1.1)
    foe_max = max(8, int(you_max * rng.uniform(0.7, 1.0) * hp_mult * diff))
    foe_pwr = max(1, int(you_pwr * rng.uniform(0.55, 0.85) * pwr_mult * diff))

    you_hp, foe_hp = you_max, foe_max
    rounds: list[Round] = []
    your_turn = True
    while you_hp > 0 and foe_hp > 0 and len(rounds) < MAX_ROUNDS:
        if your_turn:
            crit = rng.random() < crit_chance
            dmg = max(1, int(you_pwr * rng.uniform(0.8, 1.2) * (1.8 if crit else 1.0)))
            foe_hp = max(0, foe_hp - dmg)
            rounds.append(Round("you", dmg, crit, you_hp, foe_hp))
        else:
            crit = rng.random() < 0.10
            dmg = max(1, int(foe_pwr * rng.uniform(0.8, 1.2) * (1.6 if crit else 1.0)))
            you_hp = max(0, you_hp - dmg)
            rounds.append(Round("foe", dmg, crit, you_hp, foe_hp))
        your_turn = not your_turn

    won = foe_hp <= 0 and you_hp > 0
    reward = (5 + level) * (3 if is_boss else 1) if won else 2

    loot = None
    if won:
        if is_boss and rng.random() < 0.90:
            rarity = rng.choice(["Rare", "Rare", "Epic", "Legendary"])
            loot = gear.roll_gear(level + 3, rng, rarity=rarity)
        elif not is_boss and rng.random() < 0.45:
            loot = gear.roll_gear(level, rng)

    return Battle(name, level, you_max, foe_max, rounds, won, reward, loot=loot,
                  is_boss=is_boss)
