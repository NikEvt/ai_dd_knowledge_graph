<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: inventory

Источник: [`knowledge/rules/inventory.yaml`](../../knowledge/rules/inventory.yaml)

## R-INVENTORY-CUSTODIAN-01 — Операции с фондом площадки выполняет только её хранитель

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: В общей схеме роли «хранитель фонда» нет: в модели ролей проекта (operator, admin и т.д.) её тоже нет. Полномочия держа…

Регистрация экземпляра, выдача и продление по МБА, приём возврата, утеря, порча, списание по ветхости и исправление места хранения доступны только сотруднику, записанному хранителем фонда нужной площадки (inventory.custodians). Иначе AccessDenied «сотрудник не является хранителем фонда этой площадки». Для операций с экземпляром проверяется площадка, на которой он числится сейчас.

- Реализация: [`services/inventory/service.py::_require_custodian:39-41`](../../services/inventory/service.py#L39), [`services/inventory/service.py::register_copy:78-78`](../../services/inventory/service.py#L78), [`services/inventory/service.py::_out_loan:324-325`](../../services/inventory/service.py#L324), [`services/inventory/service.py::_on_shelf:381-382`](../../services/inventory/service.py#L381), [`services/inventory/service.py::issue_ill:280-281`](../../services/inventory/service.py#L280)
- Тесты: `tests/test_inventory_copies.py::test_worn_out_write_off_by_custodian_only`
- Связанные: R-INVENTORY-TRANSFER-06, R-INVENTORY-RECONCILE-01
- ⚠ Оговорка: В общей схеме роли «хранитель фонда» нет: в модели ролей проекта (operator, admin и т.д.) её тоже нет. Полномочия держатся только на таблице inventory.custodians, а employee_id приходит в теле запроса (custodian_id) и не сверяется с аутентифицированным пользователем.

## R-INVENTORY-COPY-01 — Инвентарный номер нормализуется и должен иметь вид «ШИФР-00000»

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: Формат номера проверяет только код. CHECK на inventory.copies.inventory_no нет, поэтому прямая запись в БД может сохран…

При регистрации экземпляра инвентарный номер обрезается от пробелов и переводится в верхний регистр, затем сверяется с шаблоном INVENTORY_NO: 1–4 буквы (кириллица или латиница), дефис, 4–8 цифр. Если номер не подходит — DomainError «инвентарный номер должен иметь вид «ШИФР-00000»».

- Реализация: [`services/inventory/service.py::register_copy:79-81`](../../services/inventory/service.py#L79)
- Настройки: `services/inventory/service.py::INVENTORY_NO`
- Тесты: `tests/test_inventory_copies.py::test_inventory_number_is_normalized_and_unique`
- Связанные: R-INVENTORY-COPY-02
- ⚠ Оговорка: Формат номера проверяет только код. CHECK на inventory.copies.inventory_no нет, поэтому прямая запись в БД может сохранить номер в любом формате.

## R-INVENTORY-COPY-02 — Инвентарный номер уникален во всём фонде

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Инвентарный номер не может повторяться ни на одной площадке. Код проверяет номер после нормализации и бросает DomainError «инвентарный номер … уже занят». В БД то же самое обеспечивает уникальный ключ copies_inventory_no_key.

- Реализация: [`services/inventory/service.py::register_copy:82-83`](../../services/inventory/service.py#L82)
- БД: `copies_inventory_no_key`
- Тесты: `tests/test_inventory_copies.py::test_inventory_number_is_normalized_and_unique`
- Связанные: R-INVENTORY-COPY-01

## R-INVENTORY-COPY-03 — Новый экземпляр поступает в фонд доступным и пересчитывает остаток

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: В срезе графа у inventory.copy_registered и других событий остатка не указан публикатор: их публикует _stock_event(topi…

Зарегистрированный экземпляр получает состояние available на площадке хранителя, acquired_at равен текущему моменту. Публикуется inventory.copy_registered, и подписчик on_stock_changed пересчитывает остаток издания на площадке.

- Реализация: [`services/inventory/service.py::register_copy:84-95`](../../services/inventory/service.py#L84), [`services/inventory/consumers.py::on_stock_changed:18-20`](../../services/inventory/consumers.py#L18)
- Тесты: `tests/test_inventory_copies.py::test_registered_copies_counted_in_stock`
- Связанные: R-INVENTORY-STOCK-01
- ⚠ Оговорка: В срезе графа у inventory.copy_registered и других событий остатка не указан публикатор: их публикует _stock_event(topic=…), и экстрактор такой вызов не распознаёт.

## R-INVENTORY-COPY-04 — Состояние экземпляра ограничено фиксированным набором

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

В БД CHECK copies_state_check разрешает только перечисленные состояния: available, on_loan, in_transit, lost, damaged, written_off. Любое другое значение отклоняется на уровне БД.

- Реализация: [`services/inventory/service.py::_set_state:51-53`](../../services/inventory/service.py#L51)
- БД: `copies_state_check`
- Тесты: `tests/test_inventory_copies.py::test_state_is_constrained`
- Связанные: R-INVENTORY-WRITEOFF-03

## R-INVENTORY-STOCK-01 — Остаток издания считается по экземплярам, которые ещё числятся в фонде

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 4 тестами

recount_stock пересчитывает stock_levels для пары (издание, площадка). В total входят экземпляры в состояниях ON_BALANCE (available, on_loan, in_transit), в available — только available. Утерянные, испорченные и списанные экземпляры из остатка выпадают. Экземпляр в пути числится на площадке-отправителе, пока его не примут.

- Реализация: [`services/inventory/service.py::recount_stock:107-125`](../../services/inventory/service.py#L107)
- Настройки: `services/inventory/models.py::ON_BALANCE`
- Тесты: `tests/test_inventory_copies.py::test_registered_copies_counted_in_stock`, `tests/test_inventory_copies.py::test_lost_copy_is_written_off_and_leaves_stock`, `tests/test_inventory_transfers.py::test_transfer_moves_copy_and_stock`, `tests/test_inventory_ill.py::test_ill_loan_due_in_thirty_days`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-STOCK-02

## R-INVENTORY-STOCK-02 — Остаток пересчитывается асинхронно по событиям движения экземпляра

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами · оговорка: На inventory.copy_lost и inventory.copy_damaged on_stock_changed не подписан: остаток после утери или порчи пересчитыва…

on_stock_changed подписан на inventory.copy_registered, copy_relocated, copy_written_off, transfer_shipped, transfer_received, transfer_cancelled, ill_issued и ill_returned. Он пересчитывает остаток для каждой площадки из payload.venue_ids: при приёме перемещения и сверке это обе площадки. Остаток в stock_levels обновляется только после доставки событий, а не в транзакции операции.

- Реализация: [`services/inventory/consumers.py::on_stock_changed:10-20`](../../services/inventory/consumers.py#L10), [`services/inventory/service.py::_stock_event:56-59`](../../services/inventory/service.py#L56)
- Тесты: `tests/test_inventory_transfers.py::test_transfer_moves_copy_and_stock`, `tests/test_inventory_transfers.py::test_cancel_in_transit_returns_copy_to_shelf`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-STOCK-01
- ⚠ Оговорка: На inventory.copy_lost и inventory.copy_damaged on_stock_changed не подписан: остаток после утери или порчи пересчитывается только через последующее copy_written_off. Пока событие списания не обработано, total и available включают экземпляр в состоянии lost/damaged по старому значению.

## R-INVENTORY-STOCK-03 — Остатки в БД неотрицательны, и доступных не больше общего числа

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

CHECK на inventory.stock_levels требует total >= 0 (stock_levels_total_check), available >= 0 (stock_levels_available_check) и available <= total (stock_levels_check).

- Реализация: [`services/inventory/service.py::recount_stock:116-124`](../../services/inventory/service.py#L116)
- БД: `stock_levels_total_check`, `stock_levels_available_check`, `stock_levels_check`
- Связанные: R-INVENTORY-STOCK-01

## R-INVENTORY-RECONCILE-01 — Сверка переносит экземпляр на другую площадку без оформления перемещения

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом · оговорка: Код проверяет только хранителя площадки назначения, площадку-источник не проверяет: хранитель любой площадки может «заб…

reconcile_venue по итогам инвентаризации меняет venue_id экземпляра напрямую. Требуется хранитель площадки назначения; если по экземпляру есть открытое перемещение — DomainError «по экземпляру оформлено перемещение». Публикуется inventory.copy_relocated с обеими площадками для пересчёта остатков.

- Реализация: [`services/inventory/service.py::reconcile_venue:135-145`](../../services/inventory/service.py#L135)
- БД: `trg_copies_transfer_lock`
- Тесты: `tests/test_inventory_transfers.py::test_loaned_copy_cannot_change_venue_even_on_reconciliation`
- Связанные: R-INVENTORY-RECONCILE-02, R-INVENTORY-STOCK-02
- ⚠ Оговорка: Код проверяет только хранителя площадки назначения, площадку-источник не проверяет: хранитель любой площадки может «забрать» к себе экземпляр чужой. Состояние экземпляра код не проверяет, его блокирует только триггер БД. У функции нет HTTP-маршрута.

## R-INVENTORY-RECONCILE-02 — Выданный по МБА экземпляр не может сменить площадку (триггер БД)

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Триггер trg_copies_transfer_lock (функция forbid_transfer_of_loaned_copy) при изменении venue_id отклоняет обновление, если экземпляр в состоянии on_loan или по нему есть выдача МБА в статусе out. Ограничение срабатывает даже при сверке, где код его не проверяет.

- Реализация: [`services/inventory/service.py::reconcile_venue:141-144`](../../services/inventory/service.py#L141)
- БД: `trg_copies_transfer_lock`, `forbid_transfer_of_loaned_copy`
- Тесты: `tests/test_inventory_transfers.py::test_loaned_copy_cannot_change_venue_even_on_reconciliation`
- Связанные: R-INVENTORY-RECONCILE-01, R-INVENTORY-TRANSFER-02

## R-INVENTORY-TRANSFER-01 — Перемещение оформляет хранитель площадки, где лежит экземпляр, и только на другую площадку

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

request_transfer требует хранителя текущей площадки экземпляра. Площадка назначения должна отличаться от текущей, иначе «экземпляр уже находится на этой площадке». В БД это дублируют CHECK transfers_check (from_venue_id <> to_venue_id) и триггер trg_transfers_origin: from_venue_id обязан совпадать с текущей площадкой экземпляра.

- Реализация: [`services/inventory/service.py::request_transfer:155-158`](../../services/inventory/service.py#L155), [`services/inventory/service.py::request_transfer:175-185`](../../services/inventory/service.py#L175)
- БД: `transfers_check`, `trg_transfers_origin`, `check_transfer_origin`
- Тесты: `tests/test_inventory_transfers.py::test_transfer_must_start_where_copy_is`, `tests/test_inventory_transfers.py::test_transfer_moves_copy_and_stock`
- Связанные: R-INVENTORY-TRANSFER-02, R-INVENTORY-TRANSFER-03

## R-INVENTORY-TRANSFER-02 — Перемещать можно только доступный экземпляр

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Выданный экземпляр (on_loan) переместить нельзя: «экземпляр выдан, перемещение невозможно до возврата». Экземпляр в любом другом состоянии, кроме available, тоже: «перемещать можно только экземпляр, доступный на площадке».

- Реализация: [`services/inventory/service.py::request_transfer:159-162`](../../services/inventory/service.py#L159)
- Тесты: `tests/test_inventory_transfers.py::test_loaned_copy_cannot_be_transferred`
- Связанные: R-INVENTORY-RECONCILE-02

## R-INVENTORY-TRANSFER-03 — По экземпляру не больше одного незавершённого перемещения

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

Если у экземпляра есть перемещение в статусе requested или in_transit (OPEN_TRANSFER), новое не оформляется: «по экземпляру уже есть незавершённое перемещение». В БД это обеспечивает частичный уникальный индекс uq_transfers_one_open. После отмены или приёма можно оформить новое.

- Реализация: [`services/inventory/service.py::request_transfer:163-164`](../../services/inventory/service.py#L163), [`services/inventory/service.py::_open_transfer:62-65`](../../services/inventory/service.py#L62)
- БД: `uq_transfers_one_open`
- Настройки: `services/inventory/models.py::OPEN_TRANSFER`
- Тесты: `tests/test_inventory_transfers.py::test_one_open_transfer_per_copy`, `tests/test_inventory_transfers.py::test_cancel_in_transit_returns_copy_to_shelf`
- Связанные: R-INVENTORY-TRANSFER-01

## R-INVENTORY-TRANSFER-04 — На площадке должен остаться минимум экземпляров издания

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: Текст ошибки «хотя бы один» зашит в код и не меняется вместе с MIN_COPIES_ON_VENUE. Учитываются только уже оформленные …

Перед оформлением перемещения код считает другие доступные экземпляры того же издания на площадке. Если их меньше MIN_COPIES_ON_VENUE (1), отказ: «на площадке должен остаться хотя бы один экземпляр издания». Выданные и находящиеся в пути экземпляры в этот счёт не входят.

- Реализация: [`services/inventory/service.py::request_transfer:165-174`](../../services/inventory/service.py#L165)
- Настройки: `services/inventory/settings.py::MIN_COPIES_ON_VENUE`
- Тесты: `tests/test_inventory_transfers.py::test_last_copy_stays_on_venue`
- Связанные: R-INVENTORY-TRANSFER-02
- ⚠ Оговорка: Текст ошибки «хотя бы один» зашит в код и не меняется вместе с MIN_COPIES_ON_VENUE. Учитываются только уже оформленные перемещения: два одновременных запроса по разным экземплярам могут вместе вывести площадку ниже минимума (ограничения в БД нет).

## R-INVENTORY-TRANSFER-05 — Отправка переводит экземпляр в путь, приём переносит его на новую площадку

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

ship_transfer выполняет хранитель площадки-отправителя и только для перемещения в статусе requested с доступным экземпляром. Экземпляр переходит в in_transit, перемещение — в in_transit с shipped_at, публикуется inventory.transfer_shipped. receive_transfer выполняет хранитель площадки назначения и только из in_transit: экземпляр получает новую площадку и состояние available, перемещение — статус received с closed_at, публикуется inventory.transfer_received с обеими площадками.

- Реализация: [`services/inventory/service.py::ship_transfer:197-206`](../../services/inventory/service.py#L197), [`services/inventory/service.py::receive_transfer:212-227`](../../services/inventory/service.py#L212)
- БД: `transfers_check1`, `transfers_check2`, `transfers_status_check`
- Тесты: `tests/test_inventory_transfers.py::test_transfer_moves_copy_and_stock`
- Связанные: R-INVENTORY-TRANSFER-06, R-INVENTORY-TRANSFER-08

## R-INVENTORY-TRANSFER-06 — Отменить перемещение может хранитель любой из двух площадок или система

`draft` · permission

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

cancel_transfer с custodian_id требует, чтобы сотрудник был хранителем площадки-отправителя или площадки назначения, иначе AccessDenied «отменить перемещение может хранитель одной из площадок». custodian_id=None означает системную отмену (истёк срок), права тогда не проверяются. Завершённое перемещение отменить нельзя: «перемещение уже завершено».

- Реализация: [`services/inventory/service.py::cancel_transfer:236-244`](../../services/inventory/service.py#L236)
- Настройки: `services/inventory/models.py::OPEN_TRANSFER`
- Тесты: `tests/test_inventory_transfers.py::test_cancel_in_transit_returns_copy_to_shelf`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-TRANSFER-07, R-INVENTORY-TRANSFER-08

## R-INVENTORY-TRANSFER-07 — Отмена перемещения в пути возвращает экземпляр на полку отправителя

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

При отмене перемещения в статусе in_transit экземпляр снова становится available и остаётся на площадке-отправителе: venue_id не менялся. Перемещение получает статус cancelled, причину (по API — note или «cancelled») и closed_at, публикуется inventory.transfer_cancelled.

- Реализация: [`services/inventory/service.py::cancel_transfer:245-251`](../../services/inventory/service.py#L245), [`services/inventory/api.py::cancel_transfer:147-148`](../../services/inventory/api.py#L147)
- БД: `transfers_check2`
- Тесты: `tests/test_inventory_transfers.py::test_cancel_in_transit_returns_copy_to_shelf`
- Связанные: R-INVENTORY-TRANSFER-06

## R-INVENTORY-TRANSFER-08 — Неотправленная заявка на перемещение отменяется по истечении срока

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: В репозитории не найден планировщик, вызывающий jobs.py модуля inventory: задача запускается только из тестов. Для пере…

Фоновая задача expire_stale_transfers отменяет перемещения в статусе requested, у которых requested_at старше TRANSFER_REQUEST_TTL_DAYS (14 дней), с причиной «expired» от имени системы. Перемещения в пути задача не трогает.

- Реализация: [`services/inventory/jobs.py::expire_stale_transfers:50-61`](../../services/inventory/jobs.py#L50)
- Настройки: `services/inventory/settings.py::TRANSFER_REQUEST_TTL_DAYS`
- Тесты: `tests/test_inventory_transfers.py::test_stale_requests_expire`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-TRANSFER-06
- ⚠ Оговорка: В репозитории не найден планировщик, вызывающий jobs.py модуля inventory: задача запускается только из тестов. Для перемещений, застрявших в in_transit, таймера нет.

## R-INVENTORY-ILL-01 — Выдача по МБА только доступного экземпляра без открытого перемещения

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

issue_ill требует хранителя площадки экземпляра. Экземпляр должен быть available, иначе «экземпляр недоступен для выдачи», и без открытого перемещения, иначе «по экземпляру оформлено перемещение». В БД частичный уникальный индекс uq_ill_loans_one_out не допускает двух выдач в статусе out по одному экземпляру.

- Реализация: [`services/inventory/service.py::issue_ill:287-290`](../../services/inventory/service.py#L287)
- БД: `uq_ill_loans_one_out`
- Тесты: `tests/test_inventory_ill.py::test_ill_loan_due_in_thirty_days`
- Связанные: R-INVENTORY-ILL-02, R-INVENTORY-ILL-03

## R-INVENTORY-ILL-02 — Партнёр без новых выдач при приостановке, просрочке, лимите или долге

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

Библиотеке-партнёру не выдают экземпляр, если: выдачи ей приостановлены (suspended); у неё есть активная выдача с истёкшим due_at; число активных выдач уже достигло max_active_loans; сумма неоплаченных пеней (accruing и final) больше ILL_PARTNER_DEBT_LIMIT.

- Реализация: [`services/inventory/service.py::issue_ill:285-286`](../../services/inventory/service.py#L285), [`services/inventory/service.py::issue_ill:292-303`](../../services/inventory/service.py#L292), [`services/inventory/service.py::partner_debt:271-276`](../../services/inventory/service.py#L271)
- БД: `partner_libraries_max_active_loans_check`
- Настройки: `services/inventory/settings.py::ILL_PARTNER_DEBT_LIMIT`
- Тесты: `tests/test_inventory_ill.py::test_partner_with_overdue_loan_gets_nothing_new`, `tests/test_inventory_ill.py::test_active_loans_limit`, `tests/test_inventory_ill.py::test_loss_by_partner_charges_and_suspends`
- Связанные: R-INVENTORY-PARTNER-02, R-INVENTORY-PARTNER-03

## R-INVENTORY-ILL-03 — Срок выдачи по МБА — ILL_LOAN_PERIOD_DAYS от момента выдачи

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

При выдаче due_at = issued_at + ILL_LOAN_PERIOD_DAYS (30 дней), экземпляр переходит в on_loan, публикуется inventory.ill_issued, и остаток пересчитывается: экземпляр числится в total, но не в available. CHECK ill_loans_check требует due_at > issued_at.

- Реализация: [`services/inventory/service.py::issue_ill:305-316`](../../services/inventory/service.py#L305)
- БД: `ill_loans_check`, `ill_loans_status_check`
- Настройки: `services/inventory/settings.py::ILL_LOAN_PERIOD_DAYS`
- Тесты: `tests/test_inventory_ill.py::test_ill_loan_due_in_thirty_days`
- Связанные: R-INVENTORY-ILL-04

## R-INVENTORY-ILL-04 — Выдачу по МБА можно продлить ограниченное число раз и только до просрочки

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: Число продлений нигде не хранится: оно выводится из разницы due_at и issued_at. Поэтому смена ILL_LOAN_PERIOD_DAYS или …

renew_ill сдвигает due_at на ILL_RENEWAL_DAYS (14). Просроченную выдачу продлить нельзя: «просроченную выдачу продлить нельзя». Новый срок не может превышать issued_at + ILL_LOAN_PERIOD_DAYS + ILL_RENEWAL_DAYS × ILL_MAX_RENEWALS, иначе «выдача уже продлевалась». При настройках по умолчанию выдача продлевается один раз, до 44 дней.

- Реализация: [`services/inventory/service.py::renew_ill:333-341`](../../services/inventory/service.py#L333)
- Настройки: `services/inventory/settings.py::ILL_RENEWAL_DAYS`, `services/inventory/settings.py::ILL_MAX_RENEWALS`, `services/inventory/settings.py::ILL_LOAN_PERIOD_DAYS`
- Тесты: `tests/test_inventory_ill.py::test_renewal_only_once_and_not_when_overdue`
- Связанные: R-INVENTORY-ILL-03
- ⚠ Оговорка: Число продлений нигде не хранится: оно выводится из разницы due_at и issued_at. Поэтому смена ILL_LOAN_PERIOD_DAYS или ILL_RENEWAL_DAYS меняет лимит и для уже действующих выдач.

## R-INVENTORY-ILL-05 — Закрытую выдачу по МБА нельзя вернуть, продлить или объявить утерянной

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Возврат, продление и утеря по выдаче возможны только в статусе out, иначе «выдача уже закрыта». Права проверяются у хранителя текущей площадки экземпляра. CHECK ill_loans_check1 связывает статус returned с заполненным returned_at.

- Реализация: [`services/inventory/service.py::_out_loan:320-328`](../../services/inventory/service.py#L320)
- БД: `ill_loans_check1`, `ill_loans_status_check`
- Тесты: `tests/test_inventory_ill.py::test_timely_return_has_no_penalty`
- Связанные: R-INVENTORY-ILL-06, R-INVENTORY-ILL-07

## R-INVENTORY-ILL-06 — Возврат по МБА возвращает экземпляр на полку, испорченный — списывается

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

return_ill закрывает выдачу (status=returned, returned_at=now) и публикует inventory.ill_returned с due_at и returned_at. Экземпляр получает available, а при damaged=true — damaged, и дополнительно публикуется inventory.copy_damaged. Его подписчик on_copy_damaged оформляет акт списания с причиной damaged и ссылкой на выдачу.

- Реализация: [`services/inventory/service.py::return_ill:348-363`](../../services/inventory/service.py#L348), [`services/inventory/consumers.py::on_copy_damaged:35-44`](../../services/inventory/consumers.py#L35)
- Тесты: `tests/test_inventory_ill.py::test_damaged_on_return_is_written_off`, `tests/test_inventory_ill.py::test_late_return_finalizes_penalty`
- Связанные: R-INVENTORY-PENALTY-03, R-INVENTORY-WRITEOFF-01

## R-INVENTORY-ILL-07 — Утеря экземпляра партнёром списывает его и начисляет компенсацию

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: Компенсация одинакова для любых изданий и партнёров и не зависит от стоимости книги.

report_ill_lost переводит выдачу в статус lost, экземпляр — в lost, и публикует inventory.copy_lost с ill_loan_id. Подписчик on_copy_lost оформляет акт списания (reason=lost) и вызывает charge_lost_copy: тот начисляет партнёру пени вида lost на фиксированную сумму ILL_LOST_COMPENSATION (1500.00) сразу в статусе final.

- Реализация: [`services/inventory/service.py::report_ill_lost:368-373`](../../services/inventory/service.py#L368), [`services/inventory/consumers.py::on_copy_lost:24-31`](../../services/inventory/consumers.py#L24), [`services/inventory/service.py::charge_lost_copy:496-505`](../../services/inventory/service.py#L496)
- Настройки: `services/inventory/settings.py::ILL_LOST_COMPENSATION`
- Тесты: `tests/test_inventory_ill.py::test_loss_by_partner_charges_and_suspends`
- Связанные: R-INVENTORY-PENALTY-04, R-INVENTORY-PARTNER-02
- ⚠ Оговорка: Компенсация одинакова для любых изданий и партнёров и не зависит от стоимости книги.

## R-INVENTORY-PENALTY-01 — Просрочка считается в начатых сутках

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

days_late возвращает 0, если момент не позже due_at, иначе число полных суток плюс одни, если есть остаток (округление вверх). Например, 30 дней 5 часов после выдачи на 30 дней — 1 день просрочки.

- Реализация: [`services/inventory/service.py::days_late:31-36`](../../services/inventory/service.py#L31)
- Настройки: `services/inventory/service.py::DAY`
- Тесты: `tests/test_inventory_ill.py::test_overdue_flag_accrues_penalty`, `tests/test_inventory_ill.py::test_late_return_finalizes_penalty`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PENALTY-02

## R-INVENTORY-PENALTY-02 — Просроченная выдача помечается один раз и начинает начислять пени

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами · оговорка: В репозитории не найден планировщик, запускающий эту задачу: она вызывается только из тестов.

Фоновая задача flag_overdue_ill находит выдачи в статусе out с due_at < now и overdue_flagged=false, ставит overdue_flagged=true и публикует inventory.ill_overdue с числом дней просрочки. Подписчик on_ill_overdue вызывает accrue_overdue: создаётся пеня вида overdue в статусе accruing.

- Реализация: [`services/inventory/jobs.py::flag_overdue_ill:11-33`](../../services/inventory/jobs.py#L11), [`services/inventory/consumers.py::on_ill_overdue:48-49`](../../services/inventory/consumers.py#L48)
- Тесты: `tests/test_inventory_ill.py::test_overdue_flag_accrues_penalty`, `tests/test_inventory_ill.py::test_penalty_is_capped`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PENALTY-03, R-INVENTORY-PENALTY-05
- ⚠ Оговорка: В репозитории не найден планировщик, запускающий эту задачу: она вызывается только из тестов.

## R-INVENTORY-PENALTY-03 — Пени по невозвращённым выдачам ежедневно пересчитываются

`draft` · timer

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: В докстринге задача названа ежедневной, но расписание в коде не задано и планировщик в репозитории не найден.

Фоновая задача accrue_ill_penalties пересчитывает пени по выдачам в статусе out, у которых уже есть пеня overdue в статусе accruing (то есть после пометки flag_overdue_ill). Дни просрочки считаются на текущий момент через days_late. Если пени уже final или paid, accrue_overdue их не меняет.

- Реализация: [`services/inventory/jobs.py::accrue_ill_penalties:36-47`](../../services/inventory/jobs.py#L36), [`services/inventory/service.py::accrue_overdue:472-474`](../../services/inventory/service.py#L472)
- Тесты: `tests/test_inventory_ill.py::test_overdue_flag_accrues_penalty`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PENALTY-02, R-INVENTORY-PENALTY-05
- ⚠ Оговорка: В докстринге задача названа ежедневной, но расписание в коде не задано и планировщик в репозитории не найден.

## R-INVENTORY-PENALTY-04 — Пени за просрочку — дневная ставка партнёра × дни, не более ILL_PENALTY_MAX_DAYS

`draft` · calculation

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

accrue_overdue ставит days = min(дни просрочки, ILL_PENALTY_MAX_DAYS (90)) и amount = daily_penalty партнёра × days. Пеня создаётся по выдаче один раз на каждый вид (уникальный ключ ill_penalties_ill_loan_id_kind_key). После каждого начисления публикуется inventory.ill_penalty_accrued.

- Реализация: [`services/inventory/service.py::accrue_overdue:472-485`](../../services/inventory/service.py#L472), [`services/inventory/service.py::_penalty:447-464`](../../services/inventory/service.py#L447)
- БД: `ill_penalties_ill_loan_id_kind_key`, `ill_penalties_amount_check`, `ill_penalties_days_check`, `ill_penalties_kind_check`, `partner_libraries_daily_penalty_check`
- Настройки: `services/inventory/settings.py::ILL_PENALTY_MAX_DAYS`
- Тесты: `tests/test_inventory_ill.py::test_penalty_is_capped`, `tests/test_inventory_ill.py::test_overdue_flag_accrues_penalty`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PENALTY-01, R-INVENTORY-PARTNER-02

## R-INVENTORY-PENALTY-05 — Поздний возврат фиксирует итоговые пени даже без фоновой задачи

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 3 тестами

Подписчик on_ill_returned считает дни просрочки между due_at и returned_at из события. Если они есть, вызывает accrue_overdue с final=True: пеня создаётся, если её ещё не было, пересчитывается на дату возврата и получает статус final. Своевременный возврат пеней не создаёт.

- Реализация: [`services/inventory/consumers.py::on_ill_returned:52-58`](../../services/inventory/consumers.py#L52)
- Тесты: `tests/test_inventory_ill.py::test_late_return_finalizes_penalty`, `tests/test_inventory_ill.py::test_late_return_before_job_still_charges`, `tests/test_inventory_ill.py::test_timely_return_has_no_penalty`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PENALTY-04, R-INVENTORY-ILL-06

## R-INVENTORY-PENALTY-06 — При утере партнёром пени за просрочку замораживаются на последнем начислении

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом · оговорка: Если выдача просрочена, но flag_overdue_ill ещё не отработал, пеня за просрочку при утере не начисляется вовсе: on_ill_…

charge_lost_copy переводит существующую пеню overdue из accruing в final без пересчёта. Сумма остаётся такой, какой её посчитал последний запуск задачи. Компенсация за утерю начисляется отдельной пеней вида lost.

- Реализация: [`services/inventory/service.py::charge_lost_copy:491-495`](../../services/inventory/service.py#L491)
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-ILL-07
- ⚠ Оговорка: Если выдача просрочена, но flag_overdue_ill ещё не отработал, пеня за просрочку при утере не начисляется вовсе: on_ill_returned при утере не вызывается, а пени overdue ещё нет.

## R-INVENTORY-PENALTY-07 — Оплатить можно только итоговые пени

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом · оговорка: В settle_penalty нет проверки прав и HTTP-маршрута; связи с платежами billing нет, оплата отмечается прямым вызовом.

settle_penalty отклоняет оплату пеней в статусе accruing («пени ещё начисляются: экземпляр не возвращён») и уже оплаченных («пени уже оплачены»), в остальных случаях ставит статус paid. CHECK ill_penalties_status_check ограничивает статусы значениями accruing, final, paid.

- Реализация: [`services/inventory/service.py::settle_penalty:516-525`](../../services/inventory/service.py#L516)
- БД: `ill_penalties_status_check`
- Тесты: `tests/test_inventory_ill.py::test_settling_debt_resumes_partner`
- Связанные: R-INVENTORY-PARTNER-03
- ⚠ Оговорка: В settle_penalty нет проверки прав и HTTP-маршрута; связи с платежами billing нет, оплата отмечается прямым вызовом.

## R-INVENTORY-PARTNER-01 — Код библиотеки-партнёра уникален и имеет формат A-Z0-9-

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

register_partner отклоняет уже занятый код («библиотека с кодом … уже зарегистрирована»), в БД это дублирует partner_libraries_code_key. Формат кода (2–16 символов A-Z, 0-9, дефис) проверяет только CHECK partner_libraries_code_check. По умолчанию лимит одновременных выдач max_active_loans=5 задан литералом в сигнатуре функции; CHECK требует, чтобы он был больше 0.

- Реализация: [`services/inventory/service.py::register_partner:258-268`](../../services/inventory/service.py#L258)
- БД: `partner_libraries_code_key`, `partner_libraries_code_check`, `partner_libraries_max_active_loans_check`, `partner_libraries_daily_penalty_check`
- Связанные: R-INVENTORY-ILL-02

## R-INVENTORY-PARTNER-02 — Партнёр приостанавливается, когда долг по пеням превышает лимит

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: На inventory.partner_suspended нет подписчиков: никого не уведомляют.

На каждое inventory.ill_penalty_accrued подписчик on_penalty_accrued вызывает review_partner_debt. Если партнёр не приостановлен, а сумма неоплаченных пеней (accruing и final) больше ILL_PARTNER_DEBT_LIMIT (1000.00), ставится suspended=true и публикуется inventory.partner_suspended. При настройках по умолчанию любая утеря (компенсация 1500.00) приостанавливает партнёра.

- Реализация: [`services/inventory/consumers.py::on_penalty_accrued:61-63`](../../services/inventory/consumers.py#L61), [`services/inventory/service.py::review_partner_debt:534-539`](../../services/inventory/service.py#L534)
- Настройки: `services/inventory/settings.py::ILL_PARTNER_DEBT_LIMIT`
- Тесты: `tests/test_inventory_ill.py::test_loss_by_partner_charges_and_suspends`
- Роли: Система (события и фоновые задачи)
- Связанные: R-INVENTORY-PARTNER-03, R-INVENTORY-ILL-02
- ⚠ Оговорка: На inventory.partner_suspended нет подписчиков: никого не уведомляют.

## R-INVENTORY-PARTNER-03 — Оплата пеней возобновляет выдачи, когда долг опускается до лимита

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом · оговорка: На inventory.partner_resumed нет подписчиков. Приостановка снимается только оплатой, другого пути (например, вручную) н…

После оплаты пеней settle_penalty снимает приостановку (suspended=false) и публикует inventory.partner_resumed, если партнёр был приостановлен и неоплаченный долг теперь не больше ILL_PARTNER_DEBT_LIMIT.

- Реализация: [`services/inventory/service.py::settle_penalty:526-530`](../../services/inventory/service.py#L526)
- Настройки: `services/inventory/settings.py::ILL_PARTNER_DEBT_LIMIT`
- Тесты: `tests/test_inventory_ill.py::test_settling_debt_resumes_partner`
- Связанные: R-INVENTORY-PARTNER-02, R-INVENTORY-PENALTY-07
- ⚠ Оговорка: На inventory.partner_resumed нет подписчиков. Приостановка снимается только оплатой, другого пути (например, вручную) нет.

## R-INVENTORY-WRITEOFF-01 — Утеря или порча на полке ведёт к списанию через событие

`draft` · effect

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 2 тестами

mark_lost и mark_damaged переводят экземпляр в lost или damaged и публикуют inventory.copy_lost или inventory.copy_damaged. Подписчики on_copy_lost и on_copy_damaged оформляют акт списания с причиной lost/damaged и автором — хранителем. Экземпляр становится written_off и выпадает из остатка.

- Реализация: [`services/inventory/service.py::mark_lost:392-396`](../../services/inventory/service.py#L392), [`services/inventory/service.py::mark_damaged:399-405`](../../services/inventory/service.py#L399), [`services/inventory/consumers.py::on_copy_lost:24-29`](../../services/inventory/consumers.py#L24), [`services/inventory/consumers.py::on_copy_damaged:35-44`](../../services/inventory/consumers.py#L35)
- Тесты: `tests/test_inventory_copies.py::test_lost_copy_is_written_off_and_leaves_stock`, `tests/test_inventory_copies.py::test_damaged_copy_is_written_off`
- Связанные: R-INVENTORY-WRITEOFF-02, R-INVENTORY-WRITEOFF-04

## R-INVENTORY-WRITEOFF-02 — Утеря, порча и списание по ветхости — только для экземпляра на полке

`draft` · guard

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Экземпляр должен быть доступен на площадке и без открытого перемещения. Выданный по МБА — «экземпляр выдан по МБА, оформите утерю или возврат по выдаче». В другом состоянии, кроме available, — «экземпляр уже выбыл из фонда или находится в пути». С открытым перемещением — «по экземпляру оформлено перемещение».

- Реализация: [`services/inventory/service.py::_on_shelf:380-389`](../../services/inventory/service.py#L380), [`services/inventory/service.py::write_off_worn:411-412`](../../services/inventory/service.py#L411)
- Тесты: `tests/test_inventory_copies.py::test_worn_out_write_off_by_custodian_only`
- Связанные: R-INVENTORY-WRITEOFF-01, R-INVENTORY-ILL-07

## R-INVENTORY-WRITEOFF-03 — Списанный экземпляр нельзя изменить (триггер БД)

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Триггер trg_copies_written_off_final (функция forbid_written_off_change) отклоняет любое UPDATE строки inventory.copies, если её текущее состояние written_off. Списание необратимо и на уровне БД.

- Реализация: [`services/inventory/service.py::write_off:438-438`](../../services/inventory/service.py#L438)
- БД: `trg_copies_written_off_final`, `forbid_written_off_change`
- Тесты: `tests/test_inventory_copies.py::test_written_off_copy_cannot_be_changed`
- Связанные: R-INVENTORY-WRITEOFF-04

## R-INVENTORY-WRITEOFF-04 — Один акт списания на экземпляр с номером СП-год-id

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 3 тестами

write_off идемпотентен: если по экземпляру уже есть акт, возвращается он, и новый не создаётся. Номер акта собирается как «СП-<год>-<id экземпляра, 6 цифр>». Причина — lost, damaged или worn_out. После списания экземпляр получает written_off, публикуется inventory.copy_written_off. В БД: уникальные write_offs_copy_id_key и write_offs_act_no_key, CHECK write_offs_reason_check.

- Реализация: [`services/inventory/service.py::write_off:424-440`](../../services/inventory/service.py#L424)
- БД: `write_offs_copy_id_key`, `write_offs_act_no_key`, `write_offs_reason_check`
- Тесты: `tests/test_inventory_copies.py::test_lost_copy_is_written_off_and_leaves_stock`, `tests/test_inventory_copies.py::test_worn_out_write_off_by_custodian_only`, `tests/test_inventory_ill.py::test_damaged_on_return_is_written_off`
- Связанные: R-INVENTORY-WRITEOFF-03
