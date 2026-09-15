"""Sound effects — short casino sounds generated in code (no audio files to ship).

Each effect is synthesized once into a small WAV (cached next to the app) and
played with ffplay, so effects mix over the background music instead of cutting
it off. Everything is guarded: if ffplay isn't present the game just runs silent.
Toggle with set_enabled(); on by default.
"""
import os
import math
import array
import wave
import random
import shutil
import subprocess

_DIR = os.path.join(os.path.dirname(__file__), "sfx_cache")
_RATE = 22050
_VOLUME = 55                                   # ffplay volume for effects (over music at 35)
_CREATE_NO_WINDOW = 0x08000000
_enabled = [True]

_FFPLAY = shutil.which("ffplay")
if not _FFPLAY:
    try:
        import audio
        _FFPLAY = audio.FFPLAY
    except Exception:
        _FFPLAY = None


def _env(i, n, attack=0.005, decay=4.0):
    t = i / _RATE
    a = min(1.0, t / attack)
    return a * math.exp(-decay * t)


def _tone(freq, dur, vol=0.3, decay=4.0, harmonics=(1.0, 0.25)):
    n = int(_RATE * dur)
    out = [0.0] * n
    for i in range(n):
        t = i / _RATE
        s = sum(h * math.sin(2 * math.pi * freq * k * t) for k, h in enumerate(harmonics, 1))
        out[i] = vol * _env(i, n, decay=decay) * s
    return out


def _noise(dur, vol=0.3, decay=18.0):
    n = int(_RATE * dur)
    return [vol * _env(i, n, attack=0.001, decay=decay) * (random.random() * 2 - 1) for i in range(n)]


def _seq(segments):
    """Concatenate (start_time, samples) segments into one buffer, mixing overlaps."""
    total = max(int(_RATE * s) + len(buf) for s, buf in segments)
    out = [0.0] * total
    for start, buf in segments:
        off = int(_RATE * start)
        for i, v in enumerate(buf):
            out[off + i] += v
    return out


def _save(name, buf):
    peak = max(1e-6, max(abs(x) for x in buf))
    norm = 0.9 / peak
    samples = array.array("h", (int(max(-1.0, min(1.0, x * norm)) * 32767) for x in buf))
    path = os.path.join(_DIR, name + ".wav")
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(samples.tobytes())
    return path


def _build():
    """Define every effect. C-major notes so wins sound pleasant."""
    C, E, G, C2, E2 = 523.25, 659.25, 783.99, 1046.5, 1318.5
    return {
        # rising three-note flourish
        "win": _seq([(0.0, _tone(C, 0.16)), (0.12, _tone(E, 0.16)), (0.24, _tone(G, 0.28))]),
        # bigger fanfare, up to the octave
        "bigwin": _seq([(0.0, _tone(C, 0.14)), (0.12, _tone(E, 0.14)),
                        (0.24, _tone(G, 0.14)), (0.36, _tone(C2, 0.42, vol=0.34))]),
        # full jackpot run, twice
        "jackpot": _seq([(0.0, _tone(C, 0.12)), (0.10, _tone(E, 0.12)), (0.20, _tone(G, 0.12)),
                         (0.30, _tone(C2, 0.12)), (0.40, _tone(E2, 0.12)), (0.50, _tone(C2, 0.14)),
                         (0.64, _tone(G, 0.12)), (0.74, _tone(C2, 0.44, vol=0.36))]),
        # low two-note "aww"
        "lose": _seq([(0.0, _tone(220.0, 0.18, decay=5.0)), (0.16, _tone(174.6, 0.34, decay=5.0))]),
        # short high click for placing a chip / bet
        "chip": _tone(1200.0, 0.05, vol=0.25, decay=30.0),
        # card flip — a soft noise snap
        "card": _noise(0.08, vol=0.35, decay=26.0),
        # dice — a couple of clacks
        "dice": _seq([(0.0, _noise(0.05, vol=0.4, decay=40.0)),
                      (0.09, _noise(0.05, vol=0.4, decay=40.0)),
                      (0.17, _noise(0.05, vol=0.35, decay=40.0))]),
    }


def _ensure():
    if not _FFPLAY:
        return False
    os.makedirs(_DIR, exist_ok=True)
    ok = True
    for name, buf in _build().items():
        path = os.path.join(_DIR, name + ".wav")
        if not os.path.exists(path):
            try:
                _save(name, buf)
            except Exception:
                ok = False
    return ok


_READY = _ensure()


def available():
    return bool(_FFPLAY) and _READY


def is_enabled():
    return _enabled[0] and available()


def set_enabled(value):
    _enabled[0] = bool(value)
    return _enabled[0]


def toggle():
    return set_enabled(not _enabled[0])


def play(name):
    """Play a named effect (fire-and-forget, non-blocking). Silent if unavailable."""
    if not is_enabled():
        return
    path = os.path.join(_DIR, name + ".wav")
    if not os.path.exists(path):
        return
    try:
        subprocess.Popen(
            [_FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(_VOLUME), path],
            creationflags=_CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
