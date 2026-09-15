"""Background music for the casino.

Primary: shuffle-plays the user's own music library through ``ffplay`` (ships with
ffmpeg — already on this machine, no install). Falls back to a short synthesized
loop played via Windows ``winsound`` if ffplay or a library isn't found. Everything
is wrapped so the casino runs silently rather than crashing if audio is unavailable.
"""
import array
import atexit
import glob
import math
import os
import random
import shutil
import subprocess
import threading
import wave

MUSIC_DIR = os.path.expanduser("~/Music")
VOLUME = 35                              # ffplay volume, 0-100 (background level)
_CREATE_NO_WINDOW = 0x08000000          # keep ffplay from flashing a console window

_state = {"mode": None, "running": False, "proc": None, "idx": 0, "now": "", "playlist": []}


# ----------------------------------------------------------------------------- ffplay (your library)
def _find_ffplay():
    p = shutil.which("ffplay")
    if p:
        return p
    hits = glob.glob(os.path.expanduser(
        "~/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffplay.exe"))
    return hits[0] if hits else None


FFPLAY = _find_ffplay()


def _scan_library():
    files = []
    if os.path.isdir(MUSIC_DIR):
        for ext in ("*.mp3", "*.m4a", "*.wav", "*.flac", "*.ogg"):
            files += glob.glob(os.path.join(MUSIC_DIR, "**", ext), recursive=True)
    return files


def now_playing():
    path = _state["now"]
    if not path:
        return ""
    stem = os.path.splitext(os.path.basename(path))[0]
    artist = os.path.basename(os.path.dirname(path))
    return f"{artist} — {stem}" if artist and artist.lower() != "music" else stem


def _play_file(path):
    return subprocess.Popen(
        [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(VOLUME), path],
        creationflags=_CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _library_worker():
    while _state["running"]:
        pl = _state["playlist"]
        if not pl:
            break
        if _state["idx"] >= len(pl):
            _state["idx"] = 0
            random.shuffle(pl)
        track = pl[_state["idx"]]
        _state["now"] = track
        try:
            proc = _play_file(track)
            _state["proc"] = proc
            proc.wait()               # blocks until the track ends OR we terminate it (Next/stop)
        except Exception:
            pass
        if _state["running"]:
            _state["idx"] += 1
    _state["now"] = ""


def _kill_proc():
    p = _state["proc"]
    if p and p.poll() is None:
        try:
            p.terminate()
        except Exception:
            pass


# ----------------------------------------------------------------------------- synth fallback
_SYNTH_PATH = os.path.join(os.path.dirname(__file__), "casino_music.wav")
try:
    import winsound
    _HAVE_WINSOUND = True
except Exception:
    _HAVE_WINSOUND = False


def _midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _note(freq, dur, vol=0.25):
    n = int(22050 * dur)
    out = [0.0] * n
    for i in range(n):
        t = i / 22050
        env = min(1.0, t / 0.008) * math.exp(-3.2 * t)
        out[i] = vol * env * (math.sin(2 * math.pi * freq * t) * 0.7
                              + math.sin(2 * math.pi * 2 * freq * t) * 0.15)
    return out


def _generate_synth(path=_SYNTH_PATH):
    if os.path.exists(path):
        return path
    buf = []
    for ch in ([57, 60, 64], [53, 57, 60], [60, 64, 67], [55, 59, 62]):
        bass = _note(_midi(ch[0] - 12), 2.0, vol=0.16)
        arp = []
        for m in (ch[0], ch[1], ch[2], ch[1]):
            arp += _note(_midi(m + 12), 0.5, vol=0.20)
        for i in range(len(arp)):
            buf.append(arp[i] + (bass[i] if i < len(bass) else 0.0))
    peak = max(1e-6, max(abs(x) for x in buf))
    samples = array.array("h", (int(max(-1.0, min(1.0, x * (0.9 / peak))) * 32767) for x in buf))
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(samples.tobytes())
    return path


# ----------------------------------------------------------------------------- public API
def available():
    return FFPLAY is not None or _HAVE_WINSOUND


def is_on():
    return _state["running"]


def source():
    """'library' (your music) or 'synth' (generated loop) or None."""
    return _state["mode"]


def start():
    if _state["running"]:
        return True
    # Prefer the user's own library via ffplay.
    if FFPLAY:
        pl = _scan_library()
        if pl:
            random.shuffle(pl)
            _state.update({"mode": "library", "playlist": pl, "idx": 0, "running": True})
            threading.Thread(target=_library_worker, daemon=True).start()
            return True
    # Fall back to the synthesized loop.
    if _HAVE_WINSOUND:
        try:
            _generate_synth()
            winsound.PlaySound(_SYNTH_PATH, winsound.SND_ASYNC | winsound.SND_LOOP)
            _state.update({"mode": "synth", "running": True})
            return True
        except Exception:
            pass
    return False


def stop():
    _state["running"] = False
    if _state["mode"] == "library":
        _kill_proc()
    elif _state["mode"] == "synth" and _HAVE_WINSOUND:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
    _state["now"] = ""
    _state["mode"] = None


def next_track():
    """Skip to the next song (library mode only)."""
    if _state["running"] and _state["mode"] == "library":
        _kill_proc()          # the worker advances when the process ends


def prev_track():
    """Go back to the previous song (library mode only)."""
    if _state["running"] and _state["mode"] == "library":
        pl = _state["playlist"]
        if pl:
            # the worker does idx += 1 after the track stops; step back two so the
            # NEXT track it plays is the previous one.
            _state["idx"] = (_state["idx"] - 2) % len(pl)
            _kill_proc()


def toggle():
    if _state["running"]:
        stop()
    else:
        start()
    return _state["running"]


# Safety net: if the app exits for ANY reason, make sure the ffplay child process
# is stopped too, so music never keeps playing after the casino closes.
atexit.register(stop)
