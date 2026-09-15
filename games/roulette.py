"""Roulette table — European single-zero wheel (numbers 0-36).

Outside bets (red/black, even/odd, low/high) pay 1:1; a straight-up number pays
35:1. The lone green 0 is the house edge — it loses every outside bet. Reads and
writes the shared casino ``bank``.
"""
import tkinter as tk
import math
import random

import theme
import coach
import dealer
import sfx
import fx
import stats
import players as players_mod

RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
# the real order of pockets around a European wheel
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
               5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

FELT = "#0c1020"; DARKFELT = "#1e2647"; IVORY = "#f7faf5"; GOLD = "#f6d365"
RED = "#c0392b"; BLACK = "#161616"; GREEN = "#1e8f5e"; WIN = "#7fe0a8"; LOSE = "#e0616b"
MIN_BET = 5

RULES = (
    "Roulette — European wheel, numbers 0 to 36.\n\n"
    "Pick a bet, set your chips, and SPIN.\n\n"
    "OUTSIDE BETS (each pays 1:1):\n"
    "      Red / Black   ·   Even / Odd   ·   1-18 / 19-36\n\n"
    "SINGLE NUMBER (pays 35:1):\n"
    "      pick an exact number from 0 to 36.\n\n"
    "The lone green 0 loses every outside bet — that's the house edge."
)

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


BET_LABELS = {"red": "Red", "black": "Black", "even": "Even", "odd": "Odd",
              "low": "1-18", "high": "19-36", "number": "#"}


def open_game(parent, bank, on_change):
    # Multiplayer: when "players" > 1, a roster takes turns placing bets, then ONE
    # spin resolves everyone. Solo (players == 1) keeps the original behavior.
    st = {"bet": 10, "busy": False, "players": 1, "mode": "mix",
          "mp": False, "roster": None, "turn": 0, "bets": {}}

    win = tk.Toplevel(parent)
    win.title("Roulette")
    win.configure(bg=FELT)
    win.geometry("560x760")
    win.resizable(True, True)
    win.minsize(420, 480)
    theme.header(win, "ROULETTE", w=560)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)          # all controls live in a scrollable area

    chips = tk.Label(body, text="", font=("Consolas", 20, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(10, 2))

    db = dealer.DealerBox(body, win, felt=FELT)
    db.pack(fill="x", padx=18, pady=(0, 2))

    # --- the drawn roulette wheel (grows with the window width; scroll to reach controls) ---
    wheel = tk.Canvas(body, bg=FELT, highlightthickness=0, width=460, height=460)
    wheel.pack(pady=(2, 0))
    result = tk.Label(body, text="", font=("Consolas", 15, "bold"), bg=FELT, fg=GOLD)
    result.pack()
    _seg = 360 / 37
    _geo = {"cx": 230, "cy": 230, "R": 214}
    _ball = [None]
    _ball_angle = [90.0]

    def _ang(idx):
        return 90 - (idx + 0.5) * _seg           # math-degrees of pocket center (0 at top, clockwise)

    def _xy(radius, deg):
        r = math.radians(deg)
        return _geo["cx"] + radius * math.cos(r), _geo["cy"] - radius * math.sin(r)

    def place_ball(deg):
        _ball_angle[0] = deg
        R = _geo["R"]
        bx, by = _xy(R * 0.90, deg)
        br = max(4, R * 0.05)
        if _ball[0] is None:
            _ball[0] = wheel.create_oval(bx - br, by - br, bx + br, by + br, fill="white", outline="#b9b9b9", width=1)
        else:
            wheel.coords(_ball[0], bx - br, by - br, bx + br, by + br)
        wheel.tag_raise(_ball[0])

    def draw_wheel():
        wheel.delete("wheel")
        cx, cy, R = _geo["cx"], _geo["cy"], _geo["R"]
        fs = max(6, int(R * 0.066))
        wheel.create_oval(cx - R - 7, cy - R - 7, cx + R + 7, cy + R + 7,
                          fill="#3a2a12", outline=GOLD, width=3, tags="wheel")
        for i, num in enumerate(WHEEL_ORDER):
            col = GREEN if num == 0 else (RED if num in RED_NUMS else "#141414")
            wheel.create_arc(cx - R, cy - R, cx + R, cy + R, start=_ang(i) - _seg / 2,
                             extent=_seg, fill=col, outline="#0a0d14", width=1, style="pieslice", tags="wheel")
            tx, ty = _xy(R * 0.82, _ang(i))
            wheel.create_text(tx, ty, text=str(num), font=("Consolas", fs, "bold"), fill="white", tags="wheel")
        hub = R * 0.26
        wheel.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill=DARKFELT, outline=GOLD, width=2, tags="wheel")
        wheel.create_text(cx, cy, text="◆", font=("Segoe UI", max(10, int(R * 0.13)), "bold"), fill=GOLD, tags="wheel")
        place_ball(_ball_angle[0])

    # size the wheel to the available width so it grows when the window is maximized
    _last_w = [0]

    def _size_wheel(e=None):
        avail = win.winfo_width() - 60                     # window width minus scrollbar + padding
        size = max(300, min(avail, 900))                   # square wheel, sensibly capped
        if abs(size - _last_w[0]) < 8:                     # ignore tiny/height-only jitters
            return
        _last_w[0] = size
        wheel.config(width=size, height=size)
        _geo["cx"] = _geo["cy"] = size / 2
        _geo["R"] = size / 2 - 16
        draw_wheel()

    win.bind("<Configure>", _size_wheel)
    win.after(120, _size_wheel)
    draw_wheel()

    msg = tk.Label(body, text="Pick a bet, set your chips, and SPIN!",
                   font=("Segoe UI", 13, "bold"), bg=FELT, fg="white", wraplength=500)
    msg.pack(pady=(6, 8))

    MODES = [("Bots", "bots"), ("Humans", "humans"), ("Mix", "mix")]
    setup = tk.Frame(body, bg=FELT)
    setup.pack(pady=(0, 4))
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

    bettype = tk.StringVar(value="red")

    outside = tk.Frame(body, bg=FELT)
    outside.pack()
    for i, (lbl, val) in enumerate(OUTSIDE):
        tk.Radiobutton(outside, text=f"{lbl}\n1:1", value=val, variable=bettype,
                       font=("Segoe UI", 11, "bold"), width=8, height=2, indicatoron=False,
                       bg=DARKFELT, fg="white", selectcolor="#12704c",
                       activebackground="#12704c", relief="flat").grid(row=i // 3, column=i % 3, padx=5, pady=5)

    numrow = tk.Frame(body, bg=FELT)
    numrow.pack(pady=(10, 4))
    tk.Radiobutton(numrow, text="Single number (35:1):", value="number", variable=bettype,
                   font=("Segoe UI", 11, "bold"), indicatoron=False, bg=DARKFELT, fg=GOLD,
                   selectcolor="#12704c", activebackground="#12704c", relief="flat", padx=8, pady=6).pack(side="left", padx=4)
    numspin = tk.Spinbox(numrow, from_=0, to=36, width=4, font=("Consolas", 14, "bold"),
                         justify="center")
    numspin.pack(side="left", padx=4)

    betrow = tk.Frame(body, bg=FELT)
    betrow.pack(pady=(12, 4))

    def cur_player():
        if st["mp"] and st["roster"] and st["turn"] < len(st["roster"]):
            return st["roster"][st["turn"]]
        return None

    def cur_chips():
        p = cur_player()
        return players_mod.chips(p, bank) if p else bank.balance

    def refresh():
        if st["mp"]:
            p = cur_player()
            chips.config(text=f"{players_mod.label(p)}:  ${cur_chips()}" if p else "Spinning…")
            spin_btn.config(text="✅  LOCK IN")
        else:
            chips.config(text=f"CHIPS:  ${bank.balance}")
            spin_btn.config(text="🔴  SPIN")
        bet_lbl.config(text=f"Bet: ${st['bet']}")
        broke = (not st["mp"]) and bank.balance < MIN_BET
        for b in (minus_btn, plus_btn):
            b.config(state="disabled" if st["busy"] else "normal")
        spin_btn.config(state="disabled" if (st["busy"] or broke) else "normal")
        for b in seat_btns + mode_btns:
            b.config(state="disabled" if st["busy"] else "normal")
        if broke and not st["busy"]:
            msg.config(text="Out of chips! Buy in from the lobby.", fg=LOSE)
        on_change()

    def change_bet(d):
        cap = cur_chips() if st["mp"] else bank.balance
        st["bet"] = max(MIN_BET, min(st["bet"] + d, max(MIN_BET, cap)))
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
            big = amt >= st["bet"] * 10
            db.react("bigwin" if big else "win", amt=amt, game="Roulette")
            sfx.play("bigwin" if big else "win")
            stats.record("Roulette", "win", amt, wager=st["bet"])
            if big:
                fx.celebrate(win, amt, big=True)
        else:
            bank.add(-st["bet"])
            msg.config(text=f"{n} {color_name(n)} — you lose ${st['bet']}.", fg=LOSE)
            db.react("loss", game="Roulette")
            sfx.play("lose")
            stats.record("Roulette", "loss", -st["bet"], wager=st["bet"])
        refresh()

    def animate_spin(on_done):
        result.config(text="")
        n = random.randint(0, 36)
        target = _ang(WHEEL_ORDER.index(n))
        start, end, N = 90.0, target - 360 * 4, 52       # 4 loops clockwise, then rest on n

        def ease(p):
            return 1 - (1 - p) ** 3

        def step(t):
            p = t / N
            place_ball(start + ease(p) * (end - start))
            if t < N:
                win.after(int(24 + p * 46), lambda: step(t + 1))
            else:
                place_ball(target)
                rc = GREEN if n == 0 else ("#e0616b" if n in RED_NUMS else "white")
                result.config(text=f"{n}  ·  {color_name(n)}", fg=rc)
                on_done(n)
        step(0)

    def spin(event=None):
        if st["busy"]:
            return
        if st["mp"]:
            lock_in()
            return
        if bank.balance < st["bet"]:
            return
        st["busy"] = True
        refresh()
        animate_spin(resolve)

    # ---------------- multiplayer: take turns, then one spin resolves everyone ----------------
    def _cur_number():
        try:
            return int(numspin.get())
        except (ValueError, tk.TclError):
            return 0

    def bet_text(bet):
        if bet["amount"] < MIN_BET:
            return "no bet"
        lab = f"#{bet['number']}" if bet["kind"] == "number" else BET_LABELS.get(bet["kind"], bet["kind"])
        return f"{lab} ${bet['amount']}"

    def bot_pick(p):
        avail = players_mod.chips(p, bank)
        amt = min(random.choice([10, 15, 20, 25]), avail)
        if amt < MIN_BET:
            return {"kind": "red", "number": 0, "amount": 0}
        if random.random() < 0.2:
            return {"kind": "number", "number": random.randint(0, 36), "amount": amt}
        return {"kind": random.choice([v for _, v in OUTSIDE]), "number": 0, "amount": amt}

    def start_round():
        st["turn"] = 0
        st["bets"] = {}
        st["busy"] = False
        prompt_turn()

    def prompt_turn():
        p = cur_player()
        st["bet"] = max(MIN_BET, min(st["bet"], max(MIN_BET, cur_chips())))
        if p["kind"] == "you":
            msg.config(text="YOUR turn — pick a bet and LOCK IN.", fg="white")
        else:
            msg.config(text=f"Pass to {p['name']} — pick a bet and LOCK IN.", fg=GOLD)
        refresh()

    def lock_in():
        amt = min(st["bet"], cur_chips())
        if amt < MIN_BET:
            amt = 0
        st["bets"][st["turn"]] = {"kind": bettype.get(), "number": _cur_number(), "amount": amt}
        st["turn"] += 1
        step_turn()

    def step_turn():
        if st["turn"] >= len(st["roster"]):
            do_spin_mp()
            return
        p = cur_player()
        if p["kind"] == "bot":
            bet = bot_pick(p)
            st["bets"][st["turn"]] = bet
            st["busy"] = True
            msg.config(text=f"{p['name']} bets {bet_text(bet)}.", fg=GOLD)
            refresh()
            st["turn"] += 1
            win.after(900, step_turn)
        else:
            st["busy"] = False
            prompt_turn()

    def do_spin_mp():
        st["busy"] = True
        refresh()
        animate_spin(resolve_all)

    def resolve_all(n):
        lines, net_you, you_wager = [], 0, 0
        for idx in sorted(st["bets"]):
            bet = st["bets"][idx]
            p = st["roster"][idx]
            if bet["amount"] < MIN_BET:
                lines.append(f"{p['name']}: —")
                continue
            if wins(n, bet["kind"], bet["number"]):
                amt = bet["amount"] * (35 if bet["kind"] == "number" else 1)
                players_mod.add(p, amt, bank)
                lines.append(f"{p['name']}: +${amt}")
                if p["kind"] == "you":
                    net_you += amt; you_wager = bet["amount"]
            else:
                players_mod.add(p, -bet["amount"], bank)
                lines.append(f"{p['name']}: −${bet['amount']}")
                if p["kind"] == "you":
                    net_you -= bet["amount"]; you_wager = bet["amount"]
        msg.config(text=f"{n} {color_name(n)}   ·   " + "   ".join(lines),
                   fg=WIN if net_you > 0 else (LOSE if net_you < 0 else GOLD))
        if you_wager:
            if net_you > 0:
                big = net_you >= you_wager * 10
                stats.record("Roulette", "win", net_you, wager=you_wager)
                db.react("bigwin" if big else "win", amt=net_you, game="Roulette")
                sfx.play("bigwin" if big else "win")
                if big:
                    fx.celebrate(win, net_you, big=True)
            elif net_you < 0:
                stats.record("Roulette", "loss", net_you, wager=you_wager)
                db.react("loss", game="Roulette"); sfx.play("lose")
        win.after(2600, start_round)

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
            start_round()
        else:
            st["roster"] = None
            st["turn"], st["bets"] = 0, {}
            msg.config(text="Pick a bet, set your chips, and SPIN!", fg="white")
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
            start_round()

    minus_btn = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                          command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus_btn.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus_btn = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                         command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus_btn.pack(side="left", padx=4)

    spin_btn = tk.Button(body, text="🔴  SPIN", font=("Segoe UI", 16, "bold"), command=spin,
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat", padx=34, pady=12)
    spin_btn.pack(pady=16)

    def new_game():
        if st["busy"]:
            return
        result.config(text="")
        place_ball(90)
        if st["mp"]:
            start_round()
        else:
            msg.config(text="Pick a bet, set your chips, and SPIN!", fg="white")

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(0, 16))
    tk.Button(bottom, text="🔄  New Game", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=new_game).pack(side="left", padx=6)
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "ROULETTE", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="🧠  Odds Tip", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: msg.config(text=coach.ROULETTE_TIP, fg=GOLD)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)

    win.bind("<space>", spin)
    refresh()
    db.react("greeting", game="Roulette")
