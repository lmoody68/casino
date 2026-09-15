"""Casino — a multi-game desktop casino (Craps, Roulette, Slots, Video Poker).

The lobby shows your shared chip balance and launches each game as its own window.
Every game reads and writes the same Bank, so your chips carry across games and
sessions. Background music plays from your own library. Run:  python main.py
"""
import importlib
import tkinter as tk
from tkinter import messagebox

from bank import Bank
import audio
import theme
import art
import voice
import stats
import profile

W, H = 560, 770

GAMES = [
    ("craps", "CRAPS"),
    ("roulette", "ROULETTE"),
    ("slots", "SLOTS"),
    ("video_poker", "VIDEO POKER"),
    ("blackjack", "BLACKJACK"),
    ("holdem", "TEXAS HOLD'EM"),
]

bank = Bank()
root = tk.Tk()
root.title("Mac Land Casino")
root.geometry(f"{W}x{H}")
root.resizable(True, True)
root.minsize(W, H)
root.configure(bg=theme.NIGHT)

# --- gradient backdrop; centered so a maximized window shows it on the dark ground ---
bg = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=theme.NIGHT)
bg.place(relx=0.5, rely=0.5, anchor="center")
theme.paint_gradient(bg, W, H, top="#2b1656", bottom="#070910", steps=90)

# crown + "MAC ◆ LAND CASINO" branding
art.crown(bg, W // 2, 30, 30)
cx = W // 2
TF = ("Georgia", 30, "bold")
bg.create_text(cx - 24 + 2, 74, text="MAC", font=TF, fill="#221a06", anchor="e")     # shadow
bg.create_text(cx + 24 + 2, 74, text="LAND", font=TF, fill="#221a06", anchor="w")
bg.create_text(cx - 24, 72, text="MAC", font=TF, fill=theme.GOLD, anchor="e")
bg.create_text(cx + 24, 72, text="LAND", font=TF, fill=theme.GOLD, anchor="w")
_g = 13                                                                               # light-blue diamond gem
bg.create_polygon(cx, 72 - _g, cx + _g * 0.85, 72, cx, 72 + _g, cx - _g * 0.85, 72,
                  fill="#37bff0", outline="#1a86c0", width=2)
bg.create_line(cx - _g * 0.85, 72, cx + _g * 0.85, 72, fill="#bff0ff", width=1)
bg.create_line(cx, 72 - _g, cx, 72 + _g, fill="#bff0ff", width=1)
bg.create_text(cx, 104, text="C A S I N O", font=("Georgia", 15, "bold"), fill=theme.GOLD)
bg.create_text(cx, 126, text="ONE BANKROLL   ·   EVERY GAME", font=("Consolas", 10, "bold"),
               fill=theme.MUTED)

# decorative chips in the top corners
art.chip(bg, 40, 40, 18, "#c0392b")
art.chip(bg, 58, 54, 18, "#1e6fd0")
art.chip(bg, W - 40, 40, 18, "#2e9e4f")
art.chip(bg, W - 58, 54, 18, "#c0392b")

# chip plaque (canvas text so it blends with the gradient)
bg.create_text(W // 2, 150, text="YOUR CHIPS", font=("Consolas", 10, "bold"), fill=theme.MUTED)
chip_id = bg.create_text(W // 2, 180, text="", font=("Consolas", 30, "bold"), fill="white")


def refresh():
    bg.itemconfig(chip_id, text=f"${bank.balance}")
    bg.itemconfigure(buyin_win, state="hidden" if bank.balance >= 5 else "normal")


def launch(name):
    try:
        module = importlib.import_module(f"games.{name}")
    except ModuleNotFoundError:
        messagebox.showinfo("Coming soon", f"{name.replace('_', ' ').title()} is coming soon!")
        return
    module.open_game(root, bank, refresh)


# --- game tiles (drawn on the canvas with colorful icons) ---
tile_pos = [(W // 2 - 118, 266), (W // 2 + 118, 266),
            (W // 2 - 118, 372), (W // 2 + 118, 372),
            (W // 2 - 118, 478), (W // 2 + 118, 478)]
TILE_W, TILE_H = 214, 100
tiles = []   # (name, x0, y0, x1, y1) for click hit-testing
for (name, disp), (x, y) in zip(GAMES, tile_pos):
    x0, y0, x1, y1 = x - TILE_W / 2, y - TILE_H / 2, x + TILE_W / 2, y + TILE_H / 2
    art.rr(bg, x0, y0, x1, y1, 14, fill=theme.PANEL, outline=theme.GOLD_DEEP, width=2)
    art.game_icon(bg, name, x, y - 16, 46)
    bg.create_text(x, y + 36, text=disp, font=("Georgia", 13, "bold"), fill=theme.GOLD)
    tiles.append((name, x0, y0, x1, y1))


def _lobby_click(e):
    for name, x0, y0, x1, y1 in tiles:
        if x0 <= e.x <= x1 and y0 <= e.y <= y1:
            launch(name)
            return


def _lobby_move(e):
    over = any(x0 <= e.x <= x1 and y0 <= e.y <= y1 for _, x0, y0, x1, y1 in tiles)
    bg.config(cursor="hand2" if over else "")


bg.bind("<Button-1>", _lobby_click)
bg.bind("<Motion>", _lobby_move)


# --- music controls ---
def toggle_music():
    on = audio.toggle()
    music_btn.config(text="🔊  Music" if on else "🔇  Muted")


def poll_now_playing():
    music_btn.config(text="🔊  Music" if audio.is_on() else "🔇  Muted")   # stay in sync with in-game mutes
    if audio.is_on() and audio.source() == "library":
        now = audio.now_playing()
        bg.itemconfig(now_id, text=f"♪  {now}" if now else "♪  loading…")
        next_btn.config(state="normal")
        prev_btn.config(state="normal")
    else:
        bg.itemconfig(now_id, text="")
        next_btn.config(state="disabled")
        prev_btn.config(state="disabled")
    root.after(1500, poll_now_playing)


music_btn = tk.Button(root, text="🔊  Music", font=("Segoe UI", 10, "bold"),
                      bg=theme.NIGHT2, fg=theme.GOLD, activebackground="#232b4d", relief="flat",
                      bd=0, padx=14, pady=6, cursor="hand2", command=toggle_music)
bg.create_window(W // 2 - 120, 592, window=music_btn)
prev_btn = tk.Button(root, text="⏮  Prev", font=("Segoe UI", 10, "bold"),
                     bg=theme.NIGHT2, fg=theme.GOLD, activebackground="#232b4d", relief="flat",
                     bd=0, padx=14, pady=6, cursor="hand2", command=audio.prev_track)
bg.create_window(W // 2 + 20, 592, window=prev_btn)
next_btn = tk.Button(root, text="⏭  Next", font=("Segoe UI", 10, "bold"),
                     bg=theme.NIGHT2, fg=theme.GOLD, activebackground="#232b4d", relief="flat",
                     bd=0, padx=14, pady=6, cursor="hand2", command=audio.next_track)
bg.create_window(W // 2 + 110, 592, window=next_btn)
now_id = bg.create_text(W // 2, 628, text="", font=("Segoe UI", 9, "italic"), fill=theme.GOLD, width=480)

# buy-in (hidden unless broke)
buyin_btn = tk.Button(root, text="Buy in — reset to $500", font=("Segoe UI", 11, "bold"),
                      bg=theme.GOLD, fg=theme.INK, activebackground=theme.GOLD_DEEP, relief="flat",
                      bd=0, padx=16, pady=7, cursor="hand2",
                      command=lambda: (bank.reset(), refresh()))
buyin_win = bg.create_window(W // 2, 668, window=buyin_btn, state="hidden")

def open_rename():
    dlg = tk.Toplevel(root)
    dlg.title("Table Names")
    dlg.configure(bg=theme.NIGHT)
    dlg.resizable(False, False)
    theme.header(dlg, "TABLE NAMES", w=420, h=60)

    def _entry(parent, value):
        e = tk.Entry(parent, font=("Segoe UI", 12, "bold"), justify="center", width=15,
                     bg=theme.NIGHT2, fg=theme.GOLD, insertbackground=theme.GOLD, relief="flat")
        e.insert(0, value)
        return e

    tk.Label(dlg, text="Your name", font=("Segoe UI", 10, "bold"), bg=theme.NIGHT,
             fg=theme.IVORY).pack(pady=(14, 2))
    you_ent = _entry(dlg, profile.name())
    you_ent.pack(pady=(0, 10), ipady=4)
    you_ent.focus_set()
    you_ent.select_range(0, "end")

    tk.Label(dlg, text="Opponents (computer players)", font=("Segoe UI", 10, "bold"),
             bg=theme.NIGHT, fg=theme.IVORY).pack(pady=(4, 4))
    grid = tk.Frame(dlg, bg=theme.NIGHT)
    grid.pack(padx=24)
    bots = profile.bot_names()
    bot_ents = []
    for i in range(6):                                  # up to 6 opponents to choose from
        e = _entry(grid, bots[i] if i < len(bots) else "")
        e.grid(row=i // 2, column=i % 2, padx=5, pady=4, ipady=3)
        bot_ents.append(e)
    tk.Label(dlg, text="(at least 3 are kept; blank slots are ignored)", font=("Segoe UI", 8),
             bg=theme.NIGHT, fg=theme.MUTED).pack(pady=(4, 0))

    def save(_=None):
        nm = profile.set_name(you_ent.get())
        profile.set_bot_names([e.get() for e in bot_ents])
        name_btn.config(text=f"👤  {nm}")
        dlg.destroy()

    you_ent.bind("<Return>", save)
    tk.Button(dlg, text="Save", font=("Segoe UI", 11, "bold"), bg=theme.GOLD, fg=theme.INK,
              relief="flat", bd=0, padx=24, pady=6, cursor="hand2", command=save).pack(pady=(12, 18))
    dlg.transient(root)


name_btn = tk.Button(root, text=f"👤  {profile.name()}", font=("Segoe UI", 10, "bold"),
                     bg=theme.NIGHT2, fg=theme.GOLD, activebackground="#232b4d", relief="flat",
                     bd=0, padx=12, pady=6, cursor="hand2", command=open_rename)
bg.create_window(W // 2 - 78, 704, window=name_btn)
stats_btn = tk.Button(root, text="📊  Stats", font=("Segoe UI", 10, "bold"),
                      bg=theme.NIGHT2, fg=theme.GOLD, activebackground="#232b4d", relief="flat",
                      bd=0, padx=12, pady=6, cursor="hand2", command=lambda: stats.show_panel(root))
bg.create_window(W // 2 + 66, 704, window=stats_btn)

bg.create_text(W // 2, H - 26, text="Your chips save automatically · music from your own library",
               font=("Segoe UI", 9), fill=theme.MUTED)

refresh()
if audio.available():
    audio.start()
else:
    music_btn.config(text="🔇  n/a", state="disabled")
poll_now_playing()

# stop the music the moment the lobby is closed (belt-and-suspenders with audio's atexit hook)
root.protocol("WM_DELETE_WINDOW", lambda: (audio.stop(), voice.stop(), root.destroy()))
root.mainloop()
