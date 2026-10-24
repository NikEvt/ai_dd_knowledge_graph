"""Слой процесса: этапы, переходы и условия из bpm/application_process.yaml и их связь с кодом.

- переход ``from->to`` (несколько описаний одного перехода с разными исполнителями сливаются в варианты);
- условие ``guard:<name>`` и его реализация (``@bpm.guard("name")``);
- код, который выполняет переход (``bpm.transition(session, app, "dst", actor=...)``);
- роли-исполнители переходов.

Запуск: uv run python tools/knowledge/extract_bpm.py  ->  knowledge/model/bpm.json
"""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import ROOT, edge, model_document, node, rel, write_model
from tools.knowledge.pyindex import Project

GENERATOR = "tools/knowledge/extract_bpm.py"
PROCESS_FILE = ROOT / "bpm" / "application_process.yaml"
PROCESS_TABLE = {"application": "applications.applications"}


def _as_list(v: str | list[str]) -> list[str]:
    return v if isinstance(v, list) else [v]


def transition_hash(variants: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [{k: v for k, v in x.items() if k != "line"} for x in variants], sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def load_process() -> tuple[dict[str, Any], list[int]]:
    text = PROCESS_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    root = yaml.compose(text)
    lines: list[int] = []
    for key, value in root.value:  # type: ignore[union-attr]
        if key.value == "transitions":
            lines = [item.start_mark.line + 1 for item in value.value]
    return data, lines


def extract(p: Project | None = None) -> dict[str, Any]:
    if p is None:
        p = Project()
        p.analyze()
    data, lines = load_process()
    path = rel(PROCESS_FILE)
    process = data["process"]
    table = PROCESS_TABLE.get(process)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    kinds_by_stage: dict[str, list[str]] = defaultdict(list)
    for kind, stages in data["paths"].items():
        for st in stages:
            kinds_by_stage[st].append(kind)
    nodes.append(
        node(f"process:{process}", "bpm_process", name=process, path=path, paths=data["paths"], table=table)
    )
    for i, st in enumerate(data["stages"]):
        nodes.append(
            node(f"stage:{st}", "status", name=st, path=path, order=i, kinds=kinds_by_stage.get(st) or None)
        )

    variants: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t, line in zip(data["transitions"], lines, strict=True):
        for src in _as_list(t["from"]):
            v = {"actor": _as_list(t["actor"]), "line": line}
            if "kinds" in t:
                v["kinds"] = t["kinds"]
            if "guard" in t:
                v["guard"] = t["guard"]
            variants[f"{src}->{t['to']}"].append(v)

    guard_impl = {d.guard: sid for sid, d in p.decorations.items() if d.guard}
    guards: set[str] = set()
    roles: set[str] = set()
    for tid, vs in sorted(variants.items()):
        src, dst = tid.split("->")
        nodes.append(
            node(
                tid,
                "bpm_transition",
                name=tid,
                path=path,
                line=vs[0]["line"],
                variants=vs,
                hash=transition_hash(vs),
            )
        )
        edges.append(edge(tid, f"stage:{src}", "from_stage"))
        edges.append(edge(tid, f"stage:{dst}", "to_stage"))
        for v in vs:
            if g := v.get("guard"):
                guards.add(g)
                edges.append(edge(tid, f"guard:{g}", "guarded_by"))
            for a in v["actor"]:
                roles.add(a)
                edges.append(
                    edge(tid, f"role:{a}", "allowed_for", kinds=",".join(v.get("kinds", [])) or None)
                )

    for g in sorted(guards | set(guard_impl)):
        impl = guard_impl.get(g)
        sym = p.symbols.get(impl) if impl else None
        nodes.append(
            node(
                f"guard:{g}",
                "bpm_guard",
                name=g,
                path=path,
                implemented_by=impl,
                doc=sym.doc if sym else None,
                missing="условие не зарегистрировано через @bpm.guard" if impl is None else None,
                unused="условие не используется в процессе" if g not in guards else None,
            )
        )
        if impl:
            edges.append(edge(f"guard:{g}", impl, "implemented_by", line=sym.line if sym else None))

    for r in sorted(roles):
        nodes.append(node(f"role:{r}", "role", name=r))

    for sid, f in sorted(p.facts.items()):
        if sid.startswith("tests/"):
            continue
        for t in f.transitions:
            dst, actor = t["to"], t["actor"]
            matched = [
                tid
                for tid, vs in variants.items()
                if (dst is None or tid.split("->")[1] == dst)
                and any(actor is None or actor in v["actor"] for v in vs)
            ]
            for tid in matched:
                edges.append(
                    edge(
                        sid,
                        tid,
                        "transitions_to",
                        line=t["line"],
                        actor=actor or "(параметр)",
                        condition=t["condition"] or None,
                    )
                )
            if table:
                edges.append(
                    edge(sid, table, "writes", line=t["line"], columns=["stage"], via="libs/bpm/engine.py")
                )

    return model_document(GENERATOR, nodes, edges, stages=data["stages"], paths=data["paths"])


def main() -> None:
    doc = extract()
    write_model("bpm", doc)
    print(f"knowledge/model/bpm.json: {len(doc['nodes'])} nodes, {len(doc['edges'])} edges")


if __name__ == "__main__":
    main()
