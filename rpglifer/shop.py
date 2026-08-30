"""The Shop — spend points on temporary **bonuses**, never on stats.

Hero points (from progress and the Arena) and Overachiever points (from the
weekly well-rounded challenge) buy time-limited XP boosts and per-fight combat
boosts. Buying grants a :class:`rpglifer.character.Bonus`; the character model
applies it. Real-life stats are only ever earned by doing real activities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .character import Bonus


@dataclass(frozen=True)
class ShopItem:
    id: str
    name: str
    desc: str
    cost: int
    currency: str  # "hero" or "overachiever"
    kind: str  # "xp_mult" or "combat_power"
    magnitude: float
    hours: int = 0  # lifetime for time-based (xp_mult) bonuses
    uses: int = 0  # fights for use-based (combat_power) bonuses


ITEMS: tuple[ShopItem, ...] = (
    ShopItem("xp_elixir", "XP Elixir", "+25% XP from every activity for 24 hours.",
             50, "hero", "xp_mult", 0.25, hours=24),
    ShopItem("focus_brew", "Focus Brew", "+40% XP for the next 12 hours.",
             90, "hero", "xp_mult", 0.40, hours=12),
    ShopItem("battle_draught", "Battle Draught",
             "+30% Power in your next 3 Arena battles.",
             40, "hero", "combat_power", 0.30, uses=3),
    ShopItem("grand_elixir", "Grand XP Elixir", "+50% XP from everything for 24 hours.",
             60, "overachiever", "xp_mult", 0.50, hours=24),
    ShopItem("champions_sigil", "Champion's Sigil",
             "+25% Power in your next 5 Arena battles.",
             45, "overachiever", "combat_power", 0.25, uses=5),
)


def balance(character, currency: str) -> int:
    return (character.hero_points if currency == "hero"
            else character.overachiever_points)


def can_afford(character, item: ShopItem) -> bool:
    return balance(character, item.currency) >= item.cost


def purchase(character, item: ShopItem, now: datetime | None = None) -> bool:
    """Spend points and grant ``item``'s bonus. Returns False if unaffordable."""
    if not can_afford(character, item):
        return False
    if item.currency == "hero":
        character.hero_points -= item.cost
    else:
        character.overachiever_points -= item.cost

    expires = ""
    uses = -1
    if item.kind == "xp_mult":
        when = (now or datetime.now(timezone.utc)) + timedelta(hours=item.hours)
        expires = when.replace(microsecond=0).isoformat()
    else:
        uses = item.uses
    character.add_bonus(Bonus(id=item.id, name=item.name, kind=item.kind,
                              magnitude=item.magnitude, expires_at=expires,
                              uses_left=uses))
    return True
