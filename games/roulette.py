"""Roulette table — European single-zero wheel (numbers 0-36).

Outside bets (red/black, even/odd, low/high) pay 1:1; a straight-up number pays
35:1. The lone green 0 is the house edge — it loses every outside bet. Reads and
writes the shared casino ``bank``.
"""
import tkinter as tk
import random

RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

FELT = "#0e5a3c"; DARKFELT = "#0a4630"; IVORY = "#f7faf5"; GOLD = "#f4d35e"
RED = "#c0392b"; BLACK = "#161616"; GREEN = "#1e8f5e"; WIN = "#8fe6b8"; LOSE = "#e06a5c"
MIN_BET = 5

OUTSIDE = [("Red", "red"), ("Black", "black"), ("Even", "even"),
           ("Odd", "odd"), ("1-18", "low"), ("19-36", "high")]


def color_of(n):
    if n == 0:
        return GREEN
    return RED if n in RED_NUMS else BLACK


def color_name(n):
    if n == 0:
        return "green"
    return "red" if n in RED_NUMS else "black"


def wins(n, kind, number):
    if kind == "red":
        return n in RED_NUMS
    if kind == "black":
        return n != 0 and n not in RED_NUMS
    if kind == "even":
        return n != 0 and n % 2 == 0
    if kind == "odd":
        return n % 2 == 1
    if kind == "low":
        return 1 <= n <= 18
    if kind == "high":
        return 19 <= n <= 36
    if kind == "number":
        return n == number
    return False


def open_game(parent, bank, on_change):
    st = {"bet": 10, "busy": False}

    win = tk.Toplevel(parent)
    win.title("Roulette")
    win.configure(bg=FELT)
    win.geometry("560x650")
    win.resizable(False, False)

    chips = tk.Label(win, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(16, 6))
    result = tk.Label(win, text="–", font=("Segoe UI", 42, "bold"), bg=DARKFELT, fg="white", width=3)
    result.pack(pady=6)
    msg = tk.Label(win, text="Pick a bet, set your chips, and SPIN!",
                   font=("Segoe UI", 13, "bold"), bg=FELT, fg="white", wraplength=500)
    msg.pack(pady=(6, 8))

    bettype = tk.StringVar(value="red")

    outside = tk.Frame(win, bg=FELT)
    outside.pack()
    for i, (lbl, val) in enumerate(OUTSIDE):
        tk.Radiobutton(outside, text=f"{lbl}\n1:1", value=val, variable=bettype,
                       font=("Segoe UI", 11, "bold"), width=8, height=2, indicatoron=False,
                       bg=DARKFELT, fg="white", selectcolor="#12704c",
                       activebackground="#12704c", relief="flat").grid(row=i // 3, column=i % 3, padx=5, pady=5)

    numrow = tk.Frame(win, bg=FELT)
    numrow.pack(pady=(10, 4))
    tk.Radiobutton(numrow, text="Single number (35:1):", value="number", variable=bettype,
                   font=("Segoe UI", 11, "bold"), indicatoron=False, bg=DARKFELT, fg=GOLD,
                   selectcolor="#12704c", activebackground="#12704c", relief="flat", padx=8, pady=6).pack(side="left", padx=4)
    numspin = tk.Spinbox(numrow, from_=0, to=36, width=4, font=("Consolas", 14, "bold"),
                         justify="center")
    numspin.pack(side="left", padx=4)

    betrow = tk.Frame(win, bg=FELT)
    betrow.pack(pady=(12, 4))

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

    def resolve(n):
        st["busy"] = False
        kind = bettype.get()
        try:
            number = int(numspin.get())
        except ValueError:
            number = 0
        if wins(n, kind, number):
            mult = 35 if kind == "number" else 1
            amt = st["bet"] * mult
            bank.add(amt)
            msg.config(text=f"{n} {color_name(n)} — YOU WIN ${amt}!", fg=WIN)
        else:
            bank.add(-st["bet"])
            msg.config(text=f"{n} {color_name(n)} — you lose ${st['bet']}.", fg=LOSE)
        refresh()

    def spin(event=None):
        if st["busy"] or bank.balance < st["bet"]:
            return
        st["busy"] = True
        refresh()

        def step(i):
            n = random.randint(0, 36)
            result.config(text=str(n), bg=color_of(n))
            if i < 18:
                win.after(45 + i * 14, lambda: step(i + 1))
            else:
                resolve(n)
        step(0)

    minus_btn = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    spin_btn = tk.Button(win, text="🔴  SPIN", font=("Segoe UI", 16, "bold"), command=spin,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=34, pady=12)
    spin_btn.pack(pady=16)

    win.bind("<space>", spin)
    refresh()
