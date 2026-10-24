#!/usr/bin/env bash
# Фаза 5: аудит bootstrap модели знаний на ревизии REV (по умолчанию v1).
set -euo pipefail
source "$(dirname "$0")/lib.sh"
REV=${1:-v1}
OUT=$EVAL/logs/bootstrap/$REV
WT=$WT_ROOT/audit-$REV
DOCS=$WT_ROOT/docs-only-$REV
rm -rf "$WT" "$DOCS" "$OUT"; mkdir -p "$OUT"
git clone -q --no-local --single-branch --no-tags --branch "$REV" "$REPO" "$WT" 2>/dev/null
mkdir -p "$DOCS" && cp -R "$WT/docs" "$DOCS/docs"

"$EVAL/scripts/audit.sh" --mode bootstrap --task bootstrap --workdir "$WT" --out "$OUT"
"$EVAL/scripts/audit.sh" --mode docqa --task docqa --workdir "$DOCS" --out "$OUT"
"$EVAL/scripts/audit.sh" --mode docqa_judge --task docqa --workdir "$EVAL/ground_truth" --out "$OUT"
uv run -q --with pyyaml python "$EVAL/scripts/score_bootstrap.py" "$OUT" "$REV"
rm -rf "$WT" "$DOCS"
