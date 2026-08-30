"""RPG Lifer — turn the things you do every day into a leveling RPG character.

The package is split into a pure, UI-independent *core* (stats, activities,
fuzzy search, leveling math, the character model, and save/load) and two
front-ends that sit on top of it: a Tkinter desktop GUI and a console CLI.
Keeping the core free of any UI code is what lets us unit-test everything and
swap or add front-ends later.
"""

__version__ = "0.1.0"
__app_name__ = "RPG Lifer"
