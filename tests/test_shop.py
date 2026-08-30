from rpglifer import shop
from rpglifer.character import Character


def _first(currency=None, kind=None):
    for item in shop.ITEMS:
        if (currency is None or item.currency == currency) and \
           (kind is None or item.kind == kind):
            return item
    raise AssertionError("no matching item")


def test_purchase_deducts_and_grants_xp_bonus():
    c = Character()
    c.hero_points = 200
    item = _first(currency="hero", kind="xp_mult")
    assert shop.purchase(c, item)
    assert c.hero_points == 200 - item.cost
    assert c.xp_multiplier() > 1.0


def test_cannot_afford_leaves_state_untouched():
    c = Character()
    c.hero_points = 0
    item = _first(currency="hero")
    assert not shop.purchase(c, item)
    assert c.bonuses == []
    assert c.hero_points == 0


def test_combat_bonus_is_consumed_per_fight():
    c = Character()
    item = _first(kind="combat_power")
    setattr(c, "overachiever_points" if item.currency == "overachiever"
            else "hero_points", 500)
    assert shop.purchase(c, item)
    got = c.consume_combat_bonuses()
    assert got > 0
    combat = [b for b in c.bonuses if b.kind == "combat_power"]
    assert combat and combat[0].uses_left == item.uses - 1


def test_xp_bonus_actually_scales_logged_xp():
    from rpglifer.activities import activity_by_name
    c = Character()
    c.hero_points = 500
    item = _first(currency="hero", kind="xp_mult")
    reading = activity_by_name("Reading")  # INT 0.8
    without = c.log_activity(reading, 30).gains["INT"]
    shop.purchase(c, item)
    with_boost = c.log_activity(reading, 30).gains["INT"]
    assert with_boost > without


def test_cosmetic_buy_select_and_default():
    from rpglifer.character import Character
    c = Character()
    c.overachiever_points = 100
    emerald = next(x for x in shop.COSMETICS if x.id == "ring_emerald")
    assert not shop.owns_cosmetic(c, emerald)
    assert shop.buy_cosmetic(c, emerald)
    assert emerald.id in c.owned_cosmetics
    assert c.overachiever_points == 100 - emerald.cost
    assert shop.select_cosmetic(c, emerald)
    assert c.ring_color == emerald.color
    gold = next(x for x in shop.COSMETICS if x.id == "ring_gold")
    assert shop.owns_cosmetic(c, gold)  # default is always owned
    shop.select_cosmetic(c, gold)
    assert c.ring_color == ""


def test_cosmetic_cannot_afford():
    from rpglifer.character import Character
    c = Character()
    c.overachiever_points = 0
    amethyst = next(x for x in shop.COSMETICS if x.id == "ring_amethyst")
    assert not shop.buy_cosmetic(c, amethyst)
    assert amethyst.id not in c.owned_cosmetics


def test_cosmetics_roundtrip():
    from rpglifer.character import Character
    c = Character()
    c.owned_cosmetics = ["ring_emerald"]
    c.ring_color = "#6bb39b"
    c2 = Character.from_dict(c.to_dict())
    assert c2.owned_cosmetics == ["ring_emerald"]
    assert c2.ring_color == "#6bb39b"
