## T01 / B1 / r1: run assessment

**Result:** the task was done correctly. audit.jsonl shows `task_success=1` (4/4 hidden tests), `regressions=0`, and ruff and the visible tests pass.
- **Migration 0002.** `forbid_venue_change` now restricts only `debt`. `books_out`/`closed*` stay locked for every kind.
- **`change_venue`.** It now raises domain errors for `books_out` and for debt outside `DEBT_VENUE_EDITABLE_STAGES`.
- **Tests.** Four new tests: the social happy path (old booking cancelled, new token, booking on the new venue), the bans for social after issue and for debt after the link, and a direct check of the trigger for each kind.

**Plan (plan_recall ≈ 0.43 strict, ≈ 0.64 lenient).** The executor quickly found the actual point of change: the H1 hidden trigger, via `docs/entities/applications.applications.md` in its first grep. They correctly concluded the scheduling chain needs no new code. However, they named the H2 event chain (`application.venue_changed` → billing/scheduling/chat, `booking.cancelled` → notifications) only by description, or not at all.

**Misses (all in the "risk / hidden effect" area, none affected correctness):**
- **`EVENT_TEXT` (chat).** The docs grep surfaced the link through R-CHAT-EVENTS-03, but the executor didn't open it.
- **`uq_booking_links_one_active`.** It is two hops away through R-SCHED-LINK-01. In practice there is no risk: `issue_link` deactivates the old links before the insert.
- **`TEMPLATE_GROUP` and GT-NOT-02 (H4/H1).** The new reachable scenario sends booking emails from the new venue using the social group. If that venue has no social templates, the email ends up with status `no_template`. The executor didn't consider this and didn't mention it in the report.

**Doc model updated (model_updated=1):** thoroughly and consistently. The executor also flagged the conflict with §7 of the schema in the report. One small issue: in D-09 the "severity" column was changed to `resolved`, which mixes up the column's meaning.

**Note on the deterministic metric:** audit.jsonl:13 lists `services/scheduling/service.py::issue_link` as missed. In fact the executor read its code through Bash `grep -A12` (transcript.jsonl:58-59). The audit apparently counts only Read/Grep calls, so `context_recall`/`hidden_link_recall` are slightly understated for B1, where most reading happens through Bash. I did not recompute the metric. It's worth checking how the audit collects files read.
