#!/usr/bin/env bash
# Пилот (B1, S × T01, T04, T08 × 2) и серия SMB с памятью Ruflo (T02 → T07).
set -uo pipefail
cd "$(dirname "$0")/.."
for REP in 1 2; do
  for TASK in T01 T04 T08; do
    for V in B1 S; do
      if ls -d logs/runs/*-$TASK-$V-r$REP >/dev/null 2>&1; then echo "skip $TASK $V r$REP (уже есть)"; continue; fi
      ./scripts/run_task.sh "$TASK" "$V" "$REP" 2>&1 | grep -E "^(run|done|warn|worker exited|audit failed|RATE_LIMIT)"
      [[ ${PIPESTATUS[0]} == 75 ]] && { echo "STOP: лимит подписки"; exit 75; }
    done
  done
done
echo "=== серия SMB"
for TASK in T02 T03 T05 T06 T07; do
  ./scripts/run_task.sh "$TASK" SMB 1 --series smb1 2>&1 | grep -E "^(run|done|warn|worker exited|audit failed|series|RATE_LIMIT)"
  [[ ${PIPESTATUS[0]} == 75 ]] && { echo "STOP: лимит подписки"; exit 75; }
done
echo "=== агрегация"
duckdb < scripts/aggregate.sql > logs/summary.txt 2>&1 || true
echo "pilot finished"
