# 🎰 Casino — A Multi-Game Desktop Casino in Python

Four playable casino games — **Craps, Roulette, Slots, and Video Poker** — sharing one **persistent chip bankroll**, all launched from a single lobby. Built in **pure Python** (tkinter, standard library only — no dependencies to install).

> _Add screenshots here — snap the lobby and a couple of games, save them in a `screenshots/` folder._
> `![Casino lobby](screenshots/lobby.png)`

---

## The games

| Game | How it plays |
|------|--------------|
| 🎲 **Craps** | Full Pass Line game — come-out roll, points, seven-out, plus **true-odds** betting (2:1 / 3:2 / 6:5, the zero-house-edge bet) |
| 🔴 **Roulette** | European single-zero wheel — bet red/black, even/odd, high/low (1:1) or a single number (35:1) |
| 🎰 **Slots** | Three weighted reels — match three for a payout, chase the **7️⃣7️⃣7️⃣ 100× jackpot** |
| 🃏 **Video Poker** | Jacks-or-Better — deal, **hold** the cards you want, draw, and get paid by hand rank |

## Features

- 🏦 **Shared, persistent bankroll** — win chips in one game, spend them in another; the balance **saves to disk** between sessions
- 🎞️ **Animated** dice, spinning wheel, and reels
- ✅ **Correct casino math** in every game — real payouts and odds, not approximations
- 🔒 **Input validation** — you can never bet more chips than you have, and each game enforces its own rules
- 🧩 **Modular design** — a shared bank, a `games/` package, and a lobby that loads each game dynamically

## Run it

**Requirements:** Python 3.8+ (tkinter ships with standard Python on Windows and macOS).

```bash
python main.py
```

No `pip install`, no setup.

## Project structure

```
casino/
├── main.py            # the lobby: shows chips, launches games
├── bank.py            # the shared, persistent chip bankroll (single source of truth)
└── games/
    ├── craps.py       # each game exposes open_game(parent, bank, on_change)
    ├── roulette.py
    ├── slots.py
    └── video_poker.py
```

The key design idea: **the money lives in one place** (`bank.py`), and every game reads and writes through it. Games know nothing about each other — the lobby wires them together. Adding a fifth game is just a new file in `games/`.

## What this project demonstrates

- **Application architecture** — separating shared state (the bank) from independent feature modules (the games), with a lobby that discovers and loads them
- **Event-driven GUI programming** with tkinter — canvas drawing, animation via scheduled callbacks, dynamic button/label state
- **Correct implementation of real-world rules and probability** across four different games
- **Data persistence** — the bankroll survives between runs
- **Testing** — the Video Poker hand evaluator is verified against every hand rank, including edge cases like the A-2-3-4-5 "wheel" straight

## Possible next steps

- More bets (Craps Field/Come, additional slot lines)
- Sound effects and a polished theme
- **Online / multiplayer version** — a web front end (React) with a server (FastAPI) that owns the RNG and chip balances, so players share a live table

## A note

This is a **play-money** project — virtual chips only, built to practice software design and demonstrate skills. It is not a gambling product.

## Author

**Les Moody** — built as a hands-on exercise in Python application architecture, GUI development, and game logic. Part of an ongoing software portfolio.
