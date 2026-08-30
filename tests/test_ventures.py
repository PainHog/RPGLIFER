from rpglifer import ventures, gear
from rpglifer.character import STAR_XP, Character


def _hero():
    c = Character()
    for k in ("STR", "CHA", "CRE"):
        c.stat_xp[k] = 20000
    return c


def test_roll_vault_shape():
    chests = ventures.roll_vault(_hero(), seed=3)
    assert len(chests) == 3
    for ch in chests:
        assert ch.tier in ("common", "rare", "jackpot")
        assert ch.hero > 0
        assert ch.gear is None or isinstance(ch.gear, gear.Gear)


def test_roll_vault_deterministic():
    a = ventures.roll_vault(_hero(), seed=9)
    b = ventures.roll_vault(_hero(), seed=9)
    assert [(c.tier, c.hero, c.gear is not None) for c in a] == \
           [(c.tier, c.hero, c.gear is not None) for c in b]


def test_luck_shifts_tiers_up():
    poor = Character()  # low Luck
    rich = Character()
    rich.stat_xp["CRE"] = STAR_XP * 2  # boosts LCK a lot
    rich.stat_xp["CHA"] = STAR_XP * 2
    def jackpots(c):
        return sum(ch.tier == "jackpot"
                   for s in range(150) for ch in ventures.roll_vault(c, seed=s))
    assert jackpots(rich) > jackpots(poor)
