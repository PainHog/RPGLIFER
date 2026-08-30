from datetime import datetime, timedelta, timezone

from rpglifer import quests
from rpglifer.activities import activity_by_name
from rpglifer.character import Character

UTC = timezone.utc


def test_daily_quests_are_stable_and_three_distinct():
    a = quests.daily_quests("2026-03-02")
    b = quests.daily_quests("2026-03-02")
    assert [q.id for q in a] == [q.id for q in b]
    assert len(a) == 3 and len({q.id for q in a}) == 3


def test_quests_complete_and_award_via_logging():
    c = Character()
    base = datetime(2026, 3, 2, 9, tzinfo=UTC)
    names = ["Strength workout", "Reading a novel", "Meditation", "Running",
             "Socializing", "Watercolor painting"]
    for i, n in enumerate(names):
        c.log_activity(activity_by_name(n), 30,
                       when=(base + timedelta(minutes=15 * i)).isoformat())
    claimed = [q for q, _c, cl in c.quest_status(base) if cl]
    assert claimed  # at least one of today's quests completed
    assert c.hero_points > 0
    # No double awards.
    before = c.hero_points
    c.evaluate_daily_quests(base)
    assert c.hero_points == before


def test_arena_win_completes_the_arena_quest():
    # Find a date whose quest set includes the Arena quest.
    date = next(f"2026-04-{d:02d}" for d in range(1, 60)
                if any(q.id == "arena" for q in quests.daily_quests(f"2026-04-{d:02d}")))
    at = datetime.fromisoformat(date + "T09:00:00+00:00")
    c = Character()
    before = c.hero_points
    done = c.record_arena_win(at)
    assert any(q.id == "arena" for q in done)
    assert c.hero_points > before
    assert c.daily[date]["arena_wins"] == 1


def test_quest_state_survives_roundtrip():
    c = Character()
    c.log_activity(activity_by_name("Reading"), 30)
    c2 = Character.from_dict(c.to_dict())
    assert c2.quests_claimed == c.quests_claimed
    assert c2.daily == c.daily
