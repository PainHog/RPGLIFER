"""The desktop GUI (CustomTkinter) — a gamified character screen, not a form.

The Character screen is built to feel like an RPG sheet: an eight-point stat
web (radar), a level ring, an evolving class name, derived combat stats, and
juicy "+XP" feedback when you log an activity. Everything is soft, rounded, and
muted; navigation hides behind a hamburger dropdown.

The core (character, activities, fuzzy, recommend, derived) holds all the logic;
this module only renders it. A window is created only in :func:`run`.
"""

from __future__ import annotations

import math
import random
import tkinter as tk

import customtkinter as ctk

from . import adventure, derived, fuzzy, shop, storage
from .activities import ACTIVITIES, Activity
from .character import ARENA_RUNS_PER_DAY, Character
from .recommend import recommendations, top_activities_for_stat
from .stats import STAT_KEYS, STATS, stat
from .titles import next_title

# --- Palette ---------------------------------------------------------------
BG = "#15171d"
SURFACE = "#1e2028"
SURFACE_2 = "#262932"
TRACK = "#111319"
TICK = "#2b2f3a"
GRID = "#2a2e39"
TEXT = "#e7e9f0"
MUTED = "#99a0b2"
FAINT = "#606779"
GOLD = "#d9b26a"
GOLD_DIM = "#8f7a49"
TEAL = "#6bb39b"
TEAL_HOVER = "#7cc4ac"
TEAL_DEEP = "#3f6f61"
STREAK = "#d59a63"
AVATAR = "#3a4250"  # placeholder hero silhouette
HERO = "#d9b26a"   # Hero points (gold)
OVER = "#6bb39b"   # Overachiever points (teal)
HP_YOU = "#6bb39b"
HP_FOE = "#d9574f"

DEFAULT_MINUTES = 30
SUGGESTION_LIMIT = 7
SECTIONS = ["Character", "Activities", "History", "Shop", "Adventure", "Gear"]

ctk.set_appearance_mode("dark")


# ---------------------------------------------------------------------------
# Animation + drawing helpers
# ---------------------------------------------------------------------------
def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)  # smoothstep


def tween(widget, duration_ms, on_frame, on_done=None):
    frames = max(1, duration_ms // 16)

    def step(i):
        try:
            on_frame(_ease(i / frames))
        except tk.TclError:
            return
        if i < frames:
            widget.after(16, lambda: step(i + 1))
        elif on_done:
            on_done()

    step(0)


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class Tooltip:
    def __init__(self, widget, text_provider, font):
        self.widget, self.text_provider, self.font = widget, text_provider, font
        self.tip = None
        self._after = None
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
                     justify="left", wraplength=340).pack(padx=15, pady=11)

    def _hide(self, _e=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class RoundedBar:
    def __init__(self, parent, width, height, bg, segments=12, fill=TEAL):
        self.w, self.h, self.segments, self.fill = width, height, segments, fill
        self.canvas = tk.Canvas(parent, width=width, height=height, bg=bg,
                                highlightthickness=0, bd=0)

    def set(self, fraction):
        c = self.canvas
        c.delete("all")
        w, h, r = self.w, self.h, self.h / 2
        frac = max(0.0, min(1.0, fraction))
        round_rect(c, 1, 1, w - 1, h - 1, r, fill=TRACK, outline="")
        if frac > 0:
            round_rect(c, 1, 1, 1 + max(h, (w - 2) * frac), h - 1, r,
                       fill=self.fill, outline="")
        if self.segments:
            seg = (w - 2) / self.segments
            for i in range(1, self.segments):
                c.create_line(1 + i * seg, 4, 1 + i * seg, h - 4, fill=TICK, width=1)


class RadarChart:
    """An eight-point stat web with hover tooltips on each axis."""

    def __init__(self, parent, app, size=320):
        self.app = app
        self.size = size
        self.cx = size / 2
        self.cy = size / 2 + 2
        self.R = size / 2 - 60
        self.canvas = tk.Canvas(parent, width=size, height=size, bg=SURFACE,
                                highlightthickness=0, bd=0)
        self.disp = {k: 0.0 for k in STAT_KEYS}  # currently drawn levels
        self._gen = 0
        self._labels = {}
        for i, s in enumerate(STATS):
            vx, vy = self._point(i, self.R + 20)
            lbl = ctk.CTkLabel(self.canvas, text=s.name, text_color=MUTED,
                               font=app.fonts["radar"], fg_color="transparent")
            self.canvas.create_window(vx, vy, window=lbl)
            Tooltip(lbl, lambda key=s.key: self._tip(key), app.fonts["tip"])
            self._labels[s.key] = lbl

    def _point(self, i, radius):
        theta = math.radians(-90 + i * 45)
        return self.cx + radius * math.cos(theta), self.cy + radius * math.sin(theta)

    def _tip(self, key):
        c = self.app.character
        s = stat(key)
        lvl = c.level(key)
        title = c.title(key) or "Unranked"
        raise_with = ", ".join(a.name for a in top_activities_for_stat(key, 3))
        lines = [f"{s.name} — Level {lvl}  ·  {title}", "", s.blurb, "",
                 f"Raise it with:  {raise_with}"]
        nxt = next_title(key, lvl)
        if nxt:
            lines.append(f"Next title:  {nxt[1]}  at Lv {nxt[0]}")
        return "\n".join(lines)

    def render(self):
        c = self.canvas
        c.delete("web")
        # 0–100 mastery scale; if any stat has prestiged past 100, grow the cap
        # so the web keeps showing relative shape.
        cap = max(100.0, max(self.disp.values()) if self.disp else 100.0)
        # concentric grid octagons
        for ring in (0.25, 0.5, 0.75, 1.0):
            pts = []
            for i in range(len(STAT_KEYS)):
                x, y = self._point(i, self.R * ring)
                pts += [x, y]
            c.create_polygon(pts, outline=GRID, fill="", width=1, tags="web")
        # axis spokes
        for i in range(len(STAT_KEYS)):
            x, y = self._point(i, self.R)
            c.create_line(self.cx, self.cy, x, y, fill=GRID, width=1, tags="web")
        # data polygon
        pts, dots = [], []
        for i, k in enumerate(STAT_KEYS):
            frac = min(1.0, self.disp[k] / cap)
            x, y = self._point(i, self.R * frac)
            pts += [x, y]
            dots.append((x, y))
        if len(pts) >= 6:
            c.create_polygon(pts, outline=TEAL, fill=TEAL, width=2,
                             stipple="gray50", tags="web")
        for x, y in dots:
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=TEAL, outline="",
                          tags="web")
        c.tag_lower("web")  # keep axis labels (windows) on top

    def set_levels(self, target: dict, animate=True):
        self._gen += 1
        gen = self._gen
        start = dict(self.disp)
        target = {k: float(target.get(k, 0)) for k in STAT_KEYS}
        if not animate:
            self.disp = dict(target)
            self.render()
            return

        def frame(t):
            if gen != self._gen:
                return
            self.disp = {k: start[k] + (target[k] - start[k]) * t for k in STAT_KEYS}
            self.render()

        def done():
            if gen != self._gen:
                return
            self.disp = dict(target)
            self.render()

        tween(self.canvas, 420, frame, on_done=done)


class LevelRing:
    """A hero avatar inside a gold progress ring, with a level badge."""

    def __init__(self, parent, app, size=104):
        self.app = app
        self.size = size
        self.canvas = tk.Canvas(parent, width=size, height=size, bg=SURFACE,
                                highlightthickness=0, bd=0)
        # Level badge overlaps the bottom of the ring.
        self._badge = ctk.CTkLabel(self.canvas, text="Lv 1", text_color=BG,
                                   font=app.fonts["ringbadge"], fg_color=GOLD,
                                   corner_radius=9, width=44, height=20)
        self.canvas.create_window(size / 2, size - 8, window=self._badge)

    def _avatar(self):
        c = self.canvas
        cx = self.size / 2
        cy = self.size / 2 - 4
        # head
        c.create_oval(cx - 11, cy - 20, cx + 11, cy + 2, fill=AVATAR, outline="",
                      tags="ring")
        # shoulders / torso
        round_rect(c, cx - 19, cy + 5, cx + 19, cy + 30, 12, fill=AVATAR,
                   outline="")

    def set(self, level, fraction):
        c = self.canvas
        c.delete("ring")
        pad = 7
        c.create_oval(pad, pad, self.size - pad, self.size - pad, outline=GRID,
                      width=6, tags="ring")
        if fraction > 0:
            c.create_arc(pad, pad, self.size - pad, self.size - pad, start=90,
                         extent=-359.9 * max(0.03, min(1.0, fraction)), style="arc",
                         outline=GOLD, width=6, tags="ring")
        self._avatar()
        c.tag_lower("ring")
        self._badge.configure(text=f"Lv {level}")


def line_icon(parent, kind, size=64, color=GOLD, bg=BG):
    c = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
    s, w = size, 2
    if kind == "shop":
        c.create_line(s*.18, s*.40, s*.18, s*.82, fill=color, width=w)
        c.create_line(s*.82, s*.40, s*.82, s*.82, fill=color, width=w)
        c.create_line(s*.18, s*.82, s*.82, s*.82, fill=color, width=w)
        c.create_polygon(s*.14, s*.40, s*.24, s*.24, s*.76, s*.24, s*.86, s*.40,
                         outline=color, fill="", width=w)
        c.create_rectangle(s*.40, s*.58, s*.60, s*.82, outline=color, width=w)
    elif kind == "map":
        c.create_oval(s*.30, s*.20, s*.70, s*.60, outline=color, width=w)
        c.create_line(s*.50, s*.60, s*.50, s*.82, fill=color, width=w)
        c.create_oval(s*.44, s*.34, s*.56, s*.46, outline=color, width=w)
    elif kind == "gear":  # a shield outline
        pts = [(.5, .18), (.8, .30), (.72, .66), (.5, .84), (.28, .66), (.2, .30)]
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            c.create_line(s*x1, s*y1, s*x2, s*y2, fill=color, width=w)
    return c


# ---------------------------------------------------------------------------
# Character screen
# ---------------------------------------------------------------------------
class StatRow:
    def __init__(self, parent, s, row, fonts):
        self.stat = s
        self.char = None
        self.target = 0.0
        self.shown = 0.0

        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=row, column=0, sticky="w", padx=(2, 12), pady=2)
        ctk.CTkLabel(cell, text=s.name, text_color=TEXT, font=fonts["stat"],
                     anchor="w", height=20).pack(anchor="w")
        self.title_lbl = ctk.CTkLabel(cell, text="", text_color=GOLD_DIM,
                                      font=fonts["title_small"], anchor="w", height=15)
        self.title_lbl.pack(anchor="w")

        self.level_lbl = ctk.CTkLabel(parent, text="Lv 1", text_color=GOLD,
                                      font=fonts["level"], width=82, anchor="w",
                                      height=20)
        self.level_lbl.grid(row=row, column=1, sticky="w", pady=2)
        self.bar = RoundedBar(parent, width=150, height=13, bg=SURFACE)
        self.bar.canvas.grid(row=row, column=2, sticky="ew", padx=10, pady=2)
        self.xp_lbl = ctk.CTkLabel(parent, text="", text_color=FAINT,
                                   font=fonts["xp"], width=92, anchor="e", height=20)
        self.xp_lbl.grid(row=row, column=3, sticky="e", padx=(4, 2), pady=2)

        Tooltip(cell, self._tip, fonts["tip"])

    def _tip(self):
        if self.char is None:
            return ""
        s, c = self.stat, self.char
        lvl = c.level(s.key)
        title = c.title(s.key) or "Unranked"
        stars = c.stars(s.key)
        star_txt = f"★{stars} · " if stars else ""
        raise_with = ", ".join(a.name for a in top_activities_for_stat(s.key, 3))
        lines = [f"{s.name} — {star_txt}Level {lvl}  ·  {title}", "", s.blurb, "",
                 f"Raise it with:  {raise_with}"]
        eff = c.effective_level(s.key)
        nxt = next_title(s.key, eff)
        if nxt:
            lines.append(f"Next title:  {nxt[1]}  at Lv {nxt[0]}")
        return "\n".join(lines)

    def update_labels(self, character):
        self.char = character
        p = character.progress(self.stat.key)
        self.target = p.fraction
        stars = character.stars(self.stat.key)
        star_txt = f"★{stars}  " if stars else ""
        self.level_lbl.configure(text=f"{star_txt}Lv {p.level}")
        self.xp_lbl.configure(text=f"{p.xp_into_level}/{p.xp_for_level}")
        title = character.title(self.stat.key)
        self.title_lbl.configure(text=title or "Unranked",
                                 text_color=GOLD if title else FAINT)


class CharacterView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts

        # Hero header ------------------------------------------------------
        header = ctk.CTkFrame(self, corner_radius=18, fg_color=SURFACE)
        header.pack(fill="x", padx=8, pady=(8, 10))
        top = ctk.CTkFrame(header, fg_color="transparent")
        top.pack(fill="x", padx=22, pady=(16, 6))
        self.ring = LevelRing(top, app, size=104)
        self.ring.canvas.pack(side="left", padx=(0, 20), pady=2)
        namecol = ctk.CTkFrame(top, fg_color="transparent")
        namecol.pack(side="left", anchor="w")
        self.name_lbl = ctk.CTkLabel(namecol, text="", text_color=TEXT,
                                     font=fonts["hero_name"], anchor="w")
        self.name_lbl.pack(anchor="w", pady=(8, 0))
        self.class_lbl = ctk.CTkLabel(namecol, text="", text_color=GOLD,
                                      font=fonts["hero_class"], anchor="w")
        self.class_lbl.pack(anchor="w")
        # Derived combat stats — a compact horizontal chip row.
        self.chips = ctk.CTkFrame(header, fg_color="transparent")
        self.chips.pack(fill="x", padx=22, pady=(2, 16))

        # Body: radar + stat list -----------------------------------------
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        radar_card = ctk.CTkFrame(body, corner_radius=18, fg_color=SURFACE)
        radar_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.radar = RadarChart(radar_card, app, size=320)
        self.radar.canvas.pack(padx=14, pady=14)

        list_card = ctk.CTkFrame(body, corner_radius=18, fg_color=SURFACE)
        list_card.grid(row=0, column=1, sticky="nsew")
        inner = ctk.CTkFrame(list_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)
        inner.grid_columnconfigure(2, weight=1)
        self.rows = [StatRow(inner, s, i, fonts) for i, s in enumerate(STATS)]
        self._gen = 0

    def _chip(self, name, value):
        f = ctk.CTkFrame(self.chips, corner_radius=12, fg_color=SURFACE_2)
        f.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f, text=name, text_color=MUTED,
                     font=self.app.fonts["chip_k"]).pack(side="left", padx=(11, 6),
                                                         pady=5)
        ctk.CTkLabel(f, text=str(value), text_color=TEAL,
                     font=self.app.fonts["chip_v"]).pack(side="left", padx=(0, 11))

    def refresh(self, animate=False):
        c = self.app.character
        self.name_lbl.configure(text=c.name)
        self.class_lbl.configure(text=derived.character_class(c))
        avg = sum(c.progress(k).fraction for k in STAT_KEYS) / len(STAT_KEYS)
        level = c.overall_level()
        if not animate:
            self.ring.set(level, avg)

        for w in self.chips.winfo_children():
            w.destroy()
        d = derived.compute(c)
        for ds in derived.DERIVED:
            self._chip(ds.name, d[ds.key])

        for row in self.rows:
            row.update_labels(c)
        self.radar.set_levels({k: c.effective_level(k) for k in STAT_KEYS},
                              animate=animate)

        self._gen += 1
        gen = self._gen
        if animate:
            starts = {id(r): r.shown for r in self.rows}

            def frame(t):
                if gen != self._gen:
                    return
                for r in self.rows:
                    r.shown = starts[id(r)] + (r.target - starts[id(r)]) * t
                    r.bar.set(r.shown)
                self.ring.set(level, avg * t)

            def done():
                if gen != self._gen:
                    return
                for r in self.rows:
                    r.shown = r.target
                    r.bar.set(r.target)
                self.ring.set(level, avg)

            tween(self, 420, frame, on_done=done)
        else:
            for r in self.rows:
                r.shown = r.target
                r.bar.set(r.target)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
class ActivitiesView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts
        self.selected = None
        self._matches = []

        col = ctk.CTkFrame(self, fg_color="transparent")
        col.place(relx=0.5, rely=0.05, anchor="n", relwidth=0.74)

        self.activity_var = tk.StringVar()
        self.entry = ctk.CTkEntry(col, textvariable=self.activity_var,
                                  placeholder_text="What did you do?  (start typing…)",
                                  height=50, corner_radius=14, fg_color=SURFACE,
                                  border_width=0, font=fonts["search"])
        self.entry.pack(fill="x", pady=(4, 12))
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self.do_log())

        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="minutes", text_color=MUTED,
                     font=fonts["small"]).pack(side="left", padx=(2, 10))
        self.minutes_var = tk.StringVar(value=str(DEFAULT_MINUTES))
        ctk.CTkEntry(row, textvariable=self.minutes_var, width=74, height=44,
                     corner_radius=12, fg_color=SURFACE, border_width=0,
                     justify="center", font=fonts["search"]).pack(side="left")
        self.log_btn = ctk.CTkButton(row, text="Log", command=self.do_log, width=130,
                                     height=44, corner_radius=14, fg_color=TEAL,
                                     hover_color=TEAL_HOVER, text_color=BG,
                                     font=fonts["btn"])
        self.log_btn.pack(side="right")

        self.list_head = ctk.CTkLabel(col, text="", text_color=FAINT,
                                      font=fonts["kicker"], anchor="w")
        self.list_head.pack(fill="x", pady=(22, 6))
        self.list_frame = ctk.CTkFrame(col, fg_color="transparent")
        self.list_frame.pack(fill="x")

    def _fuzzy(self):
        return fuzzy.rank(self.activity_var.get(), ACTIVITIES,
                          lambda a: a.search_terms(), limit=SUGGESTION_LIMIT)

    def _item(self, text, on_click):
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

    def _pick(self, activity):
        self.activity_var.set(activity.name)
        self.selected = activity
        self._clear_list()
        self.list_head.configure(text="")
        self.entry.icursor(tk.END)
        self.entry.focus_set()

    def _resolve(self):
        if self.selected is not None:
            return self.selected
        m = self._fuzzy()
        return m[0] if m else None

    def refresh(self):
        if self.activity_var.get().strip() and self.selected is None:
            self._matches = self._fuzzy()
            self._show_matches()
        elif not self.activity_var.get().strip():
            self._show_explore()

    def do_log(self):
        activity = self._resolve()
        if activity is None:
            self._flash("No match — try different words.", GOLD)
            return
        try:
            minutes = float(self.minutes_var.get())
        except ValueError:
            self._flash("Minutes must be a number.", GOLD)
            return
        if minutes <= 0:
            self._flash("Minutes must be more than zero.", GOLD)
            return

        result = self.app.log_activity(activity, minutes)
        self._burst(activity, minutes, result)
        self.app.celebrate(result)  # no-op unless a level-up / new title happened
        self.activity_var.set("")
        self.selected = None
        self._show_explore()
        self.entry.focus_set()

    def _flash(self, text, color):
        self.list_head.configure(text=text, text_color=color)

    def _burst(self, activity, minutes, result):
        """A floating reward popup — the little hit of fun on every log."""
        pop = ctk.CTkFrame(self, corner_radius=16, fg_color=SURFACE_2)
        gains = "    ".join(f"+{round(v)} {stat(k).name}" for k, v in
                            sorted(result.gains.items(), key=lambda kv: -kv[1])
                            if round(v))
        ctk.CTkLabel(pop, text=f"{activity.name}  ·  {int(minutes)}m",
                     text_color=MUTED, font=self.app.fonts["small"]).pack(
            padx=22, pady=(12, 2))
        ctk.CTkLabel(pop, text=gains, text_color=TEAL,
                     font=self.app.fonts["burst"]).pack(padx=22, pady=(0, 4))
        if result.bonus > 0:
            ctk.CTkLabel(pop, text=f"🔥  {result.streak}-week streak  ·  "
                         f"+{int(result.bonus*100)}% XP", text_color=STREAK,
                         font=self.app.fonts["small"]).pack(padx=22)
        pts = []
        if result.hero_gain:
            pts.append(f"◆ +{result.hero_gain} Hero")
        if result.overachiever_gain:
            pts.append(f"✦ +{result.overachiever_gain} Overachiever")
        if pts:
            ctk.CTkLabel(pop, text="   ".join(pts), text_color=HERO,
                         font=self.app.fonts["small"]).pack(padx=22)
        for su in result.star_ups:
            ctk.CTkLabel(pop, text=f"★  MASTERY —  {stat(su.stat).name}  ★{su.star}",
                         text_color=GOLD, font=self.app.fonts["burst"]).pack(padx=22)
        for lu in result.level_ups:
            ctk.CTkLabel(pop, text=f"LEVEL UP —  {stat(lu.stat).name}  {lu.to_level}",
                         text_color=GOLD, font=self.app.fonts["burst"]).pack(padx=22)
        for t in result.titles:
            ctk.CTkLabel(pop, text=f"NEW TITLE —  “{t.title}”", text_color=GOLD,
                         font=self.app.fonts["small"]).pack(padx=22, pady=(0, 2))
        pad = ctk.CTkLabel(pop, text="", font=self.app.fonts["small"])
        pad.pack(pady=1)

        start_y = 0.80
        pop.place(relx=0.5, rely=start_y, anchor="center")

        def frame(t):
            pop.place_configure(rely=start_y - 0.08 * t)

        tween(self, 260, frame)
        self.after(1500, lambda: pop.winfo_exists() and pop.destroy())


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
        for text, w in [("WHEN", 150), ("ACTIVITY", 220), ("MIN", 60),
                        ("XP GAINED", 250)]:
            ctk.CTkLabel(head, text=text, text_color=FAINT, font=fonts["kicker"],
                         width=w, anchor="w").pack(side="left")
        ctk.CTkLabel(head, text="STREAK", text_color=FAINT, font=fonts["kicker"],
                     anchor="w").pack(side="left")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        entries = list(reversed(self.app.character.log))[:200]
        if not entries:
            ctk.CTkLabel(self.scroll, text="Nothing logged yet — head to Activities.",
                         text_color=FAINT, font=self.app.fonts["small"]).pack(pady=30)
            return
        for idx, e in enumerate(entries):
            stripe = SURFACE if idx % 2 == 0 else "transparent"
            rowf = ctk.CTkFrame(self.scroll, fg_color=stripe, corner_radius=10)
            rowf.pack(fill="x", pady=1)
            when = e.when[:16].replace("T", "  ")
            gained = ", ".join(f"+{round(v)} {k}" for k, v in
                               sorted(e.xp.items(), key=lambda kv: -kv[1]) if round(v))
            streak = f"{e.streak}-wk" if e.bonus > 0 else "—"
            for text, w, color in [(when, 150, MUTED), (e.activity, 220, TEXT),
                                   (str(int(e.minutes)), 60, MUTED),
                                   (gained, 250, MUTED),
                                   (streak, 80, STREAK if e.bonus > 0 else FAINT)]:
                ctk.CTkLabel(rowf, text=text, text_color=color,
                             font=self.app.fonts["list"], width=w, anchor="w").pack(
                    side="left", padx=(10, 0), pady=7)


# ---------------------------------------------------------------------------
# Adventure — the Arena auto-battle
# ---------------------------------------------------------------------------
class AdventureView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts
        self._battle = None
        self._round_i = 0
        self._playing = False

        card = ctk.CTkFrame(self, corner_radius=18, fg_color=SURFACE)
        card.place(relx=0.5, rely=0.03, anchor="n", relwidth=0.8)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(head, text="THE ARENA", text_color=MUTED,
                     font=fonts["kicker"]).pack(side="left")
        self.energy_lbl = ctk.CTkLabel(head, text="", text_color=HERO,
                                       font=fonts["kicker"])
        self.energy_lbl.pack(side="right")

        # Foe row
        self.foe_lbl = ctk.CTkLabel(card, text="", text_color=TEXT, font=fonts["stat"],
                                    anchor="w")
        self.foe_lbl.pack(fill="x", padx=24, pady=(8, 2))
        self.foe_bar = RoundedBar(card, width=560, height=14, bg=SURFACE,
                                  segments=0, fill=HP_FOE)
        self.foe_bar.canvas.pack(padx=24, anchor="w")
        # You row
        self.you_lbl = ctk.CTkLabel(card, text="", text_color=TEXT, font=fonts["stat"],
                                    anchor="w")
        self.you_lbl.pack(fill="x", padx=24, pady=(12, 2))
        self.you_bar = RoundedBar(card, width=560, height=14, bg=SURFACE,
                                  segments=0, fill=HP_YOU)
        self.you_bar.canvas.pack(padx=24, anchor="w")

        self.fight_btn = ctk.CTkButton(card, text="Enter the Arena", command=self._go,
                                       height=46, corner_radius=14, fg_color=HERO,
                                       hover_color="#e6c079", text_color=BG,
                                       font=fonts["btn"])
        self.fight_btn.pack(pady=16)

        self.log = ctk.CTkTextbox(card, height=150, fg_color=TRACK, text_color=MUTED,
                                  font=fonts["list"], corner_radius=12,
                                  activate_scrollbars=True)
        self.log.pack(fill="x", padx=24, pady=(0, 20))
        self.log.configure(state="disabled")

    def _log(self, text, clear=False):
        self.log.configure(state="normal")
        if clear:
            self.log.delete("1.0", "end")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _hp(self, who_lbl, bar, name, hp, mx, color):
        who_lbl.configure(text=f"{name}    {max(0, hp)} / {mx}")
        bar.set(hp / mx if mx else 0)

    def refresh(self):
        c = self.app.character
        energy = c.arena_energy()
        self.energy_lbl.configure(text=f"⚡ {energy}/{ARENA_RUNS_PER_DAY} today")
        d = derived.compute(c)
        if not self._playing:
            self._hp(self.you_lbl, self.you_bar, c.name, d["HP"], d["HP"], HP_YOU)
            self.foe_lbl.configure(text="A foe awaits…")
            self.foe_bar.set(0)
        if energy <= 0 and not self._playing:
            self.fight_btn.configure(text="No energy — resets tomorrow", state="disabled",
                                     fg_color=SURFACE_2)
        elif not self._playing:
            self.fight_btn.configure(text="Enter the Arena", state="normal",
                                     fg_color=HERO)

    def _go(self):
        c = self.app.character
        if self._playing or c.arena_energy() <= 0:
            return
        c.spend_arena_energy()
        self.energy_lbl.configure(text=f"⚡ {c.arena_energy()}/{ARENA_RUNS_PER_DAY} today")
        combat = c.consume_combat_bonuses()
        self._battle = adventure.simulate(c, combat_bonus=combat)
        b = self._battle
        self._playing = True
        self._round_i = 0
        self.fight_btn.configure(state="disabled", fg_color=SURFACE_2)
        boost = "   (+Power boost!)" if combat else ""
        self._log(f"⚔  You face a {b.foe_name}  (Lv {b.foe_level}){boost}", clear=True)
        self._hp(self.foe_lbl, self.foe_bar, b.foe_name, b.foe_max_hp, b.foe_max_hp, HP_FOE)
        self._hp(self.you_lbl, self.you_bar, c.name, b.you_max_hp, b.you_max_hp, HP_YOU)
        self.app.root.after(500, self._step)

    def _step(self):
        b = self._battle
        if self._round_i >= len(b.rounds):
            return self._finish()
        r = b.rounds[self._round_i]
        self._round_i += 1
        if r.attacker == "you":
            self._hp(self.foe_lbl, self.foe_bar, b.foe_name, r.foe_hp, b.foe_max_hp, HP_FOE)
            crit = "  CRIT!" if r.crit else ""
            self._log(f"  You hit for {r.damage}{crit}")
        else:
            self._hp(self.you_lbl, self.you_bar, self.app.character.name, r.you_hp,
                     b.you_max_hp, HP_YOU)
            crit = "  CRIT!" if r.crit else ""
            self._log(f"  {b.foe_name} hits you for {r.damage}{crit}")
        self.app.root.after(360, self._step)

    def _finish(self):
        b = self._battle
        c = self.app.character
        self._playing = False
        if b.won:
            c.hero_points += b.reward
            self._log(f"★  Victory!  +{b.reward} Hero points")
        else:
            c.hero_points += b.reward
            self._log(f"✕  Defeated…  +{b.reward} Hero points for trying")
        storage.save(c)
        self.app.refresh_points()
        self.refresh()


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------
class ShopView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        fonts = app.fonts
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        self.outer = outer

        head = ctk.CTkFrame(outer, fg_color="transparent")
        head.pack(fill="x", padx=6, pady=(4, 2))
        ctk.CTkLabel(head, text="SHOP", text_color=MUTED,
                     font=fonts["kicker"]).pack(side="left")
        self.bal_lbl = ctk.CTkLabel(head, text="", text_color=TEXT,
                                    font=fonts["kicker"])
        self.bal_lbl.pack(side="right")
        ctk.CTkLabel(outer, text="Spend points on temporary boosts — never on stats.",
                     text_color=FAINT, font=fonts["small"], anchor="w").pack(
            fill="x", padx=6, pady=(0, 8))

        self.items_box = ctk.CTkFrame(outer, fg_color="transparent")
        self.items_box.pack(fill="x")
        self.active_head = ctk.CTkLabel(outer, text="", text_color=MUTED,
                                        font=fonts["kicker"], anchor="w")
        self.active_head.pack(fill="x", padx=6, pady=(16, 4))
        self.active_box = ctk.CTkFrame(outer, fg_color="transparent")
        self.active_box.pack(fill="x")
        self.status = ctk.CTkLabel(outer, text="", text_color=MUTED,
                                   font=fonts["small"], anchor="w")
        self.status.pack(fill="x", padx=6, pady=(8, 0))

    def _buy(self, item):
        if shop.purchase(self.app.character, item):
            storage.save(self.app.character)
            self.app.refresh_points()
            self.status.configure(text=f"Bought {item.name}.", text_color=OVER)
            self.refresh()
        else:
            self.status.configure(text=f"Not enough {item.currency} points for "
                                  f"{item.name}.", text_color=HERO)

    def refresh(self):
        c = self.app.character
        fonts = self.app.fonts
        self.bal_lbl.configure(
            text=f"◆ {c.hero_points} Hero      ✦ {c.overachiever_points} Overachiever")
        for w in self.items_box.winfo_children():
            w.destroy()
        for item in shop.ITEMS:
            row = ctk.CTkFrame(self.items_box, corner_radius=14, fg_color=SURFACE)
            row.pack(fill="x", padx=6, pady=5)
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=16, pady=12)
            ctk.CTkLabel(left, text=item.name, text_color=TEXT,
                         font=fonts["list_b"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(left, text=item.desc, text_color=MUTED, font=fonts["small"],
                         anchor="w").pack(anchor="w")
            cur_col = HERO if item.currency == "hero" else OVER
            sym = "◆" if item.currency == "hero" else "✦"
            ctk.CTkButton(row, text=f"{sym} {item.cost}", width=90, height=40,
                          corner_radius=12,
                          fg_color=cur_col if shop.can_afford(c, item) else SURFACE_2,
                          text_color=BG if shop.can_afford(c, item) else FAINT,
                          hover_color=cur_col, font=fonts["btn"],
                          command=lambda it=item: self._buy(it)).pack(
                side="right", padx=16)

        for w in self.active_box.winfo_children():
            w.destroy()
        active = c.active_bonuses()
        self.active_head.configure(text=f"ACTIVE BOOSTS ({len(active)})")
        if not active:
            ctk.CTkLabel(self.active_box, text="None active — buy one above.",
                         text_color=FAINT, font=fonts["small"], anchor="w").pack(
                fill="x", padx=6)
        for b in active:
            if b.kind == "xp_mult":
                tail = "time-limited"
            else:
                tail = f"{b.uses_left} fights left"
            ctk.CTkLabel(self.active_box,
                         text=f"◆  {b.name}  ·  +{int(b.magnitude*100)}%  ·  {tail}",
                         text_color=OVER, font=fonts["small"], anchor="w").pack(
                fill="x", padx=6, pady=1)


class PlaceholderView(ctk.CTkFrame):
    def __init__(self, parent, app, icon, title, blurb):
        super().__init__(parent, fg_color="transparent")
        fonts = app.fonts
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.42, anchor="center")
        line_icon(inner, icon, size=72, color=GOLD, bg=BG).pack()
        ctk.CTkLabel(inner, text=title, text_color=TEXT, font=fonts["h1"]).pack(
            pady=(14, 4))
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
    def __init__(self, root, character):
        self.root = root
        self.character = character
        self._menu = None
        f = "Segoe UI"
        self.fonts = {
            "h1": ctk.CTkFont(f, 22, weight="bold"),
            "wordmark": ctk.CTkFont(f, 17, weight="bold"),
            "section": ctk.CTkFont(f, 14),
            "menu": ctk.CTkFont(f, 13),
            "hero_name": ctk.CTkFont(f, 22, weight="bold"),
            "hero_class": ctk.CTkFont(f, 14),
            "ring": ctk.CTkFont(f, 26, weight="bold"),
            "ringsub": ctk.CTkFont(f, 9, weight="bold"),
            "ringbadge": ctk.CTkFont(f, 12, weight="bold"),
            "chip_k": ctk.CTkFont(f, 11),
            "chip_v": ctk.CTkFont(f, 13, weight="bold"),
            "radar": ctk.CTkFont(f, 11),
            "stat": ctk.CTkFont(f, 14),
            "title_small": ctk.CTkFont(f, 10, slant="italic"),
            "level": ctk.CTkFont(f, 13, weight="bold"),
            "xp": ctk.CTkFont(f, 10),
            "search": ctk.CTkFont(f, 14),
            "btn": ctk.CTkFont(f, 14, weight="bold"),
            "burst": ctk.CTkFont(f, 15, weight="bold"),
            "small": ctk.CTkFont(f, 12),
            "kicker": ctk.CTkFont(f, 11, weight="bold"),
            "tip": ctk.CTkFont(f, 12),
            "list": ctk.CTkFont(f, 13),
            "list_b": ctk.CTkFont(f, 13, weight="bold"),
            "burger": ctk.CTkFont(f, 20),
            "levelbadge": ctk.CTkFont(f, 16, weight="bold"),
        }

        root.title("RPG Lifer")
        root.configure(fg_color=BG)
        root.geometry("1080x760")
        root.minsize(940, 680)

        self._build_topbar()
        self.content = ctk.CTkFrame(root, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=26, pady=(2, 18))
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.views = {
            "Character": CharacterView(self.content, self),
            "Activities": ActivitiesView(self.content, self),
            "History": HistoryView(self.content, self),
            "Shop": ShopView(self.content, self),
            "Adventure": AdventureView(self.content, self),
            "Gear": PlaceholderView(self.content, self, "gear", "Gear",
                "Equip what you find on adventures — bonuses to your combat stats, "
                "never to your real-life stats."),
        }
        for v in self.views.values():
            v.grid(row=0, column=0, sticky="nsew")
        self.show("Character")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent", height=54)
        bar.pack(fill="x", padx=26, pady=(14, 4))
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
        self.points_lbl = ctk.CTkLabel(bar, text="", text_color=MUTED,
                                       font=self.fonts["section"])
        self.points_lbl.pack(side="right", padx=(0, 18))
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
            ctk.CTkButton(panel, text=section, width=180, height=38, anchor="w",
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

    def _menu_pick(self, section):
        self._close_menu()
        self.show(section)

    def show(self, section):
        self.section_lbl.configure(text=f"·   {section}")
        view = self.views[section]
        if section == "Character":
            view.refresh(animate=True)
        else:
            view.refresh()
        view.tkraise()
        self.level_value.configure(text=f"Lv {self.character.overall_level()}")
        self.refresh_points()

    def refresh_points(self):
        c = self.character
        self.points_lbl.configure(text=f"◆ {c.hero_points}   ✦ {c.overachiever_points}")

    def log_activity(self, activity, minutes):
        result = self.character.log_activity(activity, minutes)
        storage.save(self.character)
        self.level_value.configure(text=f"Lv {self.character.overall_level()}")
        self.refresh_points()
        self.views["Character"].refresh(animate=False)
        self.views["History"].refresh()
        return result

    def celebrate(self, result):
        """A centered pop with a gold particle burst for stars / level-ups / titles."""
        if not (result.star_ups or result.level_ups or result.titles):
            return
        f = "Segoe UI"
        if result.star_ups:
            su = result.star_ups[0]
            head = "★  MASTERY  ★"
            detail, sub = stat(su.stat).name, f"Star {su.star}"
            n_parts = 34
        elif result.titles:
            head, detail = "NEW TITLE!", f"“{result.titles[0].title}”"
            sub, n_parts = stat(result.titles[0].stat).name, 20
        else:
            lu = result.level_ups[0]
            head, detail, sub = "LEVEL UP!", f"{stat(lu.stat).name}  {lu.to_level}", ""
            n_parts = 20

        card = ctk.CTkFrame(self.content, corner_radius=20, fg_color=SURFACE_2)
        cv = tk.Canvas(card, width=340, height=170, bg=SURFACE_2,
                       highlightthickness=0, bd=0)
        cv.pack(padx=6, pady=6)
        parts = [(random.uniform(0, 2 * math.pi), random.uniform(45, 120))
                 for _ in range(n_parts)]
        dots = [cv.create_oval(170, 70, 170, 70, fill=GOLD, outline="")
                for _ in parts]
        cv.create_text(170, 60, text=head, fill=GOLD, font=(f, 26, "bold"))
        cv.create_text(170, 98, text=detail, fill=TEXT, font=(f, 19, "bold"))
        if sub:
            cv.create_text(170, 126, text=sub, fill=MUTED, font=(f, 12))

        def frame(t):
            for (ang, dist), d in zip(parts, dots):
                r = dist * t
                x, y = 170 + r * math.cos(ang), 70 + r * math.sin(ang)
                cv.coords(d, x - 2, y - 2, x + 2, y + 2)

        tween(card, 520, frame)
        card.place(relx=0.5, rely=0.46, anchor="center")
        card.bind("<Button-1>", lambda e: card.destroy())
        self.root.after(1600, lambda: card.winfo_exists() and card.destroy())

    def _on_name_change(self, *_):
        self.character.name = self.name_var.get().strip() or "Adventurer"
        self.views["Character"].name_lbl.configure(text=self.character.name)

    def on_close(self):
        self.character.name = self.name_var.get().strip() or "Adventurer"
        storage.save(self.character)
        self.root.destroy()


def run(character=None):
    character = character if character is not None else storage.load()
    root = ctk.CTk()
    RPGLiferApp(root, character)
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
