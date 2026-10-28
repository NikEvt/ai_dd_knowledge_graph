<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: marketing

Источник: [`knowledge/rules/marketing.yaml`](../../knowledge/rules/marketing.yaml)

## R-MARKETING-ACCESS-01 — Рассылками площадки управляет только её менеджер или менеджер сети

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 3 тестами

Любое действие с аудиториями, шаблонами, кампаниями и письмами (создание, архив, добавление адресов, планирование, отмена, запуск, отчёт, просмотр писем, тестовое письмо) требует записи в marketing.managers: менеджер этой площадки (venue_id = площадка) или менеджер сети (venue_id IS NULL), который допущен ко всем площадкам. Иначе AccessDenied «менеджер не ведёт рассылки этой площадки» (HTTP 403). Менеджера рассылок нет в общей модели ролей: права задаются только таблицей marketing.managers.

- Реализация: [`services/marketing/service.py::_require_manager:50-58`](../../services/marketing/service.py#L50), [`services/marketing/service.py::_campaign_for:261-266`](../../services/marketing/service.py#L261)
- Тесты: `tests/test_marketing_audiences.py::test_audience_is_created_by_venue_manager`, `tests/test_marketing_audiences.py::test_manager_of_other_venue_is_denied`, `tests/test_marketing_api.py::test_access_and_missing_campaign`
- Связанные: R-MARKETING-ACCESS-02

## R-MARKETING-ACCESS-02 — Шаблоны сети задаёт только менеджер сети

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Шаблон без площадки (venue_id = NULL, шаблон сети по умолчанию) может создать или изменить только менеджер сети (строка marketing.managers без venue_id); менеджер площадки получает AccessDenied «шаблоны сети задаёт только менеджер сети». Проверка в _require_manager при вызове из set_template.

- Реализация: [`services/marketing/service.py::_require_manager:55-57`](../../services/marketing/service.py#L55), [`services/marketing/service.py::set_template:165-165`](../../services/marketing/service.py#L165)
- Тесты: `tests/test_marketing_templates.py::test_network_templates_only_by_network_manager`
- Связанные: R-MARKETING-ACCESS-01, R-MARKETING-TEMPLATE-04

## R-MARKETING-ACCESS-03 — Отписка и регистрация возврата письма доступны без проверки менеджера

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Эндпоинты POST /marketing/unsubscribe и POST /marketing/messages/{id}/bounce не принимают manager_id и не проверяют права. Отписка через API всегда записывается с причиной reader (причину передать нельзя), venue_id необязателен — без него адрес отписывается от всей сети.

- Реализация: [`services/marketing/api.py::unsubscribe:190-191`](../../services/marketing/api.py#L190), [`services/marketing/api.py::bounce:185-186`](../../services/marketing/api.py#L185)
- Тесты: `tests/test_marketing_api.py::test_unsubscribe_and_bounce_endpoints`
- Роли: Клиент
- Связанные: R-MARKETING-UNSUBSCRIBE-01, R-MARKETING-BOUNCE-01

## R-MARKETING-ACCESS-04 — Менеджер закрепляется за площадкой или сетью не более одного раза

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Один manager_id может быть только одной строкой менеджера сети (managers_network_uq, venue_id IS NULL) и только одной строкой на каждую площадку (managers_venue_uq). add_manager сам ничего не проверяет и в API не выставлен; дубль отсекает только БД.

- Реализация: [`services/marketing/service.py::add_manager:41-47`](../../services/marketing/service.py#L41)
- БД: `managers_network_uq`, `managers_venue_uq`
- Связанные: R-MARKETING-ACCESS-01

## R-MARKETING-AUDIENCE-01 — Название аудитории непустое и уникально в пределах площадки

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

При создании аудитории название обрезается по краям пробелов; пустое — DomainError «у аудитории должно быть название», уже занятое на этой площадке (точное совпадение с учётом регистра) — DomainError «на площадке уже есть аудитория …». БД дублирует обе проверки (CHECK на trim(name) и UNIQUE (venue_id, name)).

- Реализация: [`services/marketing/service.py::create_audience:66-73`](../../services/marketing/service.py#L66)
- БД: `audiences_name_check`, `audiences_venue_name_uq`
- Тесты: `tests/test_marketing_audiences.py::test_audience_name_is_unique_within_venue`, `tests/test_marketing_audiences.py::test_audience_is_created_by_venue_manager`

## R-MARKETING-AUDIENCE-02 — Нельзя архивировать аудиторию с запланированной или идущей кампанией

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

archive_audience запрещает архив, если по аудитории есть кампании в статусах scheduled, preparing или sending (DomainError «по аудитории есть незавершённые кампании»). Черновики (draft) архиву не мешают и остаются, но запустить их после архива нельзя. После отмены запланированной кампании архив разрешён.

- Реализация: [`services/marketing/service.py::archive_audience:90-97`](../../services/marketing/service.py#L90)
- Настройки: `services/marketing/service.py::RUNNING`
- Тесты: `tests/test_marketing_audiences.py::test_archived_audience_cannot_have_pending_campaigns`, `tests/test_marketing_api.py::test_schedule_cancel_and_report`
- Связанные: R-MARKETING-AUDIENCE-03, R-MARKETING-CAMPAIGN-03

## R-MARKETING-AUDIENCE-03 — Архивная аудитория закрыта для новых адресов, кампаний и запусков

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Если аудитория в архиве, add_member, create_campaign и start (ручной запуск и запуск по расписанию) отклоняют действие с DomainError «аудитория в архиве». Ограничение только в коде, в БД его нет.

- Реализация: [`services/marketing/service.py::add_member:124-125`](../../services/marketing/service.py#L124), [`services/marketing/service.py::create_campaign:237-238`](../../services/marketing/service.py#L237), [`services/marketing/service.py::start:299-300`](../../services/marketing/service.py#L299)
- Тесты: `tests/test_marketing_audiences.py::test_archived_audience_cannot_have_pending_campaigns`
- Связанные: R-MARKETING-AUDIENCE-02

## R-MARKETING-MEMBER-01 — Сегмент читателя ограничен списком из настройки AUDIENCE_GROUP

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

При добавлении адреса сегмент должен быть ключом AUDIENCE_GROUP (paid, debt, social, vip, corporate), иначе DomainError «неизвестный сегмент читателя». Тот же список захардкожен в CHECK audience_members_segment_check: при добавлении сегмента в настройку нужна миграция.

- Реализация: [`services/marketing/service.py::add_member:126-127`](../../services/marketing/service.py#L126)
- БД: `audience_members_segment_check`
- Настройки: `services/marketing/settings.py::AUDIENCE_GROUP`
- Тесты: `tests/test_marketing_audiences.py::test_unknown_segment_and_bad_email_rejected`
- Связанные: R-MARKETING-TEMPLATE-01

## R-MARKETING-MEMBER-02 — В аудитории не больше MAX_AUDIENCE_SIZE адресов

`draft` · config

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

add_member отклоняет новый адрес, если в аудитории уже MAX_AUDIENCE_SIZE (5000) записей. В счёт входят и отписавшиеся (opted_out) участники, которые писем уже не получают. В БД лимита нет.

- Реализация: [`services/marketing/service.py::add_member:129-131`](../../services/marketing/service.py#L129)
- Настройки: `services/marketing/settings.py::MAX_AUDIENCE_SIZE`

## R-MARKETING-MEMBER-03 — Адрес встречается в аудитории один раз

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

После нормализации адрес не может повторяться внутри аудитории: код отвечает DomainError «адрес уже есть в аудитории», БД держит уникальный индекс (audience_id, email). Один адрес может быть в разных аудиториях.

- Реализация: [`services/marketing/service.py::add_member:132-138`](../../services/marketing/service.py#L132)
- БД: `audience_members_email_uq`
- Тесты: `tests/test_marketing_audiences.py::test_member_email_is_normalized_and_unique`
- Связанные: R-MARKETING-EMAIL-01

## R-MARKETING-MEMBER-04 — Отписанный адрес нельзя добавить в аудиторию

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

add_member отклоняет адрес, если для него есть отписка от всей сети или от площадки аудитории (DomainError «адрес отписан от рассылок площадки»). Отписка от другой площадки добавлению не мешает.

- Реализация: [`services/marketing/service.py::add_member:139-140`](../../services/marketing/service.py#L139), [`services/marketing/service.py::is_unsubscribed:101-110`](../../services/marketing/service.py#L101)
- Тесты: `tests/test_marketing_audiences.py::test_unsubscribed_address_cannot_be_added`
- Связанные: R-MARKETING-UNSUBSCRIBE-01, R-MARKETING-UNSUBSCRIBE-03

## R-MARKETING-EMAIL-01 — Адреса хранятся в нижнем регистре без пробелов и с «@» не в начале

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

normalize_email обрезает пробелы, переводит адрес в нижний регистр и отклоняет адрес без «@» после первого символа. БД дублирует нормализацию триггерами audience_members_normalize_email и unsubscriptions_normalize_email (функция normalize_email), формат — CHECK audience_members_email_check. У marketing.sent_messages триггера нормализации нет.

- Реализация: [`services/marketing/service.py::normalize_email:27-31`](../../services/marketing/service.py#L27), [`services/marketing/service.py::add_member:128-128`](../../services/marketing/service.py#L128), [`services/marketing/service.py::unsubscribe:532-532`](../../services/marketing/service.py#L532)
- БД: `audience_members_normalize_email`, `unsubscriptions_normalize_email`, `normalize_email`, `audience_members_email_check`
- Тесты: `tests/test_marketing_audiences.py::test_member_email_is_normalized_and_unique`, `tests/test_marketing_audiences.py::test_member_email_normalized_by_database_too`, `tests/test_marketing_audiences.py::test_unknown_segment_and_bad_email_rejected`
- Связанные: R-MARKETING-MEMBER-03

## R-MARKETING-TEMPLATE-01 — Платные сегменты (paid, debt, corporate) получают общий шаблон группы paid

`draft` · config

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Шаблоны заводятся на группу аудитории, а не на сегмент: AUDIENCE_GROUP отображает corporate, debt и paid в группу paid, social — в social, vip — в vip. Поэтому шаблон группы paid получают все платные сегменты.

- Реализация: [`services/marketing/service.py::find_template:194-195`](../../services/marketing/service.py#L194)
- Настройки: `services/marketing/settings.py::AUDIENCE_GROUP`
- Тесты: `tests/test_marketing_templates.py::test_paying_segments_share_template`
- Связанные: R-MARKETING-TEMPLATE-02, R-MARKETING-MEMBER-01

## R-MARKETING-TEMPLATE-02 — Порядок поиска шаблона: площадка, сеть, затем запасная группа paid

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Для сегмента читателя и типа кампании find_template ищет шаблон в таком порядке: шаблон площадки для группы читателя, шаблон сети для этой группы, затем шаблон площадки и шаблон сети для FALLBACK_GROUP (paid). Если сегмент неизвестен, берётся сразу группа paid. Если ничего не нашлось, возвращается None: при подготовке рассылки письмо пропускается, для тестового письма возникает ошибка.

- Реализация: [`services/marketing/service.py::find_template:194-210`](../../services/marketing/service.py#L194)
- Настройки: `services/marketing/settings.py::FALLBACK_GROUP`, `services/marketing/settings.py::AUDIENCE_GROUP`
- Тесты: `tests/test_marketing_templates.py::test_find_template_falls_back_to_network_then_paid_group`, `tests/test_marketing_templates.py::test_paying_segments_share_template`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-TEMPLATE-01, R-MARKETING-PREPARE-02, R-MARKETING-TEST-01

## R-MARKETING-TEMPLATE-03 — Проверки шаблона: группа, тип кампании, непустой текст, длина

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

set_template принимает только группу из значений AUDIENCE_GROUP (paid, social, vip; сегмент, например debt, отклоняется), тип из CAMPAIGN_TYPES (newsletter, event, promo), текст не из одних пробелов и не длиннее MAX_TEMPLATE_LENGTH (10000). В БД есть CHECK на группу (список захардкожен) и на length(body) > 0 (пробельный текст БД пропустит). Тип кампании и длину шаблона БД не проверяет.

- Реализация: [`services/marketing/service.py::set_template:166-173`](../../services/marketing/service.py#L166)
- БД: `campaign_templates_audience_group_check`, `campaign_templates_body_check`
- Настройки: `services/marketing/settings.py::AUDIENCE_GROUP`, `services/marketing/settings.py::CAMPAIGN_TYPES`, `services/marketing/settings.py::MAX_TEMPLATE_LENGTH`
- Тесты: `tests/test_marketing_templates.py::test_template_validation`, `tests/test_marketing_api.py::test_access_and_missing_campaign`
- Связанные: R-MARKETING-TEMPLATE-04

## R-MARKETING-TEMPLATE-04 — Один шаблон на площадку (или сеть), группу и тип; повторная запись обновляет его

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

set_template работает как upsert: если шаблон для (площадка или сеть, группа, тип) уже есть, меняются его body и updated_at, иначе создаётся новый. В БД уникальность держат UNIQUE (venue_id, audience_group, type) и частичный индекс campaign_templates_default_uq для шаблонов сети, потому что NULL в UNIQUE не сравниваются.

- Реализация: [`services/marketing/service.py::set_template:175-186`](../../services/marketing/service.py#L175)
- БД: `campaign_templates_venue_group_type_uq`, `campaign_templates_default_uq`
- Тесты: `tests/test_marketing_templates.py::test_set_template_updates_existing`
- Связанные: R-MARKETING-TEMPLATE-03

## R-MARKETING-TEMPLATE-05 — Текст письма подставляет $full_name, $email и $subject

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Текст письма получается из шаблона через string.Template.safe_substitute с переменными full_name, email и subject (тема кампании). Неизвестные плейсхолдеры остаются в тексте как есть, ошибки нет. Так готовятся и письма кампании, и тестовые письма.

- Реализация: [`services/marketing/service.py::render:34-35`](../../services/marketing/service.py#L34), [`services/marketing/service.py::prepare_messages:369-372`](../../services/marketing/service.py#L369), [`services/marketing/service.py::send_test_message:481-481`](../../services/marketing/service.py#L481)
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`, `tests/test_marketing_api.py::test_test_message_then_campaign_messages`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-PREPARE-02, R-MARKETING-TEST-01

## R-MARKETING-CAMPAIGN-01 — Кампания создаётся с известным типом и темой, в статусе draft или scheduled

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

create_campaign требует тип из CAMPAIGN_TYPES и непустую тему (после обрезки пробелов). Если задано scheduled_at, оно проверяется по окну планирования и кампания получает статус scheduled, иначе draft. Площадка кампании берётся из аудитории. Наличие шаблона при создании не проверяется, а тип кампании в БД не ограничен.

- Реализация: [`services/marketing/service.py::create_campaign:239-256`](../../services/marketing/service.py#L239)
- БД: `campaigns_check`
- Настройки: `services/marketing/settings.py::CAMPAIGN_TYPES`
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`
- Связанные: R-MARKETING-CAMPAIGN-02, R-MARKETING-AUDIENCE-03

## R-MARKETING-CAMPAIGN-02 — Кампанию планируют только в будущее и не дальше MAX_SCHEDULE_AHEAD_DAYS

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

При создании с датой и при переносе время запуска должно быть позже текущего («нельзя запланировать кампанию на прошедшее время») и не дальше MAX_SCHEDULE_AHEAD_DAYS (90) дней от текущего момента. В БД CHECK campaigns_check требует scheduled_at у кампании в статусе scheduled; само окно планирования БД не проверяет.

- Реализация: [`services/marketing/service.py::_check_schedule:216-223`](../../services/marketing/service.py#L216), [`services/marketing/service.py::create_campaign:244-245`](../../services/marketing/service.py#L244), [`services/marketing/service.py::schedule_campaign:275-277`](../../services/marketing/service.py#L275)
- БД: `campaigns_check`
- Настройки: `services/marketing/settings.py::MAX_SCHEDULE_AHEAD_DAYS`
- Тесты: `tests/test_marketing_api.py::test_schedule_cancel_and_report`
- Связанные: R-MARKETING-CAMPAIGN-01, R-MARKETING-CAMPAIGN-03

## R-MARKETING-CAMPAIGN-03 — Перенести или отменить можно только не запущенную кампанию

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

schedule_campaign и cancel_campaign разрешены только в статусах draft и scheduled (NOT_STARTED). Перенос переводит кампанию в scheduled с новой датой, в том числе из draft; отмена — в cancelled. Для запущенной или завершённой кампании — DomainError «…только кампанию, которая ещё не запущена».

- Реализация: [`services/marketing/service.py::schedule_campaign:273-277`](../../services/marketing/service.py#L273), [`services/marketing/service.py::cancel_campaign:283-285`](../../services/marketing/service.py#L283)
- Настройки: `services/marketing/service.py::NOT_STARTED`
- Тесты: `tests/test_marketing_campaigns.py::test_finished_campaign_and_sent_letters_are_frozen`, `tests/test_marketing_api.py::test_schedule_cancel_and_report`
- Связанные: R-MARKETING-CAMPAIGN-04, R-MARKETING-AUDIENCE-02

## R-MARKETING-CAMPAIGN-04 — Отправленная или отменённая кампания больше не меняет статус

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Жизненный цикл кампании: draft/scheduled → preparing → sending → sent, или draft/scheduled → cancelled. Допустимые статусы задаёт CHECK campaigns_status_check. Триггер campaigns_guard_status запрещает менять статус из sent и cancelled («кампания % уже в статусе %») даже прямым SQL.

- Реализация: [`services/marketing/service.py::start:296-297`](../../services/marketing/service.py#L296)
- БД: `campaigns_status_check`
- Настройки: `services/marketing/service.py::NOT_STARTED`, `services/marketing/service.py::RUNNING`
- Тесты: `tests/test_marketing_campaigns.py::test_finished_campaign_and_sent_letters_are_frozen`, `tests/test_marketing_campaigns.py::test_audience_rests_between_campaigns`
- Связанные: R-MARKETING-CAMPAIGN-03, R-MARKETING-LAUNCH-01

## R-MARKETING-LAUNCH-01 — Условия запуска кампании и публикация marketing.campaign_launched

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

start запускает кампанию только при выполнении всех условий: статус draft или scheduled, аудитория не в архиве, по аудитории не идёт другая кампания, выдержана пауза MIN_DAYS_BETWEEN_CAMPAIGNS и есть хотя бы один не отписавшийся участник. Тогда кампания переходит в preparing, получает launched_at и публикует marketing.campaign_launched. Через start идут и ручной запуск (launch_campaign), и запуск по расписанию.

- Реализация: [`services/marketing/service.py::start:295-327`](../../services/marketing/service.py#L295), [`services/marketing/service.py::launch_campaign:289-292`](../../services/marketing/service.py#L289)
- Настройки: `services/marketing/service.py::NOT_STARTED`
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`, `tests/test_marketing_campaigns.py::test_audience_rests_between_campaigns`
- Связанные: R-MARKETING-LAUNCH-02, R-MARKETING-LAUNCH-03, R-MARKETING-LAUNCH-05, R-MARKETING-PREPARE-01

## R-MARKETING-LAUNCH-02 — По аудитории одновременно идёт не больше одной кампании

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

start отклоняет запуск, если у аудитории уже есть другая кампания в статусе preparing или sending (DomainError «по аудитории уже идёт другая кампания»). БД дублирует проверку частичным уникальным индексом campaigns_audience_active_uq по audience_id для статусов preparing и sending.

- Реализация: [`services/marketing/service.py::start:301-307`](../../services/marketing/service.py#L301)
- БД: `campaigns_audience_active_uq`
- Настройки: `services/marketing/service.py::RUNNING`
- Тесты: `tests/test_marketing_campaigns.py::test_one_running_campaign_per_audience`
- Связанные: R-MARKETING-LAUNCH-01

## R-MARKETING-LAUNCH-03 — Пауза между кампаниями одной аудитории отсчитывается от завершения предыдущей

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Кампанию нельзя запустить, если с last_campaign_at аудитории прошло меньше MIN_DAYS_BETWEEN_CAMPAIGNS (3) дней. last_campaign_at выставляет summarize_campaign (подписчик marketing.campaign_finished) равным finished_at завершённой кампании, а не времени запуска. Отменённые кампании паузу не сдвигают.

- Реализация: [`services/marketing/service.py::start:308-312`](../../services/marketing/service.py#L308), [`services/marketing/service.py::summarize_campaign:416-418`](../../services/marketing/service.py#L416)
- Настройки: `services/marketing/settings.py::MIN_DAYS_BETWEEN_CAMPAIGNS`
- Тесты: `tests/test_marketing_campaigns.py::test_audience_rests_between_campaigns`, `tests/test_marketing_campaigns.py::test_job_launches_due_campaigns`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-LAUNCH-01, R-MARKETING-REPORT-01

## R-MARKETING-LAUNCH-04 — Запланированную кампанию можно запустить вручную раньше срока

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

launch_campaign вызывает start без сравнения с scheduled_at: кампания в статусе scheduled запускается вручную сразу. Срок планирования соблюдает только фоновая задача launch_due.

- Реализация: [`services/marketing/service.py::launch_campaign:289-292`](../../services/marketing/service.py#L289), [`services/marketing/service.py::start:296-297`](../../services/marketing/service.py#L296)
- Настройки: `services/marketing/service.py::NOT_STARTED`
- Связанные: R-MARKETING-LAUNCH-05

## R-MARKETING-LAUNCH-05 — Фоновая задача запускает наступившие запланированные кампании, неудачные ждут следующего прогона

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

launch_due выбирает кампании в статусе scheduled с scheduled_at <= now (по возрастанию времени, со SKIP LOCKED) и запускает каждую через start во вложенной транзакции. Если запуск не прошёл (DomainError: пауза, идёт другая кампания, нет адресов), кампания остаётся scheduled и повторяется при каждом следующем прогоне без ограничения числа попыток и без уведомления менеджера.

- Реализация: [`services/marketing/jobs.py::launch_due:17-33`](../../services/marketing/jobs.py#L17)
- БД: `campaigns_scheduled_idx`
- Тесты: `tests/test_marketing_campaigns.py::test_job_launches_due_campaigns`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-LAUNCH-01, R-MARKETING-LAUNCH-03

## R-MARKETING-PREPARE-01 — Запуск кампании по цепочке событий готовит, отправляет письма и подводит итог

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Кампания проходит три асинхронных шага внутри модуля: marketing.campaign_launched → prepare_messages (preparing → sending, публикует marketing.campaign_prepared) → deliver_messages (sending → sent, публикует marketing.campaign_finished) → summarize_campaign. Каждый шаг берёт кампанию с блокировкой FOR UPDATE и молча завершается, если статус уже не тот. Других подписчиков в других сервисах у событий нет.

- Реализация: [`services/marketing/consumers.py::on_campaign_launched:10-11`](../../services/marketing/consumers.py#L10), [`services/marketing/consumers.py::on_campaign_prepared:15-16`](../../services/marketing/consumers.py#L15), [`services/marketing/consumers.py::on_campaign_finished:20-21`](../../services/marketing/consumers.py#L20), [`services/marketing/service.py::prepare_messages:332-334`](../../services/marketing/service.py#L332)
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-PREPARE-02, R-MARKETING-DELIVERY-01, R-MARKETING-REPORT-01

## R-MARKETING-PREPARE-02 — Письма при подготовке: отписавшиеся не входят, отписанные и без шаблона пропускаются

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

prepare_messages создаёт письмо на каждого участника аудитории с opted_out = false; участники с opted_out не попадают ни в письма, ни в recipients_count. Если адрес отписан от сети или от площадки кампании, письмо получает статус skipped с причиной unsubscribed. Если для сегмента нет шаблона — skipped с причиной no_template. Остальные письма ставятся в queued с текстом по шаблону. recipients_count равен числу неотписавшихся участников.

- Реализация: [`services/marketing/service.py::prepare_messages:335-377`](../../services/marketing/service.py#L335)
- БД: `sent_messages_campaign_email_uq`
- Тесты: `tests/test_marketing_campaigns.py::test_reader_without_template_is_skipped`, `tests/test_marketing_campaigns.py::test_unsubscribed_reader_excluded_from_future_campaigns`, `tests/test_marketing_campaigns.py::test_venue_unsubscribe_keeps_other_venues`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-TEMPLATE-02, R-MARKETING-UNSUBSCRIBE-03, R-MARKETING-PREPARE-01

## R-MARKETING-DELIVERY-01 — Все письма из очереди отмечаются отправленными одним обновлением

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

deliver_messages (подписчик marketing.campaign_prepared) одним UPDATE переводит все письма кампании из queued в sent с одним sent_at, ставит кампании статус sent и finished_at и публикует marketing.campaign_finished. Реальной отправки и поштучной обработки ошибок доставки нет. О проблемах доставки система узнаёт только из возвратов (bounce), зарегистрированных позже.

- Реализация: [`services/marketing/consumers.py::on_campaign_prepared:15-16`](../../services/marketing/consumers.py#L15), [`services/marketing/service.py::deliver_messages:384-398`](../../services/marketing/service.py#L384)
- БД: `sent_messages_check`
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-PREPARE-01, R-MARKETING-BOUNCE-01

## R-MARKETING-REPORT-01 — Итоги кампании: sent_count — отправленные вместе с возвратами, skipped_count — пропущенные

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

summarize_campaign (подписчик marketing.campaign_finished) считает письма кампании без тестовых: sent_count = sent + bounced, skipped_count = skipped. Счётчики считаются один раз при завершении, поэтому возвраты, зарегистрированные позже, их не меняют. Заодно обновляется last_campaign_at аудитории. Неотрицательность счётчиков обеспечивают CHECK в БД.

- Реализация: [`services/marketing/consumers.py::on_campaign_finished:20-21`](../../services/marketing/consumers.py#L20), [`services/marketing/service.py::summarize_campaign:405-418`](../../services/marketing/service.py#L405)
- БД: `campaigns_sent_count_check`, `campaigns_skipped_count_check`, `campaigns_recipients_count_check`
- Тесты: `tests/test_marketing_campaigns.py::test_launch_prepares_sends_and_summarizes`, `tests/test_marketing_campaigns.py::test_reader_without_template_is_skipped`, `tests/test_marketing_campaigns.py::test_repeated_bounces_unsubscribe_address`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-LAUNCH-03, R-MARKETING-REPORT-02

## R-MARKETING-REPORT-02 — Отчёт по кампании разбивает пропущенные письма по причинам

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

campaign_report возвращает кампанию и число пропущенных писем по причинам skip_reason (unsubscribed, no_template) без тестовых писем. Доступен менеджеру площадки кампании или менеджеру сети.

- Реализация: [`services/marketing/service.py::campaign_report:426-438`](../../services/marketing/service.py#L426)
- Тесты: `tests/test_marketing_api.py::test_schedule_cancel_and_report`
- Связанные: R-MARKETING-REPORT-01

## R-MARKETING-MESSAGE-01 — Текст отправленного письма неизменен

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено ограничением БД и 1 тестом

Триггер sent_messages_freeze_body запрещает менять body письма, у которого заполнен sent_at («письмо % уже отправлено, текст менять нельзя»). CHECK sent_messages_check требует sent_at у писем в статусах sent и bounced, CHECK sent_messages_status_check ограничивает статусы значениями queued, sent, skipped, bounced. В коде этих проверок нет: защищает только БД.

- БД: `sent_messages_check`, `sent_messages_status_check`
- Тесты: `tests/test_marketing_campaigns.py::test_finished_campaign_and_sent_letters_are_frozen`
- Связанные: R-MARKETING-DELIVERY-01

## R-MARKETING-TEST-01 — Тестовые письма — только до запуска, не больше MAX_TEST_MESSAGES и только при наличии шаблона

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

send_test_message разрешён для кампании в статусе draft или scheduled, с известным сегментом (по умолчанию paid), не больше MAX_TEST_MESSAGES (5) на кампанию. Если шаблон не найден, возникает DomainError «для этого сегмента нет шаблона письма». Письмо сразу сохраняется со статусом sent и is_test = true. Тестовые письма выводятся в списке писем кампании вместе с настоящими.

- Реализация: [`services/marketing/service.py::send_test_message:461-489`](../../services/marketing/service.py#L461), [`services/marketing/service.py::campaign_messages:444-449`](../../services/marketing/service.py#L444)
- Настройки: `services/marketing/settings.py::MAX_TEST_MESSAGES`, `services/marketing/settings.py::AUDIENCE_GROUP`, `services/marketing/service.py::NOT_STARTED`
- Тесты: `tests/test_marketing_api.py::test_test_messages_are_limited_and_purged`, `tests/test_marketing_api.py::test_test_message_then_campaign_messages`
- Связанные: R-MARKETING-TEST-02, R-MARKETING-TEST-03, R-MARKETING-TEMPLATE-02

## R-MARKETING-TEST-02 — Тестовые письма не входят в статистику, возвраты и уникальность адресатов

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Письма с is_test = true не учитываются в sent_count и skipped_count, в отчёте о пропусках и в подсчёте возвратов. Регистрация возврата по ним запрещена. Уникальный индекс (campaign_id, email) действует только для нетестовых писем, поэтому тестовое письмо можно отправить на адрес из аудитории.

- Реализация: [`services/marketing/service.py::summarize_campaign:407-410`](../../services/marketing/service.py#L407), [`services/marketing/service.py::campaign_report:429-435`](../../services/marketing/service.py#L429), [`services/marketing/service.py::register_bounce:496-497`](../../services/marketing/service.py#L496), [`services/marketing/service.py::handle_bounce:508-512`](../../services/marketing/service.py#L508)
- БД: `sent_messages_campaign_email_uq`
- Связанные: R-MARKETING-TEST-01, R-MARKETING-REPORT-01, R-MARKETING-BOUNCE-01

## R-MARKETING-TEST-03 — Тестовые письма удаляются через TEST_MESSAGE_TTL_DAYS после отправки

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Фоновая задача purge_test_messages физически удаляет тестовые письма, у которых sent_at раньше now − TEST_MESSAGE_TTL_DAYS (14 дней). Письма кампании не удаляются.

- Реализация: [`services/marketing/jobs.py::purge_test_messages:36-39`](../../services/marketing/jobs.py#L36), [`services/marketing/service.py::purge_test_messages:517-521`](../../services/marketing/service.py#L517)
- Настройки: `services/marketing/settings.py::TEST_MESSAGE_TTL_DAYS`
- Тесты: `tests/test_marketing_api.py::test_test_messages_are_limited_and_purged`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-TEST-01

## R-MARKETING-BOUNCE-01 — Возврат регистрируется только по отправленному письму кампании

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

register_bounce принимает только нетестовое письмо в статусе sent. Повторный возврат по тому же письму и возврат по тестовому, пропущенному или ещё не отправленному письму отклоняются с DomainError «возврат возможен только по отправленному письму кампании». Письмо переходит в bounced, публикуется marketing.message_bounced.

- Реализация: [`services/marketing/service.py::register_bounce:496-503`](../../services/marketing/service.py#L496)
- БД: `sent_messages_check`, `sent_messages_bounced_idx`
- Тесты: `tests/test_marketing_campaigns.py::test_repeated_bounces_unsubscribe_address`, `tests/test_marketing_api.py::test_unsubscribe_and_bounce_endpoints`
- Связанные: R-MARKETING-BOUNCE-02, R-MARKETING-ACCESS-03

## R-MARKETING-BOUNCE-02 — После BOUNCE_LIMIT возвратов адрес отписывается от всех рассылок сети

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

handle_bounce (подписчик marketing.message_bounced) считает все нетестовые письма адреса в статусе bounced по всем кампаниям и площадкам без ограничения по времени. Когда их становится BOUNCE_LIMIT (3) или больше, адрес отписывается от всей сети (venue_id = NULL) с причиной bounce. Это публикует marketing.unsubscribed и исключает адрес из аудиторий.

- Реализация: [`services/marketing/consumers.py::on_message_bounced:30-31`](../../services/marketing/consumers.py#L30), [`services/marketing/service.py::handle_bounce:508-514`](../../services/marketing/service.py#L508)
- Настройки: `services/marketing/settings.py::BOUNCE_LIMIT`
- Тесты: `tests/test_marketing_campaigns.py::test_repeated_bounces_unsubscribe_address`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-BOUNCE-01, R-MARKETING-UNSUBSCRIBE-02

## R-MARKETING-UNSUBSCRIBE-01 — Отписка от площадки или сети идемпотентна и требует известной причины

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

unsubscribe принимает причину из UNSUBSCRIBE_REASONS (reader, bounce, complaint, operator) и нормализует адрес. Если адрес уже отписан от всей сети или от этой площадки, возвращается существующая отписка без нового события. Иначе создаётся запись (venue_id = NULL — от всей сети) и публикуется marketing.unsubscribed. Отписка от площадки не мешает последующей отписке от сети. Список причин продублирован в CHECK БД, уникальность держат частичные индексы для сети и для площадки.

- Реализация: [`services/marketing/service.py::unsubscribe:530-549`](../../services/marketing/service.py#L530)
- БД: `unsubscriptions_reason_check`, `unsubscriptions_network_uq`, `unsubscriptions_venue_uq`
- Настройки: `services/marketing/service.py::UNSUBSCRIBE_REASONS`
- Тесты: `tests/test_marketing_campaigns.py::test_unsubscribed_reader_excluded_from_future_campaigns`, `tests/test_marketing_audiences.py::test_unsubscribed_address_cannot_be_added`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-UNSUBSCRIBE-02, R-MARKETING-ACCESS-03, R-MARKETING-BOUNCE-02

## R-MARKETING-UNSUBSCRIBE-02 — Отписка исключает адрес из аудиторий и снимает ещё не ушедшие письма

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

exclude_address (подписчик marketing.unsubscribed) ставит opted_out = true во всех аудиториях площадки отписки, а при отписке от сети — во всех аудиториях. Письма адреса в статусе queued в кампаниях, которые сейчас идут (preparing, sending), переводятся в skipped с причиной unsubscribed. Уже отправленные письма не меняются. Способа вернуть opted_out = false в коде нет.

- Реализация: [`services/marketing/consumers.py::on_unsubscribed:25-26`](../../services/marketing/consumers.py#L25), [`services/marketing/service.py::exclude_address:554-572`](../../services/marketing/service.py#L554)
- БД: `audience_members_email_idx`
- Настройки: `services/marketing/service.py::RUNNING`
- Тесты: `tests/test_marketing_campaigns.py::test_unsubscribe_skips_messages_not_yet_sent`, `tests/test_marketing_api.py::test_unsubscribe_and_bounce_endpoints`
- Роли: Система (события и фоновые задачи)
- Связанные: R-MARKETING-UNSUBSCRIBE-01, R-MARKETING-PREPARE-02

## R-MARKETING-UNSUBSCRIBE-03 — Отписка от площадки не влияет на рассылки других площадок

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Отписка с venue_id действует только на кампании и аудитории этой площадки: при подготовке писем и при добавлении в аудиторию учитываются отписки от сети и от площадки кампании или аудитории. Отписка от сети (venue_id = NULL) действует везде.

- Реализация: [`services/marketing/service.py::prepare_messages:342-351`](../../services/marketing/service.py#L342), [`services/marketing/service.py::is_unsubscribed:101-110`](../../services/marketing/service.py#L101), [`services/marketing/service.py::exclude_address:556-558`](../../services/marketing/service.py#L556)
- Тесты: `tests/test_marketing_campaigns.py::test_venue_unsubscribe_keeps_other_venues`
- Связанные: R-MARKETING-UNSUBSCRIBE-01, R-MARKETING-MEMBER-04, R-MARKETING-PREPARE-02
