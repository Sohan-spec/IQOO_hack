PHASE 1 — Fix the blocking C5 retry bug and restore confirm_acked visibility on the snapshot

Context: the current implementation of C5 (confirm.py, called from both the automatic matcher path and the R1 manual-confirm route) retries its POST to callback_url inline, on the same request/thread that triggered the confirmation. This has already caused an observed failure: an R1 manual-confirm curl against a dummy/unreachable callback_url timed out at ~5 seconds because the HTTP handler was blocked inside the retry backoff loop before it could return a response. PLAN.md's original spec for this was a background retry loop ("start expiry sweeper + confirm retry loop" in the lifespan), not an inline blocking call — this phase brings the implementation back in line with that and fixes the bug it caused.

Two required changes, in this order:

1. DECOUPLE THE CONFIRM-SEND FROM THE REQUEST THAT TRIGGERS IT.

Whichever caller invokes the confirm path — the ingest route after a successful match, or the R1 manual-confirm route — must do two things in sequence and then return immediately:
  a. Call queue.try_confirm(session_id) (or equivalent) to perform the atomic pending -> confirmed transition. This part stays synchronous and stays inside the existing lock, exactly as before — do not change the locking semantics from Change 3, do not touch test_race.py's guarantees.
  b. Hand off the actual outbound POST to callback_url — including the full retry/backoff sequence — to a background task that runs independently of the request/response cycle. Since the stack is stdlib http.server (not asyncio/FastAPI), implement this as a daemon thread (or a small thread pool / worker queue if one doesn't already exist) that the handler enqueues work onto and returns from without waiting.

The HTTP response to the caller (ingest route or R1 route) must be sent back immediately after step (a) succeeds, carrying the entry's current state (status: "confirmed", confirm_acked: false at that instant) — it must NOT wait for step (b) to finish, succeed, or exhaust its retries. Callers today are already written expecting a response describing the just-completed state transition; do not change that response shape, only stop blocking on delivery.

Make sure the background retry worker still honors every existing rule: same backoff schedule (0.5/1/2/4s), still sets confirm_acked = True only on a 2xx response, still leaves status permanently as CONFIRMED win-or-lose on delivery, never reverts to pending on failure. Do not silently drop failed deliveries after retries exhaust — log them clearly (structured log line with session_id and final failure reason) so a failed delivery is discoverable during a demo debrief.

2. RESTORE confirm_acked AND RECENT-MATCH VISIBILITY ON THE SNAPSHOT.

PLAN.md's HTTP contract explicitly specifies GET /v1/internal/snapshot returns "pending, recent credits, recent matches, confirm_acked flags." The current implementation only surfaces confirm_acked on entries still in the pending list — once an entry transitions to confirmed and (depending on current logic) leaves the pending view, its delivery status becomes invisible except transiently in the R1 response body. Fix the snapshot handler so it returns:
  - pending: entries currently in PENDING state, as today
  - recent_matches: the last N (use the existing MatchEvent ring buffer size, currently 100, or whatever events.py already defines) confirmed/matched entries, each including session_id, status, confirm_acked, matched_at, and via ("auto" | "manual")
  - recent_credits: unchanged, as already implemented

This is the only debugging window available until Module A exists for real, so it needs to actually reflect live delivery state, not just the instant-of-confirmation snapshot.

Do NOT change: the matcher's step-0 pending-only filter, the shared asyncio.Lock's scope or the two callers that use it, the enqueue/409 contract, the parser, or anything in the Flutter/Kotlin layer — this phase is backend-only, confined to the confirm/send path and the snapshot response shape.

VERIFICATION — run this exact sequence after the change and report the results:

1. Enqueue a transaction with a deliberately unreachable callback_url (reuse the same dummy 127.0.0.1:9 setup that caused the original timeout).
2. Trigger R1 manual confirm on it via curl. Measure and report the response time — it must return in well under 1 second, not ~5 seconds, regardless of whether the callback ever succeeds.
3. Immediately curl GET /v1/internal/snapshot and confirm the entry appears under recent_matches with status "confirmed" and confirm_acked: false.
4. Wait past the full retry window (past the 4s final backoff), curl snapshot again, and confirm confirm_acked is still false (since the callback is unreachable) and a failure was logged.
5. Repeat steps 1–3 but with callback_url pointed at something that actually returns 2xx (e.g. a throwaway local listener or webhook.site), and confirm confirm_acked flips to true on the snapshot shortly after.
6. Re-run the full existing test suite (test_race.py, test_double_confirm.py, test_confirm.py, all others in backend/tests/) and confirm nothing regressed — pay particular attention to any test that asserted on the old blocking/inline confirm-send behavior, since those assertions may now be timing-dependent and need adjusting to poll/wait for the background worker rather than assuming synchronous completion.

Report back explicitly: the R1 response time before and after, whether recent_matches/confirm_acked now appear correctly on snapshot, and the full test suite pass/fail state.


PHASE 2 — R3: capture real PhonePe notification strings and validate the parser against them

Context: parser.py's regex patterns (_CREDIT_HINT, _DEBIT_HINT, _AMOUNT_RE, _PAYER_RE) were written against placeholder fixtures in backend/app/fixtures/phonepe_credits.json — invented strings, never captured from the actual PhonePe app installed on this iQOO demo device. This has been the single largest unverified risk in the build since before the wake-lock work started, and every passing parser/matcher test to date only proves the code is internally consistent with guessed input, not that it can read what PhonePe actually posts.

This phase requires physical action on the real device — you cannot complete it purely by editing code. Do the following in order:

1. On the demo iQOO phone, with the Relay app installed, notification access granted, and DND off: send 3 separate real UPI payments of a small amount (e.g. ₹1–₹5 each) TO the merchant VPA configured on that phone, using 3 different sending identities/apps if possible (e.g. one from PhonePe, one from Google Pay, one from a plain bank app) — the PRD's C2 spec says PhonePe is the required MVP target, but capturing what other apps' credit notifications look like now is cheap and informs whether the "PhonePe package only" filter in RelayNotificationListener.kt is too narrow for later.

2. For each payment, capture the EXACT raw notification title and body text as posted on this device. Do this by temporarily adding a raw logging line in RelayNotificationListener.kt (or by reading it from POST /v1/internal/notifications on the Python side, since that's already receiving package/title/text) — log the full unmodified strings, including exact currency symbol usage (₹ vs Rs. vs INR), exact spacing, exact name formatting, and any punctuation. Do not paraphrase or clean up what you capture — the fixtures need to be byte-for-byte real.

3. Replace the contents of backend/app/fixtures/phonepe_credits.json entirely with these captured real strings (keep the existing JSON shape/schema, just replace the invented content), tagged with which sending app produced each one and the actual amount/name involved.

4. Diff the captured strings against what _AMOUNT_RE, _PAYER_RE, _CREDIT_HINT, and _DEBIT_HINT in parser.py currently expect to match. Do not assume they'll work — walk through each captured string manually against each regex and note explicitly where they diverge (e.g. if the real string uses "Rs." with no space before the amount, or if the payer name appears after "by" instead of "from", or if there's no explicit "received" keyword and something else signals a credit instead).

5. Fix the regex patterns to match the real captured strings, prioritizing PhonePe's format since that's the MVP requirement, and note in a comment above each pattern which real captured example it was derived from. If GPay/bank-app formats differ meaningfully and matter for future non-PhonePe support, note that as a follow-up rather than trying to generalize the regex to cover all of them now — MVP scope is PhonePe only per C2.

6. Update backend/tests/test_parser.py so its test cases run against the real captured fixtures instead of (or in addition to) the old placeholder ones. Keep both if useful for regression coverage, but the primary assertions should now be against real device output.

VERIFICATION — run this exact sequence and report results:

1. Full parser test suite passes against the real fixtures.
2. Re-run the same physical payment capture (one more real ₹1 payment) with the fixed regex now live, verify via GET /v1/internal/snapshot that it appears correctly in recent_credits with the right amount and payer name extracted — not just that a notification was received, but that C3 actually parsed it correctly.
3. Confirm the amount-only debit/promo filtering still correctly discards a non-credit PhonePe notification (send yourself a small outbound payment or trigger any other PhonePe notification, e.g. a promotional one if one arrives, and confirm it does NOT appear as a credit event).

Report back: the exact real strings captured (redact the actual payer names/amounts if you'd rather not share them verbatim, but the structural format needs to be visible), what changed in the regex patterns as a result, and the pass/fail state of both the automated tests and the live re-verification payment.


PHASE 3 — Close the three explicitly unproven reliability claims: live-notification-with-real-permission-flow, long screen-off idle, and boot-receiver/Chaquopy restart behavior

Context: three things are currently either unproven or proven only via a shortcut that won't hold up on demo day:
  (a) The only screen-off test so far used `adb shell dumpsys deviceidle whitelist` to grant Doze exemption programmatically — this proves the mechanism (wake lock + Doze exemption together keep the process unfrozen), but has never been tested via the actual user-facing "tap Allow" flow that R2's setup pass triggers, and it's never been tested after a genuinely fresh install.
  (b) The screen-off hotspot test that passed held for roughly 30 seconds. Nothing has verified this holds over a realistic idle period (several minutes), which is what an actual demo waiting period would look like.
  (c) BootReceiver.kt is meant to restart the foreground service after a device reboot, but whether Chaquopy/Python actually comes back up depends on whether starting a service from a BroadcastReceiver transitively triggers RelayApplication.onCreate() (where Chaquopy boots), or whether Python only ever starts if the user manually opens the app first. This has not been tested, only assumed.

Do the following, in order, on the real demo iQOO device:

1. FRESH INSTALL, REAL PERMISSION FLOW.
   Fully uninstall the Relay app (not just force-stop — a true uninstall, to clear any residual Doze-whitelist state from prior adb commands). Reinstall the current debug APK. Walk through the app's actual setup flow as a first-time user would: grant notification access via the real settings screen, and when the ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS dialog appears, tap Allow on the real system dialog — do not use any adb shortcut for this step. Also complete the manual iQOO-specific steps documented in owner_app/DEVICE_SETUP.md (Autostart, unrestricted background power, lock in recents) by hand, on-device.

2. LONG SCREEN-OFF IDLE OVER THE REAL HOTSPOT.
   With the phone acting as its own hotspot (not adb, not USB — the real demo network path) and a laptop connected to it, lock the phone's screen. Wait a minimum of 5 full minutes without touching the phone. Then, from the laptop, curl GET http://<phone-hotspot-ip>:8787/v1/internal/snapshot. It must succeed. Repeat this for at least one additional 5-minute idle window later in the same session (i.e. two separate long-idle checks, not just one), to rule out a first-idle-only fluke.

3. REBOOT AND BOOT-RECEIVER VERIFICATION.
   With the app still installed and all permissions/toggles from step 1 in place, reboot the phone fully. After it finishes booting, DO NOT open the Relay app manually. Wait 60 seconds, then attempt GET /v1/internal/snapshot from a laptop on the hotspot. Use `adb shell dumpsys activity services` (this one adb use is fine — it's a read-only diagnostic, not a permission bypass) to confirm whether KeepAliveService is actually running post-boot, and check whether the snapshot request actually succeeds (proving Python/Chaquopy came up) or times out (proving BootReceiver restarts the Android service shell but Python inside it never boots). If it fails, do not treat this as a Phase 3 blocker requiring a redesign yet — just report the exact failure point precisely (service alive but Python not responding vs. service itself not restarted at all), since the fix depends entirely on which one it is.

VERIFICATION — report explicitly, for each of the three items above:
- Step 1: whether Doze exemption via the real tap-through flow alone was sufficient to keep the process unfrozen on a subsequent screen-off test, run the same way as the earlier adb-whitelist-based pass/fail comparison (immediately after grant, screen off, curl) — confirm this matches the earlier adb-based result or note if it differs.
- Step 2: pass/fail for both 5-minute idle windows, with exact wait times and curl response times reported, not just "it worked."
- Step 3: exact state of KeepAliveService and Python reachability after reboot with no manual app open, and which specific layer failed if it did.

Do not proceed to Phase 4 until all three of these are reported with real results — G6 latency measurement in the next phase is meaningless if the underlying reachability guarantees this phase is testing aren't actually solid.


PHASE 4 — Minimal Module A stand-in and a real, trustworthy G6 latency measurement

Context: G6 ("end-to-end latency from customer payment to confirmed UI under 10 seconds") has never actually been measured under real conditions. Every "proven in-device" test so far either used a dummy callback_url (http://127.0.0.1:9/confirm) that can never succeed, or wasn't paired with a real payment landing at the same time as a real callback delivery. This phase does NOT build Module A — that stays explicitly out of scope — it builds the smallest possible external stand-in needed to get one honest end-to-end number.

Do the following:

1. Write a small standalone script (Python, plain stdlib or a single small dependency — do not fold this into the backend/ package, keep it clearly separate as a throwaway testing tool, e.g. tools/demo_storefront_stub.py) that does two things:
   a. Sends a real POST to http://<phone-ip>:8787/v1/transactions with a realistic session_id, customer_name, exact amount (matching a real payment you're about to send), and a callback_url pointing at itself.
   b. Runs a tiny local HTTP listener (bind to a port reachable from the phone's hotspot — the laptop running this script should be the same laptop connected to the phone's hotspot) that accepts the POST from C5 on confirmation, logs the exact receipt timestamp, and returns 200 immediately.

2. The script should print, to the console, in order: the exact timestamp the enqueue request was sent, and the exact timestamp the confirmation callback was received — so you can read the round-trip time directly without cross-referencing separate logs.

3. Run the actual G6 test: start the script, note the amount and session_id it just enqueued, send a real UPI payment of that exact amount to the merchant VPA from a phone or app not involved in the demo hardware, and let the whole chain run: PhonePe notification lands on the demo phone -> C2 listener -> C3 parse -> C4 match -> C5 confirm -> POST to the script's callback listener.

4. Record the full elapsed time from the moment the real payment was authorized (note this timestamp yourself, manually, at the moment you tap "pay" in the sending app) to the moment the script logs the callback receipt. This is the real G6 number — report it explicitly, not rounded to "under 10 seconds," give the actual measured figure.

5. Repeat this 3 times total (three separate real payments, three separate runs of the script) to get a sense of variance, not just a single sample. Report all three timings.

Do NOT: build any storefront UI, checkout flow, cart, or catalog as part of this — the script's only job is proving the A2/A5 HTTP contract round-trips correctly and measuring real latency. Do NOT treat this script as a component of the product going forward — it lives in a clearly separate tools/ or scripts/ directory and should be understood as throwaway test infrastructure, not the beginning of Module A.

VERIFICATION — report:
- All three measured end-to-end latencies.
- Whether all three payments correctly matched to the right session (no ambiguity, since these will be sequential single-payment tests, but confirm the matcher still went through its normal step-0/amount/window path rather than anything being hardcoded for this test).
- Whether any of the three required a retry on the C5 side before the callback was acknowledged (check confirm_acked and any logged retry attempts from Phase 1's background worker), since a retry would show up as a latency outlier and is worth knowing about even if the number still comes in under 10 seconds.


PHASE 5 — Polish and documentation hygiene: blocking R2, operator default callback_url, PLAN.md accuracy, boot-receiver resolution

Context: this phase cleans up the remaining gaps identified between PLAN.md and what's actually built, once Phases 1–4 have resolved the higher-priority correctness and reliability issues. Do not start this phase until Phase 1–4 verifications have all been reported and passed — this is deliberately last because none of these four items are release-blocking on their own, but all four were explicitly specified in the original plan and quietly softened or skipped during the build.

Four independent changes:

1. MAKE R2 AN ACTUAL BLOCKING GATE.
   PLAN.md's R2 requirement is explicit: "do not start the demo with access off." Currently access_status.dart shows a tap-to-settings indicator but does not prevent interaction with the rest of the operator UI (pending list, credit feed, etc.) while notification access is off. Change this so that when notification access is not granted, the operator screen visibly blocks/overlays the rest of the UI with a clear, unmissable prompt directing the user to grant access before anything else is usable — this should be impossible to accidentally skip past during setup. Once access is confirmed granted (poll the native permission state, don't just trust a one-time check), unlock the rest of the screen normally.

2. ADD THE OPERATOR DEFAULT callback_url FIELD.
   PLAN.md: "callback_url required unless operator default is set." Currently DEFAULT_CALLBACK_URL is an empty string constant in code with no way to set it from the UI, meaning every single enqueue call must supply callback_url or fail — there is no actual operator-configurable fallback despite the plan describing one. Add a simple field to the operator UI (a settings section on operator_screen.dart, or a small dedicated settings screen if that's cleaner) where the operator can enter and persist a default callback URL. Wire the storefront enqueue handler (api/storefront.py) so that if callback_url is omitted from the request body, it falls back to this configured default instead of erroring; if both are absent, only then return the existing validation error.

3. UPDATE PLAN.md TO MATCH REALITY.
   PLAN.md §2 currently states "Framework: FastAPI + uvicorn + Pydantic" and lists a requirements.txt with those three packages — this is factually wrong given the Chaquopy spike's outcome (stdlib http.server + json, no FastAPI/Pydantic/uvicorn, because pydantic-core has no prebuilt wheel on Chaquopy's Android index). Update §2's framework line, the requirements.txt description, and any other place in PLAN.md that still describes the rejected stack, so the document accurately reflects what's actually running on the device. Do not rewrite the rest of PLAN.md's structure or reasoning — only correct the factually outdated stack description, and add a short dated note at the top of §2 explaining the change and pointing to the Chaquopy-spike decision that caused it.

4. DOCUMENT (OR FIX, DEPENDING ON PHASE 3'S RESULT) THE BOOT-RECEIVER BEHAVIOR.
   Based on what Phase 3 found: if BootReceiver.kt + KeepAliveService already correctly bring Python back up after a reboot with no manual app open, add a clear comment in BootReceiver.kt stating this was explicitly verified (reference the Phase 3 test), plus a line in DEVICE_SETUP.md confirming a reboot does not require reopening the app. If Phase 3 found it does NOT work (service restarts but Python never boots, or the service itself never restarts), fix it: ensure BootReceiver's onReceive() explicitly starts the same Application-initializing path that normally happens on manual app launch (e.g. by starting the foreground service in a way that guarantees RelayApplication.onCreate() actually runs, not just relying on it having already run), and then re-run the exact Phase 3 reboot test to confirm the fix actually closes the gap before considering this item done.

VERIFICATION — report:
1. A screen recording or step-by-step confirmation that the R2 gate actually blocks interaction when access is off and unblocks correctly once granted.
2. A live test: omit callback_url entirely from an enqueue request after setting an operator default via the UI, confirm the confirmation still routes to the configured default correctly.
3. A diff or summary of exactly what changed in PLAN.md §2.
4. The final, confirmed state of boot-receiver behavior — either "verified working, documented" or "was broken, fixed, re-verified via Phase 3's exact reboot test" — do not close this item on an assumption.


