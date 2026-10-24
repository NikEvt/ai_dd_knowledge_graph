#!/usr/bin/env bash
# Повторный аудит прогона: клон ветки варианта + diff.patch прогона → audit.sh --mode score.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
RUN_DIR=$(cd "$1" && pwd)
VARIANT=$(jq -r .variant "$RUN_DIR/meta.json"); TASK=$(jq -r .task_id "$RUN_DIR/meta.json")
WT=$WT_ROOT/reaudit-$(basename "$RUN_DIR"); rm -rf "$WT"
git clone -q --no-local --single-branch --no-tags --branch "variant/$VARIANT" "$REPO" "$WT"
git -C "$WT" apply --whitespace=nowarn "$RUN_DIR/diff.patch"
jq -c 'select(.method != "llm")' "$RUN_DIR/audit.jsonl" > "$RUN_DIR/audit.tmp" && mv "$RUN_DIR/audit.tmp" "$RUN_DIR/audit.jsonl"
"$EVAL/scripts/audit.sh" --mode score --task "$TASK" --workdir "$WT" --run "$RUN_DIR"
rm -rf "$WT"
