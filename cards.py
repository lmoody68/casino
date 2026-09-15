"""Shared playing cards — a standard 52-card deck and a card-face renderer for tkinter.

draw_card() paints a proper-looking card on a Canvas: rank + suit in the corners and
a large suit in the middle (red for hearts/diamonds, black for spades/clubs), with a
rounded white edge. Face cards (J/Q/K) show a big letter; a face-down card shows a back.
No image files — everything is drawn, so it's dependency-free and legally clean.
"""
import random

SUITS = ["♠", "♥", "♦", "♣"]
RED_SUITS = {"♥", "♦"}
RANK_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}

CARD_BG = "#f7faf5"; CARD_EDGE = "#c9ccc0"
CARD_RED = "#c0392b"; CARD_BLACK = "#1a1a1a"
BACK = "#1e2647"; BACK_TRIM = "#f6d365"


def rank_label(r):
    return RANK_STR.get(r, str(r))


def new_deck():
    """A fresh, unshuffled 52-card deck of (rank, suit); rank 2-14 (14 = Ace)."""
    return [(r, s) for r in range(2, 15) for s in SUITS]


def _round_rect(cv, x, y, w, h, r, **kw):
    pts = [x + r, y, x + w - r, y, x + w, y, x + w, y + r,
           x + w, y + h - r, x + w, y + h, x + w - r, y + h,
           x + r, y + h, x, y + h, x, y + h - r, x, y + r, x, y]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_card(cv, x, y, w, h, rank=None, suit=None, face_up=True):
    """Draw one card with its top-left corner at (x, y)."""
    if not face_up:
        _round_rect(cv, x, y, w, h, 10, fill=BACK, outline=BACK_TRIM, width=2)
        cv.create_text(x + w / 2, y + h / 2, text="♦", font=("Segoe UI", int(h * 0.34), "bold"),
                       fill=BACK_TRIM)
        return

    _round_rect(cv, x, y, w, h, 10, fill=CARD_BG, outline=CARD_EDGE, width=2)
    color = CARD_RED if suit in RED_SUITS else CARD_BLACK
    rl = rank_label(rank)

    # corner indices (top-left and bottom-right)
    cv.create_text(x + w * 0.17, y + h * 0.16, text=rl, font=("Segoe UI", int(h * 0.15), "bold"), fill=color)
    cv.create_text(x + w * 0.17, y + h * 0.31, text=suit, font=("Segoe UI", int(h * 0.12)), fill=color)
    cv.create_text(x + w * 0.83, y + h * 0.84, text=rl, font=("Segoe UI", int(h * 0.15), "bold"), fill=color)
    cv.create_text(x + w * 0.83, y + h * 0.69, text=suit, font=("Segoe UI", int(h * 0.12)), fill=color)

    # center
    if rank in (11, 12, 13):                       # face cards: big letter + suit
        cv.create_text(x + w / 2, y + h * 0.42, text=rl, font=("Georgia", int(h * 0.30), "bold"), fill=color)
        cv.create_text(x + w / 2, y + h * 0.68, text=suit, font=("Segoe UI", int(h * 0.20)), fill=color)
    else:                                          # number cards + ace: big suit
        cv.create_text(x + w / 2, y + h / 2, text=suit, font=("Segoe UI", int(h * 0.42)), fill=color)
