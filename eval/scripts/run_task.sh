#!/usr/bin/env bash
# Один измеряемый прогон: run_task.sh TASK VARIANT REP [--no-audit]
#   VARIANT: B0 | B1 | S | SMB  (ветка variant/<VARIANT> в library-erp)
# Исполнитель — новая headless-сессия в отдельном клоне (видна только ветка варианта),
# изоляция от личных настроек — claude_isolated из lib.sh.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

TASK=$1 VARIANT=$2 REP=$3; shift 3
AUDIT=1 SERIES=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-audit) AUDIT=0; shift ;;
    --series) SERIES=$2; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
RUN_ID="$(date +%Y%m%d-%H%M%S)-$TASK-$VARIANT-r$REP${SERIES:+-$SERIES}"
RUN_DIR=$EVAL/logs/runs/$RUN_ID
# Серия: один клон на все задачи, изменения копятся; иначе — свой клон на прогон
if [[ -n $SERIES ]]; then WT=$WT_ROOT/series-$SERIES; else WT=$WT_ROOT/$RUN_ID; fi
mkdir -p "$RUN_DIR"
echo "run $RUN_ID"

# 1. Чистое состояние: клон только с веткой варианта, без тегов и чужих веток
if [[ -n $SERIES && -d $WT ]]; then
  echo "series $SERIES: reuse $WT"
else
  git clone -q --no-local --single-branch --no-tags --branch "variant/$VARIANT" "$REPO" "$WT"
  git -C "$WT" switch -q -c "run/${SERIES:-$RUN_ID}"
fi
BASE=$(git -C "$WT" rev-parse HEAD)
(cd "$WT" && uv sync -q && docker compose up -d --wait >/dev/null 2>&1)
if [[ -f "$WT/package.json" ]]; then
  (cd "$WT" && { npm ci --silent --no-audit --no-fund >/dev/null 2>&1 || npm install --silent --no-audit --no-fund --no-save >/dev/null 2>&1; }) \
    || echo "warn: npm install failed"
  echo "ruflo: $(cd "$WT" && npx --no-install ruflo --version 2>/dev/null || echo missing)"
fi
cat > "$RUN_DIR/meta.json" <<EOF
{"run_id": "$RUN_ID", "task_id": "$TASK", "variant": "$VARIANT", "repeat": $REP,
 "worker_model": "$WORKER_MODEL", "effort": "$EFFORT", "base": "$BASE", "workdir": "$WT", "series": "$SERIES"}
EOF

# 2. Исполнитель
PROFILE=$EVAL/profiles/worker.settings.json; AUTO_MEMORY=0
case $VARIANT in
  S|SL) MCP=$EVAL/mcp/S.json ;;
  SMB) MCP=$EVAL/mcp/SMB.json; PROFILE=$EVAL/profiles/worker_smb.settings.json; AUTO_MEMORY=1 ;;
  *) MCP=$EVAL/mcp/none.json ;;
esac
export AUTO_MEMORY
export EVAL_RUN_ID=$RUN_ID EVAL_MCP_LOG=$RUN_DIR/mcp.jsonl
START=$(date +%s)
(cd "$WT" && claude_isolated "$PROFILE" \
  -p "$(cat "$EVAL/ground_truth/tasks/$TASK.prompt.md")" \
  --model "$WORKER_MODEL" \
  --output-format stream-json --verbose \
  --mcp-config "$MCP" \
  --permission-mode acceptEdits \
  --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "TodoWrite" "Task" "Agent" \
     "Bash(uv run *)" "Bash(uv sync *)" "Bash(docker compose *)" \
     "Bash(git status *)" "Bash(git diff *)" "Bash(git log *)" "Bash(ls *)" "mcp__knowledge" \
     "mcp__claude-flow" "Bash(npx --no-install ruflo *)" \
  --max-budget-usd "$WORKER_BUDGET_USD" \
  < /dev/null > "$RUN_DIR/transcript.jsonl" 2> "$RUN_DIR/worker_stderr.log") || echo "worker exited with $?"
echo "{\"wall_seconds\": $(( $(date +%s) - START ))}" > "$RUN_DIR/timing.json"
if jq -e 'select(.type=="result") | (.api_error_status==429 or (.result|tostring|test("session limit|usage limit|rate limit")))' \
     "$RUN_DIR/transcript.jsonl" >/dev/null 2>&1; then
  echo "RATE_LIMIT: $(jq -r 'select(.type=="result") | .result' "$RUN_DIR/transcript.jsonl" | head -1)"
  mv "$RUN_DIR" "$EVAL/logs/runs_invalid/" 2>/dev/null; [[ -z $SERIES ]] && rm -rf "$WT"
  exit 75
fi
unset EVAL_MCP_LOG

# 3. Результат. Скрытые тесты попадают в клон только после завершения сессии.
git -C "$WT" add -A
# Служебные файлы Ruflo (хуки, метрики, политики) — отдельно от изменений исполнителя
RUFLO_PATHS=(.claude-flow .claude/helpers .claude/proven-config.json .claude/.proven-config-version)
EXCLUDE=(); for p in "${RUFLO_PATHS[@]}"; do EXCLUDE+=(":(exclude)$p"); done
git -C "$WT" diff --cached "$BASE" -- . "${EXCLUDE[@]}" > "$RUN_DIR/diff.patch"
git -C "$WT" diff --cached --stat "$BASE" -- . "${EXCLUDE[@]}" > "$RUN_DIR/diff.stat"
git -C "$WT" diff --cached --stat "$BASE" -- "${RUFLO_PATHS[@]}" > "$RUN_DIR/ruflo_runtime.stat" 2>/dev/null || true
(cd "$WT" && uv run ruff check . > "$RUN_DIR/ruff.txt" 2>&1) && echo ok > "$RUN_DIR/ruff.status" || echo fail > "$RUN_DIR/ruff.status"
(cd "$WT" && uv run pytest tests -q -p no:cacheprovider --junitxml="$RUN_DIR/junit-visible.xml" > "$RUN_DIR/pytest-visible.txt" 2>&1) || true
cp -R "$EVAL/hidden_tests" "$WT/_hidden"
(cd "$WT" && uv run pytest _hidden -q -p no:cacheprovider --junitxml="$RUN_DIR/junit-hidden.xml" > "$RUN_DIR/pytest-hidden.txt" 2>&1) || true
rm -rf "$WT/_hidden"
if [[ -f "$WT/tools/knowledge/drift.py" ]]; then
  (cd "$WT" && uv run python tools/knowledge/drift.py --json > "$RUN_DIR/drift.json" 2>&1) || true
fi

# Память Ruflo, сформированная за прогон (только варианты с Ruflo)
if [[ -d "$WT/node_modules/ruflo" ]]; then
  mkdir -p "$RUN_DIR/ruflo"
  (cd "$WT" && npx --no-install ruflo memory peek > "$RUN_DIR/ruflo/peek.txt" 2>&1
   npx --no-install ruflo memory stats > "$RUN_DIR/ruflo/stats.txt" 2>&1
   npx --no-install ruflo memory list -l 500 > "$RUN_DIR/ruflo/list.txt" 2>&1
   npx --no-install ruflo memory export -o "$RUN_DIR/ruflo/memory.json" --include-vectors false > /dev/null 2>&1
   [[ -f .swarm/agentdb-memory.db ]] && npx --no-install ruflo memory export -o "$RUN_DIR/ruflo/agentdb.json" \
      --path .swarm/agentdb-memory.db --include-vectors false > /dev/null 2>&1
   cp -R .claude-flow/sessions "$RUN_DIR/ruflo/sessions" 2>/dev/null) || true
  MEM_DIR=$(claude_memory_dir "$WT")
  [[ -d $MEM_DIR ]] && cp -R "$MEM_DIR" "$RUN_DIR/ruflo/claude_auto_memory"
fi

# 4. Метрики: сначала детерминированные, потом аудитор (новая сессия, тот же клон)
uv run -q --with pyyaml python "$EVAL/scripts/collect_run.py" "$RUN_DIR"
if [[ $AUDIT == 1 ]]; then
  "$EVAL/scripts/audit.sh" --mode score --task "$TASK" --workdir "$WT" --run "$RUN_DIR" || echo "audit failed"
fi

# 5. Уборка: клон удаляется, артефакты остаются в RUN_DIR; автопамять прогона тоже удаляется
if [[ -n $SERIES ]]; then
  # Изменения задачи остаются в клоне серии: следующая задача строится на них
  git -C "$WT" -c user.name="Worker" -c user.email="worker@local" commit -qm "series $SERIES: $TASK" >/dev/null 2>&1 || true
else
  rm -rf "$WT"
  RUN_PROJECT_DIR=$(dirname "$(claude_memory_dir "$WT")")
  if [[ $RUN_PROJECT_DIR == "$HOME/.claude/projects/"*-wt-*"$RUN_ID" ]]; then rm -rf "$RUN_PROJECT_DIR"; fi
fi
echo "done $RUN_ID"
