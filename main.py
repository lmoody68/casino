"""Casino — a multi-game desktop casino (Craps, Roulette, Slots, Video Poker).

The lobby shows your shared chip balance and launches each game as its own
window. Every game reads and writes the same Bank, so your chips carry across
games and sessions. Run:  python main.py
"""
import importlib
import tkinter as tk
from tkinter import messagebox

from bank import Bank

FELT = "#0b3d2b"; PANEL = "#0e5a3c"; IVORY = "#f7faf5"; GOLD = "#f4d35e"; INK = "#0a3d29"

# (module name in games/, button label, emoji)
GAMES = [
    ("craps", "CRAPS", "🎲"),
    ("roulette", "ROULETTE", "🔴"),
    ("slots", "SLOTS", "🍒"),
    ("video_poker", "VIDEO POKER", "🃏"),
]

bank = Bank()
root = tk.Tk()
root.title("Casino")
root.configure(bg=FELT)
root.geometry("520x560")
root.resizable(False, False)

tk.Label(root, text="🎰  CASINO  🎰", font=("Segoe UI", 26, "bold"), bg=FELT, fg=GOLD).pack(pady=(28, 4))
tk.Label(root, text="one bankroll · every game", font=("Segoe UI", 11), bg=FELT, fg="#b9d6c7").pack()

chips_lbl = tk.Label(root, text="", font=("Consolas", 22, "bold"), bg=FELT, fg="white")
chips_lbl.pack(pady=(16, 4))


def refresh_chips():
    chips_lbl.config(text=f"CHIPS:  ${bank.balance}")
    buyin_btn.pack(pady=(0, 6)) if bank.balance < 5 else buyin_btn.pack_forget()


def launch(name):
    try:
        module = importlib.import_module(f"games.{name}")
    except ModuleNotFoundError:
        messagebox.showinfo("Coming soon", f"{name.replace('_', ' ').title()} is coming soon!")
        return
    module.open_game(root, bank, refresh_chips)


grid = tk.Frame(root, bg=FELT)
grid.pack(pady=14)
for i, (name, label, emoji) in enumerate(GAMES):
    b = tk.Button(grid, text=f"{emoji}\n{label}", font=("Segoe UI", 14, "bold"),
                  width=11, height=3, bg=PANEL, fg=IVORY, activebackground="#12704c",
                  relief="flat", command=lambda n=name: launch(n))
    b.grid(row=i // 2, column=i % 2, padx=10, pady=10)

buyin_btn = tk.Button(root, text="Buy in — reset to $500", font=("Segoe UI", 12, "bold"),
                      bg=GOLD, fg=INK, relief="flat", padx=16, pady=6,
                      command=lambda: (bank.reset(), refresh_chips()))

tk.Label(root, text="Tip: your chips save automatically between sessions.",
         font=("Segoe UI", 9), bg=FELT, fg="#7fae97").pack(side="bottom", pady=10)

refresh_chips()
root.mainloop()
