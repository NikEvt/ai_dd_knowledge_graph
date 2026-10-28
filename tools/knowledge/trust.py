"""Достоверность фактов модели знаний.

Статус правила (draft/verified/suspect) — этап ревью. Достоверность — отдельный профиль, который считается
при сборке индекса и руками не пишется:

- происхождение: откуда факт (код, каталог БД, BPM, ИИ, человек) — `provenance` правила, слой модели;
- способ получения: ast, pg_catalog, yaml (извлечено), heuristic (предположение), llm, human — у рёбер;
- актуальность: код и бизнес-требования не менялись после фиксации правила и после проверки человеком;
- неоднозначность: открытые расхождения D-xx, `deviates_from`, оговорки, открытые вопросы, битые ссылки;
- соответствие требованию: реализует бизнес-требование, расходится с ним или требования нет.

Итог — уровень (худший побеждает): contested > stale > unanchored > weak > supported > confirmed.
Коды уровней — для машин (фильтры, CI, docs). В контекст ИИ уходят фразы из describe(): что это за правило,
насколько ему верить и что делать агенту.
"""

import hashlib
import json
from typing import Any

LEVELS = ("contested", "stale", "unanchored", "weak", "supported", "confirmed")
LEVEL_RU = {
    "contested": "расхождение с требованием или открытый вопрос",
    "stale": "устарело",
    "unanchored": "без ссылок на код",
    "weak": "без тестов",
    "supported": "подкреплено кодом и тестами",
    "confirmed": "проверено человеком",
}
METHOD_BY_LAYER = {"db": "pg_catalog", "code": "ast", "events": "ast", "bpm": "yaml"}
ANCHOR_KEYS = ("symbol", "transition", "guard", "constraint", "trigger", "index", "function")
# Служебные поля: не входят в смысл правила (сравнение с базовой веткой, отпечаток проверки).
SERVICE_FIELDS = {
    "hash",
    "status",
    "suspect_since",
    "suspect_reason",
    "verified_by",
    "verified_at",
    "verified_fingerprint",
}


def edge_method(layer: str, e: dict[str, Any]) -> str:
    if e.get("inferred") or e.get("dynamic"):
        return "heuristic"
    return METHOD_BY_LAYER.get(layer, "ast")


def anchor(entry: Any) -> str | None:
    if isinstance(entry, dict):
        for key in (*ANCHOR_KEYS, "requirement"):
            if entry.get(key):
                return entry[key]
    return None


# Поля, которые сборка индекса добавляет узлу правила; в YAML их нет.
NODE_FIELDS = {"type", "name", "path", "trust"}


def semantic(rule: dict[str, Any]) -> dict[str, Any]:
    """Содержимое правила без служебных полей и хэшей."""
    skip = SERVICE_FIELDS | NODE_FIELDS
    clean = {k: v for k, v in rule.items() if k not in skip and not k.startswith("_")}
    for key in ("implemented_by", "enforced_by_db", "satisfies"):
        if clean.get(key):
            clean[key] = [
                {k: v for k, v in e.items() if k != "hash"} if isinstance(e, dict) else e for e in clean[key]
            ]
    return clean


def fingerprint(rule: dict[str, Any]) -> str:
    """Отпечаток проверенной версии: смысл правила + хэши кода, БД и требований, на которые оно ссылается."""
    hashes = sorted(
        f"{anchor(e)}={e.get('hash')}"
        for key in ("implemented_by", "enforced_by_db", "satisfies")
        for e in rule.get(key) or []
        if isinstance(e, dict)
    )
    data = json.dumps({"rule": semantic(rule), "anchors": hashes}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def _open_discrepancies(rid: str, discrepancies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [d for d in discrepancies if d.get("status", "open") == "open" and rid in (d.get("rules") or [])]


def profile(
    rule: dict[str, Any], nodes: dict[str, dict[str, Any]], discrepancies: list[dict[str, Any]]
) -> dict[str, Any]:
    """Профиль достоверности правила по данным графа (nodes — узлы с текущими хэшами кода, БД, требований)."""
    code = [e for e in rule.get("implemented_by") or [] if isinstance(e, dict)]
    db = [e for e in rule.get("enforced_by_db") or [] if isinstance(e, dict)]
    satisfies = [e for e in rule.get("satisfies") or [] if isinstance(e, dict)]
    deviates = [e for e in rule.get("deviates_from") or [] if isinstance(e, dict)]
    tests = rule.get("tested_by") or []

    drifted, missing = [], []
    for e in code + db:
        target = anchor(e)
        cur = nodes.get(target or "")
        if cur is None:
            missing.append(target)
        elif e.get("hash") and cur.get("hash") and e["hash"] != cur["hash"]:
            drifted.append(target)
    req_changed = []
    for e in satisfies:
        cur = nodes.get(e["requirement"])
        if cur is None:
            missing.append(e["requirement"])
        elif e.get("hash") and e["hash"] != cur.get("hash"):
            req_changed.append(e["requirement"])

    status = rule.get("status", "draft")
    reason = rule.get("suspect_reason")
    if status == "suspect" and not reason:
        reason = "code_changed"
    if status == "suspect" and reason == "code_changed" and not drifted:
        drifted = ["код"]
    if status == "suspect" and reason == "requirement_changed" and not req_changed:
        req_changed = [e["requirement"] for e in satisfies] or ["требование"]

    verification = None
    if status == "verified":
        pinned = rule.get("verified_fingerprint")
        state = "unpinned" if not pinned else ("current" if pinned == fingerprint(rule) else "outdated")
        verification = {"by": rule.get("verified_by"), "at": rule.get("verified_at"), "state": state}

    if drifted:
        freshness = "code_changed"
    elif req_changed:
        freshness = "requirement_changed"
    elif verification and verification["state"] == "outdated":
        freshness = "verified_outdated"
    else:
        freshness = "current"

    opened = _open_discrepancies(rule["id"], discrepancies)
    cancelled = [
        e["requirement"] for e in satisfies if nodes.get(e["requirement"], {}).get("status") == "cancelled"
    ]
    ambiguity = {
        "discrepancies": [
            {"id": d["id"], "severity": d.get("severity"), "question": d.get("question")} for d in opened
        ],
        "deviates": [{"requirement": e["requirement"], "note": e.get("note", "")} for e in deviates],
        "caveats": list(rule.get("caveats") or []),
        "open_questions": list(rule.get("open_questions") or []),
        "missing": [m for m in missing if m],
        "cancelled_requirements": cancelled,
    }

    if deviates or opened or ambiguity["open_questions"] or cancelled:
        level = "contested"
    elif freshness != "current":
        level = "stale"
    elif not code and not db:
        level = "unanchored"
    elif verification and verification["state"] == "current":
        level = "confirmed"
    elif tests and not missing:
        level = "supported"
    else:
        level = "weak"

    provenance = rule.get("provenance") or {}
    return {
        "level": level,
        "origin": provenance.get("origin", "llm"),
        "source": provenance.get("source"),
        "verification": verification,
        "freshness": freshness,
        "drifted": drifted,
        "requirement_changed": req_changed,
        "anchors": {"code": len(code), "db": len(db), "tests": len(tests)},
        "requirements": [e["requirement"] for e in satisfies],
        "ambiguity": ambiguity,
    }


# ---------------------------------------------------------------------------- фразы для ИИ


def _clip(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _plural_tests(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} тестом"
    return f"{n} тестами"


def _support(anchors: dict[str, int]) -> str:
    parts = []
    if anchors["code"]:
        parts.append("кодом")
    if anchors["db"]:
        parts.append("ограничением БД")
    if anchors["tests"]:
        parts.append(_plural_tests(anchors["tests"]))
    return ", ".join(parts[:-1]) + (" и " if len(parts) > 1 else "") + parts[-1] if parts else ""


def origin_text(t: dict[str, Any]) -> str:
    return {"llm": "извлечено ИИ из кода", "human": "записано человеком"}.get(t["origin"], t["origin"])


def verdict(t: dict[str, Any]) -> str:
    """Насколько верить и что делать — одна фраза без кодов."""
    level, amb = t["level"], t["ambiguity"]
    if level == "contested":
        if amb["deviates"]:
            d = amb["deviates"][0]
            ds = ", ".join(x["id"] for x in amb["discrepancies"])
            return (
                f"⚠ код расходится с требованием {d['requirement']}"
                + (f" ({ds})" if ds else "")
                + f": {_clip(d['note'], 140)} — уточни у пользователя"
            )
        if amb["discrepancies"]:
            d = amb["discrepancies"][0]
            return (
                f"⚠ открытый вопрос {d['id']}: {_clip(d.get('question') or '', 140)} — уточни у пользователя"
            )
        if amb["cancelled_requirements"]:
            return (
                f"⚠ реализует отменённое требование {', '.join(amb['cancelled_requirements'])}"
                " — уточни у пользователя, нужно ли поведение"
            )
        return f"⚠ открытый вопрос: {_clip(amb['open_questions'][0], 140)} — уточни у пользователя"
    if level == "stale":
        if t["freshness"] == "code_changed":
            where = ", ".join(str(x) for x in t["drifted"][:2])
            return f"⚠ код изменился после фиксации правила ({where}) — сверь с кодом"
        if t["freshness"] == "requirement_changed":
            return (
                f"⚠ бизнес-требование {', '.join(t['requirement_changed'])} изменилось после фиксации правила"
                " — проверь реализацию"
            )
        return "⚠ правило правили после проверки человеком — сверь с кодом"
    if level == "unanchored":
        return f"{origin_text(t)}, ссылок на код нет — не опирайся без проверки"
    if level == "weak":
        return f"{origin_text(t)}, есть код, нет тестов — сверь с кодом"
    if level == "supported":
        return f"{origin_text(t)}, подкреплено {_support(t['anchors'])}"
    v = t["verification"] or {}
    return f"проверено человеком {v.get('at') or ''}".rstrip() + ", с тех пор не менялось"


def kind_text(t: dict[str, Any]) -> str:
    """Что это за правило относительно бизнес-требований."""
    if t["requirements"]:
        return "реализует требование " + ", ".join(t["requirements"])
    if t["ambiguity"]["deviates"]:
        return "по требованию " + ", ".join(d["requirement"] for d in t["ambiguity"]["deviates"])
    return "поведение кода без бизнес-требования"


def reason_short(t: dict[str, Any]) -> str:
    """Короткая причина риска: для компактной пометки и сводки пакета."""
    amb = t["ambiguity"]
    if t["level"] == "contested":
        if amb["deviates"]:
            ds = ", ".join(x["id"] for x in amb["discrepancies"])
            return f"расходится с {amb['deviates'][0]['requirement']}" + (f" ({ds})" if ds else "")
        if amb["discrepancies"]:
            return f"открыт вопрос {amb['discrepancies'][0]['id']}"
        if amb["cancelled_requirements"]:
            return "реализует отменённое требование"
        return "открыт вопрос"
    if t["level"] == "stale":
        return {
            "code_changed": "код изменился после фиксации правила",
            "requirement_changed": "требование изменилось после фиксации правила",
            "verified_outdated": "правило меняли после проверки человеком",
        }[t["freshness"]]
    return LEVEL_RU[t["level"]]


COMPACT = {
    "confirmed": "проверено человеком",
    "supported": "подкреплено кодом и тестами",
    "weak": "нет тестов — сверь с кодом",
    "unanchored": "ссылок на код нет — не опирайся без проверки",
}


def describe(n: dict[str, Any], form: str = "full") -> str:
    """Пометка правила для контекста ИИ.

    full — карточки и find_entry: тип правила, вердикт, оговорка;
    compact — пакет impact: требования и вердикт в несколько слов (полный текст — в rule(id));
    short — списки: только вердикт.
    """
    t = n.get("trust")
    if not t:
        return ""
    if form == "short":
        level = LEVEL_RU[t["level"]]
        return level if t["level"] in ("confirmed", "supported") else f"⚠ {level}"
    if form == "compact":
        reqs = f"требование {', '.join(t['requirements'])}" if t["requirements"] else ""
        if t["level"] in ("contested", "stale"):
            act = "уточни у пользователя" if t["level"] == "contested" else "сверь с кодом"
            verdict_ = f"⚠ {reason_short(t)} — {act}"
        else:
            verdict_ = COMPACT[t["level"]]
        if not t["requirements"] and not t["ambiguity"]["deviates"]:
            reqs = "без бизнес-требования"
        return " · ".join(x for x in (reqs, verdict_) if x)
    out = f"{kind_text(t)} · {verdict(t)}"
    caveats = t["ambiguity"]["caveats"]
    if caveats and t["level"] != "contested":
        out += f" · оговорка: {_clip(caveats[0], 120)}"
    return out


def action(t: dict[str, Any]) -> str:
    """Группа для сводки пакета: на что можно опереться, что сверить, что уточнить."""
    return {
        "confirmed": "rely",
        "supported": "rely",
        "weak": "check",
        "stale": "check",
        "unanchored": "verify",
        "contested": "ask",
    }[t["level"]]


EDGE_NOTE = {"human": "проверено человеком"}


def edge_note(data: dict[str, Any]) -> str:
    """Пометка связи «почему узел попал в пакет».

    Без пометки: извлечённые из кода, БД и BPM и связи правил, указанные ИИ (это сказано в заголовке пакета).
    """
    method = data.get("method")
    if method == "heuristic":
        why = data.get("inferred") or ("динамическая подписка" if data.get("dynamic") else "")
        return f"предположение: {why}" if why else "предположение"
    return EDGE_NOTE.get(method or "", "")
