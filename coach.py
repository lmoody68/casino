"""AI Strategy Coach — tells you the mathematically best move.

Two techniques, each chosen because it fits its game:

* **Blackjack** uses *basic strategy* — the proven-optimal hit/stand/double
  decision for every (player hand, dealer up-card). It's a lookup, so it's
  instant and provably correct. (Rules here: dealer stands on 17, double on any
  two cards, no splitting/surrender — the tables below match those rules.)

* **Video Poker** uses an *exact expected-value (EV) solver*. For each of the 32
  ways to hold/discard your five cards, it enumerates every possible draw from
  the 47 unseen cards and averages the payout. The hold with the highest average
  payout is the optimal play. This is real decision theory, not a guess — and it
  needs no model or GPU.

Deliberately NOT an LLM: correctness matters and the state space is tiny, so an
exact solver beats a chatbot on every axis (right, instant, offline).
"""
from itertools import combinations
from functools import lru_cache

# Video-poker deck definition (mirrors games/video_poker.py so the solver is self-contained)
_SUITS = ("s", "h", "d", "c")
_RANK_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}


def _rank_label(r):
    return _RANK_STR.get(r, str(r))


# --------------------------------------------------------------------------- #
#  BLACKJACK — basic strategy (dealer stands on 17, double any two, no split)  #
# --------------------------------------------------------------------------- #
def _card_value(r):
    if r == 14:
        return 11
    if r >= 11:
        return 10
    return r


def _hand_shape(hand):
    """Return (total, is_soft): best total <=21 if possible, and whether an ace
    is still counted as 11 (a 'soft' hand that can't bust on the next card)."""
    total = sum(_card_value(r) for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == 14)
    reductions = 0
    while total > 21 and reductions < aces:
        total -= 10
        reductions += 1
    is_soft = (aces - reductions) > 0 and total <= 21
    return total, is_soft


def _dbl(can_double, otherwise):
    """DOUBLE if allowed, else fall back to the correct non-double play."""
    return "DOUBLE" if can_double else otherwise


def blackjack_advice(player_hand, dealer_up_rank, can_double=True):
    """Return (move, reason). move is 'HIT' | 'STAND' | 'DOUBLE'."""
    total, soft = _hand_shape(player_hand)
    up = _card_value(dealer_up_rank)          # dealer up-card value, ace = 11
    up_txt = "A" if up == 11 else str(up)

    if total >= 21:
        return "STAND", "You're at 21 — stand."

    if soft:
        move = _soft_advice(total, up, can_double)
    else:
        move = _hard_advice(total, up, can_double)

    kind = "soft" if soft else "hard"
    reason = f"{kind} {total} vs dealer {up_txt} → basic strategy says {move}."
    return move, reason


def _hard_advice(t, up, can_double):
    if t >= 17:
        return "STAND"
    if t <= 8:
        return "HIT"
    if t == 9:
        return _dbl(can_double, "HIT") if 3 <= up <= 6 else "HIT"
    if t == 10:
        return _dbl(can_double, "HIT") if 2 <= up <= 9 else "HIT"
    if t == 11:
        return _dbl(can_double, "HIT") if up <= 10 else "HIT"        # double vs 2-10, hit vs A
    if t == 12:
        return "STAND" if 4 <= up <= 6 else "HIT"
    if 13 <= t <= 16:
        return "STAND" if 2 <= up <= 6 else "HIT"
    return "HIT"


def _soft_advice(t, up, can_double):
    if t >= 19:
        return "STAND"                                               # A8, A9, A10
    if t == 18:                                                      # A7
        if 3 <= up <= 6:
            return _dbl(can_double, "STAND")
        if up in (2, 7, 8):
            return "STAND"
        return "HIT"                                                 # vs 9, 10, A
    if t == 17:                                                      # A6
        return _dbl(can_double, "HIT") if 3 <= up <= 6 else "HIT"
    if t in (15, 16):                                                # A4, A5
        return _dbl(can_double, "HIT") if 4 <= up <= 6 else "HIT"
    if t in (13, 14):                                                # A2, A3
        return _dbl(can_double, "HIT") if 5 <= up <= 6 else "HIT"
    return "HIT"


# --------------------------------------------------------------------------- #
#  VIDEO POKER — exact expected-value solver                                   #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def _payout(ranks, flush):
    """Payout multiple for a hand described by its sorted rank tuple + flush flag.
    Cached: the solver evaluates millions of draws but only a few thousand distinct
    (ranks, flush) patterns exist, so each is computed once and reused."""
    counts = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    shape = sorted(counts.values(), reverse=True)
    rset = set(ranks)
    straight = (len(rset) == 5 and ranks[-1] - ranks[0] == 4) or rset == {14, 2, 3, 4, 5}
    royal = rset == {10, 11, 12, 13, 14}

    if straight and flush and royal:
        return 250
    if straight and flush:
        return 50
    if shape[0] == 4:
        return 25
    if shape == [3, 2]:
        return 9
    if flush:
        return 6
    if straight:
        return 4
    if shape[0] == 3:
        return 3
    if shape == [2, 2, 1]:
        return 2
    if shape[0] == 2:
        if max(r for r, c in counts.items() if c == 2) >= 11:
            return 1
    return 0


def _score(hand):
    """Jacks-or-Better payout multiple for a 5-card hand (mirrors the game)."""
    s0 = hand[0][1]
    flush = all(c[1] == s0 for c in hand)
    return _payout(tuple(sorted(c[0] for c in hand)), flush)


def video_poker_advice(hand):
    """Return (held_indices, ev, reason). Enumerates all 32 holds; for each,
    averages the payout over every possible draw from the 47 unseen cards, and
    returns the hold with the highest expected value."""
    unseen = [(r, s) for r in range(2, 15) for s in _SUITS if (r, s) not in hand]
    best_ev, best_mask = -1.0, 0

    for mask in range(32):
        held = [hand[i] for i in range(5) if mask & (1 << i)]
        draw_n = 5 - len(held)
        if draw_n == 0:
            ev = float(_score(held))
        else:
            total, n = 0, 0
            for combo in combinations(unseen, draw_n):
                total += _score(held + list(combo))
                n += 1
            ev = total / n
        if ev > best_ev:
            best_ev, best_mask = ev, mask

    held_idx = [i for i in range(5) if best_mask & (1 << i)]
    if held_idx:
        labels = ", ".join(f"{_rank_label(hand[i][0])}{hand[i][1]}" for i in held_idx)
        reason = f"Hold {labels}  (avg return {best_ev:.2f}× per bet)."
    else:
        reason = f"Hold nothing — draw five fresh (avg return {best_ev:.2f}×)."
    return held_idx, best_ev, reason


# --------------------------------------------------------------------------- #
#  ROULETTE / CRAPS — fixed odds facts (no decision to optimize each round)    #
# --------------------------------------------------------------------------- #
ROULETTE_TIP = ("Every bet on a single-zero wheel has the same 2.7% house edge, "
                "so bet for fun. Even-money bets (Red/Black, Even/Odd, 1-18/19-36) "
                "give the steadiest ride; a single number pays 35:1 but hits only 1 in 37.")

CRAPS_TIP = ("The Pass Line is one of the best bets in the casino (~1.4% edge). "
             "Once a point is set, back it with the ODDS bet — odds are paid at "
             "TRUE odds with ZERO house edge, so max your odds to lower your overall edge.")
