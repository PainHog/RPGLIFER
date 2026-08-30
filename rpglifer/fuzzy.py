"""Fuzzy, type-as-you-go matching for the activity picker.

Goal: the moment someone starts typing, surface the closest activities even when
what they typed isn't an exact keyword — "dsh" should find *Dishes*, "wrk" should
find *Strength workout*, and a typo like "medltate" should still land on
*Meditation*.

This uses only the standard library (``difflib``) so the packaged ``.exe`` stays
small and dependency-free. The scoring blends four cheap signals:

* exact / prefix / whole-word-prefix matches (people usually type the start),
* substring matches (earlier and more complete is better),
* subsequence matches (the "dsh" -> "dishes" case), and
* ``difflib``'s similarity ratio (catches transposed/typo'd letters).

The best signal for a candidate wins; the best candidate string for an activity
wins for that activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Iterable, Sequence, TypeVar

T = TypeVar("T")

# Below this combined score a candidate is considered "not really a match".
DEFAULT_THRESHOLD = 120.0


def _subsequence_positions(query: str, text: str) -> list[int] | None:
    """Return the indices where ``query`` matches ``text`` in order, or ``None``."""
    positions: list[int] = []
    qi = 0
    for i, ch in enumerate(text):
        if qi < len(query) and ch == query[qi]:
            positions.append(i)
            qi += 1
    return positions if qi == len(query) else None


def _subsequence_score(query: str, text: str) -> float | None:
    """Score ``query`` as a subsequence spanning the whole ``text`` (cross-word).

    Returns ``None`` when it isn't a subsequence. Rewards compactness — letters
    appearing close together beat letters scattered across the string.
    """
    positions = _subsequence_positions(query, text)
    if positions is None:
        return None
    span = positions[-1] - positions[0] + 1
    compactness = len(query) / span if span else 1.0
    head_bonus = max(0.0, 1.0 - positions[0] / (len(text) or 1)) * 20.0
    return compactness * 100.0 + head_bonus


def _subsequence_in_word(query: str, word: str) -> float | None:
    """Score ``query`` as a subsequence *inside a single word*.

    Matching within one word (``wrk`` -> ``workout``) is a stronger signal than
    matching scattered across a whole phrase, and matching nearer the start of
    the word is stronger still. Both are rewarded here.
    """
    positions = _subsequence_positions(query, word)
    if positions is None:
        return None
    span = positions[-1] - positions[0] + 1
    compactness = len(query) / span if span else 1.0
    early = max(0.0, 1.0 - positions[0] / (len(word) or 1))
    # Where the match starts matters most: "dsh" opens "dishes" but sits mid-word
    # in "hea<dsh>ots", so the latter scores lower even though it's contiguous.
    return compactness * 80.0 + early * 140.0


def score_text(query: str, text: str) -> float:
    """Score how well ``text`` matches ``query`` (higher is better, 0 = no match)."""
    q = query.strip().lower()
    t = text.strip().lower()
    if not q or not t:
        return 0.0
    if q == t:
        return 1000.0

    best = 0.0

    # Whole-string prefix.
    if t.startswith(q):
        best = max(best, 780.0 + (len(q) / len(t)) * 100.0)

    # Word-level signals (e.g. "work"/"wrk" against "strength workout").
    # Split on spaces and slashes so multi-word names are matched per word.
    for word in t.replace("/", " ").split():
        if word == q:
            best = max(best, 900.0)
        elif word.startswith(q):
            best = max(best, 680.0 + (len(q) / len(word)) * 80.0)
        else:
            in_word = _subsequence_in_word(q, word)
            if in_word is not None:
                best = max(best, 190.0 + in_word)

    # Substring anywhere. A match at a word boundary is a strong signal; a
    # fragment buried mid-word (e.g. "dsh" inside "hea<dsh>ots") is weak and must
    # not outrank a real subsequence match on a short name.
    idx = t.find(q)
    if idx != -1:
        at_word_start = idx == 0 or t[idx - 1] in " /-"
        coverage = len(q) / len(t)
        base = 470.0 if at_word_start else 285.0
        best = max(best, base + coverage * 120.0 - idx * 1.5)

    # Subsequence (handles dropped letters like "dsh" -> "dishes").
    sub = _subsequence_score(q, t)
    if sub is not None:
        best = max(best, 240.0 + sub)

    # Similarity ratio catches transpositions and typos.
    ratio = SequenceMatcher(None, q, t).ratio()
    best = max(best, ratio * 320.0)

    return best


@dataclass(frozen=True)
class Match:
    item: object
    score: float


def rank(
    query: str,
    items: Sequence[T],
    terms: Callable[[T], Iterable[str]],
    limit: int = 8,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[T]:
    """Rank ``items`` against ``query``.

    ``terms`` yields the searchable strings for an item (name plus aliases); the
    item's score is the best score across its terms. Items scoring below
    ``threshold`` are dropped. Ties break by the item's original order, keeping
    results stable as the user types.
    """
    q = query.strip()
    if not q:
        return []
    scored: list[tuple[float, int, T]] = []
    for order, item in enumerate(items):
        best = 0.0
        for term in terms(item):
            s = score_text(q, term)
            if s > best:
                best = s
        if best >= threshold:
            scored.append((best, order, item))
    scored.sort(key=lambda triple: (-triple[0], triple[1]))
    return [item for _, _, item in scored[:limit]]
