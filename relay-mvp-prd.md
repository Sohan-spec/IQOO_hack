# Relay — Product Requirements Document
### MVP v1 (Hackathon Build)

**Document owner:** Vince
**Status:** Approved for build
**Scope:** MVP only. Everything outside the workflow defined in §4 is explicitly out of scope.

---

## 1. Summary

Relay turns a merchant's own Android phone into the payment verification backend for their online store.

Today, a small Indian merchant selling online has two bad options. They can paste a static UPI QR screenshot on their checkout page and manually eyeball their PhonePe notifications to confirm each order — slow, error-prone, and unscalable. Or they can integrate a payment aggregator like Razorpay or Stripe and pay a per-transaction commission on every sale.

Relay is the third option. The customer pays over standard UPI directly into the merchant's existing bank account. The merchant's phone, running the Relay app, detects the incoming payment notification, matches it against a pending order, and automatically confirms the order back to the storefront. No funds ever pass through Relay. No commission is charged.

**MVP objective:** demonstrate a complete, unbroken, automatic payment→verification→confirmation loop across three physical devices, with no human in the middle.

---

## 2. Goals and Non-Goals

### 2.1 Goals

| # | Goal |
|---|---|
| G1 | Customer completes checkout and is redirected into their UPI app with payee and amount pre-filled |
| G2 | Storefront registers a pending transaction on the owner device before the customer pays |
| G3 | Owner device automatically detects the incoming UPI credit notification |
| G4 | Owner device matches the notification against the pending transaction without manual input |
| G5 | Storefront UI updates to a confirmed state automatically, with no page refresh or user action |
| G6 | End-to-end latency from customer payment to confirmed UI under 10 seconds |

### 2.2 Non-Goals (MVP)

These are deliberately excluded. They are not deferred features to sneak in — they are out of scope for this build.

- Merchant onboarding, signup, authentication, or multi-merchant support
- Refunds, partial payments, order cancellation, or reconciliation reports
- iOS owner app (Android only — the verification mechanism does not exist on iOS)
- Real product catalog, inventory, or persistent order history
- Settlement, escrow, or any handling of funds by Relay
- Fraud detection beyond the matching rules defined in §7
- Production security hardening, rate limiting, or abuse prevention
- Play Store distribution and permission declaration compliance

---

## 3. Actors and Devices

| Actor | Device | Role |
|---|---|---|
| **Customer** | Personal phone (or laptop + phone) | Browses the storefront, checks out, pays via their own UPI app |
| **Merchant / Owner** | Android phone, always on, running the Relay app | Acts as the verification backend. Receives payment into their existing UPI account |
| **Storefront** | Web app, publicly reachable | Hosts the shop, checkout, and post-payment status UI |

Three physical devices are required for the demo. The customer device and the owner device must be separate handsets.

---

## 4. Core Workflow — Canonical

**This section is fixed. No module may deviate from it.**

1. Customer visits the online shop, adds items to cart, proceeds to checkout.
2. Customer enters their details — Name, Email, and other checkout fields — and clicks **Pay**.
3. On the Pay click, two things happen:
   - **3a.** The customer is redirected to their UPI payment app, with the merchant's UPI ID and the cart total pre-filled.
   - **3b.** The shop sends an API call to the owner device's on-device backend queue, with a body containing: **Name**, **payment amount**, and **session ID**.
4. The customer pays the amount from the UPI app of their choice.
5. On the owner device:
   - The pending transaction for this session is already sitting in the queue, placed there in step 3b.
   - The Relay app reads the incoming PhonePe notification indicating an amount was credited. The notification carries a **Name** and an **amount**.
   - These two fields are cross-checked against the entries in the queue.
6. Once verified, the owner device sends a success API call back to the storefront, carrying the matching **session ID**.
7. The storefront UI for that customer updates to a confirmed state.

Steps 3a and 3b are concurrent and independent. Step 3b must not block or delay the redirect in 3a.

---

## 5. System Architecture

Three modules, each independently buildable and testable.

```
┌────────────────────┐                    ┌──────────────────────┐
│   MODULE A         │   1. enqueue       │   MODULE C           │
│   Storefront       │───────────────────▶│   Owner Device App   │
│   (Web)            │                    │   (Android)          │
│                    │◀───────────────────│                      │
│                    │   3. confirm       │   • Queue            │
└─────────┬──────────┘   (session ID)     │   • Notif. Listener  │
          │                               │   • Matcher          │
          │ 2. UPI deep link              └──────────▲───────────┘
          ▼                                          │
┌────────────────────┐                                │
│   MODULE B         │        UPI rails               │
│   Customer Device  │────────────────────────────────┘
│   (UPI app)        │   payment → credit notification
└────────────────────┘
```

Relay owns Module A and Module C. Module B is the customer's existing UPI app and is not built — only integrated with, via the UPI deep link specification.

### 5.1 Connectivity note

The owner device must be reachable by the storefront over the network for steps 3b and 6. For the MVP demo this is satisfied by a tunnel exposing the on-device HTTP listener to a public URL, or by both devices sitting on the same local network with the owner device's address configured in the storefront. This is a transport detail and does not alter the workflow: the queue, the matching, and the verification decision all live on the owner's phone.

---

## 6. Module Specifications

### 6.1 Module A — Storefront (Web)

The customer-facing shop. Responsible for collecting order details, initiating both branches of step 3, and reflecting final state.

**Screens**

| Screen | Purpose |
|---|---|
| Catalog | A small hardcoded set of products with add-to-cart |
| Cart | Line items and computed total |
| Checkout | Name, Email, and other customer fields. Single **Pay** action |
| Awaiting Payment | Shown immediately after Pay. Displays amount, session reference, and a live "waiting for confirmation" state |
| Confirmed | Success state. Order reference and paid amount |

**Responsibilities**

- **A1 — Session creation.** On Pay, generate a unique session ID for the transaction. This ID is the correlation key for the entire lifecycle and must be unique per checkout attempt.
- **A2 — Enqueue.** Send the pending transaction to the owner device queue: Name, payment amount, session ID. Fire this before or concurrently with the redirect.
- **A3 — Deep link redirect.** Construct a UPI deep link containing the merchant's VPA, merchant name, exact amount, currency, and the session ID carried in the transaction reference field. Redirect the customer to it.
- **A4 — Await confirmation.** Hold the customer on the Awaiting Payment screen and listen for confirmation against their session ID.
- **A5 — Confirmation endpoint.** Expose an endpoint the owner device calls with a session ID to mark that transaction confirmed.
- **A6 — UI update.** On confirmation, transition the customer's view to the Confirmed screen without requiring a refresh or any user action.

**Constraint:** the Awaiting Payment screen must survive the app-switch to the UPI app and back. The customer leaves the browser and returns; the session must still be live when they do.

---

### 6.2 Module B — Customer Device (UPI App)

Not built by Relay. Integrated with via the UPI deep link specification.

**Responsibilities**

- **B1** — Receive the deep link and open the customer's chosen UPI app with payee and amount pre-filled.
- **B2** — Customer authorises and completes the payment through their normal UPI flow.
- **B3** — Payment settles directly from the customer's bank to the merchant's bank over UPI rails.

**Deep link fields used**

| Field | Content |
|---|---|
| Payee address | Merchant's VPA |
| Payee name | Merchant display name |
| Amount | Cart total, exact, two decimal places |
| Currency | INR |
| Transaction reference | Session ID |
| Transaction note | Human-readable order reference |

**Known constraint:** the UPI deep link flow provides no guaranteed callback to the originating web page. The customer's browser cannot learn the outcome of the payment. This is precisely why verification is architected on the owner side. It is a property of UPI, not a limitation of Relay.

---

### 6.3 Module C — Owner Device App (Android)

The on-device backend. This is the core of the product and the centre of the demo.

#### C1 — Ingress / Queue

- Accepts pending transactions from the storefront (Name, amount, session ID).
- Stores them in an in-memory pending queue on the device.
- Each entry carries a timestamp at insertion.
- Entries live in the queue until matched or until they expire.

**Pending entry fields**

| Field | Type | Source | Purpose |
|---|---|---|---|
| Session ID | String | Storefront | Correlation key returned on confirmation |
| Customer name | String | Checkout form | Matching signal |
| Amount | Decimal | Cart total | Primary matching signal |
| Created at | Timestamp | Device clock | Expiry and tie-breaking |
| Status | Enum | Internal | `pending` / `confirmed` / `expired` |

#### C2 — Notification Listener

- Runs as a background service with notification access granted.
- Observes every notification posted on the device.
- Filters to payment app packages only. **PhonePe is the required target for MVP.** Other UPI apps are optional additions if time permits.
- On a matching notification, extracts the raw title and body text and forwards it to the matcher.

**Permission:** notification access is a special app access granted manually by the owner in Android system settings. The app must detect whether access is granted, and if not, present a clear prompt that opens the settings screen. This grant must be completed during setup, not during a live transaction.

#### C3 — Parser

- Extracts the credited **amount** from the notification text.
- Extracts the payer **name** from the notification text.
- Discards notifications that are not credit events — promotional messages, debit alerts, and app chatter must not enter the matcher.

**Note:** notification text formatting varies by app and app version. The parser must be built against notification strings captured from the actual demo device, not against assumed formats.

#### C4 — Matcher

Takes a parsed credit event and resolves it to at most one pending queue entry. Rules are specified in §7.

#### C5 — Confirmation Sender

- On a successful match, calls the storefront confirmation endpoint with the matched session ID.
- Marks the queue entry `confirmed`.
- Retries on network failure with a short backoff. A confirmed payment must not be lost because the merchant's phone briefly dropped signal.

#### C6 — Operator UI

A single screen on the owner phone, visible during the demo. It is both a debugging surface and a persuasion device — it makes the invisible verification legible to a judge.

- Notification access status indicator
- Live list of pending transactions: name, amount, elapsed time
- Live feed of detected credit events
- Visual match event: pending entry and credit event resolving into a confirmation
- **Manual confirm control** — see §9

---

## 7. Verification and Matching Logic

The matcher receives a credit event (amount, name) and searches the pending queue.

**Rules, in order:**

1. **Amount is the primary key.** Filter pending entries to those whose amount equals the credited amount exactly.
2. **Time window.** Discard candidates older than the expiry window (default: 5 minutes from creation). A payment cannot match an order placed long before it.
3. **Name as a secondary signal.** Where multiple candidates survive, use a normalised, case-insensitive comparison between the checkout name and the payer name to disambiguate.
4. **Oldest-first tie-break.** If ambiguity remains, resolve to the oldest surviving candidate.
5. **No match, no action.** If zero candidates survive, log the credit event and take no action. Relay must never confirm an order it cannot attribute.
6. **Single confirmation.** A queue entry can be confirmed exactly once. Repeat notifications for the same credit must not double-confirm.

**Why name is secondary, not primary:** the name in a UPI notification is the payer's bank-registered name, which frequently differs from what the customer typed at checkout — initials, surname ordering, or an account held in a family member's name. Treating it as a hard requirement would cause false negatives on legitimate payments. Amount plus a tight time window is the reliable signal; name narrows collisions within it.

**Known MVP limitation:** two customers paying identical amounts within the same window is an ambiguous case. The MVP resolves it by oldest-first and accepts the residual risk. This is an acknowledged gap, not an oversight, and is the first thing to address post-hackathon.

---

## 8. Transaction State Machine

| State | Entered when | Exits to |
|---|---|---|
| `created` | Customer clicks Pay; session ID generated | `pending` |
| `pending` | Entry accepted into the owner device queue | `confirmed` or `expired` |
| `confirmed` | Matcher resolves a credit event to this entry | terminal |
| `expired` | Time window elapses with no match | terminal |

The storefront reflects `pending` as the Awaiting Payment screen and `confirmed` as the Confirmed screen. `expired` surfaces to the customer as a prompt to contact the merchant — the MVP does not attempt automated recovery.

---

## 9. Demo Reliability

The demo depends on a live payment, a live notification, and three devices on a network the team does not control. The following are build requirements, not suggestions.

- **R1 — Manual confirm control.** The owner app must include a control that confirms a selected pending transaction directly, executing the identical confirmation path as an automatic match. This is a fallback for a live failure, not the primary flow. The automatic path remains the demonstrated capability.
- **R2 — Pre-granted permissions.** Notification access must be granted and verified on the demo device before presenting.
- **R3 — Real-device parser validation.** The parser must be tested against genuine PhonePe credit notifications captured on the actual demo handset, using real low-value payments.
- **R4 — Network fallback.** Do not depend on venue Wi-Fi. Have a mobile hotspot configured and tested as the demo network.
- **R5 — Do Not Disturb off.** Notification delivery on the owner device must be verified under the exact settings state used during the demo.

---

## 10. Success Criteria

The MVP is complete when, on three separate physical devices and with no manual intervention:

1. A customer completes checkout and lands in their UPI app with the correct amount pre-filled.
2. The pending transaction appears in the owner app queue before the payment is made.
3. The customer pays, and the owner app detects and parses the credit notification.
4. The matcher resolves it to the correct pending entry.
5. The storefront transitions to Confirmed within 10 seconds of payment, with no refresh or user action.

All five must pass in a single continuous run.

---

## 11. Post-MVP Considerations

Recorded for the pitch and roadmap. Not in this build.

- **Stronger correlation.** Where a UPI app surfaces the transaction reference in the notification, match on session ID directly rather than on amount and name.
- **Trust model.** Notification text is an unsigned string posted by another app. It is adequate for a trusted single-merchant MVP and inadequate as a long-term fraud boundary. Production verification should reconcile against bank-side data.
- **Regulatory posture.** Funds move directly customer-bank to merchant-bank; Relay never holds, routes, or aggregates money. This is a materially different position from a payment aggregator, and it is the correct framing for any regulatory conversation. The boundary is untested and warrants proper legal review before commercial launch.
- **Resilience.** Persistent queue surviving app restart, multi-device redundancy, and merchant-side dispute tooling.
