from datetime import datetime, timedelta, timezone

from rpglifer import shop
from rpglifer.activities import activity_by_name
from rpglifer.character import Character

UTC = timezone.utc


def _cos(cid):
    return next(x for x in shop.COSMETICS if x.id == cid)


def test_earned_cosmetic_is_locked_and_not_buyable_until_earned():
    c = Character()
    ember = _cos("ring_ember")  # earned via a 7-day streak
    assert ember.unlock is not None
    assert not shop.owns_cosmetic(c, ember)
    # Earned-only cosmetics can't be bought with points.
    c.overachiever_points = 999
    assert shop.buy_cosmetic(c, ember) is False
    assert ember.id not in c.owned_cosmetics


def test_earned_cosmetic_unlocks_and_persists():
    now = datetime.now(UTC)
    c = Character()
    a = activity_by_name("Reading")
    for d in range(7):  # a live 7-day streak
        c.log_activity(a, 20, when=(now - timedelta(days=d))
                       .replace(microsecond=0).isoformat())
    assert c.daily_streak() >= 7
    newly = shop.check_cosmetic_unlocks(c)
    ids = {i.id for i in newly}
    assert "ring_ember" in ids
    assert shop.owns_cosmetic(c, _cos("ring_ember"))
    # Idempotent: a second check grants nothing new.
    assert shop.check_cosmetic_unlocks(c) == []
    # Persists even if the condition later lapses (streak breaks).
    c.log = []
    assert c.daily_streak() == 0
    assert shop.owns_cosmetic(c, _cos("ring_ember"))


def test_prestige_ring_unlocks_at_first_star():
    from rpglifer.leveling import XP_TO_MAX
    c = Character()
    assert not shop.owns_cosmetic(c, _cos("ring_prestige"))
    c.stat_xp["STR"] = XP_TO_MAX + 100  # one prestige star
    shop.check_cosmetic_unlocks(c)
    assert shop.owns_cosmetic(c, _cos("ring_prestige"))


def test_bought_cosmetic_still_works():
    c = Character()
    c.overachiever_points = 100
    emerald = _cos("ring_emerald")
    assert shop.buy_cosmetic(c, emerald)
    assert shop.owns_cosmetic(c, emerald)
    assert shop.select_cosmetic(c, emerald)
    assert c.ring_color == emerald.color
