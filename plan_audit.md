# Plan audit — backend vs `phases.md`

Date: 2026-08-30  
Scope: `backend/app/**`, `backend/tests/**`, `tools/demo_storefront_stub.py` compared to `phases.md` and the PLAN.md HTTP/C3–C5/R1/R5 contract.  
Not in scope as backend work: Flutter UI, Kotlin `BootReceiver`, live iQOO capture.

Legend: **DONE** = present in code with a test or an explicit contract check. **MISSING** = required by phases/PLAN and not in Python. **DEVICE** = cannot be closed without the demo phone.

---

## 1. Phase 1 — C5 retry decoupling + snapshot `confirm_acked`

`phases.md` lines 1–25: two required changes.

### 1.1 Decouple confirm-send from the triggering request

| Spec | Code | Verdict |
|---|---|---|
| Atomic pending → confirmed stays inside the queue lock | `runtime.py` `_match_and_confirm` 103–116 and `manual_confirm` 129–137: `async with self.queue.lock` then `mark_confirmed` | **DONE** |
| Do not change Change 3 lock semantics / `test_race.py` | `tests/test_race.py` still asserts exactly one winner and one C5 POST | **DONE** |
| Hand off outbound POST (full backoff) to a background worker; handler must not wait | `confirm.py` `ConfirmationSender.submit` 84–91: increment jobs, start daemon `relay-confirm`, `put` and return | **DONE** |
| HTTP response immediately after (a): `status: "confirmed"`, `confirm_acked: false` | `api/internal.py` `manual_confirm` 62–66 returns those fields; `test_phase1_http.py` asserts elapsed < 1.0s and `confirm_acked is False` | **DONE** |
| Backoff 0.5 / 1 / 2 / 4 s | `config.py` `CONFIRM_BACKOFF_SECONDS = (0.5, 1.0, 2.0, 4.0)`; `_deliver` iterates `(0.0, *CONFIRM_BACKOFF_SECONDS)` | **DONE** |
| `confirm_acked = True` only on 2xx | `_post_json_with_reason` 58–60; `_deliver` 125–128 | **DONE** |
| Status stays CONFIRMED on delivery failure; never revert to pending | `state.py` `mark_confirmed` is one-way; `_deliver` does not touch `status` | **DONE** |
| Exhausted retries: structured log with `session_id` and reason | `confirm.py` 131–135 `logger.warning("confirm delivery failed session_id=%s reason=%s", ...)` | **DONE** |

### 1.2 Restore `confirm_acked` and recent-match visibility on snapshot

| Spec | Code | Verdict |
|---|---|---|
| `pending`: currently PENDING only | `runtime.snapshot` 155–160 | **DONE** |
| `recent_matches`: last N confirmed/matched entries | `events.py` deque `maxlen=EVENT_LOG_SIZE`; snapshot maps via `_recent_match_dict` | **DONE** |
| Each match: `session_id`, `status`, `confirm_acked`, `matched_at`, `via` (`"auto"` \| `"manual"`) | `_recent_match_dict` 173–185: `via` from source, `matched_at` = `at`, live `status`/`confirm_acked` from queue entry | **DONE** |
| N = existing ring size, “currently 100” | `config.py` `EVENT_LOG_SIZE = 100` (was 50 before this scan; Phase 1 text asked for 100) | **DONE** |
| `recent_credits` unchanged | snapshot key `recent_credits` from `events.credits` | **DONE** |
| Do not change matcher step 0 | `matcher.py` 33–34 `candidates = [entry for entry in entries if entry.status == PENDING]` | **DONE** |

Phase 1 backend: **complete**.

---

## 2. Phase 2 — Real PhonePe capture + regex freeze

`phases.md` (R3): do not freeze regexes until strings are captured from the actual demo PhonePe build.

| Spec | Code | Verdict |
|---|---|---|
| Fixture-driven parser tests | `tests/test_parser.py` reads `app/fixtures/phonepe_credits.json` with `encoding="utf-8"` | **DONE** (placeholders) |
| Replay path `POST /v1/internal/notifications` | `main.py` 129–131 → `internal.ingest_notification` | **DONE** |
| Raw capture on snapshot for debrief | `recent_raw_notifications` in snapshot; ingest always `add_raw_notification` before parse | **DONE** |
| Capture real `package/title/text` from demo iQOO | `parser.py` 3–5: “R3 capture from the demo iQOO is still pending. Regexes and fixtures are placeholders” | **DEVICE / MISSING** |
| Freeze `_AMOUNT` / `_FROM` / `_CREDIT` / `_DEBIT` against captured strings | Same; do not edit regexes against guessed strings (`CODEBASE_ISSUES.md` P5) | **DEVICE / MISSING** |

Phase 2: **blocked on device**. Software surface for replay/logging is present.

---

## 3. Phase 3 — Fresh install, idle, boot-receiver

`phases.md` items are APK install, 5-minute idle with screen off, reboot without reopening the app.

No Python module implements this. `main.py` `start()` binds HTTP; Android `RelayApplication` / `BootReceiver` / `KeepAliveService` own process lifetime.

Phase 3: **DEVICE**. Not a backend gap.

---

## 4. Phase 4 — G6 / `demo_storefront_stub.py`

| Spec | Code | Verdict |
|---|---|---|
| Throwaway A2 enqueue + A5 callback listener | `tools/demo_storefront_stub.py` | **DONE** |
| Does not special-case matcher / session ids | `tests/test_demo_storefront_stub.py` `test_matcher_not_hardcoded_for_stub` | **DONE** |
| Uses R1 + Phase 1 background C5 (does not wait inline) | stub test comments + `wait_for_callback` after R1 | **DONE** |
| ASCII-safe on Windows (no `→`) | stub `G6_NOTE` is ASCII; `test_cli_help_subprocess` | **DONE** |
| Three live PhonePe payments, record enqueue→callback times | Requires owner phone + customer UPI | **DEVICE / MISSING** |

Phase 4 software: **complete**. Live G6 numbers: **missing**.
---

## 5. Phase 5 — Operator default `callback_url`, PLAN.md, boot docs

| Spec | Code | Verdict |
|---|---|---|
| Enqueue: omit `callback_url` → operator default; both absent → 400 | `storefront.py` 32–35; `runtime.enqueue` uses `(callback_url or self.default_callback_url)` | **DONE** |
| Set default via HTTP | `POST /v1/internal/settings` `update_settings`; snapshot returns `default_callback_url` | **DONE** |
| Persist default across Python process restart | Python holds it in `Runtime` memory only (`runtime.py` 39). Flutter SharedPreferences re-push is owner_app (`CODEBASE_ISSUES.md` P3) | **MISSING in Python by design**; Flutter gap |
| PLAN.md §2 stack = stdlib `http.server` + json, not FastAPI | `PLAN.md` spike outcome; `requirements.txt` has no FastAPI/Pydantic/uvicorn | **DONE** (docs, pre-existing) |
| R2 blocking access overlay | Flutter `access_status.dart` | **not backend** |
| BootReceiver documented or fixed | Kotlin + `DEVICE_SETUP.md` | **not backend** |

Phase 5 backend contract: **done**. Operator UI / boot: **out of this scan**.

---

## 6. PLAN.md HTTP contract (backend)

Routes in `main.py`:

| Route | Auth/bind | Verdict |
|---|---|---|
| `POST /v1/transactions` | LAN (`0.0.0.0:8787`) | **DONE** |
| `GET /v1/internal/snapshot` | loopback only (`is_loopback_client`) | **DONE** |
| `POST /v1/internal/notifications` | loopback | **DONE** |
| `POST /v1/internal/transactions/{session_id}/confirm` | loopback; path segment `unquote`d | **DONE** |
| `POST /v1/internal/settings` | loopback; not in original “no other public routes” list, added for Phase 5 default URL | extra internal route, loopback-gated |

Snapshot keys today: `pending`, `recent_credits`, `recent_raw_notifications`, `recent_matches`, `default_callback_url`, `server.bind`, `interruption_filter`.

PLAN.md Change 5: include interruption filter in GET `/v1/internal/snapshot` after native reports it. `Runtime.interruption_filter` defaults `None`; settings can set an int. Native Flutter still reads DND via MethodChannel (`dnd_status.dart`) and does not have to POST it for the operator widget to work. Backend field exists so a reporter can land it.

Enqueue: 201 `{session_id, status, created_at}`; 409 duplicate `session_id`; amount `Decimal` quantized 0.01, must be `> 0` (`models.parse_amount`).

C5 body: `{session_id, status: "confirmed"}` (`confirm.py` 119).

Matcher order: step 0 pending → amount → 5-minute window (`EXPIRY_SECONDS = 300`) → name if multiple → oldest. Sweeper: `_sweeper` every `SWEEP_INTERVAL_SECONDS = 1.0`.

---

## 7. `CODEBASE_ISSUES.md` vs tree

| ID | Claim | Current tree |
|---|---|---|
| P1 | `test_parser.py` `read_text()` missing encoding | **Fixed.** `encoding="utf-8"` at line 12 |
| P2 | stub prints `→`, crashes cp1252 | **Fixed.** ASCII `G6_NOTE` |
| P3 | Flutter one-shot default-callback push vs in-memory Python | **Still Flutter.** Backend cannot persist across process death without a file; none added |
| P4 | comments | Parser R3 placeholder comment present |
| P5 | real PhonePe strings unverified | **Still true.** Phase 2 |
| P6 zero amount | `parse_amount` allowed 0 | **Fixed.** `amount <= 0` raises |
| P6 session_id not URL-decoded | `main.py` sliced raw path | **Fixed.** `unquote(...)` at `main.py` 140 |
| P6 `_entries` never evicts | load-bearing for live `confirm_acked` | **Unchanged on purpose** (`queue.py` docstring) |

---

## 8. What this scan implemented (not in original tree)

1. `unquote` on R1 `session_id` (`main.py` 140).
2. Ingest `ValueError` (bad `posted_at`) mapped to HTTP 400 (`internal.py` 47–50).
3. Snapshot `interruption_filter`; settings accept it without requiring `default_callback_url`.
4. `EVENT_LOG_SIZE` 50 → 100.
5. `_RelayHTTPServer.allow_reuse_address = True`; `stop()` `server_close()`, cancel loop, clear `_runtime`.
6. Tests: URL-decoded confirm, invalid `posted_at`, DND on snapshot, `expire_due` stale-pending-only.
7. `backend/pyproject.toml` pytest `addopts` disable host plugins `web3` / `pytest_ethereum` / `langsmith_plugin` (they crash import on this Windows host).

---

## 9. Tests run during scan

Host: Windows, Python 3.12. Must use `-p no:web3 -p no:pytest_ethereum -p no:langsmith_plugin` (now default via `pyproject.toml`).

| Batch | Result |
|---|---|
| `test_parser`, `test_state`, `test_matcher`, `test_storefront` | 17 passed |
| `test_confirm`, `test_race`, `test_double_confirm`, `test_raw_capture` | 12 passed |
| `test_http` (incl. new URL-decode, posted_at, DND) | 7 passed |
| `test_demo_storefront_stub` + `test_r1_reachable_callback_flips_confirm_acked` | 5 passed |
| `test_r1_unreachable_callback_returns_quickly` | **not finished in this session** (waits `wait_idle(timeout=40)` for exhausted C5 retries; tool timeout/abort) |

Full suite in one process was not recorded green. Slow test is expected ~7.5s+ of backoff (0.5+1+2+4) plus connect timeouts, budgeted 40s.

---

## 10. Closed vs open

**Backend vs `phases.md` Phases 1, 4 (software), 5 (enqueue default):** closed.

**Open, not backend code:**

- Phase 2 live PhonePe capture and regex freeze
- Phase 3 install / idle / reboot
- Phase 4 three live G6 timings
- Phase 5 R2 overlay, BootReceiver; PLAN.md already corrected
- Flutter P3: re-push `default_callback_url` after Python restart

**Open, verification:**

- One-shot `pytest tests` including the 40s unreachable-callback test
- `CHANGELOG.md` was requested after tests; not written yet (this file is the audit only)

