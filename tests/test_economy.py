from datetime import datetime, timedelta, timezone

from rpglifer import economy
from rpglifer.activities import activity_by_name
from rpglifer.character import Character

UTC = timezone.utc


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


def test_hero_points_awarded_on_progress():
    c = Character()
    r = c.log_activity(activity_by_name("Strength workout"), 60)
    assert r.hero_gain > 0
    assert c.hero_points == r.hero_gain


def test_reach_bonus_for_a_new_activity():
    c = Character()
    r = c.log_activity(activity_by_name("Reading"), 30)
    assert r.hero_gain >= economy.HERO_REACH_BONUS


def test_weekly_wellrounded_awards_once_per_week():
    c = Character()
    base = datetime(2026, 3, 2, 12, tzinfo=UTC)  # a Monday
    names = ["Strength workout", "Reading a novel", "Meditation", "Running",
             "Socializing", "Watercolor painting"]
    total = 0
    for i, n in enumerate(names):
        total += c.log_activity(activity_by_name(n), 30,
                                when=_iso(base + timedelta(hours=i))).overachiever_gain
    assert total == economy.OVERACHIEVER_WEEKLY  # exactly one payout
    # Logging more in the same week does not pay again.
    again = c.log_activity(activity_by_name("Dishes"), 20,
                           when=_iso(base + timedelta(hours=9))).overachiever_gain
    assert again == 0


def test_points_for_events_counts_each_kind():
    class E:  # minimal stand-ins
        pass
    lv = [E(), E()]
    ti = [E()]
    st = [E()]
    expected = (economy.HERO_PER_LEVEL * 2 + economy.HERO_PER_TITLE
                + economy.HERO_PER_STAR)
    assert economy.points_for_events(lv, ti, st) == expected
