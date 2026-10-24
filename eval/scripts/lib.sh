# Общие настройки стенда. Подключается: source "$(dirname "$0")/lib.sh"
EVAL=${EVAL:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
REPO=$(cd "${REPO:-$EVAL/../library-erp}" && pwd)
WT_ROOT=$(cd "${WT_ROOT:-$EVAL/../wt}" && pwd)
WORKER_MODEL=${WORKER_MODEL:-claude-opus-5-5}
export AUDITOR_MODEL=${AUDITOR_MODEL:-claude-opus-5-5}
WORKER_BUDGET_USD=${WORKER_BUDGET_USD:-8}
AUDITOR_BUDGET_USD=${AUDITOR_BUDGET_USD:-5}
# Уровень усилий headless-сессий (с 2026-10-23, фаза 9; малый пилот шёл с уровнем по умолчанию)
EFFORT=${EFFORT:-medium}

# Изоляция на подписке (проверено 2026-10-22, Claude Code 2.1.168):
#   --setting-sources project,local  — без пользовательских settings/хуков/плагинов
#   --strict-mcp-config              — только MCP из --mcp-config
#   claudeMdExcludes                 — без ~/.claude/CLAUDE.md (graphify)
#   autoMemoryEnabled=false + env    — без автопамяти
# CLAUDE.md проекта при этом загружается.
claude_isolated() {
  local settings=$1; shift
  # AUTO_MEMORY=1 — только для SMB: автопамять Claude Code нужна мосту памяти Ruflo.
  # Она хранится по пути рабочей папки, а у каждого прогона свой клон.
  if [[ ${AUTO_MEMORY:-0} == 1 ]]; then
    claude --effort "$EFFORT" --settings "$settings" --setting-sources project,local --strict-mcp-config "$@"
  else
    CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude --effort "$EFFORT" --settings "$settings" \
      --setting-sources project,local --strict-mcp-config "$@"
  fi
}
# Каталог автопамяти Claude Code для рабочей папки
claude_memory_dir() { echo "$HOME/.claude/projects/$(echo "$1" | sed 's|[/.]|-|g')/memory"; }

# Все worktree используют одну пару контейнеров (прогоны идут последовательно).
export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME:-aidd}

# Ruflo — локальная закреплённая версия из library-eval/node_modules, без автообновления.
export CLAUDE_FLOW_AUTO_UPDATE=false
ruflo_eval() { (cd "$EVAL" && npx --no-install ruflo "$@"); }
