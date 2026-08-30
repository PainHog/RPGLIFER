from datetime import datetime, timedelta, timezone

from rpglifer.activities import activity_by_name
from rpglifer.character import Character

UTC = timezone.utc
NOON = datetime(2026, 5, 20, 12, tzinfo=UTC)  # a fixed "today"


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


def _log_on(c, day_offset):
    a = activity_by_name("Reading")
    c.log_activity(a, 20, when=_iso(NOON - timedelta(days=day_offset)))


def test_no_logs_is_zero():
    assert Character().daily_streak(at=NOON) == 0


def test_today_only_is_one():
    c = Character()
    _log_on(c, 0)
    assert c.daily_streak(at=NOON) == 1


def test_consecutive_days_count():
    c = Character()
    for d in (0, 1, 2, 3):
        _log_on(c, d)
    assert c.daily_streak(at=NOON) == 4


def test_gap_breaks_streak():
    c = Character()
    for d in (0, 1, 3, 4):  # missing day 2
        _log_on(c, d)
    assert c.daily_streak(at=NOON) == 2


def test_today_empty_but_yesterday_still_counts():
    c = Character()
    for d in (1, 2, 3):  # nothing today (offset 0)
        _log_on(c, d)
    # Streak ends yesterday and is still extendable today.
    assert c.daily_streak(at=NOON) == 3


def test_stale_streak_is_zero():
    c = Character()
    for d in (5, 6, 7):  # last activity 5 days ago
        _log_on(c, d)
    assert c.daily_streak(at=NOON) == 0


def test_multiple_logs_same_day_count_once():
    c = Character()
    _log_on(c, 0)
    _log_on(c, 0)
    _log_on(c, 1)
    assert c.daily_streak(at=NOON) == 2


def test_streak_achievements_unlock():
    from rpglifer import achievements
    ids = {a.id for a in achievements.ACHIEVEMENTS}
    assert {"on_fire", "unstoppable_habit"} <= ids
    # Log on the last 7 real calendar days so daily_streak() (which uses the
    # real "now") sees a live 7-day streak and the trophy actually unlocks.
    now = datetime.now(UTC)
    c = Character()
    a = activity_by_name("Reading")
    for d in range(7):
        c.log_activity(a, 20, when=_iso(now - timedelta(days=d)))
    assert c.daily_streak() >= 7
    # log_activity already runs check_achievements, so the trophy is unlocked
    # and persisted by the time the 7th day is logged.
    c.check_achievements()
    assert "on_fire" in c.achievements
