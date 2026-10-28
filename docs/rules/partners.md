<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: partners

Источник: [`knowledge/rules/partners.yaml`](../../knowledge/rules/partners.yaml)

## R-PARTNERS-REQUEST-01 — Заявку на подключение принимают только с корректным ИНН

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Заявка на подключение агентства отклоняется с ошибкой «некорректный ИНН», если ИНН не состоит из 10 цифр или не сходится контрольная цифра (веса _INN_WEIGHTS, сумма mod 11 mod 10). В БД формат ИНН дополнительно ограничен CHECK на 10 цифр (контрольную сумму БД не проверяет).

- Реализация: [`services/partners/service.py::inn_valid:30-35`](../../services/partners/service.py#L30), [`services/partners/service.py::submit_request:86-87`](../../services/partners/service.py#L86)
- БД: `onboarding_requests_inn_check`, `partners_inn_check`
- Настройки: `services/partners/service.py::_INN_WEIGHTS`
- Тесты: `tests/test_partners_onboarding.py::test_request_with_bad_inn_is_refused`
- Связанные: R-PARTNERS-REQUEST-02

## R-PARTNERS-REQUEST-02 — КПП, если указан, должен состоять из 9 цифр

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

При подаче заявки и при правке реквизитов партнёра непустой КПП проверяется на 9 цифр (ошибка «КПП должен состоять из 9 цифр»). Пустой КПП (None) допускается. Это же ограничение продублировано CHECK в таблицах заявок и партнёров.

- Реализация: [`services/partners/service.py::_check_kpp:38-40`](../../services/partners/service.py#L38), [`services/partners/service.py::submit_request:88-88`](../../services/partners/service.py#L88), [`services/partners/service.py::update_requisites:223-224`](../../services/partners/service.py#L223)
- БД: `onboarding_requests_kpp_check`, `partners_kpp_check`
- Связанные: R-PARTNERS-REQUEST-01, R-PARTNERS-REQUISITES-01

## R-PARTNERS-REQUEST-03 — Подключённый партнёр не может подать новую заявку

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Заявка отклоняется с ошибкой «партнёр с таким ИНН уже подключён», если у партнёра с этим ИНН есть договор в статусе active или suspended. Договор в статусе draft подачу не блокирует.

- Реализация: [`services/partners/service.py::submit_request:89-95`](../../services/partners/service.py#L89)
- Тесты: `tests/test_partners_onboarding.py::test_connected_partner_cannot_apply_again`
- Связанные: R-PARTNERS-REQUEST-04

## R-PARTNERS-REQUEST-04 — Новая заявка с тем же ИНН закрывает открытые как дубли

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

При подаче заявки все открытые заявки с тем же ИНН переводятся в статус duplicate (decided_at = текущее время) с публикацией partners.request_closed_duplicate на каждую; затем создаётся новая открытая заявка. Подписчиков у события нет.

- Реализация: [`services/partners/service.py::submit_request:97-110`](../../services/partners/service.py#L97), [`services/partners/service.py::close_duplicates:57-73`](../../services/partners/service.py#L57)
- Тесты: `tests/test_partners_onboarding.py::test_new_request_supersedes_open_one`, `tests/test_partners_onboarding.py::test_close_duplicates_keeps_given_request`
- Связанные: R-PARTNERS-REQUEST-05

## R-PARTNERS-REQUEST-05 — В БД не больше одной открытой заявки на ИНН

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Частичный уникальный индекс запрещает две заявки со статусом open и одинаковым ИНН. Код соблюдает его, закрывая открытые заявки как дубли перед вставкой новой.

- Реализация: [`services/partners/service.py::close_duplicates:59-66`](../../services/partners/service.py#L59)
- БД: `ux_onboarding_requests_open_inn`
- Тесты: `tests/test_partners_onboarding.py::test_only_one_open_request_per_inn_in_database`
- Связанные: R-PARTNERS-REQUEST-04

## R-PARTNERS-REQUEST-06 — Решение по заявке принимается один раз

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Одобрить или отклонить можно только заявку в статусе open, иначе ошибка «по заявке уже принято решение». При решении фиксируются decided_at и decided_by (manager_id). CHECK в БД требует decided_at у любой не открытой заявки.

- Реализация: [`services/partners/service.py::_decide:114-120`](../../services/partners/service.py#L114)
- БД: `onboarding_requests_check1`
- Тесты: `tests/test_partners_onboarding.py::test_request_decided_only_once`
- Связанные: R-PARTNERS-REQUEST-07, R-PARTNERS-ONBOARD-01

## R-PARTNERS-REQUEST-07 — Отказ по заявке требует причины

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Отклонение заявки без непустой причины запрещено («укажите причину отказа»); причина сохраняется в reject_reason, публикуется partners.request_rejected (подписчиков нет). CHECK в БД требует reject_reason у отклонённой заявки.

- Реализация: [`services/partners/service.py::reject_request:133-138`](../../services/partners/service.py#L133)
- БД: `onboarding_requests_check`
- Тесты: `tests/test_partners_onboarding.py::test_request_decided_only_once`
- Связанные: R-PARTNERS-REQUEST-06

## R-PARTNERS-REQUEST-08 — Заявка без решения истекает через ONBOARDING_REQUEST_TTL_DAYS

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Фоновая задача переводит открытые заявки, поданные раньше чем ONBOARDING_REQUEST_TTL_DAYS (30) дней назад (от submitted_at), в статус expired и проставляет decided_at. Событие при этом не публикуется.

- Реализация: [`services/partners/jobs.py::expire_requests:46-58`](../../services/partners/jobs.py#L46)
- Настройки: `services/partners/settings.py::ONBOARDING_REQUEST_TTL_DAYS`
- Тесты: `tests/test_partners_jobs.py::test_stale_requests_expire`
- Роли: Система (события и фоновые задачи)

## R-PARTNERS-ONBOARD-01 — Одобрение заявки заводит партнёра и черновик договора

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Подписчик на partners.request_approved заводит партнёра по ИНН заявки (или дополняет существующего непустыми полями заявки) и, если у партнёра нет текущего договора (draft/active/suspended), создаёт черновик со ставкой DEFAULT_COMMISSION_PCT и сроком CONTRACT_TERM_DAYS от сегодняшней даты. Менеджером нового партнёра становится одобривший заявку; у существующего партнёра менеджер не меняется. Публикуется partners.partner_onboarded.

- Реализация: [`services/partners/consumers.py::on_request_approved:10-11`](../../services/partners/consumers.py#L10), [`services/partners/service.py::approve_request:123-127`](../../services/partners/service.py#L123), [`services/partners/service.py::onboard:147-182`](../../services/partners/service.py#L147)
- БД: `partners_inn_key`
- Настройки: `services/partners/settings.py::DEFAULT_COMMISSION_PCT`, `services/partners/settings.py::CONTRACT_TERM_DAYS`, `services/partners/service.py::CURRENT_CONTRACT`
- Тесты: `tests/test_partners_onboarding.py::test_approved_request_creates_partner_with_draft_contract`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-REQUEST-06, R-PARTNERS-ONBOARD-02, R-PARTNERS-CONTRACT-01

## R-PARTNERS-ONBOARD-02 — Заявка связывается с партнёром после онбординга

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Подписчик на partners.partner_onboarded записывает partner_id в заявку на подключение. Связь заявки с партнёром устанавливается только этим асинхронным шагом.

- Реализация: [`services/partners/consumers.py::on_partner_onboarded:15-16`](../../services/partners/consumers.py#L15), [`services/partners/service.py::link_request:185-187`](../../services/partners/service.py#L185)
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-ONBOARD-01

## R-PARTNERS-ONBOARD-03 — Номер договора формируется по ИНН, id партнёра и порядковому номеру

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Номер договора имеет вид «АГ-<последние 4 цифры ИНН>/<id партнёра>-<номер>», где номер — количество договоров партнёра + 1. Номер уникален в БД.

- Реализация: [`services/partners/service.py::_next_contract_number:142-144`](../../services/partners/service.py#L142)
- БД: `contracts_number_key`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-ONBOARD-01, R-PARTNERS-CONTRACT-09

## R-PARTNERS-ACCESS-01 — Партнёром и его договорами управляет только закреплённый менеджер

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Правка реквизитов, активация, ставка, кредитные условия, расторжение, перезаключение договора и действия со сделками (открытие, предоплата, закрытие, отмена) доступны только менеджеру, за которым закреплён партнёр (partner.manager_id); иначе AccessDenied «партнёр закреплён за другим менеджером». Регистрация оплаты сделки в кредит и чтение договора, истории, комиссий и ведомостей проверки менеджера не имеют.

- Реализация: [`services/partners/service.py::_partner_for_manager:193-199`](../../services/partners/service.py#L193), [`services/partners/service.py::_contract_for_manager:202-207`](../../services/partners/service.py#L202), [`services/partners/service.py::_deal_for_manager:387-392`](../../services/partners/service.py#L387)
- Тесты: `tests/test_partners_contracts.py::test_contract_managed_only_by_partner_manager`
- Связанные: R-PARTNERS-DEAL-06

## R-PARTNERS-REQUISITES-01 — Менеджер правит только разрешённые реквизиты партнёра

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Через правку реквизитов можно изменить только kpp, legal_name, contact_name, contact_email, contact_phone (EDITABLE_FIELDS); ИНН и прочие поля — ошибка «нельзя изменить поля: …». Ответ API возвращает список незаполненных обязательных реквизитов.

- Реализация: [`services/partners/service.py::update_requisites:219-232`](../../services/partners/service.py#L219), [`services/partners/api.py::update_requisites:114-117`](../../services/partners/api.py#L114)
- БД: `partners_contact_email_check`, `partners_legal_name_check`
- Настройки: `services/partners/service.py::EDITABLE_FIELDS`
- Связанные: R-PARTNERS-REQUISITES-02, R-PARTNERS-ACCESS-01

## R-PARTNERS-REQUISITES-02 — Нельзя очистить обязательные реквизиты при действующем договоре

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Если у партнёра есть текущий договор не в статусе draft (active/suspended), очистка любого из REQUIRED_PARTNER_FIELDS (inn, kpp, legal_name) запрещена: «нельзя удалить обязательные реквизиты партнёра с действующим договором». При черновике договора очищать можно.

- Реализация: [`services/partners/service.py::update_requisites:225-229`](../../services/partners/service.py#L225)
- Настройки: `services/partners/settings.py::REQUIRED_PARTNER_FIELDS`
- Тесты: `tests/test_partners_contracts.py::test_required_requisites_cannot_be_cleared_on_active_contract`
- Связанные: R-PARTNERS-CONTRACT-02

## R-PARTNERS-CONTRACT-01 — У партнёра не больше одного текущего договора

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Текущими считаются договоры в статусах draft, active, suspended (CURRENT_CONTRACT). Частичный уникальный индекс в БД запрещает второй такой договор у партнёра; код перед созданием проверяет наличие текущего договора.

- Реализация: [`services/partners/service.py::current_contract:210-213`](../../services/partners/service.py#L210)
- БД: `ux_contracts_partner_current`, `contracts_status_check`
- Настройки: `services/partners/service.py::CURRENT_CONTRACT`
- Связанные: R-PARTNERS-ONBOARD-01, R-PARTNERS-CONTRACT-09

## R-PARTNERS-CONTRACT-02 — Договор активируется только из черновика при заполненных реквизитах и в сроке

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Активировать можно только договор в статусе draft; у партнёра должны быть заполнены ИНН, КПП и наименование (REQUIRED_PARTNER_FIELDS, в ошибке — названия из REQUISITE_TITLES); дата окончания договора не должна быть в прошлом. Триггер БД при переходе draft→active повторно проверяет реквизиты партнёра. Публикуется partners.contract_activated (подписчиков нет).

- Реализация: [`services/partners/service.py::activate_contract:239-256`](../../services/partners/service.py#L239), [`services/partners/service.py::missing_requisites:43-44`](../../services/partners/service.py#L43)
- БД: `trg_contract_requisites`, `check_partner_requisites`
- Настройки: `services/partners/settings.py::REQUIRED_PARTNER_FIELDS`, `services/partners/settings.py::REQUISITE_TITLES`
- Тесты: `tests/test_partners_contracts.py::test_contract_not_activated_without_requisites`
- Связанные: R-PARTNERS-REQUISITES-02

## R-PARTNERS-CONTRACT-03 — Ставка комиссии от 0 до MAX_COMMISSION_PCT, только на текущем договоре

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Менеджер меняет ставку комиссии только на договоре в статусе draft/active/suspended («договор закрыт» иначе); ставка должна быть в пределах 0..MAX_COMMISSION_PCT (30%). В БД — CHECK 0..100. Публикуется partners.contract_rate_changed (подписчиков нет), изменение пишется в историю триггером.

- Реализация: [`services/partners/service.py::change_commission_rate:267-278`](../../services/partners/service.py#L267), [`services/partners/service.py::_check_rate:259-261`](../../services/partners/service.py#L259)
- БД: `contracts_commission_pct_check`
- Настройки: `services/partners/settings.py::MAX_COMMISSION_PCT`, `services/partners/service.py::CURRENT_CONTRACT`
- Тесты: `tests/test_partners_contracts.py::test_commission_rate_bounds`
- Связанные: R-PARTNERS-CONTRACT-07, R-PARTNERS-COMMISSION-02

## R-PARTNERS-CONTRACT-04 — Кредитный лимит от 0 до MAX_CREDIT_LIMIT; без кредита лимит обнуляется

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Кредитные условия меняются только на текущем договоре; отрицательный лимит и лимит выше MAX_CREDIT_LIMIT (500 000, «без согласования») запрещены. При запрете кредита лимит принудительно ставится 0 (CHECK в БД требует credit_limit = 0 без credit_allowed). Лимит не сверяется с текущей задолженностью; событие не публикуется, изменение попадает в историю триггером.

- Реализация: [`services/partners/service.py::set_credit_terms:284-294`](../../services/partners/service.py#L284)
- БД: `contracts_check1`, `contracts_credit_limit_check`
- Настройки: `services/partners/settings.py::MAX_CREDIT_LIMIT`, `services/partners/service.py::CURRENT_CONTRACT`
- Тесты: `tests/test_partners_api.py::test_contract_terms_through_api`
- Связанные: R-PARTNERS-CREDIT-02, R-PARTNERS-CONTRACT-07

## R-PARTNERS-CONTRACT-05 — Договор с истёкшим сроком переводится в expired

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Фоновая задача переводит договоры active/suspended с valid_to раньше сегодняшней даты в статус expired, сбрасывает причину приостановки и отменяет сделки в ожидании предоплаты; открытые и неоплаченные кредитные сделки не трогаются. Публикуется partners.contract_expired (подписчиков нет). Черновики с истёкшим сроком не истекают.

- Реализация: [`services/partners/jobs.py::expire_contracts:33-43`](../../services/partners/jobs.py#L33), [`services/partners/service.py::expire_contract:541-549`](../../services/partners/service.py#L541)
- БД: `contracts_check`
- Настройки: `services/partners/settings.py::CONTRACT_TERM_DAYS`
- Тесты: `tests/test_partners_jobs.py::test_contract_expires_after_term`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-ONBOARD-01

## R-PARTNERS-CONTRACT-06 — Расторжение договора требует причины и отсутствия открытых сделок и долга

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Расторгнуть можно только текущий договор (draft/active/suspended) с непустой причиной; запрещено, если есть сделки в статусе open или неоплаченная задолженность по сделкам в кредит. Сделки в ожидании предоплаты отменяются, договор получает статус terminated, публикуется partners.contract_terminated (подписчиков нет). Причина в договоре не сохраняется — только в событии.

- Реализация: [`services/partners/service.py::terminate_contract:555-575`](../../services/partners/service.py#L555)
- Настройки: `services/partners/service.py::CURRENT_CONTRACT`
- Тесты: `tests/test_partners_contracts.py::test_terminated_contract_can_be_renewed`
- Связанные: R-PARTNERS-CREDIT-01, R-PARTNERS-CONTRACT-09

## R-PARTNERS-CONTRACT-07 — Изменения условий договора журналируются триггером БД

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Триггер AFTER UPDATE на договорах пишет в contract_history старое и новое значение при изменении commission_pct, credit_allowed, credit_limit и status. Код журнал не ведёт, только читает его.

- Реализация: [`services/partners/service.py::contract_history:602-606`](../../services/partners/service.py#L602)
- БД: `trg_contract_history`, `log_contract_change`, `contract_history_field_check`
- Тесты: `tests/test_partners_commissions.py::test_rate_change_does_not_touch_accrued_commission`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-CONTRACT-03, R-PARTNERS-CONTRACT-04

## R-PARTNERS-CONTRACT-08 — Приостановленный договор обязан иметь причину

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

CHECK в БД требует suspend_reason у договора в статусе suspended. Код ставит причину при приостановке и сбрасывает её при возобновлении, истечении и расторжении.

- Реализация: [`services/partners/service.py::suspend_contract:314-315`](../../services/partners/service.py#L314)
- БД: `contracts_check2`
- Связанные: R-PARTNERS-CREDIT-03

## R-PARTNERS-CONTRACT-09 — Новый договор создаётся на условиях последнего, если нет текущего

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Перезаключение возможно, только если у партнёра нет договора в статусе draft/active/suspended. Новый черновик копирует ставку и кредитные условия последнего договора партнёра (или берёт DEFAULT_COMMISSION_PCT и кредит выключен), срок — CONTRACT_TERM_DAYS от сегодня.

- Реализация: [`services/partners/service.py::renew_contract:580-599`](../../services/partners/service.py#L580)
- БД: `ux_contracts_partner_current`
- Настройки: `services/partners/settings.py::DEFAULT_COMMISSION_PCT`, `services/partners/settings.py::CONTRACT_TERM_DAYS`
- Тесты: `tests/test_partners_contracts.py::test_terminated_contract_can_be_renewed`
- Связанные: R-PARTNERS-CONTRACT-01, R-PARTNERS-CONTRACT-06

## R-PARTNERS-DEAL-01 — Сделка открывается только по действующему договору в сроке

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Новая сделка запрещена по приостановленному договору («договор приостановлен, новые сделки запрещены»), по договору не в статусе active и вне периода valid_from..valid_to. Сумма должна быть положительной (также CHECK в БД), внешний номер сделки уникален в пределах договора.

- Реализация: [`services/partners/service.py::_in_force:343-349`](../../services/partners/service.py#L343), [`services/partners/service.py::open_deal:355-364`](../../services/partners/service.py#L355)
- БД: `deals_amount_check`, `deals_contract_id_external_ref_key`
- Тесты: `tests/test_partners_jobs.py::test_overdue_credit_suspends_contract`
- Связанные: R-PARTNERS-DEAL-02, R-PARTNERS-CREDIT-02

## R-PARTNERS-DEAL-02 — Режим сделки определяется договором — в кредит или с предоплатой

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Если договор разрешает кредит, сделка открывается сразу в статусе open со сроком оплаты created_at + CREDIT_PAYMENT_DAYS (14 дней); иначе — в статусе awaiting_prepayment без срока. CHECK в БД: due_at задан тогда и только тогда, когда сделка в кредит; кредитная сделка не может ожидать предоплаты или иметь prepaid_at.

- Реализация: [`services/partners/service.py::open_deal:366-376`](../../services/partners/service.py#L366)
- БД: `deals_check`, `deals_check1`, `deals_status_check`
- Настройки: `services/partners/settings.py::CREDIT_PAYMENT_DAYS`
- Тесты: `tests/test_partners_contracts.py::test_credit_deal_goes_without_prepayment`, `tests/test_partners_contracts.py::test_deal_without_credit_needs_prepayment`
- Связанные: R-PARTNERS-DEAL-03, R-PARTNERS-CREDIT-04

## R-PARTNERS-DEAL-03 — Сделку без кредита закрывают только после предоплаты

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Предоплата регистрируется только для сделки в статусе awaiting_prepayment (переводит её в open, ставит prepaid_at). Закрытие сделки в ожидании предоплаты запрещено; закрыть можно только сделку в статусе open — ставится closed_at (CHECK в БД) и публикуется partners.deal_closed.

- Реализация: [`services/partners/service.py::register_prepayment:396-401`](../../services/partners/service.py#L396), [`services/partners/service.py::close_deal:405-422`](../../services/partners/service.py#L405)
- БД: `deals_check2`
- Тесты: `tests/test_partners_contracts.py::test_deal_without_credit_needs_prepayment`
- Связанные: R-PARTNERS-COMMISSION-01

## R-PARTNERS-DEAL-04 — Отменить можно только незакрытую сделку

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Отмена разрешена для сделок в статусах awaiting_prepayment и open; закрытую или уже отменённую сделку отменить нельзя. Отменённая сделка перестаёт учитываться в кредитной задолженности, комиссия по ней не начисляется. Публикуется partners.deal_cancelled (подписчиков нет).

- Реализация: [`services/partners/service.py::cancel_deal:426-431`](../../services/partners/service.py#L426)
- Тесты: `tests/test_partners_contracts.py::test_cancelled_deal_releases_credit`, `tests/test_partners_commissions.py::test_no_commission_for_cancelled_deal`
- Связанные: R-PARTNERS-CREDIT-01, R-PARTNERS-COMMISSION-01

## R-PARTNERS-DEAL-05 — Оплата регистрируется только по кредитной сделке и один раз

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Регистрация оплаты запрещена для сделки с предоплатой («сделка оплачена предоплатой»), а также для уже оплаченной или отменённой сделки. Оплата ставит paid_at (статус сделки не меняется) и публикует partners.deal_paid.

- Реализация: [`services/partners/service.py::register_payment:439-445`](../../services/partners/service.py#L439)
- Тесты: `tests/test_partners_contracts.py::test_lowered_limit_blocks_all_deals_until_paid`
- Связанные: R-PARTNERS-CREDIT-03, R-PARTNERS-DEAL-06

## R-PARTNERS-DEAL-06 — Оплату кредитной сделки регистрируют без проверки менеджера

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Маршрут POST /deals/{deal_id}/payment и register_payment не принимают manager_id и не проверяют закрепление партнёра — в отличие от остальных действий со сделками.

- Реализация: [`services/partners/api.py::payment:161-162`](../../services/partners/api.py#L161), [`services/partners/service.py::register_payment:434-438`](../../services/partners/service.py#L434)
- Связанные: R-PARTNERS-ACCESS-01, R-PARTNERS-DEAL-05

## R-PARTNERS-CREDIT-01 — Кредитная задолженность — сумма неоплаченных неотменённых сделок в кредит

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Задолженность по договору считается как сумма amount сделок on_credit без paid_at и не в статусе cancelled (закрытые неоплаченные входят). Она показывается в карточке договора как credit_used и блокирует расторжение; та же формула используется в триггере лимита.

- Реализация: [`services/partners/service.py::credit_exposure:297-307`](../../services/partners/service.py#L297), [`services/partners/api.py::contract:125-133`](../../services/partners/api.py#L125)
- БД: `ix_deals_contract_unpaid_credit`
- Тесты: `tests/test_partners_contracts.py::test_cancelled_deal_releases_credit`, `tests/test_partners_api.py::test_credit_limit_and_commissions_via_api`
- Связанные: R-PARTNERS-CREDIT-02, R-PARTNERS-CONTRACT-06

## R-PARTNERS-CREDIT-02 — Кредитный лимит проверяет только триггер БД при вставке сделки

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Триггер BEFORE INSERT на сделках запрещает кредитную сделку по договору без кредита; запрещает любую новую сделку (включая с предоплатой), если текущая задолженность уже выше лимита (например, после снижения лимита); и запрещает кредитную сделку, если задолженность плюс её сумма превысит лимит. В коде проверки лимита нет — ошибка приходит из БД (check_violation).

- Реализация: [`services/partners/service.py::open_deal:366-378`](../../services/partners/service.py#L366)
- БД: `trg_contract_credit_limit`, `check_credit_limit`
- Тесты: `tests/test_partners_contracts.py::test_credit_limit_blocks_new_deal`, `tests/test_partners_contracts.py::test_lowered_limit_blocks_all_deals_until_paid`
- Связанные: R-PARTNERS-CREDIT-01, R-PARTNERS-CONTRACT-04, R-PARTNERS-DEAL-01

## R-PARTNERS-CREDIT-03 — Просрочка оплаты кредитной сделки приостанавливает договор

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Фоновая задача помечает overdue_flagged у неоплаченных неотменённых кредитных сделок с due_at в прошлом и публикует partners.credit_overdue по каждой (однократно). Подписчик приостанавливает договор, если он active, с причиной credit_overdue и публикует partners.contract_suspended (подписчиков нет).

- Реализация: [`services/partners/jobs.py::flag_overdue_credit:11-30`](../../services/partners/jobs.py#L11), [`services/partners/consumers.py::on_credit_overdue:30-31`](../../services/partners/consumers.py#L30), [`services/partners/service.py::suspend_contract:310-317`](../../services/partners/service.py#L310)
- БД: `contracts_check2`
- Настройки: `services/partners/settings.py::CREDIT_PAYMENT_DAYS`
- Тесты: `tests/test_partners_jobs.py::test_overdue_credit_suspends_contract`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-CREDIT-04, R-PARTNERS-CONTRACT-08, R-PARTNERS-DEAL-01

## R-PARTNERS-CREDIT-04 — Договор возобновляется после оплаты всех просроченных сделок

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

На partners.deal_paid подписчик возобновляет договор (suspended→active, причина сбрасывается, публикуется partners.contract_resumed), только если причина приостановки — credit_overdue и по договору не осталось неоплаченных неотменённых сделок с overdue_flagged.

- Реализация: [`services/partners/consumers.py::on_deal_paid:35-36`](../../services/partners/consumers.py#L35), [`services/partners/service.py::resume_if_settled:320-337`](../../services/partners/service.py#L320)
- Тесты: `tests/test_partners_jobs.py::test_paying_all_overdue_deals_resumes_contract`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-CREDIT-03, R-PARTNERS-DEAL-05

## R-PARTNERS-COMMISSION-01 — Комиссия начисляется один раз при закрытии сделки

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

На partners.deal_closed подписчик начисляет комиссию по закрытой сделке, если по ней ещё нет начисления (также UNIQUE deal_id в БД): база — сумма сделки, ставка — текущая ставка договора на момент начисления. Публикуется partners.commission_accrued.

- Реализация: [`services/partners/consumers.py::on_deal_closed:20-21`](../../services/partners/consumers.py#L20), [`services/partners/service.py::accrue_commission:455-482`](../../services/partners/service.py#L455)
- БД: `commissions_deal_id_key`, `commissions_base_amount_check`, `commissions_rate_pct_check`
- Тесты: `tests/test_partners_commissions.py::test_commission_accrued_on_deal_closed`, `tests/test_partners_commissions.py::test_no_commission_for_cancelled_deal`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-COMMISSION-02, R-PARTNERS-PAYOUT-01

## R-PARTNERS-COMMISSION-02 — Сумма комиссии включает базу сделки

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

amount комиссии считается как base × (1 + pct/100) с округлением до копейки ROUND_HALF_UP, т.е. это сумма сделки плюс комиссия, а не сама комиссия. CHECK в БД требует amount >= base_amount.

- Реализация: [`services/partners/service.py::commission_amount:451-452`](../../services/partners/service.py#L451)
- БД: `commissions_check`
- Настройки: `services/partners/service.py::CENT`
- Тесты: `tests/test_partners_commissions.py::test_commission_accrued_on_deal_closed`
- Связанные: R-PARTNERS-COMMISSION-01

## R-PARTNERS-COMMISSION-03 — Начисленная комиссия не пересчитывается

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Триггер БД запрещает менять amount, rate_pct и base_amount начисленной комиссии; смена ставки договора на уже начисленные комиссии не влияет. Менять можно только payout_id.

- Реализация: [`services/partners/service.py::accrue_commission:462-470`](../../services/partners/service.py#L462)
- БД: `trg_commission_frozen`, `forbid_commission_change`
- Тесты: `tests/test_partners_commissions.py::test_accrued_commission_is_frozen_in_database`, `tests/test_partners_commissions.py::test_rate_change_does_not_touch_accrued_commission`
- Связанные: R-PARTNERS-CONTRACT-03

## R-PARTNERS-PAYOUT-01 — Комиссия попадает в месячную ведомость партнёра

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

На partners.commission_accrued подписчик добавляет комиссию в ведомость партнёра за месяц начисления (period — первое число месяца), увеличивая total и commissions_count. Если ведомость этого месяца уже закрыта, комиссия уходит в ведомость следующего месяца. Ведомость на партнёра и период одна (UNIQUE).

- Реализация: [`services/partners/consumers.py::on_commission_accrued:25-26`](../../services/partners/consumers.py#L25), [`services/partners/service.py::add_to_payout:485-503`](../../services/partners/service.py#L485), [`services/partners/service.py::_open_payout:506-514`](../../services/partners/service.py#L506)
- БД: `payouts_partner_id_period_key`, `payouts_period_check`, `payouts_total_check`, `payouts_commissions_count_check`
- Тесты: `tests/test_partners_commissions.py::test_commissions_collected_into_monthly_payout`, `tests/test_partners_commissions.py::test_closed_payout_period`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-COMMISSION-01, R-PARTNERS-PAYOUT-02

## R-PARTNERS-PAYOUT-02 — Ведомость закрывается только после окончания месяца

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Закрыть можно только открытую ведомость прошедшего месяца; ведомость текущего месяца закрыть нельзя. Фоновая задача закрывает все открытые ведомости с периодом раньше начала текущего месяца и публикует partners.payout_closed (подписчиков нет).

- Реализация: [`services/partners/jobs.py::close_payouts:61-71`](../../services/partners/jobs.py#L61), [`services/partners/service.py::close_payout:517-531`](../../services/partners/service.py#L517)
- БД: `payouts_status_check`
- Тесты: `tests/test_partners_commissions.py::test_closed_payout_period`
- Роли: Система (события и фоновые задачи)
- Связанные: R-PARTNERS-PAYOUT-01
