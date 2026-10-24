#!/usr/bin/env bash
# Запуск аудитора: новая headless-сессия, только чтение, без MCP, без CLAUDE.md.
#   audit.sh --mode blind --task T01 --workdir <клон проекта> --out <каталог>
#   audit.sh --mode score --task T01 --workdir <клон проекта> --run <RUN_DIR>
set -euo pipefail
source "$(dirname "$0")/lib.sh"

MODE="" TASK="" WORKDIR="" OUT="" RUN_DIR=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --mode) MODE=$2; shift 2 ;;
    --task) TASK=$2; shift 2 ;;
    --workdir) WORKDIR=$(cd "$2" && pwd); shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --run) RUN_DIR=$(cd "$2" && pwd); OUT=$RUN_DIR; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)

PROMPT="$(awk 'NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$EVAL/agents/context-auditor.md")

---
MODE=$MODE
TASK_ID=$TASK"
ADD_DIRS=()
if [[ $MODE == blind ]]; then
  PROMPT+="
TASK_TEXT:
$(cat "$EVAL/ground_truth/tasks/$TASK.prompt.md")"
elif [[ $MODE == score ]]; then
  ADD_DIRS+=(--add-dir "$EVAL/ground_truth" --add-dir "$RUN_DIR")
  PROMPT+="
RUN_DIR=$RUN_DIR
GROUND_TRUTH=$EVAL/ground_truth"
elif [[ $MODE == bootstrap ]]; then
  ADD_DIRS+=(--add-dir "$EVAL/ground_truth")
  PROMPT+="
GROUND_TRUTH=$EVAL/ground_truth"
elif [[ $MODE == docqa ]]; then
  PROMPT+="
QUESTIONS:
$(uv run -q --with pyyaml python -c 'import yaml,sys; [print(q["id"]+": "+q["q"]) for q in yaml.safe_load(open(sys.argv[1]))["questions"]]' "$EVAL/ground_truth/doc_questions.yaml")"
elif [[ $MODE == docqa_judge ]]; then
  ADD_DIRS+=(--add-dir "$EVAL/ground_truth")
  PROMPT+="
GROUND_TRUTH=$EVAL/ground_truth
ANSWERS:
$(cat "$OUT/auditor_docqa.jsonl")"
fi

START=$(date +%s)
(cd "$WORKDIR" && printf '%s' "$PROMPT" | claude_isolated "$EVAL/profiles/auditor.settings.json" \
  -p \
  --model "$AUDITOR_MODEL" \
  --output-format json \
  --mcp-config "$EVAL/mcp/none.json" \
  --tools "Read,Grep,Glob" \
  --allowedTools "Read,Grep,Glob" \
  --permission-mode dontAsk \
  --max-budget-usd "$AUDITOR_BUDGET_USD" \
  ${ADD_DIRS[@]+"${ADD_DIRS[@]}"} \
  > "$OUT/auditor_raw_$MODE.json")

RESULT=$(jq -r '.result' "$OUT/auditor_raw_$MODE.json")
printf '%s\n' "$RESULT" | awk '/^---SUMMARY---$/{exit} /^\{/' > "$OUT/auditor_$MODE.jsonl"
printf '%s\n' "$RESULT" | awk 'f; /^---SUMMARY---$/{f=1}' > "$OUT/auditor_${MODE}_summary.md"
jq -c --arg task "$TASK" --arg mode "$MODE" --argjson wall $(( $(date +%s) - START )) \
  '{task: $task, mode: $mode, cost_usd: .total_cost_usd, turns: .num_turns, wall_seconds: $wall,
    input_tokens: (.usage.input_tokens + .usage.cache_read_input_tokens + .usage.cache_creation_input_tokens),
    output_tokens: .usage.output_tokens, is_error: .is_error}' \
  "$OUT/auditor_raw_$MODE.json" | tee "$OUT/auditor_${MODE}_usage.json"
echo "nodes: $(wc -l < "$OUT/auditor_$MODE.jsonl")"

# В режиме score оценки аудитора дописываются в общий лог прогона с метаданными
if [[ $MODE == score ]]; then
  jq -c --slurpfile meta "$RUN_DIR/meta.json" \
    '. + {run_id: $meta[0].run_id, task_id: $meta[0].task_id, variant: $meta[0].variant,
          repeat: $meta[0].repeat, worker_model: $meta[0].worker_model,
          auditor_model: env.AUDITOR_MODEL, method: (.method // "llm"), phase: (.phase // "audit")}' \
    "$OUT/auditor_score.jsonl" >> "$RUN_DIR/audit.jsonl" 2>/dev/null || echo "warn: some auditor lines are not JSON"
fi

# Итог аудита — в память Ruflo стенда (library-eval/.swarm), отдельной командой после сессии.
# Сам аудитор память не читает: работает в клоне проекта, без хуков Ruflo.
SUMMARY_FILE="$OUT/auditor_${MODE}_summary.md"
if [[ -s $SUMMARY_FILE ]]; then
  KEY="audit/${MODE}/${TASK}/$(basename "$OUT")"
  ruflo_eval memory store -n audit -k "$KEY" --value "$(head -c 4000 "$SUMMARY_FILE")" \
    --tags "mode:$MODE,task:$TASK" --provenance agent_output >/dev/null 2>&1 \
    && echo "ruflo memory: $KEY" || echo "warn: ruflo memory store failed"
fi
