"""Guard the text-mode fallback so model changes can't silently break it."""

from rpglifer.activities import activity_by_name
from rpglifer.character import STAR_XP, Character
from rpglifer.cli import format_log_result, format_recent, format_sheet


def test_format_sheet_renders_all_stats():
    c = Character(name="Hero")
    out = format_sheet(c)
    assert "Hero" in out
    for name in ("Strength", "Creativity", "Discipline"):
        assert name in out


def test_format_sheet_shows_stars_and_points():
    c = Character()
    c.stat_xp["STR"] = STAR_XP + 100  # ★1
    c.hero_points = 42
    out = format_sheet(c)
    assert "★1" in out
    assert "42" in out


def test_format_log_result_covers_events():
    c = Character()
    r = c.log_activity(activity_by_name("Studying"), 200)  # level-ups + title
    out = format_log_result(r)
    assert "Studying" in out
    assert "level" in out.lower()


def test_format_recent_runs():
    c = Character()
    c.log_activity(activity_by_name("Reading"), 30)
    assert "Reading" in format_recent(c)
