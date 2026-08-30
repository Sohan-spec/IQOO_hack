# Relay ingress

Public adapter so a storefront on any network can enqueue to the owner phone.
The phone opens `wss://<host>/connect`; the storefront POSTs `/v1/transactions`.
C5 confirm callbacks do **not** go through this service.

Deployed on **Modal** (`modal_app.py`). Fly.io is not used: the personal org
blocked machine placement without a payment method.

## Auth

`RELAY_SECRET` HMAC-signs device tokens `{merchant_id}.{hmac_hex}`.

The secret is a Modal Secret named `relay-hmac`. It is **not** compiled into
the APK. Paste the same value on the phone (Settings → Relay HMAC secret). The
phone stores it in Keystore-backed DataStore.

```bash
openssl rand -hex 32 > .secret
chmod 600 .secret
python3 -c 'from pathlib import Path; Path(".secret.env").write_text("RELAY_SECRET="+Path(".secret").read_text().strip()+"\n")'
modal secret create relay-hmac --from-dotenv .secret.env --force
```

Copy `.secret` onto the phone by hand. Do not commit `.secret` or `.secret.env`.

## Deploy

```bash
modal deploy modal_app.py
```

`min_containers=1` and `max_containers=1` are required. The phone socket is
long-lived, and the in-memory Hub must see both the WebSocket and the storefront
POST. `timeout=86400` is the WebSocket call lifetime (Modal's max); the phone
reconnects if the container is replaced.

Public URL after deploy (workspace `sohan-spec`, label `relay`):

- Health: `https://sohan-spec--relay.modal.run/health`
- Enqueue: `https://sohan-spec--relay.modal.run/v1/transactions`
- Phone WS: `wss://sohan-spec--relay.modal.run/connect`

Confirm with `curl -sS https://sohan-spec--relay.modal.run/health` and
`modal app logs relay-owner-ingress`.

## Local

```bash
export RELAY_SECRET="$(cat .secret)"
uvicorn app:app --host 127.0.0.1 --port 8080 --ws-ping-interval 25 --ws-ping-timeout 10
```

## Storefront call

```bash
curl -sS -X POST https://sohan-spec--relay.modal.run/v1/transactions \
  -H 'Content-Type: application/json' \
  -d '{"merchant_id":"<uuid-from-operator-ui>","session_id":"s1","customer_name":"Priya","amount":"1.00","callback_url":"https://example/confirm"}'
```
