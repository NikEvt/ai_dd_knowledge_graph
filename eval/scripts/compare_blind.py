"""Сравнение слепого аудита (полный контекст) с эталоном задач.

    uv run --with pyyaml python scripts/compare_blind.py [T01 ...]

Сравниваются только узлы, не являющиеся правилами (code/config/db/event/bpm): ID правил эталона
аудитору неизвестны. Результат — logs/blind/compare.md для ручного разбора (строка #4 карты запусков)
и logs/blind/<T>/compare.json.
"""

import json
import sys
from pathlib import Path

import yaml

EVAL = Path(__file__).resolve().parents[1]
GT = EVAL / "ground_truth"
BLIND = EVAL / "logs" / "blind"


def norm(kind: str, ref: str) -> str:
    ref = ref.strip()
    if kind == "bpm":
        return ref.replace(" ", "")
    if kind == "db":
        return ref.split(" ")[0].lower()
    return ref


def load_task(task: str) -> dict:
    return yaml.safe_load((GT / "tasks" / f"{task}.yaml").read_text())


def main(tasks: list[str]) -> None:
    lines = ["# Слепой аудит против эталона", ""]
    totals = {"expected": 0, "found": 0, "hidden": 0, "hidden_found": 0}
    for task in tasks:
        spec = load_task(task)
        expected = {
            norm(n["kind"], n["ref"]): n for n in spec["expected_nodes"] if n["kind"] != "rule"
        }
        path = BLIND / task / "auditor_blind.jsonl"
        if not path.exists():
            lines += [f"## {task}: нет результата", ""]
            continue
        found_nodes = {}
        for line in path.read_text().splitlines():
            try:
                node = json.loads(line)
            except json.JSONDecodeError:
                continue
            found_nodes[norm(node["kind"], node["ref"])] = node
        # Ссылка на файл в эталоне засчитывается, если найден любой символ этого файла
        for ref in list(expected):
            if "::" not in ref and expected[ref]["kind"] == "code":
                if any(f.startswith(ref + "::") for f in found_nodes):
                    found_nodes.setdefault(ref, {"kind": "code", "role": "file", "why": "символы файла"})
        hit = sorted(set(expected) & set(found_nodes))
        missed = sorted(set(expected) - set(found_nodes))
        extra = sorted(r for r in set(found_nodes) - set(expected) if found_nodes[r].get('role') != 'file')
        hidden = [r for r, n in expected.items() if n.get("hidden")]
        hidden_hit = [r for r in hidden if r in found_nodes]
        totals["expected"] += len(expected)
        totals["found"] += len(hit)
        totals["hidden"] += len(hidden)
        totals["hidden_found"] += len(hidden_hit)
        usage = json.loads((BLIND / task / "auditor_blind_usage.json").read_text())
        result = {
            "task": task,
            "recall": len(hit) / len(expected) if expected else None,
            "hidden_recall": len(hidden_hit) / len(hidden) if hidden else None,
            "hit": hit,
            "missed": missed,
            "extra": extra,
            "cost_usd": usage["cost_usd"],
            "input_tokens": usage["input_tokens"],
        }
        (BLIND / task / "compare.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        lines += [
            f"## {task} — {spec['summary']}",
            "",
            f"recall {len(hit)}/{len(expected)}, hidden {len(hidden_hit)}/{len(hidden)}, "
            f"стоимость ${usage['cost_usd']:.2f}, входных токенов {usage['input_tokens']:,}",
            "",
            "**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**",
            *[
                f"- `{r}` ({expected[r]['kind']}, {expected[r]['role']}, {expected[r].get('hidden', '-')})"
                for r in missed
            ],
            "" if missed else "- нет",
            "",
            "**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**",
            *[
                f"- `{r}` ({found_nodes[r]['kind']}, {found_nodes[r]['role']}): "
                f"{found_nodes[r].get('why', '')}"
                for r in extra
            ],
            "",
        ]
    if totals["expected"]:
        lines.insert(
            2,
            f"Итого recall {totals['found']}/{totals['expected']} = "
            f"{totals['found'] / totals['expected']:.2f}; "
            f"hidden {totals['hidden_found']}/{totals['hidden']} = "
            f"{totals['hidden_found'] / max(totals['hidden'], 1):.2f}\n",
        )
    (BLIND / "compare.md").write_text("\n".join(lines))
    print("\n".join(lines[:4]))


if __name__ == "__main__":
    main(sys.argv[1:] or [f"T0{i}" for i in range(1, 9)])
