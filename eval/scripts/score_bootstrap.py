"""Метрики документирования (evaluation_plan.md, 4.1) по выводу аудитора: score_bootstrap.py OUT REV"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

EVAL = Path(__file__).resolve().parents[1]
OUT, REV = Path(sys.argv[1]), sys.argv[2]


def lines(name: str) -> list[dict]:
    path = OUT / name
    rows = []
    for line in path.read_text().splitlines() if path.exists() else []:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


gt = {r["id"]: r for r in yaml.safe_load((EVAL / "ground_truth" / "rules.yaml").read_text())["rules"]}
boot = lines("auditor_bootstrap.jsonl")
matches = {r["gt"]: r for r in boot if r.get("metric") == "rule_match"}
correct = [r for r in boot if r.get("metric") == "model_rule_correct"]
judged = [r for r in lines("auditor_docqa_judge.jsonl") if r.get("metric") == "docqa_correct"]
score = {"full": 1.0, "partial": 0.5, "none": 0.0}

result: dict = {"rev": REV, "gt_rules": len(gt), "matched_gt_rules": len(matches)}
result["rule_recall"] = round(sum(score[matches[g]["match"]] for g in gt if g in matches) / len(gt), 3)
result["rule_recall_full_only"] = round(
    sum(matches.get(g, {}).get("match") == "full" for g in gt) / len(gt), 3
)
by_cat: dict[str, list[float]] = defaultdict(list)
for gid, rule in gt.items():
    for cat in rule.get("hidden", []):
        by_cat[cat].append(score[matches[gid]["match"]] if gid in matches else 0.0)
result["rule_recall_by_hidden_category"] = {c: round(sum(v) / len(v), 2) for c, v in sorted(by_cat.items())}
result["missed_gt_rules"] = sorted(g for g in gt if matches.get(g, {}).get("match", "none") == "none")

cval = {"yes": 1.0, "partial": 0.5, "no": 0.0}
if correct:
    result["model_rules_judged"] = len(correct)
    result["rule_precision"] = round(sum(cval[r["correct"]] for r in correct) / len(correct), 3)
    for status in ("verified", "draft"):
        group = [r for r in correct if r.get("status") == status]
        if group:
            result[f"wrong_share_{status}"] = round(sum(r["correct"] == "no" for r in group) / len(group), 3)
            result[f"n_{status}"] = len(group)
    result["wrong_model_rules"] = [r["model"] for r in correct if r["correct"] == "no"]
if judged:
    result["doc_qa_accuracy"] = round(sum(float(r["value"]) for r in judged) / len(judged), 3)
    result["doc_qa_failed"] = [r["id"] for r in judged if float(r["value"]) < 1]

for name in ("bootstrap", "docqa", "docqa_judge"):
    usage = OUT / f"auditor_{name}_usage.json"
    if usage.exists():
        result[f"cost_{name}"] = json.loads(usage.read_text())["cost_usd"]
(OUT / "bootstrap_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
