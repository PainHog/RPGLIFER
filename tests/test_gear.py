import random

from rpglifer import adventure, derived, gear
from rpglifer.character import STAR_XP, Character

DERIVED_KEYS = {"HP", "PWR", "FOC", "INS", "INF", "LCK"}


def test_roll_gear_shape():
    g = gear.roll_gear(20, random.Random(1))
    assert g.slot in gear.SLOTS
    assert g.rarity in gear.RARITY_MULT
    assert g.bonuses and all(k in DERIVED_KEYS for k in g.bonuses)


def test_roll_gear_is_deterministic():
    a = gear.roll_gear(15, random.Random(7))
    b = gear.roll_gear(15, random.Random(7))
    assert a.to_dict() == b.to_dict()


def test_gear_boosts_adventure_loadout_not_life_stats():
    c = Character()
    c.stat_xp["STR"] = 15000
    innate = derived.compute(c)["PWR"]          # life-only (character sheet)
    loadout = derived.with_gear(c)["PWR"]        # adventure games
    assert loadout == innate                     # nothing equipped yet
    c.add_gear(gear.Gear("w1", "Sword", "Weapon", "Epic", {"PWR": 10}))
    c.equip("w1")
    # Gear lifts the adventure loadout only; the life-derived sheet is untouched.
    assert derived.with_gear(c)["PWR"] == innate + 10
    assert derived.compute(c)["PWR"] == innate


def test_equipping_same_slot_replaces():
    c = Character()
    c.add_gear(gear.Gear("a", "A", "Weapon", "Common", {"PWR": 3}))
    c.add_gear(gear.Gear("b", "B", "Weapon", "Rare", {"PWR": 5}))
    c.equip("a")
    c.equip("b")
    assert c.equipped["Weapon"] == "b"
    assert c.gear_bonuses()["PWR"] == 5  # only one weapon contributes


def test_unequip_removes_bonus():
    c = Character()
    c.add_gear(gear.Gear("t", "Charm", "Trinket", "Rare", {"LCK": 4}))
    c.equip("t")
    assert c.gear_bonuses().get("LCK") == 4
    c.unequip("Trinket")
    assert "LCK" not in c.gear_bonuses()


def test_gear_survives_roundtrip():
    c = Character()
    g = gear.roll_gear(10, random.Random(2))
    c.add_gear(g)
    c.equip(g.id)
    c2 = Character.from_dict(c.to_dict())
    assert len(c2.inventory) == 1
    assert c2.equipped == c.equipped
    assert c2.gear_bonuses() == c.gear_bonuses()


def test_arena_drops_loot_sometimes():
    c = Character()
    for k in ("STR", "DEX", "CON"):
        c.stat_xp[k] = STAR_XP
    drops = sum(adventure.simulate(c, seed=s).loot is not None for s in range(80))
    assert drops > 0
