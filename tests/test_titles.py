from rpglifer.stats import STAT_KEYS
from rpglifer.titles import TITLES, next_title, title_for


def test_every_stat_has_a_title_ladder():
    for key in STAT_KEYS:
        assert key in TITLES and len(TITLES[key]) >= 1


def test_ladders_are_sorted_ascending():
    for key, ladder in TITLES.items():
        levels = [level for level, _ in ladder]
        assert levels == sorted(levels), f"{key} ladder not sorted"


def test_no_title_below_first_milestone():
    assert title_for("STR", 1) is None
    assert title_for("STR", 9) is None


def test_title_at_and_above_milestone():
    assert title_for("STR", 10) == "Gym Rookie"
    assert title_for("STR", 24) == "Gym Rookie"  # holds until the next rung
    assert title_for("STR", 25) == "Weight Hauler"


def test_title_caps_at_top_rung():
    assert title_for("STR", 100) == "Colossus"
    assert title_for("STR", 999) == "Colossus"


def test_next_title_points_forward():
    assert next_title("INT", 1) == (10, "Curious")
    assert next_title("INT", 10) == (25, "Bookworm")


def test_next_title_none_when_maxed():
    top_level = TITLES["INT"][-1][0]
    assert next_title("INT", top_level) is None


def test_unknown_stat_is_safe():
    assert title_for("BOGUS", 50) is None
    assert next_title("BOGUS", 50) is None
