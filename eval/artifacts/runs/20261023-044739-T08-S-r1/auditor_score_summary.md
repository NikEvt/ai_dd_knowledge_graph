
## T08 (control task, variant S, r1): score

**Result:** the task was done correctly and with minimal changes. task_success=1, regressions=0, ruff_pass=1 (deterministic metrics from audit.jsonl, not recomputed). The diff changes exactly the 4 reference nodes, MessageIn, MessageOut, _out and tests/test_chat_api.py. The rest of the diff is regenerated knowledge-model and docs artifacts. No migration was created, which is correct.

**LLM metrics**
| metric | value | comment |
|---|---|---|
| impact_precision | 1.0 | Only because the pack held one node. find_entry was noisy (≈1–2 relevant out of 8). |
| plan_recall | 0.75 (low confidence) | The plan was a single line. _out is not named in it. |
| model_updated | 1 | discrepancy edited by hand, plus drift, rebuild and docs regeneration. |

**miss_reason:** no lines. All 4 reference nodes were in the MCP output or in files the executor read whole: services/chat/api.py (transcript.jsonl:9–11) and tests/test_chat_api.py (transcript.jsonl:20–21).

**Why pack_recall=0.25 (diagnosis, not a miss):** impact from MessageIn returned only the node itself. In code.json, MessageIn and MessageOut have only a `part_of → service:chat` edge (code.json:2019–2025). The extractor does not create edges for type usage: the parameter annotation `body: MessageIn` in `post`, the return type `-> MessageOut`, and the construction `MessageOut(...)` inside `_out`. So the graph has no path MessageIn → post → _out → MessageOut, and no path to the test that tests_by uses through the route. This is a **no_edge** class problem in the model. It is worth adding edges for Pydantic types in route signatures and for constructor calls.

**Executor behaviour:** the executor ran grep on `body` before using MCP and relied mainly on direct reading (transcript.jsonl:6, 12). For a local task like this, that is enough. It checked that `body` has no other HTTP consumers (notifications is a different entity). It added the negative assertion `"body" not in r.json()[-1]` and warned that the API change breaks clients. There were 2 permission denials (sed -i, awk); both were worked around without harming the result.
