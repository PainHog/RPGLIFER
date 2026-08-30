from rpglifer.activities import ACTIVITIES, DEFAULT_XP_PER_MINUTE, activity_by_name
from rpglifer.stats import STAT_KEYS


def test_catalog_is_nonempty():
    assert len(ACTIVITIES) >= 30


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
