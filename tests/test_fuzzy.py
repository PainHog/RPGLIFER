from rpglifer import fuzzy
from rpglifer.activities import ACTIVITIES


def _search(query, limit=8):
    return fuzzy.rank(query, ACTIVITIES, lambda a: a.search_terms(), limit=limit)


def _names(query, limit=8):
    return [a.name for a in _search(query, limit)]


def test_exact_name_scores_highest():
    assert fuzzy.score_text("dishes", "dishes") > fuzzy.score_text("dsh", "dishes")


def test_prefix_beats_scattered_subsequence():
    assert fuzzy.score_text("dish", "dishes") > fuzzy.score_text("dsh", "dishes")


def test_dropped_letters_still_match_dishes():
    # "dsh" is not a substring of "dishes" but is a subsequence.
    assert "Dishes" in _names("dsh")


def test_partial_word_finds_workout():
    assert "Strength workout" in _names("wrk")


def test_workout_outranks_scattered_match_for_wrk():
    # A subsequence inside one word ("wrk" in "workout") should beat one
    # scattered across a longer phrase.
    assert _names("wrk")[0] == "Strength workout"


def test_typo_still_finds_meditation():
    assert "Meditation" in _names("medi")
    assert "Meditation" in _names("meditate")  # via alias


def test_alias_matches():
    # "gym" is an alias of Strength workout.
    assert "Strength workout" in _names("gym")


def test_empty_query_returns_nothing():
    assert _search("") == []


def test_limit_is_respected():
    assert len(_search("a", limit=3)) <= 3


def test_results_are_sorted_by_score():
    results = _search("read")
    scores = [
        max(fuzzy.score_text("read", term) for term in a.search_terms())
        for a in results
    ]
    assert scores == sorted(scores, reverse=True)


def test_reading_is_top_hit_for_read():
    assert _names("read")[0] == "Reading"


def test_mid_word_alias_fragment_does_not_beat_real_match():
    # "dsh" lives inside aliases like "hea<dsh>ots"/"frien<dsh>ip"; the real
    # intent (Dishes) must win over those mid-word fragments.
    names = _names("dsh", limit=3)
    assert names[0] == "Dishes"
    assert "Portrait photography" not in names[:2]
