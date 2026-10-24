"""Слой БД: реальная схема после ``alembic upgrade head``.

По умолчанию создаёт временную базу рядом с основной (тот же сервер из DATABASE_URL), прогоняет
миграции, читает information_schema и pg_catalog и удаляет базу. С ``--database-url`` читает уже
мигрированную базу как есть.

Извлекаются: таблицы и колонки, PK, FK, CHECK, UNIQUE, индексы (в т.ч. частичные), триггеры и
тела функций (какие таблицы функция читает, какие ошибки бросает). Для каждого объекта ищется
место в миграциях (файл и строка).

Запуск: uv run python tools/knowledge/extract_db.py [--database-url URL]  ->  knowledge/model/db.json
"""

import argparse
import asyncio
import hashlib
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import asyncpg

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import ROOT, edge, model_document, node, rel, write_model

GENERATOR = "tools/knowledge/extract_db.py"
SYSTEM = "('pg_catalog', 'information_schema')"
IGNORED_TABLES = {"public.alembic_version"}
MIGRATIONS = ROOT / "migrations" / "versions"

Q_TABLES = f"""
SELECT n.nspname AS schema, c.relname AS name, obj_description(c.oid) AS comment
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p') AND n.nspname NOT IN {SYSTEM} AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY 1, 2
"""
Q_COLUMNS = f"""
SELECT table_schema AS schema, table_name AS table, column_name AS name, data_type AS type,
       is_nullable = 'YES' AS nullable, column_default AS default, ordinal_position AS pos
FROM information_schema.columns
WHERE table_schema NOT IN {SYSTEM}
ORDER BY 1, 2, ordinal_position
"""
Q_CONSTRAINTS = f"""
SELECT con.conname AS name, n.nspname AS schema, rel.relname AS table, con.contype::text AS type,
       pg_get_constraintdef(con.oid) AS definition,
       ARRAY(SELECT a.attname FROM unnest(con.conkey) k
             JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k ORDER BY a.attnum) AS columns,
       fn.nspname AS ref_schema, frel.relname AS ref_table
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace n ON n.oid = rel.relnamespace
LEFT JOIN pg_class frel ON frel.oid = con.confrelid
LEFT JOIN pg_namespace fn ON fn.oid = frel.relnamespace
WHERE n.nspname NOT IN {SYSTEM}
ORDER BY 2, 3, 1
"""
Q_INDEXES = f"""
SELECT ic.relname AS name, n.nspname AS schema, t.relname AS table, i.indisunique AS is_unique,
       pg_get_indexdef(i.indexrelid) AS definition, pg_get_expr(i.indpred, i.indrelid) AS predicate
FROM pg_index i
JOIN pg_class ic ON ic.oid = i.indexrelid
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname NOT IN {SYSTEM} AND n.nspname NOT LIKE 'pg_toast%'
  AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = i.indexrelid)
ORDER BY 2, 3, 1
"""
Q_TRIGGERS = f"""
SELECT tg.tgname AS name, n.nspname AS schema, t.relname AS table, pg_get_triggerdef(tg.oid) AS definition,
       pn.nspname AS function_schema, p.proname AS function
FROM pg_trigger tg
JOIN pg_class t ON t.oid = tg.tgrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_proc p ON p.oid = tg.tgfoid
JOIN pg_namespace pn ON pn.oid = p.pronamespace
WHERE NOT tg.tgisinternal AND n.nspname NOT IN {SYSTEM}
ORDER BY 2, 3, 1
"""
Q_FUNCTIONS = f"""
SELECT n.nspname AS schema, p.proname AS name, l.lanname AS language,
       pg_get_function_result(p.oid) AS returns, p.prosrc AS body
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
JOIN pg_language l ON l.oid = p.prolang
WHERE n.nspname NOT IN {SYSTEM} AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY 1, 2
"""


def _dsn(url: str) -> str:
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def _with_db(url: str, dbname: str) -> str:
    return re.sub(r"/[^/?]+(\?|$)", f"/{dbname}\\1", url, count=1)


def _h(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:12]


class MigrationIndex:
    """Где в миграциях определён объект БД."""

    def __init__(self) -> None:
        self.files = {
            rel(p): p.read_text(encoding="utf-8").splitlines() for p in sorted(MIGRATIONS.glob("*.py"))
        }

    def find(self, pattern: str, start: tuple[str, int] | None = None, stop: str | None = None):
        rx = re.compile(pattern, re.IGNORECASE)
        for path, lines in self.files.items():
            if start and path != start[0]:
                continue
            first = start[1] - 1 if start else 0
            for i in range(first, len(lines)):
                if stop and i > first and re.search(stop, lines[i], re.IGNORECASE):
                    break
                if rx.search(lines[i]):
                    return path, i + 1
        return None

    def table(self, fullname: str):
        return self.find(rf"CREATE TABLE\s+{re.escape(fullname)}\b")

    def named(self, name: str):
        return self.find(rf"\b{re.escape(name)}\b")

    def in_table(self, fullname: str, *needles: str):
        loc = self.table(fullname)
        if loc is None:
            return None
        rx = ".*".join(re.escape(n) for n in needles)
        return self.find(rx, start=loc, stop=r"^\);|CREATE (TABLE|FUNCTION|TRIGGER|INDEX|UNIQUE)") or loc


def _loc(loc: tuple[str, int] | None) -> dict[str, Any]:
    return {"path": loc[0], "line": loc[1]} if loc else {}


def _trigger_parts(definition: str) -> dict[str, Any]:
    m = re.search(r"TRIGGER \S+ (BEFORE|AFTER|INSTEAD OF) (.+?) ON ", definition)
    if not m:
        return {}
    events = m.group(2)
    cols = re.search(r"UPDATE OF ([\w, ]+?)(?: OR | ON |$)", events + " ON ")
    return {
        "timing": m.group(1),
        "events": [e.split(" OF ")[0].strip() for e in events.split(" OR ")],
        "columns": [c.strip() for c in cols.group(1).split(",")] if cols else None,
        "for_each": "ROW" if "FOR EACH ROW" in definition else "STATEMENT",
    }


def _function_facts(body: str, tables: set[str]) -> dict[str, Any]:
    refs = sorted({t for t in tables if re.search(rf"\b{re.escape(t)}\b", body)})
    raises = [m.group(1) for m in re.finditer(r"RAISE EXCEPTION\s+'([^']*)'", body)]
    new_old = sorted(set(re.findall(r"\b(?:NEW|OLD)\.(\w+)", body)))
    return {"tables": refs, "raises": raises, "row_columns": new_old}


async def introspect(url: str) -> dict[str, Any]:
    conn = await asyncpg.connect(_dsn(url))
    try:
        tables = [dict(r) for r in await conn.fetch(Q_TABLES)]
        columns = [dict(r) for r in await conn.fetch(Q_COLUMNS)]
        constraints = [dict(r) for r in await conn.fetch(Q_CONSTRAINTS)]
        indexes = [dict(r) for r in await conn.fetch(Q_INDEXES)]
        triggers = [dict(r) for r in await conn.fetch(Q_TRIGGERS)]
        functions = [dict(r) for r in await conn.fetch(Q_FUNCTIONS)]
    finally:
        await conn.close()
    return {
        "tables": tables,
        "columns": columns,
        "constraints": constraints,
        "indexes": indexes,
        "triggers": triggers,
        "functions": functions,
    }


def build(raw: dict[str, Any]) -> dict[str, Any]:
    mig = MigrationIndex()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    full = lambda r: f"{r['schema']}.{r['table']}"  # noqa: E731
    table_ids = {f"{t['schema']}.{t['name']}" for t in raw["tables"]} - IGNORED_TABLES

    # Имена объектов должны быть уникальны: при совпадении в разных схемах добавляем схему.
    names: dict[str, int] = {}
    for group in ("constraints", "indexes", "triggers", "functions"):
        for r in raw[group]:
            names[r["name"]] = names.get(r["name"], 0) + 1

    def oid(r: dict[str, Any]) -> str:
        return r["name"] if names[r["name"]] == 1 else f"{r['schema']}.{r['name']}"

    cols_by_table: dict[str, list[dict[str, Any]]] = {}
    for c in raw["columns"]:
        t = full(c)
        cols_by_table.setdefault(t, []).append(
            {k: c[k] for k in ("name", "type", "nullable", "default") if c[k] not in (None,)}
        )
    pk: dict[str, list[str]] = {}
    for r in raw["constraints"]:
        if r["type"] == "p":
            pk[full(r)] = list(r["columns"])

    for t in raw["tables"]:
        tid = f"{t['schema']}.{t['name']}"
        if tid not in table_ids:
            continue
        cols = cols_by_table.get(tid, [])
        nodes.append(
            node(
                tid,
                "table",
                name=tid,
                schema=t["schema"],
                columns=cols,
                primary_key=pk.get(tid),
                comment=t["comment"],
                hash=_h(repr(cols) + repr(pk.get(tid))),
                **_loc(mig.table(tid)),
            )
        )

    for r in raw["constraints"]:
        tid = full(r)
        if tid not in table_ids:
            continue
        kind = {"c": "check", "u": "unique", "f": "foreign_key", "x": "exclusion"}.get(r["type"])
        if kind is None:
            continue
        if kind == "foreign_key":
            ref = f"{r['ref_schema']}.{r['ref_table']}"
            edges.append(
                edge(
                    tid,
                    ref,
                    "fk",
                    constraint=r["name"],
                    columns=",".join(r["columns"]),
                    on_delete="cascade" if "ON DELETE CASCADE" in r["definition"] else None,
                )
            )
            continue
        cols = list(r["columns"])
        keyword = "CHECK" if kind == "check" else "UNIQUE"
        if len(cols) == 1:
            loc = mig.named(r["name"]) or mig.in_table(tid, cols[0], keyword)
        else:  # ограничение уровня таблицы: отдельная строка «CHECK (...)» / «UNIQUE (...)»
            table_loc = mig.table(tid)
            loc = (
                mig.named(r["name"])
                or (table_loc and mig.find(rf"^\s*{keyword}\s*\(", start=table_loc, stop=r"^\);"))
                or table_loc
            )
        nodes.append(
            node(
                oid(r),
                "db_constraint",
                name=r["name"],
                kind=kind,
                table=tid,
                columns=cols,
                definition=r["definition"],
                hash=_h(r["definition"]),
                **_loc(loc),
            )
        )
        edges.append(edge(oid(r), tid, "constrains"))

    for r in raw["indexes"]:
        tid = full(r)
        if tid not in table_ids:
            continue
        kind = ("partial_unique_index" if r["predicate"] else "unique_index") if r["is_unique"] else "index"
        nodes.append(
            node(
                oid(r),
                "db_constraint",
                name=r["name"],
                kind=kind,
                table=tid,
                definition=r["definition"],
                predicate=r["predicate"],
                hash=_h(r["definition"]),
                **_loc(mig.named(r["name"])),
            )
        )
        edges.append(edge(oid(r), tid, "constrains"))

    fn_ids = {(r["schema"], r["name"]): oid(r) for r in raw["functions"]}
    for r in raw["functions"]:
        facts = _function_facts(r["body"], table_ids)
        fid = oid(r)
        nodes.append(
            node(
                fid,
                "db_constraint",
                name=r["name"],
                kind="function",
                schema=r["schema"],
                language=r["language"],
                returns=r["returns"],
                body=r["body"].strip(),
                raises=facts["raises"],
                row_columns=facts["row_columns"],
                hash=_h(r["body"]),
                **_loc(
                    mig.find(
                        rf"CREATE (OR REPLACE )?FUNCTION\s+{re.escape(r['schema'])}\.{re.escape(r['name'])}\b"
                    )
                ),
            )
        )
        for t in facts["tables"]:
            edges.append(edge(fid, t, "reads"))

    for r in raw["triggers"]:
        tid = full(r)
        parts = _trigger_parts(r["definition"])
        tg = oid(r)
        fn = fn_ids.get((r["function_schema"], r["function"]))
        nodes.append(
            node(
                tg,
                "db_constraint",
                name=r["name"],
                kind="trigger",
                table=tid,
                definition=r["definition"],
                function=fn,
                hash=_h(r["definition"]),
                **parts,
                **_loc(mig.find(rf"CREATE TRIGGER\s+{re.escape(r['name'])}\b")),
            )
        )
        edges.append(edge(tg, tid, "on_table"))
        if fn:
            edges.append(edge(tg, fn, "executes"))

    return model_document(GENERATOR, nodes, edges)


def migrate_temp_database(base_url: str) -> tuple[str, str]:
    name = f"erp_knowledge_{uuid.uuid4().hex[:8]}"
    asyncio.run(_admin(base_url, f'CREATE DATABASE "{name}"'))
    url = _with_db(base_url, name)
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    return name, url


async def _admin(base_url: str, sql: str) -> None:
    conn = await asyncpg.connect(_dsn(base_url))
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database-url", help="читать уже мигрированную базу вместо временной")
    args = parser.parse_args()
    if args.database_url:
        raw = asyncio.run(introspect(args.database_url))
    else:
        from libs import settings

        name, url = migrate_temp_database(settings.DATABASE_URL)
        try:
            raw = asyncio.run(introspect(url))
        finally:
            asyncio.run(_admin(settings.DATABASE_URL, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    doc = build(raw)
    write_model("db", doc)
    print(f"knowledge/model/db.json: {len(doc['nodes'])} nodes, {len(doc['edges'])} edges")


if __name__ == "__main__":
    main()
