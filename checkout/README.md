# Checkout (Pay page + C5 callback)

Serves `GET /` (Pay), `POST /confirm`, `GET /status/{session_id}`.

VPA, payee name, and merchant_id are **not** customer form fields. Set them
via Modal secret `checkout-merchant` (see `.env.example`). After a fresh
phone install the merchant UUID changes — update the secret and redeploy;
do not put that UUID in git or shared docs.

```bash
# gitignored
cp .env.example .env
# fill CHECKOUT_VPA, CHECKOUT_PAYEE_NAME, CHECKOUT_MERCHANT_ID,
# CHECKOUT_CONFIRM_SECRET (phone C5 sends this as Authorization: Bearer)
modal secret create checkout-merchant --from-dotenv .env --force
modal deploy modal_app.py
```

`POST /confirm` is public (the owner phone must reach it from any network) but
rejects unsigned requests with 401 and does not change session status. Paste
the same `CHECKOUT_CONFIRM_SECRET` into the owner app Settings (DataStore +
Keystore, like `RELAY_SECRET`).

`@modal.concurrent(max_inputs=50)` is required so confirm POST and status GET
share the same in-memory map on one container. `GET /status/{id}` is CORS-open
so the storefront can poll from a browser.
