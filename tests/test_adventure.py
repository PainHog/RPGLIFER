from rpglifer import adventure
from rpglifer.character import STAR_XP, Character


def _fighter():
    c = Character()
    c.stat_xp["STR"] = 20000
    c.stat_xp["CON"] = 20000
    c.stat_xp["DEX"] = 15000
    return c


def test_battle_is_deterministic_with_a_seed():
    c = _fighter()
    a = adventure.simulate(c, seed=42)
    b = adventure.simulate(c, seed=42)
    assert (a.won, len(a.rounds), a.reward, a.foe_name) == \
           (b.won, len(b.rounds), b.reward, b.foe_name)


def test_battle_has_valid_shape():
    b = adventure.simulate(_fighter(), seed=1)
    assert b.you_max_hp > 0 and b.foe_max_hp > 0
    assert b.rounds and len(b.rounds) <= adventure.MAX_ROUNDS
    assert b.reward > 0


def test_a_strong_character_wins_most_of_the_time():
    c = Character()
    for k in ("STR", "DEX", "CON"):
        c.stat_xp[k] = STAR_XP  # maxed physical stats
    wins = sum(adventure.simulate(c, seed=s).won for s in range(60))
    assert wins >= 30


def test_combat_bonus_raises_win_rate():
    c = _fighter()
    base = sum(adventure.simulate(c, seed=s).won for s in range(80))
    boosted = sum(adventure.simulate(c, combat_bonus=0.5, seed=s).won
                  for s in range(80))
    assert boosted >= base
