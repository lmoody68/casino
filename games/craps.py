"""Craps table — Pass Line bet + true-odds bet.

Opens as its own window and reads/writes the shared casino ``bank``. Call
``open_game(parent, bank, on_change)``; ``on_change`` is fired whenever chips
change so the lobby can refresh its display.
"""
import tkinter as tk
import random

PIPS = {
    1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (2, 0), (0, 2), (2, 2)],
    5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
    6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)],
}
ODDS = {4: (2, 1), 10: (2, 1), 5: (3, 2), 9: (3, 2), 6: (6, 5), 8: (6, 5)}

FELT = "#0e5a3c"; DARKFELT = "#0a4630"; IVORY = "#f7faf5"
DOT = "#14312a"; GOLD = "#f4d35e"; RED = "#e06a5c"; WIN = "#8fe6b8"; BLUE = "#7cc7e8"
MIN_BET = 5


def open_game(parent, bank, on_change):
    st = {"bet": 10, "odds": 0, "point": None, "busy": False}

    win = tk.Toplevel(parent)
    win.title("Craps")
    win.configure(bg=FELT)
    win.geometry("580x720")
    win.resizable(False, False)

    chips_lbl = tk.Label(win, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips_lbl.pack(pady=(18, 4))
    point_lbl = tk.Label(win, text="", font=("Segoe UI", 13, "bold"), bg=FELT, fg="white")
    point_lbl.pack()
    canvas = tk.Canvas(win, width=420, height=210, bg=FELT, highlightthickness=0)
    canvas.pack(pady=(10, 6))
    msg = tk.Label(win, text="", font=("Segoe UI", 14, "bold"), bg=FELT, fg="white", wraplength=520)
    msg.pack(pady=(2, 6))

    def odds_payout(point, amount):
        num, den = ODDS[point]
        return (amount * num) // den

    def draw_die(x0, y0, size, n):
        canvas.create_rectangle(x0, y0, x0 + size, y0 + size, fill=IVORY, outline="#0a3d29", width=5)
        step = size / 4
        r = size * 0.09
        for (col, rowp) in PIPS[n]:
            canvas.create_oval(x0 + step * (col + 1) - r, y0 + step * (rowp + 1) - r,
                               x0 + step * (col + 1) + r, y0 + step * (rowp + 1) + r,
                               fill=DOT, outline="")

    def draw_two(a, b):
        canvas.delete("all")
        draw_die(15, 15, 180, a)
        draw_die(225, 15, 180, b)

    def refresh():
        chips_lbl.config(text=f"CHIPS:  ${bank.balance}")
        bet_lbl.config(text=f"Pass Line: ${st['bet']}")
        come_out = st["point"] is None
        broke = bank.balance < MIN_BET
        if come_out:
            point_lbl.config(text="Come-out roll  ·  POINT: OFF")
            odds_lbl.config(text="Odds: —  (set a point first)")
        else:
            num, den = ODDS[st["point"]]
            point_lbl.config(text=f"POINT:  {st['point']}   ·   odds pay {num}:{den}")
            odds_lbl.config(text=f"Odds: ${st['odds']}"
                                 + (f"  → wins ${odds_payout(st['point'], st['odds'])}" if st["odds"] else ""))
        for b in (minus_btn, plus_btn):
            b.config(state="normal" if (come_out and not st["busy"] and not broke) else "disabled")
        room = bank.balance - st["bet"] - st["odds"]
        for b in (odds_minus, odds_plus):
            b.config(state="normal" if (not come_out and not st["busy"]) else "disabled")
        odds_plus.config(state="normal" if (not come_out and not st["busy"] and room >= MIN_BET) else "disabled")
        roll_btn.config(state="disabled" if (st["busy"] or broke) else "normal")
        reset_btn.pack_forget()
        if broke and not st["busy"]:
            msg.config(text="Out of chips! Head to the lobby to buy in.", fg=RED)
            reset_btn.pack(pady=6)
        on_change()

    def change_bet(d):
        st["bet"] = max(MIN_BET, min(st["bet"] + d, bank.balance))
        refresh()

    def change_odds(d):
        room = bank.balance - st["bet"]
        st["odds"] = max(0, min(st["odds"] + d, room))
        refresh()

    def resolve(a, b):
        total = a + b
        bet = st["bet"]
        if st["point"] is None:
            if total in (7, 11):
                bank.add(bet)
                msg.config(text=f"{a}+{b} = {total} — NATURAL! You win ${bet}!", fg=WIN)
            elif total in (2, 3, 12):
                bank.add(-bet)
                msg.config(text=f"{a}+{b} = {total} — CRAPS! You lose ${bet}.", fg=RED)
            else:
                st["point"] = total; st["odds"] = 0
                num, den = ODDS[total]
                msg.config(text=f"{a}+{b} = {total} is your POINT. Take ODDS (pays {num}:{den}) "
                                f"— roll {total} before a 7!", fg=GOLD)
        else:
            point = st["point"]
            if total == point:
                extra = odds_payout(point, st["odds"])
                bank.add(bet + extra)
                tail = f"  +${extra} on odds!" if st["odds"] else ""
                msg.config(text=f"{a}+{b} = {total} — POINT HIT! Win ${bet} on the line{tail}", fg=WIN)
                st["point"] = None; st["odds"] = 0
            elif total == 7:
                lost = bet + st["odds"]
                bank.add(-lost)
                msg.config(text=f"{a}+{b} = {total} — SEVEN OUT! You lose ${lost}.", fg=RED)
                st["point"] = None; st["odds"] = 0
            else:
                msg.config(text=f"{a}+{b} = {total} — no decision. Roll again for {point}.", fg=BLUE)
        refresh()

    def roll(event=None):
        if st["busy"] or bank.balance < MIN_BET:
            return
        st["busy"] = True
        refresh()

        def step(i):
            a, b = random.randint(1, 6), random.randint(1, 6)
            draw_two(a, b)
            if i < 13:
                win.after(40 + i * 12, lambda: step(i + 1))
            else:
                st["busy"] = False
                resolve(a, b)
        step(0)

    bet_frame = tk.Frame(win, bg=FELT); bet_frame.pack(pady=(4, 2))
    minus_btn = tk.Button(bet_frame, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(bet_frame, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=15)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(bet_frame, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    odds_frame = tk.Frame(win, bg=FELT); odds_frame.pack(pady=(2, 4))
    odds_minus = tk.Button(odds_frame, text="–", font=("Segoe UI", 13, "bold"), width=3,
                           command=lambda: change_odds(-MIN_BET), bg=DARKFELT, fg=BLUE, relief="flat")
    odds_minus.pack(side="left", padx=4)
    odds_lbl = tk.Label(odds_frame, text="", font=("Consolas", 13, "bold"), bg=FELT, fg=BLUE, width=22)
    odds_lbl.pack(side="left", padx=4)
    odds_plus = tk.Button(odds_frame, text="+", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_odds(MIN_BET), bg=DARKFELT, fg=BLUE, relief="flat")
    odds_plus.pack(side="left", padx=4)

    roll_btn = tk.Button(win, text="🎲🎲   ROLL", font=("Segoe UI", 16, "bold"), command=roll,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=30, pady=12)
    roll_btn.pack(pady=14)
    reset_btn = tk.Button(win, text="(broke — buy in from the lobby)", font=("Segoe UI", 10),
                          bg=FELT, fg=RED, relief="flat", state="disabled")

    win.bind("<space>", roll)
    draw_two(1, 1)
    msg.config(text="Pass Line bet. Roll 7 or 11 to win, 2/3/12 to lose. Good luck!")
    refresh()
