"""Shared 'luxe casino night' look — a dark navy/black palette with gold, plus a
gradient banner with a glowing gold title. Kept small and dependency-free; every
screen imports these so the casino feels like one place.
"""
import tkinter as tk

# palette
NIGHT = "#0c1020"      # deep navy-black — main background
NIGHT2 = "#151b33"     # slightly lifted panels
PANEL = "#1e2647"      # game tiles / raised buttons
GOLD = "#f6d365"       # primary accent
GOLD_DEEP = "#c9a227"  # gold shadow / border
IVORY = "#f7faf5"      # cards, dice, reels
INK = "#0a0d18"        # text on gold
MUTED = "#8b93b5"      # secondary text
WINY = "#7fe0a8"       # win green
LOSEY = "#e0616b"      # loss red


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _hx(t):
    return "#%02x%02x%02x" % t


def _lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def paint_gradient(canvas, w, h, top, bottom, steps=60):
    """Fill a canvas with a vertical gradient (drawn as horizontal bands)."""
    c1, c2 = _rgb(top), _rgb(bottom)
    band = h / steps
    for i in range(steps):
        canvas.create_rectangle(0, i * band, w, (i + 1) * band + 1, outline="",
                                fill=_hx(_lerp(c1, c2, i / steps)))


def header(win, title, w=580, h=84, top="#2a1550"):
    """A gradient banner with a glowing gold title, packed at the top of a window."""
    c = tk.Canvas(win, width=w, height=h, highlightthickness=0, bg=NIGHT)
    c.pack()   # centered (not fill-x) so the title stays centered when the window is maximized
    paint_gradient(c, w, h, top, NIGHT, steps=40)
    for dx, dy, col in [(2, 3, "#221a06"), (0, 2, GOLD_DEEP)]:   # faux glow: layered text
        c.create_text(w // 2 + dx, h // 2 + dy, text=title, font=("Georgia", 24, "bold"), fill=col)
    c.create_text(w // 2, h // 2, text=title, font=("Georgia", 24, "bold"), fill=GOLD)
    return c


def scrollable(win, bg=NIGHT):
    """Wrap a window's body in a vertically scrollable area and return the inner
    frame — pack all your content into that frame instead of the window.

    Why: tkinter lays out in fixed pixels and can't fluidly shrink content, so a
    tall game (big wheel + all its controls) can run off the bottom of the screen
    with no way to reach the buttons. This is the standard fix: a Canvas holds an
    inner Frame and scrolls it, with a real Scrollbar on the right and mouse-wheel
    support, so every control is always reachable no matter how tall the content or
    how small the screen. The inner frame always matches the visible width, so the
    content still fills the window horizontally (and game art can grow when maximized).
    """
    outer = tk.Frame(win, bg=bg)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    vbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                        troughcolor=NIGHT2, bg=GOLD_DEEP, activebackground=GOLD,
                        relief="flat", bd=0, width=14)
    canvas.configure(yscrollcommand=vbar.set)
    vbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=bg)
    win_id = canvas.create_window((0, 0), window=inner, anchor="n")

    def _on_inner(_=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner)

    def _on_canvas(e):
        canvas.itemconfigure(win_id, width=e.width)          # inner fills the visible width
        canvas.coords(win_id, e.width / 2, 0)                # keep it centered
    canvas.bind("<Configure>", _on_canvas)

    def _wheel(e):                                            # bubbles up from any child widget
        canvas.yview_scroll(int(-e.delta / 120), "units")
    win.bind("<MouseWheel>", _wheel)

    return inner


def show_rules(parent, title, body):
    """Open a styled 'How to Play' popup showing a game's rules / payouts."""
    win = tk.Toplevel(parent)
    win.title(f"{title} — How to Play")
    win.configure(bg=NIGHT)
    win.resizable(False, False)
    header(win, title, w=480, h=66)
    tk.Label(win, text="HOW TO PLAY", font=("Consolas", 10, "bold"), bg=NIGHT, fg=MUTED).pack(pady=(14, 6))
    tk.Label(win, text=body, font=("Segoe UI", 11), bg=NIGHT, fg=IVORY, justify="left",
             wraplength=430).pack(padx=26, pady=(0, 6))
    tk.Button(win, text="Got it", font=("Segoe UI", 11, "bold"), bg=GOLD, fg=INK, relief="flat",
              bd=0, padx=22, pady=6, cursor="hand2", command=win.destroy).pack(pady=(8, 20))
    win.transient(parent)


def names_dialog(parent, on_saved=None):
    """The shared 'Table Names' editor — set your name and the opponent names.
    Used by the lobby and by the in-game 👤 Name buttons. Calls on_saved(new_name)
    after saving so the caller can refresh its display."""
    import profile
    dlg = tk.Toplevel(parent)
    dlg.title("Table Names")
    dlg.configure(bg=NIGHT)
    dlg.resizable(False, False)
    header(dlg, "TABLE NAMES", w=420, h=60)

    def _entry(par, value):
        e = tk.Entry(par, font=("Segoe UI", 12, "bold"), justify="center", width=15,
                     bg=NIGHT2, fg=GOLD, insertbackground=GOLD, relief="flat")
        e.insert(0, value)
        return e

    tk.Label(dlg, text="Your name", font=("Segoe UI", 10, "bold"), bg=NIGHT, fg=IVORY).pack(pady=(14, 2))
    you_ent = _entry(dlg, profile.name())
    you_ent.pack(pady=(0, 10), ipady=4)
    you_ent.focus_set()
    you_ent.select_range(0, "end")

    tk.Label(dlg, text="Opponents (computer players)", font=("Segoe UI", 10, "bold"),
             bg=NIGHT, fg=IVORY).pack(pady=(4, 4))
    grid = tk.Frame(dlg, bg=NIGHT)
    grid.pack(padx=24)
    bots = profile.bot_names()
    bot_ents = []
    for i in range(6):
        e = _entry(grid, bots[i] if i < len(bots) else "")
        e.grid(row=i // 2, column=i % 2, padx=5, pady=4, ipady=3)
        bot_ents.append(e)
    tk.Label(dlg, text="(at least 3 are kept; blank slots are ignored)", font=("Segoe UI", 8),
             bg=NIGHT, fg=MUTED).pack(pady=(4, 0))

    def save(_=None):
        nm = profile.set_name(you_ent.get())
        profile.set_bot_names([e.get() for e in bot_ents])
        if on_saved:
            on_saved(nm)
        dlg.destroy()

    you_ent.bind("<Return>", save)
    tk.Button(dlg, text="Save", font=("Segoe UI", 11, "bold"), bg=GOLD, fg=INK, relief="flat",
              bd=0, padx=24, pady=6, cursor="hand2", command=save).pack(pady=(12, 18))
    dlg.transient(parent)


def rules_button(win, title, body):
    """A small '❔ How to Play' button that opens the rules popup. Packed by the caller."""
    return tk.Button(win, text="❔  How to Play", font=("Segoe UI", 9, "bold"),
                     bg=NIGHT2, fg=GOLD, activebackground="#232b4d", relief="flat", bd=0,
                     padx=10, pady=4, cursor="hand2",
                     command=lambda: show_rules(win, title, body))


def music_toggle(win):
    """A small 🔊/🔇 button that mutes/unmutes the shared music from inside any game.
    The caller positions it (e.g. .place(relx=1.0, x=-10, y=10, anchor='ne'))."""
    import audio
    btn = tk.Button(win, font=("Segoe UI", 12, "bold"), bg=NIGHT2, fg=GOLD,
                    activebackground="#232b4d", relief="flat", bd=0, width=3, cursor="hand2")

    def _toggle():
        on = audio.toggle()
        btn.config(text="🔊" if on else "🔇")

    btn.config(text="🔊" if audio.is_on() else "🔇", command=_toggle)
    return btn


def music_bar(win):
    """A compact in-game music strip: ⏮ previous · 🔊/🔇 mute · ⏭ next — so you can
    change the song without going back to the lobby. The caller positions it
    (e.g. .place(relx=1.0, x=-8, y=8, anchor='ne'))."""
    import audio
    bar = tk.Frame(win, bg=NIGHT2)

    def _mk(txt, cmd, w=2):
        return tk.Button(bar, text=txt, font=("Segoe UI", 11, "bold"), bg=NIGHT2, fg=GOLD,
                         activebackground="#232b4d", relief="flat", bd=0, width=w, cursor="hand2",
                         command=cmd)

    prev_b = _mk("⏮", audio.prev_track)
    mute_b = _mk("🔊", None, w=3)
    next_b = _mk("⏭", audio.next_track)

    def _toggle():
        on = audio.toggle()
        mute_b.config(text="🔊" if on else "🔇")
    mute_b.config(command=_toggle)

    prev_b.pack(side="left", padx=1)
    mute_b.pack(side="left", padx=1)
    next_b.pack(side="left", padx=1)

    def _poll():
        if not bar.winfo_exists():
            return
        on = audio.is_on()
        mute_b.config(text="🔊" if on else "🔇")
        lib = on and audio.source() == "library"          # skip only works on your library
        prev_b.config(state="normal" if lib else "disabled")
        next_b.config(state="normal" if lib else "disabled")
        win.after(1500, _poll)

    _poll()
    return bar
