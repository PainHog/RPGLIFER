"""The Arena — a lightweight auto-battle mini-game (the first Adventure).

A run pits your **derived combat stats** (Vitality, Power, Focus — see
:mod:`rpglifer.derived`) against a foe scaled to your character. Rounds resolve
automatically; the UI plays them out. Winning pays **Hero points** — it never
touches your real-life stats. Temporary combat **bonuses** bought in the Shop
add to your Power for a run.

Everything here is deterministic given a seed, so battles are unit-testable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import derived, gear
from .stats import STAT_KEYS

FOES = [
    "Cave Slime", "Goblin Scout", "Dire Wolf", "Bandit", "Skeleton",
    "Giant Spider", "Ogre", "Wraith", "Stone Golem", "Basilisk", "Young Dragon",
]

MAX_ROUNDS = 40


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


def _avg_level(character) -> float:
    return sum(character.effective_level(k) for k in STAT_KEYS) / len(STAT_KEYS)


def simulate(character, combat_bonus: float = 0.0, seed: int | None = None) -> Battle:
    """Resolve one Arena battle and return the full round-by-round record."""
    rng = random.Random(seed)
    d = derived.compute(character)
    you_max = max(10, d["HP"])
    you_pwr = max(2, d["PWR"]) * (1.0 + combat_bonus)
    crit_chance = min(0.4, d["FOC"] / 400.0)

    level = max(1, round(_avg_level(character)))
    diff = rng.uniform(0.85, 1.15)
    foe_max = max(8, int(you_max * rng.uniform(0.7, 1.0) * diff))
    foe_pwr = max(1, int(you_pwr * rng.uniform(0.55, 0.85) * diff))

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
    reward = (5 + level) if won else 2
    loot = None
    if won and rng.random() < 0.45:  # victors sometimes find gear
        loot = gear.roll_gear(level, rng)
    return Battle(rng.choice(FOES), level, you_max, foe_max, rounds, won, reward,
                  loot=loot)
