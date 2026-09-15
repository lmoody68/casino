"""Video Poker — Jacks or Better.

Deal five cards, HOLD the ones you want, then DRAW to replace the rest. The final
hand is scored on the classic Jacks-or-Better paytable (a pair of Jacks or higher
returns your bet; better hands pay more). Uses the shared casino ``bank``.
"""
import tkinter as tk
import random
import threading
from collections import Counter

import theme
import cards
import coach
import dealer
import sfx
import fx
import stats

FELT = "#0c1020"; DARKFELT = "#1e2647"; IVORY = "#f7faf5"; GOLD = "#f6d365"
WIN = "#7fe0a8"; LOSE = "#e0616b"; HELD = "#f6d365"
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

RULES = (
    "Jacks or Better video poker.\n\n"
    "1.  Set your bet and press DEAL — you get 5 cards.\n"
    "2.  Tap HOLD on the cards you want to keep.\n"
    "3.  Press DRAW — the cards you didn't hold are replaced.\n"
    "4.  You're paid by your final hand.\n\n"
    "PAYOUTS (× your bet):\n"
    "Royal Flush 250×    Straight Flush 50×\n"
    "Four of a Kind 25×    Full House 9×    Flush 6×\n"
    "Straight 4×    Three of a Kind 3×    Two Pair 2×\n"
    "Pair of Jacks or better 1×\n\n"
    "A pair lower than Jacks does not pay."
)


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
    win.geometry("620x620")
    win.resizable(True, True)
    win.minsize(480, 480)
    theme.header(win, "VIDEO POKER", w=620)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)          # scrollable so every control is always reachable

    chips = tk.Label(body, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(14, 4))

    db = dealer.DealerBox(body, win, felt=FELT)
    db.pack(fill="x", padx=18, pady=(0, 2))

    pay_text = "   ".join(f"{n} {m}×" for n, m in PAYTABLE)
    tk.Label(body, text=pay_text, bg=FELT, fg="#b9d6c7", font=("Consolas", 9)).pack(pady=(0, 8))

    FELT_GREEN = "#0a6b3f"
    CW, CH = 86, 120
    felt = tk.Frame(body, bg=FELT_GREEN, highlightbackground=GOLD, highlightthickness=3)
    felt.pack(pady=8)
    tk.Label(felt, text="●   ●   ●    FIVE-CARD DRAW    ●   ●   ●", font=("Consolas", 9, "bold"),
             bg=FELT_GREEN, fg="#8fd0ab").pack(pady=(8, 0))
    card_row = tk.Frame(felt, bg=FELT_GREEN)
    card_row.pack(padx=14, pady=(4, 12))
    card_canvases, hold_btns = [], []
    for i in range(5):
        col = tk.Frame(card_row, bg=FELT_GREEN)
        col.grid(row=0, column=i, padx=6)
        cv = tk.Canvas(col, width=CW + 8, height=CH + 8, bg=FELT_GREEN, highlightthickness=0)
        cv.pack()
        hb = tk.Button(col, text="HOLD", font=("Segoe UI", 10, "bold"), width=7, relief="flat",
                       bg=DARKFELT, fg="white", command=lambda i=i: toggle_hold(i))
        hb.pack(pady=6)
        card_canvases.append(cv)
        hold_btns.append(hb)

    msg = tk.Label(body, text="Set your bet and press DEAL.", font=("Segoe UI", 14, "bold"),
                   bg=FELT, fg="white", wraplength=560)
    msg.pack(pady=(8, 6))

    betrow = tk.Frame(body, bg=FELT)
    betrow.pack(pady=4)

    def show_card(i):
        cv = card_canvases[i]
        cv.delete("all")
        if st["cards"]:
            r, s = st["cards"][i]
            cards.draw_card(cv, 4, 4, CW, CH, r, s, face_up=True)
        else:
            cards.draw_card(cv, 4, 4, CW, CH, face_up=False)
        held = st["held"][i]
        if held:
            cv.create_rectangle(2, 2, CW + 6, CH + 6, outline=GOLD, width=3)
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
        sfx.play("card")
        coach_lbl.config(text="")
        msg.config(text="Tap HOLD on the cards to keep, then press DRAW.", fg="white")
        refresh()

    def draw():
        for i in range(5):
            if not st["held"][i]:
                st["cards"][i] = st["deck"].pop()
            show_card(i)
        sfx.play("card")
        name, mult = evaluate(st["cards"])
        if mult > 0:
            payout = st["bet"] * mult
            bank.add(payout)
            msg.config(text=f"{name}!  You win ${payout}  ({mult}×)", fg=WIN)
            ev = "jackpot" if mult >= 25 else ("bigwin" if mult >= 6 else "win")
            db.react(ev, amt=payout, game="Video Poker")
            sfx.play(ev)
            stats.record("Video Poker", "win", payout - st["bet"], wager=st["bet"])
            if mult >= 6:
                fx.celebrate(win, payout, big=True)
        else:
            msg.config(text=f"{name}. Better luck next hand.", fg=LOSE)
            db.react("loss", game="Video Poker")
            sfx.play("lose")
            stats.record("Video Poker", "loss", -st["bet"], wager=st["bet"])
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

    action_btn = tk.Button(body, text="DEAL", font=("Segoe UI", 16, "bold"), command=action,
                           bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=40, pady=12)
    action_btn.pack(pady=14)

    # --- AI Strategy Coach: exact expected-value solver (runs off the UI thread) ---
    coach_lbl = tk.Label(body, text="", font=("Segoe UI", 11, "bold"), bg=FELT, fg=GOLD,
                         wraplength=560, justify="center")
    coach_lbl.pack(pady=(2, 0))

    def show_advice():
        if st["phase"] != "draw":
            coach_lbl.config(text="🧠  Deal a hand first — then I'll find the best cards to hold.")
            return
        coach_btn.config(state="disabled")
        coach_lbl.config(text="🧠  Analyzing every possible draw…")
        hand = list(st["cards"])

        def work():
            held, ev, reason = coach.video_poker_advice(hand)

            def done():
                coach_btn.config(state="normal")
                if st["phase"] != "draw" or st["cards"] != hand:
                    return                        # the hand changed while we were thinking
                coach_lbl.config(text=f"🧠  {reason}")
                for i in range(5):                # cyan dashed outline on the cards to keep
                    show_card(i)
                    if i in held:
                        card_canvases[i].create_rectangle(3, 3, CW + 5, CH + 5,
                                                          outline="#37bff0", width=3, dash=(4, 3))
            win.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    coach_btn = tk.Button(body, text="🧠  Best Hold?", font=("Segoe UI", 10, "bold"), bg=theme.NIGHT2,
                          fg=GOLD, activebackground="#232b4d", relief="flat", bd=0, padx=12, pady=5,
                          cursor="hand2", command=show_advice)
    coach_btn.pack(pady=(6, 2))

    def new_game():
        if st["phase"] == "draw":
            return                                  # don't abandon a hand mid-draw
        st["phase"] = "bet"
        st["cards"] = []
        st["held"] = [False] * 5
        for i in range(5):
            show_card(i)
        coach_lbl.config(text="")
        msg.config(text="New hand. Set your bet and press DEAL.", fg="white")
        refresh()

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(0, 16))
    tk.Button(bottom, text="🔄  New Game", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=new_game).pack(side="left", padx=6)
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "VIDEO POKER", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)

    for i in range(5):
        show_card(i)
    refresh()
    db.react("greeting", game="Video Poker")
