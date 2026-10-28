#!/usr/bin/env bash
# Bootstrap модели знаний.
#
#   1. Детерминированные экстракторы (БД, код, события, процесс) и индекс.
#   2. Правила из кода: для каждого сервиса — отдельная headless-сессия `claude -p` (новый контекст)
#      с промптом prompts/extract_rules.md и срезом графа модуля. Результат: knowledge/rules/<module>.yaml
#      (status: draft, ссылки на строки кода, хэши проставляются скриптом).
#   3. Сверка со схемой: детерминированная (reconcile.py) + сессия `claude -p` с prompts/reconcile.md.
#      Результат: knowledge/rules/schema.yaml и knowledge/reconciliation.yaml.
#   4. Хэши, индекс, документация. Итоговая стоимость — в конце вывода.
#
# Лог каждой сессии (stream-json) — knowledge/.bootstrap/<module>.jsonl (в .gitignore).
#
#   tools/knowledge/bootstrap_rules.sh                 # всё
#   tools/knowledge/bootstrap_rules.sh rules billing   # только правила одного модуля
#   tools/knowledge/bootstrap_rules.sh reconcile       # только сверка
#   PARALLEL=1 tools/knowledge/bootstrap_rules.sh      # сессии по модулям параллельно
set -euo pipefail
cd "$(dirname "$0")/../.."

MODEL=claude-opus-5-5
BUDGET_USD=5
LOGDIR=knowledge/.bootstrap
ALL_MODULES=(applications billing scheduling notifications chat)
mkdir -p "$LOGDIR"

prefix_of() {
  case "$1" in
    applications) echo APP ;;
    billing) echo BILL ;;
    scheduling) echo SCHED ;;
    notifications) echo NOTIF ;;
    chat) echo CHAT ;;
    *) echo "$1" | tr '[:lower:]' '[:upper:]' ;;
  esac
}

headless() {  # headless <log> <prompt>  (входные данные — stdin)
  claude -p "$2" \
    --model "$MODEL" \
    --max-budget-usd "$BUDGET_USD" \
    --output-format stream-json --verbose \
    --allowedTools "Read,Grep,Glob" \
    --disallowedTools "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch" \
    --strict-mcp-config \
    --no-session-persistence \
    > "$1"
}

extract() {
  uv run python tools/knowledge/build_index.py --all
}

rules_for() {
  local m=$1 p input
  p=$(prefix_of "$m")
  input="$LOGDIR/$m.input.md"
  sed -e "s|{{MODULE_PATH}}|services/$m|g" -e "s|{{PREFIX}}|$p|g" tools/knowledge/prompts/extract_rules.md > "$input"
  printf '\n\n---\n\n' >> "$input"
  uv run python tools/knowledge/build_index.py --slice "services/$m" >> "$input"
  grep -q "^# Срез графа: services/$m" "$input" || { echo "[$m] срез графа не построен" >&2; return 1; }
  echo "[$m] claude -p ($MODEL, бюджет \$$BUDGET_USD) ..."
  headless "$LOGDIR/$m.jsonl" "Извлеки правила модуля services/$m по инструкции и срезу графа из входных данных." < "$input" || true
  uv run python tools/knowledge/bootstrap_collect.py rules "$m" "$LOGDIR/$m.jsonl"
}

rules() {
  local modules=("$@")
  [ ${#modules[@]} -eq 0 ] && modules=("${ALL_MODULES[@]}")
  uv run python tools/knowledge/build_index.py  # индекс один раз до параллельных срезов
  if [ "${PARALLEL:-0}" = "1" ]; then
    for m in "${modules[@]}"; do rules_for "$m" & done
    wait
  else
    for m in "${modules[@]}"; do rules_for "$m"; done
  fi
}

reconcile() {
  local input="$LOGDIR/reconcile.input.md"
  uv run python tools/knowledge/build_index.py
  {
    cat tools/knowledge/prompts/reconcile.md
    printf '\n\n---\n\n## Извлечённые правила (код и БД)\n\n'
    uv run python tools/knowledge/reconcile.py --rules-digest
    printf '\n## Детерминированная сверка\n\n'
    uv run python tools/knowledge/reconcile.py
  } > "$input"
  echo "[reconcile] claude -p ($MODEL, бюджет \$$BUDGET_USD) ..."
  headless "$LOGDIR/reconcile.jsonl" "Сверь общую схему с извлечёнными правилами по инструкции из входных данных." < "$input" || true
  uv run python tools/knowledge/bootstrap_collect.py reconcile "$LOGDIR/reconcile.jsonl"
}

finish() {
  uv run python tools/knowledge/drift.py --write --skip-model-check || true
  uv run python tools/knowledge/build_index.py
  uv run python tools/knowledge/render_docs.py
  shopt -s nullglob
  uv run python tools/knowledge/bootstrap_collect.py cost "$LOGDIR"/*.jsonl
}

case "${1:-all}" in
  all) extract; rules; reconcile; finish ;;
  extract) extract ;;
  rules) shift; rules "$@"; finish ;;
  reconcile) reconcile; finish ;;
  finish) finish ;;
  *) echo "usage: $0 [all|extract|rules [module...]|reconcile|finish]" >&2; exit 2 ;;
esac
