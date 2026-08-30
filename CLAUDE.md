# CLAUDE.md — working notes for RPG Lifer

A desktop RPG that turns real-life activities into a leveling character. Python +
CustomTkinter GUI, packaged to a single Windows `.exe`.

## Run / test / build

```bash
python -m pytest -q          # tests (no display needed; ~110 tests)
python run.py                # launch the GUI (needs CustomTkinter + a display)
python run.py --cli          # text-mode fallback (stdlib only)
pip install -r requirements.txt   # runtime dep: customtkinter
pyinstaller --noconfirm --clean packaging/rpglifer.spec   # build dist/RPGLifer.exe
```

CI (`.github/workflows/build-windows.yml`) runs the tests on Ubuntu, then builds
`RPGLifer.exe` on Windows and uploads it as an artifact.

**This dev box has no Tkinter in the default `python3`.** Use `/usr/bin/python3.12`
(has Tk 8.6) under `xvfb-run` to run/smoke/screenshot the GUI, e.g.
`PYTHONPATH=. xvfb-run -a /usr/bin/python3.12 script.py`, and `scrot -o out.png`
to capture. `python3 -m pytest` works because tests never import the GUI.

## Architecture

The **core is UI-free and fully tested**; two front-ends sit on top.

```
rpglifer/
  leveling.py     0–100 mastery curve (front-loaded: level = 100*(xp/XP_TO_MAX)^0.4)
  stats.py        the 8 core stats (STR DEX CON INT WIS CHA DIS CRE; plain-life names)
  titles.py       per-stat title ladders (levels 10/25/40/55/75/100)
  derived.py      combat/shop stats (HP/PWR/FOC/INS/INF/LCK) + evolving class, from core
  activities.py   loads data/activities.json into Activity objects
  data/activities.json   600+ multi-stat activities (editable; weights are per-stat multipliers)
  fuzzy.py        type-ahead / closest-match search (stdlib only)
  recommend.py    "explore" suggestions + per-stat activity lookups
  economy.py      Hero/Overachiever point rules
  quests.py       daily quest templates (3/day, seeded by date)
  achievements.py 17 milestone trophies (pure predicates over character state)
  adventure.py    Arena auto-battle engine (foe archetypes + bosses; seedable/pure)
  gear.py         loot generation (3 slots, 4 rarities)
  shop.py         Shop catalog + purchase -> Bonus
  character.py    THE model: XP, prestige (★), streaks, points, bonuses, quests,
                  achievements, gear, save shape. Levels are always derived from XP.
  storage.py      JSON save in the per-user data dir (RPGLIFER_DATA_DIR overrides)
  cli.py          text-mode front-end
  ui_tk.py        the gamified GUI (radar, level ring, XP bursts, 8 sections)
  app.py          entry point (GUI, falls back to CLI if Tkinter is missing)
```

## Key model concepts

- **Prestige:** a stat's XP never resets. `stars = xp // STAR_XP`; `level` is the
  0–99 climb within the current star; `effective_level = stars*100 + level`
  (uncapped). `overall_level` sums effective levels. Titles/derived/radar use
  effective levels.
- **Points:** Hero (progress, reach bonus, Arena) and Overachiever (weekly
  well-rounded challenge). `LogResult` carries all the "what changed" events.
- **Bonuses (Shop):** temporary — `xp_mult` (time-limited, folds into logging)
  or `combat_power` (per-fight, spent in the Arena). Never buy stats.
- **Gear:** equipped items add flat bonuses to *derived* stats only.
- **Save schema is v2**, additive; `from_dict` tolerates old/missing fields, so
  old saves load. Add new fields with defaults; don't break back-compat.

## Conventions

- Keep game logic in the core (importable, testable); `ui_tk.py` only renders.
- Every new subsystem gets: a module, `character` integration + persistence, a
  test file, and a GUI smoke/screenshot under xvfb before committing.
- Palette + widgets live at the top of `ui_tk.py` (deep slate, muted gold/teal,
  rounded, no borders, flat line icons — no multicolor emoji in the UI chrome).
- Run the full audit script pattern (long play-through + save/load roundtrip +
  old-schema load) after model changes.
