"""Слой кода модели знаний: символы, вызовы, ORM-таблицы, настройки, Depends, слушатели ORM, тесты.

Запуск: uv run python tools/knowledge/extract_code.py  ->  knowledge/model/code.json
"""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import SERVICES, edge, model_document, node, write_model
from tools.knowledge.pyindex import Project, Symbol

GENERATOR = "tools/knowledge/extract_code.py"
CONFIG_FILES = ("libs/settings.py",)
# Вызовы, которые модель хранит смысловыми рёбрами (publishes, transitions_to), а не calls.
SEMANTIC_CALLS = {"libs/events/outbox.py::publish", "libs/bpm/engine.py::transition", "libs/clock.py::now"}


def service_of(path: str) -> str | None:
    parts = path.split("/")
    if parts[0] == "services" and len(parts) > 2 and parts[1] in SERVICES:
        return parts[1]
    return None


def is_job(s: Symbol) -> bool:
    return s.path.endswith("/jobs.py") and s.kind == "function"


def is_test(s: Symbol) -> bool:
    return (
        s.path.startswith("tests/")
        and Path(s.path).name.startswith("test_")
        and s.qualname.startswith("test_")
    )


def _words(text: str) -> set[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    return {w.lower().rstrip("s") for w in re.split(r"[^A-Za-z]+", text) if len(w) > 2}


def _identifiers(s: Symbol) -> set[str]:
    words: set[str] = set(_words(s.qualname))
    for n in ast.walk(s.node):
        if isinstance(n, ast.Name):
            words |= _words(n.id)
        elif isinstance(n, ast.Attribute):
            words |= _words(n.attr)
        elif isinstance(n, ast.arg):
            words |= _words(n.arg)
    return words


def config_symbols(p: Project) -> set[str]:
    used = {cid for sid, f in p.facts.items() if not sid.startswith("tests/") for cid, _ in f.config}
    return {
        s.id
        for s in p.symbols.values()
        if s.kind == "constant"
        and not s.path.startswith("tests/")
        and not (isinstance(s.value, (dict, list, tuple)) and not s.value)  # пустой реестр, а не настройка
        and (s.id in used or s.path in CONFIG_FILES or s.path.endswith("/config.py"))
    }


def infer_magic_numbers(p: Project, configs: set[str]) -> list[dict[str, Any]]:
    """Литерал в timedelta(days=N), равный значению настройки *_DAYS, — скрытая связь с настройкой."""
    out = []
    day_configs = [
        p.symbols[c] for c in configs if c.endswith("_DAYS") and isinstance(p.symbols[c].value, int)
    ]
    for sid, f in p.facts.items():
        if sid.startswith("tests/") or not f.days_literals:
            continue
        ids = _identifiers(p.symbols[sid])
        for value, line in f.days_literals:
            candidates = [c for c in day_configs if c.value == value]
            scored = sorted(
                ((len(_words(c.qualname.removesuffix("_DAYS")) & ids), c.id) for c in candidates),
                reverse=True,
            )
            best = [cid for score, cid in scored if score and score == scored[0][0]]
            out.append(
                {
                    "symbol": sid,
                    "line": line,
                    "value": value,
                    "candidates": [cid for _, cid in scored],
                    "likely": best[0] if len(best) == 1 else None,
                }
            )
    return out


def tested_by(p: Project) -> dict[str, set[str]]:
    """symbol -> тесты, которые вызывают его напрямую или через помощников из tests/."""
    result: dict[str, set[str]] = defaultdict(set)
    for s in p.symbols.values():
        if not is_test(s):
            continue
        seen: set[str] = set()
        stack = [s.id]
        while stack:
            cur = stack.pop()
            f = p.facts.get(cur)
            if f is None:
                continue
            for target, _ in [*f.calls, *f.refs]:
                if target in seen:
                    continue
                seen.add(target)
                if target.startswith("tests/"):
                    stack.append(target)
                elif target.startswith("services/"):
                    result[target].add(s.id)
    return result


def symbol_type_and_kind(p: Project, s: Symbol) -> tuple[str, str]:
    d = p.decorations.get(s.id)
    if is_test(s):
        return "test", "test"
    if is_job(s):
        return "job", "job"
    if s.kind == "class":
        return "symbol", "orm_model" if s.id in p.orm else "class"
    if d is not None:
        if d.route:
            return "symbol", "route"
        if d.subscribe:
            return "symbol", "consumer"
        if d.guard:
            return "symbol", "guard"
        if d.listens_for:
            return "symbol", "orm_listener"
    if any(sub["handler"] == s.id for f in p.facts.values() for sub in f.subscribes):
        return "symbol", "consumer"
    return "symbol", s.kind


def signature(s: Symbol) -> str | None:
    n = s.node
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [a.arg for a in [*n.args.posonlyargs, *n.args.args]]
        if n.args.kwonlyargs:
            args += ["*", *(a.arg for a in n.args.kwonlyargs)]
        return f"({', '.join(args)})"
    return None


def service_apps(p: Project) -> dict[str, dict[str, Any]]:
    """FastAPI-приложения сервисов: какие роутеры подключены и что загружается при старте."""
    apps: dict[str, dict[str, Any]] = {}
    for m in p.modules.values():
        svc = service_of(m.path)
        if svc is None or not m.path.endswith("/app.py"):
            continue
        info: dict[str, Any] = {"path": m.path, "routers": [], "startup_calls": []}
        for stmt in m.tree.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "include_router" and call.args:
                    info["routers"].append(p.dotted(m, call.args[0]))
                else:
                    target = p.resolve_symbol(m, call.func)
                    info["startup_calls"].append(target.id if target else ast.unparse(call.func))
        apps[svc] = info
    return apps


def wiring_modules(p: Project) -> list[str]:
    s = p.symbols.get("services/wiring.py::MODULES")
    return list(s.value) if s is not None and s.value else []


def extract() -> dict[str, Any]:
    p = Project()
    p.analyze()
    configs = config_symbols(p)
    tests = tested_by(p)
    magic = infer_magic_numbers(p, configs)
    apps = service_apps(p)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for svc in SERVICES:
        nodes.append(
            node(
                f"service:{svc}",
                "service",
                name=svc,
                path=f"services/{svc}",
                app=apps.get(svc, {}).get("path"),
                startup=apps.get(svc, {}).get("startup_calls"),
            )
        )

    for s in sorted(p.symbols.values(), key=lambda s: s.id):
        if s.kind == "constant":
            if s.id not in configs:
                continue
            value = s.value if s.value is not None else ast.unparse(s.node.value)[:200]  # type: ignore[attr-defined]
            nodes.append(
                node(
                    s.id,
                    "config",
                    name=s.qualname,
                    path=s.path,
                    line=s.line,
                    end_line=s.end_line,
                    doc=s.doc,
                    value=value,
                    service=service_of(s.path),
                    hash=p.own_hash(s),
                )
            )
            continue
        if s.path.startswith("tests/") and not is_test(s):
            continue  # помощники тестов учитываются только в tested_by
        type_, kind = symbol_type_and_kind(p, s)
        d = p.decorations.get(s.id)
        f = p.facts.get(s.id)
        attrs: dict[str, Any] = {
            "name": s.qualname,
            "path": s.path,
            "line": s.line,
            "end_line": s.end_line,
            "doc": s.doc,
            "kind": kind,
            "service": service_of(s.path),
            "signature": signature(s),
        }
        if type_ != "test":
            attrs["hash"] = p.transitive_hash(s.id) if s.is_function else p.own_hash(s)
            attrs["hash_own"] = p.own_hash(s)
        if d is not None:
            if d.route:
                attrs["route"] = f"{d.route[0]} {d.route[1]}"
            if d.listens_for:
                attrs["listens_for"] = f"{d.listens_for[0]}.{d.listens_for[1]}"
        if f is not None and f.checks:
            attrs["checks"] = f.checks
        if s.id in p.orm:
            attrs["table"] = p.orm[s.id]["table"]
        nodes.append(node(s.id, type_, **attrs))

        if service_of(s.path) and type_ != "test":
            edges.append(edge(s.id, f"service:{service_of(s.path)}", "part_of"))
        if s.id in p.orm:
            edges.append(edge(s.id, p.orm[s.id]["table"], "maps_to"))
        if f is None or type_ == "test":
            continue
        for target, line in f.calls:
            callee = p.symbols.get(target)
            if callee is not None and callee.kind == "class":
                continue  # исключения и DTO: проверки уже в checks
            if not target.startswith("tests/") and target not in p.orm and target not in SEMANTIC_CALLS:
                edges.append(edge(s.id, target, "calls", line=line))
        for target, line in f.refs:
            if not target.startswith("tests/"):
                edges.append(edge(s.id, target, "refs", line=line))
        for target, line in f.depends:
            edges.append(edge(s.id, target, "depends_on", line=line))
        for target, line in f.config:
            if target in configs:
                edges.append(edge(s.id, target, "reads_config", line=line))
        for kind_, items in (("reads", f.reads), ("writes", f.writes)):
            cols: dict[str, set[str]] = defaultdict(set)
            lines: dict[str, list[int]] = defaultdict(list)
            for cls, line, col in items:
                table = p.orm[cls]["table"]
                lines[table].append(line)
                if col:
                    cols[table].add(col)
            for table, ls in lines.items():
                for line in sorted(set(ls)):
                    edges.append(edge(s.id, table, kind_, line=line, columns=sorted(cols[table]) or None))
        if d is not None and d.listens_for:
            for cls, line in f.isinstance_of:
                edges.append(edge(s.id, p.orm[cls]["table"], "listens", line=line, event=d.listens_for[1]))

    for m in magic:
        if m["likely"]:
            edges.append(
                edge(
                    m["symbol"],
                    m["likely"],
                    "reads_config",
                    line=m["line"],
                    inferred=f"литерал {m['value']} вместо настройки",
                )
            )

    for target, ts in tests.items():
        if target in p.symbols:
            for t in sorted(ts):
                edges.append(edge(target, t, "tested_by"))

    known = {n["id"] for n in nodes}
    edges = [e for e in edges if e["dst"] in known or e["type"] in ("reads", "writes", "maps_to", "listens")]
    return model_document(
        GENERATOR,
        nodes,
        edges,
        orm={p.orm[c]["table"]: {"class": c, **p.orm[c]} for c in sorted(p.orm)},
        wiring={"path": "services/wiring.py", "modules": wiring_modules(p)},
        apps=apps,
        magic_numbers=magic,
    )


def main() -> None:
    doc = extract()
    path = write_model("code", doc)
    print(
        f"{path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}: "
        f"{len(doc['nodes'])} nodes, {len(doc['edges'])} edges"
    )


if __name__ == "__main__":
    main()
