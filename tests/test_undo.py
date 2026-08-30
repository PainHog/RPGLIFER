from rpglifer.activities import activity_by_name
from rpglifer.character import Character, LogEntry


def test_delete_entry_removes_it_and_subtracts_xp():
    c = Character()
    reading = activity_by_name("Reading")
    r1 = c.log_activity(reading, 30)
    r2 = c.log_activity(reading, 60)
    assert len(c.log) == 2
    xp_before = dict(c.stat_xp)
    entry = c.log[0]  # the first (30-min) session
    assert c.delete_log_entry(entry)
    assert len(c.log) == 1
    for k, v in entry.xp.items():
        assert abs(c.stat_xp[k] - (xp_before[k] - v)) < 1e-9


def test_delete_last_entry_zeroes_a_fresh_stat():
    c = Character()
    a = activity_by_name("Reading")
    c.log_activity(a, 30)
    only = c.log[0]
    assert c.delete_log_entry(only)
    assert len(c.log) == 0
    # No other Reading XP existed, so INT/WIS return to 0.
    for k in only.xp:
        assert c.stat_xp[k] == 0.0


def test_delete_unknown_entry_returns_false():
    c = Character()
    c.log_activity(activity_by_name("Reading"), 30)
    ghost = LogEntry(activity="Nope", minutes=1, when="2020-01-01T00:00:00",
                     xp={"INT": 5.0})
    assert not c.delete_log_entry(ghost)
    assert len(c.log) == 1


def test_delete_never_drives_a_stat_negative():
    c = Character()
    a = activity_by_name("Reading")
    c.log_activity(a, 30)
    entry = c.log[0]
    # Tamper: pretend the stat already drifted below the entry's recorded xp.
    for k in entry.xp:
        c.stat_xp[k] = 1.0
    c.delete_log_entry(entry)
    for k in entry.xp:
        assert c.stat_xp[k] >= 0.0


def test_delete_lowers_overall_level_and_roundtrips():
    c = Character()
    a = activity_by_name("Strength workout")
    for _ in range(6):
        c.log_activity(a, 90)
    before = c.overall_level()
    c.delete_log_entry(c.log[-1])
    assert c.overall_level() <= before
    c2 = Character.from_dict(c.to_dict())
    assert c2.overall_level() == c.overall_level()
    assert len(c2.log) == len(c.log)
