## T01 / variant S / repeat 2: the run succeeded with a narrow plan

**Result:**
- **Deterministic metrics (taken from audit.jsonl):**
  - all 4 hidden tests pass, no regressions;
  - ruff is clean;
  - change_recall = 1.0;
  - context_recall = 0.857;
  - hidden_link_recall = 0.833 (H1 0.667, H2 0.875, H4 1.0).
- **The fix is correct:**
  - migration `0002_social_venue_change.py` takes `social` out of the "after booking link" lock in `forbid_venue_change`;
  - the lock for everyone on `books_out`/`closed*` stays, and so does the lock for `debt`;
  - `change_venue` gained matching DomainError checks (`diff.patch:2514-2517`);
  - 3 tests were added, including the scenario where the booking is cancelled and a new link is issued (`diff.patch:2580`).

**LLM metrics:**

| metric | value | comment |
|---|---|---|
| impact_precision | 0.54 | about half the pack is the unarchive, refund and duplicate branches, which are irrelevant to the task |
| plan_recall | 0.43 | no explicit plan; the event chain (venue_changed → scheduling/billing/chat → booking.cancelled → notifications) is described only in general terms, without nodes |
| model_updated | 1 | rules R-APP-VENUE-CHANGE-02 and R-SCHED-VENUE-CHANGE-01 were rewritten, the model and docs were rebuilt; D-09 was left for a human |

**Misses in context delivery:**
- **`on_booking_cancelled` (H2): depth_cutoff.** The chain to the cancellation-email subscriber is longer than depth 4, and 154 nodes were cut by the budget.
- **`uq_booking_links_one_active` (H1): depth_cutoff, low confidence.** It is reachable only through `issue_link`, which the executor did not expand.
- **GT-NOT-02 (risk): no_edge.** The model has no edge from venue change to the social templates at the new venue.

**Recommendations for the knowledge model:**
1. Treat `booking.cancelled` and its subscribers as a mandatory continuation of `reset_bookings` without spending depth on it.
2. Add an edge from venue change to the notification templates for (venue, kind_group).
3. Lower the weight of the unarchive branch in an impact query from R-APP-VENUE-CHANGE-02.
