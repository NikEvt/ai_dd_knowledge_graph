## T04 / B1 / r1: duplicates between social and paid applications

**Result:** the task was done correctly and with little code. All hidden tests passed (3/3), as did the visible tests and ruff, with no regressions (audit.jsonl:17-20).

**What changed**
- Removed `_same_track` and its check in `close_duplicates`.
- `on_review_passed` now also handles `kind=social`.
- Added 6 tests in `tests/test_dedup.py`: social against paid/debt/social, debt against social, full payment against social, and other sphere or other client.

**Context:** context_recall=0.9 and hidden_link_recall=0.857 came from grep over the generated `docs/`. The only hidden link missed was `scheduling/service.py::reset_bookings`. It is one hop beyond `scheduling/consumers.py::on_closed_duplicate`, and the docs do not mention it. impact_precision cannot be measured: B1 has no pack or MCP.

**Plan (plan_recall≈0.3):** the plan before editing is a single sentence naming only the rule and the two files. The event chain (`application.closed_duplicate` → billing/scheduling, `approve` → `review_passed`) was in the grep output, but the executor never named it. Behaviour was checked with integration tests instead.

**Documentation (model_updated=1):** docs/ was updated meaningfully, including R-APP-DEDUP-01, D-21, D-01, coverage and line references. There is a minor inconsistency in coverage.md. The executor rightly flagged that `knowledge/` and the generator are missing, so the hand edits will be overwritten the next time docs are generated.

**Worth noting**
- The executor flagged the unresolved D-01 risk: `OPEN_STAGES` includes `awaiting_issue`, so it now applies to social applications too.
- The executor made its own call that two social applications are also duplicates of each other. This goes beyond the old GT-DUP-04 behaviour, but it matches the task wording.
