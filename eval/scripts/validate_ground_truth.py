"""Проверка эталона против кода: все ссылки существуют, H-категории покрыты, тесты на месте.

    uv run --with pyyaml python scripts/validate_ground_truth.py ../library-erp
"""

import ast
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

EVAL = Path(__file__).resolve().parents[1]
REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else EVAL.parent / "library-erp"
GT = EVAL / "ground_truth"
errors: list[str] = []

migrations_sql = "\n".join(p.read_text() for p in (REPO / "migrations" / "versions").glob("*.py"))
bpm_text = (REPO / "bpm" / "application_process.yaml").read_text()


def top_level_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def check_code(ref: str, where: str) -> None:
    file, _, symbol = ref.partition("::")
    path = REPO / file
    if not path.exists():
        errors.append(f"{where}: нет файла {file}")
    elif symbol and symbol not in top_level_names(path):
        errors.append(f"{where}: в {file} нет символа {symbol}")


def check_db(ref: str, where: str) -> None:
    token = re.split(r"[ (]", ref)[0]
    name = token.split(".")[-1]
    if token.count(".") == 2:  # schema.table.column
        name = token.split(".")[-1]
    if name not in migrations_sql and not name.endswith("_check"):
        errors.append(f"{where}: в миграциях нет {name}")


def check_bpm(ref: str, where: str) -> None:
    for state in re.findall(r"[a-z_]+", ref):
        if state not in bpm_text:
            errors.append(f"{where}: в bpm нет состояния {state}")


rules = yaml.safe_load((GT / "rules.yaml").read_text())["rules"]
rule_ids = {r["id"] for r in rules}
categories: Counter[str] = Counter()
hidden_tests = {
    f"{p.name}::{n}"
    for p in (EVAL / "hidden_tests" / "regression").glob("test_*.py")
    for n in top_level_names(p)
    if n.startswith("test_")
}

for rule in rules:
    where = rule["id"]
    for h in rule.get("hidden", []):
        categories[h] += 1
    for link in rule["implemented_by"]:
        (kind, ref), = link.items()
        {"code": check_code, "config": check_code, "db": check_db, "bpm": check_bpm}.get(
            kind, lambda *_: None
        )(ref, where)
    for test in rule.get("tested_by", []):
        if test not in hidden_tests:
            errors.append(f"{where}: нет скрытого теста {test}")

events = yaml.safe_load((GT / "events.yaml").read_text())["events"]
for topic, spec in events.items():
    for ref in spec["publishers"] + spec["consumers"]:
        check_code(ref, f"event {topic}")
    if not any(f'"{topic}"' in p.read_text() for p in (REPO / "services").rglob("*.py")):
        errors.append(f"event {topic}: топик не встречается в коде")

for task_file in sorted((GT / "tasks").glob("T*.yaml")):
    task = yaml.safe_load(task_file.read_text())
    where = task["id"]
    for node in task["expected_nodes"]:
        ref, kind = node["ref"], node["kind"]
        if kind == "rule" and ref not in rule_ids:
            errors.append(f"{where}: нет правила {ref}")
        elif kind in ("code", "config"):
            check_code(ref, where)
        elif kind == "db":
            check_db(ref, where)
        elif kind == "event" and ref not in events:
            errors.append(f"{where}: нет события {ref}")
    for test in task["supersedes"]:
        if test not in hidden_tests:
            errors.append(f"{where}: supersedes несуществующий тест {test}")

for q in yaml.safe_load((GT / "doc_questions.yaml").read_text())["questions"]:
    for r in q["rules"]:
        if r not in rule_ids:
            errors.append(f"{q['id']}: нет правила {r}")

print(f"rules={len(rules)} events={len(events)} hidden regression tests={len(hidden_tests)}")
print("hidden categories:", dict(sorted(categories.items())))
weak = [h for h in ("H1", "H2", "H3", "H4", "H5", "H6", "H7") if categories[h] < 2]
if weak:
    errors.append(f"категории с < 2 случаями: {weak}")
untested = [r["id"] for r in rules if not r.get("tested_by")]
print(f"rules without hidden regression test: {len(untested)}")
if errors:
    print("ERRORS:")
    print("\n".join(f"  {e}" for e in errors))
    sys.exit(1)
print("OK")
