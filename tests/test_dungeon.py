import random

from rpglifer import dungeon
from rpglifer.character import Character


def test_trap_chance_grows_with_depth_and_is_bounded():
    prev = -1.0
    for floor in range(1, 20):
        p = dungeon.trap_chance(floor, luck=0.0)
        assert dungeon.MIN_TRAP <= p <= dungeon.MAX_TRAP
        assert p >= prev  # non-decreasing with depth
        prev = p


def test_luck_lowers_trap_chance():
    lucky = dungeon.trap_chance(5, luck=0.4)
    unlucky = dungeon.trap_chance(5, luck=0.0)
    assert lucky < unlucky


def test_floor_reward_increases():
    assert dungeon.floor_reward(2) > dungeon.floor_reward(1)
    assert dungeon.floor_reward(1) == dungeon.FLOOR_BASE


def test_run_is_deterministic_for_a_seed():
    c = Character()
    r1 = dungeon.DungeonRun.for_character(c, seed=99)
    r2 = dungeon.DungeonRun.for_character(c, seed=99)
    out1, out2 = [], []
    while not r1.over:
        s = r1.descend()
        out1.append((s.floor, s.trapped, s.reward, s.gear.rarity if s.gear else None))
        if not s.trapped and s.floor >= 12:
            break
    while not r2.over:
        s = r2.descend()
        out2.append((s.floor, s.trapped, s.reward, s.gear.rarity if s.gear else None))
        if not s.trapped and s.floor >= 12:
            break
    assert out1 == out2


def test_trap_forfeits_pending_and_ends_run():
    # Force a trap on the very first descend with a stub RNG.
    run = dungeon.DungeonRun(luck=0.0, level=10, rng=random.Random())
    run.rng.random = lambda: 0.0  # always below the trap chance
    step = run.descend()
    assert step.trapped
    assert run.over and not run.alive
    assert run.pending_hero == 0 and run.pending_gear == []
    assert run.cash_out() == (0, [])


def test_clearing_floors_accumulates_then_cash_out_banks():
    run = dungeon.DungeonRun(luck=0.0, level=10, rng=random.Random())
    run.rng.random = lambda: 0.99  # never trap, never drop gear
    run.descend()
    run.descend()
    run.descend()
    expected = sum(dungeon.floor_reward(f) for f in (1, 2, 3))
    assert run.pending_hero == expected
    hero, loot = run.cash_out()
    assert hero == expected
    assert loot == []
    assert run.over and run.cashed


def test_cannot_descend_after_run_is_over():
    run = dungeon.DungeonRun(luck=0.0, level=5, rng=random.Random())
    run.cash_out()
    try:
        run.descend()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_dungeon_counters_unlock_achievements():
    from rpglifer import achievements
    ids = {a.id for a in achievements.ACHIEVEMENTS}
    assert {"delver", "dungeoneer"} <= ids
    c = Character()
    c.counters["dungeon_best"] = 8
    c.counters["dungeon_runs"] = 20
    unlocked = {a.id for a in c.check_achievements()}
    assert "delver" in unlocked
    assert "dungeoneer" in unlocked


def test_next_trap_chance_matches_upcoming_floor():
    run = dungeon.DungeonRun(luck=0.1, level=5, rng=random.Random())
    assert run.next_trap_chance() == dungeon.trap_chance(1, 0.1)
    run.rng.random = lambda: 0.99
    run.descend()
    assert run.next_trap_chance() == dungeon.trap_chance(2, 0.1)
