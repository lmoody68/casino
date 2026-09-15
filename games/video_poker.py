"""Video Poker — Jacks or Better.

Deal five cards, HOLD the ones you want, then DRAW to replace the rest. The final
hand is scored on the classic Jacks-or-Better paytable (a pair of Jacks or higher
returns your bet; better hands pay more). Uses the shared casino ``bank``.
"""
import tkinter as tk
import random
from collections import Counter

FELT = "#0e5a3c"; DARKFELT = "#0a4630"; IVORY = "#f7faf5"; GOLD = "#f4d35e"
WIN = "#8fe6b8"; LOSE = "#e06a5c"; HELD = "#f4d35e"
CARD_RED = "#c0392b"; CARD_BLACK = "#141414"
MIN_BET = 5

SUITS = ["♠", "♥", "♦", "♣"]
RED_SUITS = {"♥", "♦"}
RANK_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}

# (hand name, payout multiple of the bet). Order matters — best first.
PAYTABLE = [
    ("Royal Flush", 250), ("Straight Flush", 50), ("Four of a Kind", 25),
    ("Full House", 9), ("Flush", 6), ("Straight", 4),
    ("Three of a Kind", 3), ("Two Pair", 2), ("Jacks or Better", 1),
]


def rank_label(r):
    return RANK_STR.get(r, str(r))


def evaluate(cards):
    """Return (hand_name, payout_multiple) for a 5-card hand."""
    ranks = sorted(c[0] for c in cards)
    counts = Counter(ranks)
    shape = sorted(counts.values(), reverse=True)
    is_flush = len({c[1] for c in cards}) == 1
    uniq = sorted(set(ranks))
    is_straight = (len(uniq) == 5 and uniq[-1] - uniq[0] == 4) or set(ranks) == {14, 2, 3, 4, 5}
    royal = set(ranks) == {10, 11, 12, 13, 14}

    if is_straight and is_flush and royal:
        return ("Royal Flush", 250)
    if is_straight and is_flush:
        return ("Straight Flush", 50)
    if shape[0] == 4:
        return ("Four of a Kind", 25)
    if shape == [3, 2]:
        return ("Full House", 9)
    if is_flush:
        return ("Flush", 6)
    if is_straight:
        return ("Straight", 4)
    if shape[0] == 3:
        return ("Three of a Kind", 3)
    if shape == [2, 2, 1]:
        return ("Two Pair", 2)
    if shape[0] == 2:
        pair_rank = max(r for r, c in counts.items() if c == 2)
        if pair_rank >= 11:
            return ("Jacks or Better", 1)
    return ("No win", 0)


def open_game(parent, bank, on_change):
    st = {"bet": 10, "phase": "bet", "cards": [], "held": [False] * 5, "deck": []}

    win = tk.Toplevel(parent)
    win.title("Video Poker")
    win.configure(bg=FELT)
    win.geometry("620x560")
    win.resizable(False, False)

    chips = tk.Label(win, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(14, 4))

    pay_text = "   ".join(f"{n} {m}×" for n, m in PAYTABLE)
    tk.Label(win, text=pay_text, bg=FELT, fg="#b9d6c7", font=("Consolas", 9)).pack(pady=(0, 8))

    card_row = tk.Frame(win, bg=FELT)
    card_row.pack(pady=6)
    card_lbls, hold_btns = [], []
    for i in range(5):
        col = tk.Frame(card_row, bg=FELT)
        col.grid(row=0, column=i, padx=7)
        cl = tk.Label(col, text="?", font=("Segoe UI", 30, "bold"), bg=IVORY, fg=CARD_BLACK,
                      width=3, height=2)
        cl.pack()
        hb = tk.Button(col, text="HOLD", font=("Segoe UI", 10, "bold"), width=6, relief="flat",
                       bg=DARKFELT, fg="white", command=lambda i=i: toggle_hold(i))
        hb.pack(pady=6)
        card_lbls.append(cl)
        hold_btns.append(hb)

    msg = tk.Label(win, text="Set your bet and press DEAL.", font=("Segoe UI", 14, "bold"),
                   bg=FELT, fg="white", wraplength=560)
    msg.pack(pady=(8, 6))

    betrow = tk.Frame(win, bg=FELT)
    betrow.pack(pady=4)

    def show_card(i):
        r, s = st["cards"][i]
        card_lbls[i].config(text=f"{rank_label(r)}\n{s}",
                            fg=CARD_RED if s in RED_SUITS else CARD_BLACK)
        held = st["held"][i]
        hold_btns[i].config(bg=HELD if held else DARKFELT, fg="#0a3d29" if held else "white",
                            text="HELD" if held else "HOLD")

    def refresh():
        chips.config(text=f"CHIPS:  ${bank.balance}")
        bet_lbl.config(text=f"Bet: ${st['bet']}")
        bet_phase = st["phase"] == "bet"
        broke = bank.balance < MIN_BET
        for b in (minus_btn, plus_btn):
            b.config(state="normal" if (bet_phase and not broke) else "disabled")
        for hb in hold_btns:
            hb.config(state="normal" if st["phase"] == "draw" else "disabled")
        if st["phase"] == "draw":
            action_btn.config(text="DRAW", state="normal")
        else:
            action_btn.config(text="DEAL", state="disabled" if broke else "normal")
        if broke and bet_phase:
            msg.config(text="Out of chips! Buy in from the lobby.", fg=LOSE)
        on_change()

    def change_bet(d):
        if st["phase"] != "bet":
            return
        st["bet"] = max(MIN_BET, min(st["bet"] + d, bank.balance))
        refresh()

    def toggle_hold(i):
        if st["phase"] != "draw":
            return
        st["held"][i] = not st["held"][i]
        show_card(i)

    def deal():
        if st["phase"] != "bet" or bank.balance < st["bet"]:
            return
        bank.add(-st["bet"])                 # put the bet in
        st["deck"] = [(r, s) for r in range(2, 15) for s in SUITS]
        random.shuffle(st["deck"])
        st["cards"] = [st["deck"].pop() for _ in range(5)]
        st["held"] = [False] * 5
        st["phase"] = "draw"
        for i in range(5):
            show_card(i)
        msg.config(text="Tap HOLD on the cards to keep, then press DRAW.", fg="white")
        refresh()

    def draw():
        for i in range(5):
            if not st["held"][i]:
                st["cards"][i] = st["deck"].pop()
            show_card(i)
        name, mult = evaluate(st["cards"])
        if mult > 0:
            payout = st["bet"] * mult
            bank.add(payout)
            msg.config(text=f"{name}!  You win ${payout}  ({mult}×)", fg=WIN)
        else:
            msg.config(text=f"{name}. Better luck next hand.", fg=LOSE)
        st["phase"] = "bet"
        refresh()

    def action():
        deal() if st["phase"] == "bet" else draw()

    minus_btn = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    action_btn = tk.Button(win, text="DEAL", font=("Segoe UI", 16, "bold"), command=action,
                           bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=40, pady=12)
    action_btn.pack(pady=14)

    refresh()
