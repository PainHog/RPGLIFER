"""The desktop GUI (Tkinter) — the real Windows app.

Layout at a glance::

    +--------------------------------------------------------------+
    |  ⚔ RPG LIFER            [ character name ]        LV  42      |
    +---------------------------+----------------------------------+
    |  STR  💪  Lv 5  [====   ] |  Log an activity                 |
    |  DEX  🤸  Lv 3  [==     ] |   ( activity text field )        |
    |  CON  🛡  Lv 6  [=====  ] |   [ live fuzzy suggestions ]     |
    |  INT  📚  Lv 8  [====== ] |   minutes: [ 30 ]   [ Log ]      |
    |  WIS  🧘  Lv 4  [===    ] |   status line / level-up toast   |
    |  CHA  🎭  Lv 2  [=      ] |  Recent activity                 |
    |                           |   ...                            |
    +---------------------------+----------------------------------+

Only the core (character, activities, fuzzy) is imported here — no game logic
lives in the UI. Tkinter is imported at module load (safe without a display);
an actual window is created only in :func:`run`.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from . import fuzzy, storage
from .activities import ACTIVITIES, Activity
from .character import Character
from .stats import STATS, stat

# --- Palette ---------------------------------------------------------------
BG = "#1b1e28"
PANEL = "#242a38"
PANEL_2 = "#2c3345"
TRACK = "#161923"
TEXT = "#e8eaf0"
MUTED = "#9aa0b4"
ACCENT = "#e9c46a"  # gold
GOOD = "#7ed08f"

SUGGESTION_LIMIT = 7
DEFAULT_MINUTES = 30


class StatRow:
    """One stat's display: name, level, a colored XP bar, and XP text."""

    def __init__(self, parent: tk.Widget, s, row: int, fonts: dict):
        self.stat = s
        self.bar_w = 170
        self.bar_h = 16

        name = tk.Label(parent, text=f"{s.emoji}  {s.name}", bg=PANEL, fg=TEXT,
                        font=fonts["label"], anchor="w")
        name.grid(row=row, column=0, sticky="w", padx=(14, 8), pady=6)

        self.level_lbl = tk.Label(parent, text="Lv 1", bg=PANEL, fg=s.color,
                                  font=fonts["level"], anchor="w", width=6)
        self.level_lbl.grid(row=row, column=1, sticky="w", pady=6)

        self.canvas = tk.Canvas(parent, width=self.bar_w, height=self.bar_h,
                                bg=TRACK, highlightthickness=0, bd=0)
        self.canvas.grid(row=row, column=2, sticky="w", padx=8, pady=6)

        self.xp_lbl = tk.Label(parent, text="", bg=PANEL, fg=MUTED,
                               font=fonts["xp"], anchor="e", width=11)
        self.xp_lbl.grid(row=row, column=3, sticky="e", padx=(4, 14), pady=6)

    def update(self, character: Character):
        p = character.progress(self.stat.key)
        self.level_lbl.config(text=f"Lv {p.level}")
        self.xp_lbl.config(text=f"{p.xp_into_level} / {p.xp_for_level}")
        self.canvas.delete("all")
        fill_w = int(self.bar_w * p.fraction)
        if fill_w > 0:
            self.canvas.create_rectangle(0, 0, fill_w, self.bar_h,
                                         fill=self.stat.color, width=0)
        # thin top highlight for a touch of depth
        if fill_w > 1:
            self.canvas.create_rectangle(0, 0, fill_w, 2, fill="#ffffff", width=0,
                                         stipple="gray25")


class RPGLiferApp:
    def __init__(self, root: tk.Tk, character: Character):
        self.root = root
        self.character = character
        self.selected: Activity | None = None

        base_family = self._pick_font()
        self.fonts = {
            "title": tkfont.Font(family=base_family, size=20, weight="bold"),
            "badge": tkfont.Font(family=base_family, size=13, weight="bold"),
            "badge_big": tkfont.Font(family=base_family, size=22, weight="bold"),
            "label": tkfont.Font(family=base_family, size=12),
            "level": tkfont.Font(family=base_family, size=12, weight="bold"),
            "xp": tkfont.Font(family=base_family, size=10),
            "heading": tkfont.Font(family=base_family, size=13, weight="bold"),
            "entry": tkfont.Font(family=base_family, size=13),
            "status": tkfont.Font(family=base_family, size=11),
            "list": tkfont.Font(family=base_family, size=10),
        }

        root.title("RPG Lifer")
        root.configure(bg=BG)
        root.geometry("940x600")
        root.minsize(860, 540)

        self._build_header()
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1, minsize=360)
        body.rowconfigure(0, weight=1)
        self._build_stats(body)
        self._build_log_panel(body)

        self.refresh()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- construction ------------------------------------------------------
    def _pick_font(self) -> str:
        available = set(tkfont.families(self.root))
        for family in ("Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial"):
            if family in available:
                return family
        return "TkDefaultFont"

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 10))

        tk.Label(header, text="⚔  RPG LIFER", bg=BG, fg=ACCENT,
                 font=self.fonts["title"]).pack(side="left")

        # Overall level badge on the right.
        badge = tk.Frame(header, bg=PANEL_2)
        badge.pack(side="right")
        tk.Label(badge, text="LEVEL", bg=PANEL_2, fg=MUTED,
                 font=self.fonts["status"]).pack(padx=14, pady=(6, 0))
        self.level_value = tk.Label(badge, text="0", bg=PANEL_2, fg=ACCENT,
                                    font=self.fonts["badge_big"])
        self.level_value.pack(padx=14, pady=(0, 6))

        # Editable character name in the middle.
        name_wrap = tk.Frame(header, bg=BG)
        name_wrap.pack(side="right", padx=18)
        tk.Label(name_wrap, text="Hero", bg=BG, fg=MUTED,
                 font=self.fonts["status"]).pack(anchor="w")
        self.name_var = tk.StringVar(value=self.character.name)
        name_entry = tk.Entry(name_wrap, textvariable=self.name_var, bg=PANEL, fg=TEXT,
                              insertbackground=TEXT, relief="flat", width=18,
                              font=self.fonts["badge"])
        name_entry.pack(ipady=3)
        self.name_var.trace_add("write", self._on_name_change)

    def _build_stats(self, parent: tk.Widget):
        panel = tk.Frame(parent, bg=PANEL)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(panel, text="CHARACTER SHEET", bg=PANEL, fg=MUTED,
                 font=self.fonts["heading"]).grid(row=0, column=0, columnspan=4,
                                                  sticky="w", padx=14, pady=(14, 4))
        self.rows: list[StatRow] = []
        for i, s in enumerate(STATS, start=1):
            self.rows.append(StatRow(panel, s, i, self.fonts))
        # a little breathing room at the bottom
        tk.Frame(panel, bg=PANEL, height=8).grid(row=len(STATS) + 1, column=0)

    def _build_log_panel(self, parent: tk.Widget):
        panel = tk.Frame(parent, bg=PANEL)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)

        tk.Label(panel, text="LOG AN ACTIVITY", bg=PANEL, fg=MUTED,
                 font=self.fonts["heading"]).grid(row=0, column=0, sticky="w",
                                                  padx=14, pady=(14, 6))

        self.activity_var = tk.StringVar()
        entry = tk.Entry(panel, textvariable=self.activity_var, bg=PANEL_2, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=self.fonts["entry"])
        entry.grid(row=1, column=0, sticky="ew", padx=14, ipady=6)
        entry.bind("<KeyRelease>", self._on_activity_key)
        entry.bind("<Down>", self._focus_suggestions)
        entry.bind("<Return>", lambda e: self.do_log())
        self.activity_entry = entry

        self.suggestions = tk.Listbox(
            panel, height=SUGGESTION_LIMIT, bg=PANEL_2, fg=TEXT,
            selectbackground=ACCENT, selectforeground=BG, relief="flat",
            highlightthickness=0, activestyle="none", font=self.fonts["list"])
        self.suggestions.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 8))
        self.suggestions.bind("<<ListboxSelect>>", self._on_suggestion_select)
        self.suggestions.bind("<Return>", lambda e: self.do_log())
        self.suggestions.bind("<Double-Button-1>", lambda e: self.do_log())

        controls = tk.Frame(panel, bg=PANEL)
        controls.grid(row=3, column=0, sticky="ew", padx=14)
        tk.Label(controls, text="minutes", bg=PANEL, fg=MUTED,
                 font=self.fonts["status"]).pack(side="left")
        self.minutes_var = tk.StringVar(value=str(DEFAULT_MINUTES))
        tk.Spinbox(controls, from_=1, to=1440, increment=5, width=6,
                   textvariable=self.minutes_var, bg=PANEL_2, fg=TEXT,
                   insertbackground=TEXT, relief="flat", justify="center",
                   font=self.fonts["entry"]).pack(side="left", padx=(6, 12))
        tk.Button(controls, text="Log Activity", command=self.do_log,
                  bg=ACCENT, fg=BG, relief="flat", font=self.fonts["badge"],
                  activebackground=GOOD, cursor="hand2",
                  padx=14, pady=4).pack(side="left")

        self.status = tk.Label(panel, text="Start typing an activity…", bg=PANEL,
                               fg=MUTED, font=self.fonts["status"], anchor="w",
                               justify="left", wraplength=360)
        self.status.grid(row=4, column=0, sticky="ew", padx=14, pady=(10, 6))

        tk.Label(panel, text="RECENT", bg=PANEL, fg=MUTED,
                 font=self.fonts["heading"]).grid(row=5, column=0, sticky="w",
                                                  padx=14, pady=(6, 4))
        self.recent = tk.Listbox(panel, bg=TRACK, fg=TEXT, relief="flat",
                                 highlightthickness=0, activestyle="none",
                                 font=self.fonts["list"])
        self.recent.grid(row=6, column=0, sticky="nsew", padx=14, pady=(0, 14))
        panel.rowconfigure(6, weight=1)

    # --- behavior ----------------------------------------------------------
    def _matches(self) -> list[Activity]:
        query = self.activity_var.get()
        return fuzzy.rank(query, ACTIVITIES, lambda a: a.search_terms(),
                          limit=SUGGESTION_LIMIT)

    def _on_activity_key(self, event=None):
        # Ignore navigation keys; those are handled elsewhere.
        if event and event.keysym in ("Down", "Up", "Return"):
            return
        self.selected = None
        self._refill_suggestions(self._matches())

    def _refill_suggestions(self, matches: list[Activity]):
        self._current_matches = matches
        self.suggestions.delete(0, tk.END)
        for a in matches:
            stats = " / ".join(sorted(a.weights, key=lambda k: -a.weights[k]))
            self.suggestions.insert(tk.END, f"{a.name}   ·   {stats}")

    def _focus_suggestions(self, event=None):
        if self.suggestions.size():
            self.suggestions.focus_set()
            self.suggestions.selection_clear(0, tk.END)
            self.suggestions.selection_set(0)
            self.suggestions.activate(0)

    def _on_suggestion_select(self, event=None):
        sel = self.suggestions.curselection()
        if not sel:
            return
        idx = sel[0]
        matches = getattr(self, "_current_matches", [])
        if 0 <= idx < len(matches):
            self.selected = matches[idx]
            self.set_status(f"Selected: {self.selected.name}", MUTED)

    def _resolve_activity(self) -> Activity | None:
        if self.selected is not None:
            return self.selected
        matches = self._matches()
        return matches[0] if matches else None

    def do_log(self):
        activity = self._resolve_activity()
        if activity is None:
            self.set_status("No matching activity — try different words.", ACCENT)
            return
        try:
            minutes = float(self.minutes_var.get())
        except ValueError:
            self.set_status("Minutes must be a number.", ACCENT)
            return
        if minutes <= 0:
            self.set_status("Minutes must be greater than zero.", ACCENT)
            return

        result = self.character.log_activity(activity, minutes)
        storage.save(self.character)
        self.refresh()

        gains = "   ".join(f"+{round(v)} {k}" for k, v in result.gains.items() if v)
        msg = f"Logged {int(minutes)}m of {activity.name}:  {gains}"
        color = TEXT
        if result.level_ups:
            ups = ", ".join(f"{stat(lu.stat).name} → Lv {lu.to_level}"
                            for lu in result.level_ups)
            msg += f"\n⭐ Level up!  {ups}"
            color = ACCENT
        self.set_status(msg, color)

        # Reset the picker for the next entry.
        self.activity_var.set("")
        self.selected = None
        self.suggestions.delete(0, tk.END)
        self.activity_entry.focus_set()

    def set_status(self, text: str, color: str = MUTED):
        self.status.config(text=text, fg=color)

    def _on_name_change(self, *_):
        self.character.name = self.name_var.get().strip() or "Adventurer"

    def refresh(self):
        for row in self.rows:
            row.update(self.character)
        self.level_value.config(text=str(self.character.overall_level()))
        self.recent.delete(0, tk.END)
        for e in self.character.recent(20):
            stamp = e.when[5:16].replace("T", " ")
            self.recent.insert(tk.END, f"{stamp}   {e.activity}  ({int(e.minutes)}m)")

    def on_close(self):
        self.character.name = self.name_var.get().strip() or "Adventurer"
        storage.save(self.character)
        self.root.destroy()


def run(character: Character | None = None) -> int:
    """Create the window and enter the Tk event loop. Returns an exit code."""
    character = character if character is not None else storage.load()
    root = tk.Tk()
    RPGLiferApp(root, character)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
