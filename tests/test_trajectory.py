from datetime import datetime, timedelta, timezone

from rpglifer.activities import activity_by_name
from rpglifer.character import Character

UTC = timezone.utc


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


def test_empty_trajectory():
    assert Character().level_trajectory() == []


def test_trajectory_is_nondecreasing_and_ends_at_overall():
    c = Character()
    a = activity_by_name("Strength workout")
    base = datetime(2026, 1, 1, 9, tzinfo=UTC)
    for d in range(10):
        c.log_activity(a, 45, when=_iso(base + timedelta(days=d)))
    traj = c.level_trajectory()
    assert len(traj) == 10  # one sample per distinct day
    assert traj == sorted(traj)  # climbing (XP only ever added)
    assert traj[-1] == c.overall_level()


def test_multiple_same_day_logs_collapse_to_one_sample():
    c = Character()
    a = activity_by_name("Reading")
    base = datetime(2026, 2, 2, 8, tzinfo=UTC)
    c.log_activity(a, 30, when=_iso(base))
    c.log_activity(a, 30, when=_iso(base + timedelta(hours=2)))
    c.log_activity(a, 30, when=_iso(base + timedelta(days=1)))
    traj = c.level_trajectory()
    assert len(traj) == 2  # two distinct days
    assert traj[-1] == c.overall_level()
