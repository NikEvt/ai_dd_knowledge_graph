#!/usr/bin/env bash
# Генерация платформенного сервиса-«шума» для large/v0: gen_noise.sh SVC
set -uo pipefail
source "$(dirname "$0")/lib.sh"
SVC=$1
OUT=$EVAL/logs/noise/$SVC; WT=$WT_ROOT/gen-$SVC
rm -rf "$OUT" "$WT"; mkdir -p "$OUT"
git clone -q --no-local --single-branch --no-tags --branch large/v0 "$REPO" "$WT"
BASE=$(git -C "$WT" rev-parse HEAD)
docker exec aidd-postgres-1 psql -q -U erp -d erp -c "DROP DATABASE IF EXISTS erp_gen_$SVC WITH (FORCE)" -c "CREATE DATABASE erp_gen_$SVC" >/dev/null
export DATABASE_URL="postgresql+asyncpg://erp:erp@localhost:55432/erp_gen_$SVC"
PROMPT="$(sed "s/{SVC}/$SVC/g" "$EVAL/noise/common.md")

## Сервис
$(cat "$EVAL/noise/specs/$SVC.md")"
(cd "$WT" && uv sync -q && claude_isolated "$EVAL/profiles/worker.settings.json" -p "$PROMPT" \
  --model "$WORKER_MODEL" --output-format stream-json --verbose --mcp-config "$EVAL/mcp/none.json" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "TodoWrite" "Bash(uv run *)" "Bash(uv sync *)" "Bash(ls *)" "Bash(wc *)" \
  --max-budget-usd 12 < /dev/null > "$OUT/transcript.jsonl" 2> "$OUT/stderr.log")
jq -r 'select(.type=="result") | "\(.subtype) err=\(.is_error) cost=\(.total_cost_usd) \(.result|tostring|.[0:200])"' "$OUT/transcript.jsonl" > "$OUT/result.txt"
git -C "$WT" add -A
git -C "$WT" diff --cached --name-only "$BASE" > "$OUT/files.txt"
grep -vE "^(services/$SVC/|tests/test_${SVC}_|tests/${SVC}_factories\.py$|migrations/noise/$SVC\.sql$)" "$OUT/files.txt" > "$OUT/violations.txt"
git -C "$WT" diff --cached "$BASE" -- "services/$SVC" "migrations/noise/$SVC.sql" tests > "$OUT/service.patch"
(cd "$WT" && uv run pytest -q -p no:cacheprovider > "$OUT/pytest.txt" 2>&1; echo $? > "$OUT/pytest.exit")
(cd "$WT" && uv run ruff check . > "$OUT/ruff.txt" 2>&1; echo $? > "$OUT/ruff.exit")
LINES=$(cd "$WT" && cat $(grep -E "\.(py|sql)$" "$OUT/files.txt") 2>/dev/null | wc -l | tr -d ' ')
echo "$SVC: $(cat "$OUT/result.txt" | cut -c1-80) | lines=$LINES pytest=$(cat $OUT/pytest.exit) ruff=$(cat $OUT/ruff.exit) violations=$(wc -l < "$OUT/violations.txt" | tr -d ' ') | $(tail -1 "$OUT/pytest.txt")"
