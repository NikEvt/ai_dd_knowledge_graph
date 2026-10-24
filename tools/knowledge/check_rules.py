"""Проверка правил и аннотаций ``# @rule`` (Ruff не поддерживает пользовательские правила).

Ошибки (exit 1):
- YAML правил некорректен: нет id/title/text, неверный формат ID или статус, повторный ID;
- ссылка правила на несуществующий узел модели: implemented_by (символ, переход, условие),
  enforced_by_db, tested_by, config, related;
- аннотация ``# @rule R-…`` ссылается на несуществующее правило или символ не указан в implemented_by.

Предупреждения:
- строки implemented_by вне тела символа; неразрешённые ссылки в trigger/effects; неизвестные роли;
- с --base: новый или изменённый код в services/ без правила и без аннотации @rule.

  uv run python tools/knowledge/check_rules.py [--base origin/main]
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import (
    ROOT,
    RULE_ID,
    RULE_STATUSES,
    error,
    git,
    load_glossary,
    load_model,
    rel,
    rule_files,
    warn,
)
from tools.knowledge.drift import ref_target
from tools.knowledge.graph import _rule_refs

ANNOTATION = re.compile(r"#\s*@rule\s+((?:R-[A-Z0-9-]+[\s,]*)+)")
ANNOTATED_DIRS = ("services", "libs", "tests")
REQUIRED = ("id", "title", "text", "status")


def annotations() -> list[tuple[str, int, str, str | None]]:
    """(файл, строка, ID правила, символ, к которому относится аннотация)."""
    out = []
    for d in ANNOTATED_DIRS:
        for path in sorted((ROOT / d).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "@rule" not in text:
                continue
            lines = text.splitlines()
            defs = _def_spans(ast.parse(text))
            for i, line in enumerate(lines, 1):
                m = ANNOTATION.search(line)
                if not m:
                    continue
                symbol = _symbol_at(defs, i)
                for rid in re.findall(r"R-[A-Z0-9-]+", m.group(1)):
                    out.append((rel(path), i, rid, f"{rel(path)}::{symbol}" if symbol else None))
    return out


def _def_spans(tree: ast.Module) -> list[tuple[int, int, str]]:
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            spans.append((start, node.end_lineno or node.lineno, node.name))
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        s = min([sub.lineno, *(d.lineno for d in sub.decorator_list)])
                        spans.append((s, sub.end_lineno or sub.lineno, f"{node.name}.{sub.name}"))
    return spans


def _symbol_at(spans: list[tuple[int, int, str]], line: int) -> str | None:
    """Символ, внутри которого стоит аннотация, или следующий за ней (комментарий над def)."""
    inside = [s for s in spans if s[0] <= line <= s[1]]
    if inside:
        return max(inside, key=lambda s: s[0])[2]
    after = [s for s in spans if s[0] > line]
    return min(after, key=lambda s: s[0])[2] if after else None


def _line_span(spec: Any) -> tuple[int, int] | None:
    m = re.match(r"^\s*(\d+)(?:\s*-\s*(\d+))?\s*$", str(spec))
    return (int(m.group(1)), int(m.group(2) or m.group(1))) if m else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка правил и аннотаций @rule")
    parser.add_argument("--base", help="базовая ревизия PR для поиска кода без правил")
    args = parser.parse_args()

    nodes = {n["id"]: n for name in ("code", "events", "bpm", "db") for n in load_model(name)["nodes"]}
    roles = set(load_glossary().get("roles", {}))
    errors = 0
    rules: dict[str, dict[str, Any]] = {}

    def fail(msg: str) -> None:
        nonlocal errors
        errors += 1
        error(msg)

    for path in rule_files():
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            fail(f"{rel(path)}: YAML не разбирается: {exc}")
            continue
        for r in doc.get("rules", []) or []:
            rid = r.get("id")
            where = f"{rel(path)}: {rid}"
            missing = [k for k in REQUIRED if not r.get(k)]
            if missing:
                fail(f"{where}: нет полей {missing}")
            if not rid or not RULE_ID.match(str(rid)):
                fail(f"{where}: неверный формат ID (ожидается R-ТЕМА-NN)")
                continue
            if rid in rules:
                fail(f"{where}: повторный ID (уже в {rules[rid]['_file']})")
            r["_file"] = rel(path)
            rules[rid] = r
            if r.get("status") not in RULE_STATUSES:
                fail(f"{where}: статус {r.get('status')!r} не из {RULE_STATUSES}")
            for e in r.get("implemented_by") or []:
                target = ref_target(e)
                if target not in nodes:
                    fail(f"{where}: implemented_by -> неизвестный узел {target!r}")
                    continue
                span = _line_span(e.get("lines")) if e.get("lines") else None
                n = nodes[target]
                if (
                    span
                    and n.get("line")
                    and not (n["line"] - 3 <= span[0] <= span[1] <= n.get("end_line", n["line"]))
                ):
                    warn(f"{where}: строки {e['lines']} вне {target} ({n['line']}-{n.get('end_line')})")
            for e in r.get("enforced_by_db") or []:
                target = ref_target(e)
                if target not in nodes or nodes[target]["type"] not in ("db_constraint", "table"):
                    fail(f"{where}: enforced_by_db -> неизвестный объект БД {target!r}")
            for t in r.get("tested_by") or []:
                if t not in nodes or nodes[t]["type"] != "test":
                    fail(f"{where}: tested_by -> неизвестный тест {t!r}")
            for c in r.get("config") or []:
                if c not in nodes or nodes[c]["type"] != "config":
                    fail(f"{where}: config -> неизвестная настройка {c!r}")
            for role in r.get("roles") or []:
                if role not in roles:
                    warn(f"{where}: неизвестная роль {role!r} (см. knowledge/glossary.yaml)")
            for ref in _rule_refs([r.get("trigger"), r.get("applies_to"), r.get("effects")]):
                if ref not in nodes and not ref.startswith(
                    ("role:", "stage:", "guard:", "effect:", "service:")
                ):
                    warn(f"{where}: ссылка {ref!r} в trigger/effects не найдена в модели")
            if r.get("unresolved_refs"):
                warn(f"{where}: неразрешённые ссылки после bootstrap: {r['unresolved_refs']}")

    for rid, r in rules.items():
        for other in r.get("related") or []:
            if other not in rules:
                fail(f"{r['_file']}: {rid}: related -> неизвестное правило {other}")

    implemented: dict[str, set[str]] = {}
    for rid, r in rules.items():
        implemented[rid] = {ref_target(e) for e in r.get("implemented_by") or [] if ref_target(e)}
    for path, line, rid, symbol in annotations():
        if rid not in rules:
            fail(f"{path}:{line}: @rule {rid} — нет такого правила")
        elif symbol and symbol not in implemented[rid] and not symbol.startswith("tests/"):
            fail(f"{path}:{line}: @rule {rid} на {symbol}, но символа нет в implemented_by правила")
        elif symbol and symbol.startswith("tests/") and symbol not in (rules[rid].get("tested_by") or []):
            fail(f"{path}:{line}: @rule {rid} на тесте {symbol}, но теста нет в tested_by правила")

    if args.base:
        base_text = git("show", f"{args.base}:knowledge/model/code.json")
        base_hash = (
            {n["id"]: n.get("hash_own") for n in json.loads(base_text)["nodes"]} if base_text.strip() else {}
        )
        covered = {t for ts in implemented.values() for t in ts}
        annotated = {s for *_, s in annotations() if s}
        for n in load_model("code")["nodes"]:
            if n["type"] not in ("symbol", "job") or not n["id"].startswith("services/"):
                continue
            if n.get("kind") in ("class", "orm_model", "module") or n["name"].startswith("_"):
                continue
            if base_hash.get(n["id"]) == n.get("hash_own"):
                continue
            if n["id"] not in covered and n["id"] not in annotated:
                warn(f"{n['id']}: новый или изменённый код без правила и аннотации @rule")

    print(f"check_rules: правил {len(rules)}, аннотаций {len(annotations())}, ошибок {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
