"""Session stats — a running scoreboard of how the night is going.

In-memory for the current session (resets when you close the casino). Every game
calls ``record()`` on a resolved round; the lobby and games can open a styled
panel with ``show_panel()``. Also handy fuel for the dealer's commentary later.
"""
import tkinter as tk

import theme

_s = {
    "rounds": 0, "wins": 0, "losses": 0, "pushes": 0,
    "wagered": 0, "net": 0, "biggest_win": 0,
    "streak": 0, "best_win_streak": 0,
    "by_game": {},          # game -> {"rounds","wins","net"}
}


def record(game, result, delta, wager=0):
    """Record one resolved round.
    result: 'win' | 'loss' | 'push'.  delta: net chip change (payout minus stake).
    """
    _s["rounds"] += 1
    _s["wagered"] += max(0, wager)
    _s["net"] += delta

    g = _s["by_game"].setdefault(game, {"rounds": 0, "wins": 0, "net": 0})
    g["rounds"] += 1
    g["net"] += delta

    if result == "win":
        _s["wins"] += 1
        g["wins"] += 1
        _s["biggest_win"] = max(_s["biggest_win"], delta)
        _s["streak"] = _s["streak"] + 1 if _s["streak"] >= 0 else 1
        _s["best_win_streak"] = max(_s["best_win_streak"], _s["streak"])
    elif result == "loss":
        _s["losses"] += 1
        _s["streak"] = _s["streak"] - 1 if _s["streak"] <= 0 else -1
    else:
        _s["pushes"] += 1                      # a push doesn't change the streak


def summary():
    decided = _s["wins"] + _s["losses"]
    win_rate = (100 * _s["wins"] / decided) if decided else 0.0
    return {**_s, "win_rate": win_rate}


def reset():
    _s.update({"rounds": 0, "wins": 0, "losses": 0, "pushes": 0, "wagered": 0,
               "net": 0, "biggest_win": 0, "streak": 0, "best_win_streak": 0, "by_game": {}})


def show_panel(parent):
    """Open a styled Session Stats popup."""
    s = summary()
    win = tk.Toplevel(parent)
    win.title("Session Stats")
    win.configure(bg=theme.NIGHT)
    win.resizable(False, False)
    theme.header(win, "SESSION STATS", w=420, h=64)

    net = s["net"]
    net_col = theme.WINY if net > 0 else (theme.LOSEY if net < 0 else theme.IVORY)
    sign = "+" if net > 0 else ""
    tk.Label(win, text=f"{sign}${net}", font=("Consolas", 30, "bold"),
             bg=theme.NIGHT, fg=net_col).pack(pady=(14, 0))
    tk.Label(win, text="net this session", font=("Segoe UI", 9), bg=theme.NIGHT,
             fg=theme.MUTED).pack(pady=(0, 10))

    grid = tk.Frame(win, bg=theme.NIGHT)
    grid.pack(padx=24, pady=(0, 8))
    rows = [
        ("Rounds played", s["rounds"]),
        ("Wins / Losses / Pushes", f"{s['wins']} / {s['losses']} / {s['pushes']}"),
        ("Win rate", f"{s['win_rate']:.0f}%  (of decided rounds)"),
        ("Total wagered", f"${s['wagered']}"),
        ("Biggest single win", f"${s['biggest_win']}"),
        ("Best win streak", f"{s['best_win_streak']} in a row"),
    ]
    for i, (k, v) in enumerate(rows):
        tk.Label(grid, text=k, font=("Segoe UI", 11), bg=theme.NIGHT, fg=theme.MUTED,
                 anchor="w").grid(row=i, column=0, sticky="w", padx=(0, 18), pady=3)
        tk.Label(grid, text=str(v), font=("Consolas", 12, "bold"), bg=theme.NIGHT,
                 fg=theme.IVORY, anchor="e").grid(row=i, column=1, sticky="e", pady=3)

    if s["by_game"]:
        tk.Label(win, text="— by game —", font=("Segoe UI", 9, "bold"), bg=theme.NIGHT,
                 fg=theme.GOLD).pack(pady=(8, 2))
        gg = tk.Frame(win, bg=theme.NIGHT)
        gg.pack(padx=24)
        for i, (game, d) in enumerate(sorted(s["by_game"].items())):
            gn = d["net"]
            col = theme.WINY if gn > 0 else (theme.LOSEY if gn < 0 else theme.IVORY)
            tk.Label(gg, text=game, font=("Segoe UI", 10), bg=theme.NIGHT, fg=theme.MUTED,
                     anchor="w").grid(row=i, column=0, sticky="w", padx=(0, 18), pady=2)
            tk.Label(gg, text=f"{d['rounds']} rounds", font=("Consolas", 10), bg=theme.NIGHT,
                     fg=theme.MUTED).grid(row=i, column=1, padx=(0, 18))
            tk.Label(gg, text=f"{'+' if gn > 0 else ''}${gn}", font=("Consolas", 10, "bold"),
                     bg=theme.NIGHT, fg=col, anchor="e").grid(row=i, column=2, sticky="e", pady=2)

    tk.Button(win, text="Close", font=("Segoe UI", 11, "bold"), bg=theme.GOLD, fg=theme.INK,
              relief="flat", bd=0, padx=22, pady=6, cursor="hand2",
              command=win.destroy).pack(pady=(14, 18))
    win.transient(parent)
