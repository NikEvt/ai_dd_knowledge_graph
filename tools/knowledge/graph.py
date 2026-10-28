"""Граф знаний: сборка индекса SQLite и запросы к нему (поиск точки входа, context pack, карточки).

Индекс собирается из knowledge/model/*.json, knowledge/rules/*.yaml, knowledge/requirements/*.md,
knowledge/reconciliation.yaml и knowledge/glossary.yaml. У ребра — способ получения (method), у правила —
профиль достоверности (trust, см. trust.py).
Граф небольшой (сотни узлов), поэтому запросы выполняются в памяти; SQLite хранит узлы, рёбра
и полнотекстовый индекс FTS5 со стеммингом (русский и английский) и словарём синонимов.
"""

import heapq
import json
import math
import os
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import snowballstemmer

from tools.knowledge import trust
from tools.knowledge.common import (
    GLOSSARY,
    INDEX,
    MODEL,
    MODEL_FILES,
    RECONCILIATION,
    RULES,
    estimate_tokens,
    load_discrepancies,
    load_glossary,
    load_model,
    load_rules,
    rule_files,
)
from tools.knowledge.requirements import requirement_files, requirement_nodes

# ---------------------------------------------------------------------------- текст и стемминг

_RU = snowballstemmer.stemmer("russian")
_EN = snowballstemmer.stemmer("english")
STOP = set(
    "и в во на с со по к ко о об от до из за для при после перед не ни что как это ли бы же или а но "
    "его её их ее он она они мы вы я все всё весь тот этот так также если то только уже ещё еще где "
    "когда чтобы нужно надо можно нельзя быть был была были есть нет да вызови найди сделай "
    "the a an of to in on for and or is are be by with from at as it this that".split()
)


def words(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text or "")
    return [w for w in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", text.lower().replace("ё", "е")) if w]


def stem(word: str) -> str:
    """Ключ слова для поиска. Русский Snowball нестабилен на коротких основах («архив» -> «арх»,
    «архива» -> «архив»), поэтому берём основу не короче 4 букв и режем до 5."""
    if re.search(r"[а-я]", word):
        s = _RU.stemWord(word)
        return (s if len(s) >= 4 else word)[:5]
    return _EN.stemWord(word)


def stems(text: str) -> list[str]:
    return [stem(w) for w in words(text) if w not in STOP and len(w) > 1]


@cache
def _synonyms() -> list[tuple[list[tuple[str, ...]], set[str]]]:
    """Для каждой записи словаря: фразы (кортежи стемов) и все стемы записи."""
    out = []
    for entry in load_glossary().get("terms", []):
        phrases = [tuple(stems(p)) for p in [*entry.get("ru", []), *entry.get("en", [])]]
        phrases = [p for p in phrases if p]
        out.append((phrases, {s for p in phrases for s in p}))
    return out


def expand(tokens: list[str]) -> list[str]:
    present = set(tokens)
    extra: list[str] = []
    for phrases, all_stems in _synonyms():
        if any(set(p) <= present for p in phrases):
            extra.extend(sorted(all_stems - present))
    return tokens + extra


# ---------------------------------------------------------------------------- сборка индекса

TYPE_BOOST = {
    "rule": 1.6,
    "requirement": 1.5,
    "config": 1.4,
    "job": 1.2,
    "bpm_guard": 1.1,
    "event": 1.1,
    "db_constraint": 1.1,
    "bpm_transition": 1.0,
    "table": 1.0,
    "symbol": 1.0,
    "effect": 0.9,
    "status": 0.7,
    "role": 0.6,
    "service": 0.5,
    "bpm_process": 0.5,
    "test": 0.4,
}


def _rule_refs(value: Any) -> list[str]:
    """Ссылки на узлы в полях правила: event:x, transition:a->b, stage:x, role:x, symbol:..., config:..."""
    out: list[str] = []
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, dict):
            for v in item.values():
                out += _rule_refs(v)
            continue
        if not isinstance(item, str):
            continue
        out += [m.group(2).rstrip(".,;)") for m in _REF.finditer(item)]
        out += [m.group(0).rstrip(".,;)") for m in _TYPED_REF.finditer(item)]
    return out


_REF = re.compile(
    r"\b(event|transition|symbol|config|job|constraint|trigger|index|function|table):([^\s,\]]+)"
)
_TYPED_REF = re.compile(r"\b(?:stage|role|guard|service|effect):[\w.]+")


def rule_graph(rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes, edges = [], []
    for r in rules:
        rid = r.get("id")
        if not rid:
            continue
        start = len(edges)
        nodes.append(
            {
                "id": rid,
                "type": "rule",
                "name": r.get("title", ""),
                "path": r.get("_file"),
                **{k: v for k, v in r.items() if not k.startswith("_") and k != "id"},
            }
        )
        for impl in r.get("implemented_by") or []:
            target = impl.get("symbol") or impl.get("transition") or impl.get("guard")
            if target:
                edges.append(
                    {"src": rid, "dst": target, "type": "implemented_by", "lines": impl.get("lines")}
                )
        for db in r.get("enforced_by_db") or []:
            target = next(iter(db.values())) if isinstance(db, dict) else db
            edges.append({"src": rid, "dst": target, "type": "enforced_by_db"})
        for t in r.get("tested_by") or []:
            edges.append({"src": rid, "dst": t if isinstance(t, str) else t.get("test"), "type": "tested_by"})
        for other in r.get("related") or []:
            edges.append({"src": rid, "dst": other, "type": "related"})
        for c in r.get("config") or []:
            edges.append({"src": rid, "dst": c, "type": "reads_config"})
        for role in r.get("roles") or []:
            edges.append({"src": rid, "dst": f"role:{role}", "type": "performed_by"})
        for ref in _rule_refs([r.get("trigger"), r.get("applies_to"), r.get("effects")]):
            edges.append({"src": rid, "dst": ref, "type": "applies_to"})
        for s in r.get("satisfies") or []:
            edges.append({"src": rid, "dst": s.get("requirement"), "type": "satisfies"})
        for d in r.get("deviates_from") or []:
            edges.append(
                {"src": rid, "dst": d.get("requirement"), "type": "deviates_from", "note": d.get("note")}
            )
        # Связи правила утверждены ИИ; проверены человеком, пока проверенная версия актуальна.
        checked = r.get("status") == "verified" and r.get("verified_fingerprint") == trust.fingerprint(r)
        for e in edges[start:]:
            e["method"] = "human" if checked else "llm"
    return nodes, edges


def search_text(n: dict[str, Any]) -> tuple[str, str]:
    """(заголовок, тело) узла для полнотекстового поиска."""
    t = n["type"]
    title = " ".join([n.get("name") or "", n["id"]])
    body: list[str] = [n.get("doc") or ""]
    if t == "requirement":
        title = f"{n['id']} {n.get('title', '')}"
        body.append(str(n.get("text", "")))
    elif t == "rule":
        title = f"{n['id']} {n.get('title', '')}"
        body += [
            str(n.get("text", "")),
            str(n.get("applies_to", "")),
            str(n.get("trigger", "")),
            str(n.get("effects", "")),
        ]
    elif t == "config":
        body.append(str(n.get("value", ""))[:300])
    elif t in ("symbol", "job"):
        body += [n.get("route") or "", n.get("path") or ""]
        body += [f"{c['condition']} {c['message']}" for c in n.get("checks", [])]
    elif t == "db_constraint":
        body += [n.get("definition") or "", n.get("table") or "", " ".join(n.get("raises", []))]
        body.append(" ".join(n.get("row_columns", [])))
    elif t == "table":
        body.append(" ".join(c["name"] for c in n.get("columns", [])))
    elif t == "event":
        body += n.get("payload", []) + n.get("consumers", []) + n.get("publishers", [])
    elif t == "bpm_transition":
        body += [json.dumps(n.get("variants", []), ensure_ascii=False)]
        body += [glossary_stage(s) for s in n["id"].split("->")]
    elif t == "status":
        body.append(glossary_stage(n["name"]))
    elif t == "role":
        body.append(load_glossary().get("roles", {}).get(n["name"], {}).get("ru", ""))
    elif t == "service":
        body.append(load_glossary().get("services", {}).get(n["name"], ""))
    return title, " ".join(body)


def glossary_stage(name: str) -> str:
    return load_glossary().get("stages", {}).get(name, name)


def _index_inputs() -> list[Path]:
    return [
        *(MODEL / f"{m}.json" for m in MODEL_FILES),
        *rule_files(),
        *requirement_files(),
        RECONCILIATION,
        GLOSSARY,
    ]


def index_is_stale(path: Path = INDEX) -> bool:
    if not path.exists():
        return True
    built = path.stat().st_mtime
    return any(p.exists() and p.stat().st_mtime > built for p in _index_inputs()) or (
        RULES.exists() and RULES.stat().st_mtime > built
    )


def build(path: Path = INDEX) -> dict[str, int]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for name in MODEL_FILES:
        doc = load_model(name)
        for n in doc["nodes"]:
            nodes.setdefault(n["id"], n)
        for e in doc["edges"]:
            e["method"] = trust.edge_method(name, e)
        edges += doc["edges"]
    for n in requirement_nodes():
        nodes[n["id"]] = n
    rnodes, redges = rule_graph(load_rules())
    for n in rnodes:
        nodes[n["id"]] = n
    edges += redges
    edges = [e for e in edges if e["src"] in nodes and e["dst"] in nodes]
    discrepancies = load_discrepancies()
    for n in rnodes:
        n["trust"] = trust.profile(n, nodes, discrepancies)

    tmp = path.with_suffix(f".{os.getpid()}.tmp")  # параллельные сборки не мешают друг другу
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT, path TEXT, line INT, data TEXT
        );
        CREATE TABLE edges (src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL, data TEXT);
        CREATE INDEX ix_edges_src ON edges (src);
        CREATE INDEX ix_edges_dst ON edges (dst);
        CREATE VIRTUAL TABLE search USING fts5(
            id UNINDEXED, type UNINDEXED, title, body, tokenize='unicode61'
        );
        """
    )
    for n in nodes.values():
        db.execute(
            "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?)",
            (
                n["id"],
                n["type"],
                n.get("name"),
                n.get("path"),
                n.get("line"),
                json.dumps(n, ensure_ascii=False),
            ),
        )
        title, body = search_text(n)
        t_stems = expand(stems(title))
        b_stems = expand(stems(body))
        db.execute(
            "INSERT INTO search VALUES (?, ?, ?, ?)",
            (n["id"], n["type"], " ".join(t_stems), " ".join(b_stems)),
        )
    for e in edges:
        db.execute(
            "INSERT INTO edges VALUES (?, ?, ?, ?)",
            (
                e["src"],
                e["dst"],
                e["type"],
                json.dumps({k: v for k, v in e.items() if k not in ("src", "dst", "type")}),
            ),
        )
    db.commit()
    db.close()
    tmp.replace(path)
    return {"nodes": len(nodes), "edges": len(edges)}


# ---------------------------------------------------------------------------- граф в памяти


@dataclass
class Edge:
    src: str
    dst: str
    type: str
    data: dict[str, Any]


@dataclass
class Graph:
    nodes: dict[str, dict[str, Any]]
    out: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    inc: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    db: sqlite3.Connection | None = None

    @classmethod
    def load(cls, path: Path = INDEX, *, rebuild_if_stale: bool = True) -> Graph:
        if rebuild_if_stale and index_is_stale(path):
            build(path)
        db = sqlite3.connect(path, check_same_thread=False)
        nodes = {row[0]: json.loads(row[1]) for row in db.execute("SELECT id, data FROM nodes")}
        g = cls(nodes=nodes, db=db)
        for src, dst, type_, data in db.execute("SELECT src, dst, type, data FROM edges"):
            e = Edge(src, dst, type_, json.loads(data))
            g.out[src].append(e)
            g.inc[dst].append(e)
        return g

    # -- поиск ----------------------------------------------------------------

    def search(
        self,
        text: str,
        limit: int = 8,
        types: tuple[str, ...] | None = None,
        cap: int | None = None,
        keep: Any = None,
    ) -> list[tuple[str, float]]:
        """Полнотекстовый поиск. cap — максимум узлов одного типа, keep(node) — дополнительный фильтр."""
        assert self.db is not None
        q = [s for s in dict.fromkeys(stems(text)) if s]
        if not q:
            return []
        match = " OR ".join(f'"{s}"*' for s in q)
        rows = self.db.execute(
            "SELECT id, type, bm25(search, 0, 0, 3.0, 1.0) FROM search "
            "WHERE search MATCH ? ORDER BY 3 LIMIT 300",
            (match,),
        ).fetchall()
        scored = []
        for id_, type_, rank in rows:
            n = self.nodes.get(id_, {})
            if (types and type_ not in types) or (keep is not None and not keep(n)):
                continue
            boost = TYPE_BOOST.get(type_, 1.0)
            if type_ == "rule" and n.get("status") == "verified":
                boost *= 1.1
            scored.append((id_, -rank * boost))
        scored.sort(key=lambda x: -x[1])
        per_type: dict[str, int] = defaultdict(int)
        out = []
        for id_, score in scored:
            t = self.nodes[id_]["type"]
            type_cap = cap or (4 if t == "rule" else 3)
            if per_type[t] >= type_cap:
                continue
            per_type[t] += 1
            out.append((id_, score))
            if len(out) >= limit:
                break
        return out

    def resolve(self, name: str) -> str | None:
        """ID узла по точному ID, короткому имени, имени класса/таблицы или поиском."""
        name = name.strip()
        if name in self.nodes:
            return name
        for prefix in ("event:", "transition:", "symbol:", "config:", "constraint:", "trigger:", "table:"):
            if name.startswith(prefix) and name[len(prefix) :] in self.nodes:
                return name[len(prefix) :]
        candidates = [i for i in self.nodes if i.endswith(f"::{name}") or i.endswith(f".{name}")]
        if len(candidates) == 1:
            return candidates[0]
        hits = self.search(name, limit=1)
        return hits[0][0] if hits else None

    # -- обход -----------------------------------------------------------------

    def neighbours(self, nid: str) -> list[tuple[Edge, str, bool]]:
        """(ребро, сосед, прямое направление)."""
        return [(e, e.dst, True) for e in self.out.get(nid, [])] + [
            (e, e.src, False) for e in self.inc.get(nid, [])
        ]


# Вес ребра при обходе: (по направлению ребра, против направления).
EDGE_WEIGHT: dict[str, tuple[float, float]] = {
    "publishes": (1.0, 1.0),
    "consumes": (1.0, 1.0),
    "enforced_by_db": (1.0, 0.95),
    "implemented_by": (0.95, 0.9),
    "guarded_by": (0.95, 0.85),
    "executes": (0.95, 0.95),
    "reads_config": (0.9, 0.85),
    "transitions_to": (0.9, 0.75),
    "notifies": (0.85, 0.6),
    "applies_to": (0.85, 0.85),
    "listens": (0.85, 0.85),
    "on_table": (0.6, 0.9),
    "constrains": (0.5, 0.85),
    "writes": (0.75, 0.6),
    "related": (0.7, 0.7),
    "satisfies": (0.5, 0.9),
    "deviates_from": (0.6, 0.9),
    "calls": (0.7, 0.5),
    "tested_by": (0.6, 0.35),
    "maps_to": (0.5, 0.35),
    "refs": (0.5, 0.4),
    "reads": (0.4, 0.3),
    "fk": (0.3, 0.3),
    "depends_on": (0.3, 0.2),
    "from_stage": (0.3, 0.2),
    "to_stage": (0.3, 0.2),
    "allowed_for": (0.3, 0.1),
    "performed_by": (0.3, 0.1),
    "part_of": (0.0, 0.0),
}
# Не возвращаемся тем же типом ребра в обратную сторону: это соседи-«сиблинги» (другие вызывающие
# той же функции, другие публикаторы того же события), а не последствия.
STRUCTURAL = {
    "calls",
    "refs",
    "reads",
    "writes",
    "maps_to",
    "tested_by",
    "depends_on",
    "fk",
    "constrains",
    "on_table",
    "publishes",
    "notifies",
    "satisfies",
    "deviates_from",
}
LEAF_TYPES = {"role", "status", "service", "bpm_process", "test", "effect"}
FANOUT = 4
INFRA_PENALTY = 0.3


def _is_infra(nid: str) -> bool:
    return nid.startswith("libs/")


def _is_reversal(g: Graph, nid: str, came: tuple[str, bool] | None, etype: str, fwd: bool) -> bool:
    if came is None or came != (etype, not fwd):
        return False
    # Обработчик -> другие темы того же обработчика — шум; событие -> другие его подписчики — последствия.
    return etype in STRUCTURAL or (etype == "consumes" and g.nodes[nid]["type"] != "event")


def _constraint_columns(n: dict[str, Any]) -> set[str]:
    return set(n.get("columns") or []) | set(n.get("row_columns") or [])


def _column_factor(g: Graph, table_arrival: tuple[str, bool, frozenset[str]] | None, other: str) -> float:
    """Таблица -> её ограничение: важнее те, что касаются колонок, которые пишет путь."""
    if table_arrival is None:
        return 1.0
    etype, _, cols = table_arrival
    if etype == "reads":
        return 0.4
    n = g.nodes[other]
    ccols = _constraint_columns(n)
    if not ccols and n.get("function") in g.nodes:  # триггер без UPDATE OF: колонки из тела функции
        ccols = _constraint_columns(g.nodes[n["function"]])
    if not cols or not ccols:
        return 0.7
    return 1.0 if ccols & cols else 0.35


def walk(
    g: Graph, start: str, max_depth: int = 4, min_score: float = 0.04
) -> list[tuple[str, float, int, str]]:
    """Best-first обход от узла: (узел, вес, глубина, причина) по убыванию веса.

    Вес = произведение весов рёбер пути (приоритет типа ребра) со штрафом за ветвление.
    Глубина — верхний предел; тема события глубину не добавляет (публикатор -> тема -> подписчик = 1 шаг).
    """
    best: dict[str, tuple[float, int, str]] = {start: (1.0, 0, "")}
    arrived: dict[str, tuple[str, bool] | None] = {start: None}
    arrived_cols: dict[str, frozenset[str]] = {}
    heap = [(-1.0, 0, start)]
    done: set[str] = set()
    while heap:
        neg, depth, nid = heapq.heappop(heap)
        if nid in done:
            continue
        done.add(nid)
        score = -neg
        node_type = g.nodes[nid]["type"]
        if depth >= max_depth or (depth > 0 and (node_type in LEAF_TYPES or _is_infra(nid))):
            continue
        groups: dict[tuple[str, bool], list[tuple[Edge, str]]] = defaultdict(list)
        for e, other, fwd in g.neighbours(nid):
            groups[(e.type, fwd)].append((e, other))
        for (etype, fwd), items in groups.items():
            weight = EDGE_WEIGHT.get(etype, (0.3, 0.3))[0 if fwd else 1]
            if weight <= 0 or _is_reversal(g, nid, arrived.get(nid), etype, fwd):
                continue
            fan = len({o for _, o in items})
            penalty = math.sqrt(min(1.0, FANOUT / fan))
            for e, other in items:
                if other not in g.nodes or other == start:
                    continue
                s = score * weight * penalty * (INFRA_PENALTY if _is_infra(other) else 1.0)
                if node_type == "table" and etype in ("constrains", "on_table") and not fwd and depth > 0:
                    came = arrived.get(nid)
                    s *= _column_factor(
                        g, (*came, arrived_cols.get(nid, frozenset())) if came else None, other
                    )
                if s < min_score:
                    continue
                step = 0 if g.nodes[other]["type"] == "event" else 1
                if other not in best or s > best[other][0]:
                    why = f"{short(nid)} —{etype}→" if fwd else f"—{etype}→ {short(nid)}"
                    if note := trust.edge_note(e.data):
                        why += f" ({note})"
                    best[other] = (s, depth + step, why)
                    arrived[other] = (etype, fwd)
                    arrived_cols[other] = frozenset(e.data.get("columns") or [])
                    heapq.heappush(heap, (-s, depth + step, other))
    return sorted(((n, s, d, why) for n, (s, d, why) in best.items()), key=lambda x: (-x[1], x[0]))


# ---------------------------------------------------------------------------- отображение


def short(nid: str) -> str:
    return nid.split("/")[-1] if "::" in nid else nid


def _clip(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _loc(n: dict[str, Any]) -> str:
    if n.get("path") and n.get("line"):
        return f"{n['path']}:{n['line']}"
    return n.get("path") or ""


def variants_text(n: dict[str, Any]) -> str:
    parts = []
    for v in n.get("variants", []):
        s = "/".join(v["actor"])
        if v.get("kinds"):
            s += f" [{','.join(v['kinds'])}]"
        if v.get("guard"):
            s += f" guard {v['guard']}"
        parts.append(s)
    return "; ".join(parts)


def brief(n: dict[str, Any], detail: int = 1) -> str:
    """Одна строка про узел. detail=0 — минимум, 2 — с подробностями."""
    t, nid = n["type"], n["id"]
    if t == "rule":
        if detail == 0:
            return f"{nid} {n.get('title', '')} ({trust.describe(n, 'short')})"
        if detail >= 2:
            s = f"{nid} {n.get('title', '')} [{trust.describe(n, 'compact')}]"
            return s + (f" — {_clip(n['text'], 260)}" if n.get("text") else "")
        return f"{nid} {n.get('title', '')} — {trust.describe(n)}"
    if t == "requirement":
        s = f"{nid} {n.get('title', '')} — бизнес-требование"
        if n.get("status") != "approved":
            s += f" ({requirement_status_ru(n)})"
        if detail >= 2 and n.get("text"):
            s += f": {_clip(n['text'], 220)}"
        return s
    if t == "config":
        value = n.get("value")
        value = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        s = f"{nid} = {_clip(value, 80)}"
        return s + (f" — {n['doc']}" if n.get("doc") else "")
    if t in ("symbol", "job", "test"):
        s = f"{nid}:{n.get('line', '')}"
        if t == "job":
            s += " (фоновая задача)"
        elif n.get("kind") not in (None, "function", "method", "test"):
            s += f" ({n['kind']})"
        if n.get("route"):
            s += f" {n['route']}"
        if n.get("doc") and detail >= 1:
            s += f" — {_clip(n['doc'], 120)}"
        if detail >= 2 and n.get("checks"):
            checks = "; ".join(
                _clip(f"{c['condition']} ⇒ {c['message']}" if c["condition"] else c["message"], 110)
                for c in n["checks"][:3]
            )
            s += f" | проверки: {checks}"
        return s
    if t == "event":
        pubs = ", ".join(short(p) for p in n.get("publishers", [])) or "—"
        subs = ", ".join(short(c) for c in n.get("consumers", [])) or "—"
        return f"{nid}: {pubs} ⇒ {subs}" + (f" ({n['orphan']})" if n.get("orphan") else "")
    if t == "bpm_transition":
        return f"{nid}: {variants_text(n)} ({_loc(n)})"
    if t == "bpm_guard":
        return f"{nid} → {n.get('implemented_by') or 'НЕ РЕАЛИЗОВАНО'}" + (
            f" — {n['doc']}" if n.get("doc") else ""
        )
    if t == "db_constraint":
        kind = n.get("kind")
        if kind == "trigger":
            s = f"{nid}: {_clip(n.get('definition', '').split(' ', 3)[-1], 120)}"
        elif kind == "function":
            s = f"{nid}(): {'; '.join(repr(r) for r in n.get('raises', [])) or _clip(n.get('body', ''), 100)}"
        else:
            s = f"{nid} ({kind} на {n.get('table')}): {_clip(n.get('definition', ''), 110)}"
        return s + (f" ({_loc(n)})" if detail >= 1 and n.get("path") else "")
    if t == "table":
        cols = ", ".join(c["name"] for c in n.get("columns", []))
        return f"{nid} ({_clip(cols, 140)})" + (f" ({_loc(n)})" if detail >= 2 else "")
    if t == "status":
        return f"{nid} — {glossary_stage(n['name'])}"
    if t == "role":
        return f"{nid} — {load_glossary().get('roles', {}).get(n['name'], {}).get('ru', '')}"
    if t == "service":
        return f"{nid} — {load_glossary().get('services', {}).get(n['name'], '')}"
    if t == "effect":
        return f"{nid} — {n.get('name', '')}"
    return f"{nid} ({t})"


SECTIONS = [
    ("Бизнес-требования", ("requirement",)),
    ("Правила", ("rule",)),
    ("Процесс (BPM): переходы и условия", ("bpm_transition", "bpm_guard")),
    ("События (outbox → подписчики)", ("event",)),
    ("Ограничения БД", ("db_constraint",)),
    ("Таблицы", ("table",)),
    ("Код: точки входа", ("symbol", "job")),
    ("Настройки", ("config",)),
    ("Эффекты: письма, чат", ("effect",)),
    ("Тесты", ("test",)),
]


@dataclass
class Answer:
    text: str
    nodes: list[str]


def impact(g: Graph, node: str, budget_tokens: int = 4000, max_depth: int = 4) -> Answer:
    start = g.resolve(node)
    if start is None:
        return Answer(f"Узел «{node}» не найден. Вызови find_entry с текстом задачи.", [])
    ranked = walk(g, start, max_depth=max_depth)
    header = (
        f"# Context pack: {start}\n(бюджет ~{budget_tokens} токенов, глубина ≤ {max_depth}; "
        "курсивом — связь, по которой найден узел: от кода, БД и процесса извлечена из них, от правила (R-…) "
        "указана ИИ, если не помечено иначе;\nу правила в [ ] — бизнес-требование и насколько ему верить, "
        "полностью — rule(id))\n"
    )
    used = estimate_tokens(header) + 150
    chosen: list[tuple[str, str]] = []
    skipped = 0
    for nid, score, depth, why in ranked:
        n = g.nodes[nid]
        if n["type"] in ("status", "role", "service", "bpm_process"):
            continue
        detail = 2 if score >= 0.5 or n["type"] == "rule" else 1
        line = f"- {brief(n, detail)}"
        if depth >= 1 and n["type"] not in ("rule",):
            line += f"  _{why}_"
        cost = estimate_tokens(line) + 1
        if used + cost > budget_tokens:
            skipped += 1
            continue
        used += cost
        chosen.append((nid, line))
    while True:
        text = _render_pack(g, header, chosen, skipped)
        if estimate_tokens(text) <= budget_tokens or not chosen:
            return Answer(text, [n for n, _ in chosen])
        chosen.pop()
        skipped += 1


def _render_pack(g: Graph, header: str, chosen: list[tuple[str, str]], skipped: int) -> str:
    by_type: dict[str, list[str]] = defaultdict(list)
    for nid, line in chosen:
        by_type[g.nodes[nid]["type"]].append(line)
    parts = [header]
    for title, types in SECTIONS:
        lines = [ln for t in types for ln in by_type.get(t, [])]
        if lines:
            parts.append(f"\n## {title}\n" + "\n".join(lines))
    rules = [g.nodes[n] for n, _ in chosen if g.nodes[n]["type"] == "rule" and g.nodes[n].get("trust")]
    notes = trust_summary(rules)
    if skipped:
        notes.append(
            f"Не вошло по бюджету: {skipped} узлов "
            "(увеличь budget_tokens или вызови impact для узла из списка)."
        )
    if notes:
        parts.append("\n## Пометки\n" + "\n".join(f"- {x}" for x in notes))
    return "\n".join(parts) + "\n"


def requirement_status_ru(n: dict[str, Any]) -> str:
    return {
        "proposed": "черновик требования, не утверждено",
        "approved": "утверждено",
        "cancelled": "отменено",
    }.get(n.get("status", "proposed"), "")


def trust_summary(rules: list[dict[str, Any]]) -> list[str]:
    """Сводка по правилам пакета: на что опереться, что сверить с кодом, что уточнить у пользователя."""
    groups: dict[str, list[str]] = defaultdict(list)
    for r in rules:
        t = r["trust"]
        groups[trust.action(t)].append(r["id"])
    out = []
    if groups["rely"]:
        out.append(f"Можно опереться: {len(groups['rely'])} правил(а).")
    if groups["check"]:
        out.append(
            f"Сверь с кодом, прежде чем опираться (нет тестов или код менялся): {', '.join(groups['check'])}."
        )
    if groups["verify"]:
        out.append(f"Не опирайся без проверки кода (ссылок на код нет): {', '.join(groups['verify'])}.")
    if groups["ask"]:
        out.append(
            "Код расходится с бизнес-требованием или есть открытый вопрос (причина — у правила) — "
            "уточни у пользователя: "
            f"{', '.join(groups['ask'])}."
        )
    return out


def find_entry(g: Graph, task_text: str, limit: int = 8) -> Answer:
    hits = g.search(task_text, limit=limit)
    if not hits:
        return Answer("Ничего не найдено. Переформулируй задачу через сущности: заявка, счёт, площадка…", [])
    lines = [f"Точки входа для «{_clip(task_text, 80)}» (передай ID в impact):"]
    for i, (nid, _) in enumerate(hits, 1):
        n = g.nodes[nid]
        lines.append(f"{i}. [{n['type']}] {brief(n, 1)}")
    return Answer("\n".join(lines) + "\n", [nid for nid, _ in hits])


def rule_card(g: Graph, rule_id: str) -> Answer:
    rid = rule_id.strip()
    n = g.nodes.get(rid)
    if n is None or n["type"] != "rule":
        hits = g.search(rid, limit=5, types=("rule",))
        if not hits:
            return Answer(f"Правило {rid} не найдено.", [])
        alt = "\n".join(f"- {brief(g.nodes[h], 0)}" for h, _ in hits)
        return Answer(f"Правило {rid} не найдено. Похожие:\n{alt}\n", [h for h, _ in hits])
    ids = [rid]
    t = n["trust"]
    out = [f"# {rid} {n.get('title', '')}", "", f"{trust.kind_text(t)} · {trust.verdict(t)}", ""]
    why = []
    for e in g.out.get(rid, []):
        if e.type in ("satisfies", "deviates_from") and e.dst in g.nodes:
            ids.append(e.dst)
            req = g.nodes[e.dst]
            line = f"- {brief(req, 2)}"
            if e.type == "deviates_from":
                line += f"\n  ⚠ код расходится с требованием: {_clip(e.data.get('note') or '', 300)}"
            why.append(line)
    out += [
        "## Почему (бизнес-требования)",
        *(why or ["- бизнес-требования нет: правило описывает поведение кода"]),
    ]
    out += ["", "## Как (правило)", str(n.get("text", "")).strip()]
    for key in ("kind", "applies_to", "trigger", "effects", "roles"):
        if n.get(key):
            out.append(
                f"- {key}: {n[key] if isinstance(n[key], str) else json.dumps(n[key], ensure_ascii=False)}"
            )
    out += ["", "## Достоверность", *trust_lines(t, n)]
    linked = (
        "проверены человеком"
        if any(e.data.get("method") == "human" for e in g.out.get(rid, []))
        else "указаны ИИ, существование проверяет CI"
    )
    out += ["", f"## Где (ссылки {linked})"]
    sections = [
        ("Реализация", "implemented_by"),
        ("Ограничения БД", "enforced_by_db"),
        ("Настройки", "reads_config"),
        ("Тесты", "tested_by"),
        ("Связанные правила", "related"),
        ("Затрагивает", "applies_to"),
    ]
    for title, etype in sections:
        lines = []
        for e in g.out.get(rid, []):
            if e.type != etype or e.dst not in g.nodes:
                continue
            ids.append(e.dst)
            target = g.nodes[e.dst]
            line = f"- {brief(target, 1)}"
            if e.data.get("lines"):
                line += f" [строки {e.data['lines']}]"
            if etype == "implemented_by":
                stored = next(
                    (
                        i.get("hash")
                        for i in n.get("implemented_by", [])
                        if e.dst in (i.get("symbol"), i.get("transition"))
                    ),
                    None,
                )
                if stored and target.get("hash") and stored != target["hash"]:
                    line += " ⚠ код изменился после фиксации правила (drift)"
            lines.append(line)
        if etype == "related":
            lines += [
                f"- {brief(g.nodes[e.src], 0)}"
                for e in g.inc.get(rid, [])
                if e.type == "related" and e.src in g.nodes
            ]
        if lines:
            out += ["", f"### {title}", *lines]
    out.append(f"\nИсточник: {n.get('path')}")
    return Answer("\n".join(out) + "\n", list(dict.fromkeys(ids)))


def trust_lines(t: dict[str, Any], n: dict[str, Any]) -> list[str]:
    """Оси достоверности правила словами — для карточки."""
    a = t["anchors"]
    out = [f"- происхождение: {trust.origin_text(t)}" + (f" ({t['source']})" if t.get("source") else "")]
    v = t["verification"]
    if v is None:
        out.append("- проверка человеком: не проводилась")
    else:
        who = f"{v.get('by') or 'кто — не записано'}, {v.get('at') or 'дата не записана'}"
        state = {
            "current": "проверенная версия совпадает с текущей",
            "outdated": "⚠ правило меняли после проверки",
            "unpinned": "версия при проверке не зафиксирована",
        }[v["state"]]
        out.append(f"- проверка человеком: {who}; {state}")
    fresh = {
        "current": "код и требования не менялись после фиксации правила",
        "code_changed": f"⚠ код изменился после фиксации правила: {', '.join(map(str, t['drifted']))}",
        "requirement_changed": f"⚠ изменилось бизнес-требование: {', '.join(t['requirement_changed'])}",
        "verified_outdated": "⚠ правило меняли после проверки человеком",
    }[t["freshness"]]
    out.append(
        f"- актуальность: {fresh}" + (f" (suspect с {n['suspect_since']})" if n.get("suspect_since") else "")
    )
    out.append(f"- опоры: код — {a['code']}, ограничения БД — {a['db']}, тесты — {a['tests']}")
    amb = t["ambiguity"]
    for d in amb["discrepancies"]:
        question = _clip(d.get("question") or "", 220)
        out.append(f"- ⚠ открытое расхождение {d['id']} ({d.get('severity') or '?'}): {question}")
    for q in amb["open_questions"]:
        out.append(f"- ⚠ открытый вопрос: {_clip(q, 220)}")
    for c in amb["caveats"]:
        out.append(f"- оговорка: {_clip(c, 300)}")
    if amb["missing"]:
        out.append(f"- ⚠ ссылки не найдены в модели: {', '.join(amb['missing'])}")
    if amb["cancelled_requirements"]:
        out.append(f"- ⚠ реализует отменённые требования: {', '.join(amb['cancelled_requirements'])}")
    return out


def requirement_card(g: Graph, req_id: str) -> Answer:
    rid = req_id.strip()
    n = g.nodes.get(rid)
    if n is None or n["type"] != "requirement":
        hits = g.search(rid, limit=5, types=("requirement",))
        if not hits:
            return Answer(f"Требование {rid} не найдено.", [])
        alt = "\n".join(f"- {brief(g.nodes[h], 1)}" for h, _ in hits)
        return Answer(f"Требование {rid} не найдено. Похожие:\n{alt}\n", [h for h, _ in hits])
    meta = [requirement_status_ru(n), f"владелец: {n.get('owner') or '—'}"]
    if n.get("schema"):
        meta.append(f"схема: {n['schema']}")
    out = [
        f"# {rid} {n.get('title', '')}",
        "",
        f"бизнес-требование · {' · '.join(meta)}",
        "",
        n.get("text", ""),
    ]
    ids = [rid]
    impl = [e.src for e in g.inc.get(rid, []) if e.type == "satisfies" and e.src in g.nodes]
    dev = [e for e in g.inc.get(rid, []) if e.type == "deviates_from" and e.src in g.nodes]
    out += ["", "## Реализуют правила"]
    out += [f"- {brief(g.nodes[r], 1)}" for r in impl] or [
        "- ⚠ правил нет: требование в коде не реализовано (или реализующее правило не связано)"
    ]
    ids += impl
    if dev:
        out += ["", "## Расходятся с требованием"]
        for e in dev:
            ids.append(e.src)
            out.append(f"- {e.src} {g.nodes[e.src].get('title', '')}: {_clip(e.data.get('note') or '', 260)}")
    opened = [
        d
        for d in load_discrepancies()
        if d.get("status", "open") == "open" and rid in (d.get("requirements") or [])
    ]
    if opened:
        out += ["", "## Открытые расхождения (нужно решение)"]
        out += [f"- {d['id']} {d.get('title', '')}: {_clip(d.get('question') or '', 220)}" for d in opened]
    if n.get("status") == "cancelled" and impl:
        out += ["", "⚠ требование отменено, но правила его реализуют — уточни, нужно ли поведение."]
    out.append(f"\nИсточник: {n.get('path')}:{n.get('line')}")
    return Answer("\n".join(out) + "\n", list(dict.fromkeys(ids)))


def _table_for(g: Graph, name: str) -> str | None:
    if name in g.nodes and g.nodes[name]["type"] == "table":
        return name
    tables = {tid.split(".")[-1]: tid for tid, n in g.nodes.items() if n["type"] == "table"}
    query = tuple(stems(name))
    for entry in load_glossary().get("terms", []):  # «заявка» -> application(s) -> applications.applications
        if any(tuple(stems(ru)) == query for ru in entry.get("ru", [])):
            for en in entry.get("en", []):
                for candidate in (en, en + "s"):
                    if candidate in tables:
                        return tables[candidate]
    nid = g.resolve(name)
    if nid and g.nodes[nid]["type"] == "table":
        return nid
    if nid and g.nodes[nid].get("kind") == "orm_model":
        return g.nodes[nid].get("table")
    lowered = name.lower()
    for tid in g.nodes:
        if g.nodes[tid]["type"] == "table" and (tid.split(".")[-1] in (lowered, lowered + "s")):
            return tid
    hits = g.search(name, limit=1, types=("table",))
    return hits[0][0] if hits else None


def entity_card(g: Graph, name: str) -> Answer:
    tid = _table_for(g, name)
    if tid is None:
        return Answer(f"Сущность «{name}» не найдена.", [])
    t = g.nodes[tid]
    ids = [tid]
    out = [f"# {tid}", f"Миграция: {_loc(t)}", "", "## Поля"]
    for c in t.get("columns", []):
        flags = [] if c.get("nullable") else ["NOT NULL"]
        if c["name"] in (t.get("primary_key") or []):
            flags.append("PK")
        out.append(f"- {c['name']}: {c['type']} {' '.join(flags)}".rstrip())
    fks = [e for e in g.out.get(tid, []) if e.type == "fk"]
    fks_in = [e for e in g.inc.get(tid, []) if e.type == "fk"]
    if fks or fks_in:
        out += ["", "## Связи (FK)"]
        out += [f"- {e.data.get('columns')} → {e.dst}" for e in fks]
        out += [f"- {e.src}.{e.data.get('columns')} → сюда" for e in fks_in]
    cons = [g.nodes[e.src] for e in g.inc.get(tid, []) if e.type in ("constrains", "on_table")]
    if cons:
        out += ["", "## Ограничения и триггеры"]
        for c in sorted(cons, key=lambda c: (c.get("kind", ""), c["id"])):
            ids.append(c["id"])
            out.append(f"- {brief(c, 1)}")
            if c.get("function") and c["function"] in g.nodes:
                ids.append(c["function"])
                out.append(f"  - {brief(g.nodes[c['function']], 0)}")
    orm = [g.nodes[e.src] for e in g.inc.get(tid, []) if e.type == "maps_to"]
    if orm:
        out += ["", "## ORM", *(f"- {brief(o, 0)}" for o in orm)]
        ids += [o["id"] for o in orm]
    if any(c["name"] == "stage" for c in t.get("columns", [])):
        procs = [n for n in g.nodes.values() if n["type"] == "bpm_process" and n.get("table") == tid]
        for p in procs:
            out += ["", f"## Этапы (процесс {p['name']}, bpm/application_process.yaml)"]
            for kind, path in p.get("paths", {}).items():
                out.append(f"- {kind}: {' → '.join(path)}")
    writers = sorted({e.src for e in g.inc.get(tid, []) if e.type == "writes"})
    if writers:
        out += ["", "## Пишут (код)"]
        for w in writers[:25]:
            cols = sorted(
                {
                    c
                    for e in g.inc[tid]
                    if e.type == "writes" and e.src == w
                    for c in e.data.get("columns") or []
                }
            )
            out.append(f"- {w}" + (f" [{', '.join(cols)}]" if cols else ""))
            ids.append(w)
        if len(writers) > 25:
            out.append(f"- … ещё {len(writers) - 25}")
    rules = sorted(
        {
            e.src
            for target in ids
            for e in g.inc.get(target, [])
            if e.type in ("enforced_by_db", "applies_to", "implemented_by")
            and g.nodes.get(e.src, {}).get("type") == "rule"
        }
    )
    if rules:
        out += ["", "## Правила"]
        for r in rules:
            out.append(f"- {brief(g.nodes[r], 0)}")
            ids.append(r)
    return Answer("\n".join(out) + "\n", list(dict.fromkeys(ids)))


def _roles_of(g: Graph, n: dict[str, Any]) -> list[tuple[str, str]]:
    """Роли по именам параметров функции — предположение, не проверка доступа: (роль, параметр)."""
    params = (n.get("signature") or "").strip("()").replace("*", "").split(", ")
    roles = []
    for role, info in load_glossary().get("roles", {}).items():
        roles += [(role, p) for p in info.get("params", []) if p in params][:1]
    return roles


def who_can(g: Graph, action: str) -> Answer:
    hits = g.search(
        action,
        limit=8,
        types=("symbol", "job", "bpm_transition", "rule"),
        cap=5,
        keep=lambda n: (
            n.get("kind") not in ("orm_model", "class", "route", "module")
            and not (n.get("type") == "rule" and not n.get("roles"))
        ),
    )
    if not hits:
        return Answer(f"Действие «{action}» не найдено.", [])
    roles_ru = {k: v.get("ru", k) for k, v in load_glossary().get("roles", {}).items()}
    out = [f"# Кто может: «{_clip(action, 80)}»"]
    ids: list[str] = []
    for nid, _ in hits:
        n = g.nodes[nid]
        t = n["type"]
        if t == "rule":
            ids.append(nid)
            who = ", ".join(roles_ru.get(r, r) for r in n["roles"])
            out.append(
                f"\n## {n['id']} {n.get('title', '')}\n- {trust.describe(n)}\n- роли (по правилу): {who}"
                f"\n- {_clip(n.get('text', ''), 300)}"
            )
        elif t == "bpm_transition":
            ids.append(nid)
            out.append(f"\n## Переход {nid}")
            for v in n.get("variants", []):
                who = ", ".join(roles_ru.get(a, a) for a in v["actor"])
                cond = []
                if v.get("kinds"):
                    cond.append(f"виды: {', '.join(v['kinds'])}")
                if v.get("guard"):
                    cond.append(f"условие: {v['guard']}")
                out.append(f"- {who}" + (f" ({'; '.join(cond)})" if cond else ""))
        elif t in ("symbol", "job"):
            ids.append(nid)
            roles = _roles_of(g, n)
            transitions = [e for e in g.out.get(nid, []) if e.type == "transitions_to"]
            out.append(f"\n## {nid}:{n.get('line')}" + (f" — {n['doc']}" if n.get("doc") else ""))
            for role, param in roles:
                out.append(
                    f"- исполнитель (предположение по имени параметра {param}): {roles_ru.get(role, role)}"
                )
            if t == "job" or n.get("kind") in ("consumer", "orm_listener"):
                out.append("- исполнитель: система (событие или фоновая задача)")
            helpers = [
                g.nodes[e.dst]
                for e in g.out.get(nid, [])
                if e.type == "calls" and g.nodes.get(e.dst, {}).get("name", "").startswith("_")
            ]
            for c in [*n.get("checks", []), *(c for h in helpers for c in h.get("checks", []))]:
                if c["error"] == "NotFound":
                    continue
                label = "доступ" if c["error"] == "AccessDenied" else "условие"
                cond = f"{c['condition']} ⇒ " if c["condition"] else ""
                out.append(f"- {label}: {_clip(cond + c['message'], 200)} (строка {c['line']})")
            for e in transitions[:6]:
                ids.append(e.dst)
                out.append(f"- переход {e.dst} как {e.data.get('actor')}: {variants_text(g.nodes[e.dst])}")
            for e in g.inc.get(nid, []):
                if e.type == "implemented_by" and g.nodes.get(e.src, {}).get("type") == "rule":
                    r = g.nodes[e.src]
                    ids.append(r["id"])
                    roles_r = ", ".join(roles_ru.get(x, x) for x in r.get("roles") or [])
                    out.append(
                        f"- правило {brief(r, 0)}" + (f" — роли по правилу: {roles_r}" if roles_r else "")
                    )
    return Answer("\n".join(out) + "\n", list(dict.fromkeys(ids)))


# ---------------------------------------------------------------------------- срез модуля для LLM


def module_slice(g: Graph, prefix: str) -> str:
    """Срез графа по модулю (например services/billing) — вход для LLM-извлечения правил."""
    own = sorted(
        (
            n
            for n in g.nodes.values()
            if (n.get("path") or "").startswith(prefix) and n["type"] in ("symbol", "job", "config")
        ),
        key=lambda n: (n.get("path"), n.get("line") or 0),
    )
    own_ids = {n["id"] for n in own}
    out = [f"# Срез графа: {prefix}", ""]
    out.append("## Символы модуля (файл:строка, вид, проверки, связи)")
    tables: set[str] = set()
    events: set[str] = set()
    transitions: set[str] = set()
    tests: set[str] = set()
    for n in own:
        out.append(f"\n### {n['id']} (строки {n.get('line')}-{n.get('end_line', n.get('line'))})")
        if n["type"] == "config":
            out.append(
                f"- настройка = {json.dumps(n.get('value'), ensure_ascii=False)}"
                + (f" — {n['doc']}" if n.get("doc") else "")
            )
        else:
            meta = [n.get("kind", "")]
            if n.get("route"):
                meta.append(n["route"])
            if n.get("listens_for"):
                meta.append(f"слушатель ORM {n['listens_for']}")
            out.append(f"- {', '.join(m for m in meta if m)}" + (f" — {n['doc']}" if n.get("doc") else ""))
            for c in n.get("checks", []):
                cond = f"если {c['condition']}: " if c["condition"] else ""
                out.append(f"- проверка (строка {c['line']}): {cond}{c['error']}({c['message']!r})")
        for e in g.out.get(n["id"], []):
            if e.type in ("part_of",):
                continue
            extra = []
            if e.data.get("lines"):
                extra.append(f"строки {e.data['lines']}")
            for k in ("columns", "condition", "actor", "inferred", "dynamic", "registered_in"):
                if e.data.get(k):
                    extra.append(f"{k}={e.data[k]}")
            out.append(f"- {e.type} → {e.dst}" + (f" ({'; '.join(map(str, extra))})" if extra else ""))
            if e.type in ("reads", "writes"):
                tables.add(e.dst)
            elif e.type in ("publishes", "consumes"):
                events.add(e.dst)
            elif e.type == "transitions_to":
                transitions.add(e.dst)
            elif e.type == "tested_by":
                tests.add(e.dst)
        for e in g.inc.get(n["id"], []):
            if e.type in ("calls", "refs", "reads_config") and e.src not in own_ids:
                out.append(f"- вызывается из {e.src}")
            elif e.type == "implemented_by" and g.nodes.get(e.src, {}).get("type") == "bpm_guard":
                out.append(f"- реализует условие процесса {e.src}")
    if events:
        out += ["", "## События модуля: все публикаторы и подписчики"]
        out += [f"- {brief(g.nodes[ev], 1)}" for ev in sorted(events) if ev in g.nodes]
    if transitions:
        out += ["", "## Переходы процесса, которые выполняет модуль"]
        out += [f"- {brief(g.nodes[t], 1)}" for t in sorted(transitions)]
    if tables:
        out += ["", "## Таблицы и их ограничения в БД"]
        for t in sorted(tables):
            if t not in g.nodes:
                continue
            out.append(f"- {brief(g.nodes[t], 1)}")
            for e in g.inc.get(t, []):
                if e.type in ("constrains", "on_table"):
                    c = g.nodes[e.src]
                    out.append(f"  - {brief(c, 1)}")
                    if c.get("function") in g.nodes:
                        f = g.nodes[c["function"]]
                        out.append(f"    - функция {f['id']}:\n```sql\n{f.get('body', '')}\n```")
    if tests:
        out += ["", "## Тесты, вызывающие код модуля"]
        out += [f"- {t}" for t in sorted(tests)]
    return "\n".join(out) + "\n"
