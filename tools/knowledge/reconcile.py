"""Детерминированная сверка источников: БД, ORM, код, процесс, правила.

Находит то, что потом формулирует человек или LLM:
- ограничения БД, не описанные правилами (скрытые правила);
- расхождения ORM-моделей (Base.metadata) и реальной схемы;
- проверки в коде (raise DomainError/AccessDenied), не покрытые правилами;
- литералы, совпадающие со значением настройки (срок задан в обход настройки);
- события без подписчиков или публикаторов, модули с подписчиками вне services/wiring.py;
- условия процесса без реализации, переходы, которые код никогда не выполняет;
- роли, которые код не проверяет; фоновые задачи без вызова из кода (только тесты).

  uv run python tools/knowledge/reconcile.py [--format md|json]
  uv run python tools/knowledge/reconcile.py --rules-digest     # краткий список правил для LLM
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import load_glossary, load_model, load_rules
from tools.knowledge.drift import DB_KINDS, ref_target

CHECK_ERRORS = {"DomainError", "AccessDenied", "TransitionError"}


def _lines(spec: Any) -> set[int] | None:
    if spec is None:
        return None
    out: set[int] = set()
    for part in str(spec).replace(" ", "").split(","):
        if m := re.match(r"^(\d+)(?:-(\d+))?$", part):
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            out |= set(range(a, b + 1))
    return out or None


def _norm_type(t: str) -> str:
    t = t.lower()
    aliases = {
        "integer": "int",
        "bigint": "int",
        "varchar": "text",
        "character varying": "text",
        "timestamp with time zone": "datetime",
        "datetime": "datetime",
        "date": "date",
        "boolean": "bool",
        "jsonb": "json",
        "numeric": "numeric",
    }
    base = re.sub(r"\(.*\)", "", t).strip()
    return aliases.get(base, base)


def findings() -> dict[str, Any]:
    code = load_model("code")
    db = load_model("db")
    events = load_model("events")
    bpm = load_model("bpm")
    rules = load_rules()
    nodes = {n["id"]: n for m in (code, db, events, bpm) for n in m["nodes"]}
    out: dict[str, Any] = {}

    covered_db = {ref_target(e) for r in rules for e in r.get("enforced_by_db") or []}
    out["db_uncovered"] = sorted(
        n["id"] for n in db["nodes"] if n.get("kind") in DB_KINDS and n["id"] not in covered_db
    )

    # ORM <-> БД
    db_tables = {n["id"]: n for n in db["nodes"] if n["type"] == "table"}
    orm = code.get("orm", {})
    orm_db: list[str] = []
    for table, info in sorted(orm.items()):
        if table not in db_tables:
            orm_db.append(f"{table}: таблица есть в ORM ({info['class']}), но нет в БД")
            continue
        dcols = {c["name"]: c for c in db_tables[table]["columns"]}
        for col, spec in info["columns"].items():
            if col not in dcols:
                orm_db.append(f"{table}.{col}: колонка есть в ORM, но нет в БД")
                continue
            if not spec["pk"] and spec["nullable"] != dcols[col]["nullable"]:
                orm_db.append(
                    f"{table}.{col}: nullable в ORM={spec['nullable']}, в БД={dcols[col]['nullable']}"
                )
            if _norm_type(spec["type"]) != _norm_type(dcols[col]["type"]):
                orm_db.append(f"{table}.{col}: тип в ORM {spec['type']}, в БД {dcols[col]['type']}")
        for col in sorted(set(dcols) - set(info["columns"])):
            orm_db.append(f"{table}.{col}: колонка есть в БД, но нет в ORM")
        fk_db = {e["dst"] for e in db["edges"] if e["type"] == "fk" and e["src"] == table}
        fk_orm = {f.split("->")[1].rsplit(".", 1)[0] for f in info.get("foreign_keys", [])}
        for t in sorted(fk_db - fk_orm):
            orm_db.append(f"{table}: FK на {t} есть в БД, но не объявлен в ORM")
    for table in sorted(set(db_tables) - set(orm)):
        orm_db.append(f"{table}: таблица есть в БД, но нет ORM-модели")
    out["orm_vs_db"] = orm_db

    # Проверки в коде без правил
    covered: dict[str, list[set[int] | None]] = {}
    for r in rules:
        for e in r.get("implemented_by") or []:
            if isinstance(e, dict) and e.get("symbol"):
                covered.setdefault(e["symbol"], []).append(_lines(e.get("lines")))
    uncovered_checks = []
    for n in code["nodes"]:
        if not n["id"].startswith("services/"):
            continue
        for c in n.get("checks", []):
            if c["error"] not in CHECK_ERRORS:
                continue
            spans = covered.get(n["id"])
            if spans and any(s is None or c["line"] in s for s in spans):
                continue
            uncovered_checks.append(f"{n['id']}:{c['line']} {c['error']}: {c['message']}")
    out["code_checks_uncovered"] = uncovered_checks

    out["magic_numbers"] = [
        f"{m['symbol']}:{m['line']}: литерал {m['value']} совпадает с {', '.join(m['candidates'])}"
        + (f" (вероятно {m['likely']})" if m.get("likely") else "")
        for m in code.get("magic_numbers", [])
    ]
    out["event_orphans"] = [f"{n['id']}: {n['orphan']}" for n in events["nodes"] if n.get("orphan")]

    wired = set(code.get("wiring", {}).get("modules", []))
    registering = set()
    for n in code["nodes"]:
        if n.get("kind") in ("consumer", "guard", "orm_listener") and n["id"].startswith("services/"):
            registering.add(n["path"][:-3].replace("/", "."))
    out["unwired_modules"] = sorted(
        f"{m}: регистрирует обработчики, но не подключён в services/wiring.py" for m in registering - wired
    )

    out["bpm_guards"] = [
        f"{n['id']}: {n.get('missing') or n.get('unused')}"
        for n in bpm["nodes"]
        if n["type"] == "bpm_guard" and (n.get("missing") or n.get("unused"))
    ]
    executed = {e["dst"] for e in bpm["edges"] if e["type"] == "transitions_to"}
    out["bpm_unexecuted"] = sorted(
        f"{n['id']} ({'/'.join(a for v in n['variants'] for a in v['actor'])}): "
        "нет кода, выполняющего переход"
        for n in bpm["nodes"]
        if n["type"] == "bpm_transition" and n["id"] not in executed
    )

    params = {
        p for n in code["nodes"] for p in (n.get("signature") or "").strip("()").replace("*", "").split(", ")
    }
    actors = {n["name"] for n in bpm["nodes"] if n["type"] == "role"}
    out["roles_unchecked"] = sorted(
        f"{role} ({info.get('ru')}): нет параметра-исполнителя в коде и переходов процесса"
        for role, info in load_glossary().get("roles", {}).items()
        if not any(p in params for p in info.get("params", [])) and role not in actors
    )

    callers = {
        e["dst"]
        for e in code["edges"]
        if e["type"] in ("calls", "refs") and not e["src"].startswith("tests/")
    }
    out["jobs_unscheduled"] = sorted(
        f"{n['id']}: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория"
        for n in code["nodes"]
        if n["type"] == "job" and n["id"] not in callers
    )
    out["rules_with_discrepancy"] = sorted(
        f"{r['id']}: {' '.join(str(r['discrepancy']).split())}" for r in rules if r.get("discrepancy")
    )
    out["rules_unresolved_refs"] = sorted(
        f"{r['id']}: {', '.join(r['unresolved_refs'])}" for r in rules if r.get("unresolved_refs")
    )
    out["_nodes_count"] = len(nodes)
    return out


TITLES = {
    "db_uncovered": "Ограничения БД без правил (скрытые правила)",
    "orm_vs_db": "ORM-модели и реальная схема БД",
    "code_checks_uncovered": "Проверки в коде, не покрытые правилами",
    "magic_numbers": "Литералы вместо настроек",
    "event_orphans": "События без подписчиков или публикаторов",
    "unwired_modules": "Модули с обработчиками вне services/wiring.py",
    "bpm_guards": "Условия процесса без реализации или неиспользуемые",
    "bpm_unexecuted": "Переходы процесса, которые код не выполняет",
    "roles_unchecked": "Роли схемы, которые код не проверяет",
    "jobs_unscheduled": "Фоновые задачи без запуска в репозитории",
    "rules_with_discrepancy": "Правила с расхождением со схемой",
    "rules_unresolved_refs": "Правила с неразрешёнными ссылками",
}


def to_markdown(f: dict[str, Any]) -> str:
    parts = []
    for key, title in TITLES.items():
        items = f.get(key, [])
        parts.append(f"### {title} ({len(items)})\n")
        parts.append("\n".join(f"- {x}" for x in items) if items else "- нет")
        parts.append("")
    return "\n".join(parts) + "\n"


def rules_digest() -> str:
    lines = []
    for r in load_rules():
        impl = ", ".join(str(ref_target(e)) for e in r.get("implemented_by") or [])
        db = ", ".join(str(ref_target(e)) for e in r.get("enforced_by_db") or [])
        lines.append(
            f"- {r['id']} | {r.get('title', '')} | {' '.join(str(r.get('text', '')).split())}"
            f" | schema_ref: {r.get('schema_ref', '-')} | код: {impl or '-'} | БД: {db or '-'}"
            + (f" | discrepancy: {' '.join(str(r['discrepancy']).split())}" if r.get("discrepancy") else "")
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Сверка источников модели знаний")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--rules-digest", action="store_true")
    args = parser.parse_args()
    if args.rules_digest:
        sys.stdout.write(rules_digest())
        return
    f = findings()
    sys.stdout.write(
        json.dumps(f, ensure_ascii=False, indent=1) + "\n" if args.format == "json" else to_markdown(f)
    )


if __name__ == "__main__":
    main()
