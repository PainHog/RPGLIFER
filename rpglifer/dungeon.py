"""Dungeon Dive — a push-your-luck Adventure mini-game.

Descend floor by floor. Each floor you clear adds Hero points (and, deeper down,
maybe gear) to a **pending** pile — but every descent risks a trap that ends the
run and forfeits everything not yet **banked**. Cash out to keep your haul, or
push your luck for more. Your derived **Luck** stat softens the trap odds and
sweetens the drops.

Pure and seedable: a :class:`DungeonRun` is driven entirely by a seeded RNG plus
the character's Luck and level, so the whole game is deterministic under test.
The character/UI spend one shared Adventure-energy charge to begin a run.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import derived, gear
from .stats import STAT_KEYS

# Trap odds grow with depth and are softened (never erased) by Luck.
BASE_TRAP = 0.10
TRAP_PER_FLOOR = 0.06
MIN_TRAP = 0.03
MAX_TRAP = 0.80
# Hero points found on a cleared floor, escalating with depth.
FLOOR_BASE = 6
FLOOR_STEP = 4
# Gear can drop from this floor onward.
GEAR_FROM_FLOOR = 3
GEAR_CHANCE = 0.30


def _avg_level(character) -> int:
    return max(1, round(sum(character.effective_level(k) for k in STAT_KEYS)
                        / len(STAT_KEYS)))


def _luck_factor(character) -> float:
    """0.0–~0.45: how strongly Luck helps, from the derived LCK stat."""
    return min(0.45, derived.compute(character)["LCK"] / 300.0)


def trap_chance(floor: int, luck: float) -> float:
    """Probability the descent to ``floor`` (1-based) springs a trap."""
    raw = BASE_TRAP + TRAP_PER_FLOOR * (floor - 1)
    raw *= max(0.4, 1.0 - luck)  # Luck softens, but a floor of risk remains.
    return max(MIN_TRAP, min(MAX_TRAP, raw))


def floor_reward(floor: int) -> int:
    """Hero points for clearing ``floor``."""
    return FLOOR_BASE + (floor - 1) * FLOOR_STEP


@dataclass
class DiveStep:
    floor: int
    trapped: bool
    reward: int  # Hero points found this floor (0 when trapped)
    gear: object = None  # a gear.Gear, or None


@dataclass
class DungeonRun:
    """One push-your-luck descent. Call :meth:`descend` / :meth:`cash_out`."""

    luck: float
    level: int
    rng: random.Random = field(default_factory=random.Random)
    floor: int = 0
    pending_hero: int = 0
    pending_gear: list = field(default_factory=list)
    alive: bool = True
    cashed: bool = False
    steps: list = field(default_factory=list)

    @classmethod
    def for_character(cls, character, seed: int | None = None) -> "DungeonRun":
        return cls(luck=_luck_factor(character), level=_avg_level(character),
                   rng=random.Random(seed))

    @property
    def over(self) -> bool:
        return self.cashed or not self.alive

    def next_trap_chance(self) -> float:
        """Trap odds for the *next* descent (for showing the player the risk)."""
        return trap_chance(self.floor + 1, self.luck)

    def descend(self) -> DiveStep:
        """Go one floor deeper. May spring a trap and end the run."""
        if self.over:
            raise RuntimeError("run is already over")
        self.floor += 1
        if self.rng.random() < trap_chance(self.floor, self.luck):
            self.alive = False
            self.pending_hero = 0
            self.pending_gear = []
            step = DiveStep(self.floor, True, 0, None)
            self.steps.append(step)
            return step
        reward = floor_reward(self.floor)
        loot = None
        if self.floor >= GEAR_FROM_FLOOR and \
                self.rng.random() < GEAR_CHANCE + self.luck:
            rarity = None
            if self.floor >= 7:
                rarity = self.rng.choice(["Rare", "Epic", "Epic", "Legendary"])
            elif self.floor >= 5:
                rarity = self.rng.choice(["Rare", "Rare", "Epic"])
            loot = gear.roll_gear(self.level + self.floor, self.rng, rarity=rarity)
            self.pending_gear.append(loot)
        self.pending_hero += reward
        step = DiveStep(self.floor, False, reward, loot)
        self.steps.append(step)
        return step

    def cash_out(self) -> tuple[int, list]:
        """Bank the pending haul and end the run. Returns (hero, gear list)."""
        if not self.alive:
            return 0, []
        self.cashed = True
        return self.pending_hero, list(self.pending_gear)
