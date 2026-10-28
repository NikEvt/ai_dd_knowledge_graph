<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: halls

Источник: [`knowledge/rules/halls.yaml`](../../knowledge/rules/halls.yaml)

## R-HALLS-ACCESS-01 — Залами, бронями и шаблонами управляет только менеджер, закреплённый за площадкой

`draft` · permission

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Перед созданием зала, его выводом из аренды, бронированием, сменой площадки, отменой брони и сохранением шаблона письма код проверяет, что менеджер есть в halls.hall_managers для площадки. Если его там нет, код отклоняет действие с AccessDenied «менеджер не закреплён за площадкой». При смене площадки проверяется менеджер текущей площадки брони, а менеджер новой площадки не проверяется. Отдельной роли из общей ролевой модели у менеджера нет: доступ даёт только запись в hall_managers.

- Реализация: [`services/halls/service.py::_require_manager:27-29`](../../services/halls/service.py#L27), [`services/halls/service.py::create_hall:58-58`](../../services/halls/service.py#L58), [`services/halls/service.py::deactivate_hall:73-73`](../../services/halls/service.py#L73), [`services/halls/service.py::create_booking:154-154`](../../services/halls/service.py#L154), [`services/halls/service.py::change_venue:196-196`](../../services/halls/service.py#L196), [`services/halls/service.py::cancel_booking:237-237`](../../services/halls/service.py#L237), [`services/halls/service.py::set_template:402-402`](../../services/halls/service.py#L402)
- Тесты: `tests/test_halls_booking.py::test_manager_of_other_venue_cannot_book`, `tests/test_halls_booking.py::test_change_venue_requires_manager_of_current_venue`
- Связанные: R-HALLS-VENUE-CHANGE-01

## R-HALLS-ACCESS-02 — Права на внесение платежа по счёту зала не проверяются

`draft` · permission

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

record_payment не проверяет ни роль, ни закрепление за площадкой. Идентификатор recorded_by из запроса только сохраняется в halls.hall_payments. Внести платёж через POST /invoices/{invoice_id}/payments может любой вызывающий.

- Реализация: [`services/halls/service.py::record_payment:352-358`](../../services/halls/service.py#L352), [`services/halls/api.py::record_payment:129-131`](../../services/halls/api.py#L129)
- Связанные: R-HALLS-PAYMENT-01

## R-HALLS-HALL-01 — Название зала обязательно и уникально в пределах площадки

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

При создании зала название обрезается по краям. Пустое название отклоняется («у зала должно быть название»), повтор на той же площадке тоже («на площадке уже есть зал …»). Уникальность дублирует ограничение UNIQUE (venue_id, name).

- Реализация: [`services/halls/service.py::create_hall:59-64`](../../services/halls/service.py#L59)
- БД: `halls_venue_id_name_key`
- Связанные: R-HALLS-HALL-02

## R-HALLS-HALL-02 — Вместимость и почасовая ставка зала положительны — только на уровне БД

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

create_hall не проверяет capacity и hourly_rate. Нулевые и отрицательные значения отклоняет только БД через CHECK capacity > 0 и hourly_rate > 0, и пользователь получает ошибку БД, а не доменную.

- БД: `halls_capacity_check`, `halls_hourly_rate_check`
- Связанные: R-HALLS-HALL-01, R-HALLS-INVOICE-01

## R-HALLS-HALL-03 — Зал нельзя вывести из аренды, пока в нём есть предстоящие брони

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

deactivate_hall отклоняет вывод зала из аренды, если в нём есть бронь в статусе из ACTIVE_STATUSES (draft, prepaid, confirmed) с ends_at позже текущего момента: «в зале есть предстоящие брони — сначала перенесите или отмените их». Иначе ставит active = false.

- Реализация: [`services/halls/service.py::deactivate_hall:74-83`](../../services/halls/service.py#L74)
- Настройки: `services/halls/settings.py::ACTIVE_STATUSES`
- Тесты: `tests/test_halls_booking.py::test_deactivate_hall_with_upcoming_bookings_rejected`
- Связанные: R-HALLS-HALL-04

## R-HALLS-HALL-04 — Неактивный зал не показывается в списке и не бронируется

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

В списке залов площадки (GET /venues/{venue_id}/halls) только залы с active = true. При бронировании и при переносе брони неактивный зал отклоняется: «зал … не сдаётся».

- Реализация: [`services/halls/service.py::venue_halls:88-90`](../../services/halls/service.py#L88), [`services/halls/service.py::_check_fits:131-132`](../../services/halls/service.py#L131)
- Тесты: `tests/test_halls_booking.py::test_deactivate_hall_with_upcoming_bookings_rejected`
- Связанные: R-HALLS-HALL-03, R-HALLS-VENUE-CHANGE-01

## R-HALLS-BOOKING-01 — Вид мероприятия — из фиксированного списка

`draft` · config

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Бронь принимается только для вида мероприятия из EVENT_KINDS (ключи TEMPLATE_GROUP: wedding, birthday, party, corporate, conference), иначе «неизвестный вид мероприятия». Список дублируется CHECK на event_kind в БД. Новый вид нужно добавить в обоих местах.

- Реализация: [`services/halls/service.py::create_booking:155-156`](../../services/halls/service.py#L155)
- БД: `hall_bookings_event_kind_check`
- Настройки: `services/halls/settings.py::EVENT_KINDS`, `services/halls/settings.py::TEMPLATE_GROUP`
- Связанные: R-HALLS-EMAIL-01

## R-HALLS-BOOKING-02 — Число гостей положительно и не больше вместимости зала

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

При бронировании число гостей должно быть больше нуля («число гостей должно быть положительным») и не больше capacity зала («зал … вмещает не больше N гостей»). Вместимость проверяется и при переносе брони в другой зал. Положительность дублирует CHECK guests > 0.

- Реализация: [`services/halls/service.py::create_booking:157-159`](../../services/halls/service.py#L157), [`services/halls/service.py::_check_fits:133-134`](../../services/halls/service.py#L133)
- БД: `hall_bookings_guests_check`
- Тесты: `tests/test_halls_booking.py::test_guests_over_capacity_rejected`
- Связанные: R-HALLS-VENUE-CHANGE-01

## R-HALLS-BOOKING-03 — Зал бронируется не позже чем за 2 дня и не дальше чем на 365 дней вперёд

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

От текущего момента до начала мероприятия должно быть не меньше MIN_LEAD_DAYS (2) дней и не больше BOOKING_HORIZON_DAYS (365) дней. Проверка идёт только при создании брони, при смене площадки сроки не перепроверяются.

- Реализация: [`services/halls/service.py::_check_period:98-102`](../../services/halls/service.py#L98)
- Настройки: `services/halls/settings.py::MIN_LEAD_DAYS`, `services/halls/settings.py::BOOKING_HORIZON_DAYS`
- Тесты: `tests/test_halls_booking.py::test_booking_period_rules`
- Связанные: R-HALLS-BOOKING-04, R-HALLS-VENUE-CHANGE-01

## R-HALLS-BOOKING-04 — Аренда длится от 2 до 12 часов

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Длительность брони (ends_at − starts_at) должна быть не меньше MIN_DURATION_HOURS (2) и не больше MAX_DURATION_HOURS (12) часов. БД дополнительно требует ends_at > starts_at.

- Реализация: [`services/halls/service.py::_check_period:103-107`](../../services/halls/service.py#L103)
- БД: `hall_bookings_check`
- Настройки: `services/halls/settings.py::MIN_DURATION_HOURS`, `services/halls/settings.py::MAX_DURATION_HOURS`
- Тесты: `tests/test_halls_booking.py::test_booking_period_rules`
- Связанные: R-HALLS-BOOKING-03, R-HALLS-INVOICE-01

## R-HALLS-BOOKING-05 — Брони одного зала не пересекаются с учётом часа на уборку

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Новая или перенесённая бронь отклоняется («зал … занят в это время»), если в зале есть бронь в статусе из ACTIVE_STATUSES (draft, prepaid, confirmed), чей интервал, расширенный на CLEANUP_MINUTES (60) с каждой стороны, пересекает новый. Отменённые и проведённые брони зал не занимают. В БД есть только частичный уникальный индекс (hall_id, starts_at) WHERE status <> 'cancelled': он ловит лишь совпадение времени начала, а пересечения и зазор на уборку проверяет только код.

- Реализация: [`services/halls/service.py::_check_hall_free:117-127`](../../services/halls/service.py#L117), [`services/halls/service.py::create_booking:161-161`](../../services/halls/service.py#L161), [`services/halls/service.py::change_venue:203-203`](../../services/halls/service.py#L203)
- БД: `hall_bookings_hall_start_uq`
- Настройки: `services/halls/settings.py::CLEANUP_MINUTES`, `services/halls/settings.py::ACTIVE_STATUSES`
- Тесты: `tests/test_halls_booking.py::test_overlapping_booking_rejected_with_cleanup_gap`, `tests/test_halls_booking.py::test_cancelled_booking_frees_hall`
- Связанные: R-HALLS-CANCEL-01, R-HALLS-VENUE-CHANGE-01

## R-HALLS-BOOKING-06 — Новая бронь создаётся черновиком, и на неё сразу выставляется счёт

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

create_booking создаёт бронь в статусе draft с created_at = текущий момент и публикует halls.booking_created (подписчиков нет). Затем сразу выставляет счёт на всю сумму аренды через issue_invoice.

- Реализация: [`services/halls/service.py::create_booking:163-187`](../../services/halls/service.py#L163)
- Тесты: `tests/test_halls_booking.py::test_booking_starts_as_draft_with_invoice`
- Связанные: R-HALLS-INVOICE-01, R-HALLS-INVOICE-04

## R-HALLS-BOOKING-07 — Ссылка на клиента в брони не может быть пустой — только на уровне БД

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

create_booking не проверяет client_ref. Пустую строку или строку из пробелов отклоняет только CHECK length(trim(client_ref)) > 0.

- БД: `hall_bookings_client_ref_check`

## R-HALLS-INVOICE-01 — Сумма счёта — почасовая ставка зала за фактические минуты аренды

`draft` · calculation

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Сумма счёта = hourly_rate × целые минуты аренды / 60, округлённая до копеек (CENT = 0.01, quantize с банковским округлением по умолчанию). Неполные часы оплачиваются поминутно, секунды отбрасываются. Скидок и надбавок нет.

- Реализация: [`services/halls/service.py::rent_amount:137-139`](../../services/halls/service.py#L137), [`services/halls/service.py::issue_invoice:280-285`](../../services/halls/service.py#L280)
- БД: `hall_invoices_amount_check`
- Настройки: `services/halls/service.py::CENT`
- Тесты: `tests/test_halls_booking.py::test_partial_hours_are_billed_by_minutes`
- Связанные: R-HALLS-BOOKING-06, R-HALLS-VENUE-CHANGE-03

## R-HALLS-INVOICE-02 — У брони не больше одного действующего счёта

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Действующим считается счёт брони в статусе open или paid (любой, кроме void): так его ищет active_invoice. БД это гарантирует частичным уникальным индексом по booking_id WHERE status <> 'void'. Поэтому при перевыставлении старый счёт аннулируется (flush) до создания нового.

- Реализация: [`services/halls/service.py::active_invoice:262-265`](../../services/halls/service.py#L262), [`services/halls/service.py::reissue_invoice:301-306`](../../services/halls/service.py#L301)
- БД: `hall_invoices_booking_active_uq`
- Тесты: `tests/test_halls_booking.py::test_change_venue_moves_booking_and_reissues_invoice`
- Связанные: R-HALLS-VENUE-CHANGE-03

## R-HALLS-INVOICE-03 — Закрытый счёт (paid/void) всегда имеет дату закрытия

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Статус счёта — open, paid или void. По CHECK closed_at пуст тогда и только тогда, когда счёт open. Код проставляет closed_at в трёх местах: при полной оплате, при аннулировании по отмене брони и при перевыставлении.

- Реализация: [`services/halls/service.py::record_payment:361-363`](../../services/halls/service.py#L361), [`services/halls/service.py::void_invoice:322-324`](../../services/halls/service.py#L322), [`services/halls/service.py::reissue_invoice:303-304`](../../services/halls/service.py#L303)
- БД: `hall_invoices_check`, `hall_invoices_status_check`
- Связанные: R-HALLS-PAYMENT-04, R-HALLS-CANCEL-02, R-HALLS-VENUE-CHANGE-03

## R-HALLS-INVOICE-04 — При выставлении счёта клиенту уходит письмо со счётом

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

issue_invoice публикует halls.invoice_issued с суммой. Подписчик on_invoice_issued записывает письмо типа invoice по шаблону площадки с подстановкой amount. Это касается и перевыставления при смене площадки, так что клиент получает второе письмо со счётом.

- Реализация: [`services/halls/service.py::issue_invoice:288-292`](../../services/halls/service.py#L288), [`services/halls/consumers.py::on_invoice_issued:10-11`](../../services/halls/consumers.py#L10)
- Тесты: `tests/test_halls_booking.py::test_change_venue_moves_booking_and_reissues_invoice`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-EMAIL-01, R-HALLS-VENUE-CHANGE-03

## R-HALLS-PAYMENT-01 — Платёж принимается только на открытый счёт неотменённой брони

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

record_payment отклоняет платёж на счёт не в статусе open («счёт закрыт, платёж принять нельзя») и на счёт отменённой брони («бронь отменена, платёж принять нельзя»). Проверку открытого счёта дублирует BEFORE INSERT триггер на hall_payments. Проверку отменённой брони делает только код.

- Реализация: [`services/halls/service.py::record_payment:337-341`](../../services/halls/service.py#L337)
- БД: `trg_hall_payments_open_invoice`, `forbid_payment_on_closed_invoice`
- Тесты: `tests/test_halls_payments.py::test_payment_to_void_invoice_rejected_in_service_and_db`, `tests/test_halls_cancel.py::test_cancelled_and_held_bookings_cannot_be_cancelled_or_paid`
- Связанные: R-HALLS-CANCEL-02, R-HALLS-ACCESS-02

## R-HALLS-PAYMENT-02 — Сумма платежа положительна и не больше остатка по счёту

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Платёж с суммой ≤ 0 отклоняется («сумма платежа должна быть положительной»), как и платёж больше остатка: сумма счёта минус уже внесённое («сумма больше остатка по счёту»). Переплатить одним платежом нельзя. Положительность дублирует CHECK amount > 0.

- Реализация: [`services/halls/service.py::record_payment:342-350`](../../services/halls/service.py#L342)
- БД: `hall_payments_amount_check`
- Тесты: `tests/test_halls_payments.py::test_payment_over_rest_rejected`
- Связанные: R-HALLS-PAYMENT-01

## R-HALLS-PAYMENT-03 — Банковская ссылка платежа учитывается один раз

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Если у платежа указан external_ref и платёж с такой ссылкой уже есть, record_payment отклоняет его («платёж … уже учтён»). Уникальность дублирует частичный уникальный индекс WHERE external_ref IS NOT NULL. Платежи без ссылки не дедуплицируются.

- Реализация: [`services/halls/service.py::record_payment:344-347`](../../services/halls/service.py#L344)
- БД: `hall_payments_external_ref_uq`
- Тесты: `tests/test_halls_payments.py::test_duplicate_bank_reference_rejected`

## R-HALLS-PAYMENT-04 — Полная оплата закрывает счёт, любой платёж пересчитывает статус брони

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

После записи платежа счёт, оплаченный полностью, получает статус paid и closed_at. В любом случае публикуется halls.payment_received. Его подписчик on_payment_received вызывает apply_payments и пересчитывает статус брони.

- Реализация: [`services/halls/service.py::record_payment:359-368`](../../services/halls/service.py#L359), [`services/halls/consumers.py::on_payment_received:15-16`](../../services/halls/consumers.py#L15)
- Тесты: `tests/test_halls_payments.py::test_full_payment_confirms_booking_in_one_step`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-STATUS-01, R-HALLS-STATUS-02

## R-HALLS-STATUS-01 — Полностью оплаченная бронь подтверждается, клиенту уходит письмо

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

apply_payments переводит бронь в статусе draft или prepaid в confirmed, если внесённое покрывает действующий счёт, ставит confirmed_at и публикует halls.booking_confirmed. Подписчик записывает письмо типа confirmed. Полная оплата черновика подтверждает его сразу, минуя prepaid и письмо о предоплате. CHECK требует confirmed_at для статусов confirmed и held.

- Реализация: [`services/halls/service.py::apply_payments:375-385`](../../services/halls/service.py#L375), [`services/halls/consumers.py::on_booking_confirmed:25-26`](../../services/halls/consumers.py#L25)
- БД: `hall_bookings_check2`
- Тесты: `tests/test_halls_payments.py::test_full_payment_confirms_booking_in_one_step`, `tests/test_halls_booking.py::test_status_history_written_by_trigger`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-STATUS-02, R-HALLS-PAYMENT-04

## R-HALLS-STATUS-02 — Оплата половины счёта делает черновик предоплаченным

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Если внесено не меньше PREPAY_SHARE (0.5) суммы действующего счёта, но не всё, apply_payments переводит бронь из draft в prepaid и публикует halls.booking_prepaid с внесённой суммой. Подписчик записывает письмо типа prepaid. Повторные частичные платежи по предоплаченной брони статус не меняют и писем не дают.

- Реализация: [`services/halls/service.py::apply_payments:386-389`](../../services/halls/service.py#L386), [`services/halls/consumers.py::on_booking_prepaid:20-21`](../../services/halls/consumers.py#L20)
- Настройки: `services/halls/settings.py::PREPAY_SHARE`
- Тесты: `tests/test_halls_payments.py::test_half_payment_makes_booking_prepaid`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-STATUS-01, R-HALLS-STATUS-03, R-HALLS-TIMER-01

## R-HALLS-STATUS-03 — Предоплаченная бронь возвращается в черновик, если после перевыставления не хватает предоплаты

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Если по действующему счёту внесено меньше PREPAY_SHARE его суммы (например, после переноса в более дорогой зал), apply_payments молча возвращает бронь из prepaid в draft: без события и без письма клиенту. created_at не меняется. Поэтому задача cancel_unpaid может сразу отменить такую бронь, если с её создания прошло больше UNPAID_CANCEL_DAYS.

- Реализация: [`services/halls/service.py::apply_payments:390-392`](../../services/halls/service.py#L390)
- Настройки: `services/halls/settings.py::PREPAY_SHARE`
- Тесты: `tests/test_halls_booking.py::test_change_venue_to_pricier_hall_can_drop_prepaid`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-VENUE-CHANGE-03, R-HALLS-TIMER-01

## R-HALLS-STATUS-04 — Статусы брони и согласованность дат отмены и подтверждения

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Статус брони — draft, prepaid, confirmed, held или cancelled (CHECK). По CHECK cancelled_at задан тогда и только тогда, когда статус cancelled. Для confirmed и held обязателен confirmed_at. Код ставит эти поля вместе со статусом: в _cancel и в apply_payments.

- Реализация: [`services/halls/service.py::_cancel:218-220`](../../services/halls/service.py#L218), [`services/halls/service.py::apply_payments:383-384`](../../services/halls/service.py#L383)
- БД: `hall_bookings_status_check`, `hall_bookings_check1`, `hall_bookings_check2`
- Связанные: R-HALLS-STATUS-01, R-HALLS-CANCEL-01

## R-HALLS-STATUS-05 — История статусов брони пишется триггером БД

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено ограничением БД и 1 тестом

AFTER INSERT OR UPDATE OF status на hall_bookings добавляет строку в halls.hall_booking_history: при создании (NULL → статус) и при каждой реальной смене статуса (старый → новый). В коде записи истории нет: модель BookingHistory только читает таблицу.

- БД: `trg_hall_bookings_history`, `log_status_change`
- Тесты: `tests/test_halls_booking.py::test_status_history_written_by_trigger`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-STATUS-04

## R-HALLS-VENUE-CHANGE-01 — Бронь переносится на другую площадку только до подтверждения

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 4 тестами

change_venue разрешён только для броней в статусе draft или prepaid («площадку можно сменить только до подтверждения брони»). Новый зал должен быть на другой площадке («зал находится на той же площадке»), сдаваться, вмещать гостей и быть свободным в то же время. Время брони не меняется, сроки MIN_LEAD_DAYS и BOOKING_HORIZON_DAYS не перепроверяются. Перенос в другой зал той же площадки не поддерживается.

- Реализация: [`services/halls/service.py::change_venue:195-213`](../../services/halls/service.py#L195)
- БД: `trg_hall_bookings_venue_lock`
- Тесты: `tests/test_halls_booking.py::test_change_venue_after_confirmation_forbidden`, `tests/test_halls_booking.py::test_change_venue_within_same_venue_rejected`, `tests/test_halls_booking.py::test_change_venue_requires_manager_of_current_venue`, `tests/test_halls_booking.py::test_change_venue_moves_booking_and_reissues_invoice`
- Связанные: R-HALLS-VENUE-CHANGE-02, R-HALLS-VENUE-CHANGE-03, R-HALLS-ACCESS-01, R-HALLS-BOOKING-05

## R-HALLS-VENUE-CHANGE-02 — Триггер БД запрещает менять площадку подтверждённой или проведённой брони

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено ограничением БД и 1 тестом

BEFORE UPDATE OF venue_id на hall_bookings выбрасывает check_violation («бронь … подтверждена, площадку сменить нельзя»), если старый статус confirmed или held и venue_id меняется. Триггер дублирует проверку в change_venue. Смену hall_id внутри той же площадки он не ловит.

- БД: `trg_hall_bookings_venue_lock`, `halls.forbid_venue_change`
- Тесты: `tests/test_halls_booking.py::test_venue_lock_trigger_protects_confirmed_booking`
- Связанные: R-HALLS-VENUE-CHANGE-01

## R-HALLS-VENUE-CHANGE-03 — Смена площадки перевыставляет счёт по ставке нового зала с переносом платежей

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

На halls.venue_changed подписчик вызывает reissue_invoice (только для draft и prepaid). Код аннулирует действующий счёт и выставляет новый по ставке нового зала, после чего уходит письмо со счётом. Все платежи старого счёта перепривязываются к новому. Если их хватает на новую сумму, счёт сразу закрывается как paid. Затем публикуется halls.payment_received, и apply_payments пересчитывает статус: бронь может стать confirmed, остаться prepaid или откатиться в draft. Если внесено больше суммы нового (более дешёвого) счёта, переплата не возвращается.

- Реализация: [`services/halls/consumers.py::on_venue_changed:30-31`](../../services/halls/consumers.py#L30), [`services/halls/service.py::reissue_invoice:298-316`](../../services/halls/service.py#L298)
- БД: `hall_invoices_booking_active_uq`
- Тесты: `tests/test_halls_booking.py::test_change_venue_moves_booking_and_reissues_invoice`, `tests/test_halls_booking.py::test_change_venue_keeps_prepayment`, `tests/test_halls_booking.py::test_change_venue_to_pricier_hall_can_drop_prepaid`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-VENUE-CHANGE-01, R-HALLS-STATUS-03, R-HALLS-INVOICE-02, R-HALLS-INVOICE-04

## R-HALLS-CANCEL-01 — Отменить можно любую бронь, кроме уже отменённой и проведённой

`draft` · guard

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

cancel_booking отклоняет повторную отмену («бронь уже отменена») и отмену проведённого мероприятия («мероприятие уже прошло»). Отменить можно бронь в статусе draft, prepaid и даже confirmed (полностью оплаченную). Отмена ставит cancelled, cancelled_at и cancel_reason (по умолчанию client_request) и публикует halls.booking_cancelled. Отменённая бронь освобождает зал.

- Реализация: [`services/halls/service.py::cancel_booking:236-242`](../../services/halls/service.py#L236), [`services/halls/service.py::_cancel:218-230`](../../services/halls/service.py#L218)
- БД: `hall_bookings_check1`
- Тесты: `tests/test_halls_cancel.py::test_cancelled_and_held_bookings_cannot_be_cancelled_or_paid`, `tests/test_halls_booking.py::test_cancelled_booking_frees_hall`
- Связанные: R-HALLS-CANCEL-02, R-HALLS-BOOKING-05

## R-HALLS-CANCEL-02 — Отмена брони аннулирует открытый счёт и отправляет письмо об отмене

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

На halls.booking_cancelled подписчик аннулирует действующий счёт, если тот open, и записывает письмо типа cancel с причиной отмены. Счёт со статусом paid (отмена подтверждённой брони) остаётся paid. Платежи по аннулированному или оплаченному счёту не возвращаются: возврата в модуле нет.

- Реализация: [`services/halls/consumers.py::on_booking_cancelled:35-37`](../../services/halls/consumers.py#L35), [`services/halls/service.py::void_invoice:321-324`](../../services/halls/service.py#L321)
- Тесты: `tests/test_halls_cancel.py::test_cancel_sends_letter_from_event_group_template`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-CANCEL-01, R-HALLS-EMAIL-01

## R-HALLS-TIMER-01 — Черновик без предоплаты автоматически отменяется через 30 дней после создания

`draft` · timer

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Задача cancel_unpaid отменяет с причиной unpaid брони в статусе draft, у которых created_at ≤ now − UNPAID_CANCEL_DAYS (30). Строки берутся с блокировкой FOR UPDATE SKIP LOCKED. Срок отсчитывается от создания брони, а не от даты мероприятия: если мероприятие ближе 30 дней, неоплаченный черновик доживёт до него и останется draft. Предоплаченные (prepaid) брони задача не трогает.

- Реализация: [`services/halls/jobs.py::cancel_unpaid:12-24`](../../services/halls/jobs.py#L12), [`services/halls/service.py::cancel_unpaid:246-247`](../../services/halls/service.py#L246)
- Настройки: `services/halls/settings.py::UNPAID_CANCEL_DAYS`
- Тесты: `tests/test_halls_cancel.py::test_unpaid_booking_cancelled_after_thirty_days`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-CANCEL-02, R-HALLS-STATUS-03

## R-HALLS-TIMER-02 — Подтверждённая бронь после окончания мероприятия становится проведённой

`draft` · timer

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Задача close_past_events переводит брони в статусе confirmed с ends_at ≤ now в held и публикует halls.booking_held (подписчиков нет). Брони draft и prepaid с прошедшей датой не закрываются и не отменяются. prepaid-бронь не трогает ни эта задача, ни cancel_unpaid.

- Реализация: [`services/halls/jobs.py::close_past_events:30-38`](../../services/halls/jobs.py#L30), [`services/halls/service.py::mark_held:250-256`](../../services/halls/service.py#L250)
- БД: `hall_bookings_check2`
- Тесты: `tests/test_halls_cancel.py::test_close_past_events_skips_unconfirmed`, `tests/test_halls_cancel.py::test_cancelled_and_held_bookings_cannot_be_cancelled_or_paid`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-TIMER-01, R-HALLS-CANCEL-01

## R-HALLS-EMAIL-01 — Письмо клиенту берётся из шаблона площадки по группе вида мероприятия

`draft` · effect

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

send_email ищет шаблон по площадке брони, группе вида мероприятия (TEMPLATE_GROUP: wedding, birthday, party → private; corporate, conference → corporate) и типу письма (invoice, prepaid, confirmed, cancel). В шаблон подставляются hall, starts_at, guests и доп. поля. Если шаблона нет, письмо всё равно записывается со статусом no_template и пустым телом, без ошибки.

- Реализация: [`services/halls/service.py::find_template:424-430`](../../services/halls/service.py#L424), [`services/halls/service.py::send_email:436-455`](../../services/halls/service.py#L436)
- БД: `hall_emails_status_check`
- Настройки: `services/halls/settings.py::TEMPLATE_GROUP`
- Тесты: `tests/test_halls_cancel.py::test_cancel_sends_letter_from_event_group_template`, `tests/test_halls_cancel.py::test_venue_without_templates_records_unsent_letter`
- Роли: Система (события и фоновые задачи)
- Связанные: R-HALLS-EMAIL-02, R-HALLS-INVOICE-04, R-HALLS-CANCEL-02

## R-HALLS-EMAIL-02 — Шаблон письма — один на площадку, группу и тип

`draft` · config

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

set_template (менеджер площадки) проверяет, что группа шаблона есть среди значений TEMPLATE_GROUP («неизвестная группа шаблонов»). Дальше он обновляет тело существующего шаблона для пары (площадка, группа, тип) или создаёт новый. Тип письма код не проверяет: недопустимый тип отклоняет только CHECK в БД. Уникальность тройки обеспечивает UNIQUE (venue_id, kind_group, type).

- Реализация: [`services/halls/service.py::set_template:403-417`](../../services/halls/service.py#L403)
- БД: `hall_templates_kind_group_check`, `hall_templates_type_check`, `hall_templates_venue_id_kind_group_type_key`
- Настройки: `services/halls/settings.py::TEMPLATE_GROUP`
- Связанные: R-HALLS-EMAIL-01, R-HALLS-ACCESS-01
