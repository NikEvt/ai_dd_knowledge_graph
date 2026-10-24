"""Разбор результата headless-сессии bootstrap_rules.sh.

Читает stream-json лог `claude -p`, достаёт итоговый YAML, проверяет ссылки на модель, проставляет
статус draft и хэши реализаций и пишет knowledge/rules/<module>.yaml. Печатает стоимость сессии.

  uv run python tools/knowledge/bootstrap_collect.py rules <module> <log.jsonl>
  uv run python tools/knowledge/bootstrap_collect.py reconcile <log.jsonl>
  uv run python tools/knowledge/bootstrap_collect.py cost <log.jsonl>...
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import KNOWLEDGE, RULE_ID, RULES, dump_rules_yaml, load_model
from tools.knowledge.drift import current_hashes, ref_target

HEADER = (
    "# Правила модуля {module}: извлечены LLM (tools/knowledge/bootstrap_rules.sh) из кода и среза графа.\n"
    "# Статус verified ставит только человек. Хэши обновляет tools/knowledge/drift.py --write.\n"
)


def session_result(log: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    return result


def yaml_block(text: str) -> Any:
    blocks = re.findall(r"```ya?ml\s*\n(.*?)```", text, flags=re.DOTALL)
    return yaml.safe_load(blocks[-1] if blocks else text)


def known_ids() -> set[str]:
    return {n["id"] for name in ("code", "events", "bpm", "db") for n in load_model(name)["nodes"]}


def _fix_ref(ref: str, known: set[str]) -> str | None:
    if ref in known:
        return ref
    tail = [k for k in known if k.endswith("::" + ref.split("::")[-1]) and ref.split("::")[0] in k]
    return tail[0] if len(tail) == 1 else None


def normalize(rules: list[dict[str, Any]], prefix: str | None) -> tuple[list[dict[str, Any]], list[str]]:
    known = known_ids()
    hashes = current_hashes()
    problems: list[str] = []
    seen: set[str] = set()
    out = []
    for r in rules:
        rid = str(r.get("id", ""))
        if not RULE_ID.match(rid) or (prefix and not rid.startswith(f"R-{prefix}-")) or rid in seen:
            problems.append(f"{rid}: неверный или повторный ID — правило пропущено")
            continue
        seen.add(rid)
        r["status"] = "draft"
        for key in ("implemented_by", "enforced_by_db"):
            kept = []
            for e in r.get(key) or []:
                if isinstance(e, str):  # ссылка строкой: символ, переход или объект БД
                    e = {"symbol" if "::" in e else "transition" if "->" in e else "constraint": e}
                target = ref_target(e)
                if target is None and isinstance(e, dict):  # нестандартный ключ: unique:, check:, index_name:
                    key, target = next(
                        ((k, v) for k, v in e.items() if isinstance(v, str) and k != "lines"), (None, None)
                    )
                    if key and key != "constraint" and key in e:
                        e["constraint" if key not in ("symbol", "transition", "guard") else key] = e.pop(key)
                fixed = _fix_ref(target, known) if target else None
                if fixed is None:
                    problems.append(f"{rid}: неизвестная ссылка {key} {target!r} — убрана")
                    r.setdefault("unresolved_refs", []).append(str(target))
                    continue
                for k in ("symbol", "transition", "guard", "constraint", "trigger", "index", "function"):
                    if e.get(k):
                        e[k] = fixed
                if isinstance(e.get("lines"), int):
                    e["lines"] = str(e["lines"])
                if fixed in hashes:
                    e["hash"] = hashes[fixed]
                kept.append(e)
            r[key] = kept
        for key in ("tested_by", "config"):
            kept = []
            for t in r.get(key) or []:
                if t in known:
                    kept.append(t)
                else:
                    problems.append(f"{rid}: неизвестная ссылка {key} {t!r} — убрана")
            r[key] = kept
        out.append({k: v for k, v in r.items() if v not in (None, [], "")})
    return out, problems


def collect_rules(module: str, log: Path) -> float:
    res = session_result(log)
    cost = float(res.get("total_cost_usd") or 0)
    if not res or res.get("is_error"):
        print(
            f"{module}: сессия завершилась ошибкой ({res.get('subtype')}); стоимость ${cost:.2f}",
            file=sys.stderr,
        )
        return cost
    doc = yaml_block(res.get("result", ""))
    rules = doc.get("rules", []) if isinstance(doc, dict) else []
    prefix = rules[0]["id"].split("-")[1] if rules else None
    rules, problems = normalize(rules, prefix)
    for p in problems:
        print(f"  {module}: {p}", file=sys.stderr)
    RULES.mkdir(parents=True, exist_ok=True)
    path = RULES / f"{module}.yaml"
    path.write_text(dump_rules_yaml(HEADER.format(module=module), rules), encoding="utf-8")
    print(f"{module}: {len(rules)} правил -> {path.relative_to(KNOWLEDGE.parent)}; ${cost:.2f}")
    return cost


def collect_reconcile(log: Path) -> float:
    res = session_result(log)
    cost = float(res.get("total_cost_usd") or 0)
    if not res or res.get("is_error"):
        print(f"reconcile: сессия завершилась ошибкой; стоимость ${cost:.2f}", file=sys.stderr)
        return cost
    doc = yaml_block(res.get("result", "")) or {}
    rules, problems = normalize(doc.get("rules", []) or [], "SCHEMA")
    for p in problems:
        print(f"  reconcile: {p}", file=sys.stderr)
    header = (
        "# Правила из общей схемы (knowledge/sources/erp-library.md), не найденные в коде проекта.\n"
        "# Извлечены LLM на шаге сверки (bootstrap_rules.sh). Статус verified ставит только человек.\n"
    )
    (RULES / "schema.yaml").write_text(dump_rules_yaml(header, rules), encoding="utf-8")
    discrepancies = doc.get("discrepancies", []) or []
    text = yaml.dump({"discrepancies": discrepancies}, allow_unicode=True, sort_keys=False, width=100)
    (KNOWLEDGE / "reconciliation.yaml").write_text(
        "# Расхождения схемы, кода и БД. Фиксируются, код не исправляется. Правится руками.\n" + text,
        encoding="utf-8",
    )
    print(f"reconcile: {len(rules)} правил из схемы, {len(discrepancies)} расхождений; ${cost:.2f}")
    return cost


def main() -> None:
    cmd, *args = sys.argv[1:]
    if cmd == "rules":
        collect_rules(args[0], Path(args[1]))
    elif cmd == "reconcile":
        collect_reconcile(Path(args[0]))
    elif cmd == "cost":
        total = sum(float(session_result(Path(a)).get("total_cost_usd") or 0) for a in args)
        print(f"Итоговая стоимость bootstrap: ${total:.2f}")


if __name__ == "__main__":
    main()
