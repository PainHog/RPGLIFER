import json

from rpglifer import activities as activities_mod
from rpglifer.activities import ACTIVITIES, DEFAULT_XP_PER_MINUTE, activity_by_name
from rpglifer.stats import STAT_KEYS


def test_data_file_is_clean():
    """The shipped catalog file itself has unique names and valid stat keys."""
    raw = json.loads(activities_mod._data_file().read_text(encoding="utf-8"))
    names = [str(r["name"]).strip().lower() for r in raw]
    assert len(names) == len(set(names)), "duplicate activity names in data file"
    for r in raw:
        for key in r.get("weights", {}):
            assert key in STAT_KEYS, f"{r['name']} references unknown stat {key}"


def test_most_activities_touch_multiple_stats():
    multi = sum(1 for a in ACTIVITIES if len(a.weights) >= 2)
    assert multi / len(ACTIVITIES) > 0.7  # the catalog is deliberately multi-stat


def test_catalog_is_large():
    # The catalog is meant to be comprehensive (500+ activities).
    assert len(ACTIVITIES) >= 500


def test_activity_names_are_unique():
    names = [a.name for a in ACTIVITIES]
    assert len(names) == len(set(names))


def test_all_weight_keys_are_valid_stats():
    for activity in ACTIVITIES:
        for key in activity.weights:
            assert key in STAT_KEYS, f"{activity.name} references unknown stat {key}"


def test_weights_are_positive():
    for activity in ACTIVITIES:
        assert activity.weights, f"{activity.name} has no stats"
        for key, weight in activity.weights.items():
            assert weight > 0, f"{activity.name}:{key} weight must be positive"


def test_every_stat_has_at_least_one_activity():
    covered = {key for a in ACTIVITIES for key in a.weights}
    assert covered == set(STAT_KEYS)


def test_xp_split_scales_with_time():
    activity = activity_by_name("Reading")
    assert activity is not None
    ten = activity.xp_split(10)
    twenty = activity.xp_split(20)
    for key in ten:
        assert twenty[key] == 2 * ten[key]


def test_xp_split_matches_weights():
    activity = activity_by_name("Reading")
    split = activity.xp_split(10)
    base = 10 * DEFAULT_XP_PER_MINUTE
    for key, weight in activity.weights.items():
        assert abs(split[key] - base * weight) < 1e-9


def test_activity_lookup_is_case_insensitive():
    assert activity_by_name("reading") is activity_by_name("Reading")
    assert activity_by_name("nope") is None
