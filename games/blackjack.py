"""Blackjack (21) — play against the dealer.

Standard rules: get closer to 21 than the dealer without going over. Hit, stand,
or double down. Dealer draws to 17 and stands on 17+. Blackjack (21 on the first
two cards) pays 3:2. Uses the shared card renderer and casino bank.
"""
import tkinter as tk
import random

import theme
import cards
import coach
import dealer
import sfx
import fx
import stats
import profile

FELT = "#0c1020"; DARKFELT = "#1e2647"; IVORY = "#f7faf5"; GOLD = "#f6d365"
WIN = "#7fe0a8"; LOSE = "#e0616b"; PUSH = "#7cc7e8"
MIN_BET = 5
CW, CH, OFF = 76, 106, 30
BOT_NAMES = ["Rosa", "Duke", "Mika", "Sal", "Nina", "Gus", "Lola", "Vic"]

RULES = (
    "Beat the dealer by getting closer to 21 — without going over.\n\n"
    "Card values:  2-10 = face value  ·  J/Q/K = 10  ·  Ace = 1 or 11\n\n"
    "1.  Bet, then DEAL — you get 2 cards, the dealer gets 2 (one hidden).\n"
    "2.  HIT to take a card, STAND to stop.\n"
    "3.  DOUBLE doubles your bet for exactly one more card.\n"
    "4.  SPLIT a matching pair into two hands (each gets its own bet). You can\n"
    "     double after a split, and re-split up to four hands. Split Aces get\n"
    "     one card each. A 21 after a split counts as 21, not a blackjack.\n"
    "5.  Go over 21 and you BUST (that hand loses).\n"
    "6.  Then the dealer draws to 17 and must stand on 17 or more.\n\n"
    "Higher total without busting wins.\n"
    "Win pays 1:1  ·  Blackjack (21 on first two cards) pays 3:2  ·  tie = push."
)


def card_value(r):
    if r == 14:
        return 11
    if r >= 11:
        return 10
    return r


def hand_value(hand):
    total = sum(card_value(r) for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == 14)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_blackjack(hand):
    return len(hand) == 2 and hand_value(hand) == 21


def open_game(parent, bank, on_change):
    # Multi-hand model: "hands" is a list so a split can produce several player hands.
    # Each hand = {"cards":[...], "bet":int, "done":bool, "result":None|str, "ace":bool}.
    # "bots" are computer players who share the shoe and play basic strategy (flavor only,
    # they don't touch your bank). "num_bots" is the chosen table size; "th" is table height.
    st = {"bet": 10, "phase": "bet", "dealer": [], "deck": [], "reveal": False,
          "hands": [], "active": 0, "bots": [], "num_bots": 0, "th": 400}

    win = tk.Toplevel(parent)
    win.title("Blackjack")
    win.configure(bg=FELT)
    win.geometry("560x760")
    win.resizable(True, True)
    win.minsize(460, 520)
    theme.header(win, "BLACKJACK", w=560)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)          # scrollable so every control is always reachable

    chips = tk.Label(body, text="", font=("Consolas", 18, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(10, 6))

    ace = dealer.DealerBox(body, win, felt=FELT)
    ace.pack(fill="x", padx=18, pady=(0, 4))

    FELT_GREEN = "#0a6b3f"
    TW = 500
    table = tk.Canvas(body, width=TW, height=st["th"], bg=FELT, highlightthickness=0)
    table.pack(pady=(4, 2))

    def _rrt(x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return table.create_polygon(pts, smooth=True, **kw)

    def draw_table():
        th = st["th"]
        _rrt(12, 14, TW - 12, th - 8, 130, fill=FELT_GREEN, outline=GOLD, width=4)
        _rrt(22, 24, TW - 22, th - 18, 122, fill="", outline="#0a4d2c", width=2)
        if not st["bots"]:                                # decorative text tucked under the dealer
            table.create_text(TW / 2, 174, text="BLACKJACK   PAYS   3   TO   2",
                              font=("Georgia", 13, "bold"), fill="#dff0e6")
            table.create_text(TW / 2, 194, text="Dealer must stand on 17",
                              font=("Segoe UI", 9), fill="#8fd0ab")

    def draw_hand_on(hand, y, hide_hole):
        n = len(hand)
        if not n:
            return
        sx = TW / 2 - (CW + (n - 1) * OFF) / 2
        for i, (r, s) in enumerate(hand):
            x = sx + i * OFF
            if hide_hole and i == 1:
                cards.draw_card(table, x, y, CW, CH, face_up=False)
            else:
                cards.draw_card(table, x, y, CW, CH, r, s, face_up=True)

    def draw_player_hands():
        """Draw every player hand across the bottom of the felt, highlighting the
        active one. Cards shrink as more hands appear so splits still fit."""
        hands = st["hands"]
        if not hands:
            return
        H = len(hands)
        cw, ch, off = (76, 106, 30) if H == 1 else (60, 84, 22) if H == 2 else (46, 64, 16)
        usable = TW - 30
        slotw = usable / H
        y = st["th"] - ch - 48
        table.create_text(TW / 2, y - 30, text=profile.name().upper(),
                          font=("Georgia", 11, "bold"), fill=GOLD)
        for i, hand in enumerate(hands):
            cx = 15 + slotw * (i + 0.5)
            cl = hand["cards"]
            handw = cw + (len(cl) - 1) * off
            sx = cx - handw / 2
            is_active = st["phase"] == "player" and i == st["active"] and not hand["done"]
            if is_active:                                     # gold frame around the live hand
                table.create_rectangle(cx - slotw / 2 + 3, y - 20, cx + slotw / 2 - 3, y + ch + 20,
                                       outline=GOLD, width=2)
            for j, (r, s) in enumerate(cl):
                cards.draw_card(table, sx + j * off, y, cw, ch, r, s, face_up=True)
            col = GOLD if is_active else "#dff0e6"
            table.create_text(cx, y - 12, text=f"${hand['bet']} · {hand_value(cl)}",
                              font=("Consolas", 9, "bold"), fill=col)
            res = hand["result"]
            if res:
                rc = {"win": WIN, "loss": LOSE, "bust": LOSE, "push": PUSH, "bj": GOLD}.get(res, IVORY)
                table.create_text(cx, y + ch + 10, text=res.upper(), font=("Consolas", 10, "bold"), fill=rc)

    def draw_bots():
        """Draw the computer players' seats in a compact strip below the dealer."""
        bots = st["bots"]
        if not bots:
            return
        cwb, chb, offb = 30, 42, 12
        n = len(bots)
        slotw = (TW - 40) / n
        y = 172
        for i, bot in enumerate(bots):
            cx = 20 + slotw * (i + 0.5)
            cl = bot["cards"]
            handw = cwb + (len(cl) - 1) * offb
            sx = cx - handw / 2
            for j, (r, s) in enumerate(cl):
                cards.draw_card(table, sx + j * offb, y, cwb, chb, r, s, face_up=True)
            table.create_text(cx, y - 10, text=f"{bot['name']}  ·  ${bot['bet']}",
                              font=("Georgia", 9, "bold"), fill="#dff0e6")
            res = bot["result"]
            if res:
                rc = {"win": WIN, "loss": LOSE, "bust": LOSE, "push": PUSH, "bj": GOLD}.get(res, IVORY)
                table.create_text(cx, y + chb + 8, text=f"{hand_value(cl)} · {res.upper()}",
                                  font=("Consolas", 8, "bold"), fill=rc)
            else:
                table.create_text(cx, y + chb + 8, text=f"{hand_value(cl)}",
                                  font=("Consolas", 8, "bold"), fill="#8fd0ab")

    msg = tk.Label(body, text="Set your bet and press DEAL.", font=("Segoe UI", 13, "bold"),
                   bg=FELT, fg="white", wraplength=520)
    msg.pack(pady=6)

    def render():
        table.delete("all")
        draw_table()
        if st["reveal"] and st["dealer"]:
            dlab = f"DEALER — {hand_value(st['dealer'])}"
        elif st["dealer"]:
            dlab = f"DEALER — {card_value(st['dealer'][0][0])} + ?"
        else:
            dlab = "DEALER"
        table.create_text(TW / 2, 30, text=dlab, font=("Consolas", 11, "bold"), fill=GOLD)
        draw_hand_on(st["dealer"], 44, not st["reveal"])
        draw_bots()
        draw_player_hands()

    def active_hand():
        return st["hands"][st["active"]] if st["hands"] else None

    def can_split(h):
        return (st["phase"] == "player" and h is not None and len(h["cards"]) == 2 and not h["done"]
                and card_value(h["cards"][0][0]) == card_value(h["cards"][1][0])
                and len(st["hands"]) < 4 and bank.balance >= h["bet"])

    def can_double(h):
        return (st["phase"] == "player" and h is not None and len(h["cards"]) == 2 and not h["done"]
                and not h["ace"] and bank.balance >= h["bet"])

    def refresh():
        chips.config(text=f"CHIPS:  ${bank.balance}")
        bet_lbl.config(text=f"Bet: ${st['bet']}")
        betting = st["phase"] in ("bet", "done")
        broke = bank.balance < MIN_BET
        for b in (minus, plus):
            b.config(state="normal" if (betting and not broke) else "disabled")
        for b in seat_btns:
            b.config(state="normal" if betting else "disabled")     # table size locked during a hand
        deal_btn.config(state="normal" if (betting and not broke) else "disabled")
        playing = st["phase"] == "player"
        h = active_hand()
        live = playing and h is not None and not h["done"]
        hit_btn.config(state="normal" if (live and not h["ace"]) else "disabled")
        stand_btn.config(state="normal" if live else "disabled")
        dbl_btn.config(state="normal" if can_double(h) else "disabled")
        split_btn.config(state="normal" if can_split(h) else "disabled")
        on_change()

    def change_bet(d):
        if st["phase"] not in ("bet", "done"):
            return
        st["bet"] = max(MIN_BET, min(st["bet"] + d, bank.balance))
        refresh()

    def prompt_active():
        h = active_hand()
        if h is None:
            return
        opts = ["Hit", "Stand"]
        if can_double(h):
            opts.append("Double")
        if can_split(h):
            opts.append("Split")
        n = len(st["hands"])
        prefix = f"Hand {st['active'] + 1} of {n} — " if n > 1 else ""
        msg.config(text=prefix + " · ".join(opts) + "?", fg="white")

    def advance():
        """Move to the next unfinished hand; when none remain, the dealer plays."""
        for i in range(st["active"] + 1, len(st["hands"])):
            if not st["hands"][i]["done"]:
                st["active"] = i
                render(); prompt_active(); refresh()
                return
        finish_player()

    def play_bots():
        """Each computer player draws using the same basic strategy as the Coach."""
        up = st["dealer"][0][0]
        for bot in st["bots"]:
            while hand_value(bot["cards"]) < 21:
                move, _ = coach.blackjack_advice(bot["cards"], up, can_double=False)
                if move == "STAND":
                    break
                bot["cards"].append(st["deck"].pop())

    def settle_bots():
        """Set each bot's result vs the dealer (display only — never touches your bank)."""
        dv = hand_value(st["dealer"])
        for bot in st["bots"]:
            pv = hand_value(bot["cards"])
            if pv > 21:
                bot["result"] = "bust"
            elif dv > 21 or pv > dv:
                bot["result"] = "win"
            elif pv < dv:
                bot["result"] = "loss"
            else:
                bot["result"] = "push"

    def finish_player():
        st["reveal"] = True
        play_bots()
        live = (any(hand_value(h["cards"]) <= 21 for h in st["hands"])
                or any(hand_value(b["cards"]) <= 21 for b in st["bots"]))
        if live:                                          # dealer draws only if a hand is still alive
            while hand_value(st["dealer"]) < 17:
                st["dealer"].append(st["deck"].pop())
        settle_bots()
        render()
        settle_all()

    def settle_dealer_bj():
        """Dealer has Blackjack on the deal — resolve everyone immediately (dealer peek)."""
        for bot in st["bots"]:
            bot["result"] = "push" if is_blackjack(bot["cards"]) else "loss"
        net = 0
        for h in st["hands"]:
            w = h["bet"]
            if is_blackjack(h["cards"]):
                bank.add(w); h["result"] = "push"; stats.record("Blackjack", "push", 0, wager=w)
            else:
                h["result"] = "loss"; net -= w; stats.record("Blackjack", "loss", -w, wager=w)
        st["phase"] = "done"
        render()
        msg.config(text="Dealer has Blackjack." + (" Your hand pushes." if net == 0 else ""),
                   fg=PUSH if net == 0 else LOSE)
        ace.react("push" if net == 0 else "loss", amt=abs(net), game="Blackjack")
        sfx.play("card" if net == 0 else "lose")
        refresh()

    def settle_all():
        dv = hand_value(st["dealer"])
        net = 0
        parts = []
        multi = len(st["hands"]) > 1
        for i, h in enumerate(st["hands"]):
            pv, w = hand_value(h["cards"]), h["bet"]
            tag = f"H{i + 1}" if multi else "You"
            if not multi and len(h["cards"]) == 2 and pv == 21:      # untouched natural (bot mode)
                bonus = int(w * 1.5)
                bank.add(w + bonus); h["result"] = "bj"; net += bonus
                stats.record("Blackjack", "win", bonus, wager=w); parts.append(f"{tag} BLACKJACK +${bonus}")
                continue
            if pv > 21:
                h["result"] = "bust"; net -= w
                stats.record("Blackjack", "loss", -w, wager=w); parts.append(f"{tag} bust −${w}")
            elif dv > 21 or pv > dv:
                bank.add(w * 2); h["result"] = "win"; net += w
                stats.record("Blackjack", "win", w, wager=w); parts.append(f"{tag} win +${w}")
            elif pv < dv:
                h["result"] = "loss"; net -= w
                stats.record("Blackjack", "loss", -w, wager=w); parts.append(f"{tag} lose −${w}")
            else:
                bank.add(w); h["result"] = "push"
                stats.record("Blackjack", "push", 0, wager=w); parts.append(f"{tag} push")
        st["phase"] = "done"
        render()
        dtxt = "busts" if dv > 21 else str(dv)
        if multi:
            sign = "+" if net > 0 else ""
            summary = f"Dealer {dtxt}.   " + "  ·  ".join(parts) + f"    →   net {sign}${net}"
        else:
            r, w = st["hands"][0]["result"], st["hands"][0]["bet"]
            summary = {"win": f"You win ${w}!  (dealer {dtxt})",
                       "bj": f"BLACKJACK!  +${net} (3:2)!",
                       "loss": f"Dealer wins ({dtxt}). You lose ${w}.",
                       "bust": f"Bust! You lose ${w}.",
                       "push": "Push — your bet is returned."}[r]
        col = WIN if net > 0 else (LOSE if net < 0 else PUSH)
        msg.config(text=summary, fg=col)
        ace.react("win" if net > 0 else "loss" if net < 0 else "push", amt=abs(net), game="Blackjack")
        sfx.play("win" if net > 0 else "lose" if net < 0 else "card")
        if net > 0:
            fx.celebrate(win, net, big=net >= st["bet"] * 2)
        refresh()

    def deal():
        if st["phase"] not in ("bet", "done") or bank.balance < st["bet"]:
            return
        coach_lbl.config(text="")
        w = st["bet"]
        bank.add(-w)
        st["deck"] = cards.new_deck(); random.shuffle(st["deck"])
        first = [st["deck"].pop(), st["deck"].pop()]
        st["dealer"] = [st["deck"].pop(), st["deck"].pop()]
        st["hands"] = [{"cards": first, "bet": w, "done": False, "result": None, "ace": False}]
        st["active"] = 0
        names = random.sample(profile.bot_names(), st["num_bots"])  # seat the computer players
        st["bots"] = [{"name": nm, "cards": [st["deck"].pop(), st["deck"].pop()],
                       "bet": random.choice([10, 15, 20, 25]), "result": None} for nm in names]
        st["reveal"] = False; st["phase"] = "player"
        render(); sfx.play("card")
        pb, db = is_blackjack(first), is_blackjack(st["dealer"])
        if st["num_bots"] == 0:
            if pb or db:
                st["reveal"] = True
                if pb and db:
                    bank.add(w); st["hands"][0]["result"] = "push"
                    msg.config(text="Both have Blackjack — PUSH.", fg=PUSH)
                    ace.react("push", game="Blackjack"); stats.record("Blackjack", "push", 0, wager=w)
                elif pb:
                    bonus = int(w * 1.5); bank.add(w + bonus); st["hands"][0]["result"] = "bj"
                    msg.config(text=f"BLACKJACK! You win ${bonus} (3:2)!", fg=WIN)
                    ace.react("blackjack", amt=bonus, game="Blackjack")
                    sfx.play("jackpot"); stats.record("Blackjack", "win", bonus, wager=w)
                    fx.celebrate(win, bonus, big=True)
                else:
                    st["hands"][0]["result"] = "loss"
                    msg.config(text="Dealer has Blackjack — you lose.", fg=LOSE)
                    ace.react("loss", game="Blackjack"); sfx.play("lose")
                    stats.record("Blackjack", "loss", -w, wager=w)
                st["phase"] = "done"; render(); refresh(); return
            prompt_active(); refresh()
            return
        # --- computer-players mode: dealer peeks for Blackjack ---
        if db:
            st["reveal"] = True
            settle_dealer_bj()
            return
        if pb:                                            # your natural auto-stands; play it out
            st["hands"][0]["done"] = True
            advance()
            return
        prompt_active(); refresh()

    def hit():
        h = active_hand()
        if st["phase"] != "player" or h is None or h["done"] or h["ace"]:
            return
        h["cards"].append(st["deck"].pop()); sfx.play("card")
        if hand_value(h["cards"]) >= 21:            # 21 or a bust ends this hand
            h["done"] = True
            render(); advance()
        else:
            render(); refresh()

    def stand():
        h = active_hand()
        if st["phase"] != "player" or h is None or h["done"]:
            return
        h["done"] = True
        advance()

    def double():
        h = active_hand()
        if not can_double(h):
            return
        bank.add(-h["bet"]); h["bet"] *= 2
        h["cards"].append(st["deck"].pop()); sfx.play("card")
        h["done"] = True
        render(); advance()

    def split():
        h = active_hand()
        if not can_split(h):
            return
        bank.add(-h["bet"])                          # stake the second hand
        c0, c1 = h["cards"]
        is_ace = card_value(c0[0]) == 11
        new_hand = {"cards": [c1, st["deck"].pop()], "bet": h["bet"], "done": False,
                    "result": None, "ace": is_ace}
        h["cards"] = [c0, st["deck"].pop()]
        h["ace"] = is_ace
        st["hands"].insert(st["active"] + 1, new_hand)
        sfx.play("card")
        if is_ace:                                   # split Aces get one card each, then stand
            h["done"] = True
            new_hand["done"] = True
            render(); advance()
        else:
            render(); prompt_active(); refresh()

    seats_row = tk.Frame(body, bg=FELT)
    seats_row.pack(pady=(4, 0))
    tk.Label(seats_row, text="Computer players:", font=("Segoe UI", 9), bg=FELT,
             fg=theme.MUTED).pack(side="left", padx=(0, 6))
    seat_btns = []

    def set_bots(n):
        if st["phase"] not in ("bet", "done"):
            return
        st["num_bots"] = n
        st["th"] = 400 if n == 0 else 470
        table.config(height=st["th"])
        for i, b in enumerate(seat_btns):
            on = i == n
            b.config(bg=GOLD if on else theme.NIGHT2, fg=theme.INK if on else GOLD)
        render()

    for n in range(4):
        b = tk.Button(seats_row, text=("Just me" if n == 0 else str(n)), font=("Segoe UI", 9, "bold"),
                      bg=(GOLD if n == 0 else theme.NIGHT2), fg=(theme.INK if n == 0 else GOLD),
                      activebackground="#232b4d", relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                      command=lambda n=n: set_bots(n))
        b.pack(side="left", padx=2)
        seat_btns.append(b)

    betrow = tk.Frame(body, bg=FELT)
    betrow.pack(pady=(10, 4))
    minus = tk.Button(betrow, text="–", font=("Segoe UI", 13, "bold"), width=3,
                      command=lambda: change_bet(-MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    minus.pack(side="left", padx=4)
    bet_lbl = tk.Label(betrow, text="", font=("Consolas", 14, "bold"), bg=FELT, fg="white", width=10)
    bet_lbl.pack(side="left", padx=4)
    plus = tk.Button(betrow, text="+", font=("Segoe UI", 13, "bold"), width=3,
                     command=lambda: change_bet(MIN_BET), bg=DARKFELT, fg="white", relief="flat")
    plus.pack(side="left", padx=4)

    actions = tk.Frame(body, bg=FELT)
    actions.pack(pady=12)

    def _abtn(text, cmd, col, bg=IVORY, fg="#0a3d29"):
        b = tk.Button(actions, text=text, font=("Segoe UI", 12, "bold"), command=cmd,
                      bg=bg, fg=fg, activebackground="#d7ead5", relief="flat", padx=8, pady=8, width=6)
        b.grid(row=0, column=col, padx=3)
        return b

    deal_btn = _abtn("DEAL", deal, 0)
    hit_btn = _abtn("HIT", hit, 1)
    stand_btn = _abtn("STAND", stand, 2)
    dbl_btn = _abtn("DOUBLE", double, 3, bg=GOLD)
    split_btn = _abtn("SPLIT", split, 4, bg=PUSH)

    # --- AI Strategy Coach: instant, provably-optimal basic-strategy advice ---
    coach_lbl = tk.Label(body, text="", font=("Segoe UI", 11, "bold"), bg=FELT, fg=GOLD,
                         wraplength=470, justify="center")
    coach_lbl.pack(pady=(4, 0))

    def show_advice():
        h = active_hand()
        if st["phase"] != "player" or h is None:
            coach_lbl.config(text="🧠  Deal a hand first — then I'll show the optimal play.")
            return
        cd = len(h["cards"]) == 2 and bank.balance >= h["bet"]
        move, reason = coach.blackjack_advice(h["cards"], st["dealer"][0][0], cd)
        extra = "   (a pair — Split is also an option)" if can_split(h) else ""
        coach_lbl.config(text=f"🧠  Coach says {move}   ·   {reason}{extra}")

    tk.Button(body, text="🧠  Best Move?", font=("Segoe UI", 10, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
              command=show_advice).pack(pady=(6, 2))

    def new_game():
        if st["phase"] == "player":                 # abandoning a live hand — refund the wager(s)
            for h in st["hands"]:
                bank.add(h["bet"])
        st["phase"] = "bet"
        st["hands"], st["dealer"], st["deck"], st["bots"] = [], [], [], []
        st["reveal"] = False
        st["active"] = 0
        coach_lbl.config(text="")
        render()
        msg.config(text="New hand — set players and your bet, then DEAL.", fg="white")
        refresh()

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(4, 16))
    tk.Button(bottom, text="🔄  New Game", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=new_game).pack(side="left", padx=6)
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "BLACKJACK", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)

    render()
    refresh()
    ace.react("greeting", game="Blackjack")
