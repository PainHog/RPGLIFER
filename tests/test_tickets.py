from rpglifer import character as char_mod
from rpglifer.activities import activity_by_name
from rpglifer.character import Character


def test_fresh_character_has_no_tickets():
    assert Character().adventure_tickets == 0


def test_logging_earns_tickets_with_reach_bonus():
    c = Character()
    # First-ever "Strength workout" is a reach (new activity) → base + reach.
    r = c.log_activity(activity_by_name("Strength workout"), 30)
    assert r.tickets_earned == char_mod.TICKETS_PER_LOG + char_mod.TICKETS_REACH_BONUS
    assert c.adventure_tickets == r.tickets_earned


def test_repeat_of_a_strong_stat_earns_base_only():
    c = Character()
    c.log_activity(activity_by_name("Strength workout"), 30)  # now STR is strongest
    before = c.adventure_tickets
    r = c.log_activity(activity_by_name("Strength workout"), 30)  # not new, not weak
    assert r.tickets_earned == char_mod.TICKETS_PER_LOG
    assert c.adventure_tickets == before + char_mod.TICKETS_PER_LOG


def test_spend_ticket_decrements_and_floors_at_zero():
    c = Character()
    c.adventure_tickets = 1
    assert c.spend_ticket() is True
    assert c.adventure_tickets == 0
    assert c.spend_ticket() is False
    assert c.adventure_tickets == 0


def test_tickets_persist_through_roundtrip():
    c = Character()
    c.adventure_tickets = 7
    c2 = Character.from_dict(c.to_dict())
    assert c2.adventure_tickets == 7


def test_old_save_without_tickets_loads_as_zero():
    c = Character()
    data = c.to_dict()
    data.pop("adventure_tickets", None)  # simulate a pre-ticket save
    assert Character.from_dict(data).adventure_tickets == 0
