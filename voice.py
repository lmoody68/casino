"""Dealer voice — speaks Ace's lines out loud, preferring a human-sounding voice.

Tiered engine (graceful degradation, same idea as the dealer's LLM upgrade):

* **Neural (preferred):** Microsoft neural voices via the ``edge-tts`` package —
  genuinely human-sounding. It renders the line to an mp3 which we play with
  ffplay (already used for the casino music). Needs internet + the edge-tts
  package; if either is missing at runtime we fall back automatically.

* **SAPI (fallback):** Windows' built-in System.Speech engine via PowerShell.
  Robotic, but offline and dependency-free — so speech still works on any Windows
  box with no setup.

Off by default (a talking app should be opt-in). Everything runs in a subprocess
so the game never blocks, and starting a new line stops the previous one so
speech never overlaps. Set the neural voice with the CASINO_DEALER_VOICE env var
(e.g. en-US-JennyNeural); default is a warm host voice.
"""
import os
import sys
import atexit
import tempfile
import threading
import subprocess

_enabled = [False]
_proc = [None]                     # current playback/speech process (for interrupt)
_seq = [0]                         # bumps each speak() so stale neural renders are dropped
_lock = threading.Lock()

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
_VOICE = os.environ.get("CASINO_DEALER_VOICE", "en-US-ChristopherNeural").strip() or "en-US-ChristopherNeural"


def _have(cmd):
    from shutil import which
    return which(cmd) is not None


def _neural_available():
    try:
        import edge_tts            # noqa: F401
    except Exception:
        return False
    return _have("ffplay")         # we need ffplay to play the rendered mp3


# Decide the engine once. Neural if edge-tts + ffplay are present; else SAPI on Windows.
_NEURAL = _neural_available()
_SAPI = sys.platform == "win32"


def available():
    return _NEURAL or _SAPI


def engine_name():
    if _NEURAL:
        return f"neural ({_VOICE})"
    if _SAPI:
        return "Windows SAPI (robotic)"
    return "none"


def is_enabled():
    return _enabled[0] and available()


def set_enabled(value):
    _enabled[0] = bool(value) and available()
    if not _enabled[0]:
        stop()
    return _enabled[0]


def toggle():
    return set_enabled(not _enabled[0])


def speak(text):
    """Speak a line (non-blocking). Interrupts whatever was being said."""
    if not is_enabled() or not text:
        return
    stop()
    _seq[0] += 1
    seq = _seq[0]
    if _NEURAL:
        threading.Thread(target=_speak_neural, args=(str(text), seq), daemon=True).start()
    else:
        _speak_sapi(str(text))


def _speak_neural(text, seq):
    """Render the line with a neural voice and play it. Falls back to SAPI on failure."""
    try:
        import asyncio
        import edge_tts
        fd, mp3 = tempfile.mkstemp(prefix="ace_voice_", suffix=".mp3")
        os.close(fd)

        async def _render():
            await edge_tts.Communicate(text, _VOICE).save(mp3)

        asyncio.run(_render())

        if seq != _seq[0]:                       # a newer line already superseded this one
            _safe_remove(mp3)
            return
        with _lock:
            if seq != _seq[0]:
                _safe_remove(mp3)
                return
            _proc[0] = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", mp3],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW)
    except Exception:
        if _SAPI and seq == _seq[0]:             # offline / render failed -> robotic fallback
            _speak_sapi(text)


def _speak_sapi(text):
    safe = text.replace("'", "''")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.Rate = 1;"
          f"$s.Speak('{safe}')")
    try:
        with _lock:
            _proc[0] = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW)
    except Exception:
        pass


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def stop():
    with _lock:
        p = _proc[0]
        _proc[0] = None
    if p is not None and p.poll() is None:
        try:
            p.terminate()
        except Exception:
            pass


atexit.register(stop)
