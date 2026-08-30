"""The activity catalog — the "things you do" that earn XP.

Each :class:`Activity` maps to one or more stats via ``weights``. When you log
an activity for some number of minutes, it earns ``minutes * xp_per_minute`` of
base XP, split across its stats by those weights. So a 30-minute "Reading"
session (INT 0.8 / WIS 0.2 at 6 XP/min = 180 base XP) grants 144 INT and 36 WIS.

This starter catalog is intentionally broad but nowhere near complete — the plan
is a *very* long list. Adding an activity is a one-line entry below; everything
else (search, logging, the UI) picks it up automatically. Weight keys must be
valid stat keys from :mod:`rpglifer.stats` (a test enforces this).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Default XP earned per minute of an activity, before the per-stat split.
DEFAULT_XP_PER_MINUTE = 6.0


@dataclass(frozen=True)
class Activity:
    name: str
    weights: dict[str, float]  # stat key -> share of the XP (need not sum to 1)
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


# --- The catalog -----------------------------------------------------------
# Grouped loosely by the stat they lean on, but weights are what actually
# matter. Keep entries short; lean on aliases for the phrasings people type.
ACTIVITIES: tuple[Activity, ...] = (
    # Strength ---------------------------------------------------------------
    Activity("Strength workout", {"STR": 1.0},
             aliases=("weightlifting", "lifting", "weights", "gym", "resistance training"),
             category="Fitness"),
    Activity("Push-ups", {"STR": 0.7, "CON": 0.3},
             aliases=("pushups", "press ups"), category="Fitness"),
    Activity("Pull-ups", {"STR": 0.8, "CON": 0.2},
             aliases=("pullups", "chin ups"), category="Fitness"),
    Activity("Carrying / moving heavy things", {"STR": 0.8, "CON": 0.2},
             aliases=("moving boxes", "hauling", "heavy lifting"), category="Fitness"),
    Activity("Martial arts", {"STR": 0.4, "DEX": 0.4, "WIS": 0.2},
             aliases=("boxing", "karate", "jiu jitsu", "bjj", "kickboxing"),
             category="Fitness"),

    # Dexterity --------------------------------------------------------------
    Activity("Stretching", {"DEX": 0.8, "CON": 0.2},
             aliases=("mobility", "flexibility"), category="Fitness"),
    Activity("Yoga", {"DEX": 0.5, "WIS": 0.3, "CON": 0.2},
             aliases=("pilates",), category="Fitness"),
    Activity("Dancing", {"DEX": 0.6, "CHA": 0.3, "CON": 0.1},
             aliases=("dance",), category="Fitness"),
    Activity("Sports", {"DEX": 0.5, "CON": 0.4, "CHA": 0.1},
             aliases=("basketball", "soccer", "tennis", "volleyball", "football"),
             category="Fitness"),
    Activity("Drawing / painting", {"DEX": 0.6, "INT": 0.2, "WIS": 0.2},
             aliases=("art", "sketching", "painting", "drawing"), category="Creative"),
    Activity("Practicing an instrument", {"DEX": 0.4, "INT": 0.4, "WIS": 0.2},
             aliases=("guitar", "piano", "music practice", "violin", "drums"),
             category="Creative"),
    Activity("Crafting / DIY", {"DEX": 0.6, "INT": 0.4},
             aliases=("woodworking", "knitting", "building", "handiwork"),
             category="Creative"),
    Activity("Video games (skill)", {"DEX": 0.7, "INT": 0.3},
             aliases=("gaming", "esports"), category="Leisure"),
    Activity("Typing practice", {"DEX": 0.7, "INT": 0.3},
             aliases=("typing",), category="Skill"),

    # Constitution -----------------------------------------------------------
    Activity("Running", {"CON": 0.6, "DEX": 0.4},
             aliases=("jogging", "run", "5k", "cardio"), category="Fitness"),
    Activity("Walking", {"CON": 0.7, "DEX": 0.3},
             aliases=("walk", "steps"), category="Fitness"),
    Activity("Cycling", {"CON": 0.6, "DEX": 0.4},
             aliases=("biking", "bike ride", "spin"), category="Fitness"),
    Activity("Swimming", {"CON": 0.5, "STR": 0.3, "DEX": 0.2},
             aliases=("swim", "laps"), category="Fitness"),
    Activity("Hiking", {"CON": 0.6, "STR": 0.2, "WIS": 0.2},
             aliases=("hike", "trekking"), category="Fitness"),
    Activity("Dishes", {"CON": 0.6, "WIS": 0.4},
             aliases=("washing up", "wash dishes", "kitchen cleanup"), category="Chores"),
    Activity("Cleaning", {"CON": 0.6, "WIS": 0.4},
             aliases=("tidying", "chores", "vacuuming", "housework"), category="Chores"),
    Activity("Laundry", {"CON": 0.7, "WIS": 0.3},
             aliases=("washing", "folding clothes"), category="Chores"),
    Activity("Cooking / meal prep", {"CON": 0.4, "INT": 0.3, "WIS": 0.3},
             aliases=("cooking", "meal prep", "baking", "food prep"), category="Chores"),
    Activity("Good sleep", {"CON": 0.8, "WIS": 0.2},
             aliases=("sleep", "rest", "nap"), category="Health"),
    Activity("Healthy meal", {"CON": 0.7, "WIS": 0.3},
             aliases=("eating well", "nutrition", "balanced meal"), category="Health"),
    Activity("Hydration", {"CON": 1.0},
             aliases=("drinking water", "water"), category="Health"),

    # Intelligence -----------------------------------------------------------
    Activity("Reading", {"INT": 0.8, "WIS": 0.2},
             aliases=("read", "book", "reading a book"), category="Learning"),
    Activity("Studying", {"INT": 1.0},
             aliases=("study", "revision", "homework"), category="Learning"),
    Activity("Coding / programming", {"INT": 0.9, "DEX": 0.1},
             aliases=("coding", "programming", "software", "dev work"), category="Learning"),
    Activity("Writing", {"INT": 0.6, "WIS": 0.2, "CHA": 0.2},
             aliases=("blogging", "essay", "writing"), category="Creative"),
    Activity("Online course", {"INT": 1.0},
             aliases=("course", "tutorial", "lecture", "class"), category="Learning"),
    Activity("Learning a language", {"INT": 0.7, "CHA": 0.3},
             aliases=("language learning", "duolingo", "vocabulary"), category="Learning"),
    Activity("Puzzles / chess", {"INT": 0.8, "WIS": 0.2},
             aliases=("chess", "sudoku", "crossword", "puzzle"), category="Leisure"),

    # Wisdom -----------------------------------------------------------------
    Activity("Meditation", {"WIS": 1.0},
             aliases=("meditate", "mindfulness", "breathing"), category="Mindfulness"),
    Activity("Journaling", {"WIS": 0.6, "INT": 0.4},
             aliases=("journal", "diary", "gratitude journal"), category="Mindfulness"),
    Activity("Prayer / reflection", {"WIS": 1.0},
             aliases=("prayer", "reflection", "contemplation"), category="Mindfulness"),
    Activity("Time in nature", {"WIS": 0.6, "CON": 0.4},
             aliases=("nature", "outdoors", "park", "forest"), category="Mindfulness"),
    Activity("Therapy", {"WIS": 0.7, "CHA": 0.3},
             aliases=("counseling", "therapy session"), category="Health"),
    Activity("Budgeting / finances", {"WIS": 0.5, "INT": 0.5},
             aliases=("budget", "finances", "money management", "bills"), category="Admin"),

    # Charisma ---------------------------------------------------------------
    Activity("Socializing", {"CHA": 1.0},
             aliases=("hanging out", "friends", "social", "party"), category="Social"),
    Activity("Calling family / friends", {"CHA": 0.8, "WIS": 0.2},
             aliases=("phone call", "call mom", "catch up"), category="Social"),
    Activity("Networking", {"CHA": 0.7, "INT": 0.3},
             aliases=("networking event", "meetup"), category="Social"),
    Activity("Public speaking", {"CHA": 0.8, "INT": 0.2},
             aliases=("presentation", "speech", "talk"), category="Social"),
    Activity("Volunteering", {"CHA": 0.5, "WIS": 0.5},
             aliases=("charity", "helping out", "community service"), category="Social"),
    Activity("Date night", {"CHA": 0.8, "CON": 0.2},
             aliases=("date", "romance"), category="Social"),
    Activity("Team meeting", {"CHA": 0.6, "INT": 0.4},
             aliases=("meeting", "standup", "collaboration"), category="Work"),
    Activity("Gardening", {"CON": 0.5, "DEX": 0.3, "WIS": 0.2},
             aliases=("garden", "planting", "yard work"), category="Chores"),
)


def all_activities() -> tuple[Activity, ...]:
    return ACTIVITIES


def activity_by_name(name: str) -> Activity | None:
    lowered = name.strip().lower()
    for activity in ACTIVITIES:
        if activity.name.lower() == lowered:
            return activity
    return None
