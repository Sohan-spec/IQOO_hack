**Project context — Relay (hackathon MVP):**

We're building Relay, a zero-commission UPI payment gateway alternative where the merchant's own Android phone acts as the payment verification backend. Instead of paying Razorpay/Stripe commission, or manually eyeballing a static QR screenshot, the merchant runs our app and verification is automatic. Funds never touch us — payment goes directly customer-bank to merchant-bank over standard UPI rails; we only detect and confirm it.

There are three devices. (1) **Web storefront** — customer adds to cart, enters Name/Email at checkout, clicks Pay. Two things fire concurrently: the customer is redirected via a UPI deep link into their payment app with merchant UPI ID and cart total pre-filled, and the shop sends a pending transaction (Name, amount, session ID) to the owner phone's on-device queue. (2) **Customer phone** — pays normally through whatever UPI app they use. We don't build this; UPI deep links give no reliable callback to the browser, which is exactly why verification happens on the owner side. (3) **Owner phone (Android)** — reads the incoming PhonePe "amount credited" notification, parses amount and payer name, cross-checks against the pending queue, and on a match calls the storefront back with the session ID. The storefront UI then updates to confirmed live, no refresh.

Matching rules: exact amount is the primary key, within a 5-minute window, with payer name as a secondary disambiguator (bank-registered names often differ from checkout names, so name can't be a hard requirement). Known accepted limitation: two identical-amount payments in the same window, resolved oldest-first.

**This workflow is fixed — don't propose changes to it.** We're optimizing for a working end-to-end demo, not production hardening.

---