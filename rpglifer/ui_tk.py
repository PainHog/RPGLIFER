"""The desktop GUI, built with CustomTkinter for a soft, modern look.

Design language:
- Deep slate charcoal background; two faint raised tones for depth (no borders,
  no bevels — separation comes from tonal shifts and empty space).
- One muted gold accent (headings, level, titles) and one muted teal for progress.
- Rounded corners everywhere; generous padding; lots of negative space.
- No multicolor emoji. Icons are simple, single-color line drawings on a canvas.
- Navigation hides behind a hamburger dropdown — there is no persistent sidebar.

The core (character, activities, fuzzy, recommend) holds all the game logic; this
module only renders it. CustomTkinter/Tkinter import at module load is safe
without a display; a window is created only in :func:`run`.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from . import fuzzy, storage
from .activities import ACTIVITIES, Activity
from .character import Character
from .recommend import recommendations, top_activities_for_stat
from .stats import STATS, stat
from .titles import next_title

# --- Palette (deep, muted, intentional) ------------------------------------
BG = "#15171d"        # deep slate charcoal
SURFACE = "#1e2028"   # faint raised card
SURFACE_2 = "#262932"  # inputs / hover / row stripe
TRACK = "#111319"     # empty bar
TICK = "#2b2f3a"      # very faint segment ticks / dividers
TEXT = "#e7e9f0"
MUTED = "#99a0b2"
FAINT = "#606779"
GOLD = "#d9b26a"      # muted amber accent
GOLD_DIM = "#8f7a49"
TEAL = "#6bb39b"      # muted teal — progress / primary action
TEAL_HOVER = "#7cc4ac"
STREAK = "#d59a63"    # muted amber

SUGGESTION_LIMIT = 7
DEFAULT_MINUTES = 30
SECTIONS = ["Character", "Activities", "History", "Shop", "Adventure", "Gear"]

ctk.set_appearance_mode("dark")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """Draw a smooth rounded rectangle on a canvas and return its id."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class Tooltip:
    """A soft hover tooltip whose text is produced fresh each time."""

    def __init__(self, widget: tk.Widget, text_provider, font):
        self.widget = widget
        self.text_provider = text_provider
        self.font = font
        self.tip: tk.Toplevel | None = None
        self._after: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._cancel()
        self._after = self.widget.after(300, self._show)

    def _cancel(self):
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        text = self.text_provider()
        if not text or self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        frame = ctk.CTkFrame(self.tip, corner_radius=12, fg_color=SURFACE_2)
        frame.pack()
        ctk.CTkLabel(frame, text=text, text_color=TEXT, font=self.font,
                     justify="left", wraplength=360).pack(padx=16, pady=12)

    def _hide(self, _e=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class RoundedBar:
    """A rounded, single-color XP bar with faint segment ticks."""

    def __init__(self, parent, width, height, bg, segments=12):
        self.w, self.h, self.segments = width, height, segments
        self.canvas = tk.Canvas(parent, width=width, height=height, bg=bg,
                                highlightthickness=0, bd=0)

    def set(self, fraction: float):
        c = self.canvas
        c.delete("all")
        w, h = self.w, self.h
        r = h / 2
        frac = max(0.0, min(1.0, fraction))
        round_rect(c, 1, 1, w - 1, h - 1, r, fill=TRACK, outline="")
        if frac > 0:
            fill_w = max(h, (w - 2) * frac)
            round_rect(c, 1, 1, 1 + fill_w, h - 1, r, fill=TEAL, outline="")
        seg_w = (w - 2) / self.segments
        for i in range(1, self.segments):
            x = 1 + i * seg_w
            c.create_line(x, 4, x, h - 4, fill=TICK, width=1)


def line_icon(parent, kind: str, size: int = 64, color: str = GOLD, bg: str = BG):
    """A simple single-color line icon drawn on a canvas (Lucide-ish)."""
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
    s = size
    w = 2
    if kind == "shop":  # storefront
        c.create_line(s*.18, s*.40, s*.18, s*.82, fill=color, width=w)
        c.create_line(s*.82, s*.40, s*.82, s*.82, fill=color, width=w)
        c.create_line(s*.18, s*.82, s*.82, s*.82, fill=color, width=w)
        c.create_polygon(s*.14, s*.40, s*.24, s*.24, s*.76, s*.24, s*.86, s*.40,
                         outline=color, fill="", width=w)
        c.create_rectangle(s*.40, s*.58, s*.60, s*.82, outline=color, width=w)
    elif kind == "map":  # adventure / map pin
        c.create_oval(s*.30, s*.20, s*.70, s*.60, outline=color, width=w)
        c.create_line(s*.50, s*.60, s*.50, s*.82, fill=color, width=w)
        c.create_oval(s*.44, s*.34, s*.56, s*.46, outline=color, width=w)
    elif kind == "gear":  # shield
        c.create_line(s*.5, s*.18, s*.80, s*.30, fill=color, width=w)
        c.create_line(s*.80, s*.30, s*.72, s*.66, fill=color, width=w)
        c.create_line(s*.72, s*.66, s*.5, s*.84, fill=color, width=w)
        c.create_line(s*.5, s*.84, s*.28, s*.66, fill=color, width=w)
        c.create_line(s*.28, s*.66, s*.20, s*.30, fill=color, width=w)
        c.create_line(s*.20, s*.30, s*.5, s*.18, fill=color, width=w)
    return c


# ---------------------------------------------------------------------------
# Character sheet
# ---------------------------------------------------------------------------
class StatRow:
    def __init__(self, parent, s, row: int, fonts: dict, card_color: str):
        self.stat = s
        self.char: Character | None = None

        name_cell = ctk.CTkFrame(parent, fg_color="transparent")
        name_cell.grid(row=row, column=0, sticky="w", padx=(4, 18), pady=13)
        ctk.CTkLabel(name_cell, text=s.name, text_color=TEXT, font=fonts["stat"],
                     anchor="w").pack(anchor="w")
        self.title_lbl = ctk.CTkLabel(name_cell, text="", text_color=GOLD_DIM,
                                      font=fonts["title_small"], anchor="w")
        self.title_lbl.pack(anchor="w")

        self.level_lbl = ctk.CTkLabel(parent, text="Lv 1", text_color=GOLD,
                                      font=fonts["level"], width=54, anchor="w")
        self.level_lbl.grid(row=row, column=1, sticky="w", pady=13)

        self.bar = RoundedBar(parent, width=320, height=14, bg=card_color)
        self.bar.canvas.grid(row=row, column=2, sticky="ew", padx=16, pady=13)

        self.xp_lbl = ctk.CTkLabel(parent, text="", text_color=MUTED,
                                   font=fonts["xp"], width=110, anchor="e")
        self.xp_lbl.grid(row=row, column=3, sticky="e", padx=(6, 4), pady=13)

        Tooltip(name_cell, self._tip, fonts["tip"])
        Tooltip(self.bar.canvas, self._tip, fonts["tip"])

    def _tip(self) -> str:
        if self.char is None:
            return ""
        s, c = self.stat, self.char
        lvl = c.level(s.key)
        title = c.title(s.key) or "Unranked"
        raise_with = ", ".join(a.name for a in top_activities_for_stat(s.key, 3))
        lines = [f"{s.name} — Level {lvl}  ·  {title}", "", s.blurb, "",
                 f"Raise it with:  {raise_with}"]
        nxt = next_title(s.key, lvl)
        if nxt:
            lines.append(f"Next title:  {nxt[1]}  at Lv {nxt[0]}")
        return "\n".join(lines)

    def update(self, character: Character):
        self.char = character
        p = character.progress(self.stat.key)
        self.level_lbl.configure(text=f"Lv {p.level}")
        self.xp_lbl.configure(text=f"{p.xp_into_level} / {p.xp_for_level}")
        title = character.title(self.stat.key)
        self.title_lbl.configure(text=title or "Unranked",
                                 text_color=GOLD if title else FAINT)
        self.bar.set(p.fraction)


class CharacterView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        card = ctk.CTkFrame(self, corner_radius=18, fg_color=SURFACE)
        card.pack(fill="both", expand=True, padx=8, pady=8)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=26)
        inner.grid_columnconfigure(2, weight=1)
        self.rows = [StatRow(inner, s, i, app.fonts, SURFACE)
                     for i, s in enumerate(STATS)]

    def refresh(self):
        for row in self.rows:
            row.update(self.app.character)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
class ActivitiesView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts
        self.selected: Activity | None = None
        self._matches: list[Activity] = []

        col = ctk.CTkFrame(self, fg_color="transparent")
        col.place(relx=0.5, rely=0.04, anchor="n", relwidth=0.72)

        self.activity_var = tk.StringVar()
        self.entry = ctk.CTkEntry(col, textvariable=self.activity_var,
                                  placeholder_text="What did you do?  (start typing…)",
                                  height=48, corner_radius=14, fg_color=SURFACE,
                                  border_width=0, font=fonts["search"])
        self.entry.pack(fill="x", pady=(6, 10))
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self.do_log())

        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="minutes", text_color=MUTED,
                     font=fonts["small"]).pack(side="left", padx=(2, 10))
        self.minutes_var = tk.StringVar(value=str(DEFAULT_MINUTES))
        ctk.CTkEntry(row, textvariable=self.minutes_var, width=72, height=44,
                     corner_radius=12, fg_color=SURFACE, border_width=0,
                     justify="center", font=fonts["search"]).pack(side="left")
        ctk.CTkButton(row, text="Log", command=self.do_log, width=120, height=44,
                      corner_radius=14, fg_color=TEAL, hover_color=TEAL_HOVER,
                      text_color=BG, font=fonts["btn"]).pack(side="right")

        self.status = ctk.CTkLabel(col, text="", text_color=MUTED,
                                   font=fonts["small"], anchor="w", justify="left",
                                   wraplength=560)
        self.status.pack(fill="x", pady=(14, 2))

        # One dynamic list area: activity matches while typing, else "explore".
        self.list_head = ctk.CTkLabel(col, text="", text_color=FAINT,
                                      font=fonts["kicker"], anchor="w")
        self.list_head.pack(fill="x", pady=(18, 6))
        self.list_frame = ctk.CTkFrame(col, fg_color="transparent")
        self.list_frame.pack(fill="x")

    def _fuzzy(self):
        return fuzzy.rank(self.activity_var.get(), ACTIVITIES,
                          lambda a: a.search_terms(), limit=SUGGESTION_LIMIT)

    def _item(self, text: str, on_click):
        lbl = ctk.CTkLabel(self.list_frame, text=text, text_color=MUTED,
                           font=self.app.fonts["list"], anchor="w", height=32,
                           corner_radius=8, fg_color="transparent")
        lbl.pack(fill="x", pady=1)
        lbl.bind("<Button-1>", on_click)
        lbl.bind("<Enter>", lambda e: lbl.configure(fg_color=SURFACE_2, text_color=TEXT))
        lbl.bind("<Leave>", lambda e: lbl.configure(fg_color="transparent",
                                                    text_color=MUTED))
        return lbl

    def _clear_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

    def _show_matches(self):
        self._clear_list()
        self.list_head.configure(text="")
        for a in self._matches:
            self._item(f"   {a.name}       {'  ·  '.join(a.primary_stats())}",
                       lambda e, act=a: self._pick(act))

    def _show_explore(self):
        self._clear_list()
        self.list_head.configure(text="EXPLORE  ·  grow your weakest stats")
        for a in recommendations(self.app.character, count=6):
            self._item(f"   {a.name}", lambda e, act=a: self._pick(act))

    def _on_key(self, event=None):
        self.selected = None
        if self.activity_var.get().strip():
            self._matches = self._fuzzy()
            self._show_matches()
        else:
            self._show_explore()

    def _resolve(self):
        if self.selected is not None:
            return self.selected
        m = self._fuzzy()
        return m[0] if m else None

    def do_log(self):
        activity = self._resolve()
        if activity is None:
            self.status.configure(text="No match — try different words.", text_color=GOLD)
            return
        try:
            minutes = float(self.minutes_var.get())
        except ValueError:
            self.status.configure(text="Minutes must be a number.", text_color=GOLD)
            return
        if minutes <= 0:
            self.status.configure(text="Minutes must be more than zero.", text_color=GOLD)
            return

        result = self.app.log_activity(activity, minutes)
        gains = "   ".join(f"+{round(v)} {k}" for k, v in
                           sorted(result.gains.items(), key=lambda kv: -kv[1]) if round(v))
        msg = f"{activity.name} · {int(minutes)}m      {gains}"
        color = TEXT
        if result.bonus > 0:
            msg += f"      +{int(result.bonus * 100)}% streak"
            color = STREAK
        if result.level_ups:
            msg += "      Level up: " + ", ".join(
                f"{lu.stat} {lu.to_level}" for lu in result.level_ups)
            color = GOLD
        if result.titles:
            msg += "      New title: " + ", ".join(t.title for t in result.titles)
            color = GOLD
        self.status.configure(text=msg, text_color=color)

        self.activity_var.set("")
        self.selected = None
        self._show_explore()
        self.entry.focus_set()

    def _pick(self, activity: Activity):
        self.activity_var.set(activity.name)
        self.selected = activity
        self._clear_list()
        self.list_head.configure(text="")
        self.entry.icursor(tk.END)
        self.entry.focus_set()

    def refresh(self):
        if self.activity_var.get().strip() and self.selected is None:
            self._matches = self._fuzzy()
            self._show_matches()
        elif not self.activity_var.get().strip():
            self._show_explore()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class HistoryView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(10, 2))
        for text, w, side in [("WHEN", 150, "left"), ("ACTIVITY", 220, "left"),
                              ("MIN", 60, "left"), ("XP GAINED", 240, "left")]:
            ctk.CTkLabel(head, text=text, text_color=FAINT, font=fonts["kicker"],
                         width=w, anchor="w").pack(side="left")
        ctk.CTkLabel(head, text="STREAK", text_color=FAINT, font=fonts["kicker"],
                     anchor="w").pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        fonts = self.app.fonts
        entries = list(reversed(self.app.character.log))[:200]
        if not entries:
            ctk.CTkLabel(self.scroll, text="Nothing logged yet — head to Activities.",
                         text_color=FAINT, font=fonts["small"]).pack(pady=30)
            return
        for idx, e in enumerate(entries):
            stripe = SURFACE if idx % 2 == 0 else "transparent"
            rowf = ctk.CTkFrame(self.scroll, fg_color=stripe, corner_radius=10)
            rowf.pack(fill="x", pady=1)
            when = e.when[:16].replace("T", "  ")
            gained = ", ".join(f"+{round(v)} {k}" for k, v in
                               sorted(e.xp.items(), key=lambda kv: -kv[1]) if round(v))
            streak = f"{e.streak}-wk" if e.bonus > 0 else "—"
            cells = [(when, 150, MUTED), (e.activity, 220, TEXT),
                     (str(int(e.minutes)), 60, MUTED), (gained, 240, MUTED),
                     (streak, 80, STREAK if e.bonus > 0 else FAINT)]
            for text, w, color in cells:
                ctk.CTkLabel(rowf, text=text, text_color=color, font=fonts["list"],
                             width=w, anchor="w").pack(side="left", padx=(10, 0),
                                                       pady=7)


# ---------------------------------------------------------------------------
# Placeholders
# ---------------------------------------------------------------------------
class PlaceholderView(ctk.CTkFrame):
    def __init__(self, parent, app, icon: str, title: str, blurb: str):
        super().__init__(parent, fg_color="transparent")
        fonts = app.fonts
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.42, anchor="center")
        line_icon(inner, icon, size=72, color=GOLD, bg=BG).pack()
        ctk.CTkLabel(inner, text=title, text_color=TEXT,
                     font=fonts["h1"]).pack(pady=(14, 4))
        ctk.CTkLabel(inner, text="Coming soon", text_color=FAINT,
                     font=fonts["small"]).pack()
        ctk.CTkLabel(inner, text=blurb, text_color=MUTED, font=fonts["small"],
                     wraplength=380, justify="center").pack(pady=(12, 0))

    def refresh(self):
        pass


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------
class RPGLiferApp:
    def __init__(self, root: ctk.CTk, character: Character):
        self.root = root
        self.character = character
        self._menu: tk.Toplevel | None = None

        f = "Segoe UI"
        self.fonts = {
            "h1": ctk.CTkFont(f, 22, weight="bold"),
            "wordmark": ctk.CTkFont(f, 17, weight="bold"),
            "section": ctk.CTkFont(f, 14),
            "menu": ctk.CTkFont(f, 13),
            "stat": ctk.CTkFont(f, 15),
            "title_small": ctk.CTkFont(f, 11, slant="italic"),
            "level": ctk.CTkFont(f, 14, weight="bold"),
            "levelbadge": ctk.CTkFont(f, 16, weight="bold"),
            "xp": ctk.CTkFont(f, 12),
            "search": ctk.CTkFont(f, 14),
            "btn": ctk.CTkFont(f, 14, weight="bold"),
            "small": ctk.CTkFont(f, 12),
            "kicker": ctk.CTkFont(f, 11, weight="bold"),
            "tip": ctk.CTkFont(f, 12),
            "list": ctk.CTkFont(f, 13),
            "burger": ctk.CTkFont(f, 20),
        }

        root.title("RPG Lifer")
        root.configure(fg_color=BG)
        root.geometry("1000x660")
        root.minsize(860, 580)

        self._build_topbar()
        self.content = ctk.CTkFrame(root, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=30, pady=(4, 22))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.views = {
            "Character": CharacterView(self.content, self),
            "Activities": ActivitiesView(self.content, self),
            "History": HistoryView(self.content, self),
            "Shop": PlaceholderView(self.content, self, "shop", "Shop",
                "Spend the points you earn for going above and beyond — boosts, "
                "cosmetics, and new activity packs."),
            "Adventure": PlaceholderView(self.content, self, "map", "Adventure",
                "Quests, runs, and battles that reward reaching beyond your "
                "comfort zone."),
            "Gear": PlaceholderView(self.content, self, "gear", "Gear",
                "Equip what you find on your adventures — bonuses, not raw stats."),
        }
        for v in self.views.values():
            v.grid(row=0, column=0, sticky="nsew")

        self.show("Character")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- top bar ---
    def _build_topbar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent", height=56)
        bar.pack(fill="x", padx=28, pady=(16, 6))

        self.burger = ctk.CTkButton(bar, text="☰", width=40, height=40,
                                    corner_radius=12, fg_color="transparent",
                                    hover_color=SURFACE, text_color=TEXT,
                                    font=self.fonts["burger"], command=self._toggle_menu)
        self.burger.pack(side="left")
        ctk.CTkLabel(bar, text="RPG LIFER", text_color=GOLD,
                     font=self.fonts["wordmark"]).pack(side="left", padx=(10, 8))
        self.section_lbl = ctk.CTkLabel(bar, text="", text_color=MUTED,
                                        font=self.fonts["section"])
        self.section_lbl.pack(side="left")

        self.level_value = ctk.CTkLabel(bar, text="Lv 0", text_color=GOLD,
                                        font=self.fonts["levelbadge"])
        self.level_value.pack(side="right", padx=(0, 4))
        self.name_var = tk.StringVar(value=self.character.name)
        ctk.CTkEntry(bar, textvariable=self.name_var, width=170, height=40,
                     corner_radius=12, fg_color=SURFACE, border_width=0,
                     justify="right", font=self.fonts["section"]).pack(
            side="right", padx=(0, 16))
        self.name_var.trace_add("write", self._on_name_change)

    def _toggle_menu(self):
        if self._menu is not None and self._menu.winfo_exists():
            self._close_menu()
            return
        m = tk.Toplevel(self.root)
        m.wm_overrideredirect(True)
        x = self.burger.winfo_rootx()
        y = self.burger.winfo_rooty() + self.burger.winfo_height() + 6
        m.wm_geometry(f"+{x}+{y}")
        panel = ctk.CTkFrame(m, corner_radius=14, fg_color=SURFACE_2)
        panel.pack()
        for section in SECTIONS:
            ctk.CTkButton(panel, text=section, width=176, height=38, anchor="w",
                          corner_radius=10, fg_color="transparent",
                          hover_color=SURFACE, text_color=TEXT,
                          font=self.fonts["menu"],
                          command=lambda s=section: self._menu_pick(s)).pack(
                fill="x", padx=8, pady=2)
        m.bind("<FocusOut>", lambda e: self._close_menu())
        m.focus_set()
        self._menu = m

    def _close_menu(self):
        if self._menu is not None:
            try:
                self._menu.destroy()
            except tk.TclError:
                pass
            self._menu = None

    def _menu_pick(self, section: str):
        self._close_menu()
        self.show(section)

    # --- behavior ---
    def show(self, section: str):
        self.section_lbl.configure(text=f"·   {section}")
        view = self.views[section]
        view.refresh()
        view.tkraise()
        self.level_value.configure(text=f"Lv {self.character.overall_level()}")

    def log_activity(self, activity: Activity, minutes: float):
        result = self.character.log_activity(activity, minutes)
        storage.save(self.character)
        self.level_value.configure(text=f"Lv {self.character.overall_level()}")
        self.views["Character"].refresh()
        self.views["History"].refresh()
        self.views["Activities"].refresh()
        return result

    def _on_name_change(self, *_):
        self.character.name = self.name_var.get().strip() or "Adventurer"

    def on_close(self):
        self.character.name = self.name_var.get().strip() or "Adventurer"
        storage.save(self.character)
        self.root.destroy()


def run(character: Character | None = None) -> int:
    """Create the window and enter the Tk event loop. Returns an exit code."""
    character = character if character is not None else storage.load()
    root = ctk.CTk()
    RPGLiferApp(root, character)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
