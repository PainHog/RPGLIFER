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


@dataclass(frozen=True)
class Cosmetic:
    id: str
    name: str
    color: str  # hex for the level-ring arc
    cost: int  # Overachiever points (0 = owned by default)


COSMETICS: tuple[Cosmetic, ...] = (
    Cosmetic("ring_gold", "Gold Ring", "#d9b26a", 0),
    Cosmetic("ring_emerald", "Emerald Ring", "#6bb39b", 30),
    Cosmetic("ring_crimson", "Crimson Ring", "#d9574f", 30),
    Cosmetic("ring_amethyst", "Amethyst Ring", "#b07de0", 40),
    Cosmetic("ring_azure", "Azure Ring", "#5aa9e6", 40),
)


def owns_cosmetic(character, item: Cosmetic) -> bool:
    return item.cost == 0 or item.id in character.owned_cosmetics


def is_selected(character, item: Cosmetic) -> bool:
    if item.id == "ring_gold":
        return not character.ring_color
    return character.ring_color == item.color


def buy_cosmetic(character, item: Cosmetic) -> bool:
    """Unlock a cosmetic with Overachiever points (idempotent if already owned)."""
    if owns_cosmetic(character, item):
        return True
    if character.overachiever_points < item.cost:
        return False
    character.overachiever_points -= item.cost
    character.owned_cosmetics.append(item.id)
    return True


def select_cosmetic(character, item: Cosmetic) -> bool:
    """Equip an owned cosmetic (free to switch)."""
    if not owns_cosmetic(character, item):
        return False
    character.ring_color = "" if item.id == "ring_gold" else item.color
    return True


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
