"""Win celebration — a burst of gold coins and a floating "+$amount" over a game.

Uses a borderless, click-through-ish overlay window with a transparent key color
(a Windows feature) so coins can rise over the felt without a visible box. It's
fully guarded: if transparency isn't supported the effect simply no-ops and the
game plays on. Call ``celebrate(win, amount, big=False)`` on a win.
"""
import random
import tkinter as tk

import theme

_KEY = "#ff00ee"        # a color unlikely to appear in the art; becomes transparent


def celebrate(win, amount, big=False):
    try:
        win.update_idletasks()
        x, y = win.winfo_rootx(), win.winfo_rooty()
        w, h = win.winfo_width(), win.winfo_height()
        if w < 50 or h < 50:
            return

        ov = tk.Toplevel(win)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        try:
            ov.attributes("-transparentcolor", _KEY)     # Windows: key color -> see-through
        except tk.TclError:
            ov.destroy()
            return
        ov.geometry(f"{w}x{h}+{x}+{y}")

        cv = tk.Canvas(ov, width=w, height=h, bg=_KEY, highlightthickness=0)
        cv.pack()

        # floating "+$amount"
        fs = 46 if big else 30
        txt_sh = cv.create_text(w // 2 + 2, h // 2 + 2, text=f"+${amount}",
                                font=("Georgia", fs, "bold"), fill="#3a2a06")
        txt = cv.create_text(w // 2, h // 2, text=f"+${amount}",
                             font=("Georgia", fs, "bold"), fill=theme.GOLD)

        coins = []
        for _ in range(22 if big else 12):
            cx = random.randint(30, max(31, w - 30))
            cy = h - random.randint(0, 120)
            r = random.randint(7, 15)
            vy = random.uniform(-11, -6) * (1.2 if big else 1.0)
            vx = random.uniform(-2.2, 2.2)
            oid = cv.create_oval(cx - r, cy - r, cx + r, cy + r,
                                 fill=theme.GOLD, outline=theme.GOLD_DEEP, width=2)
            inner = cv.create_text(cx, cy, text="$", font=("Georgia", max(7, r), "bold"),
                                   fill=theme.GOLD_DEEP)
            coins.append([oid, inner, vx, vy])

        frames = [0]
        TOTAL = 30

        def step():
            frames[0] += 1
            cv.move(txt, 0, -3)
            cv.move(txt_sh, 0, -3)
            for c in coins:
                oid, inner, vx, vy = c
                cv.move(oid, vx, vy)
                cv.move(inner, vx, vy)
                c[3] = vy + 0.6          # gravity
            if frames[0] < TOTAL and ov.winfo_exists():
                ov.after(28, step)
            elif ov.winfo_exists():
                ov.destroy()

        step()
    except Exception:
        try:
            ov.destroy()
        except Exception:
            pass
