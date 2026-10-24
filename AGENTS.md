# ERP библиотеки — инструкции для агентов (Claude Code и Codex)

`CLAUDE.md` — симлинк на этот файл: инструкции одни для обоих агентов.

## Проект

Python 3.14, FastAPI, async SQLAlchemy, Alembic, PostgreSQL. Микросервисы `services/*`
(applications, billing, scheduling, notifications, chat) общаются событиями: transactional outbox
(`libs/events`) → Redis Streams; в тестах события доставляет `events.dispatch_pending()`.
Процесс заявки описан в `bpm/application_process.yaml` и исполняется `libs/bpm/engine.py`.
Ограничения размазаны между кодом и БД: триггеры, CHECK и частичные индексы живут в `migrations/`.

```bash
docker compose up -d          # PostgreSQL и Redis
uv run pytest                 # тесты
uv run ruff check .           # линтер
```

## Модель знаний

Связи здесь проходят по смыслу, а не по словам: смена площадки аннулирует счёт через событие,
срок задаётся настройкой, запрет живёт в триггере БД. grep их пропускает. Поэтому есть граф знаний:

- `knowledge/rules/*.yaml` — бизнес-правила со стабильными ID (`R-…`), статусом
  (`verified` — проверено человеком, `draft` — извлечено LLM, `suspect` — код менялся после проверки),
  ссылками на код (`path::symbol` + строки), ограничения БД, настройки и тесты;
- `knowledge/model/*.json` — слои, извлечённые детерминированно: `db` (реальная схема после
  миграций), `code` (символы, вызовы, ORM-таблицы, Depends, слушатели ORM, настройки, тесты),
  `events` (publish/subscribe, эффекты), `bpm` (этапы, переходы, guard'ы, код, выполняющий переход);
- MCP-сервер `knowledge` (`.mcp.json`, `uv run python mcp/knowledge_server.py`) над ними;
- `docs/` — документация для людей, генерируется из модели.

Инструменты MCP:

| Инструмент | Когда |
|---|---|
| `find_entry(task_text)` | первым: формулировка задачи → узлы графа (правила, настройки, код, таблицы, события) |
| `impact(node)` | context pack от узла: правила, переходы и guard'ы, события и подписчики в других сервисах, триггеры и CHECK, код, настройки, письма/чат, тесты (≈4000 токенов) |
| `rule(id)` | полный текст правила, реализация, БД, тесты, drift |
| `entity(name)` | карточка таблицы: поля, ограничения, триггеры, кто пишет, правила |
| `who_can(action)` | роли и условия действия |

Для сбора контекста по нетривиальной задаче используй субагента `context-scout`
(`.claude/agents/context-scout.md`): он вызывает MCP и точечно читает код в своём окне
и возвращает сжатую выжимку.

## Перед любым изменением

1. Вызови `find_entry` с текстом задачи.
2. Вызови `impact` для каждого найденного узла, относящегося к задаче.
3. В плане явно перечисли затронутые правила по ID.
   Если правило в статусе `draft` или `suspect` — отметь это как риск и сверь с кодом.
4. Не читай файлы целиком, если `impact` указал конкретные символы и строки.
5. Проверь неочевидные места: подписчиков событий в других сервисах, триггеры и CHECK в миграциях,
   условия в `bpm/application_process.yaml` и guard'ы (`@bpm.guard`), настройки (`libs/settings.py`
   и константы модулей), слушатели ORM (`services/applications/listeners.py`), фоновые задачи (`jobs.py`),
   регистрацию модулей в `services/wiring.py`.

## После изменения

5. Обнови аннотации `# @rule R-…` в изменённом коде (комментарий над функцией или внутри неё;
   символ должен быть в `implemented_by` правила, тест — в `tested_by`).
6. Если изменилось поведение — предложи правку правила в `knowledge/rules/` (текст, ссылки, строки).
   Статус `verified` ставит только человек.
7. Пересобери модель и проверь:

```bash
uv run python tools/knowledge/build_index.py --all     # экстракторы (с БД) + индекс
uv run python tools/knowledge/drift.py --write         # хэши; правила с изменённым кодом -> suspect
uv run python tools/knowledge/check_rules.py           # ссылки правил и аннотации @rule
uv run python tools/knowledge/render_docs.py           # docs/ и блок L0 ниже
```

Не правь руками `docs/`, `knowledge/model/*.json` и блок L0 — они генерируются.
Новое ограничение в миграции без правила с `enforced_by_db` блокирует PR (CI).

## Codex

MCP-сервер для Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.knowledge]
command = "uv"
args = ["run", "--quiet", "python", "mcp/knowledge_server.py"]
```

<!-- BEGIN L0: генерируется render_docs.py -->
### Карта системы (L0)

Сервисы: **applications** — Заявки, клиенты, площадки (админка), процесс заявки, архив, дедупликация; **billing** — Счета, платежи, штрафы, закрепление бухгалтера; **scheduling** — Расписание площадок, ссылки и запись на визит, выдача и возврат книг; **notifications** — Письма клиенту и представителю по шаблонам; **chat** — Чат заявки и лента событий.

Этапы заявки по видам:
- debt: draft → on_review → awaiting_issue → books_out → closed
- paid: draft → on_review → awaiting_invoice → awaiting_payment → awaiting_issue → books_out → closed
- social: draft → on_review → awaiting_issue → books_out → closed
- вне пути: archived (архив, попытки), closed_duplicate (дубль)

Роли: Оператор (`operator`), Руководитель проверяющих (`reviewer_lead`), Проверяющий (`reviewer`), Бухгалтер (`accountant`), Главный бухгалтер (`chief_accountant`), Проверяющий оператор (`site_checker`), Администратор (`admin`), Клиент (`client`), Представитель клиента (`representative`), Система (события и фоновые задачи) (`system`).

Сущности: `applications.application_books`, `applications.applications`, `applications.attempts`, `applications.books`, `applications.clients`, `applications.prices`, `applications.representatives`, `applications.spheres`, `applications.venue_spheres`, `applications.venues`, `billing.accountant_assignments`, `billing.fine_rates`, `billing.fines`, `billing.invoices`, `billing.payments`, `chat.messages`, `events.outbox`, `halls.hall_booking_history`, `halls.hall_bookings`, `halls.hall_emails`, `halls.hall_invoices`, `halls.hall_managers`, `halls.hall_payments`, `halls.hall_templates`, `halls.halls`, `inventory.copies`, `inventory.custodians`, `inventory.ill_loans`, `inventory.ill_penalties`, `inventory.partner_libraries`, `inventory.stock_levels`, `inventory.transfers`, `inventory.write_offs`, `lectures.events`, `lectures.notifications`, `lectures.registrations`, `lectures.venue_capacity_limits`, `lectures.waitlist`, `marketing.audience_members`, `marketing.audiences`, `marketing.campaign_templates`, `marketing.campaigns`, `marketing.managers`, `marketing.sent_messages`, `marketing.unsubscriptions`, `notifications.emails`, `notifications.templates`, `partners.commissions`, `partners.contract_history`, `partners.contracts`, `partners.deals`, `partners.onboarding_requests`, `partners.partners`, `partners.payouts`, `reports.export_schedules`, `reports.metric_snapshots`, `reports.report_definitions`, `reports.report_runs`, `reports.run_notifications`, `scheduling.booking_links`, `scheduling.bookings`, `scheduling.holds`, `scheduling.loans`, `scheduling.slots`, `scheduling.venue_limits`, `staff.alerts`, `staff.assignments`, `staff.briefings`, `staff.clearance_kinds`, `staff.clearances`, `staff.employees`, `staff.shift_members`, `staff.shifts`, `staff.sites`, `subscriptions.invoices`, `subscriptions.notices`, `subscriptions.payments`, `subscriptions.plans`, `subscriptions.refunds`, `subscriptions.status_history`, `subscriptions.subscriptions`.

События: `application.archived`, `application.closed_duplicate`, `application.ready_for_booking`, `application.review_passed`, `application.stage_changed`, `application.unarchived`, `application.venue_changed`, `booking.cancelled`, `booking.created`, `books.issued`, `client.updated`, `halls.booking_cancelled`, `halls.booking_confirmed`, `halls.booking_created`, `halls.booking_held`, `halls.booking_prepaid`, `halls.invoice_issued`, `halls.payment_received`, `halls.venue_changed`, `inventory.copy_damaged`, `inventory.copy_lost`, `inventory.copy_registered`, `inventory.copy_relocated`, `inventory.copy_written_off`, `inventory.ill_issued`, `inventory.ill_overdue`, `inventory.ill_penalty_accrued`, `inventory.ill_returned`, `inventory.partner_resumed`, `inventory.partner_suspended`, `inventory.transfer_cancelled`, `inventory.transfer_received`, `inventory.transfer_shipped`, `invoice.cancelled`, `invoice.issued`, `lectures.capacity_increased`, `lectures.event_cancelled`, `lectures.event_moved`, `lectures.registration_cancelled`, `lectures.registration_created`, `lectures.seat_released`, `lectures.venue_limit_changed`, `lectures.waitlist_expired`, `lectures.waitlist_promoted`, `loan.damaged`, `loan.lost`, `loan.overdue`, `marketing.campaign_finished`, `marketing.campaign_launched`, `marketing.campaign_prepared`, `marketing.message_bounced`, `marketing.unsubscribed`, `partners.commission_accrued`, `partners.contract_activated`, `partners.contract_expired`, `partners.contract_rate_changed`, `partners.contract_resumed`, `partners.contract_suspended`, `partners.contract_terminated`, `partners.credit_overdue`, `partners.deal_cancelled`, `partners.deal_closed`, `partners.deal_created`, `partners.deal_paid`, `partners.partner_onboarded`, `partners.payout_closed`, `partners.request_approved`, `partners.request_closed_duplicate`, `partners.request_rejected`, `partners.request_submitted`, `payment.fully_paid`, `payment.linked`, `payment.refunded`, `reports.definition_deactivated`, `reports.run_cancelled`, `reports.run_completed`, `reports.run_failed`, `reports.run_requested`, `staff.clearance_expired`, `staff.clearance_granted`, `staff.clearance_revoked`, `staff.employee_dismissed`, `staff.employee_hired`, `staff.employee_transferred`, `staff.employee_updated`, `staff.shift_member_removed`, `staff.shift_understaffed`, `subscriptions.activated`, `subscriptions.closed_duplicate`, `subscriptions.created`, `subscriptions.expired`, `subscriptions.grace_started`, `subscriptions.holder_rejected`, `subscriptions.holder_updated`, `subscriptions.invoice_issued`, `subscriptions.payment_completed`, `subscriptions.refund_required`, `subscriptions.renewed`, `venue.settings_changed`.

Правил в модели: 478 (draft: 456, verified: 22).
<!-- END L0 -->
