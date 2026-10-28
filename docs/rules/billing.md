<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: billing

Источник: [`knowledge/rules/billing.yaml`](../../knowledge/rules/billing.yaml)

## R-BILL-ASSIGN-01 — Бухгалтер сам закрепляет заявку за собой и может забрать её у коллеги

`draft` · permission · §3 Кто закреплён за заявкой

Достоверность: описано в бизнес-схеме §3 · ⚠ код расходится со схемой §3 (D-20): Схема: бухгалтер берёт в работу платные заявки, прошедшие проверку. Код не проверяет этап и роль: заявку можно взять на любом этапе, в том … — уточни у пользователя

take_application создаёт запись в billing.accountant_assignments, а если запись уже есть, перезаписывает accountant_id. У заявки всегда не больше одного бухгалтера (PK по application_id), согласие предыдущего бухгалтера не нужно.

- Реализация: [`services/billing/service.py::take_application:22-26`](../../services/billing/service.py#L22)
- Тесты: `tests/test_paid_flow.py::test_invoice_requires_assigned_accountant`
- Роли: Бухгалтер
- Связанные: R-BILL-ASSIGN-02, R-BILL-ASSIGN-03
- ⚠ Расхождение со схемой: Схема: бухгалтер берёт в работу платные заявки, прошедшие проверку. Код не проверяет этап и роль: заявку можно взять на любом этапе, в том числе в черновике или после закрытия.

## R-BILL-ASSIGN-02 — У заявки в долг нет бухгалтера

`draft` · guard · §3 Кто закреплён за заявкой

Достоверность: описано в бизнес-схеме §3 · ⚠ открытый вопрос D-20: Ограничить ли закрепление этапами от awaiting_invoice (для paid) и наличием штрафа (для social)? — уточни у пользователя

take_application отклоняет закрепление бухгалтера за заявкой вида debt с ошибкой «у заявки в долг нет бухгалтера».

- Реализация: [`services/billing/service.py::take_application:19-21`](../../services/billing/service.py#L19)
- Тесты: `tests/test_kinds.py::test_debt_application_skips_invoice`
- Роли: Бухгалтер
- Связанные: R-BILL-ASSIGN-01, R-BILL-FINE-INVOICE-02

## R-BILL-ASSIGN-03 — Счёт выставляет только бухгалтер, закреплённый за заявкой

`draft` · permission · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Перед выставлением счёта за книги или за штраф _require_accountant проверяет, что за заявкой закреплён именно этот бухгалтер. Иначе AccessDenied «заявка закреплена за другим бухгалтером». Если бухгалтер не закреплён совсем, ошибка та же.

- Реализация: [`services/billing/service.py::_require_accountant:29-32`](../../services/billing/service.py#L29), [`services/billing/service.py::issue_books_invoice:36-36`](../../services/billing/service.py#L36), [`services/billing/service.py::issue_fine_invoice:184-184`](../../services/billing/service.py#L184)
- Тесты: `tests/test_paid_flow.py::test_invoice_requires_assigned_accountant`
- Роли: Бухгалтер
- Связанные: R-BILL-ASSIGN-01, R-BILL-INVOICE-01, R-BILL-FINE-INVOICE-01

## R-BILL-ASSIGN-04 — Закреплённый бухгалтер — участник чата заявки

`draft` · effect · §15 Чат заявки

Достоверность: описано в бизнес-схеме §15 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

public.accountant_of возвращает бухгалтера, закреплённого за заявкой. Через него чат (services/chat/service.py::participants) включает бухгалтера в участники. Когда заявку забирает другой бухгалтер, в чат попадает новый.

- Реализация: [`services/billing/public.py::accountant_of:48-50`](../../services/billing/public.py#L48)
- Роли: Бухгалтер
- Связанные: R-BILL-ASSIGN-01

## R-BILL-INVOICE-01 — Счёт за книги выставляется только по платной заявке

`draft` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

issue_books_invoice отклоняет заявки, вид которых не paid, с ошибкой «счёт за книги выставляется только по платной заявке». По социальным заявкам и заявкам в долг счёт за книги не создаётся.

- Реализация: [`services/billing/service.py::issue_books_invoice:37-39`](../../services/billing/service.py#L37)
- Тесты: `tests/test_kinds.py::test_no_books_invoice_for_social`
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-02

## R-BILL-INVOICE-02 — Счёт за книги выставляется только на этапе «Ожидает счёта»

`draft` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

issue_books_invoice требует этап awaiting_invoice. Иначе ошибка «счёт выставляется после прохождения проверки». Поэтому по заявке в «Ожидает оплаты» второй счёт не выставить.

- Реализация: [`services/billing/service.py::issue_books_invoice:40-41`](../../services/billing/service.py#L40)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-01, R-BILL-INVOICE-06

## R-BILL-INVOICE-03 — Без реквизитов организации площадки счёт не выставить

`draft` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Счёт за книги и счёт на штраф выставляются, только если у площадки заявки заполнены реквизиты. Иначе ошибка «у площадки не заполнены реквизиты организации».

- Реализация: [`services/billing/service.py::issue_books_invoice:42-44`](../../services/billing/service.py#L42), [`services/billing/service.py::issue_fine_invoice:185-187`](../../services/billing/service.py#L185)
- Тесты: `tests/test_paid_flow.py::test_invoice_requires_venue_requisites`
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-05

## R-BILL-INVOICE-04 — Сумма счёта за книги = цена по прайсу площадки + надбавка представителя

`draft` · calculation · §10 Надбавка представителя

Достоверность: описано в бизнес-схеме §10 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Сумма считается как books_price × (1 + markup_pct / 100) и округляется до копейки (CENT = 0.01, ROUND_HALF_UP). Цену по прайсу площадки даёт applications.books_price, процент надбавки представителя — applications.markup_pct. После выставления сумма зафиксирована: код, меняющий сумму счёта, отсутствует.

- Реализация: [`services/billing/service.py::issue_books_invoice:46-48`](../../services/billing/service.py#L46)
- БД: [`invoices_amount_check`](../../migrations/versions/0001_initial.py#L168)
- Настройки: `services/billing/service.py::CENT`
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-05

## R-BILL-INVOICE-05 — Счёт сохраняет площадку и снимок её реквизитов

`draft` · invariant · §7 Площадки и цены

Достоверность: описано в бизнес-схеме §7 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

При выставлении счёта (за книги или штраф) в нём сохраняются venue_id и копия реквизитов площадки на этот момент (jsonb). Если реквизиты площадки потом изменятся, выставленный счёт останется прежним. При выставлении issued_at и payment_clock_started_at равны текущему времени.

- Реализация: [`services/billing/service.py::issue_books_invoice:49-60`](../../services/billing/service.py#L49), [`services/billing/service.py::issue_fine_invoice:188-200`](../../services/billing/service.py#L188)
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-03, R-BILL-ARCHIVE-01

## R-BILL-INVOICE-06 — У заявки не больше одного действующего счёта за книги

`draft` · invariant · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Частичный уникальный индекс uq_invoices_one_active_books разрешает только один счёт kind='books' со status='active' на заявку. Число счетов на штрафы не ограничено. В коде отдельной проверки нет: её косвенно заменяет требование этапа awaiting_invoice.

- Реализация: [`services/billing/public.py::active_books_invoice:31-45`](../../services/billing/public.py#L31)
- БД: [`uq_invoices_one_active_books`](../../migrations/versions/0001_initial.py#L177)
- Тесты: `tests/test_venue_change.py::test_venue_change_before_payment_reissues_invoice`
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-INVOICE-02

## R-BILL-INVOICE-07 — Вид счёта — books или fine; счёт на штраф ссылается на штраф

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

CHECK invoices_kind_check разрешает только виды books и fine, invoices_status_check — только статусы active и cancelled. invoices_check требует, чтобы fine_id был заполнен тогда и только тогда, когда kind='fine'. Сумма счёта строго больше нуля (invoices_amount_check), поэтому штраф нулевого размера выставить счётом нельзя.

- БД: [`invoices_kind_check`](../../migrations/versions/0001_initial.py#L166), [`invoices_status_check`](../../migrations/versions/0001_initial.py#L169), [`invoices_check`](../../migrations/versions/0001_initial.py#L175), [`invoices_amount_check`](../../migrations/versions/0001_initial.py#L168)
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-FINE-03

## R-BILL-INVOICE-08 — Выставление счёта за книги переводит заявку в «Ожидает оплаты»

`verified` · effect · §4 Порядок прохождения заявки

Достоверность: описано в бизнес-схеме §4 · проверено человеком 2026-10-23, с тех пор не менялось

issue_books_invoice публикует invoice.issued. Подписчик applications on_invoice_issued для счёта вида books переводит заявку из awaiting_invoice в awaiting_payment от имени бухгалтера. Счёт на штраф этап не меняет.

- Реализация: [`services/billing/service.py::issue_books_invoice:62-71`](../../services/billing/service.py#L62), [`services/applications/consumers.py::on_invoice_issued:13-18`](../../services/applications/consumers.py#L13), [`awaiting_invoice->awaiting_payment`](../../bpm/application_process.yaml#L27)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Бухгалтер
- Связанные: R-BILL-INVOICE-04

## R-BILL-CANCEL-01 — Счёт с привязанным платежом аннулировать нельзя

`verified` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · проверено человеком 2026-10-23, с тех пор не менялось

cancel_invoice отклоняет аннулирование, если по счёту есть действующие платежи (не отвязанные и не возвращённые): «к счёту привязан платёж: сначала отвязать или вернуть». То же условие дублирует триггер trg_invoices_cancel_guard (функция forbid_cancel_paid_invoice) при переходе статуса active→cancelled.

- Реализация: [`services/billing/service.py::cancel_invoice:81-82`](../../services/billing/service.py#L81)
- БД: [`trg_invoices_cancel_guard`](../../migrations/versions/0001_initial.py#L212), [`forbid_cancel_paid_invoice`](../../migrations/versions/0001_initial.py#L201)
- Роли: Бухгалтер, Система (события и фоновые задачи)
- Связанные: R-BILL-PAYMENT-02, R-BILL-CANCEL-02

## R-BILL-CANCEL-02 — Аннулирование уже аннулированного счёта ничего не делает

`draft` · invariant · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · ⚠ код расходится со схемой §11 (D-03): Схема: аннулирует счёт бухгалтер, закреплённый за заявкой. Код cancel_invoice не проверяет роль и закрепление, причину не требует. HTTP-мар… — уточни у пользователя

Если счёт не active, cancel_invoice молча возвращает его: событие не публикуется, причина не перезаписывается. При аннулировании действующего счёта сохраняются status='cancelled' и cancel_reason.

- Реализация: [`services/billing/service.py::cancel_invoice:79-84`](../../services/billing/service.py#L79)
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-CANCEL-01
- ⚠ Расхождение со схемой: Схема: аннулирует счёт бухгалтер, закреплённый за заявкой. Код cancel_invoice не проверяет роль и закрепление, причину не требует. HTTP-маршрута для него нет: вызывается только подписчиками.

## R-BILL-CANCEL-03 — Аннулирование счёта за книги возвращает заявку в «Ожидает счёта»

`draft` · effect · §4 Порядок прохождения заявки

Достоверность: описано в бизнес-схеме §4 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

cancel_invoice публикует invoice.cancelled. Подписчик applications on_invoice_cancelled для счёта вида books переводит заявку из awaiting_payment в awaiting_invoice (actor system), и бухгалтер выставляет новый счёт. Аннулирование счёта на штраф этап не меняет.

- Реализация: [`services/billing/service.py::cancel_invoice:85-94`](../../services/billing/service.py#L85), [`services/applications/consumers.py::on_invoice_cancelled:22-27`](../../services/applications/consumers.py#L22), [`awaiting_payment->awaiting_invoice`](../../bpm/application_process.yaml#L28)
- Тесты: `tests/test_venue_change.py::test_venue_change_before_payment_reissues_invoice`
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-VENUE-CHANGE-01, R-BILL-UNARCHIVE-01

## R-BILL-VENUE-CHANGE-01 — Смена площадки аннулирует неоплаченный счёт за книги

`draft` · effect · §7 Площадки и цены

Достоверность: описано в бизнес-схеме §7 · ⚠ код расходится со схемой §7 (D-05): Схема: после оплаты площадку меняют только через возврат платежа. Код: счёт с частичной оплатой подписчик не аннулирует и ошибку не поднима… — уточни у пользователя

На событие application.venue_changed подписчик billing on_venue_changed аннулирует действующий счёт за книги с причиной venue_changed, если оплаченная по нему сумма равна нулю. Дальше через invoice.cancelled заявка возвращается в «Ожидает счёта», и бухгалтер выставляет новый счёт по прайсу и реквизитам новой площадки.

- Реализация: [`services/billing/consumers.py::on_venue_changed:13-16`](../../services/billing/consumers.py#L13)
- БД: [`trg_invoices_cancel_guard`](../../migrations/versions/0001_initial.py#L212)
- Тесты: `tests/test_venue_change.py::test_venue_change_before_payment_reissues_invoice`
- Роли: Оператор
- Связанные: R-BILL-CANCEL-03, R-BILL-CANCEL-01
- ⚠ Расхождение со схемой: Схема: после оплаты площадку меняют только через возврат платежа. Код: счёт с частичной оплатой подписчик не аннулирует и ошибку не поднимает. Если смена площадки прошла (запрет в applications рассчитан на полную оплату), счёт остаётся на реквизитах и цене старой площадки. Счета на штрафы при смене площадки не трогаются.

## R-BILL-DUPLICATE-01 — Закрытие заявки как дубля аннулирует все её неоплаченные счета

`draft` · effect · §6 Клиент и проверка данных

Достоверность: описано в бизнес-схеме §6 · ⚠ код расходится со схемой §6 (D-15): Схема: счёт заявки-дубля аннулируется. Код: частично оплаченный счёт заявки-дубля остаётся действующим, возврат по нему автоматически не ин… — уточни у пользователя

На событие application.closed_duplicate подписчик on_closed_duplicate проходит по всем действующим счетам заявки — за книги и на штрафы — и аннулирует с причиной duplicate те, по которым оплачено 0. Счета с частичной оплатой остаются действующими.

- Реализация: [`services/billing/consumers.py::on_closed_duplicate:20-23`](../../services/billing/consumers.py#L20), [`services/billing/service.py::active_invoices:230-237`](../../services/billing/service.py#L230)
- БД: [`trg_invoices_cancel_guard`](../../migrations/versions/0001_initial.py#L212)
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-CANCEL-01, R-BILL-PAYMENT-04
- ⚠ Расхождение со схемой: Схема: счёт заявки-дубля аннулируется. Код: частично оплаченный счёт заявки-дубля остаётся действующим, возврат по нему автоматически не инициируется.

## R-BILL-UNARCHIVE-01 — При возврате из архива счёт аннулируется, только если сумма изменилась

`draft` · effect · §5 Архив и попытки

Достоверность: описано в бизнес-схеме §5 · ⚠ код расходится со схемой §5 (D-14): Решение «сумма изменилась» принимает публикатор (флаг amount_changed), billing сумму не пересчитывает. Если amount_changed=true, а по счёту… — уточни у пользователя

На application.unarchived подписчик on_unarchived смотрит на действующий счёт за книги. Если в событии amount_changed=true, счёт аннулируется с причиной amount_changed. Иначе счёт остаётся прежним, а payment_clock_started_at сбрасывается на текущее время: месяц на оплату считается заново с возврата из архива.

- Реализация: [`services/billing/consumers.py::on_unarchived:27-35`](../../services/billing/consumers.py#L27)
- БД: [`trg_invoices_cancel_guard`](../../migrations/versions/0001_initial.py#L212)
- Роли: Оператор
- Связанные: R-BILL-ARCHIVE-01, R-BILL-PROCESS-03
- ⚠ Расхождение со схемой: Решение «сумма изменилась» принимает публикатор (флаг amount_changed), billing сумму не пересчитывает. Если amount_changed=true, а по счёту есть частичная оплата, cancel_invoice поднимет DomainError внутри обработчика события.

## R-BILL-ARCHIVE-01 — Неоплаченная платная заявка уходит в архив через PAYMENT_ARCHIVE_DAYS от начала отсчёта оплаты

`draft` · timer · §5 Архив и попытки

Достоверность: описано в бизнес-схеме §5 · ⚠ открытый вопрос D-17: Где и с какой периодичностью запускаются задачи (в docstring — раз в час), и кто за этим следит? — уточни у пользователя

Фоновая задача applications archive_stale берёт через active_books_invoice счёт заявки в awaiting_payment. Если счёт оплачен не полностью и payment_clock_started_at старше PAYMENT_ARCHIVE_DAYS (30 дней), заявка уходит в архив с отметкой unpaid. Отсчёт идёт от выставления счёта или от возврата из архива. Срок задан настройкой, а не литералом.

- Реализация: [`services/billing/public.py::active_books_invoice:31-45`](../../services/billing/public.py#L31), [`awaiting_payment->archived`](../../bpm/application_process.yaml#L38)
- Настройки: `libs/settings.py::PAYMENT_ARCHIVE_DAYS`
- Тесты: `tests/test_archive.py::test_unpaid_invoice_goes_to_archive_after_month`
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-UNARCHIVE-01, R-BILL-INVOICE-05

## R-BILL-PAYMENT-01 — Платёж нельзя привязать к аннулированному счёту

`draft` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

link_payment отклоняет привязку к счёту со статусом не active: «платёж нельзя привязать к аннулированному счёту». То же условие дублирует триггер trg_payments_active_invoice (функция forbid_payment_to_cancelled) на INSERT в billing.payments.

- Реализация: [`services/billing/service.py::link_payment:102-103`](../../services/billing/service.py#L102)
- БД: [`trg_payments_active_invoice`](../../migrations/versions/0001_initial.py#L224), [`forbid_payment_to_cancelled`](../../migrations/versions/0001_initial.py#L216)
- Роли: Главный бухгалтер
- Связанные: R-BILL-PAYMENT-03

## R-BILL-PAYMENT-02 — Оплаченная сумма — сумма действующих платежей без отвязанных и возвращённых

`draft` · calculation · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

paid_amount суммирует платежи счёта, у которых unlinked_at IS NULL и refunded = false. Эта сумма используется в guard'ах fully_paid, при аннулировании счёта, в архивации по сроку и в подписчиках billing. Триггер forbid_cancel_paid_invoice использует то же определение.

- Реализация: [`services/billing/public.py::paid_amount:22-28`](../../services/billing/public.py#L22)
- БД: [`forbid_cancel_paid_invoice`](../../migrations/versions/0001_initial.py#L201)
- Тесты: `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue`
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-CANCEL-01, R-BILL-PROCESS-01

## R-BILL-PAYMENT-03 — Привязка платежа фиксирует, кто привязал; переплата помечается флагом

`verified` · effect · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · ⚠ код расходится со схемой §11 (D-03): Схема: привязывает платежи только главный бухгалтер. Код не проверяет роль: chief_id приходит в теле запроса POST /invoices/{invoice_id}/pa… — уточни у пользователя

link_payment сохраняет платёж с linked_at и linked_by (chief_id) и публикует payment.linked. Если вместе с прошлыми платежами сумма превышает сумму счёта, у платежа ставится overpayment=true. Привязка при этом не блокируется, а автоматического решения по переплате нет. Сумма платежа строго положительна (payments_amount_check).

- Реализация: [`services/billing/service.py::link_payment:104-115`](../../services/billing/service.py#L104)
- БД: [`payments_amount_check`](../../migrations/versions/0001_initial.py#L183)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Главный бухгалтер
- Связанные: R-BILL-PAYMENT-04
- ⚠ Расхождение со схемой: Схема: привязывает платежи только главный бухгалтер. Код не проверяет роль: chief_id приходит в теле запроса POST /invoices/{invoice_id}/payments и только записывается в linked_by.

## R-BILL-PAYMENT-04 — Полная оплата публикуется один раз — когда сумма впервые достигает суммы счёта

`draft` · effect · §9 Виды заявок / Платная

Достоверность: описано в бизнес-схеме §9 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

link_payment публикует payment.fully_paid, только если до платежа оплачено меньше суммы счёта, а после — не меньше (before < amount <= after). Частичная оплата событие не порождает. Повторные платежи после полной оплаты тоже не порождают.

- Реализация: [`services/billing/service.py::link_payment:116-128`](../../services/billing/service.py#L116)
- Тесты: `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue`
- Роли: Главный бухгалтер
- Связанные: R-BILL-PROCESS-01, R-BILL-FINE-PAY-01

## R-BILL-PROCESS-01 — Полная оплата счёта за книги открывает выдачу и закрывает дубли

`draft` · effect · §6 Клиент и проверка данных

Достоверность: описано в бизнес-схеме §6 · ⚠ открытый вопрос D-01: Если у клиента уже есть оплаченная заявка на «Ожидает выдачи», должна ли более поздняя заявка в долг закрыться сама как дубль, а не закрыва… — уточни у пользователя

Подписчик applications on_fully_paid для счёта books переводит заявку из awaiting_payment в awaiting_issue (actor system), формирует ссылку на запись (mark_ready_for_booking) и закрывает заявки-дубли клиента по той же сфере (dedup.close_duplicates). Переход awaiting_payment->awaiting_issue защищён guard'ом fully_paid.

- Реализация: [`services/applications/consumers.py::on_fully_paid:31-39`](../../services/applications/consumers.py#L31), [`awaiting_payment->awaiting_issue`](../../bpm/application_process.yaml#L29), [`guard:fully_paid`](../../bpm/application_process.yaml)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`, `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue`
- Роли: Главный бухгалтер
- Связанные: R-BILL-PAYMENT-04, R-BILL-PROCESS-02, R-BILL-DUPLICATE-01

## R-BILL-PROCESS-02 — Guard fully_paid: действующий счёт за книги оплачен полностью

`verified` · guard · §9 Виды заявок / Платная

Достоверность: описано в бизнес-схеме §9 · проверено человеком 2026-10-23, с тех пор не менялось

Guard fully_paid истинен, если у заявки есть действующий счёт за книги и paid_amount не меньше его суммы. Им защищён переход awaiting_payment->awaiting_issue.

- Реализация: [`services/billing/guards.py::fully_paid:10-12`](../../services/billing/guards.py#L10), [`guard:fully_paid`](../../bpm/application_process.yaml), [`awaiting_payment->awaiting_issue`](../../bpm/application_process.yaml#L29)
- Тесты: `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue`
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-PROCESS-01, R-BILL-PAYMENT-02

## R-BILL-PROCESS-03 — После повторной проверки заявка с действующим счётом идёт сразу в «Ожидает оплаты»

`draft` · guard · §5 Архив и попытки

Достоверность: описано в бизнес-схеме §5 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Guard has_active_invoice истинен, если у заявки есть действующий счёт за книги. Им защищён переход on_review->awaiting_payment. Approve в applications через active_books_invoice выбирает awaiting_payment, если такой счёт есть, иначе awaiting_invoice. Так прежний счёт переживает возврат на проверку и возврат из архива.

- Реализация: [`services/billing/guards.py::has_active_invoice:16-17`](../../services/billing/guards.py#L16), [`guard:has_active_invoice`](../../bpm/application_process.yaml), [`on_review->awaiting_payment`](../../bpm/application_process.yaml#L24)
- Роли: Проверяющий
- Связанные: R-BILL-UNARCHIVE-01

## R-BILL-REFUND-01 — Возврат платежа требует причины и исключает платёж из оплаченной суммы

`verified` · effect · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · ⚠ код расходится со схемой §11 (D-03, D-13): Схема: возврат оформляет только главный бухгалтер. Код не проверяет роль, повторный возврат и возврат отвязанного платежа. Статус штрафа (p… — уточни у пользователя

refund_payment без причины отклоняется («возврат платежа требует причины»). При возврате ставится refunded=true, и платёж перестаёт входить в paid_amount. Счёт остаётся действующим. Публикуется payment.refunded.

- Реализация: [`services/billing/service.py::refund_payment:144-160`](../../services/billing/service.py#L144)
- Роли: Главный бухгалтер
- Связанные: R-APP-PAY-04, R-BILL-PAYMENT-02
- ⚠ Расхождение со схемой: Схема: возврат оформляет только главный бухгалтер. Код не проверяет роль, повторный возврат и возврат отвязанного платежа. Статус штрафа (paid) при возврате платежа по счёту на штраф обратно не меняется.

## R-BILL-UNLINK-01 — Отвязка платежа требует причины

`draft` · guard · §11 Счета и платежи

Достоверность: описано в бизнес-схеме §11 · ⚠ код расходится со схемой §11 (D-03, D-13): Код не проверяет роль главного бухгалтера и не публикует событие. Если отвязать платёж после полной оплаты, заявка остаётся в «Ожидает выда… — уточни у пользователя

unlink_payment без причины отклоняется («отвязка платежа требует причины»). При отвязке сохраняются unlinked_at и unlink_reason, и платёж перестаёт входить в paid_amount. CHECK payments_check требует unlink_reason у каждого отвязанного платежа.

- Реализация: [`services/billing/service.py::unlink_payment:133-139`](../../services/billing/service.py#L133)
- БД: [`payments_check`](../../migrations/versions/0001_initial.py#L190)
- Роли: Главный бухгалтер
- Связанные: R-BILL-PAYMENT-02, R-BILL-CANCEL-01
- ⚠ Расхождение со схемой: Код не проверяет роль главного бухгалтера и не публикует событие. Если отвязать платёж после полной оплаты, заявка остаётся в «Ожидает выдачи», а оплаченный по нему штраф — в статусе paid. Повторная отвязка перезаписывает unlinked_at и причину.

## R-BILL-FINE-01 — Просрочка, утеря и порча книги автоматически создают штраф

`draft` · effect · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Подписчики billing на loan.overdue, loan.lost и loan.damaged (из scheduling) создают штраф вида overdue, lost или damaged по займу. Штраф создаётся для всех видов заявок.

- Реализация: [`services/billing/consumers.py::on_loan_overdue:39-40`](../../services/billing/consumers.py#L39), [`services/billing/consumers.py::on_loan_lost:44-45`](../../services/billing/consumers.py#L44), [`services/billing/consumers.py::on_loan_damaged:49-50`](../../services/billing/consumers.py#L49)
- БД: [`fines_kind_check`](../../migrations/versions/0001_initial.py#L156)
- Роли: Система (события и фоновые задачи), Проверяющий оператор
- Связанные: R-BILL-FINE-02

## R-BILL-FINE-02 — Размер штрафа берётся из ставки по представителю, площадке и виду

`draft` · calculation · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · ⚠ код расходится со схемой §14 (D-07): Если ставка не настроена, DomainError поднимается внутри обработчика loan.overdue, loan.lost или loan.damaged: штраф не создаётся, а заявку… — уточни у пользователя

create_fine ищет ставку в billing.fine_rates по ключу (representative_id, venue_id, kind) заявки и копирует её amount в штраф. Если ставки нет — ошибка «размер штрафа … не настроен для представителя и площадки». Ставка неотрицательна, вид ставки — overdue, lost или damaged.

- Реализация: [`services/billing/service.py::create_fine:165-173`](../../services/billing/service.py#L165)
- БД: [`fine_rates_amount_check`](../../migrations/versions/0001_initial.py#L197), [`fine_rates_kind_check`](../../migrations/versions/0001_initial.py#L196), [`fines_amount_check`](../../migrations/versions/0001_initial.py#L157)
- Роли: Администратор, Система (события и фоновые задачи)
- Связанные: R-BILL-FINE-01, R-BILL-INVOICE-07
- ⚠ Расхождение со схемой: Если ставка не настроена, DomainError поднимается внутри обработчика loan.overdue, loan.lost или loan.damaged: штраф не создаётся, а заявку можно закрыть без него. Нулевую ставку БД допускает, но счёт на неё не выставить (invoices_amount_check требует amount > 0).

## R-BILL-FINE-03 — Штраф бывает только «открыт» или «оплачен»

`draft` · invariant

Достоверность: поведение кода, в бизнес-схеме не описано · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

CHECK fines_status_check разрешает статусы open и paid, fines_kind_check — виды overdue, lost и damaged, fines_amount_check — неотрицательную сумму. Новый штраф создаётся со статусом open.

- БД: [`fines_status_check`](../../migrations/versions/0001_initial.py#L158), [`fines_kind_check`](../../migrations/versions/0001_initial.py#L156), [`fines_amount_check`](../../migrations/versions/0001_initial.py#L157)
- Роли: Система (события и фоновые задачи)
- Связанные: R-BILL-FINE-SETTLED-01

## R-BILL-FINE-INVOICE-01 — Счёт на штраф выставляет закреплённый бухгалтер на реквизиты площадки

`draft` · effect · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · ⚠ код расходится со схемой §14 (D-13): Код не проверяет, оплачен ли уже штраф и есть ли по нему действующий счёт. На один штраф можно выставить несколько счетов: уникальный индек… — уточни у пользователя

issue_fine_invoice создаёт счёт kind='fine' на сумму штрафа с fine_id, площадкой и снимком реквизитов и публикует invoice.issued (invoice_kind=fine). Нужны закреплённый бухгалтер и заполненные реквизиты площадки. Этап заявки не меняется.

- Реализация: [`services/billing/service.py::issue_fine_invoice:184-211`](../../services/billing/service.py#L184)
- БД: [`invoices_check`](../../migrations/versions/0001_initial.py#L175)
- Роли: Бухгалтер
- Связанные: R-BILL-ASSIGN-03, R-BILL-INVOICE-03, R-BILL-FINE-INVOICE-02
- ⚠ Расхождение со схемой: Код не проверяет, оплачен ли уже штраф и есть ли по нему действующий счёт. На один штраф можно выставить несколько счетов: уникальный индекс действует только для kind='books'.

## R-BILL-FINE-INVOICE-02 — По заявке в долг счёт на штраф не выставляется

`draft` · guard · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

issue_fine_invoice отклоняет штрафы заявок вида debt: «по заявке в долг штраф оплачивается вне системы». Проверка идёт до проверки закрепления бухгалтера.

- Реализация: [`services/billing/service.py::issue_fine_invoice:181-183`](../../services/billing/service.py#L181)
- Роли: Бухгалтер
- Связанные: R-BILL-FINE-OUTSIDE-01, R-BILL-ASSIGN-02

## R-BILL-FINE-PAY-01 — Полная оплата счёта на штраф гасит штраф

`draft` · effect · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · ⚠ открытый вопрос D-13: Должна ли отвязка или возврат оплаты возвращать заявку в «Ожидает оплаты», а штраф — в open? Можно ли выставлять второй счёт на тот же штра… — уточни у пользователя

Когда link_payment впервые доводит оплату счёта kind='fine' до его суммы, штраф получает status='paid'. Публикуется payment.fully_paid с invoice_kind=fine. Подписчик applications такие события пропускает, этап не меняется.

- Реализация: [`services/billing/service.py::link_payment:116-119`](../../services/billing/service.py#L116)
- Роли: Главный бухгалтер
- Связанные: R-BILL-PAYMENT-04, R-BILL-FINE-SETTLED-01

## R-BILL-FINE-OUTSIDE-01 — Штраф по заявке в долг гасит закреплённый оператор вне системы

`verified` · permission · §9 Виды заявок / В долг

Достоверность: описано в бизнес-схеме §9 · проверено человеком 2026-10-23, с тех пор не менялось

mark_fine_paid_outside ставит штрафу status='paid' и paid_outside=true. Это разрешено только для заявок вида debt («вне системы гасятся только штрафы по заявкам в долг») и только оператору этой заявки (AccessDenied «заявка закреплена за другим оператором»).

- Реализация: [`services/billing/service.py::mark_fine_paid_outside:220-226`](../../services/billing/service.py#L220)
- Роли: Оператор
- Связанные: R-BILL-FINE-INVOICE-02, R-BILL-FINE-SETTLED-01

## R-BILL-FINE-SETTLED-01 — Заявку нельзя закрыть, пока есть открытые штрафы

`draft` · guard · §14 Выдача, возврат и штрафы

Достоверность: описано в бизнес-схеме §14 · ⚠ открытый вопрос D-07: Что делать при отсутствии ставки — блокировать выдачу книг, пока ставки не настроены, или создавать штраф без суммы, который ждёт настройки… — уточни у пользователя

public.open_fines_count считает штрафы заявки со status='open'. Guard settled в applications использует его на переходе books_out->closed: при открытых штрафах заявка не закрывается.

- Реализация: [`services/billing/public.py::open_fines_count:53-56`](../../services/billing/public.py#L53), [`guard:settled`](../../bpm/application_process.yaml), [`books_out->closed`](../../bpm/application_process.yaml#L35)
- Роли: Проверяющий оператор
- Связанные: R-BILL-FINE-PAY-01, R-BILL-FINE-OUTSIDE-01
