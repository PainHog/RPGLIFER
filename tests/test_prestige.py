"""Prestige stars: hitting 100 resets the bar into a ★ tier, uncapped."""

from rpglifer.activities import activity_by_name
from rpglifer.character import STAR_XP, Character
from rpglifer.stats import STAT_KEYS


def test_stars_and_effective_level():
    c = Character()
    c.stat_xp["STR"] = STAR_XP * 2 + 5
    assert c.stars("STR") == 2
    assert 0 <= c.level("STR") < 100
    assert c.effective_level("STR") == 200 + c.level("STR")


def test_crossing_a_star_grants_it_and_resets_the_bar():
    c = Character()
    c.stat_xp["STR"] = STAR_XP - 50  # a hair below the first star
    before_level = c.level("STR")  # ~99
    result = c.log_activity(activity_by_name("Strength workout"), 60)  # +120 STR
    assert c.stars("STR") == 1
    assert any(su.stat == "STR" and su.star == 1 for su in result.star_ups)
    assert c.level("STR") < before_level  # visible bar reset into the new star
    # A star-up is reported instead of a granular level-up for that stat.
    assert not any(lu.stat == "STR" for lu in result.level_ups)


def test_title_maxes_and_holds_past_mastery():
    c = Character()
    c.stat_xp["STR"] = STAR_XP * 3  # effective level 300
    assert c.title("STR") == "Colossus"  # capstone, stays maxed while ★ climbs


def test_overall_level_is_uncapped():
    c = Character()
    for k in STAT_KEYS:
        c.stat_xp[k] = STAR_XP * 2  # each stat effective level 200
    assert c.overall_level() == len(STAT_KEYS) * 200  # far past the old 800 ceiling


def test_derived_stats_grow_with_prestige():
    from rpglifer import derived
    c = Character()
    base = derived.compute(c)["PWR"]
    c.stat_xp["STR"] = STAR_XP * 2  # effective 200 STR
    assert derived.compute(c)["PWR"] > base
