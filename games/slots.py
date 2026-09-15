"""Slot machine — three reels, classic symbols.

Match three-of-a-kind for a payout (rarer symbol = bigger multiple of your bet),
or land two cherries for a small win. Symbol odds are weighted so the big payouts
are genuinely rare — that's the built-in house edge. Uses the shared casino ``bank``.
"""
import tkinter as tk
import random

FELT = "#0e5a3c"; DARKFELT = "#0a4630"; IVORY = "#f7faf5"; GOLD = "#f4d35e"
WIN = "#8fe6b8"; LOSE = "#e06a5c"
MIN_BET = 5

CHERRY, LEMON, BELL, STAR, DIAMOND, SEVEN = "🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"

# how often each symbol appears on a reel (common -> rare)
REEL = ([CHERRY] * 6 + [LEMON] * 5 + [BELL] * 4 + [STAR] * 3 + [DIAMOND] * 2 + [SEVEN] * 1)

# three-of-a-kind payout, as a multiple of the bet
THREE = {CHERRY: 4, LEMON: 6, BELL: 10, STAR: 20, DIAMOND: 50, SEVEN: 100}


def open_game(parent, bank, on_change):
    st = {"bet": 10, "busy": False}

    win = tk.Toplevel(parent)
    win.title("Slots")
    win.configure(bg=FELT)
    win.geometry("520x560")
    win.resizable(False, False)

    chips = tk.Label(win, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(18, 6))

    reel_frame = tk.Frame(win, bg=DARKFELT, bd=0)
    reel_frame.pack(pady=10)
    reels = []
    for c in range(3):
        r = tk.Label(reel_frame, text="🎰", font=("Segoe UI Emoji", 46), bg=IVORY, fg="#111",
                     width=2, padx=10, pady=6)
        r.grid(row=0, column=c, padx=6, pady=10)
        reels.append(r)

    msg = tk.Label(win, text="Match 3 to win. Three 7️⃣ = 100× JACKPOT!",
                   font=("Segoe UI", 13, "bold"), bg=FELT, fg="white", wraplength=460)
    msg.pack(pady=(8, 6))

    paytable = tk.Label(
        win, bg=FELT, fg="#b9d6c7", font=("Consolas", 10),
        text="🍒🍒🍒 4×   🍋🍋🍋 6×   🔔🔔🔔 10×\n⭐⭐⭐ 20×   💎💎💎 50×   7️⃣7️⃣7️⃣ 100×   ·   any two 🍒 = 2×")
    paytable.pack(pady=(0, 6))

    betrow = tk.Frame(win, bg=FELT)
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
            amt = st["bet"] * THREE[a]
            bank.add(amt)
            tag = "JACKPOT!!!" if a == SEVEN else "THREE OF A KIND!"
            msg.config(text=f"{a}{b}{c}  —  {tag}  You win ${amt}!", fg=WIN)
        elif final.count(CHERRY) == 2:
            amt = st["bet"] * 2
            bank.add(amt)
            msg.config(text=f"{a}{b}{c}  —  two cherries! You win ${amt}!", fg=WIN)
        else:
            bank.add(-st["bet"])
            msg.config(text=f"{a}{b}{c}  —  no match. You lose ${st['bet']}.", fg=LOSE)
        refresh()

    def spin(event=None):
        if st["busy"] or bank.balance < st["bet"]:
            return
        st["busy"] = True
        refresh()
        final = [random.choice(REEL) for _ in range(3)]
        stops = (12, 18, 24)      # each reel locks a little later, for suspense

        def step(i):
            for r in range(3):
                reels[r].config(text=final[r] if i >= stops[r] else random.choice(REEL))
            if i < stops[-1]:
                win.after(60, lambda: step(i + 1))
            else:
                resolve(final)
        step(0)

    minus_btn = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    spin_btn = tk.Button(win, text="🎰  SPIN", font=("Segoe UI", 16, "bold"), command=spin,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=34, pady=12)
    spin_btn.pack(pady=14)

    win.bind("<space>", spin)
    refresh()
