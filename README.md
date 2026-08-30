# ⚔️ RPG Lifer

**Turn the things you do every day into a leveling RPG character.**

Log real-life activities — a workout, the dishes, an hour of reading — and the
time you spend becomes experience that raises your stats. Over weeks and months
your character sheet becomes a portrait of how you actually spend your life. Do
nothing but lift weights? You'll be a walking pile of **Strength** with a
**Charisma** of 1. The character you build is the one you *earn*.

![RPG Lifer screenshot](docs/screenshot.png)

---

## The idea

- **Stats.** Six classic attributes to start (easy to change and expand):
  **STR**ength, **DEX**terity, **CON**stitution, **INT**elligence,
  **WIS**dom, **CHA**risma.
- **Activities.** A growing catalog of everyday things — each mapped to the
  stat(s) it trains. Reading feeds Intelligence; a strength workout feeds
  Strength; dishes and chores build the daily-discipline of Constitution.
- **Type-ahead search.** Start typing and the closest activities pop up even if
  you don't type the exact words — `dsh` → **Dishes**, `wrk` → **Strength
  workout**, `medi` → **Meditation**.
- **Time → XP → levels.** Dedicate minutes to an activity; that time becomes XP,
  split across the activity's stats by weight. Each stat levels up on its own
  curve — early levels come fast, later ones cost more.
- **Your save is yours.** Everything is stored locally in a plain JSON file. No
  account, no cloud, no tracking.

## Get the Windows app (`.exe`)

You don't need Python to *run* the app — just a `.exe`.

**Option A — download a pre-built `.exe` (no tools needed).**
Every push builds the executable on a Windows machine via GitHub Actions:

1. Open the repo's **Actions** tab → the latest **Build Windows EXE** run.
2. Download the **`RPGLifer-windows`** artifact at the bottom of the run.
3. Unzip it and double-click **`RPGLifer.exe`**.

**Option B — build it yourself on Windows.**
Install [Python 3.9+](https://www.python.org/downloads/) (tick *"Add Python to
PATH"*), then double-click **`build.bat`**. When it finishes, your app is at
`dist\RPGLifer.exe` — copy it anywhere.

> The `.exe` is a single self-contained file (~12 MB). A friendlier one-click
> *installer* (Start-menu shortcut, uninstall entry) is on the roadmap.

## Run from source (any OS)

```bash
python run.py            # launch the GUI
python run.py --cli      # text-mode interface (no display needed)
python -m rpglifer       # same as run.py
```

No third-party packages are required at runtime — it's all standard library, and
Tkinter ships with the official python.org installers.

## How XP works

Logging `minutes` of an activity grants `minutes × xp_per_minute` of base XP
(default **6**/min), divided among the activity's stats by their weights. For
example **Reading** is `INT 0.8 / WIS 0.2`, so a 30-minute session
(30 × 6 = 180 base XP) grants **144 INT** and **36 WIS**.

Each stat's level is derived purely from its total XP, so the numbers can never
drift out of sync with your log. The first level costs 100 XP and each level
after costs ~35% more than the last.

## Add your own activities

The catalog is meant to grow into a *very* long list. Adding one is a single
line in [`rpglifer/activities.py`](rpglifer/activities.py):

```python
Activity("Rock climbing", {"STR": 0.5, "DEX": 0.4, "CON": 0.1},
         aliases=("climbing", "bouldering"), category="Fitness"),
```

The weight keys must be valid stat keys from
[`rpglifer/stats.py`](rpglifer/stats.py) (a test enforces this). Search,
logging, and the UI pick up new activities automatically.

## Where is my save?

A single `save.json`, in your user data directory:

| OS      | Location                                            |
| ------- | --------------------------------------------------- |
| Windows | `%APPDATA%\RPGLifer\save.json`                       |
| macOS   | `~/Library/Application Support/RPGLifer/save.json`   |
| Linux   | `~/.local/share/rpglifer/save.json`                 |

Set the `RPGLIFER_DATA_DIR` environment variable to override it. A corrupt save
is set aside as `save.corrupt-<timestamp>.json` rather than lost.

## Project layout

```
rpglifer/
  leveling.py     XP ↔ level math (pure functions)
  stats.py        the six stats (data-driven)
  activities.py   the activity catalog
  fuzzy.py        type-ahead / closest-match search
  character.py    the character model: XP, logging, save/load shape
  storage.py      where and how the save is written
  cli.py          text-mode front-end
  ui_tk.py        the Tkinter desktop GUI
  app.py          entry point (chooses GUI or CLI)
tests/            unit tests for the whole core
packaging/        PyInstaller spec
run.py            dev launcher & PyInstaller entry point
build.bat         one-click Windows build
```

The **core** (everything above `cli.py`) has no UI code, which is why it's
fully unit-tested and why front-ends can be swapped or added freely.

## Running the tests

```bash
python -m pytest -q
```

## Roadmap

This is the foundation. Planned next:

- **A longer catalog** — many more activities across every stat.
- **Refined stats & weights** — the six above are a starting point, not gospel.
- **Overachiever / Hero points** — earned by reaching outside your comfort
  zone, spendable on…
- **Gear, mini-games, and runs** — small challenges and loot to chase.
- **Weekly challenges & battles** — nudges to hit *all* the core areas of life,
  not just your favorites.
- **A real installer** — Start-menu shortcut and an icon.

## License

MIT.
