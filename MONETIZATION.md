# Monetizing Mac ◆ Land Casino — a reference for later

> Currently this is a **free, play-money portfolio project**. This note is here for *if you ever
> decide to charge for it*. Nothing here is set up yet.

## The one rule that keeps it legal

- ✅ **Selling access, or selling virtual chips = legal.** You're selling entertainment / virtual goods.
- ❌ **Letting players cash OUT chips for real money = gambling** — regulated, requires a license.

Keep it **"buy chips, no withdrawals"** and you're a legal *social casino / freemium game* (same model as
Zynga Poker, DoubleDown). The moment chips can be turned back into money, it becomes real gambling — a
licensed business, not a code change. Don't cross that line without lawyers + a gambling license.

## Monetization models (all legal for a no-cash-out game)

| Model | What it is |
|---|---|
| One-time purchase | Pay once to own the app |
| Subscription | Monthly access |
| Buy-chips (IAP) | Real money → virtual chips (no cash-out) |
| Freemium | Free base games; pay to unlock premium games/themes |
| Remove-ads | Free with ads; pay to remove |

## Path 1 — Sell the desktop app (easiest, no backend)

Package it and let a store handle payment + delivery:

1. Bundle to a single `.exe` with **PyInstaller**: `pyinstaller --onefile --windowed main.py`
   (include `games/`, `art.py`, `cards.py`, `theme.py`, `audio.py`).
2. Sell on **Gumroad**, **Itch.io**, the **Microsoft Store**, or **Steam** — they take payment, handle
   refunds/tax, and deliver the download. You'd keep that build closed-source.

- **Pros:** no server, store does the hard parts. **Cons:** store cut (~10–30%); subscriptions/IAP are harder.

## Path 2 — License-key gate (desktop, do-it-yourself)

Gate the app (or "premium" games) behind a key the buyer enters once:

1. Sell keys via a **Stripe Payment Link** or **Gumroad**.
2. Issue a **signed key** (e.g., an Ed25519 / HMAC signature over the buyer's email) at purchase.
3. On first run the app asks for the key and **verifies the signature offline** (no server needed), then
   stores it in `~/.maclandcasino/license`.
4. Lock premium behind "valid key present".

- **Pros:** full control, works offline. **Cons:** desktop keys are ultimately crackable; you run key issuance.

## Path 3 — The web version (the real home for a paywall) — *your stack*

Rebuild as a web app; this is where subscriptions and chip purchases belong:

- **Frontend:** React/Vite · **Backend:** FastAPI (server owns the RNG + chip balances) ·
  **DB/Auth:** Supabase · **Payments:** Stripe.
- **Paywall flow:**
  1. User signs up / logs in (Supabase Auth).
  2. Clicks buy → **Stripe Checkout Session** (a subscription price, or a chip-pack price).
  3. **Stripe webhook** hits your backend → verify the signature → mark them subscribed / credit chips.
  4. Backend **gates** premium features and grants chips; the browser only ever *shows* results.
- **Key pieces:** a Stripe Checkout session endpoint, a webhook endpoint (must verify the signature), an
  `entitlements` / `subscriptions` table, and feature-gating on protected routes.
- You already use **Stripe + Supabase + FastAPI + React**, so this is right in your wheelhouse — it's the
  same shape as adding billing to any SaaS.

## If you ever pull the trigger

- **Quick paid desktop release:** Path 1 (Gumroad/Itch) — least effort.
- **A real product with accounts + recurring revenue:** Path 3 (web + Stripe) — the scalable path.

## The hard line — never do this without a license

Real-money **betting with cash-out / prizes of real value** = licensed gambling: a state or offshore
gambling license, KYC/AML compliance, certified RNG audits, age verification, and a gambling-friendly
payment processor. That's a multi-million-dollar regulated business. Running an unlicensed one is a crime.
Keep Mac ◆ Land Casino play-money, and a paywall (Paths 1–3) is perfectly fine.
