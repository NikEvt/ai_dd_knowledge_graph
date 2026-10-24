## T04 / variant S / repeat 2: score

**Result:** a correct, minimal fix.
- **Code:** in `dedup.py`, `_same_track` and its check are removed. `on_review_passed` now handles `kind in ("debt", "social")`.
- **Tests:** 5 new tests in `tests/test_dedup.py`.
- **Deterministic checks (from audit):** task_success=1, regressions=0, change_recall=1.0.
- **Not done:** the executor did not run the new tests against the old code, because that `git stash` command was not approved (transcript:121).

**Context:**
- **What the pack did well:** `impact(R-APP-DEDUP-01)` led straight to the right places: `_same_track`, `on_review_passed`, `approve`, `application.review_passed`.
- **Precision is low (~0.41):** the pack spends about 60% of its budget on archiving, refunds and payments.
- **The pack hit its budget limit:** it came back at 3982 of 4000 tokens. This is the likely reason that `reset_bookings` and `cancel_invoice` are missing; they are the next hop after `on_closed_duplicate`.
- **Mismatch to check (low confidence):** the `nodes_returned` list in mcp.jsonl:2 does not include `billing/scheduling::on_closed_duplicate`, but audit counts them as found. They may be in the response text but not in that list. Worth checking in the audit collector.

**Executor behaviour:**
- It did not read the `billing` and `scheduling` consumers. The downstream effects of `closed_duplicate` on a social winner are covered only indirectly, by an invoice-cancellation assertion. Booking resets are not checked.
- It honestly flagged a remaining risk, `awaiting_issue` in `OPEN_STAGES`, and correctly noted that no migrations are needed.

**Knowledge model:** updated thoroughly. A side effect is that the hash of `on_fully_paid` changed (its code was not touched), which moved R-APP-PAY-03 and R-BILL-PROCESS-01 to `suspect` for no real reason. That is drift noise from the hashing method, not an executor mistake.
