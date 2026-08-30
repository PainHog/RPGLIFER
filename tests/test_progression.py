"""Consistency streaks, XP bonuses, and title unlocks on logging."""

from datetime import datetime, timedelta, timezone

import pytest

from rpglifer.activities import activity_by_name
from rpglifer.character import Character, consistency_bonus

UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def test_consistency_bonus_curve():
    assert consistency_bonus(1) == 0.0
    assert consistency_bonus(2) == pytest.approx(0.10)
    assert consistency_bonus(3) == pytest.approx(0.20)
    assert consistency_bonus(6) == pytest.approx(0.50)
    assert consistency_bonus(50) == pytest.approx(0.50)  # capped


def test_first_log_has_no_bonus():
    c = Character()
    result = c.log_activity(activity_by_name("Reading"), 30)
    assert result.streak == 1
    assert result.bonus == 0.0


def test_consecutive_weeks_build_a_streak_and_bonus():
    c = Character()
    reading = activity_by_name("Reading")
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)

    r1 = c.log_activity(reading, 30, when=_iso(w0))
    r2 = c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=7)))
    r3 = c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=14)))

    assert (r1.streak, r2.streak, r3.streak) == (1, 2, 3)
    assert r2.bonus == pytest.approx(0.10)
    assert r3.bonus == pytest.approx(0.20)


def test_bonus_actually_scales_xp():
    c = Character()
    reading = activity_by_name("Reading")  # INT 0.8
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    c.log_activity(reading, 30, when=_iso(w0))
    r2 = c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=7)))
    base = 30 * reading.xp_per_minute
    assert r2.gains["INT"] == pytest.approx(base * 0.8 * 1.10)


def test_skipping_a_week_resets_the_streak():
    c = Character()
    reading = activity_by_name("Reading")
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    c.log_activity(reading, 30, when=_iso(w0))
    c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=7)))
    # Skip a week, then log again three weeks after w0.
    r = c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=21)))
    assert r.streak == 1
    assert r.bonus == 0.0


def test_streaks_are_per_activity():
    c = Character()
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    c.log_activity(activity_by_name("Reading"), 30, when=_iso(w0))
    # A different activity in the next week starts its own streak at 1.
    r = c.log_activity(activity_by_name("Running"), 30,
                       when=_iso(w0 + timedelta(days=7)))
    assert r.streak == 1


def test_consistency_preview_matches_logging():
    c = Character()
    reading = activity_by_name("Reading")
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    c.log_activity(reading, 30, when=_iso(w0))
    # Previewing at the following week should show streak 2 / +10%.
    streak, bonus = c.consistency("Reading", at=w0 + timedelta(days=7))
    assert streak == 2
    assert bonus == pytest.approx(0.10)


def test_reaching_a_milestone_unlocks_a_title():
    c = Character()
    # 120 min of Studying (INT 1.0 @ 2 xp/min) = 240 XP = exactly level 3.
    result = c.log_activity(activity_by_name("Studying"), 120)
    assert c.level("INT") == 3
    assert any(t.stat == "INT" and t.title == "Curious" for t in result.titles)
    assert c.title("INT") == "Curious"


def test_no_title_reported_when_none_crossed():
    c = Character()
    result = c.log_activity(activity_by_name("Studying"), 10)  # tiny, stays Lv 1
    assert result.titles == []
    assert c.title("INT") is None


def test_streak_and_bonus_survive_save_roundtrip():
    c = Character()
    reading = activity_by_name("Reading")
    w0 = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    c.log_activity(reading, 30, when=_iso(w0))
    c.log_activity(reading, 30, when=_iso(w0 + timedelta(days=7)))
    restored = Character.from_dict(c.to_dict())
    assert restored.log[-1].streak == 2
    assert restored.log[-1].bonus == pytest.approx(0.10)
