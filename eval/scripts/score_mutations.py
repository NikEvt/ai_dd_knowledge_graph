"""Сводка по мутациям: поймал ли CI значимые и не шумел ли на косметике."""

import json
import re
from pathlib import Path

import yaml

EVAL = Path(__file__).resolve().parents[1]
OUT = EVAL / "logs" / "mutations"
expected = yaml.safe_load((EVAL / "mutations" / "expected.yaml").read_text())
rows = []
for m, exp in expected.items():
    d = OUT / m
    if not d.exists():
        continue
    steps = ("build_index", "model_fresh", "drift", "check_rules", "docs_fresh")
    code = {s: int((d / f"{s}.exit").read_text()) for s in steps}
    drift_text = (d / "drift.txt").read_text()
    suspect_lines = " ".join(line for line in drift_text.splitlines() if "suspect" in line.lower())
    suspects = sorted(set(re.findall(r"R-[A-Z0-9-]+", suspect_lines)))
    # Смысловой сигнал: drift (suspect, новые ограничения БД) и check_rules. Шаги model_fresh/docs_fresh —
    # механическое требование пересобрать модель (она хранит номера строк) — учитываются отдельно.
    signal = code["drift"] != 0 or code["check_rules"] != 0 or bool(suspects)
    regen_required = code["model_fresh"] != 0 or code["docs_fresh"] != 0
    rows.append({"mutation": m, "significant": exp["significant"], "expect": exp["expect"],
                 "ci_signal": signal, "correct": signal == exp["significant"],
                 "regen_required": regen_required, "exit_codes": code, "suspect_rules": suspects})
sig = [r for r in rows if r["significant"]]
cos = [r for r in rows if not r["significant"]]
summary = {
    "drift_recall": round(sum(r["ci_signal"] for r in sig) / len(sig), 2) if sig else None,
    "drift_fp_rate": round(sum(r["ci_signal"] for r in cos) / len(cos), 2) if cos else None,
    "rows": rows,
}
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
for r in rows:
    print(f"{r['mutation']} {'значимая ' if r['significant'] else 'косметика'} сигнал={r['ci_signal']} "
          f"{'OK' if r['correct'] else 'ПРОМАХ'} пересборка={r['regen_required']} "
          f"suspect={r['suspect_rules'][:6]}")
print(f"drift_recall={summary['drift_recall']} drift_fp_rate={summary['drift_fp_rate']}")
