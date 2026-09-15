"""Shared multi-player roster for the table games (Roulette, Craps).

A roster is a list of seats. Seat 0 is always YOU and your chips are the shared
casino bank. Other seats are either 'human' (pass-and-play — a real person taking
their turn on the same screen) or 'bot' (plays automatically). Non-you seats keep
their own session chip stack (not persisted) so everyone has their own money.
"""
import profile

START_STACK = 500          # session chips for every added player


def build(total, mode):
    """total: 1..4 seats. mode: 'bots' | 'humans' | 'mix' (alternate human/bot)."""
    roster = [{"name": profile.name(), "kind": "you", "stack": 0}]
    names = profile.bot_names()
    for i in range(1, total):
        if mode == "bots":
            kind = "bot"
        elif mode == "humans":
            kind = "human"
        else:                                  # mix: alternate, first extra seat human
            kind = "human" if i % 2 == 1 else "bot"
        nm = names[i - 1] if i - 1 < len(names) else f"Player {i + 1}"
        roster.append({"name": nm, "kind": kind, "stack": START_STACK})
    return roster


def chips(p, bank):
    return bank.balance if p["kind"] == "you" else p["stack"]


def add(p, amount, bank):
    if p["kind"] == "you":
        bank.add(amount)
    else:
        p["stack"] = max(0, p["stack"] + amount)


def label(p):
    tag = "" if p["kind"] == "you" else ("  🤖" if p["kind"] == "bot" else "  🧑")
    return p["name"] + tag
