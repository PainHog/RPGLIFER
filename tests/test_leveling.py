import pytest

from rpglifer import leveling


def test_zero_xp_is_level_zero():
    p = leveling.level_for_xp(0)
    assert p.level == 0
    assert p.fraction == 0.0


def test_curve_is_front_loaded_early():
    # A single ~30-minute session (60 XP) should already grant several levels.
    assert leveling.level_of(60) >= 4


def test_level_caps_at_100():
    assert leveling.level_of(leveling.XP_TO_MAX) == 100
    assert leveling.level_of(leveling.XP_TO_MAX * 5) == 100


def test_maxed_bar_is_full():
    p = leveling.level_for_xp(leveling.XP_TO_MAX)
    assert p.level == 100
    assert p.fraction == 1.0


def test_level_is_monotonic_in_xp():
    last = -1
    for xp in range(0, leveling.XP_TO_MAX, 250):
        lvl = leveling.level_of(xp)
        assert lvl >= last
        last = lvl


def test_costs_grow_with_level():
    # Advancing costs more XP the higher you are (long tail).
    assert leveling.xp_to_advance(80) > leveling.xp_to_advance(20) > leveling.xp_to_advance(2)


def test_fraction_is_bounded():
    for xp in (0, 50, 500, 5000, 60000, 500000):
        assert 0.0 <= leveling.level_for_xp(xp).fraction <= 1.0


def test_negative_xp_clamps_to_zero():
    assert leveling.level_of(-500) == 0


def test_advance_at_cap_is_zero():
    assert leveling.xp_to_advance(100) == 0


def test_advance_rejects_negative_level():
    with pytest.raises(ValueError):
        leveling.xp_to_advance(-1)
