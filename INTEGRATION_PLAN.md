# Frontend ↔ Backend Integration Plan (MVP)

Goal: make the **polished Flutter UI** (`owner_app/lib/demo_ui/`) run on **live data from the
on-device Python backend**, instead of the fake `DemoController` seed data it uses today. When
this is done, the pretty owner app is the real, functional app: it shows real pending payments,
reflects auto-matched confirmations live, and its confirm button performs a real R1 manual confirm.

**MVP only. No new features. No backend changes.** The Python backend already exposes everything
the UI needs; this is a Flutter-side wiring job. If you find yourself editing `backend/app/**`,
stop — you're out of scope.

---

## 0. Current state (why the two halves are isolated)

- **Backend** — `backend/app/`, stdlib `http.server` bound to `0.0.0.0:8787`, embedded in the
  Android process via Chaquopy (`RelayApplication.kt`). Complete and tested. Contracts it already
  serves (see `backend/app/main.py` routing):
  - `GET  /v1/internal/snapshot` → `{ pending[], recent_matches[], recent_credits[],
    recent_raw_notifications[], default_callback_url, server:{bind} }`
  - `POST /v1/internal/transactions/{session_id}/confirm` → R1 manual confirm (same code path as an
    auto-match; atomic under the queue lock)
  - `POST /v1/transactions` → storefront enqueue (used by the customer side / `tools/demo_storefront_stub.py`, **not** by this UI)
  - `POST /v1/internal/settings`, `POST /v1/internal/notifications` (listener → parser)
- **Two Flutter front ends** in `owner_app/lib/`:
  - `ui/operator_screen.dart` — plain/debug UI, **already fully wired** to the backend via
    `api/python_client.dart` (500 ms snapshot poll, `manualConfirm`) and
    `notification/notification_bridge.dart` (native permission/DND/battery). This is the reference
    for every call the pretty UI must make. **Do not delete it** until the pretty UI reaches parity.
  - `demo_ui/` — the polished UI ported from `app-ui-html/relay-app.html`. Runs entirely on
    `DemoController`'s `seedPayments()` fake data. **No backend calls at all.** This is the "frontend"
    to be integrated.
- Entry points: `main.dart` → `OperatorScreen` (what the APK ships today); `main_demo.dart` →
  `DemoApp` (the pretty UI, dev-run only via `flutter run -t lib/main_demo.dart`).

The whole integration = replace `DemoController`'s fake state with a live poll of the backend
snapshot + native bridge, keeping every `demo_ui` widget/screen visually unchanged, then ship the
pretty UI as the default entry point.

---

## 1. Scope

**In scope (this pass):**
1. A live data source in `demo_ui`: poll `GET /v1/internal/snapshot` + native bridge on a timer.
2. Map the backend snapshot → the existing `Payment` model the `demo_ui` widgets already render.
3. Wire the confirm sheet's **Confirm payment** button to the real R1 endpoint.
4. Reflect real notification-access state in the UI (read-only; tap → system settings).
5. Make the pretty UI the app's default entry point.

**Explicitly OUT of scope (do NOT build):**
- Any change to `backend/app/**` or the HTTP contracts.
- Module A (web storefront / cart / checkout). It stays external; the customer side is simulated by
  `tools/demo_storefront_stub.py` and by real UPI payments per `phases.md` Phase 4.
- Module B (customer phone).
- A backend "reject" concept, refunds, auth, merchant-profile editing, export, sound, or an
  in-app auto-confirm toggle. None of these exist in the backend and none are MVP.
- Rewriting or restyling any `demo_ui` widget. Pixels stay as they are.

---

## 2. Architecture of the integration

```
  ┌─────────────────────────── Android process (one APK) ───────────────────────────┐
  │                                                                                   │
  │   Flutter  demo_ui/                          Python backend (Chaquopy)            │
  │   ┌───────────────────────┐   loopback HTTP  ┌──────────────────────────────┐    │
  │   │ LiveController        │ ───GET  /v1/internal/snapshot ──────────────────▶│    │
  │   │  (was DemoController)  │ ◀── pending / recent_matches / recent_credits ───│    │
  │   │                        │ ───POST /v1/internal/transactions/{id}/confirm ─▶│    │
  │   │  maps snapshot→Payment │                                                  │    │
  │   └───────────┬────────────┘   MethodChannel  ┌──────────────────────────────┘    │
  │               │                 com.relay.owner/device (DeviceBridge)             │
  │               └── notificationAccessGranted / openNotificationAccessSettings      │
  │                                                                                   │
  │   Home / Payments / Account / Settings screens + ConfirmSheet  (UNCHANGED)        │
  └───────────────────────────────────────────────────────────────────────────────────┘
```

- Reuse `owner_app/lib/api/python_client.dart` verbatim — it already has `Snapshot`,
  `snapshot()`, and `manualConfirm(sessionId)`. It is the single source of backend truth.
- Reuse `owner_app/lib/notification/notification_bridge.dart` (`DeviceBridge`) for permission state.
- The backend auto-confirms matched payments on its own (matcher path). The UI never needs to
  "cause" that — it just polls, and a pending row becomes a successful row on the next tick. Polling
  is the only mechanism; no SSE, matching `PLAN.md`'s 500 ms snapshot-poll decision.

---

## 3. Backend data → `Payment` mapping (the crux)

Backend field shapes (from `backend/app/models.py` `to_public_dict`):

- **`snapshot.pending[]`** (status is always `"pending"` here):
  `{ session_id, customer_name, amount:"150.00", created_at:ISO, status, confirm_acked, elapsed_seconds }`
- **`snapshot.recent_matches[]`** (last 50, newest-first; these are the confirmed ones):
  `{ session_id, customer_name, amount:"150.00", payer_name, source:"matcher"|"manual", at:ISO,
     via:"auto"|"manual", matched_at:ISO, status:"confirmed", confirm_acked }`
- **`snapshot.recent_credits[]`** (raw parsed PhonePe credits, last 50): not needed by the pretty UI's
  three screens; ignore for MVP (the plain operator screen shows them; the pretty design has no
  credit-feed surface).

Target model — `owner_app/lib/demo_ui/models.dart` `Payment`:
`{ id, name, amount, status:PayStatus{pending|successful|failed}, group, clock, relative, ref? }`

Mapping rules the LiveController must apply each poll:

| Payment field | From a `pending[]` entry | From a `recent_matches[]` entry |
|---|---|---|
| `id` | `session_id` | `session_id` |
| `name` | `customer_name` | `customer_name` |
| `amount` | parse `amount` string → num (see §4.1) | same |
| `status` | `PayStatus.pending` | `PayStatus.successful` |
| `relative` | from `elapsed_seconds` → "just now / N min ago" | from `matched_at` age |
| `clock` | `created_at`.toLocal() → "hh:mm AM/PM" | `matched_at`.toLocal() |
| `group` | date bucket of `created_at` (see §4.2) | date bucket of `matched_at` |
| `ref` | none — no UPI ref exists (see §4.3) | none |

De-duplication: a `session_id` can appear in both `pending` (briefly) and `recent_matches` if the
UI polls mid-transition. Build the confirmed list first from `recent_matches`, then add pending
entries **whose `session_id` is not already in the confirmed set**. One row per session.

`PayStatus.failed` has **no backend source** — the backend never fails/rejects a payment. Failed
rows simply never appear from live data. That's correct for MVP (see §4.4).

---

## 4. Decisions (resolve these exactly as stated — they are the only ambiguous points)

### 4.1 Amount type
Backend amounts are decimal strings like `"150.00"`, possibly with paise. `Payment.amount` is `int`
and `money(int)` formats Indian grouping. **Change `Payment.amount` to `num`** and update `money()`
in `models.dart` to accept `num`, keep the existing lakh/crore grouping on the integer part, and
append `.` + two digits **only when paise are non-zero**. Parse the backend string with
`num.parse(amount)`. Keep the change contained to `money()` and `Payment`; the call sites
(`money(payment.amount)`, `money(total)`) don't change.

### 4.2 Date grouping (`group`)
The Payments screen buckets into `'today'` / `'yesterday'`. Compute from the entry's local date:
today → `'today'`, yesterday → `'yesterday'`, anything older → also `'today'`'s list is wrong, so
put older-than-yesterday under a third bucket is NOT supported by the screen (it only renders
`today` and `yesterday`). MVP: bucket `today` and `yesterday` by real local date; **map anything
older to `'yesterday'`** so it still renders (a demo won't produce older data anyway). Do not add
new date sections — that's a UI change.

### 4.3 UPI reference in the confirm sheet
`ConfirmSheet` shows a "UPI reference" row (`payment.ref`). The backend has **no UPI reference**
field. MVP: set `ref` to the short `session_id` (or the last 12 chars) so the row still renders with
a real, meaningful value. Do not invent a fake random ref, and do not add a backend field for it.

### 4.4 The "Reject" button
`ConfirmSheet` has a **Reject** button that today flips a payment to `failed` locally. The backend
has no reject operation and the fixed workflow (`context.md`) has no reject concept. MVP: **Reject
just closes the sheet** (no state change, payment stays pending). Do not relabel or restyle the
button, do not add a backend call. (Rationale: adding a reject endpoint is a new feature; a local
"failed" flip would lie about backend state on the next poll, which would immediately re-show it as
pending — worse than a no-op.)

### 4.5 Settings toggles
- **Notification access** row: make it reflect the **real** native state via
  `DeviceBridge.notificationAccessGranted()` each poll, and on tap call
  `openNotificationAccessSettings()`. It is not a user-flippable boolean — grant happens in system
  settings. Drive the `PillSwitch`'s value from the live permission bool; tapping it opens settings
  rather than toggling local state.
- **"Confirm payments automatically"** and **"Sound on payment"**: no backend equivalent. Leave them
  as local, non-load-bearing cosmetic switches (unchanged behavior). Do not wire them to anything.

### 4.6 Hero total / count
The backend does not aggregate totals. Derive them client-side from the confirmed set:
`total` = sum of `amount` over `recent_matches` whose `matched_at` is **today** (local);
`count` = number of those. Recompute every poll. (This is display-only; `recent_matches` is capped
at 50, acceptable for a demo.)

### 4.7 Default callback URL field
The pretty UI has no callback-URL settings field, and does **not** need one: in the demo, the
storefront (`demo_storefront_stub.py` / Module A) sends its own `callback_url` on enqueue. Do not
port the operator screen's callback-URL editor into `demo_ui`. (If a future demo needs an operator
default, that's a separate task.)

### 4.8 Access gate (R2)
`PLAN.md` R2 says "do not start the demo with access off." The plain operator screen enforces this
with `AccessGate`. For MVP integration, the minimum is that the Settings notification-access row
reflects reality (§4.5). A full blocking overlay is **optional polish** — include it only as the
last step (§5, task 7) and only if time allows; it is not required for "functional."

---

## 5. Implementation tasks (in order)

Work entirely inside `owner_app/lib/demo_ui/` plus the two entry files. Reuse
`lib/api/python_client.dart` and `lib/notification/notification_bridge.dart` as-is.

### Task 1 — `money()` + `Payment.amount` → `num`  (`demo_ui/models.dart`)
- Change `Payment.amount` field type `int` → `num`.
- Update `money(num n)` per §4.1 (grouping on integer part, optional two-decimal paise).
- Update `seedPayments()` literals if the compiler complains (they're `int`, which is a `num` — fine).

### Task 2 — Add a snapshot→Payment mapper  (`demo_ui/mapping.dart`, new file)
Pure functions, no Flutter deps beyond `models.dart`:
- `List<Payment> paymentsFromSnapshot(Snapshot s)` implementing §3 (confirmed from `recent_matches`,
  then non-duplicate pending), applying §4.1–4.4.
- Helpers: `String relativeFromSeconds(int s)`, `String relativeFromIso(String iso)`,
  `String clockFromIso(String iso)`, `String groupFromIso(String iso)` (§4.2).
- `({num total, int count}) todayTotals(Snapshot s)` per §4.6.
Keep all time math local-timezone via `DateTime.parse(iso).toLocal()`.

### Task 3 — Convert `DemoController` into a live controller  (`demo_ui/models.dart`)
Rename conceptually to a live controller (keep the class name `DemoController` to avoid touching
every screen's imports, OR rename and update the 4 screen constructors + `demo_shell.dart` — your
call; keeping the name is less churn). Changes:
- Constructor takes `PythonClient` and `DeviceBridge` (default to `PythonClient()` / `DeviceBridge()`).
- Replace `payments = seedPayments()` with an empty list populated from the backend.
- Add a `Timer.periodic` (500 ms, matching `PLAN.md`) that calls `_refresh()`:
  - `final snap = await python.snapshot();` → `payments = paymentsFromSnapshot(snap)`,
    `total/count = todayTotals(snap)`; on error keep last-known list and set an `unreachable` flag
    (mirror `operator_screen.dart`'s try/catch — never crash the UI while Python is still binding).
  - `notifAccessOn = await device.notificationAccessGranted();` (guarded).
  - `notifyListeners()`.
- Preserve the existing view-state fields and methods that the screens call: `currentTab`,
  `lastTab`, `showingSettings`, `chipFilter`, `searchQuery`, `pending`, `successful`,
  `filteredPayments`, `openSheet/closeSheet`, `goToTab`, `openSettings/closeSettings`,
  `openPayments`, `setChip`, `setQuery`, `showToast`, `sheetPayment/sheetOpen`. These stay; only their
  data backing changes from seed to live.
- `pending`/`successful`/`filteredPayments` getters keep working unchanged because they filter the
  now-live `payments` list.
- Cancel the timer in `dispose()` (alongside the existing `_toastTimer` / `searchController`).

### Task 4 — Wire confirm + reject  (`demo_ui/models.dart` `confirmPayment` / `rejectPayment`)
- `confirmPayment()`: capture `sheetPayment`; `closeSheet()`; call
  `await python.manualConfirm(p.id)`; on success `showToast('Payment confirmed')` and trigger an
  immediate `_refresh()` (don't optimistically mutate local state — let the next snapshot reflect
  the real `confirmed` status). On failure (e.g. 409 already-confirmed / not pending),
  `showToast('Already confirmed')` or surface the error, then `_refresh()`.
- `rejectPayment()`: per §4.4, just `closeSheet()`. Remove the local `failed` mutation and the
  `total/count` bookkeeping (those were part of the fake flow).
- Delete/ignore now-unused fake helpers if they cause warnings: `nextRef()`, `nowClock()` may still
  be used by the mapper — keep whatever the mapper needs, drop the rest.

### Task 5 — Settings notification-access → real  (`demo_ui/screens/settings_screen.dart`)
- The "Notification access" `PillSwitch` value = `controller.notifAccessOn` (now live from §5.3).
- `onChanged` → `controller.openNotificationAccessSettings()` (add a thin method on the controller
  that calls `device.openNotificationAccessSettings()`), NOT `toggleNotifAccess`.
- Leave "Confirm automatically" and "Sound" switches exactly as-is (§4.5).
- The Account screen's `notif-access` mirror (if present) may also read `notifAccessOn`; optional.

### Task 6 — Make the pretty UI the default app  (entry points)
- Point the shipped app at the demo shell. Simplest: change `lib/main.dart` to `runApp(const DemoApp())`
  (import `demo_ui/demo_app.dart`), OR set the Android build's Dart entrypoint/`flutter run` target to
  `lib/main_demo.dart`. Prefer editing `main.dart` so the default `flutter build apk` ships the pretty
  UI with no extra flags.
- Ensure `DemoApp`/`DemoShell` constructs the controller with real `PythonClient()` + `DeviceBridge()`
  (the defaults from §5.3 handle this).
- Confirm `pubspec.yaml` assets include `assets/images/logo.png` (the hero uses it) — it already
  does per the current demo run; verify.
- Keep `ui/operator_screen.dart` and `main.dart`'s old class available (e.g. as a second entry) only
  if you want a debug fallback; not required.

### Task 7 — (Optional, last) R2 access gate in the pretty shell  (`demo_ui/demo_shell.dart`)
Only if time remains. When `!controller.notifAccessOn`, overlay a blocking prompt (reuse the copy
from `ui/widgets/access_status.dart` / `AccessGate`) that covers the shell and directs the user to
grant access, unlocking once the live poll reports access granted. This satisfies `PLAN.md` R2 but is
polish, not core to "functional."

---

## 6. Verification

Run on a real device (or emulator with the Chaquopy Python server reachable on loopback). The
backend must be running in-process (launch the app — `RelayApplication` boots Python).

1. **Cold start, empty state.** Fresh launch with no pending payments: Home shows the empty
   "Nothing waiting" state, hero total ₹0 / 0 payments, no crash while Python is still binding
   (the try/catch keeps the UI alive; it fills in within one poll).
2. **Enqueue → pending appears.** Run `python tools/demo_storefront_stub.py` (or `curl` a
   `POST /v1/transactions` with a `callback_url` pointing at the stub) with a known
   `customer_name` + `amount`. Within ~1 poll (≤1 s), a pending row with that name/amount appears on
   Home and under Payments → Pending. `elapsed`/clock/group look right.
3. **Auto-match → moves to successful.** Send a real UPI credit (or POST a matching notification to
   `/v1/internal/notifications`) for that exact amount. The matcher confirms it backend-side; within
   one poll the row moves out of Pending into Recent/Successful, hero total/count increment, and the
   stub logs the confirmation callback. No user tap needed — this proves live polling reflects
   backend-driven state.
4. **Manual confirm (R1).** Enqueue another pending, tap it → sheet opens with real name/amount/ref
   (session id). Tap **Confirm payment**. The R1 call fires, the sheet closes, toast shows, and on
   the next poll the row is successful. Confirm the stub received the callback. Response is instant
   (Phase 1 background delivery — the tap never blocks on retries).
5. **Reject = no-op.** Open a pending sheet, tap **Reject** → sheet closes, payment still pending on
   next poll (§4.4). No `failed` row appears.
6. **Notification access reflects reality.** Revoke notification access in system settings → within
   a poll the Settings access switch reads off; tap it → system settings opens. Re-grant → switch
   reads on. (If Task 7 done: the shell blocks while off and unblocks when granted.)
7. **De-dup.** During a fast confirm, verify a session never shows as two rows (one pending + one
   successful) simultaneously — the mapper's dedup (§3) must keep exactly one.
8. **No backend files changed.** `git status` shows edits only under `owner_app/lib/**` (+ this doc).

---

## 7. File-change summary (expected diff surface)

Edit:
- `owner_app/lib/demo_ui/models.dart` — `Payment.amount`→`num`, `money()`, `DemoController`→live
  polling + real confirm/reject.
- `owner_app/lib/demo_ui/screens/settings_screen.dart` — notification-access wired to real bridge.
- `owner_app/lib/main.dart` (or the build's Dart entrypoint) — ship `DemoApp`.

Add:
- `owner_app/lib/demo_ui/mapping.dart` — snapshot→Payment pure mappers.

Reuse unchanged:
- `owner_app/lib/api/python_client.dart`, `owner_app/lib/notification/notification_bridge.dart`,
  every `demo_ui` widget and the Home/Payments/Account screens, all of `backend/`.

Leave untouched (do not delete this pass):
- `owner_app/lib/ui/**` (plain operator UI) — reference/fallback until parity is confirmed.

---

## 8. Known limitations carried into this MVP (state them, don't fix them)
- No reject/refund (backend has none — §4.4).
- No real UPI reference (session id stands in — §4.3).
- Totals derived from the 50-entry `recent_matches` buffer, today-only (§4.6).
- "Confirm automatically" / "Sound" switches are cosmetic (§4.5).
- Account/merchant profile stays static (out of scope).
- Parser regexes remain unverified against real PhonePe strings until `phases.md` Phase 2 — if
  auto-match (verification step 3) fails, that's the parser (`P5` in `CODEBASE_ISSUES.md`), not this
  integration; manual confirm (step 4) still proves the full UI↔backend round-trip.
```
