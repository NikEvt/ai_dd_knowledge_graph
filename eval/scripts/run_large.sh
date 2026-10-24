#!/usr/bin/env bash
# Фаза 9: B1L и SL × T01–T07 × 2 повтора, без аудитора. Останавливается на лимите подписки (код 75).
set -uo pipefail
cd "$(dirname "$0")/.."
for REP in 1 2; do
  for TASK in T01 T02 T03 T04 T05 T06 T07; do
    for V in B1L SL; do
      if ls -d logs/runs/*-$TASK-$V-r$REP >/dev/null 2>&1; then echo "skip $TASK $V r$REP"; continue; fi
      ./scripts/run_task.sh "$TASK" "$V" "$REP" --no-audit 2>&1 | grep -E "^(run|done|warn|worker exited|RATE_LIMIT|\{)"
      [[ ${PIPESTATUS[0]} == 75 ]] && { echo "STOP: лимит подписки"; exit 75; }
    done
  done
done
echo "large finished"
