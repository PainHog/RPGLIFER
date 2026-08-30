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


def test_boss_and_vault_achievements_use_counters():
    c = Character()
    c.bump_counter("bosses", 1)
    assert "boss_slayer" in {a.id for a in c.check_achievements()}
    c.bump_counter("vaults", 15)
    assert "vault_raider" in {a.id for a in c.check_achievements()}


def test_counters_survive_roundtrip():
    c = Character()
    c.bump_counter("bosses", 3)
    c.bump_counter("vaults", 7)
    c2 = Character.from_dict(c.to_dict())
    assert c2.counters == {"bosses": 3, "vaults": 7}


def test_progress_functions_are_consistent_with_check():
    from rpglifer import achievements
    from rpglifer.character import Character
    c = Character()
    for a in achievements.ACHIEVEMENTS:
        if a.progress is None:
            continue
        cur, tgt = a.progress(c)
        assert isinstance(cur, int) and isinstance(tgt, int)
        assert tgt > 0
        assert cur >= 0
        # On a fresh character nothing measurable is complete yet.
        assert cur < tgt
        # Progress reaching the target must agree with the unlock predicate.
        assert a.check(c) == (cur >= tgt)
