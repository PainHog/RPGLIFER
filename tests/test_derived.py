from rpglifer import derived
from rpglifer.activities import activity_by_name
from rpglifer.character import Character


def test_all_derived_present_and_nonnegative():
    c = Character()
    d = derived.compute(c)
    assert set(d) == {ds.key for ds in derived.DERIVED}
    assert all(v >= 0 for v in d.values())


def test_derived_rise_with_core_stats():
    c = Character()
    base = derived.compute(c)["HP"]
    c.stat_xp["CON"] = 5000  # push Endurance up
    assert derived.compute(c)["HP"] > base


def test_new_character_is_novice():
    assert derived.character_class(Character()) == "Novice Adventurer"


def test_class_reflects_top_stats():
    c = Character()
    c.stat_xp["STR"] = 9000
    c.stat_xp["INT"] = 4000
    # Top = STR (Warrior), second = INT (Clever)
    assert derived.character_class(c) == "Clever Warrior"
