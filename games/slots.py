"""Slot machine — three reels, classic symbols.

Match three-of-a-kind for a payout (rarer symbol = bigger multiple of your bet),
or land two cherries for a small win. Symbol odds are weighted so the big payouts
are genuinely rare — that's the built-in house edge. Uses the shared casino ``bank``.
"""
import tkinter as tk
import random

import theme

import dealer
import sfx
import fx
import stats

FELT = "#0c1020"; DARKFELT = "#1e2647"; IVORY = "#f7faf5"; GOLD = "#f6d365"
WIN = "#7fe0a8"; LOSE = "#e0616b"
MIN_BET = 5

# Classic slot symbols, DRAWN as colorful shapes (tkinter can't show color emoji).
# name -> three-of-a-kind payout (× the bet)
PAYOUT = {"cherry": 4, "lemon": 6, "bell": 10, "bar": 20, "diamond": 50, "seven": 100}
REEL = (["cherry"] * 6 + ["lemon"] * 5 + ["bell"] * 4 + ["bar"] * 3 + ["diamond"] * 2 + ["seven"] * 1)
TWO = "cherry"                  # any two cherries pays 2×


def draw_symbol(cv, kind, cx, cy, s):
    """Draw one classic slot symbol centered at (cx, cy), scaled by s, on canvas cv."""
    if kind == "seven":
        cv.create_text(cx, cy + 2, text="7", font=("Georgia", int(s * 0.74), "bold"), fill="#e11d2a")
    elif kind == "cherry":
        rr = s * 0.20
        for dx in (-s * 0.15, s * 0.17):
            cv.create_oval(cx + dx - rr, cy + s * 0.12 - rr, cx + dx + rr, cy + s * 0.12 + rr,
                           fill="#d21f2b", outline="#8f1620", width=1)
            cv.create_oval(cx + dx - rr * 0.5, cy + s * 0.12 - rr * 0.55, cx + dx - rr * 0.1,
                           cy + s * 0.12 - rr * 0.15, fill="#ff9a9a", outline="")
        cv.create_line(cx - s * 0.15, cy + s * 0.12 - rr, cx + s * 0.03, cy - s * 0.26, fill="#2e7d32", width=3)
        cv.create_line(cx + s * 0.17, cy + s * 0.12 - rr, cx + s * 0.03, cy - s * 0.26, fill="#2e7d32", width=3)
        cv.create_oval(cx + s * 0.03, cy - s * 0.34, cx + s * 0.26, cy - s * 0.2, fill="#43a047", outline="#2e7d32")
    elif kind == "lemon":
        cv.create_oval(cx - s * 0.3, cy - s * 0.2, cx + s * 0.3, cy + s * 0.2, fill="#f4d000", outline="#c9a300", width=2)
        cv.create_oval(cx - s * 0.18, cy - s * 0.13, cx - s * 0.02, cy - s * 0.01, fill="#fff59d", outline="")
        cv.create_oval(cx + s * 0.26, cy - 4, cx + s * 0.35, cy + 4, fill="#c9a300", outline="")
        cv.create_oval(cx - s * 0.35, cy - 4, cx - s * 0.26, cy + 4, fill="#c9a300", outline="")
    elif kind == "bell":
        pts = [cx - s * 0.24, cy + s * 0.16, cx - s * 0.16, cy - s * 0.06, cx, cy - s * 0.26,
               cx + s * 0.16, cy - s * 0.06, cx + s * 0.24, cy + s * 0.16]
        cv.create_polygon(pts, fill="#f4c430", outline="#b8901a", width=2)
        cv.create_rectangle(cx - s * 0.26, cy + s * 0.14, cx + s * 0.26, cy + s * 0.21, fill="#f4c430", outline="#b8901a")
        cv.create_oval(cx - 4, cy - s * 0.31, cx + 4, cy - s * 0.23, fill="#f4c430", outline="#b8901a")
        cv.create_oval(cx - s * 0.06, cy + s * 0.2, cx + s * 0.06, cy + s * 0.3, fill="#7a4f00", outline="")
    elif kind == "bar":
        cv.create_rectangle(cx - s * 0.32, cy - s * 0.13, cx + s * 0.32, cy + s * 0.13, fill="#151515",
                            outline="#f6d365", width=2)
        cv.create_text(cx, cy, text="BAR", font=("Georgia", int(s * 0.2), "bold"), fill="#f6d365")
    elif kind == "diamond":
        pts = [cx, cy - s * 0.28, cx + s * 0.26, cy - s * 0.03, cx, cy + s * 0.3, cx - s * 0.26, cy - s * 0.03]
        cv.create_polygon(pts, fill="#37bff0", outline="#1a86c0", width=2)
        cv.create_line(cx - s * 0.26, cy - s * 0.03, cx + s * 0.26, cy - s * 0.03, fill="#bff0ff", width=1)
        cv.create_line(cx, cy - s * 0.28, cx, cy + s * 0.3, fill="#bff0ff", width=1)

RULES = (
    "Slots — three reels.\n\n"
    "Set your bet and SPIN. Match three of the same symbol (× your bet):\n\n"
    "      Cherry  4×        Lemon  6×        Bell  10×\n"
    "      BAR  20×      Diamond  50×      Seven  100×  JACKPOT\n\n"
    "      any two Cherries   →   2×\n\n"
    "Rarer symbols pay more — and land less often. That's the house edge."
)


def open_game(parent, bank, on_change):
    st = {"bet": 10, "busy": False}

    win = tk.Toplevel(parent)
    win.title("Slots")
    win.configure(bg=FELT)
    win.geometry("520x720")
    win.resizable(True, True)
    win.minsize(440, 480)
    theme.header(win, "SLOTS", w=520)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)          # scrollable so every control is always reachable

    chips = tk.Label(body, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(18, 6))

    db = dealer.DealerBox(body, win, felt=FELT)
    db.pack(fill="x", padx=18, pady=(0, 4))

    machine = tk.Canvas(body, width=380, height=300, bg=FELT, highlightthickness=0)
    machine.pack(pady=(2, 4))

    def _rr(x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return machine.create_polygon(pts, smooth=True, **kw)

    _rr(18, 8, 322, 292, 22, fill="#242b48", outline=GOLD, width=4)          # cabinet body
    _rr(28, 16, 312, 284, 16, fill="#161b30", outline="#3a4468", width=2)
    _rr(48, 24, 292, 62, 12, fill=GOLD, outline="#a9821f", width=2)          # marquee
    machine.create_text(170, 43, text="★  LUCKY  7s  ★", font=("Georgia", 14, "bold"), fill="#151515")
    _rr(44, 78, 296, 198, 12, fill="#0a0d18", outline="#3a4468", width=2)    # reel window
    RW, RH = 62, 92
    reel_cv = []
    for i in range(3):
        cx = 78 + i * 82
        _rr(cx - 34, 90, cx + 34, 186, 8, fill=IVORY, outline="#c9ccc0", width=2)
        cv = tk.Canvas(machine, width=RW, height=RH, bg=IVORY, highlightthickness=0)
        machine.create_window(cx, 138, window=cv)
        reel_cv.append(cv)

    def draw_reel(i, kind):
        reel_cv[i].delete("all")
        draw_symbol(reel_cv[i], kind, RW / 2, RH / 2, 74)

    for i, k in enumerate(("seven", "cherry", "bell")):
        draw_reel(i, k)
    machine.create_line(50, 138, 290, 138, fill=LOSE, width=2)              # payline
    _rr(74, 214, 266, 250, 8, fill="#0a0d18", outline="#3a4468", width=2)   # coin tray
    machine.create_text(170, 232, text="INSERT  COIN", font=("Consolas", 9, "bold"), fill=GOLD)

    LX, PIVOT = 348, (322, 176)                                            # pull lever
    lever_rod = machine.create_line(PIVOT[0], PIVOT[1], LX, 100, fill="#9aa0b0", width=6)
    lever_knob = machine.create_oval(LX - 11, 89, LX + 11, 111, fill=LOSE, outline="#7a2b2b", width=2)

    def set_lever(knob_y):
        machine.coords(lever_rod, PIVOT[0], PIVOT[1], LX, knob_y)
        machine.coords(lever_knob, LX - 11, knob_y - 11, LX + 11, knob_y + 11)

    msg = tk.Label(body, text="Match 3 symbols to win.  Three 7s = 100× JACKPOT!",
                   font=("Segoe UI", 13, "bold"), bg=FELT, fg="white", wraplength=460)
    msg.pack(pady=(8, 6))

    paytable = tk.Label(
        body, bg=FELT, fg="#b9d6c7", font=("Consolas", 11),
        text="Cherry 4×   Lemon 6×   Bell 10×\nBAR 20×   Diamond 50×   777 100×   ·   two Cherry = 2×")
    paytable.pack(pady=(0, 6))

    betrow = tk.Frame(body, bg=FELT)
    betrow.pack(pady=6)

    def refresh():
        chips.config(text=f"CHIPS:  ${bank.balance}")
        bet_lbl.config(text=f"Bet: ${st['bet']}")
        broke = bank.balance < MIN_BET
        for b in (minus_btn, plus_btn):
            b.config(state="disabled" if st["busy"] else "normal")
        spin_btn.config(state="disabled" if (st["busy"] or broke) else "normal")
        if broke and not st["busy"]:
            msg.config(text="Out of chips! Buy in from the lobby.", fg=LOSE)
        on_change()

    def change_bet(d):
        st["bet"] = max(MIN_BET, min(st["bet"] + d, bank.balance))
        refresh()

    def resolve(final):
        st["busy"] = False
        a, b, c = final
        if a == b == c:
            amt = st["bet"] * PAYOUT[a]
            bank.add(amt)
            tag = "JACKPOT — LUCKY 7s!" if a == "seven" else "THREE OF A KIND!"
            msg.config(text=f"Three {a}s  —  {tag}  You win ${amt}!", fg=WIN)
            jack = a == "seven"
            db.react("jackpot" if jack else "bigwin", amt=amt, game="Slots")
            sfx.play("jackpot" if jack else "bigwin")
            stats.record("Slots", "win", amt, wager=st["bet"])
            fx.celebrate(win, amt, big=True)
        elif final.count(TWO) == 2:
            amt = st["bet"] * 2
            bank.add(amt)
            msg.config(text=f"Two cherries  —  you win ${amt}!", fg=WIN)
            db.react("win", amt=amt, game="Slots")
            sfx.play("win"); stats.record("Slots", "win", amt, wager=st["bet"])
        else:
            bank.add(-st["bet"])
            msg.config(text=f"{a}{b}{c}  —  no match. You lose ${st['bet']}.", fg=LOSE)
            db.react("loss", game="Slots")
            sfx.play("lose"); stats.record("Slots", "loss", -st["bet"], wager=st["bet"])
        refresh()

    def spin(event=None):
        if st["busy"] or bank.balance < st["bet"]:
            return
        st["busy"] = True
        sfx.play("chip")
        refresh()
        final = [random.choice(REEL) for _ in range(3)]
        stops = (12, 18, 24)      # each reel locks a little later, for suspense

        def reels_spin(i):
            for r in range(3):
                draw_reel(r, final[r] if i >= stops[r] else random.choice(REEL))
            if i < stops[-1]:
                win.after(60, lambda: reels_spin(i + 1))
            else:
                resolve(final)

        def pull(k):
            seq = (100, 118, 136, 152, 152, 136, 118, 100)   # yank the lever down, then release
            if k < len(seq):
                set_lever(seq[k])
                win.after(32, lambda: pull(k + 1))
            else:
                reels_spin(0)
        pull(0)

    minus_btn = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    spin_btn = tk.Button(body, text="🎰  SPIN", font=("Segoe UI", 16, "bold"), command=spin,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=34, pady=12)
    spin_btn.pack(pady=14)

    def new_game():
        if st["busy"]:
            return
        for i, k in enumerate(("seven", "cherry", "bell")):
            draw_reel(i, k)
        set_lever(100)
        msg.config(text="Match 3 symbols to win.  Three 7s = 100× JACKPOT!", fg="white")
        refresh()

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(0, 16))
    tk.Button(bottom, text="🔄  New Game", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=new_game).pack(side="left", padx=6)
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "SLOTS", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)

    win.bind("<space>", spin)
    refresh()
    db.react("greeting", game="Slots")
