"""Decorative drawn art for the casino lobby — a crown, casino chips, and colorful
game-tile icons. All drawn with canvas primitives (no image files)."""
import math

import cards

GOLD = "#f6d365"
GOLD_DEEP = "#c9a227"


def rr(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def crown(cv, cx, cy, s):
    """A gold crown with jewels, centered at (cx, cy)."""
    body = [cx - s * 0.5, cy + s * 0.2, cx - s * 0.5, cy - s * 0.28, cx - s * 0.26, cy - s * 0.02,
            cx, cy - s * 0.44, cx + s * 0.26, cy - s * 0.02, cx + s * 0.5, cy - s * 0.28,
            cx + s * 0.5, cy + s * 0.2]
    cv.create_polygon(body, fill=GOLD, outline=GOLD_DEEP, width=2)
    rr(cv, cx - s * 0.5, cy + s * 0.16, cx + s * 0.5, cy + s * 0.42, s * 0.08, fill=GOLD, outline=GOLD_DEEP, width=2)
    for jx, jy, col in ((cx - s * 0.5, cy - s * 0.28, "#e0424c"), (cx, cy - s * 0.44, "#37bff0"),
                        (cx + s * 0.5, cy - s * 0.28, "#e0424c")):
        cv.create_oval(jx - s * 0.08, jy - s * 0.08, jx + s * 0.08, jy + s * 0.08, fill=col, outline="white")
    cv.create_oval(cx - s * 0.09, cy + s * 0.2, cx + s * 0.09, cy + s * 0.38, fill="#37bff0", outline="white")


def chip(cv, cx, cy, r, color="#c0392b"):
    """A casino chip."""
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="white", width=2)
    for a in range(0, 360, 45):
        rad = math.radians(a)
        cv.create_line(cx + math.cos(rad) * r * 0.74, cy + math.sin(rad) * r * 0.74,
                       cx + math.cos(rad) * r, cy + math.sin(rad) * r, fill="white", width=3)
    cv.create_oval(cx - r * 0.58, cy - r * 0.58, cx + r * 0.58, cy + r * 0.58, outline="white", width=2)


def _die(cv, x, y, size, color, n):
    rr(cv, x, y, x + size, y + size, size * 0.16, fill=color, outline="#333", width=1)
    pips = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
            4: [(0, 0), (2, 0), (0, 2), (2, 2)], 5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
            6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]}
    step, r = size / 4, size * 0.085
    dot = "#222" if color == "#f7faf5" else "#f7faf5"
    for (c, rw) in pips[n]:
        cv.create_oval(x + step * (c + 1) - r, y + step * (rw + 1) - r,
                       x + step * (c + 1) + r, y + step * (rw + 1) + r, fill=dot, outline="")


def _wheel(cv, cx, cy, R):
    seg = 360 / 12
    for i in range(12):
        col = "#c0392b" if i % 2 else "#141414"
        cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=i * seg, extent=seg,
                      fill=col, outline=GOLD, width=1, style="pieslice")
    cv.create_oval(cx - R * 0.3, cy - R * 0.3, cx + R * 0.3, cy + R * 0.3, fill="#1e2647", outline=GOLD, width=2)


def _cherry(cv, cx, cy, s):
    r = s * 0.22
    for dx in (-s * 0.13, s * 0.15):
        cv.create_oval(cx + dx - r, cy - r, cx + dx + r, cy + r, fill="#d21f2b", outline="#8f1620")
    cv.create_line(cx - s * 0.13, cy - r, cx, cy - s * 0.3, fill="#2e7d32", width=2)
    cv.create_line(cx + s * 0.15, cy - r, cx, cy - s * 0.3, fill="#2e7d32", width=2)
    cv.create_oval(cx, cy - s * 0.38, cx + s * 0.2, cy - s * 0.26, fill="#43a047", outline="")


def game_icon(cv, game, cx, cy, s):
    """Draw a colorful icon for a game, centered at (cx, cy), roughly s tall."""
    if game == "craps":
        _die(cv, cx - s * 0.5, cy - s * 0.42, s * 0.5, "#f7faf5", 5)
        _die(cv, cx - s * 0.02, cy - s * 0.08, s * 0.5, "#d21f2b", 3)
    elif game == "roulette":
        _wheel(cv, cx, cy, s * 0.52)
    elif game == "slots":
        cv.create_text(cx - s * 0.24, cy, text="7", font=("Georgia", int(s * 0.62), "bold"), fill="#e11d2a")
        _cherry(cv, cx + s * 0.26, cy + s * 0.08, s * 0.52)
    elif game == "video_poker":
        cards.draw_card(cv, cx - s * 0.42, cy - s * 0.36, s * 0.5, s * 0.74, 14, "♠")
        cards.draw_card(cv, cx - s * 0.04, cy - s * 0.3, s * 0.5, s * 0.74, 13, "♥")
    elif game == "blackjack":
        cards.draw_card(cv, cx - s * 0.44, cy - s * 0.32, s * 0.5, s * 0.74, 14, "♠")
        cards.draw_card(cv, cx - s * 0.02, cy - s * 0.36, s * 0.5, s * 0.74, 11, "♦")
    elif game == "holdem":
        cards.draw_card(cv, cx - s * 0.5, cy - s * 0.42, s * 0.46, s * 0.68, 14, "♥")
        cards.draw_card(cv, cx - s * 0.16, cy - s * 0.46, s * 0.46, s * 0.68, 14, "♠")
        chip(cv, cx + s * 0.28, cy + s * 0.24, s * 0.24, "#2e9e4f")
        chip(cv, cx + s * 0.12, cy + s * 0.34, s * 0.24, "#c0392b")
