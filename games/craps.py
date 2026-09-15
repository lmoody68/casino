"""Craps table — Pass Line bet + true-odds bet.

Opens as its own window and reads/writes the shared casino ``bank``. Call
``open_game(parent, bank, on_change)``; ``on_change`` is fired whenever chips
change so the lobby can refresh its display.
"""
import tkinter as tk
import random

import theme
import coach
import dealer
import sfx
import fx
import stats
import players as players_mod

PIPS = {
    1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (2, 0), (0, 2), (2, 2)],
    5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
    6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)],
}
ODDS = {4: (2, 1), 10: (2, 1), 5: (3, 2), 9: (3, 2), 6: (6, 5), 8: (6, 5)}

FELT = "#0c1020"; DARKFELT = "#1e2647"; IVORY = "#f7faf5"
DOT = "#14312a"; GOLD = "#f6d365"; RED = "#e0616b"; WIN = "#7fe0a8"; BLUE = "#7cc7e8"
MIN_BET = 5

RULES = (
    "Craps — the Pass Line bet.\n\n"
    "1.  Set your bet and ROLL two dice (the 'come-out' roll):\n"
    "      •  7 or 11  →  you WIN\n"
    "      •  2, 3, or 12  →  you LOSE ('craps')\n"
    "      •  any other number  →  it becomes your POINT\n\n"
    "2.  With a point set, keep rolling:\n"
    "      •  roll the point again  →  WIN\n"
    "      •  roll a 7 first  →  LOSE ('seven out')\n\n"
    "ODDS BET (after a point is set) pays true odds — no house edge:\n"
    "      point 4 or 10 → 2:1   ·   5 or 9 → 3:2   ·   6 or 8 → 6:5"
)


def open_game(parent, bank, on_change):
    # Multiplayer: each player takes a turn as the SHOOTER (their own Pass Line +
    # odds); when their line resolves the dice pass to the next player. Solo
    # (players == 1) keeps the original single-player behavior.
    st = {"bet": 10, "odds": 0, "point": None, "busy": False, "_ended": False,
          "players": 1, "mode": "mix", "mp": False, "roster": None, "shooter": 0}

    def cur():
        return st["roster"][st["shooter"]] if st["mp"] and st["roster"] else None

    def cur_chips():
        p = cur()
        return players_mod.chips(p, bank) if p else bank.balance

    def pay(amount):
        p = cur()
        players_mod.add(p, amount, bank) if p else bank.add(amount)

    def is_you():
        p = cur()
        return (p is None) or p["kind"] == "you"

    def is_bot_turn():
        p = cur()
        return p is not None and p["kind"] == "bot"

    win = tk.Toplevel(parent)
    win.title("Craps")
    win.configure(bg=FELT)
    win.geometry("580x780")
    win.resizable(True, True)
    win.minsize(460, 520)
    theme.header(win, "CRAPS", w=580)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)          # scrollable so every control is always reachable

    chips_lbl = tk.Label(body, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips_lbl.pack(pady=(18, 4))
    db = dealer.DealerBox(body, win, felt=FELT)
    db.pack(fill="x", padx=18, pady=(0, 2))
    point_lbl = tk.Label(body, text="", font=("Segoe UI", 13, "bold"), bg=FELT, fg="white")
    point_lbl.pack()
    FELT_GREEN = "#0a6b3f"
    TW, TH = 540, 336
    table = tk.Canvas(body, width=TW, height=TH, bg=FELT, highlightthickness=0)
    table.pack(pady=(8, 4))
    msg = tk.Label(body, text="", font=("Segoe UI", 14, "bold"), bg=FELT, fg="white", wraplength=540)
    msg.pack(pady=(2, 6))

    MODES = [("Bots", "bots"), ("Humans", "humans"), ("Mix", "mix")]
    setup = tk.Frame(body, bg=FELT)
    setup.pack(pady=(0, 2))
    tk.Label(setup, text="Players:", font=("Segoe UI", 9), bg=FELT, fg=theme.MUTED).pack(side="left", padx=(0, 3))
    seat_btns = []
    for _n in range(1, 5):
        _b = tk.Button(setup, text=("Solo" if _n == 1 else str(_n)), font=("Segoe UI", 9, "bold"),
                       bg=(GOLD if _n == 1 else theme.NIGHT2), fg=(theme.INK if _n == 1 else GOLD),
                       activebackground="#232b4d", relief="flat", bd=0, padx=7, pady=3, cursor="hand2",
                       command=lambda n=_n: set_players(n))
        _b.pack(side="left", padx=2)
        seat_btns.append(_b)
    tk.Label(setup, text="   Others:", font=("Segoe UI", 9), bg=FELT, fg=theme.MUTED).pack(side="left", padx=(0, 3))
    mode_btns = []
    for _txt, _mv in MODES:
        _b = tk.Button(setup, text=_txt, font=("Segoe UI", 9, "bold"),
                       bg=(GOLD if _mv == "mix" else theme.NIGHT2), fg=(theme.INK if _mv == "mix" else GOLD),
                       activebackground="#232b4d", relief="flat", bd=0, padx=7, pady=3, cursor="hand2",
                       command=lambda m=_mv: set_mode(m))
        _b.pack(side="left", padx=2)
        mode_btns.append(_b)

    def _rr(x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return table.create_polygon(pts, smooth=True, **kw)

    def odds_payout(point, amount):
        num, den = ODDS[point]
        return (amount * num) // den

    def draw_static():
        table.delete("table")
        point = st["point"]
        _rr(14, 10, TW - 14, TH - 10, 26, fill=FELT_GREEN, outline=GOLD, width=4, tags="table")
        _rr(24, 20, TW - 24, TH - 20, 20, fill="", outline="#0a4d2c", width=2, tags="table")
        nums, bw, gap = [4, 5, 6, 8, 9, 10], 68, 12
        x0 = (TW - (len(nums) * bw + (len(nums) - 1) * gap)) / 2
        centers = {}
        for i, num in enumerate(nums):
            bx = x0 + i * (bw + gap)
            on = (num == point)
            _rr(bx, 28, bx + bw, 74, 8, fill=(GOLD if on else "#0d1b12"),
                outline=(GOLD if on else "#2f6b4a"), width=2, tags="table")
            table.create_text(bx + bw / 2, 51, text=str(num), font=("Georgia", 18, "bold"),
                              fill=("#151515" if on else "#dff0e6"), tags="table")
            centers[num] = bx + bw / 2
        _rr(70, TH - 74, TW - 70, TH - 30, 20, fill="", outline=GOLD, width=3, tags="table")
        table.create_text(TW / 2, TH - 60, text="P A S S   L I N E", font=("Georgia", 14, "bold"),
                          fill=GOLD, tags="table")
        table.create_text(TW / 2, TH - 43, text="7 or 11 win   ·   2  3  12 lose", font=("Segoe UI", 9),
                          fill="#8fd0ab", tags="table")
        if point in centers:                                # ON puck on the point box
            px = centers[point]
            table.create_oval(px - 15, 82, px + 15, 112, fill="white", outline="#111", width=2, tags="table")
            table.create_text(px, 97, text="ON", font=("Consolas", 9, "bold"), fill="#111", tags="table")
        else:                                               # OFF puck in the corner
            table.create_oval(32, 30, 60, 58, fill="#111", outline="white", width=2, tags="table")
            table.create_text(46, 44, text="OFF", font=("Consolas", 8, "bold"), fill="white", tags="table")
        table.tag_raise("dice")

    def draw_die(x0, y0, size, n):
        table.create_rectangle(x0, y0, x0 + size, y0 + size, fill=IVORY, outline="#0a3d29", width=4, tags="dice")
        step = size / 4
        r = size * 0.09
        for (col, rowp) in PIPS[n]:
            table.create_oval(x0 + step * (col + 1) - r, y0 + step * (rowp + 1) - r,
                              x0 + step * (col + 1) + r, y0 + step * (rowp + 1) + r,
                              fill=DOT, outline="", tags="dice")

    def draw_two(a, b):
        table.delete("dice")
        S, gap = 92, 28
        x = (TW - (2 * S + gap)) / 2
        draw_die(x, 138, S, a)
        draw_die(x + S + gap, 138, S, b)
        table.tag_raise("dice")

    def refresh():
        draw_static()                        # redraw felt/boxes so the point highlight stays current
        chips_now = cur_chips()
        if st["mp"]:
            chips_lbl.config(text=f"{players_mod.label(cur())}:  ${chips_now}")
        else:
            chips_lbl.config(text=f"CHIPS:  ${chips_now}")
        bet_lbl.config(text=f"Pass Line: ${st['bet']}")
        come_out = st["point"] is None
        broke = chips_now < MIN_BET
        human_turn = is_you() or (cur() is not None and cur()["kind"] == "human")
        note = f"🎲 {cur()['name']} shooting   ·   " if st["mp"] else ""
        if come_out:
            point_lbl.config(text=note + "POINT: OFF")
            odds_lbl.config(text="Odds: —  (set a point first)")
        else:
            num, den = ODDS[st["point"]]
            point_lbl.config(text=note + f"POINT: {st['point']}  ·  odds pay {num}:{den}")
            odds_lbl.config(text=f"Odds: ${st['odds']}"
                                 + (f"  → wins ${odds_payout(st['point'], st['odds'])}" if st["odds"] else ""))
        active = human_turn and not st["busy"]
        for b in (minus_btn, plus_btn):
            b.config(state="normal" if (come_out and active and not broke) else "disabled")
        room = chips_now - st["bet"] - st["odds"]
        for b in (odds_minus, odds_plus):
            b.config(state="normal" if (not come_out and active) else "disabled")
        odds_plus.config(state="normal" if (not come_out and active and room >= MIN_BET) else "disabled")
        roll_btn.config(state="disabled" if (st["busy"] or broke or not human_turn) else "normal")
        for b in seat_btns + mode_btns:
            b.config(state="disabled" if st["busy"] else "normal")
        reset_btn.pack_forget()
        if broke and not st["busy"] and is_you():
            msg.config(text="Out of chips! Head to the lobby to buy in.", fg=RED)
            reset_btn.pack(pady=6)
        on_change()

    def change_bet(d):
        st["bet"] = max(MIN_BET, min(st["bet"] + d, max(MIN_BET, cur_chips())))
        refresh()

    def change_odds(d):
        room = cur_chips() - st["bet"]
        st["odds"] = max(0, min(st["odds"] + d, room))
        refresh()

    def resolve(a, b):
        total = a + b
        bet = st["bet"]
        me = is_you()
        who = "You" if me else cur()["name"]
        if st["point"] is None:
            if total in (7, 11):
                pay(bet)
                msg.config(text=f"{a}+{b} = {total} — NATURAL! {who} win ${bet}!", fg=WIN)
                db.react("win", amt=bet, game="Craps"); sfx.play("win")
                if me:
                    stats.record("Craps", "win", bet, wager=bet)
                st["_ended"] = True
            elif total in (2, 3, 12):
                pay(-bet)
                msg.config(text=f"{a}+{b} = {total} — CRAPS! {who} lose ${bet}.", fg=RED)
                db.react("loss", game="Craps"); sfx.play("lose")
                if me:
                    stats.record("Craps", "loss", -bet, wager=bet)
                st["_ended"] = True
            else:
                st["point"] = total; st["odds"] = 0
                num, den = ODDS[total]
                msg.config(text=f"{a}+{b} = {total} is the POINT. Roll {total} before a 7! "
                                f"(odds pay {num}:{den})", fg=GOLD)
                db.react("point_set", point=total, game="Craps"); sfx.play("chip")
                st["_ended"] = False
        else:
            point = st["point"]
            if total == point:
                extra = odds_payout(point, st["odds"])
                pay(bet + extra)
                tail = f"  +${extra} on odds!" if st["odds"] else ""
                msg.config(text=f"{a}+{b} = {total} — POINT HIT! {who} win ${bet}{tail}", fg=WIN)
                db.react("bigwin" if extra else "win", amt=bet + extra, game="Craps")
                sfx.play("bigwin" if extra else "win")
                if me:
                    stats.record("Craps", "win", bet + extra, wager=bet + st["odds"])
                    fx.celebrate(win, bet + extra, big=bool(extra))
                st["point"] = None; st["odds"] = 0; st["_ended"] = True
            elif total == 7:
                lost = bet + st["odds"]
                pay(-lost)
                msg.config(text=f"{a}+{b} = {total} — SEVEN OUT! {who} lose ${lost}.", fg=RED)
                db.react("seven_out", game="Craps"); sfx.play("lose")
                if me:
                    stats.record("Craps", "loss", -lost, wager=lost)
                st["point"] = None; st["odds"] = 0; st["_ended"] = True
            else:
                msg.config(text=f"{a}+{b} = {total} — no decision. Roll again for {point}.", fg=BLUE)
                st["_ended"] = False
        refresh()
        if st["mp"]:
            after_resolve()

    def _do_roll():
        if st["busy"]:
            return
        if st["point"] is None and cur_chips() < MIN_BET:
            return
        st["busy"] = True
        sfx.play("dice")
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

    def roll(event=None):
        if st["mp"] and is_bot_turn():
            return                                   # can't roll for a bot
        _do_roll()

    # ---------------- multiplayer: rotating shooters ----------------
    def after_resolve():
        if st["_ended"]:
            win.after(1700, pass_dice)               # line resolved — dice go to the next player
        elif is_bot_turn():
            if st["point"] is not None and st["odds"] == 0:   # bot backs its point with odds once
                room = cur_chips() - st["bet"]
                if room >= MIN_BET:
                    st["odds"] = min(st["bet"], room)
                    refresh()
            win.after(1100, _do_roll)

    def pass_dice():
        st["shooter"] = (st["shooter"] + 1) % len(st["roster"])
        start_turn()

    def start_turn():
        st["point"] = None
        st["odds"] = 0
        st["busy"] = False
        p = cur()
        if p["kind"] != "you" and p["stack"] < MIN_BET:
            p["stack"] = players_mod.START_STACK    # rebuy so the table keeps going
        st["bet"] = max(MIN_BET, min(st["bet"], max(MIN_BET, cur_chips())))
        draw_two(1, 1)
        if p["kind"] == "bot":
            st["bet"] = max(MIN_BET, min(random.choice([10, 15, 20, 25]), cur_chips()))
            msg.config(text=f"{p['name']} is shooting — ${st['bet']} on the Pass Line.", fg=GOLD)
            refresh()
            win.after(1100, _do_roll)
        else:
            who = "Your" if p["kind"] == "you" else f"{p['name']}'s"
            note = "" if p["kind"] == "you" else "  (pass the dice)"
            msg.config(text=f"{who} turn to shoot — set your bet and ROLL{note}.", fg="white")
            refresh()

    def set_players(n):
        if st["busy"]:
            return
        st["players"] = n
        st["mp"] = n > 1
        for i, b in enumerate(seat_btns):
            on = (i + 1) == n
            b.config(bg=GOLD if on else theme.NIGHT2, fg=theme.INK if on else GOLD)
        if st["mp"]:
            st["roster"] = players_mod.build(n, st["mode"])
            st["shooter"] = 0
            start_turn()
        else:
            st["roster"] = None
            st["point"] = None; st["odds"] = 0; st["busy"] = False
            draw_two(1, 1)
            msg.config(text="Pass Line bet. Roll 7 or 11 to win, 2/3/12 to lose. Good luck!", fg="white")
            refresh()

    def set_mode(m):
        if st["busy"]:
            return
        st["mode"] = m
        for b, (_, mval) in zip(mode_btns, MODES):
            on = mval == m
            b.config(bg=GOLD if on else theme.NIGHT2, fg=theme.INK if on else GOLD)
        if st["mp"]:
            st["roster"] = players_mod.build(st["players"], m)
            st["shooter"] = 0
            start_turn()

    bet_frame = tk.Frame(body, bg=FELT); bet_frame.pack(pady=(4, 2))
    minus_btn = tk.Button(bet_frame, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(bet_frame, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=15)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(bet_frame, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    odds_frame = tk.Frame(body, bg=FELT); odds_frame.pack(pady=(2, 4))
    odds_minus = tk.Button(odds_frame, text="–", font=("Segoe UI", 13, "bold"), width=3,
                           command=lambda: change_odds(-MIN_BET), bg=DARKFELT, fg=BLUE, relief="flat")
    odds_minus.pack(side="left", padx=4)
    odds_lbl = tk.Label(odds_frame, text="", font=("Consolas", 13, "bold"), bg=FELT, fg=BLUE, width=22)
    odds_lbl.pack(side="left", padx=4)
    odds_plus = tk.Button(odds_frame, text="+", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_odds(MIN_BET), bg=DARKFELT, fg=BLUE, relief="flat")
    odds_plus.pack(side="left", padx=4)

    roll_btn = tk.Button(body, text="🎲🎲   ROLL", font=("Segoe UI", 16, "bold"), command=roll,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=30, pady=12)
    roll_btn.pack(pady=14)

    def new_game():
        if st["busy"]:
            return
        st["point"] = None
        st["odds"] = 0
        draw_two(1, 1)
        if st["mp"]:
            st["shooter"] = 0
            start_turn()
        else:
            msg.config(text="New round. Roll 7 or 11 to win, 2/3/12 to lose. Good luck!", fg="white")
            refresh()

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(0, 16))
    tk.Button(bottom, text="🔄  New Game", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=new_game).pack(side="left", padx=6)
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "CRAPS", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="🧠  Odds Tip", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: msg.config(text=coach.CRAPS_TIP, fg=GOLD)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)
    reset_btn = tk.Button(body, text="(broke — buy in from the lobby)", font=("Segoe UI", 10),
                          bg=FELT, fg=RED, relief="flat", state="disabled")

    win.bind("<space>", roll)
    draw_two(1, 1)
    msg.config(text="Pass Line bet. Roll 7 or 11 to win, 2/3/12 to lose. Good luck!")
    refresh()
    db.react("greeting", game="Craps")
