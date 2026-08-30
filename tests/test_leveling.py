from rpglifer import leveling


def test_first_level_costs_base_xp():
    assert leveling.xp_to_advance(1) == leveling.BASE_XP


def test_costs_grow_each_level():
    costs = [leveling.xp_to_advance(lvl) for lvl in range(1, 10)]
    assert costs == sorted(costs)
    assert costs[1] > costs[0]


def test_zero_xp_is_level_one():
    p = leveling.level_for_xp(0)
    assert p.level == 1
    assert p.xp_into_level == 0
    assert p.fraction == 0.0


def test_just_below_threshold_stays_level_one():
    p = leveling.level_for_xp(leveling.BASE_XP - 1)
    assert p.level == 1
    assert p.xp_into_level == leveling.BASE_XP - 1


def test_exactly_threshold_reaches_level_two():
    p = leveling.level_for_xp(leveling.BASE_XP)
    assert p.level == 2
    assert p.xp_into_level == 0


def test_fraction_is_bounded():
    for xp in (0, 50, 100, 250, 1000, 100000):
        assert 0.0 <= leveling.level_for_xp(xp).fraction <= 1.0


def test_level_is_monotonic_in_xp():
    last = 0
    for xp in range(0, 20000, 137):
        lvl = leveling.level_of(xp)
        assert lvl >= last
        last = lvl


def test_negative_xp_clamps_to_level_one():
    assert leveling.level_of(-500) == 1


def test_advance_rejects_bad_level():
    import pytest

    with pytest.raises(ValueError):
        leveling.xp_to_advance(0)
