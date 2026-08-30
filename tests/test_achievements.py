from rpglifer import achievements
from rpglifer.activities import activity_by_name
from rpglifer.character import STAR_XP, Character


def test_first_step_unlocks_on_first_log():
    c = Character()
    r = c.log_activity(activity_by_name("Reading"), 30)
    assert "first_step" in {a.id for a in r.achievements}
    assert "first_step" in c.achievements


def test_check_is_idempotent():
    c = Character()
    c.log_activity(activity_by_name("Reading"), 30)
    n = len(c.achievements)
    assert c.check_achievements() == []
    assert len(c.achievements) == n


def test_mastery_unlocks_on_first_star():
    c = Character()
    c.stat_xp["STR"] = STAR_XP  # one ★
    got = {a.id for a in c.check_achievements()}
    assert "first_master" in got


def test_all_ids_and_names_unique():
    ids = [a.id for a in achievements.ACHIEVEMENTS]
    names = [a.name for a in achievements.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))


def test_achievements_survive_roundtrip():
    c = Character()
    c.log_activity(activity_by_name("Reading"), 30)
    c2 = Character.from_dict(c.to_dict())
    assert set(c2.achievements) == set(c.achievements)
