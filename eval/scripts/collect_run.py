"""Детерминированные метрики прогона: collect_run.py RUN_DIR

Читает transcript.jsonl (stream-json Claude Code), mcp.jsonl, junit-*.xml, diff.patch и пишет строки
в RUN_DIR/audit.jsonl с "method": "deterministic". Клон проекта (meta.workdir) должен ещё существовать.

«Узел увиден» (seen) — исполнитель получил его в контексте: прочитал файл с символом, получил его
в выдаче MCP или в результате поиска. Сравнение идёт по не-правиловым узлам эталона
(code/config/db/event/bpm): ID правил модели знаний и эталона различаются.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import yaml

EVAL = Path(__file__).resolve().parents[1]
RUN_DIR = Path(sys.argv[1]).resolve()
meta = json.loads((RUN_DIR / "meta.json").read_text())
WT = Path(meta["workdir"])
task = yaml.safe_load((EVAL / "ground_truth" / "tasks" / f"{meta['task_id']}.yaml").read_text())
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MCP_CONTEXT_TOOLS = ("find_entry", "impact")
records: list[dict] = []


def emit(metric: str, value, phase: str, **extra) -> None:
    records.append(
        {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "run_id": meta["run_id"],
            "task_id": meta["task_id"],
            "variant": meta["variant"],
            "repeat": meta["repeat"],
            "worker_model": meta["worker_model"],
            "phase": phase,
            "metric": metric,
            "value": value,
            "method": "deterministic",
            **extra,
        }
    )


# --- транскрипт --------------------------------------------------------------------------
events = [
    json.loads(line) for line in (RUN_DIR / "transcript.jsonl").read_text().splitlines() if line.strip()
]
result = next((e for e in reversed(events) if e.get("type") == "result"), {})

seen_message_ids: set[str] = set()
tool_uses: dict[str, dict] = {}
order: list[tuple[str, dict]] = []  # ("use"|"result", payload) в порядке появления
tokens_before_edit = 0
first_edit_seen = False
for e in events:
    if e.get("type") == "assistant":
        msg = e["message"]
        if msg.get("id") not in seen_message_ids:
            seen_message_ids.add(msg.get("id"))
            u = msg.get("usage", {})
            total = (
                u.get("input_tokens", 0)
                + u.get("cache_read_input_tokens", 0)
                + u.get("cache_creation_input_tokens", 0)
                + u.get("output_tokens", 0)
            )
            if not first_edit_seen:
                tokens_before_edit += total
        for block in msg.get("content", []):
            if block.get("type") == "tool_use":
                tool_uses[block["id"]] = block
                order.append(("use", block))
                if block["name"] in EDIT_TOOLS:
                    first_edit_seen = True
    elif e.get("type") == "user":
        for block in e["message"].get("content", []) if isinstance(e["message"].get("content"), list) else []:
            if block.get("type") == "tool_result":
                order.append(("result", block))

usage = result.get("usage", {})
emit("cost_usd", result.get("total_cost_usd"), "cost")
emit("num_turns", result.get("num_turns"), "cost")
emit(
    "tokens_total",
    sum(
        usage.get(k, 0)
        for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
    ),
    "context",
)
emit("tokens_context", tokens_before_edit, "context")
emit("worker_error", int(bool(result.get("is_error"))), "result", detail=result.get("subtype"))
emit("permission_denials", len(result.get("permission_denials", [])), "discipline",
     tools=[d.get("tool_name") for d in result.get("permission_denials", [])])
emit("wall_seconds", json.loads((RUN_DIR / "timing.json").read_text())["wall_seconds"], "cost")


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


reads: list[tuple[str, str]] = []  # (относительный путь, текст результата)
search_text: list[str] = []
mcp_text: list[str] = []  # тексты ответов find_entry/impact
files_read_whole = 0
mcp_before_edit = 0
edit_started = False
scout_used = 0
for kind, block in order:
    if kind == "use":
        name = block["name"]
        if name in EDIT_TOOLS:
            edit_started = True
        if any(name.endswith(t) for t in MCP_CONTEXT_TOOLS) and name.startswith("mcp__") and not edit_started:
            mcp_before_edit += 1
        if name in ("Task", "Agent") and "scout" in json.dumps(block.get("input", {})):
            scout_used = 1
        if name == "Read":
            inp = block.get("input", {})
            path = Path(inp.get("file_path", ""))
            if "offset" not in inp and "limit" not in inp and path.exists():
                if sum(1 for _ in path.open(errors="ignore")) > 200:
                    files_read_whole += 1
        if name == "Bash" and re.search(r"(^|\s)cat\s", block.get("input", {}).get("command", "")):
            files_read_whole += 1
    else:
        use = tool_uses.get(block.get("tool_use_id"), {})
        text = result_text(block)
        if use.get("name") == "Read":
            fp = use.get("input", {}).get("file_path", "")
            try:
                rel = str(Path(fp).resolve().relative_to(WT.resolve()))
            except ValueError:
                rel = fp
            reads.append((rel, text))
        else:
            search_text.append(text)
            name = use.get("name", "")
            if name.startswith("mcp__") and any(name.endswith(t) for t in MCP_CONTEXT_TOOLS):
                mcp_text.append(text)

emit("files_read_whole", files_read_whole, "context")
emit("mcp_calls_before_edit", mcp_before_edit, "discipline")
emit("scout_used", scout_used, "discipline")

# --- MCP-лог ------------------------------------------------------------------------------
mcp_nodes: set[str] = set()
pack_tokens: list[int] = []
mcp_log = RUN_DIR / "mcp.jsonl"
if mcp_log.exists():
    for line in mcp_log.read_text().splitlines():
        call = json.loads(line)
        mcp_nodes.update(call.get("nodes_returned", []))
        if call.get("tool") == "impact":
            pack_tokens.append(call.get("response_tokens", 0))
emit("pack_tokens", max(pack_tokens) if pack_tokens else None, "context", calls=len(pack_tokens))


# --- увиденные и изменённые узлы ------------------------------------------------------------
def symbol_pattern(symbol: str) -> re.Pattern:
    return re.compile(rf"(def|class)\s+{re.escape(symbol)}\b|^\s*\d*\s*{re.escape(symbol)}\s*[:=]", re.M)


def short_ref(ref: str) -> str:
    file, _, symbol = ref.partition("::")
    return f"{Path(file).name}::{symbol}" if symbol else Path(file).name


def in_pack(node: dict) -> bool:
    # Полный ID в nodes_returned или короткое «файл::символ» в тексте ответа MCP
    # (решение пишет подписчиков других сервисов в текст без полного пути)
    ref = node["ref"]
    if ref in mcp_nodes:
        return True
    if node["kind"] in ("code", "config") and "::" in ref:
        return any(short_ref(ref) in t for t in mcp_text)
    return any(ref in t for t in mcp_text)


def node_seen(node: dict) -> bool:
    ref, kind = node["ref"], node["kind"]
    if in_pack(node):
        return True
    if kind in ("code", "config"):
        file, _, symbol = ref.partition("::")
        for rel, text in reads:
            if rel == file and (not symbol or symbol_pattern(symbol).search(text)):
                return True
        return any((file in t or short_ref(ref) in t) and (not symbol or symbol in t) for t in search_text)
    if kind == "db":
        name = ref.split(".")[-1]
        return any(name in t for _, t in reads) or any(name in t for t in search_text)
    if kind == "event":
        return any(f'"{ref}"' in t for _, t in reads) or any(ref in t for t in search_text)
    if kind == "bpm":
        src, _, dst = ref.partition("->")
        return any(rel.startswith("bpm/") and src in t and dst in t for rel, t in reads)
    return False


diff_text = (RUN_DIR / "diff.patch").read_text()
changed_files = set(re.findall(r"^\+\+\+ b/(.+)$", diff_text, re.M))


def node_changed(node: dict) -> bool:
    ref, kind = node["ref"], node["kind"]
    if kind in ("code", "config"):
        return ref.partition("::")[0] in changed_files
    if kind == "db":
        name = ref.split(".")[-1]
        return any(f.startswith("migrations/") for f in changed_files) and name in diff_text
    if kind == "bpm":
        return any(f.startswith("bpm/") for f in changed_files)
    return False


nodes = [n for n in task["expected_nodes"] if n["kind"] != "rule"]
hidden = [n for n in nodes if n.get("hidden")]
to_change = [n for n in nodes if n["role"] == "change"]
seen = [n["ref"] for n in nodes if node_seen(n)]
emit("context_recall", round(len(seen) / len(nodes), 3) if nodes else None, "context",
     expected=[n["ref"] for n in nodes], found=seen)
if hidden:
    hidden_seen = [n["ref"] for n in hidden if node_seen(n)]
    emit("hidden_link_recall", round(len(hidden_seen) / len(hidden), 3), "context",
         expected=[n["ref"] for n in hidden], found=hidden_seen,
         missed=[n["ref"] for n in hidden if n["ref"] not in hidden_seen])
    for cat in sorted({n["hidden"] for n in hidden}):
        group = [n for n in hidden if n["hidden"] == cat]
        emit("hidden_link_recall_by_category", round(sum(node_seen(n) for n in group) / len(group), 3),
             "context", hidden_category=cat)
if mcp_log.exists():
    packed = [n["ref"] for n in nodes if in_pack(n)]
    emit("pack_recall", round(len(packed) / len(nodes), 3) if nodes else None, "context", found=packed,
         missed=[n["ref"] for n in nodes if n["ref"] not in packed])
if to_change:
    changed = [n["ref"] for n in to_change if node_changed(n)]
    emit("change_recall", round(len(changed) / len(to_change), 3), "result",
         expected=[n["ref"] for n in to_change], found=changed)
emit("files_changed", len(changed_files), "result")

# --- тесты ----------------------------------------------------------------------------------
def junit(path: Path) -> list[tuple[str, bool]]:
    if not path.exists():
        return []
    out = []
    for tc in ET.parse(path).iter("testcase"):
        failed = any(c.tag in ("failure", "error") for c in tc)
        out.append((f"{tc.get('classname')}::{tc.get('name')}", not failed))
    return out


visible = junit(RUN_DIR / "junit-visible.xml")
emit("visible_tests_pass", int(bool(visible) and all(ok for _, ok in visible)), "result",
     failed=[n for n, ok in visible if not ok])
emit("ruff_pass", int((RUN_DIR / "ruff.status").read_text().strip() == "ok"), "result")

hidden_results = junit(RUN_DIR / "junit-hidden.xml")
task_mod = f"test_{meta['task_id'].lower()}"
task_tests = [(n, ok) for n, ok in hidden_results if f".{task_mod}::" in n or n.startswith(f"{task_mod}::")]
emit("task_success", int(bool(task_tests) and all(ok for _, ok in task_tests)), "result",
     passed=sum(ok for _, ok in task_tests), total=len(task_tests))
superseded = {s.split("::")[1] for s in task["supersedes"]}
if meta.get("series"):
    # В серии изменения копятся: тесты, заменённые предыдущими задачами серии, тоже не регрессия
    for prev in (EVAL / "logs" / "runs").glob(f"*-{meta['series']}"):
        prev_meta = json.loads((prev / "meta.json").read_text())
        prev_task_path = EVAL / "ground_truth" / "tasks" / f"{prev_meta['task_id']}.yaml"
        prev_task = yaml.safe_load(prev_task_path.read_text())
        superseded |= {s.split("::")[1] for s in prev_task["supersedes"]}
regressions = [
    n for n, ok in hidden_results
    if "regression" in n and not ok and n.split("::")[-1] not in superseded
]
emit("regressions", len(regressions), "result", failed=regressions)

with (RUN_DIR / "audit.jsonl").open("a") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
summary = {r["metric"]: r["value"] for r in records if r["metric"] != "hidden_link_recall_by_category"}
print(json.dumps(summary, ensure_ascii=False))
