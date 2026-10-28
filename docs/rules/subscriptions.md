<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: subscriptions

Источник: [`knowledge/rules/subscriptions.yaml`](../../knowledge/rules/subscriptions.yaml)

## R-SUBSCRIPTIONS-PLAN-01 — Тариф создаётся только известного вида, с положительной ценой и уникальным кодом

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

create_plan отклоняет вид тарифа вне PLAN_KINDS (regular, social, corporate), стоимость в месяц <= 0 и код, который уже есть. Те же условия дублирует БД: ck_plans_kind, ck_plans_fee, uq_plans_code. Лимит книг max_books (1–50) проверяет только CHECK ck_plans_max_books, в коде его проверки нет.

- Реализация: [`services/subscriptions/service.py::create_plan:56-61`](../../services/subscriptions/service.py#L56)
- БД: `ck_plans_kind`, `ck_plans_fee`, `ck_plans_max_books`, `uq_plans_code`
- Настройки: `services/subscriptions/service.py::PLAN_KINDS`
- Роли: Администратор
- Связанные: R-SUBSCRIPTIONS-PLAN-02

## R-SUBSCRIPTIONS-PLAN-02 — Архивный тариф не продаётся и не показывается, но действующие абонементы на нём продлеваются

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

archive_plan ставит у тарифа флаг archived. list_plans (GET /plans) показывает только тарифы без архивного флага, а create_subscription отклоняет оформление на архивный тариф («тариф больше не продаётся»). Выставление счетов за продление (issue_renewal_invoices) флаг archived не проверяет, поэтому уже действующие абонементы на архивном тарифе продолжают продлеваться по его цене.

- Реализация: [`services/subscriptions/service.py::archive_plan:68-71`](../../services/subscriptions/service.py#L68), [`services/subscriptions/service.py::list_plans:81-83`](../../services/subscriptions/service.py#L81), [`services/subscriptions/service.py::create_subscription:135-136`](../../services/subscriptions/service.py#L135)
- Тесты: `tests/test_subscriptions_holder.py::test_archived_plan_not_sold`
- Роли: Администратор, Клиент
- Связанные: R-SUBSCRIPTIONS-RENEWAL-01

## R-SUBSCRIPTIONS-CREATE-01 — Организация-работодатель указывается только для корпоративного тарифа и для него обязательна

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

При оформлении абонемента на корпоративный тариф нужен employer_ref («для корпоративного тарифа нужна организация-работодатель»). Для обычного и социального тарифа указать организацию нельзя («организация указывается только для корпоративного тарифа»).

- Реализация: [`services/subscriptions/service.py::create_subscription:137-140`](../../services/subscriptions/service.py#L137)
- Тесты: `tests/test_subscriptions_holder.py::test_corporate_plan_requires_employer`
- Роли: Клиент

## R-SUBSCRIPTIONS-HOLDER-01 — Данные держателя проходят проверку формата и возраста

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

_validate_holder вызывается при оформлении и при изменении данных держателя. Имя не должно быть пустым. Паспорт, если он указан, должен быть в формате «1234 567890» (PASSPORT_RE). Дата рождения должна быть в прошлом, а возраст держателя — не меньше MIN_HOLDER_AGE (14 лет). Паспорт и дата рождения необязательны, кроме социального тарифа.

- Реализация: [`services/subscriptions/service.py::_validate_holder:106-114`](../../services/subscriptions/service.py#L106)
- Настройки: `services/subscriptions/service.py::PASSPORT_RE`, `services/subscriptions/settings.py::MIN_HOLDER_AGE`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-HOLDER-02, R-SUBSCRIPTIONS-HOLDER-04

## R-SUBSCRIPTIONS-SOCIAL-01 — Для социального тарифа обязательны паспорт и дата рождения

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Абонемент на социальный тариф нельзя оформить или изменить без паспорта и даты рождения держателя (_validate_holder: «для социального тарифа нужны паспорт и дата рождения»).

- Реализация: [`services/subscriptions/service.py::_validate_holder:115-116`](../../services/subscriptions/service.py#L115)
- Тесты: `tests/test_subscriptions_holder.py::test_social_plan_needs_eligible_holder`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-SOCIAL-02

## R-SUBSCRIPTIONS-SOCIAL-02 — Социальный тариф доступен держателям не старше 23 лет или от 60 лет

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

При оформлении социального абонемента возраст держателя на сегодня должен быть <= SOCIAL_MAX_STUDENT_AGE (23) или >= SOCIAL_MIN_SENIOR_AGE (60). Иначе create_subscription отклоняет оформление («социальный тариф доступен студентам и пенсионерам»). Статус студента или пенсионера код не проверяет, только возраст.

- Реализация: [`services/subscriptions/service.py::_social_eligible:119-121`](../../services/subscriptions/service.py#L119), [`services/subscriptions/service.py::create_subscription:144-145`](../../services/subscriptions/service.py#L144)
- Настройки: `services/subscriptions/settings.py::SOCIAL_MAX_STUDENT_AGE`, `services/subscriptions/settings.py::SOCIAL_MIN_SENIOR_AGE`
- Тесты: `tests/test_subscriptions_holder.py::test_social_plan_needs_eligible_holder`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-SOCIAL-01, R-SUBSCRIPTIONS-HOLDER-03

## R-SUBSCRIPTIONS-CREATE-02 — У клиента не может быть двух действующих абонементов на один тариф

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

create_subscription отклоняет оформление, если у клиента уже есть абонемент на этот тариф в статусе active или grace (LIVE) — его предлагают продлить. БД дублирует запрет частичным уникальным индексом uq_subscriptions_one_active на (client_ref, plan_id) WHERE status IN ('active','grace'). Абонементы в статусе pending на тот же тариф этот запрет не ограничивает.

- Реализация: [`services/subscriptions/service.py::create_subscription:147-155`](../../services/subscriptions/service.py#L147)
- БД: `uq_subscriptions_one_active`
- Настройки: `services/subscriptions/service.py::LIVE`
- Тесты: `tests/test_subscriptions_activation.py::test_second_subscription_on_live_plan_rejected`, `tests/test_subscriptions_activation.py::test_database_keeps_one_live_subscription_per_plan`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-CREATE-03, R-SUBSCRIPTIONS-DEDUP-01

## R-SUBSCRIPTIONS-CREATE-03 — Клиент может держать не больше трёх неоплаченных абонементов

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

create_subscription считает абонементы клиента в статусе pending по всем тарифам. Если их уже MAX_PENDING_PER_CLIENT (3) или больше, новый абонемент не оформляется («у клиента слишком много неоплаченных абонементов»). Ограничение есть только в коде, в БД его нет.

- Реализация: [`services/subscriptions/service.py::create_subscription:156-160`](../../services/subscriptions/service.py#L156)
- Настройки: `services/subscriptions/settings.py::MAX_PENDING_PER_CLIENT`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-PENDING-01

## R-SUBSCRIPTIONS-CREATE-04 — Новый абонемент создаётся неоплаченным, и на него сразу выставляется счёт за первый месяц

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

create_subscription создаёт абонемент в статусе pending и сразу выставляет счёт за месяц, начиная с сегодняшней даты (issue_invoice). Затем публикуется subscriptions.created, по которому данные держателя отправляются на сверку. POST /subscriptions возвращает id абонемента и id открытого счёта.

- Реализация: [`services/subscriptions/service.py::create_subscription:162-178`](../../services/subscriptions/service.py#L162), [`services/subscriptions/api.py::create:80-83`](../../services/subscriptions/api.py#L80)
- Тесты: `tests/test_subscriptions_api.py::test_subscribe_and_pay_over_api`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-INVOICE-01, R-SUBSCRIPTIONS-HOLDER-02

## R-SUBSCRIPTIONS-HOLDER-02 — Сверка держателя отклоняет абонемент без паспорта или даты рождения при любом тарифе

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

При subscriptions.created и subscriptions.holder_updated recheck_holder проверяет абонемент с holder_check=pending, если он не закрыт. Без паспорта или даты рождения абонемент получает holder_check=rejected даже на обычном и корпоративном тарифе, хотя при оформлении эти поля там необязательны. Если данные полные и подходят под тариф, ставится verified. При отклонении публикуется subscriptions.holder_rejected. Отклонённая сверка не блокирует ни оплату, ни активацию абонемента.

- Реализация: [`services/subscriptions/consumers.py::on_created:10-11`](../../services/subscriptions/consumers.py#L10), [`services/subscriptions/consumers.py::on_holder_updated:15-16`](../../services/subscriptions/consumers.py#L15), [`services/subscriptions/service.py::recheck_holder:218-232`](../../services/subscriptions/service.py#L218)
- БД: `ck_subscriptions_holder_check`
- Тесты: `tests/test_subscriptions_holder.py::test_holder_without_passport_is_rejected`, `tests/test_subscriptions_holder.py::test_complete_holder_is_verified`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-HOLDER-01, R-SUBSCRIPTIONS-HOLDER-03, R-SUBSCRIPTIONS-NOTICE-01

## R-SUBSCRIPTIONS-HOLDER-03 — При сверке социального абонемента возраст держателя проверяется заново на текущую дату

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

recheck_holder проверяет право на социальный тариф (_social_eligible) по возрасту на сегодня. Например, держатель, которому исполнилось 24 года, при изменении данных получает holder_check=rejected и уведомление. Сверка запускается только при оформлении и при изменении данных держателя. Периодической перепроверки возраста нет, и сам абонемент при отклонении не закрывается.

- Реализация: [`services/subscriptions/service.py::recheck_holder:226-232`](../../services/subscriptions/service.py#L226)
- Настройки: `services/subscriptions/settings.py::SOCIAL_MAX_STUDENT_AGE`, `services/subscriptions/settings.py::SOCIAL_MIN_SENIOR_AGE`
- Тесты: `tests/test_subscriptions_holder.py::test_student_social_plan_rejected_on_recheck_after_birthday`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-SOCIAL-02, R-SUBSCRIPTIONS-HOLDER-02

## R-SUBSCRIPTIONS-HOLDER-04 — Данные держателя меняет только владелец незакрытого абонемента

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

update_holder (PUT /subscriptions/{id}/holder) отклоняет изменение с AccessDenied, если client_ref не совпадает с владельцем абонемента. У закрытого абонемента (expired, closed_duplicate) данные держателя не меняются. client_ref передаётся в теле запроса, аутентификации и проверки роли в API нет.

- Реализация: [`services/subscriptions/service.py::update_holder:192-195`](../../services/subscriptions/service.py#L192)
- Настройки: `services/subscriptions/service.py::CLOSED`
- Тесты: `tests/test_subscriptions_holder.py::test_holder_updated_only_by_owner`, `tests/test_subscriptions_holder.py::test_closed_subscription_holder_is_frozen`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-HOLDER-05, R-SUBSCRIPTIONS-API-01

## R-SUBSCRIPTIONS-HOLDER-05 — Изменение данных держателя отправляет абонемент на повторную сверку

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

update_holder сравнивает новые значения holder_name, passport и birth_date с текущими. Если ничего не изменилось, ничего не происходит. Иначе поля обновляются, holder_check сбрасывается в pending и публикуется subscriptions.holder_updated, а подписчик запускает recheck_holder. Поле, переданное как null, остаётся прежним, поэтому очистить паспорт или дату рождения нельзя.

- Реализация: [`services/subscriptions/service.py::update_holder:198-212`](../../services/subscriptions/service.py#L198)
- Настройки: `services/subscriptions/service.py::HOLDER_FIELDS`
- Тесты: `tests/test_subscriptions_holder.py::test_holder_update_sends_subscription_to_recheck`, `tests/test_subscriptions_holder.py::test_unchanged_holder_data_is_not_rechecked`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-HOLDER-02

## R-SUBSCRIPTIONS-INVOICE-01 — По абонементу может быть только один открытый счёт

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

issue_invoice отклоняет выставление счёта, если у абонемента уже есть счёт в статусе open («по абонементу уже есть неоплаченный счёт»). БД дублирует запрет частичным уникальным индексом uq_invoices_one_open (subscription_id WHERE status='open'). Кроме того, uq_invoices_period запрещает два счёта на один и тот же период одного абонемента.

- Реализация: [`services/subscriptions/service.py::issue_invoice:246-247`](../../services/subscriptions/service.py#L246)
- БД: `uq_invoices_one_open`, `uq_invoices_period`, `ck_invoices_status`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-INVOICE-02, R-SUBSCRIPTIONS-RENEWAL-01

## R-SUBSCRIPTIONS-INVOICE-02 — Счёт выставляется за календарный месяц по текущей цене тарифа

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Счёт покрывает период с period_start по тот же день следующего месяца минус один день включительно (period_for/add_months; если в следующем месяце такого дня нет, берётся последний день месяца). Сумма равна monthly_fee тарифа на момент выставления. После выставления публикуется subscriptions.invoice_issued. CHECK-ограничения ck_invoices_amount и ck_invoices_period требуют положительную сумму и period_end > period_start.

- Реализация: [`services/subscriptions/service.py::period_for:32-34`](../../services/subscriptions/service.py#L32), [`services/subscriptions/service.py::add_months:25-29`](../../services/subscriptions/service.py#L25), [`services/subscriptions/service.py::issue_invoice:248-268`](../../services/subscriptions/service.py#L248)
- БД: `ck_invoices_amount`, `ck_invoices_period`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-INVOICE-01, R-SUBSCRIPTIONS-NOTICE-01

## R-SUBSCRIPTIONS-PAYMENT-01 — Платёж принимается только по открытому счёту, в пределах остатка и с положительной суммой

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

record_payment (POST /invoices/{id}/payments) блокирует счёт (FOR UPDATE) и отклоняет платёж, если счёт не в статусе open, если сумма <= 0 или если сумма больше остатка (amount - paid_total). Те же проверки дублирует БД: триггер trg_payments_guard (функция payments_guard) запрещает платёж по неоткрытому счёту и сверх остатка, ck_payments_amount требует положительную сумму, ck_invoices_paid_total — paid_total в пределах суммы счёта.

- Реализация: [`services/subscriptions/service.py::record_payment:275-283`](../../services/subscriptions/service.py#L275)
- БД: `trg_payments_guard`, `payments_guard`, `ck_payments_amount`, `ck_invoices_paid_total`
- Тесты: `tests/test_subscriptions_activation.py::test_overpayment_rejected`, `tests/test_subscriptions_activation.py::test_paid_invoice_does_not_take_payments`, `tests/test_subscriptions_activation.py::test_database_rejects_payment_above_balance`
- Роли: Клиент, Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-PAYMENT-02, R-SUBSCRIPTIONS-PAYMENT-03

## R-SUBSCRIPTIONS-PAYMENT-02 — Внешний платёж с одним и тем же external_ref учитывается один раз

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Если у платежа есть external_ref, record_payment отклоняет его при наличии платежа с тем же идентификатором («платёж … уже учтён»). БД дублирует запрет частичным уникальным индексом uq_payments_external_ref. Платежи без external_ref не дедуплицируются.

- Реализация: [`services/subscriptions/service.py::record_payment:284-287`](../../services/subscriptions/service.py#L284)
- БД: `uq_payments_external_ref`
- Тесты: `tests/test_subscriptions_activation.py::test_same_external_payment_counted_once`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-PAYMENT-01

## R-SUBSCRIPTIONS-PAYMENT-03 — Оплаченную сумму счёта считает триггер БД, полная оплата закрывает счёт

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Код не меняет paid_total. Триггер trg_payments_apply (функция payments_apply) после вставки платежа прибавляет его сумму к invoices.paid_total. record_payment перечитывает paid_total, и если счёт оплачен полностью (paid_total >= amount), ставит ему статус paid и публикует subscriptions.payment_completed. Частичная оплата оставляет счёт открытым, и абонемент не меняется.

- Реализация: [`services/subscriptions/service.py::record_payment:289-299`](../../services/subscriptions/service.py#L289), [`services/subscriptions/service.py::fully_paid:41-42`](../../services/subscriptions/service.py#L41)
- БД: `trg_payments_apply`, `payments_apply`
- Тесты: `tests/test_subscriptions_activation.py::test_activation_only_after_full_payment`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-ACTIVATE-01

## R-SUBSCRIPTIONS-ACTIVATE-01 — Абонемент активируется только после полной оплаты первого счёта

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Подписчик subscriptions.payment_completed вызывает apply_payment. Если счёт не оплачен полностью, apply_payment ничего не меняет и выдаёт ошибку. Абонемент в статусе pending становится active: activated_at — текущее время, paid_until — конец периода счёта. Публикуется subscriptions.activated. Перед активацией закрываются дубли того же направления. Результат сверки держателя (holder_check) на активацию не влияет.

- Реализация: [`services/subscriptions/consumers.py::on_payment_completed:40-41`](../../services/subscriptions/consumers.py#L40), [`services/subscriptions/service.py::apply_payment:361-383`](../../services/subscriptions/service.py#L361)
- БД: `ck_subscriptions_paid_until`
- Тесты: `tests/test_subscriptions_activation.py::test_activation_only_after_full_payment`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-PAYMENT-03, R-SUBSCRIPTIONS-DEDUP-01, R-SUBSCRIPTIONS-STATUS-02

## R-SUBSCRIPTIONS-DEDUP-01 — При активации закрываются другие открытые абонементы клиента того же направления

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 5 тестами

close_duplicates при активации ставит статус closed_duplicate и closed_at всем другим абонементам клиента в статусах pending, active или grace из того же направления и публикует subscriptions.closed_duplicate. Направления два: социальное и платное, причём обычный и корпоративный тарифы считаются одним направлением. Поэтому оплата нового платного тарифа закрывает действующий платный абонемент на другом тарифе без возврата за оставшийся оплаченный срок. Социальный и платный абонементы действуют одновременно, абонементы других клиентов не затрагиваются.

- Реализация: [`services/subscriptions/service.py::close_duplicates:329-355`](../../services/subscriptions/service.py#L329), [`services/subscriptions/service.py::_same_track:45-47`](../../services/subscriptions/service.py#L45), [`services/subscriptions/service.py::apply_payment:373-374`](../../services/subscriptions/service.py#L373)
- Настройки: `services/subscriptions/service.py::OPEN`
- Тесты: `tests/test_subscriptions_activation.py::test_paid_subscription_closes_pending_duplicate`, `tests/test_subscriptions_activation.py::test_switching_paid_plan_closes_previous_one`, `tests/test_subscriptions_activation.py::test_corporate_and_regular_are_the_same_track`, `tests/test_subscriptions_activation.py::test_social_and_paid_plans_live_together`, `tests/test_subscriptions_activation.py::test_other_clients_are_not_duplicates`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-ACTIVATE-01, R-SUBSCRIPTIONS-DEDUP-02

## R-SUBSCRIPTIONS-DEDUP-02 — У закрытого дубля аннулируются открытые счета, частичная оплата подлежит возврату

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Подписчик subscriptions.closed_duplicate вызывает void_open_invoices: все открытые счета абонемента переводятся в void. Если по счёту уже есть частичная оплата (paid_total > 0), публикуется subscriptions.refund_required на эту сумму. Затем держателю создаётся уведомление о закрытии со ссылкой на сохранённый абонемент.

- Реализация: [`services/subscriptions/consumers.py::on_closed_duplicate:59-66`](../../services/subscriptions/consumers.py#L59), [`services/subscriptions/service.py::void_open_invoices:304-320`](../../services/subscriptions/service.py#L304)
- Тесты: `tests/test_subscriptions_activation.py::test_partly_paid_duplicate_is_refunded`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-DEDUP-01, R-SUBSCRIPTIONS-REFUND-01

## R-SUBSCRIPTIONS-REFUND-01 — Оплата, пришедшая на закрытый абонемент, подлежит возврату

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Если счёт оплачен полностью, а абонемент к этому моменту уже закрыт (expired или closed_duplicate), apply_payment не трогает статус и публикует subscriptions.refund_required на всю оплаченную сумму.

- Реализация: [`services/subscriptions/service.py::apply_payment:364-371`](../../services/subscriptions/service.py#L364)
- Настройки: `services/subscriptions/service.py::CLOSED`
- Тесты: `tests/test_subscriptions_activation.py::test_payment_for_closed_duplicate_is_refunded`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-REFUND-02, R-SUBSCRIPTIONS-DEDUP-02

## R-SUBSCRIPTIONS-REFUND-02 — Требование возврата в модуле только порождает уведомление

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Подписчик subscriptions.refund_required лишь создаёт держателю уведомление вида refund («Оплата … будет возвращена»). Сам возврат (модель Refund, таблица refunds) в модуле не создаётся: по описанию модели его проводит бухгалтерия, а кода записи возвратов в модуле нет.

- Реализация: [`services/subscriptions/consumers.py::on_refund_required:86-92`](../../services/subscriptions/consumers.py#L86)
- Тесты: `tests/test_subscriptions_activation.py::test_partly_paid_duplicate_is_refunded`, `tests/test_subscriptions_activation.py::test_payment_for_closed_duplicate_is_refunded`
- Роли: Система (события и фоновые задачи), Бухгалтер
- Связанные: R-SUBSCRIPTIONS-REFUND-01, R-SUBSCRIPTIONS-DEDUP-02

## R-SUBSCRIPTIONS-RENEWAL-01 — Счёт за следующий месяц выставляется за 7 дней до конца оплаченного периода

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Фоновая задача issue_renewal_invoices для абонементов в статусе active или grace без открытого счёта, у которых paid_until <= сегодня + RENEWAL_INVOICE_DAYS (7), выставляет счёт за месяц, начинающийся на следующий день после paid_until. Абонементы в grace тоже получают счёт.

- Реализация: [`services/subscriptions/jobs.py::issue_renewal_invoices:67-83`](../../services/subscriptions/jobs.py#L67)
- БД: `uq_invoices_one_open`
- Настройки: `services/subscriptions/settings.py::RENEWAL_INVOICE_DAYS`, `services/subscriptions/service.py::LIVE`
- Тесты: `tests/test_subscriptions_lifecycle.py::test_renewal_invoice_issued_week_before_end`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-RENEWAL-02, R-SUBSCRIPTIONS-INVOICE-01

## R-SUBSCRIPTIONS-RENEWAL-02 — Оплата продления продлевает paid_until и возвращает абонемент из grace в active

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

При полной оплате счёта по абонементу в статусе active или grace apply_payment ставит статус active и paid_until = max(paid_until, конец периода счёта), затем публикует subscriptions.renewed. Период продления отсчитывается от прежнего paid_until, а не от даты оплаты, поэтому дни в grace входят в оплаченный месяц.

- Реализация: [`services/subscriptions/service.py::apply_payment:385-391`](../../services/subscriptions/service.py#L385)
- Тесты: `tests/test_subscriptions_lifecycle.py::test_paying_renewal_extends_subscription`, `tests/test_subscriptions_lifecycle.py::test_grace_subscription_returns_to_active_after_payment`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-RENEWAL-01, R-SUBSCRIPTIONS-GRACE-01

## R-SUBSCRIPTIONS-GRACE-01 — После окончания оплаченного месяца абонемент переходит в льготный период (grace)

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Фоновая задача expire_overdue переводит абонементы в статусе active с paid_until < сегодня в статус grace и публикует subscriptions.grace_started. Дата grace_until = paid_until + GRACE_DAYS (30) передаётся держателю в уведомлении. В статусе grace абонемент ещё считается действующим (LIVE).

- Реализация: [`services/subscriptions/jobs.py::expire_overdue:30-44`](../../services/subscriptions/jobs.py#L30)
- Настройки: `services/subscriptions/settings.py::GRACE_DAYS`
- Тесты: `tests/test_subscriptions_lifecycle.py::test_unpaid_month_moves_to_grace`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-GRACE-02, R-SUBSCRIPTIONS-NOTICE-01

## R-SUBSCRIPTIONS-GRACE-02 — Через 30 дней после paid_until неоплаченный абонемент закрывается (срок задан литералом)

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

expire_overdue переводит абонементы в статусе active или grace с paid_until + 30 дней < сегодня в статус expired, ставит closed_at и публикует subscriptions.expired (reason=unpaid). Срок 30 дней здесь задан литералом, а не настройкой GRACE_DAYS. Если GRACE_DAYS изменить, фактический срок закрытия разойдётся с датой grace_until в уведомлении. Проверка на закрытие идёт до перевода в grace, поэтому «забытый» абонемент в статусе active с давно истёкшим paid_until закрывается сразу, минуя grace.

- Реализация: [`services/subscriptions/jobs.py::expire_overdue:14-28`](../../services/subscriptions/jobs.py#L14)
- БД: `ck_subscriptions_closed`
- Настройки: `services/subscriptions/settings.py::GRACE_DAYS`, `services/subscriptions/service.py::LIVE`
- Тесты: `tests/test_subscriptions_lifecycle.py::test_grace_ends_after_thirty_days`, `tests/test_subscriptions_lifecycle.py::test_forgotten_active_subscription_expires_directly`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-GRACE-01, R-SUBSCRIPTIONS-EXPIRE-01

## R-SUBSCRIPTIONS-PENDING-01 — Неоплаченный новый абонемент закрывается через 14 дней

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Фоновая задача expire_stale_pending переводит абонементы в статусе pending с created_at старше now - PENDING_TTL_DAYS (14 дней) в статус expired, ставит closed_at и публикует subscriptions.expired (reason=not_paid).

- Реализация: [`services/subscriptions/jobs.py::expire_stale_pending:49-63`](../../services/subscriptions/jobs.py#L49)
- БД: `ck_subscriptions_closed`
- Настройки: `services/subscriptions/settings.py::PENDING_TTL_DAYS`
- Тесты: `tests/test_subscriptions_lifecycle.py::test_unpaid_new_subscription_expires`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-EXPIRE-01, R-SUBSCRIPTIONS-CREATE-03

## R-SUBSCRIPTIONS-EXPIRE-01 — При закрытии абонемента по сроку его открытые счета аннулируются

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Подписчик subscriptions.expired вызывает void_open_invoices: открытые счета переходят в void, а при частичной оплате публикуется subscriptions.refund_required. Держателю создаётся уведомление «Абонемент закрыт: не оплачен.» — оно одно и то же для закрытия неоплаченного нового абонемента и для истечения льготного периода.

- Реализация: [`services/subscriptions/consumers.py::on_expired:80-82`](../../services/subscriptions/consumers.py#L80), [`services/subscriptions/service.py::void_open_invoices:304-320`](../../services/subscriptions/service.py#L304)
- Тесты: `tests/test_subscriptions_lifecycle.py::test_expired_subscription_voids_open_invoice`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-GRACE-02, R-SUBSCRIPTIONS-PENDING-01, R-SUBSCRIPTIONS-REFUND-02

## R-SUBSCRIPTIONS-STATUS-01 — Закрытый абонемент нельзя открыть снова (триггер БД)

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Триггер trg_subscriptions_terminal_guard (функция subscriptions_terminal_guard) запрещает менять статус абонемента из expired или closed_duplicate на любой другой. CHECK ck_subscriptions_closed требует, чтобы closed_at был заполнен ровно у закрытых статусов. Допустимые статусы задаёт ck_subscriptions_status: pending, active, grace, expired, closed_duplicate. В коде повторно открыть закрытый абонемент тоже нельзя: apply_payment для закрытого абонемента не меняет статус, а публикует требование возврата.

- Реализация: [`services/subscriptions/service.py::apply_payment:364-371`](../../services/subscriptions/service.py#L364)
- БД: `trg_subscriptions_terminal_guard`, `subscriptions_terminal_guard`, `ck_subscriptions_closed`, `ck_subscriptions_status`
- Настройки: `services/subscriptions/service.py::CLOSED`
- Тесты: `tests/test_subscriptions_activation.py::test_closed_subscription_cannot_be_reopened`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-REFUND-01

## R-SUBSCRIPTIONS-STATUS-02 — У действующего абонемента всегда есть paid_until

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

CHECK ck_subscriptions_paid_until требует, чтобы paid_until был заполнен у абонементов в статусах active и grace (может быть пустым только у pending, expired, closed_duplicate). Код заполняет paid_until при активации в apply_payment.

- Реализация: [`services/subscriptions/service.py::apply_payment:375-377`](../../services/subscriptions/service.py#L375)
- БД: `ck_subscriptions_paid_until`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-ACTIVATE-01

## R-SUBSCRIPTIONS-STATUS-03 — Журнал смены статусов абонемента пишет триггер БД

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Триггер trg_subscriptions_log_status (функция subscriptions_log_status) после изменения статуса абонемента добавляет в subscriptions.status_history запись со старым и новым статусом. Код журнал не пишет, только читает (модель StatusChange).

- Реализация: [`services/subscriptions/models.py::StatusChange:88-98`](../../services/subscriptions/models.py#L88)
- БД: `trg_subscriptions_log_status`, `subscriptions_log_status`
- Тесты: `tests/test_subscriptions_activation.py::test_status_changes_are_logged`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-STATUS-01

## R-SUBSCRIPTIONS-NOTICE-01 — События абонемента превращаются в уведомления держателю

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 3 тестами

Подписчики модуля на каждое из событий invoice_issued, activated, renewed, grace_started, holder_rejected, closed_duplicate, expired и refund_required создают запись в subscriptions.notices с соответствующим видом (invoice, activated, renewed, grace, holder_rejected, closed_duplicate, expired, refund). Рассылает уведомления отдельный воркер вне модуля.

- Реализация: [`services/subscriptions/service.py::add_notice:395-398`](../../services/subscriptions/service.py#L395), [`services/subscriptions/consumers.py::on_invoice_issued:30-36`](../../services/subscriptions/consumers.py#L30), [`services/subscriptions/consumers.py::on_activated:45-48`](../../services/subscriptions/consumers.py#L45), [`services/subscriptions/consumers.py::on_renewed:52-55`](../../services/subscriptions/consumers.py#L52), [`services/subscriptions/consumers.py::on_grace_started:70-76`](../../services/subscriptions/consumers.py#L70), [`services/subscriptions/consumers.py::on_holder_rejected:20-26`](../../services/subscriptions/consumers.py#L20)
- Тесты: `tests/test_subscriptions_lifecycle.py::test_unpaid_month_moves_to_grace`, `tests/test_subscriptions_lifecycle.py::test_paying_renewal_extends_subscription`, `tests/test_subscriptions_holder.py::test_holder_without_passport_is_rejected`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-REMIND-01

## R-SUBSCRIPTIONS-REMIND-01 — Напоминание перед концом льготного периода не реализовано

`draft` · config

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, ссылок на код нет — не опирайся без проверки

В настройках есть GRACE_REMINDER_DAYS = 5 (напомнить об оплате за 5 дней до конца льготного периода), а в таблице абонементов — колонка reminded_for. Ни одна задача и ни одна функция модуля их не использует: держатель получает только уведомление о начале grace и о закрытии.

- Роли: Система (события и фоновые задачи)
- Связанные: R-SUBSCRIPTIONS-GRACE-01, R-SUBSCRIPTIONS-NOTICE-01

## R-SUBSCRIPTIONS-API-01 — API абонементов не проверяет роль и личность вызывающего

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Маршруты модуля (GET /plans, POST /subscriptions, GET /subscriptions/{id}, GET /clients/{client_ref}/subscriptions, PUT /subscriptions/{id}/holder, POST /invoices/{id}/payments) зависят только от сессии БД (libs/web.py::session). Проверки ролей нет: любой вызывающий может просмотреть абонементы любого клиента и провести платёж по любому счёту. Владельца проверяет только update_holder — по client_ref из тела запроса.

- Реализация: [`services/subscriptions/api.py::by_client:92-93`](../../services/subscriptions/api.py#L92), [`services/subscriptions/api.py::pay:103-105`](../../services/subscriptions/api.py#L103), [`services/subscriptions/api.py::update_holder:97-99`](../../services/subscriptions/api.py#L97)
- Тесты: `tests/test_subscriptions_api.py::test_subscribe_and_pay_over_api`, `tests/test_subscriptions_api.py::test_api_maps_domain_errors`
- Роли: Клиент
- Связанные: R-SUBSCRIPTIONS-HOLDER-04
