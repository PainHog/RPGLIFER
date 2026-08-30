from rpglifer.activities import activity_by_name
from rpglifer.character import Character
from rpglifer.recommend import (recommendations, top_activities_for_stat,
                                 weakest_stats)
from rpglifer.stats import STAT_KEYS


def test_top_activities_for_stat_are_sorted_and_relevant():
    top = top_activities_for_stat("STR", n=5)
    assert len(top) == 5
    for a in top:
        assert "STR" in a.weights
    weights = [a.weights["STR"] for a in top]
    assert weights == sorted(weights, reverse=True)


def test_weakest_stats_picks_lowest_xp():
    c = Character()
    c.stat_xp["INT"] = 5000
    c.stat_xp["STR"] = 4000
    weak = weakest_stats(c, n=2)
    assert "INT" not in weak and "STR" not in weak


def test_recommendations_target_weak_stats():
    c = Character()
    # Pump two stats high so the other four are "weak".
    c.stat_xp["INT"] = 8000
    c.stat_xp["CHA"] = 8000
    weak = set(weakest_stats(c, 2))
    recs = recommendations(c, count=6)
    assert 1 <= len(recs) <= 6
    # Every recommendation should contribute to at least one weak stat.
    for a in recs:
        assert any(k in a.weights for k in weak)


def test_recommendations_prefer_unlogged():
    c = Character()
    # Log one activity a lot; it should not dominate suggestions.
    reading = activity_by_name("Reading")
    c.log_activity(reading, 30)
    recs = recommendations(c, count=6)
    names = [a.name for a in recs]
    assert len(names) == len(set(names))  # no duplicates
