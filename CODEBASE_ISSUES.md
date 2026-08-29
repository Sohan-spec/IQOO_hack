# Codebase issues — scan findings (agent-first)

Scope: **code and functionality issues in the current tree only.** Not product/design
concerns — the workflow in `context.md` is fixed and out of scope. Findings are scoped to
what is actually committed today, independent of `phases.md` (which is a *plan*, not a record
of what shipped).

**How to use this file (you are the agent that acts on it):**
1. Reproduce each issue with the "Verify it's real" command/step *before* changing anything.
   Some findings are confirmed-reproduced (marked ✅ REPRODUCED); others are analysis and may
   turn out benign on inspection (marked 🔍 ANALYSIS) — do not change code for those until you
   confirm the failure mode.
2. Apply the fix, then run the stated verification.
3. Do not touch the locking/confirm-decoupling semantics unless a finding says to — Phase 1's
   background C5 worker (`ConfirmationSender.submit`) is already correctly non-blocking and is
   called from both the auto-match and R1 manual paths. Leave it alone.

Environment note: the backend runs on Chaquopy (CPython, UTF-8 locale) on Android; tests and
`tools/` run on a dev/CI/demo **laptop** which may be **Windows (cp1252)**. Several findings are
latent only off-device — they still break CI and any Windows laptop, so they count.

---

## P1 — `test_parser.py` reads the fixture without an explicit encoding ✅ REPRODUCED

- **Where:** `backend/tests/test_parser.py:12` — `rows = json.loads(FIXTURES.read_text())`
- **What happens:** `Path.read_text()` uses the platform default encoding. On Windows that is
  `cp1252`, so the UTF-8 `₹` (bytes `E2 82 B9`) in `phonepe_credits.json` decodes to the mojibake
  `â‚¹`. `parse_credit` then finds no `₹`/`Rs`/`INR` amount token and returns `None`, failing the
  `credit_rupee` row.
- **Verify it's real:**
  ```
  cd backend && python -m pytest tests/test_parser.py -q
  ```
  Fails on Windows with `AssertionError: credit_rupee` / `assert None is not None`.
  (`parse_credit` itself is correct — calling it with a real UTF-8 `₹` string returns
  `(Decimal('1.00'), 'JOHN DOE')`. The bug is the file read, not the parser.)
- **Fix:** add the encoding:
  ```python
  rows = json.loads(FIXTURES.read_text(encoding="utf-8"))
  ```
- **Verify fixed:** `python -m pytest tests/test_parser.py -q` passes on Windows.
- **Also sweep:** `test_parser.py:12` is the only `read_text()`/`open()` in `backend/` + `tools/`
  missing an explicit `encoding=`. If you add any fixture/file reads, pass `encoding="utf-8"`.

---

## P2 — `demo_storefront_stub.py` prints `→` (U+2192), crashing on a Windows console/pipe ✅ REPRODUCED

- **Where:** `tools/demo_storefront_stub.py` — `G6_NOTE` (lines 26–29) and the module docstring
  (line 7) contain the `→` arrow. `G6_NOTE` is printed to stdout via `print_callback()` (line 167)
  and embedded in the argparse `epilog` (line 192), so it is emitted on both a normal run and
  `--help`.
- **What happens:** `→` (U+2192) is not representable in `cp1252`. When stdout is a pipe (e.g.
  `subprocess`/CI) or a cp1252 console, printing raises `UnicodeEncodeError`, the script dies with
  a traceback, and exits non-zero. This is not test-only: **running the stub on a Windows demo
  laptop crashes at the moment it prints the callback timing** — the exact number the tool exists
  to report.
- **Verify it's real:**
  ```
  cd backend && python -m pytest tests/test_demo_storefront_stub.py::test_cli_help_subprocess -q
  ```
  Fails: `CalledProcessError ... --help ... returned non-zero exit status 1`.
- **Fix (pick one; ASCII is simplest and matches a throwaway tool):**
  - Replace the two `→` in `G6_NOTE` and the docstring arrow with `->`.
  - *Or*, if you want to keep the glyph, force UTF-8 stdout at startup in `main()`:
    `sys.stdout.reconfigure(encoding="utf-8")` (Python 3.7+) — but ASCII is preferred here.
- **Verify fixed:** the pytest above passes; `python tools/demo_storefront_stub.py --help` prints
  and exits 0 on Windows.
- **Leave alone:** the `→` in `backend/app/matcher.py:8` and `backend/app/state.py:1` are inside
  docstrings that are never printed to stdout — harmless, do not churn them.

---

## P3 — Operator default callback URL is never re-synced to Python after a Python restart 🔍 ANALYSIS

- **Where:** `owner_app/lib/ui/operator_screen.dart:51-65` (`_pushDefaultCallbackUrl`, guarded by
  the one-shot `_callbackPushed` latch) vs. `backend/app/runtime.py:39`
  (`self.default_callback_url` is in-memory only) and `backend/app/config.py:7`
  (`DEFAULT_CALLBACK_URL = ""`).
- **What happens:** The native side persists the default URL in SharedPreferences
  (`MainActivity.kt:111-118`), but Python holds it only in `Runtime` memory. Flutter pushes it to
  Python once, then sets `_callbackPushed = true` and never pushes again (the guard returns early
  on every subsequent 500 ms `_refresh`). If the Chaquopy/Python process restarts — which is
  exactly the reboot/Doze scenario the reliability work targets — Python comes back with an empty
  default, and Flutter never re-pushes it. Any storefront enqueue that omits `callback_url` then
  fails with `400 "callback_url is required"` (`api/storefront.py:31-32`) until the operator
  manually re-saves in the UI.
- **Verify it's real:**
  1. Start backend, set a default via the UI (or `POST /v1/internal/settings`).
  2. `POST /v1/transactions` with no `callback_url` → succeeds (201).
  3. Restart the Python backend process (fresh `Runtime`).
  4. Without re-saving in the UI, `POST /v1/transactions` with no `callback_url` → **400**, and the
     running Flutter app does not repair it because `_callbackPushed` is still `true`.
- **Fix (choose the smaller one that closes the gap):**
  - Preferred: make the re-push resilient instead of one-shot. Re-push the persisted default
    whenever a snapshot comes back showing `default_callback_url` empty/different from the device
    value. Concretely, in `_refresh`, after a successful `snapshot()`, if
    `snapshot.defaultCallbackUrl` (add it to the `Snapshot` model — the backend already returns it
    at `runtime.py:166`) differs from the device value, call `setDefaultCallbackUrl` again. Drop or
    relax the `_callbackPushed` latch so a restarted Python is re-synced.
  - Note: `Snapshot.fromJson` in `python_client.dart` currently drops `default_callback_url`; add
    it to the model if you take the preferred fix.
- **Verify fixed:** repeat the repro; after step 3 the app re-syncs within one poll cycle and step
  4 succeeds without a manual save.

---

## P4 — Cross-thread read/write of `entry.confirm_acked` without synchronization 🔍 ANALYSIS (low)

- **Where:** written on the confirm worker thread at `backend/app/confirm.py:126`
  (`entry.confirm_acked = True`); read on the asyncio-loop thread at
  `backend/app/runtime.py:177` inside `snapshot()` / `_recent_match_dict`.
- **What happens:** the same `PendingEntry` object is shared between the delivery worker thread and
  the request/loop thread with no lock. For a single boolean attribute under CPython's GIL this is
  effectively atomic, so today it is benign — but it is undocumented shared mutable state and will
  bite if the field ever becomes non-atomic (e.g. a dict of retry metadata).
- **Verify it's real:** inspection only — there is no reliable failing test for a torn bool read
  under the GIL. Do **not** invent a flaky timing test.
- **Fix (minimal):** add a one-line comment at both sites noting the field is written by the
  confirm worker and read by the loop, and that only atomic-attribute writes are allowed here. No
  behavioral change needed unless the field's shape grows.

---

## P5 — Parser regexes and the Kotlin extractor are unvalidated against real notifications 🔍 ANALYSIS

- **Where:** `backend/app/parser.py` (module docstring lines 4-6 explicitly say the regexes and
  `fixtures/phonepe_credits.json` are placeholders, not captured from the device) and
  `owner_app/.../RelayNotificationListener.kt:15-17` (reads only `EXTRA_TITLE` + `EXTRA_TEXT`).
- **What happens:** every green parser/matcher test only proves internal consistency with invented
  strings. If PhonePe's real credit notification uses a format the regexes don't cover (e.g. amount
  in `EXTRA_BIG_TEXT`/sub-text rather than `EXTRA_TEXT`, `Rs.` with no space, payer after `by`
  instead of `from`, or a credit signalled without the word "received"), `parse_credit` silently
  returns `None` and no credit is ever matched.
- **This overlaps Phase 2 of `phases.md`** and requires physical device capture, so it may be out
  of scope for a pure code pass. Flagging it so it is not mistaken for "verified working."
- **Verify it's real:** requires a real PhonePe credit on the demo device; capture the exact
  `package/title/text` (the listener already logs raw at `RelayNotificationListener.kt:19`, and
  `POST /v1/internal/notifications` records it), then diff against `_AMOUNT`/`_FROM`/`_CREDIT`/
  `_DEBIT`. Do not "fix" the regexes against guessed strings.
- **Fix:** none in code until real strings exist — this is a capture task, not an edit task. If you
  are only doing a code pass, leave parser.py untouched and note it remains unverified.

---

## P6 — Minor correctness/robustness notes 🔍 ANALYSIS (low; batch or skip)

Small items; fix only if cheap and clearly safe, otherwise record and move on.

- **Zero-amount matches allowed.** `parse_amount` accepts `amount >= 0` (`models.py:25`), so a
  `0.00` enqueue/credit is matchable. If a ₹0 payment is never valid, consider rejecting `<= 0` in
  `parse_amount` — but confirm this doesn't break any test that enqueues `0`.
- **`session_id` not URL-decoded on the confirm route.** `main.py:118` slices the raw path segment;
  `python_client.dart:47` builds the URL without percent-encoding. Opaque generated ids are fine
  today, but a `session_id` containing `/` or reserved chars would mis-route the R1 confirm. Low
  risk given id generation; note only.
- **`TransactionQueue._entries` never evicts.** `queue.py` keeps confirmed/expired entries forever;
  memory grows over a long-lived process. This is currently *load-bearing* — `_recent_match_dict`
  relies on the entry still being present to report live `confirm_acked` (`runtime.py:174-180`). Do
  not add eviction without also preserving the live-ack lookup. Note as a deliberate trade-off, not
  a bug to fix blindly.

---

## Confirmed NOT broken (do not re-open)

- **Phase 1 background C5 delivery** is implemented correctly: `ConfirmationSender.submit()`
  enqueues onto a daemon worker and returns immediately; both `runtime._match_and_confirm` and
  `runtime.manual_confirm` call it after the atomic `mark_confirmed` inside the queue lock. R1/
  ingest no longer block on delivery. `snapshot()` surfaces `recent_matches` with live
  `confirm_acked`/`status`/`via`/`matched_at`. Backoff (0.5/1/2/4s), 2xx-only ack, no revert to
  pending, and exhausted-retry logging are all present and covered by `test_confirm.py`.
- **`requirements.txt`** already reflects the stdlib-only stack (no FastAPI/Pydantic/uvicorn).
- **R2 access gate** (`AccessGate` in `access_status.dart`) and the **operator default-callback UI**
  (`operator_screen.dart` ExpansionTile) both exist. (Their runtime-sync weakness is P3, not their
  absence.)

---

## Suggested order of work

1. **P1**, **P2** — confirmed-broken, one-line fixes, restore a green test suite (currently
   `2 failed, 33 passed`).
2. **P3** — real device-runtime functionality gap; highest-impact behavioral bug.
3. **P4**, **P6** — cheap hardening / comments.
4. **P5** — capture task, likely defer to the Phase 2 device session.
