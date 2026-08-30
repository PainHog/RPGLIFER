"""The activity catalog — the "things you do" that earn XP.

The catalog lives in an editable data file, ``rpglifer/data/activities.json``, so
it can grow to hundreds of entries (and be tweaked) without touching code. Each
entry maps to one or more stats via ``weights``.

**Weights are independent multipliers of the activity's base XP, per stat** — they
do not need to sum to 1. Logging an activity for some minutes earns
``minutes * xp_per_minute`` of base XP, and each stat receives that base times its
weight. So one activity can pour a lot into a primary stat and a faint trickle
into a couple of others (e.g. Watercolor painting: DEX 0.6, WIS 0.25, INT 0.1) —
exactly how real activities develop you unevenly across many dimensions.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .stats import STAT_KEYS

# Default XP earned per minute of an activity, before the per-stat weights.
# Deliberately low: real growth should take weeks of dedication, not an evening.
DEFAULT_XP_PER_MINUTE = 2.0

DATA_FILENAME = "activities.json"


@dataclass(frozen=True)
class Activity:
    name: str
    weights: dict[str, float]  # stat key -> multiplier of the base XP
    aliases: tuple[str, ...] = ()  # extra search terms / common phrasings
    xp_per_minute: float = DEFAULT_XP_PER_MINUTE
    category: str = "General"

    def xp_split(self, minutes: float) -> dict[str, float]:
        """XP awarded per stat for spending ``minutes`` on this activity."""
        base = max(0.0, minutes) * self.xp_per_minute
        return {key: base * weight for key, weight in self.weights.items()}

    def search_terms(self) -> tuple[str, ...]:
        """All strings that should match this activity in fuzzy search."""
        return (self.name, *self.aliases)

    def primary_stats(self) -> list[str]:
        """Stat keys ordered by weight, heaviest first."""
        return sorted(self.weights, key=lambda k: -self.weights[k])


def _data_file() -> Path:
    """Locate the catalog JSON both from source and inside the frozen .exe."""
    base = getattr(sys, "_MEIPASS", None)  # set by PyInstaller at runtime
    candidates: list[Path] = []
    if base:
        candidates.append(Path(base) / "rpglifer" / "data" / DATA_FILENAME)
    candidates.append(Path(__file__).resolve().parent / "data" / DATA_FILENAME)
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Activity catalog not found. Looked in: {[str(p) for p in candidates]}"
    )


def _load_catalog() -> tuple[Activity, ...]:
    """Parse the catalog file into Activity objects, defensively.

    Bad rows are skipped rather than crashing the app: entries are de-duplicated
    by name, weight keys not in :data:`rpglifer.stats.STAT_KEYS` are dropped, and
    any row left with no valid weights is ignored.
    """
    raw = json.loads(_data_file().read_text(encoding="utf-8"))
    out: list[Activity] = []
    seen: set[str] = set()
    for item in raw:
        try:
            name = str(item["name"]).strip()
        except (KeyError, TypeError):
            continue
        key = name.lower()
        if not name or key in seen:
            continue
        weights: dict[str, float] = {}
        for wk, wv in dict(item.get("weights", {})).items():
            code = str(wk).upper()
            try:
                value = float(wv)
            except (TypeError, ValueError):
                continue
            if code in STAT_KEYS and value > 0:
                weights[code] = value
        if not weights:
            continue
        seen.add(key)
        aliases = tuple(
            str(a).strip() for a in item.get("aliases", []) or () if str(a).strip()
        )
        try:
            xppm = float(item.get("xp_per_minute", DEFAULT_XP_PER_MINUTE))
        except (TypeError, ValueError):
            xppm = DEFAULT_XP_PER_MINUTE
        category = str(item.get("category", "General")).strip() or "General"
        out.append(Activity(name=name, weights=weights, aliases=aliases,
                            xp_per_minute=xppm, category=category))
    return tuple(out)


ACTIVITIES: tuple[Activity, ...] = _load_catalog()

# Lookup helpers ------------------------------------------------------------
_BY_NAME: dict[str, Activity] = {a.name.lower(): a for a in ACTIVITIES}


def all_activities() -> tuple[Activity, ...]:
    return ACTIVITIES


def activity_by_name(name: str) -> Activity | None:
    return _BY_NAME.get(name.strip().lower())


def categories() -> list[str]:
    """Distinct categories, in first-seen order."""
    seen: list[str] = []
    for a in ACTIVITIES:
        if a.category not in seen:
            seen.append(a.category)
    return seen
