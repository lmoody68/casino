"""Shared chip bankroll for the whole casino.

Every game reads and writes the same balance through this one object, and it is
saved to ``chips.json`` so your chips survive between sessions — like a real
casino account. This is the single source of truth for the player's money.
"""
import json
import os

_FILE = os.path.join(os.path.dirname(__file__), "chips.json")
STARTING = 500


class Bank:
    def __init__(self):
        self.balance = STARTING
        self.load()

    def load(self):
        try:
            with open(_FILE, encoding="utf-8") as f:
                self.balance = int(json.load(f).get("chips", STARTING))
        except Exception:
            self.balance = STARTING

    def save(self):
        try:
            with open(_FILE, "w", encoding="utf-8") as f:
                json.dump({"chips": self.balance}, f)
        except Exception:
            pass

    def add(self, amount):
        """Apply a win (positive) or loss (negative) and persist immediately."""
        self.balance += amount
        self.save()

    def reset(self):
        self.balance = STARTING
        self.save()
