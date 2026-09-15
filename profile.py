"""Player profile — your display name, remembered between sessions.

Stored in a small settings.json next to the app (gitignored). Kept tiny and
guarded so a missing/broken file just falls back to a default name.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "settings.json")
_cache = {"name": None}
DEFAULT = "Player"
DEFAULT_BOTS = ["Duke", "Rosa", "Sal", "Mika", "Nina", "Gus"]


def _load():
    try:
        with open(_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def name():
    if _cache["name"] is None:
        _cache["name"] = (_load().get("name") or DEFAULT).strip() or DEFAULT
    return _cache["name"]


def set_name(new):
    new = (new or "").strip()[:14] or DEFAULT
    _cache["name"] = new
    _save("name", new)
    return new


def bot_names():
    """The opponent names, always at least 3 (padded with defaults if the user
    cleared some)."""
    lst = [str(x).strip()[:14] for x in (_load().get("bots") or []) if str(x).strip()]
    for d in DEFAULT_BOTS:
        if len(lst) >= 3:
            break
        if d not in lst:
            lst.append(d)
    return lst or DEFAULT_BOTS[:]


def set_bot_names(names):
    clean = [str(n).strip()[:14] for n in names if str(n).strip()]
    for d in DEFAULT_BOTS:                      # never fewer than 3 so both games have opponents
        if len(clean) >= 3:
            break
        if d not in clean:
            clean.append(d)
    _save("bots", clean)
    return clean


def _save(key, value):
    data = _load()
    data[key] = value
    try:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
