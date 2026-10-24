# Сценарий: развернуть решение, провести разработку, собрать результаты

Опирается на `ai-driven-development_suggested_solution.md` (что внедряем) и `evaluation_plan.md` (что и как меряем).

**Текущий этап — только Claude Code.** Codex и проверка паритета агентов отложены.

Команды, помеченные **[сверить]**, зависят от версии инструмента. Перед запуском их нужно проверить по `claude --help` или документации.

---

## 0. Общая схема

```
Фаза 1  Окружение            uv + Python 3.14, Docker (Postgres, Redis), Claude Code, Ruflo
Фаза 2  Тестовый проект      генерация сервисов + эталон  ──▶ tag v0
Фаза 3  Слепой аудит         дополнение эталона
Фаза 4  Внедрение решения    модель знаний, MCP, AGENTS.md, CI ──▶ tag v1, ветки вариантов
Фаза 5  Аудит bootstrap      метрики документирования (4.1)
Фаза 6  Разработка           задачи × варианты × повторы, затем серия задач подряд
Фаза 7  Мутации              drift detection (4.4), без LLM
Фаза 8  Сборка результатов   агрегация логов ──▶ report.md
```

Пилот перед полным прогоном описан в разделе 9.

---

## 1. Окружение

### 1.1. Инструменты

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.14                       # локально сейчас 3.13
brew install --cask docker                   # или OrbStack
brew install duckdb jq
npm i -g @anthropic-ai/claude-code
npx ruflo@latest --version                   # [сверить] имя пакета и команда init
```

### 1.2. Директории

```
~/work/ai-dd/
  library-erp/        # репозиторий проекта: то, что видит исполнитель
  library-eval/       # репозиторий стенда: эталон, скрытые тесты, мутации, раннер, промпты аудитора, логи
  wt/                 # git worktree на каждый прогон (создаёт и удаляет раннер)
```

**Правило про CLAUDE.md.** Claude Code подхватывает `CLAUDE.md` и `.claude/` из рабочей папки и из всех родительских. Поэтому в `~/work/ai-dd/`, `~/work/` и `~` не должно быть `CLAUDE.md` и `.claude/` с настройками проекта. Иначе они попадут в каждую сессию исполнителя. Это нужно проверить после фазы 2: генератор работает из `~/work/ai-dd/` и может создать там файлы.

### 1.3. Профили Claude Code

Глобальные настройки (`~/.claude/CLAUDE.md` с инструкцией graphify, личная автопамять, свои MCP-серверы) попадут в сессию и исказят сравнение. Поэтому сессии делятся на три профиля:

| Профиль | Где конфиг | Для чего |
|---|---|---|
| **Личный** | обычный `~/.claude` | интерактивная работа человека: генерация, внедрение решения, отладка стенда |
| **Исполнитель** | `~/.claude` (логин подписки) + флаги изоляции из `lib.sh` + `profiles/worker.settings.json` | все измеряемые прогоны и bootstrap |
| **Аудитор** | то же + `profiles/auditor.settings.json` (исключает и CLAUDE.md проекта) + только инструменты чтения | все запуски аудитора |

**Проверено (2026-10-22, Claude Code 2.1.168), авторизация через подписку.** Пустой `CLAUDE_CONFIG_DIR` не видит логин подписки, а `--bare` принимает только API-ключ. Поэтому профили «исполнитель» и «аудитор» собраны флагами поверх обычного `~/.claude` (функция `claude_isolated` в `library-eval/scripts/lib.sh`):

| Что отключить | Чем |
|---|---|
| пользовательские settings, хуки, плагины | `--setting-sources project,local` |
| личные MCP-серверы и коннекторы | `--strict-mcp-config --mcp-config <файл стенда>` |
| `~/.claude/CLAUDE.md` (graphify) | `--settings` с `"claudeMdExcludes": ["/Users/<user>/.claude/CLAUDE.md"]` |
| автопамять | `"autoMemoryEnabled": false` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` |

При этом `CLAUDE.md` проекта в cwd загружается. Это проверено пробной сессией: она видит проектный CLAUDE.md, но не видит graphify, MCP и память.

Если появится `ANTHROPIC_API_KEY`, для аудитора лучше `--bare`: он отключает всё, включая автопоиск CLAUDE.md.

### 1.4. Инфраструктура проекта

`library-erp/docker-compose.yml`: Postgres 17 и Redis 7 (события через Redis Streams). Перед каждым прогоном БД пересоздаётся.

**Готово, если:** `uv run python -V` → 3.14, `docker compose up -d` поднимает оба контейнера, `CLAUDE_CONFIG_DIR=$(mktemp -d) claude -p "Перечисли загруженные инструкции и MCP-серверы"` из `wt/` не видит ни graphify, ни личных MCP.

---

## 2. Карта запусков

Главная таблица сценария: как запускать каждую сессию.

- **Новая** — свежая сессия без истории.
- **Продолжение** — `claude --continue` / `--resume` в той же папке.
- **Headless** — `claude -p` из скрипта.
- **Интерактив** — человек работает в терминале или VS Code.

| # | Фаза | Что | Сессия | Режим | Рабочая папка (cwd) | Дополнительный доступ | Профиль |
|---|---|---|---|---|---|---|---|
| 1 | 2 | Генерация проекта и эталона | новая, далее **можно продолжать**, пока генерация не закончена | интерактив | `~/work/ai-dd/` (видит оба репозитория) | — | личный |
| 2 | 2 | Доработка скрытых тестов, если тест задачи проходит на `v0` | продолжение сессии #1 | интерактив | `~/work/ai-dd/` | — | личный |
| 3 | 3 | Слепой аудит эталона | **новая на каждую задачу** | headless | `wt/blind-v0` (клон `v0` с одной веткой) | **нет** доступа к `library-eval` | аудитор |
| 4 | 3 | Разбор расхождений слепого аудита и эталона | новая | интерактив | `library-eval/` | `--add-dir ../wt/blind-v0` | личный |
| 5 | 4 | Внедрение решения (код экстракторов, MCP, CI, AGENTS.md) | новая, далее **можно продолжать** | интерактив | `library-erp/` на ветке `solution` | только `--add-dir ~/work/ai-dd/handoff`; **нет** доступа к `library-eval`, `evaluation_plan.md`, `run_scenario.md` (в них примеры заложенных связей) | личный |
| 6 | 4 | Bootstrap: извлечение правил LLM | **новая на каждый модуль** | headless | `library-erp/` на ветке `solution` | — | исполнитель |
| 7 | 4 | Проверка `draft`-правил человеком | новая | интерактив | `library-erp/` | — | личный |
| 8 | 5 | Аудит bootstrap | новая | headless | `wt/audit-v1` (worktree от `v1`) | `--add-dir library-eval/ground_truth` | аудитор |
| 9 | 6 | Прогон задачи (B0, B1, S, SMB) | **новая на каждый прогон** | headless | `wt/<run_id>` (свой worktree от `variant/<V>`) | — | исполнитель |
| 10 | 6 | Аудит прогона | **новая на каждый прогон** | headless | `wt/<run_id>` (до удаления worktree) | `--add-dir library-eval/ground_truth`, `--add-dir library-eval/logs/<run_id>` | аудитор |
| 11 | 6 | Серия задач подряд (S, SMB) | **новая на каждую задачу**, но **один и тот же** worktree | headless | `wt/series-<V>` | — | исполнитель |
| 12 | 6 | Аудит после каждой задачи серии | новая | headless | `wt/series-<V>` | `--add-dir library-eval/ground_truth` | аудитор |
| 13 | 7 | Мутации | без Claude, только скрипты | — | `wt/mut-*` | — | — |
| 14 | 8 | Агрегация | без Claude, duckdb | — | `library-eval/` | — | — |
| 15 | 8 | Текст отчёта по готовым цифрам | новая | headless или интерактив | `library-eval/logs/` | — | личный |
| 16 | 5–6 | Ручная проверка 15–20% оценок аудитора | новая | интерактив | `library-eval/` | `--add-dir` нужного worktree | личный |

**Что никогда не делать:**
- **Продолжать сессию исполнителя или аудитора.** История прошлого прогона — это утечка контекста, и метрики станут несравнимыми.
- **Запускать исполнителя из сессии #1 или #5.** Генератор знает эталон, а автор решения знает, где что лежит.
- **Давать исполнителю `--add-dir` на `library-eval`.**
- **Класть определение аудитора в `library-erp/.claude/agents/`.** Оно живёт в `library-eval/agents/`.
- **Запускать исполнителей параллельно с общей БД.** Либо по очереди, либо у каждого прогона свой `COMPOSE_PROJECT_NAME`.

**Почему серия (#11) — это новая сессия на каждую задачу в общем worktree.** Так работает реальный разработчик: новая задача — новая сессия, а между задачами знания живут в репозитории, в модели знаний и в Memory Bank, а не в истории чата. Ровно это и проверяет серия.

---

## 3. Фаза 2: тестовый проект и эталон

**Запуск:** сессия #1 — интерактив, личный профиль, cwd `~/work/ai-dd/`.

### 3.1. Что генерируем

```
library-erp/
  services/
    applications/   # заявки, проверка, архив и попытки, дедупликация
    billing/        # счета, платежи, штрафы
    scheduling/     # окна, запись, неявка
    notifications/  # шаблоны и отправка писем
    chat/           # чат и события заявки
  libs/events/      # схемы событий, outbox, подписка
  bpm/application_process.yaml   # этапы и переходы заявки по видам
  migrations/       # Alembic: таблицы, CHECK, UNIQUE, триггеры
  tests/            # видимые тесты
  docker-compose.yml, pyproject.toml (Ruff, pytest, pytest-asyncio)
```

Подмножество домена: виды заявок, этапы, смена площадки, архив, дедупликация, счета и оплата, расписание и запись, письма, штрафы, чат. Роли можно упростить до проверки «закреплён ли сотрудник».

### 3.2. Промпт генератору (суть)

```
Сгенерируй проект по разделу 3.1 run_scenario.md на стеке Python 3.14 / FastAPI / async SQLAlchemy / Alembic / Redis Streams.
Обязательно заложи неочевидные связи категорий H1–H7 из evaluation_plan.md, минимум по 2 на категорию.
Не пиши комментариев, объясняющих эти связи, и не оставляй ID правил в коде — проект имитирует код без документации.
Не создавай CLAUDE.md, AGENTS.md и .claude/ ни в library-erp, ни в ~/work/ai-dd.
Параллельно запиши в library-eval/ground_truth/:
  rules.yaml, edges.yaml, tasks/T01..T08.yaml и T01..T08.prompt.md, doc_questions.yaml (30 вопросов с ответами),
  а в library-eval/hidden_tests/ — приёмочные тесты на новое поведение каждой задачи и регрессионные тесты на все правила.
```

### 3.3. Формат эталона

```yaml
# rules.yaml
- id: GT-VENUE-06
  text: При смене площадки записанному клиенту отменяется запись, книги освобождаются, уходит письмо об отмене и новая ссылка.
  hidden: H2
  implemented_by:
    - code: services/applications/venue.py::change_venue
    - event: application.venue_changed -> services/scheduling/consumers.py::on_venue_changed
    - code: services/notifications/consumers.py::on_booking_cancelled
  enforced_by_db: []
  tested_by: [hidden_tests/regression/test_gt_venue_06.py]

# tasks/T01.yaml
id: T01
prompt_file: T01.prompt.md          # текст задачи для исполнителя — без подсказок
expected_nodes:
  - {ref: GT-VENUE-05, kind: rule}
  - {ref: GT-VENUE-06, kind: rule, hidden: H2}
  - {ref: chk_venue_change_allowed, kind: db_constraint, hidden: H1}
  - {ref: GT-MAIL-TPL-02, kind: rule, hidden: H4}
  - {ref: services/scheduling/consumers.py::on_venue_changed, kind: symbol}
hidden_tests: [hidden_tests/tasks/test_t01.py]
```

### 3.4. Проверка и фиксация

Без Claude, в терминале:

```bash
cd ~/work/ai-dd/library-erp
docker compose up -d && uv run alembic upgrade head
uv run ruff check . && uv run pytest -q                       # видимые тесты зелёные
../library-eval/scripts/check_hidden.sh --rev HEAD           # регрессия зелёная, тесты задач красные
ls ~/work/ai-dd/CLAUDE.md ~/work/ai-dd/.claude 2>/dev/null  # должно быть пусто
git add -A && git commit -m "Generated test project" && git tag v0
```

Если скрытый тест задачи проходит на `v0`, он ничего не проверяет. Тогда — продолжение сессии #1 (строка #2 карты) и переписать тест.

**Готово, если:** проект собирается, регрессия зелёная, тесты задач красные, в эталоне ≥ 2 случая на каждую H-категорию.

---

## 4. Фаза 3: слепой аудит эталона

**Запуск:** #3 — новая headless-сессия на каждую задачу, профиль аудитора, cwd `wt/blind-v0`, без доступа к эталону.

```bash
git -C library-erp worktree add ../wt/blind-v0 v0
for T in T01 T02 T03 T04 T05 T06 T07 T08; do
  library-eval/scripts/audit.sh --mode blind --task $T --worktree wt/blind-v0
done
```

Скрипт сравнивает найденное аудитором с `tasks/T*.yaml`. Разбор расхождений — сессия #4, интерактив в `library-eval/`:
- аудитор нашёл связь, которой нет в эталоне → человек решает, добавить её или отклонить;
- связь есть в эталоне, но аудитор её не нашёл → связь действительно скрытая (хорошо) или эталон ошибочен (проверить).

Результаты `blind` сохраняются как вариант **B2** (полный контекст).

**Готово, если:** все расхождения разобраны, эталон зафиксирован коммитом в `library-eval`.

---

## 5. Фаза 4: внедрение решения

**Запуск:** #5 — интерактив, личный профиль, cwd `library-erp/` на ветке `solution` от `v0`. Сессию можно продолжать между днями. `library-eval` в эту сессию не подключается: внедряющий не должен подгонять решение под эталон.

### 5.1. Структура

```
library-erp/
  knowledge/
    rules/*.yaml          # правила (формат из решения, раздел 3.3)
    model/                # сгенерированные слои: db.json, code.json, events.json, bpm.json
    index.sqlite          # собирается скриптом, не коммитится
  tools/knowledge/
    extract_db.py         # интроспекция Postgres: таблицы, FK, CHECK, UNIQUE, триггеры, функции
    extract_code.py       # AST + Base.metadata SQLAlchemy: символы, вызовы, кто пишет в какую таблицу
    extract_events.py     # публикации и подписки по libs/events: топик -> издатели/подписчики
    extract_bpm.py        # узлы и переходы из bpm/*.yaml
    build_index.py        # сборка графа в SQLite
    drift.py              # хэши по нормализованному AST + транзитивно по вызовам
    check_rules.py        # проверка @rule-аннотаций (Ruff пользовательских правил не поддерживает)
    render_docs.py        # генерация docs/ (MkDocs + Mermaid)
    prompts/extract_rules.md
  mcp/knowledge_server.py # FastMCP: find_entry, impact, rule, entity, who_can
  AGENTS.md               # инструкции из решения, раздел 5.5
  CLAUDE.md -> AGENTS.md
  .claude/agents/context-scout.md   # субагент-разведчик
  .github/workflows/knowledge.yml   # CI из решения, раздел 6
```

Поправки к решению, которые сразу закладываются в модель:
- узлы `service`, `event`, `bpm_node` и рёбра `publishes`, `consumes`, `transitions_to`;
- `impact` ограничивается бюджетом токенов и приоритетом типов рёбер, глубина — только верхний предел.

### 5.2. Лог MCP-сервера

Каждый вызов инструмента пишется строкой в файл из `EVAL_MCP_LOG`. Без переменной логирование выключено.

```json
{"ts":"…","run_id":"…","tool":"impact","args":{"node":"R-VENUE-CHANGE-05","depth":3},
 "response_tokens":3120,"nodes_returned":["R-VENUE-CHANGE-06","chk_venue_change_allowed","…"],"ms":84}
```

### 5.3. Bootstrap

Детерминированные шаги — без Claude:

```bash
cd library-erp
uv run python tools/knowledge/extract_db.py
uv run python tools/knowledge/extract_code.py
uv run python tools/knowledge/extract_events.py
uv run python tools/knowledge/extract_bpm.py
```

Извлечение правил — #6: новая headless-сессия на каждый модуль (как требует решение), профиль исполнителя:

```bash
for MOD in applications billing scheduling notifications chat; do
  CLAUDE_CONFIG_DIR=$(mktemp -d) claude -p "$(sed "s/{{MODULE}}/$MOD/" tools/knowledge/prompts/extract_rules.md)" \
    --model "$WORKER_MODEL" --output-format stream-json --verbose \
    --permission-mode acceptEdits \
    > ../library-eval/logs/bootstrap/$MOD.jsonl                     # [сверить] флаги
done
uv run python tools/knowledge/build_index.py && uv run python tools/knowledge/render_docs.py
```

Проверка `draft`-правил — #7, интерактив. Человек ставит `verified` по выборке из 20–30 правил, остальные остаются `draft`.

### 5.4. Ветки вариантов

| Ветка | Содержимое | MCP |
|---|---|---|
| `variant/B0` | `v0`, без документации | нет |
| `variant/B1` | `v0` + `docs/` (те же сгенерированные md, что в S) + AGENTS.md «документация в docs/, ищи grep» | нет |
| `variant/S` | всё из 5.1 | knowledge |
| `variant/SMB` | `variant/S` + `memory-bank/` и память Ruflo, заполненные по проекту | knowledge |

В B1 те же тексты, что генерирует решение. Так сравнивается **способ доставки** контекста, а не качество текстов.

Память Ruflo и Memory Bank в SMB должны жить **внутри репозитория** (в ветке). Тогда каждый прогон получает одинаковое начальное состояние, а серия задач — накопленное. Если Ruflo хранит память в глобальном каталоге, её нужно перенаправить в репозиторий. [сверить]

```bash
git tag v1                          # коммит с внедрённым решением
git branch variant/B0 v0
git branch variant/B1 v0 && …       # добавить docs/ и AGENTS.md
git branch variant/S  v1
git branch variant/SMB v1 && …      # ruflo init, memory-bank   [сверить]
```

MCP-конфиги лежат в стенде, вариант выбирается флагом запуска:

```
library-eval/mcp/
  none.json   {"mcpServers":{}}
  S.json      {"mcpServers":{"knowledge":{"command":"uv","args":["run","python","mcp/knowledge_server.py"]}}}
```

**Готово, если:**
- `find_entry` и `impact` отвечают в headless-сессии с `--mcp-config library-eval/mcp/S.json`;
- в `EVAL_MCP_LOG` пишутся строки;
- CI-проверки проходят на `v1`;
- `docs/` сгенерирован.

---

## 6. Фаза 5: аудит bootstrap

**Запуск:** #8 — новая headless-сессия, профиль аудитора, cwd `wt/audit-v1`, `--add-dir library-eval/ground_truth`.

```bash
git -C library-erp worktree add ../wt/audit-v1 v1
library-eval/scripts/audit.sh --mode score --phase bootstrap --worktree wt/audit-v1
```

Здесь аудитор один раз строит `mapping.json` — сопоставление ID модели с ID эталона. Дальше по нему детерминированно считается recall в каждом прогоне.

Если recall по какой-то H-категории близок к нулю, задачи с этой категорией в фазе 6 провалятся предсказуемо. Сначала чинится экстрактор (продолжение сессии #5), затем bootstrap и этот аудит повторяются.

---

## 7. Фаза 6: разработка

### 7.1. Матрица

| Измерение | Значения |
|---|---|
| Задачи | T01–T08 |
| Варианты | B0, B1, S, SMB (B2 получен в фазе 3) |
| Повторы | 3 |

Итого 8 × 4 × 3 = 96 прогонов + 96 аудитов. Сначала пилот (раздел 10).

### 7.2. Прогон задачи — `run_task.sh`

**Запуск:** #9 и #10 — для исполнителя и аудитора всегда новые headless-сессии; свой worktree, своя БД, свой пустой конфиг.

```bash
#!/usr/bin/env bash
# library-eval/scripts/run_task.sh TASK VARIANT REP
set -euo pipefail
TASK=$1 VARIANT=$2 REP=$3
EVAL=$(cd "$(dirname "$0")/.." && pwd); REPO=$EVAL/../library-erp
RUN_ID="$(date +%Y%m%d-%H%M%S)-$TASK-$VARIANT-r$REP"
RUN_DIR=$EVAL/logs/$RUN_ID; WT=$EVAL/../wt/$RUN_ID
mkdir -p "$RUN_DIR"
export COMPOSE_PROJECT_NAME="run_${RUN_ID//[^a-z0-9]/_}"

# 1. Чистое состояние: worktree от ветки варианта, пустая БД
git -C "$REPO" worktree add -q -b "run/$RUN_ID" "$WT" "variant/$VARIANT"
(cd "$WT" && docker compose up -d --wait && uv run alembic upgrade head)

# 2. Исполнитель: новая сессия, пустой конфиг, cwd = worktree
WORKER_HOME=$(mktemp -d); cp "$EVAL/profiles/worker/settings.json" "$WORKER_HOME/"
MCP=$EVAL/mcp/$([[ $VARIANT == S || $VARIANT == SMB ]] && echo S || echo none).json
export EVAL_RUN_ID=$RUN_ID EVAL_MCP_LOG=$RUN_DIR/mcp.jsonl
START=$(date +%s)
(cd "$WT" && CLAUDE_CONFIG_DIR=$WORKER_HOME \
  claude -p "$(cat "$EVAL/ground_truth/tasks/$TASK.prompt.md")" \
    --model "$WORKER_MODEL" --output-format stream-json --verbose \
    --mcp-config "$MCP" --strict-mcp-config \
    --permission-mode acceptEdits --allowedTools "Bash(uv run:*)" \
  > "$RUN_DIR/transcript.jsonl")                                     # [сверить] флаги
echo "{\"wall_seconds\": $(( $(date +%s) - START ))}" > "$RUN_DIR/timing.json"
rm -rf "$WORKER_HOME"

# 3. Результат. Скрытые тесты попадают в worktree только после завершения сессии.
git -C "$WT" add -A && git -C "$WT" diff --cached "variant/$VARIANT" > "$RUN_DIR/diff.patch"
(cd "$WT" && uv run pytest tests -q --junitxml="$RUN_DIR/junit-visible.xml") || true
cp -R "$EVAL/hidden_tests" "$WT/_hidden"
(cd "$WT" && uv run pytest _hidden -q --junitxml="$RUN_DIR/junit-hidden.xml") || true
rm -rf "$WT/_hidden"
(cd "$WT" && uv run python tools/knowledge/drift.py --json > "$RUN_DIR/drift.json") 2>/dev/null || true

# 4. Метрики: сначала детерминированные, потом аудитор (новая сессия, тот же worktree)
uv run --project "$EVAL" python "$EVAL/scripts/collect_run.py" "$RUN_DIR" "$TASK" "$VARIANT" "$REP"
"$EVAL/scripts/audit.sh" --mode score --phase task --run "$RUN_DIR" --worktree "$WT"

# 5. Уборка
(cd "$WT" && docker compose down -v)
git -C "$REPO" worktree remove --force "$WT"
```

Прогоны по умолчанию идут **последовательно**. Параллельный запуск возможен благодаря `COMPOSE_PROJECT_NAME`, но тогда в `docker-compose.yml` не должно быть фиксированных портов.

### 7.3. `audit.sh` — запуск аудитора

```bash
# library-eval/scripts/audit.sh (суть)
AUDITOR_HOME=$(mktemp -d); cp "$EVAL/profiles/auditor/settings.json" "$AUDITOR_HOME/"
ADD_DIRS=()
[[ $MODE == score ]] && ADD_DIRS+=(--add-dir "$EVAL/ground_truth")
[[ -n ${RUN_DIR:-} ]] && ADD_DIRS+=(--add-dir "$RUN_DIR")

(cd "$WORKTREE" && CLAUDE_CONFIG_DIR=$AUDITOR_HOME \
  claude -p "$(cat "$EVAL/agents/context-auditor.md")
RUN_ID=$RUN_ID TASK_ID=$TASK VARIANT=$VARIANT MODE=$MODE" \
    --model "$AUDITOR_MODEL" --output-format json \
    "${ADD_DIRS[@]}" --strict-mcp-config --mcp-config "$EVAL/mcp/none.json" \
    --allowedTools "Read,Grep,Glob" --disallowedTools "Edit,Write,Bash" \
  > "$RUN_DIR/auditor_raw.json")                                     # [сверить] флаги
rm -rf "$AUDITOR_HOME"

# JSONL до ---SUMMARY--- дописывается в audit.jsonl, остальное — в summary.md
jq -r '.result' "$RUN_DIR/auditor_raw.json" | awk '/^---SUMMARY---$/{s=1;next} !s' >> "$RUN_DIR/audit.jsonl"
jq -r '.result' "$RUN_DIR/auditor_raw.json" | awk 's; /^---SUMMARY---$/{s=1}' > "$RUN_DIR/summary.md"
```

Ключевые свойства аудитора:
- **Нет инструментов записи и MCP.** Он не может ничего изменить и не видит модель знаний через `impact`: читает её файлы напрямую.
- **В слепом режиме** (`blind`) у него нет `--add-dir` на эталон.
- **Своя модель.** `AUDITOR_MODEL` — самая сильная доступная модель. Для выборочной проверки второй судья запускается тем же скриптом с другой моделью Claude.
- **Ruflo.** Если аудитора нужно запускать через Ruflo, агент регистрируется в Ruflo-конфиге `library-eval`, а не `library-erp`. [сверить] Тогда этот блок `audit.sh` заменяется вызовом Ruflo с теми же ограничениями: новая сессия, cwd, add-dir, только чтение.

### 7.4. `collect_run.py` — детерминированные метрики

Читает `transcript.jsonl`, `mcp.jsonl`, `junit-*.xml`, `diff.patch` и дописывает строки в `audit.jsonl` с `"method":"deterministic"`:

| Метрика | Как вычисляется |
|---|---|
| `tokens_total`, `cost_usd` | итоговое событие `result` в stream-json |
| `tokens_context` | сумма usage сообщений до первого вызова Edit/Write |
| `files_read_whole` | вызовы Read без offset/limit по файлам длиннее 200 строк + `cat` в Bash |
| `mcp_calls_before_edit` | вызовы `find_entry`/`impact` до первого изменения — для compliance |
| `scout_used` | был ли вызов субагента `context-scout` |
| `pack_tokens` | `response_tokens` вызовов `impact` |
| `impact_recall`, `hidden_link_recall` | `nodes_returned` ∪ прочитанные символы против `expected_nodes` через `mapping.json` |
| `task_success` | все `hidden_tests/tasks/test_<task>.py` зелёные |
| `regressions` | число упавших `hidden_tests/regression/*` |

### 7.5. Серия задач подряд

**Запуск:** #11 и #12. Один worktree `wt/series-<V>` на всю серию. Каждая задача — **новая** headless-сессия с новым пустым конфигом. БД не пересоздаётся между задачами: миграции накапливаются, как в жизни.

```bash
# library-eval/scripts/run_series.sh VARIANT   (S или SMB)
git -C "$REPO" worktree add -b "series/$VARIANT" "$WT" "variant/$VARIANT"
for TASK in T01 T02 T03 T04 T05 T06 T07; do
  run_worker "$TASK"                      # тот же блок, что шаг 2 в run_task.sh
  run_ci_checks || log_ci_failure         # CI-проверки решения: drift, @rule, миграции
  git -C "$WT" add -A && git -C "$WT" commit -qm "series: $TASK"
  run_hidden_tests "$TASK"                # скрытые тесты: копируются, прогоняются, удаляются
  audit.sh --mode score --phase bootstrap --worktree "$WT"   # метрики 4.1 + Doc QA после каждой задачи
done
```

Модель знаний вручную не пересобирается: только то, что агент сделал по AGENTS.md, и то, что пропустил CI.

Скрытые тесты задач проверяют поведение только «своей» задачи. Если следующая задача серии меняет то же поведение, ожидания корректируются в `tasks/T*.yaml`. Это надо проверить при подготовке эталона.

---

## 8. Фаза 7: мутации

**Запуск:** #13 — без Claude.

```bash
# library-eval/scripts/run_mutations.sh
for m in "$EVAL"/mutations/*.patch; do
  WT=$EVAL/../wt/mut-$(basename "$m" .patch)
  git -C "$REPO" worktree add -q "$WT" variant/S
  git -C "$WT" apply "$m"
  (cd "$WT" && uv run python tools/knowledge/drift.py --json) > "$EVAL/logs/mutations/$(basename "$m" .patch).json"
  git -C "$REPO" worktree remove --force "$WT"
done
uv run python "$EVAL/scripts/score_mutations.py"   # сверка с mutations/expected.yaml → drift_recall, drift_fp_rate
```

Обязательные мутации: перенос логики в helper и чистый `ruff format` (`evaluation_plan.md`, 4.4).

---

## 9. Фаза 8: сборка результатов

**Запуск:** #14 — агрегация без Claude; #15 — текст отчёта, новая сессия в `library-eval/logs/`.

### 9.1. Агрегация

```sql
-- library-eval/scripts/aggregate.sql  (duckdb, cwd = library-eval)
CREATE TABLE m AS SELECT * FROM read_json_auto('logs/*/audit.jsonl', union_by_name=true);

-- Сводка по вариантам: среднее и разброс по повторам
SELECT variant, metric, round(avg(value),3) AS mean, round(stddev_samp(value),3) AS sd, count(*) AS n
FROM m WHERE phase IN ('context','result','discipline')
GROUP BY ALL ORDER BY metric, variant;

-- Скрытые связи по категориям
SELECT variant, hidden_category, round(avg(value),3) AS recall
FROM m WHERE metric='hidden_link_recall_by_category'
GROUP BY ALL ORDER BY hidden_category, variant;

-- Почему пропускаются связи
SELECT variant, reason, count(*) FROM m WHERE metric='miss_reason' GROUP BY ALL ORDER BY 3 DESC;

-- Деградация в серии
SELECT variant, task_id, metric, value FROM m
WHERE phase='series' AND metric IN ('rule_recall','doc_qa_accuracy') ORDER BY variant, task_id;
```

```bash
cd library-eval && duckdb < scripts/aggregate.sql > logs/summary.txt
uv run python scripts/make_report.py      # таблицы → report.md
```

### 9.2. Структура `report.md`

1. **Вердикт** в одном абзаце: находит ли S скрытые связи лучше B1 при токенах заметно меньше B2.
2. Таблица вариантов: hidden-link recall, impact recall и precision, токены на контекст и всего, task success, регрессии.
3. Recall по категориям H1–H7.
4. Причины пропусков → что чинить в решении.
5. Документирование: метрики 4.1 после bootstrap и в конце серии.
6. Drift: recall и ложные срабатывания по типам мутаций.
7. SMB против S: помогают Memory Bank и Ruflo или дублируют и мешают.
8. Стоимость: bootstrap, средний прогон, аудит.

### 9.3. Как читать результат

| Результат | Вывод |
|---|---|
| S ≈ B1 по hidden-link recall | граф не даёт выигрыша: смотреть причины пропусков, скорее всего неполный bootstrap |
| S ≥ B2 по recall при токенах ≪ B2 | главное утверждение решения подтверждено |
| высокий recall pack, но низкий task success | контекст доставлен, но агент его не использует: инструкции и compliance |
| высокий `depth_cutoff` | менять стратегию обхода в `impact` |
| высокий `wrong_entry` | улучшать `find_entry` (эмбеддинги, синонимы, словарь домена) |
| деградация в серии | процесс поддержки актуальности не работает, править CI и AGENTS.md |

---

## 10. Пилот

| Что | Значение |
|---|---|
| Задачи | T01 (много скрытых связей), T04 (цепочка событий), T08 (контрольная) |
| Варианты | B1, S |
| Повторы | 2 |
| Итого | 12 прогонов + 12 аудитов, без серии и мутаций |

Пилот успешен, если:
- все логи на месте и `aggregate.sql` даёт заполненную таблицу;
- в транскриптах исполнителя нет следов graphify, личной памяти и чужих MCP (проверка изоляции);
- человек (сессия #16) проверил 15–20% LLM-оценок аудитора и согласен с ≥ 90%;
- скрытые тесты различают решённую и нерешённую задачу;
- хотя бы на T01 видна разница между B1 и S (в любую сторону) — иначе задача или эталон не чувствительны.

После пилота: разобрать проблемы, затем полная матрица, серия и мутации.

---

## 11. Журнал выполнения

### 2026-10-22: фазы 1–3 выполнены

**Фаза 1.**
- Python 3.14, uv, Docker уже стояли; поставлен duckdb.
- Claude Code обновлён 2.1.168 → 2.1.308: старая версия не поддерживает `claude-opus-5-5`.
- Изоляция на подписке проверена до и после обновления (раздел 1.3).
- Ruflo не ставился: он нужен только варианту SMB, а SMB не входит в пилот.

**Фаза 2.** `library-erp@v0` и эталон в `library-eval`.
- Состав проекта:
  - 5 сервисов, outbox-события, BPM в YAML, 6 схем БД с триггерами;
  - 3,8 тыс. строк, около 45 тыс. токенов;
  - 36 видимых тестов.
- Эталон: 68 правил, 20 событий, задачи T01–T08, 30 вопросов Doc QA.
- Скрытые тесты: 47 регрессионных и 23 теста задач.
- Каждая задача проверена эталонным решением (`library-eval/reference/T*.patch`). На `v0` тесты задач красные. На эталонном решении они зелёные, а в регрессии падают только тесты из `supersedes`.
- `scripts/validate_ground_truth.py` проверяет, что все ссылки эталона существуют в коде.

**Фаза 3.** Слепой аудит всех задач.
- Стоимость: около $0.9 на задачу, всего $6.8; 1–2,5 минуты на задачу.
- Итог до разбора: recall 44/45, скрытые связи 28/28.
- При разборе в эталон добавлено 34 узла из находок аудитора (помечены `source: blind_audit`). После этого recall B2 равен 1.0 частично по построению.

**Изменения сценария по ходу выполнения:**
1. **Клон вместо git worktree для каждого прогона** (`git clone --single-branch --no-tags`). Ветки эталонных решений и прошлых прогонов в общем репозитории видны исполнителю через `git log --all`; клон с одной веткой их не содержит.
2. **Промпт аудитора передаётся через stdin, frontmatter определения агента отрезается.** Иначе CLI принимает `---` за опцию.
3. **`library-eval/scripts/lib.sh` — только для bash.** В zsh `BASH_SOURCE` пустой.
4. **Общий compose-проект `aidd`.** Все клоны используют одну пару контейнеров, прогоны идут последовательно.
5. **Отдельная папка `~/work/ai-dd/handoff` для фазы 4.** В ней решение, общая схема `erp-library.md` и промпт. `evaluation_plan.md` содержит примеры заложенных связей, поэтому внедряющему его не показываем.

**Наблюдение, важное для выводов.** Проект маленький: вся кодовая база (около 45 тыс. токенов) помещается в контекст, и полный проход стоит около $0.9. Поэтому экономия токенов от context pack на этом стенде будет скромной. Главное, что здесь можно измерить, — полноту поиска скрытых связей у исполнителя, который не читает всё подряд. Чтобы проверить экономию, нужен проект в 5–10 раз больше: например, сгенерировать дополнительные сервисы-«шум» без связей с задачами.

### 2026-10-23: Ruflo в стенде

- **Установка.** Ruflo 3.59.7 стоит локально в `library-eval` (`package.json`, точная версия). Автообновление выключено через `CLAUDE_FLOW_AUTO_UPDATE=false` в `lib.sh` и `.mcp.json`. `.mcp.json` переведён с `npx -y ruflo@latest` на локальный пакет.
- **`init`.** Выполнен с флагами `--no-global --no-signup --no-skills-sh --no-mods --no-plugin-install --no-codex-detect`. Глобальные настройки Claude Code (`~/.claude/CLAUDE.md`, `settings.json`, плагины, skills, MCP) сверены по отпечатку до и после: не изменились.
- **Аудитор.** `context-auditor` зарегистрирован в Ruflo стенда, Claude Code в `library-eval` его видит. Источник определения один — `agents/context-auditor.md`.
- **Память аудитов.** `audit.sh` пишет итог каждого аудита в память Ruflo (`library-eval/.swarm`, пространство `audit`). Хранилище своё у каждой папки: SMB-исполнитель в своём клоне его не увидит.
- **Побочный эффект.** Интерактивные сессии в `library-eval` (разбор, ручная проверка аудитора) теперь идут с хуками и `CLAUDE.md` Ruflo и подмешивают память аудитов. Для разбора это допустимо. Сами аудиты от этого изолированы: cwd — клон проекта, `CLAUDE.md` исключён профилем.
- **Вариант SMB ещё не собран.** Его собирают после `v1`: `ruflo init` с теми же флагами в ветке `variant/SMB`, MCP-сервер Ruflo в `mcp/SMB.json`, память — в `.swarm` клона серии, выгрузка `memory list/export` после каждой задачи.

### 2026-10-23: фаза 9 — большой проект (в работе)

**Цель.** Проверить главное обещание решения — выигрыш в поиске связей и токенах — на проекте, который не помещается в «прочитать всё».

**Как устроено:**
- **`large/v0`** = `v0` + 8 платформенных сервисов того же домена: `halls`, `subscriptions`, `inventory`, `lectures`, `marketing`, `staff`, `partners`, `reports`. Генерация — headless-сессии по спецификациям `library-eval/noise/` (скрипт `gen_noise.sh`).
- **Двойники.** В сервисы специально заложены двойники механизмов из задач: своя смена площадки с триггером, свои шаблоны писем с CHECK и словарём групп (в том числе `debt → paid`), свои сроки в 30 дней с литералом в фоновой задаче, своя дедупликация с `_same_track`, свои обязательные поля и слушатели ORM, свой лимит мест с триггером по реплике, свои API с полем `body`. Поиск по словам находит их наравне с настоящими местами.
- **Эталон не меняется.** Сервисы не импортируют ядро, не подписываются на его топики и не ссылаются на его таблицы — ожидаемые узлы задач остаются верными. Скрипт генерации проверяет, что файлы менялись только в разрешённых путях.
- **Изменения в ядре — минимальные.** Миграции новых сервисов — отдельная `0000` до ядра, поэтому эталонные патчи задач применяются без изменений. Подписчики подключаются автоматически. Тестовый `conftest` (и скрытый) удаляет все несистемные схемы.
- **`large/v1`** = `large/v0` + решение из `v1` (`tools/`, `mcp/`, `knowledge/`, инструкции) + bootstrap решения по 8 новым сервисам — механический запуск `bootstrap_rules.sh rules <сервисы>`, без правок решения.
- **Прогоны.** B1L и SL × T01–T07 × 2 повтора, без аудитора: решающие метрики детерминированные (успех по скрытым тестам, полнота скрытых связей, токены).

**Отложено на свежую сессию:** ручная проверка 15–20% оценок аудитора (строка #16 карты) и правка категорий причин пропусков для B1 (аудитор ставит `depth_cutoff` вариантам без графа).
