"""Texas Hold'em — play a pot against computer opponents.

A 4-handed limit Hold'em cash game: you plus three bots. Standard flow — hole
cards, a betting round, the flop, turn, and river (each with betting), then a
showdown where the best five-card hand out of seven wins the pot. Your chips are
the shared casino bank; the bots keep their own stacks and rebuy if they bust.

Design notes:
* The hand evaluator scores the best 5 of 7 cards by trying all 21 combinations
  and returning a comparable (category, tiebreakers) tuple — simple and correct.
* Betting is LIMIT (fixed bet sizes, capped raises) which bounds the state machine
  and avoids no-limit side-pot complexity. All-ins are allowed but settled as a
  single pot (a deliberate simplification for a casual game).
* Bots decide from an estimated hand strength (hole-card score pre-flop, made-hand
  category post-flop) plus a little randomness and the occasional bluff.
"""
import tkinter as tk
import random
from itertools import combinations

import theme
import cards
import dealer
import sfx
import stats
import profile

FELT = "#0c1020"; FELT_GREEN = "#0a6b3f"; DARKFELT = "#1e2647"
IVORY = "#f7faf5"; GOLD = "#f6d365"; WIN = "#7fe0a8"; LOSE = "#e0616b"; MUTED = "#8fd0ab"

SB, BB = 5, 10
CAT_NAME = {8: "Straight Flush", 7: "Four of a Kind", 6: "Full House", 5: "Flush",
            4: "Straight", 3: "Three of a Kind", 2: "Two Pair", 1: "Pair", 0: "High Card"}

RULES = (
    "Texas Hold'em — you vs three computer players (limit betting).\n\n"
    "1.  Everyone gets 2 private 'hole' cards. Blinds are posted.\n"
    "2.  Four betting rounds: pre-flop, then the FLOP (3 shared cards),\n"
    "     the TURN (1 more), and the RIVER (1 more).\n"
    "3.  On your turn: FOLD, CHECK/CALL, or RAISE (fixed limit sizes).\n"
    "4.  At showdown the best five-card hand out of your 2 + 5 shared wins the pot.\n\n"
    "Hand ranking (high to low): Straight Flush · Four of a Kind · Full House ·\n"
    "Flush · Straight · Three of a Kind · Two Pair · Pair · High Card."
)


def rank5(five):
    """Score a 5-card hand as a comparable (category, tiebreakers) tuple."""
    ranks = sorted((c[0] for c in five), reverse=True)
    counts = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    # ranks ordered by (count desc, rank desc) — puts the quad/trip/pairs first
    ordered = [r for r, _ in sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)]
    shape = sorted(counts.values(), reverse=True)
    is_flush = len({c[1] for c in five}) == 1
    distinct = sorted(set(ranks))
    straight_hi = None
    if len(distinct) == 5:
        if distinct[-1] - distinct[0] == 4:
            straight_hi = distinct[-1]
        elif set(distinct) == {2, 3, 4, 5, 14}:      # wheel: A-2-3-4-5
            straight_hi = 5

    if is_flush and straight_hi:
        return (8, [straight_hi])
    if shape == [4, 1]:
        return (7, ordered)
    if shape == [3, 2]:
        return (6, ordered)
    if is_flush:
        return (5, ranks)
    if straight_hi:
        return (4, [straight_hi])
    if shape == [3, 1, 1]:
        return (3, ordered)
    if shape == [2, 2, 1]:
        return (2, ordered)
    if shape == [2, 1, 1, 1]:
        return (1, ordered)
    return (0, ranks)


def best_hand(seven):
    """Best (category, tiebreakers) over all 5-card subsets of up to 7 cards."""
    return max(rank5(list(c)) for c in combinations(seven, 5))


def hand_name(seven):
    return CAT_NAME[best_hand(seven)[0]]


def _hole_strength(hole):
    r0, r1 = sorted((hole[0][0], hole[1][0]), reverse=True)
    suited = hole[0][1] == hole[1][1]
    if r0 == r1:
        return min(1.0, 0.5 + (r0 / 14) * 0.5)          # any pair is strong
    s = (r0 + r1) / 28.0 * 0.55
    if suited:
        s += 0.10
    if r0 - r1 == 1:
        s += 0.05
    if r0 >= 13:
        s += 0.08
    return min(1.0, s)


def _made_strength(seven):
    base = {0: .15, 1: .42, 2: .60, 3: .75, 4: .85, 5: .90, 6: .95, 7: .99, 8: 1.0}
    return base[best_hand(seven)[0]]


def open_game(parent, bank, on_change):
    st = {"players": [], "community": [], "deck": [], "pot": 0, "button": 0,
          "current_bet": 0, "street": "idle", "raises": 0, "actor": 0, "in_hand": False}

    win = tk.Toplevel(parent)
    win.title("Texas Hold'em")
    win.configure(bg=FELT)
    win.geometry("600x820")
    win.resizable(True, True)
    win.minsize(480, 560)
    theme.header(win, "TEXAS HOLD'EM", w=600)
    theme.music_bar(win).place(relx=1.0, x=-8, y=8, anchor="ne")

    body = theme.scrollable(win, bg=FELT)

    chips = tk.Label(body, text="", font=("Consolas", 16, "bold"), bg=FELT, fg=GOLD)
    chips.pack(pady=(8, 2))

    ace = dealer.DealerBox(body, win, felt=FELT)
    ace.pack(fill="x", padx=18, pady=(0, 4))

    TW, TH = 560, 430
    table = tk.Canvas(body, width=TW, height=TH, bg=FELT, highlightthickness=0)
    table.pack(pady=(2, 2))

    msg = tk.Label(body, text="Press DEAL to start a hand.", font=("Segoe UI", 12, "bold"),
                   bg=FELT, fg="white", wraplength=560)
    msg.pack(pady=4)

    def _rrt(x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return table.create_polygon(pts, smooth=True, **kw)

    # seat anchor points (name/stack label center); cards drawn near them
    SEATS = [(TW // 2, TH - 96),          # 0 = you (bottom)
             (84, 156),                   # 1 = left
             (TW // 2, 74),               # 2 = top
             (TW - 84, 156)]              # 3 = right

    def draw_table():
        _rrt(16, 16, TW - 16, TH - 16, 150, fill=FELT_GREEN, outline=GOLD, width=4)
        _rrt(28, 28, TW - 28, TH - 28, 140, fill="", outline="#0a4d2c", width=2)

    def draw_community():
        cw, ch, off = 52, 74, 60
        n = 5
        total = (n - 1) * off
        x0 = TW / 2 - total / 2
        y = TH / 2 - ch / 2 - 6
        for i in range(5):
            if i < len(st["community"]):
                r, s = st["community"][i]
                cards.draw_card(table, x0 + i * off - cw / 2, y, cw, ch, r, s, face_up=True)
            else:
                table.create_rectangle(x0 + i * off - cw / 2, y, x0 + i * off - cw / 2 + cw, y + ch,
                                       outline="#0a4d2c", width=1, dash=(3, 3))
        table.create_text(TW / 2, y - 20, text=f"POT  ${st['pot']}", font=("Georgia", 15, "bold"),
                          fill=GOLD)

    def draw_seat(i):
        p = st["players"][i]
        sx, sy = SEATS[i]
        you = p["is_you"]
        cw, ch, off = (46, 66, 26) if you else (30, 44, 18)
        # lay the seat out so the name/stack/status never sit on top of the cards
        if you:                                        # you: cards up top, labels below the anchor
            card_cy = sy - ch - 18
            name_y, info_y, tag_y, show_y = sy, sy + 15, sy + 30, sy + 44
        else:                                          # others: name above the cards, labels below
            card_cy = sy - ch / 2 + 4
            name_y = card_cy - 13
            info_y = card_cy + ch + 10
            tag_y = card_cy + ch + 22
            show_y = card_cy + ch + 34
        if p["cards"]:
            faceup = you or st["street"] == "showdown"
            bx = sx - (cw + off) / 2
            for j, (r, s) in enumerate(p["cards"]):
                cards.draw_card(table, bx + j * off, card_cy, cw, ch, r, s, face_up=faceup)
        nm = profile.name() if you else p["name"]
        active = i == st["actor"] and st["in_hand"] and not p["folded"]
        col = GOLD if active else IVORY
        stack = bank.balance if you else p["stack"]
        table.create_text(sx, name_y, text=nm, font=("Georgia", 11, "bold"), fill=col)
        table.create_text(sx, info_y, text=f"${stack}", font=("Consolas", 10, "bold"), fill=MUTED)
        tags = []
        if p["folded"]:
            tags.append("FOLD")
        elif p["all_in"]:
            tags.append("ALL-IN")
        if i == st["button"]:
            tags.append("D")
        if p["committed"]:
            tags.append(f"bet ${p['committed']}")
        if tags:
            table.create_text(sx, tag_y, text="  ·  ".join(tags), font=("Consolas", 8, "bold"),
                              fill="#cfe8d8")
        if st["street"] == "showdown" and not p["folded"] and p["cards"]:
            table.create_text(sx, show_y, text=hand_name(p["cards"] + st["community"]),
                              font=("Consolas", 8, "bold"), fill=GOLD)

    def render():
        table.delete("all")
        draw_table()
        draw_community()
        for i in range(len(st["players"])):
            draw_seat(i)

    def street_bet():
        return BB if st["street"] in ("preflop", "flop") else 2 * BB

    def refresh():
        chips.config(text=f"YOUR CHIPS:  ${bank.balance}")
        you = st["players"][0] if st["players"] else None
        my_turn = st["in_hand"] and st["actor"] == 0 and you and not you["folded"] and not you["all_in"]
        to_call = (st["current_bet"] - you["committed"]) if you else 0
        fold_btn.config(state="normal" if my_turn else "disabled")
        if my_turn:
            call_btn.config(text=("CHECK" if to_call == 0 else f"CALL ${min(to_call, bank.balance)}"),
                            state="normal")
            can_raise = st["raises"] < 4 and bank.balance > to_call
            raise_btn.config(state="normal" if can_raise else "disabled",
                             text=f"RAISE ${street_bet()}")
        else:
            call_btn.config(state="disabled")
            raise_btn.config(state="disabled")
        deal_btn.config(state="normal" if not st["in_hand"] else "disabled")
        on_change()

    # ---- chip movement ----
    def commit(p, amount):
        amount = min(amount, (bank.balance if p["is_you"] else p["stack"]))
        if amount <= 0:
            return 0
        if p["is_you"]:
            bank.add(-amount)
            st["_my_in"] = st.get("_my_in", 0) + amount   # your contribution this hand (for stats)
        else:
            p["stack"] -= amount
        p["committed"] += amount
        st["pot"] += amount
        if (bank.balance if p["is_you"] else p["stack"]) == 0:
            p["all_in"] = True
        return amount

    # ---- hand lifecycle ----
    def start_hand():
        if st["in_hand"]:
            return
        st["_my_in"] = 0
        players = st["players"]
        if not players:
            players = [{"name": "You", "is_you": True, "stack": 0, "cards": [], "folded": False,
                        "all_in": False, "committed": 0}]
            for nm in profile.bot_names()[:3]:
                players.append({"name": nm, "is_you": False, "stack": 500, "cards": [], "folded": False,
                                "all_in": False, "committed": 0})
            st["players"] = players
            st["button"] = random.randrange(4)
        else:
            st["button"] = (st["button"] + 1) % 4
            for p in players:
                if not p["is_you"] and p["stack"] < BB:
                    p["stack"] = 500                  # bots rebuy so the game continues
        if bank.balance < BB:
            msg.config(text="You're out of chips — buy in from the lobby.", fg=LOSE)
            return
        for p in players:
            p.update(cards=[], folded=False, all_in=False, committed=0, acted=False, result=None)
        st.update(community=[], pot=0, current_bet=0, street="preflop", raises=1, in_hand=True)
        st["deck"] = cards.new_deck(); random.shuffle(st["deck"])
        for _ in range(2):
            for p in players:
                p["cards"].append(st["deck"].pop())
        sb = (st["button"] + 1) % 4
        bb = (st["button"] + 2) % 4
        commit(players[sb], SB)
        commit(players[bb], BB)
        st["current_bet"] = BB
        st["actor"] = (st["button"] + 3) % 4          # first to act pre-flop = left of big blind
        sfx.play("card")
        render()
        msg.config(text="Pre-flop — your move." if st["actor"] == 0 else "Pre-flop…", fg="white")
        proceed(fresh=True)

    def alive_players():
        return [p for p in st["players"] if not p["folded"]]

    def can_still_act():
        return [p for p in st["players"] if not p["folded"] and not p["all_in"]]

    def next_actor(from_idx):
        n = len(st["players"])
        for k in range(1, n + 1):
            i = (from_idx + k) % n
            p = st["players"][i]
            if p["folded"] or p["all_in"]:
                continue
            if not p["acted"] or p["committed"] != st["current_bet"]:
                return i
        return None

    def proceed(fresh=False):
        if len(alive_players()) == 1:
            award([alive_players()[0]]); return
        if len(can_still_act()) == 0:                 # everyone all-in/folded -> run it out
            end_street(); return
        nxt = next_actor(st["actor"] if not fresh else (st["actor"] - 1) % len(st["players"]))
        if nxt is None:
            end_street(); return
        st["actor"] = nxt
        render(); refresh()
        p = st["players"][nxt]
        if p["is_you"]:
            to_call = st["current_bet"] - p["committed"]
            msg.config(text=("Your move — check or bet." if to_call == 0
                             else f"Your move — call ${to_call}, raise, or fold."), fg="white")
        else:
            msg.config(text=f"{p['name']} is thinking…", fg=MUTED)
            win.after(750, lambda i=nxt: bot_act(i))

    def apply_action(i, action):
        """action: 'fold' | 'call' | 'raise'."""
        p = st["players"][i]
        p["acted"] = True
        if action == "fold":
            p["folded"] = True
            sfx.play("card")
        elif action == "call":
            need = st["current_bet"] - p["committed"]
            commit(p, need)
            sfx.play("chip")
        elif action == "raise":
            need = st["current_bet"] + street_bet() - p["committed"]
            commit(p, need)
            st["current_bet"] = p["committed"] if p["committed"] > st["current_bet"] else st["current_bet"] + street_bet()
            st["raises"] += 1
            for q in st["players"]:                   # a raise re-opens the action
                if not q["folded"] and not q["all_in"] and q is not p:
                    q["acted"] = False
            sfx.play("chip")

    def do_fold():
        if st["in_hand"] and st["actor"] == 0:
            apply_action(0, "fold"); proceed()

    def do_call():
        if st["in_hand"] and st["actor"] == 0:
            apply_action(0, "call"); proceed()

    def do_raise():
        if st["in_hand"] and st["actor"] == 0 and st["raises"] < 4:
            apply_action(0, "raise"); proceed()

    def bot_act(i):
        if not st["in_hand"] or st["actor"] != i:
            return
        p = st["players"][i]
        to_call = st["current_bet"] - p["committed"]
        if st["community"]:
            strength = _made_strength(p["cards"] + st["community"]) + random.uniform(-0.08, 0.08)
        else:
            strength = _hole_strength(p["cards"]) + random.uniform(-0.08, 0.08)
        can_raise = st["raises"] < 4 and p["stack"] > to_call
        if to_call == 0:
            if strength > 0.68 and can_raise and random.random() < 0.6:
                apply_action(i, "raise")
            else:
                apply_action(i, "call")               # a call of 0 == check
        else:
            if strength < 0.34:
                if can_raise and random.random() < 0.10:
                    apply_action(i, "raise")          # occasional bluff
                else:
                    apply_action(i, "fold")
            elif strength < 0.62:
                apply_action(i, "call")
            else:
                if can_raise and strength > 0.75 and random.random() < 0.5:
                    apply_action(i, "raise")
                else:
                    apply_action(i, "call")
        proceed()

    def end_street():
        for p in st["players"]:
            p["acted"] = False
            p["committed"] = 0
        st["current_bet"] = 0
        st["raises"] = 0
        order = ["preflop", "flop", "turn", "river", "showdown"]
        nxt = order[order.index(st["street"]) + 1]
        st["street"] = nxt
        if nxt == "flop":
            st["community"] += [st["deck"].pop() for _ in range(3)]
        elif nxt in ("turn", "river"):
            st["community"].append(st["deck"].pop())
        elif nxt == "showdown":
            showdown(); return
        sfx.play("card")
        render()
        # if nobody can act (all all-in), keep dealing
        if len(can_still_act()) <= 1 and len(alive_players()) > 1:
            win.after(700, end_street)
            return
        st["actor"] = st["button"]                    # first active after button acts first
        msg.config(text=f"{nxt.title()}.", fg="white")
        proceed(fresh=True)

    def award(winners, note=""):
        share = st["pot"] // len(winners)
        names = []
        you_won = 0
        for p in winners:
            if p["is_you"]:
                bank.add(share); you_won = share
            else:
                p["stack"] += share
            names.append("You" if p["is_you"] else p["name"])
        st["in_hand"] = False
        st["street"] = "showdown"
        render()
        who = " & ".join(names)
        tail = f"  with {note}" if note else ""
        verb = "win" if (len(winners) > 1 or who == "You") else "wins"
        msg.config(text=f"{who} {verb} ${share}{tail}.", fg=WIN if you_won else LOSE)
        if you_won:
            stats.record("Hold'em", "win", you_won - st["_my_in"], wager=st["_my_in"])
            ace.react("bigwin" if you_won >= 4 * BB else "win", amt=you_won, game="Hold'em")
            sfx.play("bigwin" if you_won >= 4 * BB else "win")
            import fx
            fx.celebrate(win, you_won, big=you_won >= 6 * BB)
        else:
            if st.get("_my_in"):
                stats.record("Hold'em", "loss", -st["_my_in"], wager=st["_my_in"])
            ace.react("loss", game="Hold'em")
            sfx.play("lose")
        refresh()

    def showdown():
        st["street"] = "showdown"
        contenders = [p for p in st["players"] if not p["folded"]]
        best = None
        for p in contenders:
            p["_score"] = best_hand(p["cards"] + st["community"])
            if best is None or p["_score"] > best:
                best = p["_score"]
        winners = [p for p in contenders if p["_score"] == best]
        award(winners, note=hand_name(winners[0]["cards"] + st["community"]))

    # ---- controls ----
    controls = tk.Frame(body, bg=FELT)
    controls.pack(pady=8)

    def _cbtn(text, cmd, col, bg=IVORY, fg="#0a3d29"):
        b = tk.Button(controls, text=text, font=("Segoe UI", 13, "bold"), command=cmd, bg=bg, fg=fg,
                      activebackground="#d7ead5", relief="flat", padx=14, pady=9, width=9)
        b.grid(row=0, column=col, padx=4)
        return b

    fold_btn = _cbtn("FOLD", do_fold, 0, bg=LOSE, fg="white")
    call_btn = _cbtn("CHECK", do_call, 1)
    raise_btn = _cbtn("RAISE", do_raise, 2, bg=GOLD)

    deal_btn = tk.Button(body, text="DEAL", font=("Segoe UI", 15, "bold"), command=lambda: start_hand(),
                         bg=IVORY, fg="#0a3d29", activebackground="#d7ead5", relief="flat",
                         padx=30, pady=10)
    deal_btn.pack(pady=8)

    bottom = tk.Frame(body, bg=FELT)
    bottom.pack(pady=(2, 16))
    tk.Button(bottom, text="❔  How to Play", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.show_rules(win, "TEXAS HOLD'EM", RULES)).pack(side="left", padx=6)
    tk.Button(bottom, text="📊  Stats", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: stats.show_panel(win)).pack(side="left", padx=6)
    tk.Button(bottom, text="👤  Names", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT2, fg=GOLD,
              activebackground="#232b4d", relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
              command=lambda: theme.names_dialog(win, on_saved=lambda nm: render())).pack(side="left", padx=6)

    render()
    refresh()
    ace.react("greeting", game="Hold'em")
