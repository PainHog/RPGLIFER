import pytest

from rpglifer.activities import activity_by_name
from rpglifer.character import Character
from rpglifer.stats import STAT_KEYS


def test_new_character_starts_at_zero_xp():
    c = Character()
    assert c.total_xp() == 0
    for key in STAT_KEYS:
        assert c.stat_xp[key] == 0.0
        assert c.level(key) == 1


def test_overall_level_is_sum_of_stat_levels():
    c = Character()
    assert c.overall_level() == len(STAT_KEYS)  # every stat at level 1


def test_logging_awards_xp_by_weight():
    c = Character()
    reading = activity_by_name("Reading")  # INT 0.8 / WIS 0.2
    result = c.log_activity(reading, minutes=30)
    base = 30 * reading.xp_per_minute
    assert c.stat_xp["INT"] == pytest.approx(base * 0.8)
    assert c.stat_xp["WIS"] == pytest.approx(base * 0.2)
    assert result.gains["INT"] == pytest.approx(base * 0.8)


def test_logging_appends_to_log():
    c = Character()
    c.log_activity(activity_by_name("Dishes"), minutes=15)
    assert len(c.log) == 1
    assert c.log[0].activity == "Dishes"
    assert c.log[0].minutes == 15


def test_level_ups_are_reported():
    c = Character()
    # A big study session should push INT past its first level threshold.
    result = c.log_activity(activity_by_name("Studying"), minutes=60)
    assert any(lu.stat == "INT" for lu in result.level_ups)
    int_up = next(lu for lu in result.level_ups if lu.stat == "INT")
    assert int_up.to_level > int_up.from_level


def test_negative_minutes_rejected():
    c = Character()
    with pytest.raises(ValueError):
        c.log_activity(activity_by_name("Reading"), minutes=-5)


def test_recent_returns_newest_first():
    c = Character()
    c.log_activity(activity_by_name("Reading"), minutes=10)
    c.log_activity(activity_by_name("Dishes"), minutes=10)
    recent = c.recent(5)
    assert recent[0].activity == "Dishes"
    assert recent[1].activity == "Reading"


def test_roundtrip_preserves_state():
    c = Character(name="Hero")
    c.log_activity(activity_by_name("Coding / programming"), minutes=45)
    c.log_activity(activity_by_name("Running"), minutes=20)
    restored = Character.from_dict(c.to_dict())
    assert restored.name == "Hero"
    assert restored.stat_xp == c.stat_xp
    assert len(restored.log) == 2
    assert restored.overall_level() == c.overall_level()


def test_from_dict_ignores_unknown_stats():
    c = Character.from_dict({"name": "X", "stat_xp": {"BOGUS": 999, "STR": 50}})
    assert "BOGUS" not in c.stat_xp
    assert c.stat_xp["STR"] == 50
