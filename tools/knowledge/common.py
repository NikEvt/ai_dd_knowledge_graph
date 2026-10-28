"""Общие пути, формат модели знаний и загрузка правил."""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "knowledge"
MODEL = KNOWLEDGE / "model"
RULES = KNOWLEDGE / "rules"
INDEX = KNOWLEDGE / "index.sqlite"
GLOSSARY = KNOWLEDGE / "glossary.yaml"
RECONCILIATION = KNOWLEDGE / "reconciliation.yaml"
DOCS = ROOT / "docs"

MODEL_FILES = ("db", "code", "events", "bpm")
RULE_ID = re.compile(r"^R-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{2,}$")
RULE_STATUSES = ("draft", "verified", "suspect")
SERVICES = ("applications", "billing", "scheduling", "notifications", "chat")


def rel(path: Path | str) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def node(id_: str, type_: str, **attrs: Any) -> dict[str, Any]:
    return {"id": id_, "type": type_, **{k: v for k, v in attrs.items() if v not in (None, "", [], {})}}


def edge(src: str, dst: str, type_: str, **attrs: Any) -> dict[str, Any]:
    return {"src": src, "dst": dst, "type": type_, **{k: v for k, v in attrs.items() if v not in (None, "")}}


def dedup_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Одно ребро на (src, dst, type); номера строк копятся в lines."""
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for e in edges:
        key = (e["src"], e["dst"], e["type"])
        line = e.pop("line", None)
        cur = merged.setdefault(key, e)
        if line is not None:
            cur.setdefault("lines", [])
            if line not in cur["lines"]:
                cur["lines"].append(line)
        for k, v in e.items():
            cur.setdefault(k, v)
    for e in merged.values():
        if "lines" in e:
            e["lines"].sort()
    return sorted(merged.values(), key=lambda e: (e["type"], e["src"], e["dst"]))


def model_document(generator: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], **extra: Any):
    seen: dict[str, dict[str, Any]] = {}
    for n in nodes:
        seen.setdefault(n["id"], n)
    return {
        "generated_by": generator,
        "nodes": sorted(seen.values(), key=lambda n: (n["type"], n["id"])),
        "edges": dedup_edges(edges),
        **extra,
    }


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_model(name: str, data: dict[str, Any]) -> Path:
    MODEL.mkdir(parents=True, exist_ok=True)
    path = MODEL / f"{name}.json"
    path.write_text(dump_json(data), encoding="utf-8")
    return path


def load_model(name: str) -> dict[str, Any]:
    path = MODEL / f"{name}.json"
    if not path.exists():
        return {"nodes": [], "edges": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_glossary() -> dict[str, Any]:
    return yaml.safe_load(GLOSSARY.read_text(encoding="utf-8")) if GLOSSARY.exists() else {}


def rule_files() -> list[Path]:
    return sorted(p for p in RULES.glob("*.yaml"))


def load_rules() -> list[dict[str, Any]]:
    """Все правила; у каждого служебное поле _file (путь от корня репозитория)."""
    rules: list[dict[str, Any]] = []
    for path in rule_files():
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for r in doc.get("rules", []) or []:
            r["_file"] = rel(path)
            rules.append(r)
    return rules


def load_discrepancies() -> list[dict[str, Any]]:
    """Решения людей по расхождениям (knowledge/reconciliation.yaml)."""
    if not RECONCILIATION.exists():
        return []
    return (yaml.safe_load(RECONCILIATION.read_text(encoding="utf-8")) or {}).get("discrepancies", []) or []


class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper: yaml.SafeDumper, data: str) -> yaml.Node:
    if "\n" in data or len(data) > 100:  # проза: одна строка в folded-стиле, удобно править руками
        return dumper.represent_scalar("tag:yaml.org,2002:str", " ".join(data.split()) + "\n", style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_presenter)


def dump_rules_yaml(header: str, rules: list[dict[str, Any]]) -> str:
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rules]
    body = yaml.dump({"rules": clean}, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=100)
    return header + body


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def estimate_tokens(text: str) -> int:
    return len(text) // 3


def warn(msg: str) -> None:
    print(f"::warning::{msg}" if _in_ci() else f"WARNING: {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"::error::{msg}" if _in_ci() else f"ERROR: {msg}", file=sys.stderr)


def _in_ci() -> bool:
    import os

    return os.environ.get("GITHUB_ACTIONS") == "true"
