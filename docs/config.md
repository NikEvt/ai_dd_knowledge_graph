<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Настройки и фоновые задачи

## Настройки и константы, влияющие на поведение

| Настройка | Значение | Описание | Кто читает |
|---|---|---|---|
| [`engine.py::PROCESS_FILE`](../libs/bpm/engine.py#L13) | `Path(__file__).resolve().parents[2] / 'bpm' / 'application_process.yaml'` |  | [`engine.py::process`](../libs/bpm/engine.py#L33) |
| [`relay.py::STREAM_PREFIX`](../libs/events/relay.py#L13) | `events:` |  | [`relay.py::consume_forever`](../libs/events/relay.py#L39)<br>[`relay.py::relay_forever`](../libs/events/relay.py#L16) |
| [`settings.py::CLIENT_RESCHEDULE_MIN_DAYS`](../libs/settings.py#L14) | `2` | Клиент может перенести или отменить визит не позднее чем за столько дней. | [`service.py::cancel_booking`](../services/scheduling/service.py#L193) |
| [`settings.py::DATABASE_URL`](../libs/settings.py#L4) | `os.environ.get('DATABASE_URL', f'postgresql+asyncpg://erp:erp@localhost:{DB_POR…` |  | [`db.py::engine`](../libs/db.py#L27) |
| [`settings.py::DB_PORT`](../libs/settings.py#L3) | `os.environ.get('DB_PORT', '55432')` |  | — |
| [`settings.py::LOAN_PERIOD_DAYS`](../libs/settings.py#L8) | `30` | Срок пользования книгами с даты выдачи. | [`service.py::issue_books`](../services/scheduling/service.py#L223) |
| [`settings.py::PAYMENT_ARCHIVE_DAYS`](../libs/settings.py#L12) | `30` | Платная заявка уходит в архив, если счёт не оплачен за столько дней. | [`jobs.py::archive_stale`](../services/applications/jobs.py#L14) |
| [`settings.py::REDIS_URL`](../libs/settings.py#L5) | `os.environ.get('REDIS_URL', f"redis://localhost:{os.environ.get('REDIS_PORT', '…` |  | [`relay.py::consume_forever`](../libs/events/relay.py#L39)<br>[`relay.py::relay_forever`](../libs/events/relay.py#L16) |
| [`settings.py::REVIEW_ARCHIVE_DAYS`](../libs/settings.py#L10) | `30` | Заявка уходит в архив, если с начала проверки прошло столько дней, а данные не получены. | [`jobs.py::archive_stale`](../services/applications/jobs.py#L14) |
| [`dedup.py::OPEN_STAGES`](../services/applications/dedup.py#L10) | `['draft', 'on_review', 'needs_rework', 'awaiting_invoice', 'awaiting_payment', …` |  | [`dedup.py::close_duplicates`](../services/applications/dedup.py#L25) |
| [`listeners.py::TRACKED_FIELDS`](../services/applications/listeners.py#L9) | `['full_name', 'passport', 'birth_date']` |  | [`listeners.py::_domain_events`](../services/applications/listeners.py#L13) |
| [`review.py::REQUIRED_CLIENT_FIELDS`](../services/applications/review.py#L3) | `['full_name', 'passport', 'birth_date']` |  | [`review.py::missing_client_fields`](../services/applications/review.py#L6) |
| [`service.py::CLIENT_EDITABLE_FIELDS`](../services/applications/service.py#L28) | `['full_name', 'passport', 'birth_date', 'email']` |  | [`service.py::update_client`](../services/applications/service.py#L131) |
| [`service.py::PAID_VENUE_LOCKED_STAGES`](../services/applications/service.py#L26) | `['awaiting_issue', 'books_out']` |  | [`service.py::change_venue`](../services/applications/service.py#L199) |
| [`service.py::TERMINAL_STAGES`](../services/applications/service.py#L27) | `['closed', 'closed_duplicate']` |  | [`service.py::change_venue`](../services/applications/service.py#L199) |
| [`service.py::CENT`](../services/billing/service.py#L14) | `Decimal('0.01')` |  | [`service.py::issue_books_invoice`](../services/billing/service.py#L35) |
| [`consumers.py::EVENT_TEXT`](../services/chat/consumers.py#L8) | `{'application.archived': 'Заявка ушла в архив ({outcome})', 'application.closed…` |  | [`consumers.py::<module>`](../services/chat/consumers.py#L1) |
| [`service.py::NO_CHAT_ROLES`](../services/chat/service.py#L12) | `['chief_accountant', 'reviewer_lead']` |  | [`service.py::list_messages`](../services/chat/service.py#L48) |
| [`service.py::CENT`](../services/halls/service.py#L24) | `Decimal('0.01')` |  | [`service.py::rent_amount`](../services/halls/service.py#L137) |
| [`settings.py::ACTIVE_STATUSES`](../services/halls/settings.py#L28) | `['draft', 'prepaid', 'confirmed']` | Статусы, в которых бронь занимает зал. | [`service.py::_check_hall_free`](../services/halls/service.py#L110)<br>[`service.py::deactivate_hall`](../services/halls/service.py#L71) |
| [`settings.py::BOOKING_HORIZON_DAYS`](../services/halls/settings.py#L10) | `365` | ...и не дальше чем на столько дней вперёд. | [`service.py::_check_period`](../services/halls/service.py#L97) |
| [`settings.py::CLEANUP_MINUTES`](../services/halls/settings.py#L15) | `60` | Время на уборку зала между мероприятиями. | [`service.py::_check_hall_free`](../services/halls/service.py#L110) |
| [`settings.py::EVENT_KINDS`](../services/halls/settings.py#L25) | `tuple(TEMPLATE_GROUP)` |  | [`service.py::create_booking`](../services/halls/service.py#L142) |
| [`settings.py::MAX_DURATION_HOURS`](../services/halls/settings.py#L13) | `12` |  | [`service.py::_check_period`](../services/halls/service.py#L97) |
| [`settings.py::MIN_DURATION_HOURS`](../services/halls/settings.py#L12) | `2` | Длительность аренды, часы. | [`service.py::_check_period`](../services/halls/service.py#L97) |
| [`settings.py::MIN_LEAD_DAYS`](../services/halls/settings.py#L8) | `2` | Бронировать зал можно не раньше чем за столько дней до мероприятия... | [`service.py::_check_period`](../services/halls/service.py#L97) |
| [`settings.py::PREPAY_SHARE`](../services/halls/settings.py#L4) | `Decimal('0.5')` | Доля счёта, после оплаты которой бронь считается предоплаченной. | [`service.py::apply_payments`](../services/halls/service.py#L372) |
| [`settings.py::TEMPLATE_GROUP`](../services/halls/settings.py#L18) | `{'birthday': 'private', 'conference': 'corporate', 'corporate': 'corporate', 'p…` | Группа шаблонов писем по виду мероприятия. | [`service.py::find_template`](../services/halls/service.py#L421)<br>[`service.py::set_template`](../services/halls/service.py#L399) |
| [`settings.py::UNPAID_CANCEL_DAYS`](../services/halls/settings.py#L6) | `30` | Бронь без предоплаты отменяется через столько дней после создания. | [`jobs.py::cancel_unpaid`](../services/halls/jobs.py#L10) |
| [`models.py::ON_BALANCE`](../services/inventory/models.py#L12) | `['available', 'on_loan', 'in_transit']` | Состояния, в которых экземпляр ещё числится в фонде площадки | [`service.py::recount_stock`](../services/inventory/service.py#L106) |
| [`models.py::OPEN_TRANSFER`](../services/inventory/models.py#L13) | `['requested', 'in_transit']` |  | [`service.py::_open_transfer`](../services/inventory/service.py#L62)<br>[`service.py::cancel_transfer`](../services/inventory/service.py#L231) |
| [`service.py::DAY`](../services/inventory/service.py#L28) | `timedelta(days=1)` |  | [`service.py::days_late`](../services/inventory/service.py#L31) |
| [`service.py::INVENTORY_NO`](../services/inventory/service.py#L27) | `re.compile('^[А-ЯA-Z]{1,4}-\\d{4,8}$')` |  | [`service.py::register_copy`](../services/inventory/service.py#L75) |
| [`settings.py::ILL_LOAN_PERIOD_DAYS`](../services/inventory/settings.py#L4) | `30` | Срок выдачи экземпляра другой библиотеке по МБА. | [`service.py::issue_ill`](../services/inventory/service.py#L279)<br>[`service.py::renew_ill`](../services/inventory/service.py#L331) |
| [`settings.py::ILL_LOST_COMPENSATION`](../services/inventory/settings.py#L11) | `Decimal('1500.00')` | Компенсация за экземпляр, утерянный библиотекой-партнёром. | [`service.py::charge_lost_copy`](../services/inventory/service.py#L489) |
| [`settings.py::ILL_MAX_RENEWALS`](../services/inventory/settings.py#L7) | `1` |  | [`service.py::renew_ill`](../services/inventory/service.py#L331) |
| [`settings.py::ILL_PARTNER_DEBT_LIMIT`](../services/inventory/settings.py#L13) | `Decimal('1000.00')` | Партнёр с неоплаченными пенями больше этой суммы не получает новых выдач. | [`service.py::issue_ill`](../services/inventory/service.py#L279)<br>[`service.py::review_partner_debt`](../services/inventory/service.py#L534)<br>[`service.py::settle_penalty`](../services/inventory/service.py#L516) |
| [`settings.py::ILL_PENALTY_MAX_DAYS`](../services/inventory/settings.py#L9) | `90` | Пени начисляются не более чем за столько дней просрочки. | [`service.py::accrue_overdue`](../services/inventory/service.py#L467) |
| [`settings.py::ILL_RENEWAL_DAYS`](../services/inventory/settings.py#L6) | `14` | Продление выдачи по МБА: на сколько дней и сколько раз. | [`service.py::renew_ill`](../services/inventory/service.py#L331) |
| [`settings.py::MIN_COPIES_ON_VENUE`](../services/inventory/settings.py#L18) | `1` | Сколько экземпляров одного издания площадка обязана оставить у себя при перемещении. | [`service.py::request_transfer`](../services/inventory/service.py#L152) |
| [`settings.py::TRANSFER_REQUEST_TTL_DAYS`](../services/inventory/settings.py#L16) | `14` | Заявка на перемещение, не отправленная за столько дней, отменяется. | [`jobs.py::expire_stale_transfers`](../services/inventory/jobs.py#L50) |
| [`service.py::SEAT_RELEASING_REASONS`](../services/lectures/service.py#L15) | `['listener', 'organizer']` | Причины отмены, после которых место на том же мероприятии снова свободно. | [`consumers.py::on_registration_cancelled`](../services/lectures/consumers.py#L39) |
| [`settings.py::FINISH_AFTER`](../services/lectures/settings.py#L14) | `timedelta(hours=3)` | Мероприятие считается прошедшим через столько после начала. | [`jobs.py::finish_past_events`](../services/lectures/jobs.py#L62) |
| [`settings.py::MAX_ACTIVE_REGISTRATIONS`](../services/lectures/settings.py#L8) | `3` | Сколько действующих регистраций на будущие мероприятия может быть у одного слушателя. | [`service.py::register`](../services/lectures/service.py#L292) |
| [`settings.py::MIN_LEAD_TIME`](../services/lectures/settings.py#L4) | `timedelta(hours=24)` | Мероприятие можно объявить не позднее чем за столько до начала. | [`service.py::create_event`](../services/lectures/service.py#L126) |
| [`settings.py::REGISTRATION_CLOSES_BEFORE`](../services/lectures/settings.py#L6) | `timedelta(hours=1)` | Регистрация и продвижение из листа ожидания закрываются за столько до начала. | [`jobs.py::close_waitlists`](../services/lectures/jobs.py#L11)<br>[`service.py::_registration_open`](../services/lectures/service.py#L50) |
| [`settings.py::REMINDER_AHEAD`](../services/lectures/settings.py#L12) | `timedelta(hours=24)` | Напоминание слушателям рассылается за столько до начала. | [`jobs.py::send_reminders`](../services/lectures/jobs.py#L36) |
| [`settings.py::WAITLIST_MAX_SIZE`](../services/lectures/settings.py#L10) | `20` | Длина листа ожидания одного мероприятия. | [`service.py::join_waitlist`](../services/lectures/service.py#L387) |
| [`service.py::NOT_STARTED`](../services/marketing/service.py#L22) | `['draft', 'scheduled']` |  | [`service.py::cancel_campaign`](../services/marketing/service.py#L281)<br>[`service.py::schedule_campaign`](../services/marketing/service.py#L269)<br>[`service.py::send_test_message`](../services/marketing/service.py#L452)<br>[`service.py::start`](../services/marketing/service.py#L295) |
| [`service.py::RUNNING`](../services/marketing/service.py#L23) | `['preparing', 'sending']` |  | [`service.py::archive_audience`](../services/marketing/service.py#L87)<br>[`service.py::exclude_address`](../services/marketing/service.py#L552)<br>[`service.py::start`](../services/marketing/service.py#L295) |
| [`service.py::UNSUBSCRIBE_REASONS`](../services/marketing/service.py#L24) | `['reader', 'bounce', 'complaint', 'operator']` |  | [`service.py::unsubscribe`](../services/marketing/service.py#L527) |
| [`settings.py::AUDIENCE_GROUP`](../services/marketing/settings.py#L2) | `{'corporate': 'paid', 'debt': 'paid', 'paid': 'paid', 'social': 'social', 'vip'…` | Сегмент читателя -> группа шаблонов писем. | [`service.py::add_member`](../services/marketing/service.py#L113)<br>[`service.py::find_template`](../services/marketing/service.py#L190)<br>[`service.py::send_test_message`](../services/marketing/service.py#L452)<br>[`service.py::set_template`](../services/marketing/service.py#L156) |
| [`settings.py::BOUNCE_LIMIT`](../services/marketing/settings.py#L27) | `3` | После стольких возвратов адрес отписывается от всех рассылок. | [`service.py::handle_bounce`](../services/marketing/service.py#L507) |
| [`settings.py::CAMPAIGN_TYPES`](../services/marketing/settings.py#L12) | `['newsletter', 'event', 'promo']` |  | [`service.py::create_campaign`](../services/marketing/service.py#L226)<br>[`service.py::set_template`](../services/marketing/service.py#L156) |
| [`settings.py::FALLBACK_GROUP`](../services/marketing/settings.py#L10) | `paid` | Группа, шаблон которой берётся, если для группы читателя на площадке шаблона нет. | [`service.py::find_template`](../services/marketing/service.py#L190) |
| [`settings.py::MAX_AUDIENCE_SIZE`](../services/marketing/settings.py#L15) | `5000` | Сколько адресов может быть в одной аудитории. | [`service.py::add_member`](../services/marketing/service.py#L113) |
| [`settings.py::MAX_SCHEDULE_AHEAD_DAYS`](../services/marketing/settings.py#L25) | `90` | Насколько вперёд можно запланировать кампанию. | [`service.py::_check_schedule`](../services/marketing/service.py#L216) |
| [`settings.py::MAX_TEMPLATE_LENGTH`](../services/marketing/settings.py#L17) | `10000` | Длина текста шаблона. | [`service.py::set_template`](../services/marketing/service.py#L156) |
| [`settings.py::MAX_TEST_MESSAGES`](../services/marketing/settings.py#L19) | `5` | Тестовых писем на одну кампанию. | [`service.py::send_test_message`](../services/marketing/service.py#L452) |
| [`settings.py::MIN_DAYS_BETWEEN_CAMPAIGNS`](../services/marketing/settings.py#L23) | `3` | Не чаще одной кампании в столько дней на аудиторию. | [`service.py::start`](../services/marketing/service.py#L295) |
| [`settings.py::TEST_MESSAGE_TTL_DAYS`](../services/marketing/settings.py#L21) | `14` | Тестовые письма удаляются через столько дней после отправки. | [`jobs.py::purge_test_messages`](../services/marketing/jobs.py#L36) |
| [`config.py::TEMPLATE_GROUP`](../services/notifications/config.py#L2) | `{'debt': 'paid', 'paid': 'paid', 'social': 'social'}` | Группа шаблонов писем по виду заявки. | [`service.py::find_template`](../services/notifications/service.py#L32) |
| [`service.py::CENT`](../services/partners/service.py#L25) | `Decimal('0.01')` |  | [`service.py::commission_amount`](../services/partners/service.py#L451) |
| [`service.py::CURRENT_CONTRACT`](../services/partners/service.py#L23) | `['draft', 'active', 'suspended']` |  | [`service.py::change_commission_rate`](../services/partners/service.py#L264)<br>[`service.py::current_contract`](../services/partners/service.py#L210)<br>[`service.py::onboard`](../services/partners/service.py#L147)<br>[`service.py::set_credit_terms`](../services/partners/service.py#L281)<br>[`service.py::terminate_contract`](../services/partners/service.py#L552) |
| [`service.py::EDITABLE_FIELDS`](../services/partners/service.py#L24) | `['kpp', 'legal_name', 'contact_name', 'contact_email', 'contact_phone']` |  | [`service.py::update_requisites`](../services/partners/service.py#L216) |
| [`service.py::_INN_WEIGHTS`](../services/partners/service.py#L27) | `[2, 4, 10, 3, 5, 9, 4, 6, 8]` |  | [`service.py::inn_valid`](../services/partners/service.py#L30) |
| [`settings.py::CONTRACT_TERM_DAYS`](../services/partners/settings.py#L19) | `365` | Срок действия договора по умолчанию. | [`service.py::onboard`](../services/partners/service.py#L147)<br>[`service.py::renew_contract`](../services/partners/service.py#L578) |
| [`settings.py::CREDIT_PAYMENT_DAYS`](../services/partners/settings.py#L16) | `14` | Срок оплаты сделки, проведённой в кредит. | [`service.py::open_deal`](../services/partners/service.py#L352) |
| [`settings.py::DEFAULT_COMMISSION_PCT`](../services/partners/settings.py#L9) | `Decimal(10)` | Ставка комиссии нового договора и допустимый максимум. | [`service.py::onboard`](../services/partners/service.py#L147)<br>[`service.py::renew_contract`](../services/partners/service.py#L578) |
| [`settings.py::MAX_COMMISSION_PCT`](../services/partners/settings.py#L10) | `Decimal(30)` |  | [`service.py::_check_rate`](../services/partners/service.py#L259) |
| [`settings.py::MAX_CREDIT_LIMIT`](../services/partners/settings.py#L13) | `Decimal(500000)` | Максимальный лимит кредита, который менеджер выставляет без согласования. | [`service.py::set_credit_terms`](../services/partners/service.py#L281) |
| [`settings.py::ONBOARDING_REQUEST_TTL_DAYS`](../services/partners/settings.py#L22) | `30` | Заявка на подключение без решения закрывается через столько дней. | [`jobs.py::expire_requests`](../services/partners/jobs.py#L46) |
| [`settings.py::REQUIRED_PARTNER_FIELDS`](../services/partners/settings.py#L4) | `['inn', 'kpp', 'legal_name']` | Без этих реквизитов договор с партнёром не активируется. | [`service.py::missing_requisites`](../services/partners/service.py#L43)<br>[`service.py::update_requisites`](../services/partners/service.py#L216) |
| [`settings.py::REQUISITE_TITLES`](../services/partners/settings.py#L6) | `{'inn': 'ИНН', 'kpp': 'КПП', 'legal_name': 'наименование'}` |  | [`service.py::activate_contract`](../services/partners/service.py#L237) |
| [`builders.py::CENT`](../services/reports/builders.py#L29) | `Decimal('0.01')` |  | [`builders.py::_money`](../services/reports/builders.py#L32) |
| [`builders.py::KINDS`](../services/reports/builders.py#L18) | `['metric_summary', 'metric_trend', 'run_audit']` |  | [`builders.py::normalize_params`](../services/reports/builders.py#L55) |
| [`builders.py::METRIC_RE`](../services/reports/builders.py#L19) | `re.compile('^[a-z][a-z0-9_]*(\\.[a-z0-9_]+)*$')` |  | [`builders.py::metric_name`](../services/reports/builders.py#L36) |
| [`builders.py::RUN_OVERRIDABLE`](../services/reports/builders.py#L22) | `frozenset({'days', 'as_of', 'dimension'})` | Что можно переопределить при конкретном запуске, не меняя определение отчёта. | [`service.py::request_run`](../services/reports/service.py#L222) |
| [`builders.py::_ALLOWED`](../services/reports/builders.py#L23) | `{'metric_summary': frozenset({'metrics', 'days', 'dimension', 'as_of'}), 'metri…` |  | [`builders.py::normalize_params`](../services/reports/builders.py#L55) |
| [`models.py::FINISHED`](../services/reports/models.py#L12) | `['completed', 'failed', 'cancelled']` |  | [`jobs.py::purge_old_runs`](../services/reports/jobs.py#L65) |
| [`models.py::IN_FLIGHT`](../services/reports/models.py#L13) | `['requested', 'running']` |  | [`service.py::_check_run_quota`](../services/reports/service.py#L206) |
| [`settings.py::DEFAULT_PERIOD_DAYS`](../services/reports/settings.py#L13) | `7` | Период отчёта по умолчанию и максимальная глубина, дней. | [`builders.py::_period`](../services/reports/builders.py#L90) |
| [`settings.py::MAX_METRICS_PER_REPORT`](../services/reports/settings.py#L11) | `20` | Метрик в одном сводном отчёте. | [`builders.py::normalize_params`](../services/reports/builders.py#L55) |
| [`settings.py::MAX_PENDING_RUNS_PER_USER`](../services/reports/settings.py#L9) | `3` | Незавершённых ручных запусков на одного сотрудника одновременно. | [`service.py::_check_run_quota`](../services/reports/service.py#L206) |
| [`settings.py::MAX_PERIOD_DAYS`](../services/reports/settings.py#L14) | `90` |  | [`builders.py::_days`](../services/reports/builders.py#L42) |
| [`settings.py::MAX_RECIPIENTS`](../services/reports/settings.py#L19) | `20` |  | [`service.py::_recipients`](../services/reports/service.py#L366) |
| [`settings.py::MAX_SCHEDULE_INTERVAL_HOURS`](../services/reports/settings.py#L18) | `24 * 31` |  | [`service.py::create_schedule`](../services/reports/service.py#L375) |
| [`settings.py::MIN_SCHEDULE_INTERVAL_HOURS`](../services/reports/settings.py#L17) | `1` | Интервал выгрузок по расписанию, часов. | [`service.py::create_schedule`](../services/reports/service.py#L375) |
| [`settings.py::RETENTION_DAYS`](../services/reports/settings.py#L4) | `30` | Завершённые запуски хранятся столько дней, затем удаляются вместе с уведомлениями. | [`jobs.py::purge_old_runs`](../services/reports/jobs.py#L65) |
| [`settings.py::RUNS_COMPLETED_METRIC`](../services/reports/settings.py#L25) | `reports.runs_completed` | Служебная метрика: число построенных отчётов за день в разрезе кода отчёта. | [`consumers.py::count_completed_run`](../services/reports/consumers.py#L21) |
| [`settings.py::RUNS_PAGE_LIMIT`](../services/reports/settings.py#L22) | `100` | Сколько запусков отдаёт список за один раз. | [`service.py::list_runs`](../services/reports/service.py#L345) |
| [`settings.py::RUN_TIMEOUT_MINUTES`](../services/reports/settings.py#L6) | `30` | Запуск, который строится дольше этого, считается зависшим и помечается неуспешным. | [`jobs.py::fail_stuck_runs`](../services/reports/jobs.py#L42) |
| [`service.py::CLIENT_SIDE`](../services/scheduling/service.py#L14) | `['client', 'representative']` |  | [`service.py::cancel_booking`](../services/scheduling/service.py#L193) |
| [`listeners.py::TRACKED_FIELDS`](../services/staff/listeners.py#L9) | `['full_name', 'passport', 'snils', 'birth_date', 'role']` |  | [`listeners.py::_employee_changes`](../services/staff/listeners.py#L13) |
| [`service.py::EDITABLE_FIELDS`](../services/staff/service.py#L24) | `['full_name', 'passport', 'snils', 'birth_date', 'role']` |  | [`service.py::update_employee`](../services/staff/service.py#L125) |
| [`settings.py::BRIEFING_VALID_DAYS`](../services/staff/settings.py#L25) | `30` | Инструктаж годится для оформления допуска, если проведён не раньше чем столько дней назад. | [`service.py::_fresh_briefing`](../services/staff/service.py#L486)<br>[`service.py::grant_clearance`](../services/staff/service.py#L496) |
| [`settings.py::HR_ROLES`](../services/staff/settings.py#L8) | `['hr']` | Кто ведёт кадровые операции: приём, перевод, увольнение, допуски. | [`service.py::_require_hr`](../services/staff/service.py#L51) |
| [`settings.py::MAX_SHIFT_HOURS`](../services/staff/settings.py#L18) | `12` |  | [`service.py::create_shift`](../services/staff/service.py#L241) |
| [`settings.py::MAX_SHIFT_STAFF`](../services/staff/settings.py#L13) | `6` | Максимум сотрудников на смене для новой площадки. | [`service.py::create_site`](../services/staff/service.py#L153) |
| [`settings.py::MIN_EMPLOYEE_AGE`](../services/staff/settings.py#L17) | `18` |  | [`service.py::_validate_card`](../services/staff/service.py#L80) |
| [`settings.py::MIN_REST_HOURS`](../services/staff/settings.py#L20) | `8` | Минимальный отдых между сменами одного сотрудника. | [`service.py::_check_rest`](../services/staff/service.py#L303) |
| [`settings.py::PLANNING_HORIZON_DAYS`](../services/staff/settings.py#L22) | `60` | Смены планируются не дальше чем на столько дней вперёд. | [`service.py::create_shift`](../services/staff/service.py#L241) |
| [`settings.py::REQUIRED_EMPLOYEE_FIELDS`](../services/staff/settings.py#L4) | `['full_name', 'passport', 'snils', 'birth_date']` | Без этих полей карточки сотрудника нельзя допустить к сменам и оформить допуск. | [`service.py::missing_fields`](../services/staff/service.py#L65) |
| [`settings.py::RESPONSIBLE_ROLES`](../services/staff/settings.py#L10) | `['manager']` | Кого можно назначить ответственным за площадку. | [`service.py::appoint_responsible`](../services/staff/service.py#L225) |
| [`settings.py::ROLES`](../services/staff/settings.py#L6) | `['librarian', 'cashier', 'guard', 'manager', 'hr']` |  | [`service.py::_validate_card`](../services/staff/service.py#L80) |
| [`settings.py::SHIFT_STAFF_CEILING`](../services/staff/settings.py#L15) | `20` | Жёсткий потолок для любой площадки (совпадает с CHECK в staff.sql). | [`service.py::set_site_max_staff`](../services/staff/service.py#L163) |
| [`service.py::CLOSED`](../services/subscriptions/service.py#L19) | `['expired', 'closed_duplicate']` |  | [`service.py::apply_payment`](../services/subscriptions/service.py#L358)<br>[`service.py::recheck_holder`](../services/subscriptions/service.py#L216)<br>[`service.py::update_holder`](../services/subscriptions/service.py#L182) |
| [`service.py::HOLDER_FIELDS`](../services/subscriptions/service.py#L20) | `['holder_name', 'passport', 'birth_date']` |  | [`service.py::update_holder`](../services/subscriptions/service.py#L182) |
| [`service.py::LIVE`](../services/subscriptions/service.py#L17) | `['active', 'grace']` |  | [`jobs.py::expire_overdue`](../services/subscriptions/jobs.py#L11)<br>[`jobs.py::issue_renewal_invoices`](../services/subscriptions/jobs.py#L66)<br>[`service.py::create_subscription`](../services/subscriptions/service.py#L124) |
| [`service.py::OPEN`](../services/subscriptions/service.py#L18) | `['pending', 'active', 'grace']` |  | [`service.py::close_duplicates`](../services/subscriptions/service.py#L327) |
| [`service.py::PASSPORT_RE`](../services/subscriptions/service.py#L22) | `re.compile('^\\d{4} \\d{6}$')` |  | [`service.py::_validate_holder`](../services/subscriptions/service.py#L103) |
| [`service.py::PLAN_KINDS`](../services/subscriptions/service.py#L16) | `['regular', 'social', 'corporate']` |  | [`service.py::create_plan`](../services/subscriptions/service.py#L53) |
| [`settings.py::GRACE_DAYS`](../services/subscriptions/settings.py#L4) | `30` | Сколько дней после окончания оплаченного месяца абонемент ещё действует (статус grace). | [`jobs.py::expire_overdue`](../services/subscriptions/jobs.py#L11) ⚠ литерал 30 вместо настройки |
| [`settings.py::MAX_PENDING_PER_CLIENT`](../services/subscriptions/settings.py#L17) | `3` | Сколько неоплаченных абонементов клиент может держать одновременно. | [`service.py::create_subscription`](../services/subscriptions/service.py#L124) |
| [`settings.py::MIN_HOLDER_AGE`](../services/subscriptions/settings.py#L12) | `14` | Минимальный возраст держателя абонемента. | [`service.py::_validate_holder`](../services/subscriptions/service.py#L103) |
| [`settings.py::PENDING_TTL_DAYS`](../services/subscriptions/settings.py#L8) | `14` | Неоплаченный новый абонемент закрывается через столько дней. | [`jobs.py::expire_stale_pending`](../services/subscriptions/jobs.py#L48) |
| [`settings.py::RENEWAL_INVOICE_DAYS`](../services/subscriptions/settings.py#L10) | `7` | Счёт на следующий месяц выставляется за столько дней до конца оплаченного. | [`jobs.py::issue_renewal_invoices`](../services/subscriptions/jobs.py#L66) |
| [`settings.py::SOCIAL_MAX_STUDENT_AGE`](../services/subscriptions/settings.py#L15) | `23` |  | [`service.py::_social_eligible`](../services/subscriptions/service.py#L119) |
| [`settings.py::SOCIAL_MIN_SENIOR_AGE`](../services/subscriptions/settings.py#L14) | `60` | Социальный тариф оформляется с этого возраста (пенсионный) или до SOCIAL_MAX_STUDENT_AGE. | [`service.py::_social_eligible`](../services/subscriptions/service.py#L119) |
| [`wiring.py::CORE`](../services/wiring.py#L18) | `['applications', 'billing', 'scheduling', 'notifications', 'chat']` |  | [`wiring.py::load`](../services/wiring.py#L21) |
| [`wiring.py::MODULES`](../services/wiring.py#L6) | `['services.applications.listeners', 'services.applications.consumers', 'service…` |  | [`wiring.py::load`](../services/wiring.py#L21) |

## Фоновые задачи

### [`services/applications/jobs.py::archive_stale`](../services/applications/jobs.py#L14)

- без описания
- настройки: `libs/settings.py::PAYMENT_ARCHIVE_DAYS`, `libs/settings.py::REVIEW_ARCHIVE_DAYS`
- события: —; вызывает: service.py::archive, public.py::active_books_invoice

### [`services/halls/jobs.py::cancel_unpaid`](../services/halls/jobs.py#L10)

- Отменяет брони, по которым так и не внесли предоплату.
- настройки: `services/halls/settings.py::UNPAID_CANCEL_DAYS`
- события: —; вызывает: service.py::cancel_unpaid

### [`services/halls/jobs.py::close_past_events`](../services/halls/jobs.py#L28)

- Подтверждённые брони, чьё мероприятие закончилось, переводятся в «проведено».
- настройки: —
- события: —; вызывает: service.py::mark_held

### [`services/inventory/jobs.py::accrue_ill_penalties`](../services/inventory/jobs.py#L36)

- Ежедневный пересчёт пеней по ещё не возвращённым просроченным выдачам.
- настройки: —
- события: —; вызывает: service.py::accrue_overdue, service.py::days_late

### [`services/inventory/jobs.py::expire_stale_transfers`](../services/inventory/jobs.py#L50)

- без описания
- настройки: `services/inventory/settings.py::TRANSFER_REQUEST_TTL_DAYS`
- события: —; вызывает: service.py::cancel_transfer

### [`services/inventory/jobs.py::flag_overdue_ill`](../services/inventory/jobs.py#L11)

- без описания
- настройки: —
- события: `inventory.ill_overdue`; вызывает: service.py::days_late

### [`services/lectures/jobs.py::close_waitlists`](../services/lectures/jobs.py#L11)

- Когда регистрация закрылась, ждать места больше бессмысленно: лист ожидания истекает.
- настройки: `services/lectures/settings.py::REGISTRATION_CLOSES_BEFORE`
- события: `lectures.waitlist_expired`; вызывает: —

### [`services/lectures/jobs.py::finish_past_events`](../services/lectures/jobs.py#L62)

- без описания
- настройки: `services/lectures/settings.py::FINISH_AFTER`
- события: —; вызывает: —

### [`services/lectures/jobs.py::send_reminders`](../services/lectures/jobs.py#L36)

- без описания
- настройки: `services/lectures/settings.py::REMINDER_AHEAD`
- события: —; вызывает: service.py::notify

### [`services/marketing/jobs.py::launch_due`](../services/marketing/jobs.py#L11)

- Запускает запланированные кампании, время которых пришло.
- настройки: —
- события: —; вызывает: service.py::start

### [`services/marketing/jobs.py::purge_test_messages`](../services/marketing/jobs.py#L36)

- без описания
- настройки: `services/marketing/settings.py::TEST_MESSAGE_TTL_DAYS`
- события: —; вызывает: service.py::purge_test_messages

### [`services/partners/jobs.py::close_payouts`](../services/partners/jobs.py#L61)

- Закрывает ведомости прошедших месяцев.
- настройки: —
- события: —; вызывает: service.py::close_payout

### [`services/partners/jobs.py::expire_contracts`](../services/partners/jobs.py#L33)

- без описания
- настройки: —
- события: —; вызывает: service.py::expire_contract

### [`services/partners/jobs.py::expire_requests`](../services/partners/jobs.py#L46)

- без описания
- настройки: `services/partners/settings.py::ONBOARDING_REQUEST_TTL_DAYS`
- события: —; вызывает: —

### [`services/partners/jobs.py::flag_overdue_credit`](../services/partners/jobs.py#L11)

- без описания
- настройки: —
- события: `partners.credit_overdue`; вызывает: —

### [`services/reports/jobs.py::fail_stuck_runs`](../services/reports/jobs.py#L42)

- без описания
- настройки: `services/reports/settings.py::RUN_TIMEOUT_MINUTES`
- события: `reports.run_failed`; вызывает: —

### [`services/reports/jobs.py::purge_old_runs`](../services/reports/jobs.py#L65)

- Удаляет завершённые запуски старше срока хранения; уведомления уходят каскадом.
- настройки: `services/reports/models.py::FINISHED`, `services/reports/settings.py::RETENTION_DAYS`
- события: —; вызывает: —

### [`services/reports/jobs.py::run_scheduled`](../services/reports/jobs.py#L12)

- Ставит в очередь выгрузки, у которых подошёл срок.
- настройки: —
- события: —; вызывает: service.py::advance, service.py::request_run

### [`services/scheduling/jobs.py::flag_overdue`](../services/scheduling/jobs.py#L10)

- без описания
- настройки: —
- события: `loan.overdue`; вызывает: —

### [`services/staff/jobs.py::close_finished_shifts`](../services/staff/jobs.py#L26)

- без описания
- настройки: —
- события: —; вызывает: —

### [`services/staff/jobs.py::expire_clearances`](../services/staff/jobs.py#L10)

- без описания
- настройки: —
- события: `staff.clearance_expired`; вызывает: —

### [`services/subscriptions/jobs.py::expire_overdue`](../services/subscriptions/jobs.py#L11)

- Конец оплаченного месяца переводит абонемент в grace, конец льготного периода — в expired.
- настройки: `services/subscriptions/service.py::LIVE`, `services/subscriptions/settings.py::GRACE_DAYS`
- события: `subscriptions.expired`, `subscriptions.grace_started`; вызывает: —

### [`services/subscriptions/jobs.py::expire_stale_pending`](../services/subscriptions/jobs.py#L48)

- без описания
- настройки: `services/subscriptions/settings.py::PENDING_TTL_DAYS`
- события: `subscriptions.expired`; вызывает: —

### [`services/subscriptions/jobs.py::issue_renewal_invoices`](../services/subscriptions/jobs.py#L66)

- без описания
- настройки: `services/subscriptions/service.py::LIVE`, `services/subscriptions/settings.py::RENEWAL_INVOICE_DAYS`
- события: —; вызывает: service.py::issue_invoice
