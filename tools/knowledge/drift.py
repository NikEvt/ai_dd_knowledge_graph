"""Drift-проверки модели знаний (CI и локально).

1. Модель свежая: слои code/events/bpm, пересобранные из исходников, совпадают с knowledge/model/*.json
   (слой БД CI пересобирает отдельно, extract_db.py, и сравнивает через git diff).
2. Хэши правил: у каждой ссылки implemented_by / enforced_by_db хранится хэш реализации
   (нормализованный AST символа и транзитивно вызываемых функций проекта; описание перехода BPM;
   определение объекта БД). Хэш изменился, а правило в этом PR не тронуто -> правило suspect.
3. Новое ограничение БД (по сравнению с --base) без правила с enforced_by_db -> ошибка.
4. Отчёт о покрытии: правила без implemented_by / tested_by, suspect старше 14 дней.

  uv run python tools/knowledge/drift.py                      # проверка (CI)
  uv run python tools/knowledge/drift.py --base origin/main   # + сравнение с базовой веткой
  uv run python tools/knowledge/drift.py --write              # проставить хэши, пометить suspect
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import (
    ROOT,
    dump_json,
    dump_rules_yaml,
    error,
    git,
    load_model,
    rule_files,
    warn,
)

DB_KINDS = {"check", "unique", "unique_index", "partial_unique_index", "trigger", "function", "exclusion"}
STALE_SUSPECT_DAYS = 14


def current_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ("code", "bpm", "db"):
        for n in load_model(name)["nodes"]:
            if n.get("hash"):
                hashes[n["id"]] = n["hash"]
    return hashes


def ref_target(entry: Any) -> str | None:
    if isinstance(entry, dict):
        for key in ("symbol", "transition", "guard", "constraint", "trigger", "index", "function"):
            if entry.get(key):
                return entry[key]
    return None


def _entries(rule: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e
        for e in (rule.get("implemented_by") or []) + (rule.get("enforced_by_db") or [])
        if isinstance(e, dict)
    ]


def _semantic(rule: dict[str, Any]) -> dict[str, Any]:
    """Содержимое правила без служебных полей — для сравнения с базовой веткой."""
    skip = {"hash", "status", "suspect_since", "verified_by", "verified_at"}
    clean = {k: v for k, v in rule.items() if k not in skip and not k.startswith("_")}
    for key in ("implemented_by", "enforced_by_db"):
        if clean.get(key):
            clean[key] = [
                {k: v for k, v in e.items() if k != "hash"} if isinstance(e, dict) else e for e in clean[key]
            ]
    return clean


def base_rules(base: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in git("ls-tree", "-r", "--name-only", base, "knowledge/rules/").split():
        if not path.endswith(".yaml"):
            continue
        doc = yaml.safe_load(git("show", f"{base}:{path}")) or {}
        for r in doc.get("rules", []) or []:
            if r.get("id"):
                out[r["id"]] = r
    return out


def base_db_objects(base: str) -> set[str] | None:
    text = git("show", f"{base}:knowledge/model/db.json")
    if not text.strip():
        return None
    return {n["id"] for n in json.loads(text)["nodes"] if n.get("kind") in DB_KINDS}


def check_model_fresh() -> list[str]:
    from tools.knowledge import extract_bpm, extract_code, extract_events
    from tools.knowledge.pyindex import Project

    p = Project()
    p.analyze()
    fresh = {
        "code": extract_code.extract(),
        "events": extract_events.extract(p),
        "bpm": extract_bpm.extract(p),
    }
    stale = []
    for name, doc in fresh.items():
        path = ROOT / "knowledge" / "model" / f"{name}.json"
        if not path.exists() or path.read_text(encoding="utf-8") != dump_json(doc):
            stale.append(name)
    return stale


def read_rule_file(path: Path) -> tuple[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    header = ""
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        header += line + "\n"
    doc = yaml.safe_load(text) or {}
    return header, doc.get("rules", []) or []


def main() -> int:
    parser = argparse.ArgumentParser(description="Drift-проверки модели знаний")
    parser.add_argument("--base", help="базовая ревизия PR (например origin/main)")
    parser.add_argument("--write", action="store_true", help="проставить хэши и пометить suspect в YAML")
    parser.add_argument(
        "--skip-model-check", action="store_true", help="не пересобирать слои кода для сравнения"
    )
    args = parser.parse_args()
    errors = 0
    today = dt.date.today()
    summary: list[str] = ["## Модель знаний: drift и покрытие", ""]

    if not args.skip_model_check:
        stale = check_model_fresh()
        if stale:
            error(
                f"модель устарела ({', '.join(stale)}): "
                "запусти uv run python tools/knowledge/build_index.py --all"
            )
            errors += 1

    hashes = current_hashes()
    base = base_rules(args.base) if args.base else {}
    db_nodes = {n["id"]: n for n in load_model("db")["nodes"] if n.get("kind") in DB_KINDS}
    covered_db: set[str] = set()
    drifted: list[str] = []
    unstamped: list[str] = []
    stale_suspects: list[str] = []
    no_impl: list[str] = []
    no_tests: list[str] = []
    total = 0
    statuses: dict[str, int] = {}

    for path in rule_files():
        header, rules = read_rule_file(path)
        dirty = False
        for r in rules:
            total += 1
            rid = r.get("id", "?")
            statuses[r.get("status", "draft")] = statuses.get(r.get("status", "draft"), 0) + 1
            for db in r.get("enforced_by_db") or []:
                if target := ref_target(db):
                    covered_db.add(target)
            if not r.get("implemented_by") and not r.get("enforced_by_db"):
                no_impl.append(rid)
            if not r.get("tested_by"):
                no_tests.append(rid)
            rule_changed = rid in base and _semantic(base[rid]) != _semantic(r)
            for e in _entries(r):
                target = ref_target(e)
                if target not in hashes:
                    continue  # битую ссылку ловит check_rules.py
                if not e.get("hash"):
                    unstamped.append(f"{rid} -> {target}")
                    if args.write:
                        e["hash"] = hashes[target]
                        dirty = True
                    continue
                if e["hash"] == hashes[target]:
                    continue
                if rule_changed:
                    if args.write:
                        e["hash"] = hashes[target]
                        dirty = True
                    continue
                drifted.append(f"{rid} ({target})")
                if args.write:
                    e["hash"] = hashes[target]
                    if r.get("status") != "suspect":
                        r["status"] = "suspect"
                        r["suspect_since"] = today.isoformat()
                    dirty = True
            if r.get("status") == "suspect" and r.get("suspect_since"):
                since = dt.date.fromisoformat(str(r["suspect_since"]))
                if (today - since).days > STALE_SUSPECT_DAYS:
                    stale_suspects.append(f"{rid} (с {since})")
        if dirty:
            path.write_text(dump_rules_yaml(header, rules), encoding="utf-8")

    for item in drifted:
        warn(f"drift: код правила изменился, текст правила не обновлён -> suspect: {item}")
    if unstamped and not args.write:
        error(
            f"нет хэшей у ссылок правил ({len(unstamped)}): запусти drift.py --write; пример: {unstamped[0]}"
        )
        errors += 1
    for item in stale_suspects:
        warn(f"suspect дольше {STALE_SUSPECT_DAYS} дней — нужна задача на разбор: {item}")

    uncovered = sorted(set(db_nodes) - covered_db)
    base_db = base_db_objects(args.base) if args.base else None
    new_uncovered = [x for x in uncovered if base_db is not None and x not in base_db]
    for x in new_uncovered:
        error(f"новое ограничение БД без правила (enforced_by_db): {x}")
        errors += 1
    if uncovered and not new_uncovered:
        warn(f"ограничения БД без правил: {', '.join(uncovered)}")

    summary += [
        f"- правил: {total} ({', '.join(f'{k}: {v}' for k, v in sorted(statuses.items()))})",
        f"- drift (-> suspect): {len(drifted)}",
        f"- без implemented_by/enforced_by_db: {len(no_impl)}",
        f"- без tested_by: {len(no_tests)}",
        f"- ограничения БД без правил: {len(uncovered)} из {len(db_nodes)}",
        f"- suspect старше {STALE_SUSPECT_DAYS} дней: {len(stale_suspects)}",
    ]
    report = "\n".join(summary) + "\n"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(report)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
