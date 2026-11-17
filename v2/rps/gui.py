"""Tkinter interface. All game decisions live in rules/ai/game; this only draws."""
from __future__ import annotations

import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Optional

from .ai import OPPONENTS
from .game import Match, Round
from .rules import RULESETS, Outcome
from .stats import StatsStore

# Card images live next to this file, so the game finds them wherever it's installed.
ASSETS = Path(__file__).parent / "assets"

# Colour palette: dark background with the yellow of the cards as accent.
BG = "#1d1d24"
PANEL = "#2a2a34"
TEXT = "#f2f2f2"
MUTED = "#9a9aa8"
ACCENT = "#ffea00"
COLORS = {Outcome.WIN: "#4ade80", Outcome.LOSE: "#f87171", Outcome.DRAW: "#a1a1aa"}
FONT = "Helvetica"

TARGETS = ("3", "5", "10")  # options of the "First to" menu
# Card-shuffle animation before the CPU's move is shown: 8 frames x 70 ms.
SHUFFLE_FRAMES = 8
SHUFFLE_MS = 70


class App:
    """The game window. Holds the widgets and the current Match."""

    def __init__(self, root: tk.Tk, store: StatsStore) -> None:
        self.root = root
        self.store = store
        self.match: Optional[Match] = None
        # True while the shuffle animation runs; blocks new moves meanwhile.
        self.busy = False
        # Separate random generator only for visual effects, so the animation
        # never consumes numbers from the CPU's own generator.
        self._fx = random.Random()

        root.title("Rock Paper Scissors — v2")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Load the images once. Tk needs us to keep references to them:
        # if a PhotoImage is garbage-collected, it disappears from the screen.
        self.cards = {p.stem: tk.PhotoImage(file=str(p)) for p in ASSETS.glob("*.png")}
        self.thumbs = {p.stem: tk.PhotoImage(file=str(p)) for p in (ASSETS / "thumbs").glob("*.png")}
        # Empty image with the size of a card, used as the "?" placeholder.
        self.blank = tk.PhotoImage(width=174, height=248)

        # Values of the three toolbar menus.
        self.mode = tk.StringVar(value="Classic")
        self.difficulty = tk.StringVar(value="Hard")
        self.target = tk.StringVar(value="5")

        # Build the window from top to bottom.
        self._build_toolbar()
        self._build_scoreboard()
        self._build_arena()
        self._build_ai_panel()
        self.moves_frame = tk.Frame(root, bg=BG)
        self.moves_frame.pack(padx=20, pady=(4, 18))
        self.move_buttons: list[tk.Button] = []

        # Changing any menu starts a new match with the new settings.
        for var in (self.mode, self.difficulty, self.target):
            var.trace_add("write", lambda *_: self.new_match())
        # One handler for every key press (1-5, N, S).
        root.bind("<Key>", self._on_key)
        self.new_match()

    # ---------- layout ----------

    def _menu(self, parent: tk.Widget, label: str, var: tk.StringVar, options, width: int) -> None:
        """A label plus a drop-down menu, styled for the dark theme."""
        tk.Label(parent, text=label, bg=BG, fg=MUTED, font=(FONT, 10)).pack(side="left", padx=(12, 4))
        menu = tk.OptionMenu(parent, var, *options)
        menu.configure(bg=PANEL, fg=TEXT, activebackground=ACCENT, activeforeground=BG,
                       highlightthickness=0, bd=0, relief="flat", font=(FONT, 10), width=width)
        # The list that drops down is a separate widget and needs its own colours.
        menu["menu"].configure(bg=PANEL, fg=TEXT, activebackground=ACCENT, activeforeground=BG)
        menu.pack(side="left")

    def _button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        """A flat text button in the app's style."""
        return tk.Button(parent, text=text, command=command, bg=PANEL, fg=TEXT, bd=0,
                         activebackground=ACCENT, activeforeground=BG, highlightthickness=0,
                         font=(FONT, 10, "bold"), padx=12, pady=4, cursor="hand2")

    def _build_toolbar(self) -> None:
        """Top bar: Mode / CPU / First to menus, and New match / Stats buttons."""
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(12, 0))
        self._menu(bar, "Mode", self.mode, RULESETS, width=11)
        self._menu(bar, "CPU", self.difficulty, OPPONENTS, width=7)
        self._menu(bar, "First to", self.target, TARGETS, width=3)
        # side="right" packs from the right edge, so Stats ends up last.
        self._button(bar, "Stats (S)", self.show_stats).pack(side="right", padx=(6, 8))
        self._button(bar, "New match (N)", self.new_match).pack(side="right")

    def _build_scoreboard(self) -> None:
        """'YOU 2 — 1 CPU' and, below it, the round number."""
        board = tk.Frame(self.root, bg=BG)
        board.pack(pady=(16, 0))
        self.player_score = tk.Label(board, bg=BG, fg=TEXT, font=(FONT, 34, "bold"), width=3)
        self.cpu_score = tk.Label(board, bg=BG, fg=TEXT, font=(FONT, 34, "bold"), width=3)
        tk.Label(board, text="YOU", bg=BG, fg=MUTED, font=(FONT, 12, "bold")).grid(row=0, column=0)
        self.player_score.grid(row=0, column=1)
        tk.Label(board, text="—", bg=BG, fg=MUTED, font=(FONT, 24)).grid(row=0, column=2)
        self.cpu_score.grid(row=0, column=3)
        tk.Label(board, text="CPU", bg=BG, fg=MUTED, font=(FONT, 12, "bold")).grid(row=0, column=4)
        self.round_label = tk.Label(board, bg=BG, fg=MUTED, font=(FONT, 10))
        self.round_label.grid(row=1, column=0, columnspan=5)

    def _build_arena(self) -> None:
        """The two big cards (yours vs. the CPU's) and the round result."""
        arena = tk.Frame(self.root, bg=BG)
        arena.pack(pady=10)
        # Both cards start as the blank image with a "?" drawn on top
        # (compound="center" shows the text over the image).
        card = dict(image=self.blank, compound="center", bg=PANEL, fg=MUTED,
                    font=(FONT, 48, "bold"), text="?", bd=0)
        self.player_card = tk.Label(arena, **card)
        self.cpu_card = tk.Label(arena, **card)
        self.player_card.grid(row=0, column=0)
        tk.Label(arena, text="VS", bg=BG, fg=ACCENT, font=(FONT, 22, "bold")).grid(row=0, column=1, padx=28)
        self.cpu_card.grid(row=0, column=2)
        self.result = tk.Label(self.root, bg=BG, fg=TEXT, font=(FONT, 20, "bold"))  # "You win the round!"
        self.result.pack()
        self.detail = tk.Label(self.root, bg=BG, fg=MUTED, font=(FONT, 12))  # "Paper covers rock"
        self.detail.pack()

    def _build_ai_panel(self) -> None:
        """'CPU's mind' panel: what the CPU predicted, plus a row of result dots."""
        panel = tk.Frame(self.root, bg=PANEL, padx=16, pady=10)
        panel.pack(fill="x", padx=20, pady=12)
        tk.Label(panel, text="CPU'S MIND", bg=PANEL, fg=ACCENT, font=(FONT, 9, "bold")).pack(anchor="w")
        self.ai_text = tk.Label(panel, bg=PANEL, fg=TEXT, font=(FONT, 11), justify="left")
        self.ai_text.pack(anchor="w")
        self.history = tk.Canvas(panel, height=18, bg=PANEL, highlightthickness=0)
        self.history.pack(fill="x", pady=(6, 0))

    def _build_move_buttons(self) -> None:
        """One card button per move. Rebuilt when the mode changes (3 <-> 5 moves)."""
        for widget in self.moves_frame.winfo_children():
            widget.destroy()
        self.move_buttons = []
        for i, move in enumerate(self.match.rules.moves):
            col = tk.Frame(self.moves_frame, bg=BG)
            col.grid(row=0, column=i, padx=6)
            # m=move freezes the current value; a plain `lambda: self.play(move)`
            # would make every button play the last move of the loop.
            btn = tk.Button(col, image=self.thumbs[move], command=lambda m=move: self.play(m),
                            bg=BG, activebackground=ACCENT, bd=0, highlightthickness=0, cursor="hand2")
            btn.pack()
            # Keyboard hint under each card: [1], [2]...
            tk.Label(col, text=f"[{i + 1}]", bg=BG, fg=MUTED, font=(FONT, 9)).pack()
            self.move_buttons.append(btn)

    # ---------- game flow ----------

    def new_match(self) -> None:
        """Start a match with the settings currently selected in the menus."""
        if self.busy:
            return  # never interrupt the animation halfway
        rules = RULESETS[self.mode.get()]
        # A brand-new opponent each match, so it starts without knowing you.
        opponent = OPPONENTS[self.difficulty.get()](rules)
        # Only rebuild the buttons when the set of moves actually changed.
        rebuild = self.match is None or self.match.rules is not rules
        self.match = Match(rules, opponent, target=int(self.target.get()))
        if rebuild:
            self._build_move_buttons()
        for card in (self.player_card, self.cpu_card):
            card.configure(image=self.blank, text="?")
        self.result.configure(text="Pick your move", fg=TEXT)
        self.detail.configure(text=f"{opponent.name} CPU: {opponent.description}")
        self._set_buttons(True)
        self._refresh()

    def play(self, move: str) -> None:
        """Called when the player clicks a card or presses its number key."""
        if self.busy or self.match.is_over:
            return
        self.busy = True
        self._set_buttons(False)
        self.player_card.configure(image=self.cards[move], text="")
        # The CPU's move is decided now, before the animation; the shuffle is only visual
        rnd = self.match.play(move)
        self._shuffle(rnd, SHUFFLE_FRAMES)

    def _shuffle(self, rnd: Round, frames_left: int) -> None:
        """Show random cards on the CPU side a few times, then reveal the real one."""
        if frames_left:
            fake = self._fx.choice(self.match.rules.moves)
            self.cpu_card.configure(image=self.cards[fake], text="")
            # after() schedules the next frame without freezing the window
            # (time.sleep would block Tk and nothing would be redrawn).
            self.root.after(SHUFFLE_MS, self._shuffle, rnd, frames_left - 1)
        else:
            self._reveal(rnd)

    def _reveal(self, rnd: Round) -> None:
        """End of the animation: show the CPU's real move and the result."""
        self.busy = False
        self.cpu_card.configure(image=self.cards[rnd.cpu])
        headline = {Outcome.WIN: "You win the round!", Outcome.LOSE: "CPU wins the round",
                    Outcome.DRAW: "Draw"}[rnd.outcome]
        self.result.configure(text=headline, fg=COLORS[rnd.outcome])
        self.detail.configure(text=self.match.rules.describe(rnd.player, rnd.cpu))
        if self.match.is_over:
            # Save the finished match and leave the buttons disabled.
            self.store.record(self.match)
            won = self.match.result is Outcome.WIN
            self.result.configure(text="YOU WON THE MATCH!" if won else "THE CPU WON THE MATCH",
                                  fg=COLORS[self.match.result])
            self.detail.configure(text=self.detail.cget("text") + "  ·  Press N for a rematch")
        else:
            self._set_buttons(True)
        self._refresh(rnd)

    def _set_buttons(self, enabled: bool) -> None:
        for btn in self.move_buttons:
            btn.configure(state="normal" if enabled else "disabled")

    def _refresh(self, rnd: Optional[Round] = None) -> None:
        """Update the score, round label, CPU panel and result dots."""
        m = self.match
        self.player_score.configure(text=m.player_score)
        self.cpu_score.configure(text=m.cpu_score)
        self.round_label.configure(text=f"Round {len(m.rounds)} · first to {m.target} · {m.rules.name}")
        self.ai_text.configure(text=self._ai_message(rnd))
        self._draw_history()

    def _ai_message(self, rnd: Optional[Round]) -> str:
        """Text of the 'CPU's mind' panel for the round that just ended."""
        if self.match.opponent.name == "Easy":
            return "Not thinking at all: every move is a coin flip."
        if rnd is None or rnd.predicted is None:
            return "Studying you... it needs a few rounds to spot patterns."
        verdict = "it read you ✔" if rnd.was_read else "you fooled it ✘"
        line = f"It predicted {rnd.predicted.upper()} ({rnd.confidence:.0%} sure) — {verdict}"
        rate = self.match.read_rate
        # Compare with chance: 1/3 in Classic, 1/5 in Lizard-Spock.
        return f"{line}\nRead rate this match: {rate:.0%} (a random guess would be {1 / len(self.match.rules.moves):.0%})"

    def _draw_history(self) -> None:
        """One coloured dot per round (green win, red loss, grey draw), last 30 only."""
        c = self.history
        c.delete("all")
        for i, r in enumerate(self.match.rounds[-30:]):
            x = 8 + i * 18  # 18 px between dot centres
            c.create_oval(x - 6, 3, x + 6, 15, fill=COLORS[r.outcome], outline="")

    def _on_key(self, event: tk.Event) -> None:
        """Keyboard shortcuts: 1-5 play a move, N new match, S statistics."""
        key = event.char.lower()
        if key == "n":
            self.new_match()
        elif key == "s":
            self.show_stats()
        # Only numbers that match a move in the current mode (1-3 or 1-5).
        elif key.isdigit() and 1 <= int(key) <= len(self.match.rules.moves):
            self.play(self.match.rules.moves[int(key) - 1])

    # ---------- stats window ----------

    def show_stats(self) -> None:
        """Open the statistics window on top of the game."""
        win = tk.Toplevel(self.root, bg=BG, padx=24, pady=20)
        win.title("Your statistics")
        win.resizable(False, False)
        win.transient(self.root)  # keeps it above the main window
        self._fill_stats(win)

    def _fill_stats(self, win: tk.Toplevel) -> None:
        """Draw (or redraw, after a reset) the contents of the stats window."""
        for widget in win.winfo_children():
            widget.destroy()
        s = self.store.summary()

        def pct(x: Optional[float]) -> str:
            # None means "no data yet".
            return "—" if x is None else f"{x:.0%}"

        streak = s.current_streak
        # (label, value) pairs, shown as a two-column table.
        rows = [
            ("Matches played", s.matches),
            ("Matches won", f"{s.wins}  ({pct(s.win_rate)})"),
            ("Rounds  W / D / L", f"{s.rounds['win']} / {s.rounds['draw']} / {s.rounds['lose']}"),
            ("Best winning streak", s.best_streak),
            ("Current streak", f"{abs(streak)} {'won' if streak > 0 else 'lost'} in a row" if streak else "—"),
            ("Favourite move", (s.favorite_move or "—").capitalize()),
            ("How often the CPU reads you", pct(s.read_rate)),
        ]
        # One extra row per difficulty level you have played against.
        rows += [(f"Win rate vs {name}", f"{pct(w / p)}  ({w}/{p})") for name, (w, p) in s.by_difficulty.items()]
        for i, (label, value) in enumerate(rows):
            tk.Label(win, text=label, bg=BG, fg=MUTED, font=(FONT, 11), anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(win, text=value, bg=BG, fg=TEXT, font=(FONT, 11, "bold"), anchor="e").grid(row=i, column=1, sticky="e", padx=(24, 0))

        # Horizontal bar chart of how often you use each move.
        if s.moves:
            tk.Label(win, text="MOVES YOU USE", bg=BG, fg=ACCENT, font=(FONT, 9, "bold")).grid(
                row=len(rows), column=0, columnspan=2, sticky="w", pady=(14, 4))
            bars = tk.Canvas(win, width=320, height=22 * len(s.moves), bg=BG, highlightthickness=0)
            bars.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w")
            top = max(s.moves.values())
            for i, (move, count) in enumerate(s.moves.most_common()):
                y = i * 22  # one 22 px line per move
                bars.create_text(0, y + 9, text=move.capitalize(), fill=TEXT, anchor="w", font=(FONT, 10))
                # The most used move gets the full 200 px; the rest are proportional.
                bars.create_rectangle(80, y + 3, 80 + 200 * count / top, y + 16, fill=ACCENT, outline="")
                bars.create_text(290, y + 9, text=count, fill=MUTED, anchor="w", font=(FONT, 10))

        def reset() -> None:
            # Ask first: this deletes the saved history for good.
            if messagebox.askyesno("Reset statistics", "Delete all your saved matches?", parent=win):
                self.store.reset()
                self._fill_stats(win)

        self._button(win, "Reset stats", reset).grid(row=len(rows) + 2, column=0, columnspan=2, pady=(16, 0))


def run(store: Optional[StatsStore] = None) -> None:
    """Create the window and start Tk's event loop (blocks until it's closed)."""
    root = tk.Tk()
    App(root, store or StatsStore())
    root.mainloop()
