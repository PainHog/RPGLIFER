"""A text-mode front-end for RPG Lifer.

This exists for two reasons: it is a genuine fallback when a graphical display
or Tkinter is unavailable (servers, minimal Python builds), and its formatting
helpers are pure functions that can be unit-tested without a screen.

Type part of an activity to see fuzzy suggestions, pick one, enter minutes, and
watch your stats climb. ``:sheet``, ``:recent``, ``:help`` and ``:quit`` are the
meta-commands.
"""

from __future__ import annotations

import sys
from typing import Sequence

from . import fuzzy, storage
from .activities import ACTIVITIES, Activity
from .character import Character
from .stats import STATS, stat

BAR_WIDTH = 20


def bar(fraction: float, width: int = BAR_WIDTH) -> str:
    filled = int(round(max(0.0, min(1.0, fraction)) * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def format_sheet(character: Character) -> str:
    lines = [
        f"=== {character.name} — Level {character.overall_level()} ===",
    ]
    for s in STATS:
        p = character.progress(s.key)
        stars = character.stars(s.key)
        star = f"★{stars} " if stars else "   "
        title = character.title(s.key)
        tag = f"  · {title}" if title else ""
        lines.append(
            f"{s.name:<13} {star}Lv {p.level:>3}  {bar(p.fraction)} "
            f"{p.xp_into_level:>6}/{p.xp_for_level:<6} XP{tag}"
        )
    d = character.hero_points, character.overachiever_points
    lines.append(f"\nHero points: {d[0]}   Overachiever points: {d[1]}")
    return "\n".join(lines)


def format_recent(character: Character, count: int = 10) -> str:
    entries = character.recent(count)
    if not entries:
        return "No activities logged yet."
    lines = ["Recent activity:"]
    for e in entries:
        gained = ", ".join(
            f"+{round(v)} {stat(k).name[:3].upper()}" for k, v in e.xp.items() if v
        )
        stamp = e.when[:16].replace("T", " ")
        flame = f"  🔥{e.streak}" if e.bonus > 0 else ""
        lines.append(f"  {stamp}  {e.activity} ({int(e.minutes)}m)  {gained}{flame}")
    return "\n".join(lines)


def format_suggestions(matches: Sequence[Activity]) -> str:
    if not matches:
        return "  (no matches — try different words)"
    lines = []
    for i, activity in enumerate(matches, start=1):
        stats = "/".join(sorted(activity.weights, key=lambda k: -activity.weights[k]))
        lines.append(f"  {i}. {activity.name}  [{stats}]")
    return "\n".join(lines)


def format_log_result(result) -> str:
    gains = ", ".join(f"+{round(v)} {stat(k).name}" for k, v in result.gains.items() if v)
    msg = f"Logged {int(result.minutes)}m of {result.activity}: {gains}"
    if result.bonus > 0:
        msg += f"  * {result.streak}-week streak (+{int(result.bonus * 100)}% XP)"
    if result.hero_gain:
        msg += f"  (+{result.hero_gain} Hero)"
    for su in getattr(result, "star_ups", []):
        msg += f"\n  ** MASTERY! {stat(su.stat).name} reached star {su.star}!"
    for lu in result.level_ups:
        msg += f"\n  + {stat(lu.stat).name} reached level {lu.to_level}!"
    for t in result.titles:
        msg += f'\n  * New title: "{t.title}" ({stat(t.stat).name})'
    for q in getattr(result, "quests_done", []):
        msg += f"\n  * Quest complete: {q.text}"
    for a in getattr(result, "achievements", []):
        msg += f"\n  * Achievement: {a.name}"
    return msg


def suggest(query: str, limit: int = 8) -> list[Activity]:
    return fuzzy.rank(query, ACTIVITIES, lambda a: a.search_terms(), limit=limit)


HELP = """Commands:
  <text>        search activities by name (fuzzy), then pick a number to log
  :sheet        show your character sheet
  :recent       show recently logged activities
  :help         show this help
  :quit         save and exit"""


def run(character: Character | None = None, *, autosave: bool = True) -> int:
    """Run the interactive console loop. Returns a process exit code."""
    character = character if character is not None else storage.load()
    print("⚔️  RPG LIFER — log life, level up.  (type :help)\n")
    print(format_sheet(character))
    print()

    while True:
        try:
            raw = input("activity> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        if raw in (":q", ":quit", ":exit"):
            break
        if raw in (":h", ":help"):
            print(HELP)
            continue
        if raw in (":sheet", ":s"):
            print(format_sheet(character))
            continue
        if raw in (":recent", ":r"):
            print(format_recent(character))
            continue

        matches = suggest(raw)
        print(format_suggestions(matches))
        if not matches:
            continue

        choice = input("pick #> ").strip()
        if not choice.isdigit():
            continue
        idx = int(choice) - 1
        if not (0 <= idx < len(matches)):
            print("  (out of range)")
            continue
        activity = matches[idx]

        minutes_raw = input("minutes> ").strip()
        try:
            minutes = float(minutes_raw)
        except ValueError:
            print("  (not a number)")
            continue
        if minutes <= 0:
            print("  (minutes must be positive)")
            continue

        result = character.log_activity(activity, minutes)
        print(format_log_result(result))
        if autosave:
            storage.save(character)

    if autosave:
        storage.save(character)
        print("Saved. See you next session.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
