"""Tests for the AI Strategy Coach — correctness of both engines + solver speed."""
import random
import time

import coach
from games import video_poker as vp

SUITS = coach._SUITS


def test_score_matches_game_evaluator():
    """coach._score must agree with the game's own evaluate() on every hand."""
    deck = [(r, s) for r in range(2, 15) for s in SUITS]
    rng = random.Random(42)
    for _ in range(3000):
        hand = rng.sample(deck, 5)
        got = coach._score(hand)
        _, want = vp.evaluate(hand)
        assert got == want, f"{hand}: coach={got} game={want}"
    print("  ✓ scorer matches the game evaluator on 3000 random hands")


def test_blackjack_known_plays():
    """A handful of textbook basic-strategy decisions (dealer stands on 17)."""
    def hand(*rs):
        return [(r, "s") for r in rs]

    cases = [
        # (player ranks, dealer up rank, can_double, expected move)
        ((10, 6), 10, True, "HIT"),      # hard 16 vs 10 -> hit
        ((10, 6), 5, True, "STAND"),     # hard 16 vs 5  -> stand
        ((5, 6), 5, True, "DOUBLE"),     # hard 11 vs 5  -> double
        ((5, 6), 5, False, "HIT"),       # 11, can't double -> hit
        ((14, 7), 9, True, "HIT"),       # soft 18 vs 9  -> hit
        ((14, 7), 3, True, "DOUBLE"),    # soft 18 vs 3  -> double
        ((14, 7), 8, True, "STAND"),     # soft 18 vs 8  -> stand
        ((10, 10), 6, True, "STAND"),    # hard 20 -> stand
        ((14, 6), 4, True, "DOUBLE"),    # soft 17 vs 4  -> double
    ]
    for ranks, up, dbl, expected in cases:
        move, _ = coach.blackjack_advice(hand(*ranks), up, dbl)
        assert move == expected, f"{ranks} vs {up} (dbl={dbl}): got {move}, want {expected}"
    print(f"  ✓ blackjack basic strategy: {len(cases)}/{len(cases)} known plays correct")


def test_video_poker_holds_the_pair():
    """Dealt a low pair + junk, the solver must hold the pair (a known EV play)."""
    hand = [(7, "s"), (7, "h"), (2, "d"), (5, "c"), (9, "s")]  # pair of 7s
    held, ev, reason = coach.video_poker_advice(hand)
    kept_ranks = sorted(hand[i][0] for i in held)
    assert kept_ranks == [7, 7], f"expected to hold the pair of 7s, held {kept_ranks}"
    print(f"  ✓ video poker holds the pair of 7s ({reason})")


def test_video_poker_keeps_made_flush():
    """A pat flush should be held in full (EV = the guaranteed 6x, can't beat it)."""
    hand = [(2, "s"), (5, "s"), (9, "s"), (11, "s"), (13, "s")]
    held, ev, _ = coach.video_poker_advice(hand)
    assert len(held) == 5 and ev >= 6.0, f"should keep the flush, held {len(held)} ev {ev}"
    print(f"  ✓ video poker keeps a made flush (ev {ev:.2f})")


def test_solver_speed_worst_case():
    """Worst case (nothing worth holding -> must weigh drawing 5) stays usable."""
    hand = [(2, "s"), (5, "h"), (8, "d"), (11, "c"), (13, "s")]  # no pair, no draw
    t0 = time.perf_counter()
    coach.video_poker_advice(hand)
    dt = time.perf_counter() - t0
    print(f"  ✓ solver worst-case time: {dt:.2f}s")
    assert dt < 8.0, f"solver too slow: {dt:.2f}s"


if __name__ == "__main__":
    print("AI Strategy Coach — tests")
    for fn in (test_score_matches_game_evaluator, test_blackjack_known_plays,
               test_video_poker_holds_the_pair, test_video_poker_keeps_made_flush,
               test_solver_speed_worst_case):
        fn()
    print("ALL PASS")
