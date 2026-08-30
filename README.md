# Relay

Zero-commission UPI verification for a hackathon MVP. The customer pays the merchant’s existing UPI ID over normal UPI rails. Relay never holds funds. The merchant’s Android phone reads the PhonePe credit notification, matches it to a pending checkout, and confirms the order back to the storefront.

This repo is the working three-party loop: a public Pay page, a cloud ingress that reaches the phone from any network, and an on-device Python matcher inside a Flutter APK.

## How a payment is confirmed

```
 Customer browser                 Cloud                      Owner Android phone
 ┌─────────────────┐         ┌──────────────┐         ┌──────────────────────────┐
 │ checkout/       │  POST   │ relay/       │  WS     │ owner_app + backend/     │
 │ Pay page        │────────▶│ Modal ingress│────────▶│ queue / parser / matcher │
 │                 │         └──────────────┘         │                          │
 │ upi://pay?…     │                                  │ PhonePe notif (Kotlin)   │
 │        │        │                                  │        │                 │
 │        ▼        │                                  │        ▼                 │
 │  (customer UPI  │         UPI credit ─────────────▶│ match amount (+ name)    │
 │   app, not ours)│                                  │                          │
 │                 │◀──────── POST /confirm ──────────│ C5 callback (Bearer)     │
 │ poll /status    │         checkout/                └──────────────────────────┘
 └─────────────────┘
```

1. Customer opens the Pay page, enters name (and optional email / phone), taps **Pay**.
2. The page fires two things at once: enqueue `POST {RELAY_URL}/v1/transactions`, and redirect into a UPI app (`upi://pay?pa=…&am=…`).
3. Ingress forwards the enqueue over a live WebSocket to the owner phone. The on-device queue stores the pending session.
4. The customer pays. PhonePe posts a credit notification on the owner phone.
5. Kotlin forwards the raw title/body to Python on `127.0.0.1:8787`. The parser extracts amount and payer name; the matcher picks a pending row.
6. On a match (or a manual confirm in the owner UI), Python POSTs `{session_id, status: "confirmed"}` to the checkout callback URL.
7. The Pay page polls `GET /status/{session_id}` and flips to confirmed without a refresh.

Matching (primary → tie-break): exact amount, pending only, within 5 minutes, then case-insensitive name if two rows share an amount, else oldest `created_at`. Two identical-amount payments in the same window are a known limitation.

## Layout

| Path | Role |
|------|------|
| `owner_app/` | Flutter owner app (default UI: `lib/demo_ui/`). Kotlin listener, wake lock, WebSocket client. |
| `backend/` | On-device Python: queue, PhonePe parser, matcher, confirm sender, HTTP on `:8787`. Embedded via Chaquopy. |
| `relay/` | Public ingress. Storefront HTTP in, phone WebSocket out. No payment state. |
| `checkout/` | Public Pay page, `POST /confirm`, `GET /status/{session_id}`. |
| `tools/demo_storefront_stub.py` | Laptop stand-in for enqueue + callback (no Pay page). |
| `owner_app/DEVICE_SETUP.md` | iQOO / vivo battery and autostart steps the app cannot grant. |

Product intent: `context.md` and `relay-mvp-prd.md`.

## Prerequisites

- Android phone (arm64, PhonePe installed). Demo target is iQOO / OriginOS.
- Flutter SDK (Dart `^3.13`), Python **3.13**, JDK 17.
- [Modal](https://modal.com) CLI for the public relay and checkout services.
- A merchant VPA that receives credits as PhonePe notifications (`com.phonepe.app`).

## 1. Owner app

One APK. Flutter UI + Kotlin `NotificationListenerService` + Chaquopy CPython. Python binds `0.0.0.0:8787` at process start (`RelayApplication`). ABI is `arm64-v8a` only.

```bash
cd owner_app
flutter pub get
flutter run
# release APK:
flutter build apk --release
```

`lib/main.dart` launches the polished tab UI (`DemoApp`), which polls the on-device snapshot. The older operator screen is `RelayOwnerApp` in the same file.

On first launch:

1. Grant **notification access** (not only the “allow notifications” popup) for Relay Owner.
2. Allow **ignore battery optimizations**.
3. On iQOO, also do Autostart / unrestricted background / lock in recents — see `owner_app/DEVICE_SETUP.md`.
4. Open **Settings** in the app:
   - Paste the same `RELAY_SECRET` used by Modal (`relay-hmac`). Stored in Keystore-backed DataStore. The phone then connects to `wss://sohan-spec--relay.modal.run/connect`.
   - Paste `CHECKOUT_CONFIRM_SECRET`. Python sends it as `Authorization: Bearer` on confirm POSTs.
5. Copy the **merchant UUID** shown in Settings into checkout’s `CHECKOUT_MERCHANT_ID` and redeploy checkout. A fresh install issues a new UUID.

Secrets are **not** compiled into the APK.

### On-device HTTP (loopback / LAN)

| Method | Path | Who |
|--------|------|-----|
| `POST` | `/v1/transactions` | Ingress (via phone WS) or LAN storefront |
| `POST` | `/v1/internal/notifications` | Kotlin listener |
| `GET` | `/v1/internal/snapshot` | Owner UI (poll ~500 ms) |
| `POST` | `/v1/internal/transactions/{session_id}/confirm` | Manual confirm (same confirm path as auto-match) |
| `POST` | `/v1/internal/settings` | Default callback URL, etc. |

USB debug:

```bash
adb forward tcp:18787 tcp:8787
curl -sS http://127.0.0.1:18787/v1/internal/snapshot
```

## 2. Ingress (`relay/`)

Forwards enqueue to whichever phone is connected for that `merchant_id`. Confirm callbacks do **not** go through this service.

Auth: `RELAY_SECRET` HMAC token `{merchant_id}.{hmac_hex}`. Modal secret name: `relay-hmac`.

```bash
cd relay
openssl rand -hex 32 > .secret
chmod 600 .secret
python3 -c 'from pathlib import Path; Path(".secret.env").write_text("RELAY_SECRET="+Path(".secret").read_text().strip()+"\n")'
modal secret create relay-hmac --from-dotenv .secret.env --force
modal deploy modal_app.py
```

Do not commit `.secret` or `.secret.env`. Copy the same hex onto the phone.

Deployed URLs (workspace `sohan-spec`, label `relay`):

- Health: `https://sohan-spec--relay.modal.run/health`
- Enqueue: `https://sohan-spec--relay.modal.run/v1/transactions`
- Phone WS: `wss://sohan-spec--relay.modal.run/connect`

`min_containers=1` and `max_containers=1` are required so the WebSocket and the storefront POST share one in-memory hub.

Local:

```bash
cd relay
export RELAY_SECRET="$(cat .secret)"
uvicorn app:app --host 127.0.0.1 --port 8080 --ws-ping-interval 25 --ws-ping-timeout 10
```

## 3. Checkout (`checkout/`)

Serves `GET /` (Pay), `POST /confirm`, `GET /status/{session_id}`. VPA, payee name, and merchant id are **not** customer form fields.

```bash
cd checkout
cp .env.example .env
# set CHECKOUT_VPA, CHECKOUT_PAYEE_NAME, CHECKOUT_MERCHANT_ID,
# CHECKOUT_CONFIRM_SECRET (32+ hex bytes; same value as on the phone)
modal secret create checkout-merchant --from-dotenv .env --force
modal deploy modal_app.py
```

`POST /confirm` is public (the phone must reach it) but returns 401 without the Bearer secret and does not change session status. Status GET is CORS-open so the Pay page can poll.

Local:

```bash
cd checkout
# export the same CHECKOUT_* vars (and optional RELAY_URL)
uvicorn app:app --host 127.0.0.1 --port 8000
```

## Laptop-only demo (no Pay page)

With the phone on USB or the same LAN:

```bash
python3 tools/demo_storefront_stub.py --help
```

This enqueues a pending session and listens for the C5 callback. It is not Module A and is not the public checkout.

## Tests

```bash
# on-device backend (stdlib only on the phone; pytest on the host)
cd backend && python3 -m pytest tests/ -q

cd relay && python3 -m pytest tests/ -q   # needs relay/requirements-dev.txt
cd checkout && python3 -m pytest tests/ -q
cd owner_app && flutter test
```

## MVP limits

- Android owner device only. Customer UPI app is not built (deep links have no reliable browser callback).
- PhonePe credit notifications only.
- No refunds, auth/onboarding, catalog, or Play Store packaging.
- Parser fixtures in `backend/app/fixtures/phonepe_credits.json` are still placeholders until real iQOO banners are captured.
- Confirm delivery retries in the background (0.5 / 1 / 2 / 4 s). Status stays `confirmed` even if the callback never gets a 2xx (`confirm_acked` stays false).
