<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: scheduling

Источник: [`knowledge/rules/scheduling.yaml`](../../knowledge/rules/scheduling.yaml)

## R-SCHED-SITE-CHECKER-01 — Проверяющий оператор работает только со своей площадкой

`draft` · permission

Достоверность: реализует требование REQ-ROLE-09, REQ-SLOT-01 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Создать окно, уменьшить в нём число мест, убрать окно и отметить неявку может только проверяющий оператор площадки окна (venue.site_checker_id). Иначе — AccessDenied «проверяющий оператор работает только со своей площадкой». Проверка общая, в _require_site_checker.

- Реализация: [`services/scheduling/service.py::_require_site_checker:17-20`](../../services/scheduling/service.py#L17), [`services/scheduling/service.py::create_slot:32`](../../services/scheduling/service.py#L32), [`services/scheduling/service.py::reduce_capacity:56`](../../services/scheduling/service.py#L56), [`services/scheduling/service.py::remove_slot:70`](../../services/scheduling/service.py#L70), [`services/scheduling/service.py::mark_no_show:218`](../../services/scheduling/service.py#L218)
- Роли: Проверяющий оператор
- Связанные: R-SCHED-SLOT-01, R-SCHED-SLOT-04, R-SCHED-SLOT-05, R-SCHED-NO-SHOW-01
- Реализует требования: [REQ-ROLE-09](../requirements/roles.md#req-role-09), [REQ-SLOT-01](../requirements/scheduling.md#req-slot-01)

## R-SCHED-SLOT-01 — Нельзя создать окно на прошедшее время

`draft` · guard

Достоверность: реализует требование REQ-SLOT-02 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

При создании окна время начала должно быть строго позже текущего (clock.now()), иначе DomainError «нельзя создать окно на прошедшее время».

- Реализация: [`services/scheduling/service.py::create_slot:33-34`](../../services/scheduling/service.py#L33)
- Тесты: `tests/test_scheduling.py::test_slot_in_past_forbidden`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-SITE-CHECKER-01
- Реализует требования: [REQ-SLOT-02](../requirements/scheduling.md#req-slot-02)

## R-SCHED-SLOT-02 — По умолчанию в окне столько мест, сколько максимум площадки

`draft` · calculation

Достоверность: реализует требование REQ-SLOT-03 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Если при создании окна число мест не передано, берётся max_capacity площадки из реплики scheduling.venue_limits. Если лимит для площадки не задан — DomainError «для площадки не задан максимум мест». Окна создаются по паре площадка+сфера, без признака цели (выдача/сдача).

- Реализация: [`services/scheduling/service.py::create_slot:35-41`](../../services/scheduling/service.py#L35)
- БД: [`trg_slot_capacity_limit`](../../migrations/versions/0001_initial.py#L259)
- Тесты: `tests/test_scheduling.py::test_checker_can_only_reduce_capacity`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-SLOT-03, R-SCHED-VENUE-LIMIT-01
- Реализует требования: [REQ-SLOT-03](../requirements/scheduling.md#req-slot-03)

## R-SCHED-SLOT-03 — Число мест в окне не больше максимума площадки (контроль в БД)

`draft` · invariant

Достоверность: реализует требование REQ-SLOT-03 · ⚠ открытый вопрос D-18: Нужна ли блокировка окна (SELECT … FOR UPDATE) или триггер на bookings? — уточни у пользователя

Триггер trg_slot_capacity_limit (функция check_slot_capacity) на INSERT и UPDATE OF capacity таблицы scheduling.slots отклоняет запись, если для площадки нет строки в venue_limits («no capacity limit for venue») или capacity больше max_capacity («slot capacity exceeds venue maximum»). В коде create_slot явно переданное число мест с максимумом не сверяется, так что ограничение держит только БД. CHECK slots_capacity_check требует capacity > 0.

- Реализация: [`services/scheduling/service.py::create_slot:40-42`](../../services/scheduling/service.py#L40)
- БД: [`trg_slot_capacity_limit`](../../migrations/versions/0001_initial.py#L259), [`check_slot_capacity`](../../migrations/versions/0001_initial.py#L244), [`slots_capacity_check`](../../migrations/versions/0001_initial.py#L240)
- Тесты: `tests/test_scheduling.py::test_slot_capacity_cannot_exceed_venue_maximum`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-SLOT-02, R-SCHED-VENUE-LIMIT-01
- Реализует требования: [REQ-SLOT-03](../requirements/scheduling.md#req-slot-03)

## R-SCHED-SLOT-04 — Проверяющий оператор может только уменьшить число мест в окне

`draft` · guard

Достоверность: реализует требование REQ-SLOT-03 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

reduce_capacity принимает только значение строго меньше текущего capacity окна («проверяющий оператор может только уменьшить число мест») и не меньше числа действующих записей в окне («в окне уже записано больше клиентов»). Действующие записи — bookings со статусом active.

- Реализация: [`services/scheduling/service.py::reduce_capacity:57-61`](../../services/scheduling/service.py#L57), [`services/scheduling/service.py::_active_bookings:46-49`](../../services/scheduling/service.py#L46)
- БД: [`trg_slot_capacity_limit`](../../migrations/versions/0001_initial.py#L259), [`slots_capacity_check`](../../migrations/versions/0001_initial.py#L240)
- Тесты: `tests/test_scheduling.py::test_checker_can_only_reduce_capacity`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-SITE-CHECKER-01, R-SCHED-SLOT-03
- Реализует требования: [REQ-SLOT-03](../requirements/scheduling.md#req-slot-03)

## R-SCHED-SLOT-05 — Удаление окна отменяет записи на него

`draft` · effect

Достоверность: реализует требование REQ-SLOT-04 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Окно удаляется мягко (slots.removed = true). Сначала все действующие записи на окно отменяются с причиной slot_removed, на каждую публикуется booking.cancelled. Из-за этого клиент и представитель получают письмо об отмене, в чат заявки пишется событие. Закреплённые книги и ссылка на запись остаются.

- Реализация: [`services/scheduling/service.py::remove_slot:71-76`](../../services/scheduling/service.py#L71), [`services/scheduling/service.py::_cancel:178-190`](../../services/scheduling/service.py#L178)
- Роли: Проверяющий оператор
- Связанные: R-SCHED-CANCEL-01, R-SCHED-SITE-CHECKER-01
- Реализует требования: [REQ-SLOT-04](../requirements/scheduling.md#req-slot-04)

## R-SCHED-VENUE-LIMIT-01 — Максимум мест площадки реплицируется из админки событием

`draft` · effect

Достоверность: реализует требование REQ-SLOT-03 · ⚠ открытый вопрос D-29: Уменьшать ли capacity существующих будущих окон, если администратор снизил максимум? — уточни у пользователя

Подписчик venue.settings_changed (публикует admin.set_venue_max_capacity) создаёт или обновляет строку scheduling.venue_limits с новым max_capacity. Уже созданные окна не пересчитываются: триггер срабатывает только на INSERT или изменение capacity, поэтому после снижения максимума окна со старым, большим числом мест остаются. CHECK требует max_capacity > 0.

- Реализация: [`services/scheduling/consumers.py::on_venue_settings_changed:35-40`](../../services/scheduling/consumers.py#L35)
- БД: [`venue_limits_max_capacity_check`](../../migrations/versions/0001_initial.py#L232)
- Роли: Администратор
- Связанные: R-SCHED-SLOT-02, R-SCHED-SLOT-03
- Реализует требования: [REQ-SLOT-03](../requirements/scheduling.md#req-slot-03)

## R-SCHED-LINK-01 — Ссылка на запись за книгами выдаётся при готовности к записи

`draft` · effect

Достоверность: реализует требование REQ-BOOK-01 · ⚠ открытый вопрос D-02: Как клиент получает токен ссылки — нужен ли тип письма «ссылка на запись» (за книгами и на сдачу), в том числе после смены площадки? — уточни у пользователя

На событие application.ready_for_booking (публикует mark_ready_for_booking при переходе в «Ожидает выдачи»: после проверки для debt/social, после полной оплаты для paid) модуль выпускает ссылку с purpose=issue.

- Реализация: [`services/scheduling/consumers.py::on_ready_for_booking:12-13`](../../services/scheduling/consumers.py#L12), [`services/scheduling/service.py::issue_link:79-86`](../../services/scheduling/service.py#L79)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SCHED-LINK-02, R-SCHED-ISSUE-03
- Реализует требования: [REQ-BOOK-01](../requirements/scheduling.md#req-book-01)

## R-SCHED-LINK-02 — У заявки только одна действующая ссылка

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

issue_link гасит все прежние ссылки заявки (active=false) и создаёт новую со случайным токеном (secrets.token_urlsafe(16)). БД гарантирует уникальность токена и не больше одной активной ссылки на заявку. purpose ограничен значениями issue/return.

- Реализация: [`services/scheduling/service.py::issue_link:79-86`](../../services/scheduling/service.py#L79)
- БД: [`uq_booking_links_one_active`](../../migrations/versions/0001_initial.py#L270), [`booking_links_token_key`](../../migrations/versions/0001_initial.py#L266), [`booking_links_purpose_check`](../../migrations/versions/0001_initial.py#L267)
- Роли: Система (события и фоновые задачи)
- Связанные: R-SCHED-LINK-01, R-SCHED-LINK-03

## R-SCHED-LINK-03 — Неактивная ссылка не даёт ни смотреть окна, ни записываться

`draft` · guard

Достоверность: по требованию REQ-BOOK-07 · ⚠ код расходится с требованием REQ-BOOK-07 (D-19): Схема: по закрытой заявке ссылка не работает. Код: на закрытие заявки (books_out->closed) модуль не подписан, ссылка на сдачу (purpose=retu… — уточни у пользователя

Просмотр свободных окон и запись по токену требуют существующую активную ссылку. Иначе — DomainError «ссылка на запись не действует». Ссылка гаснет при архивации, закрытии дублем, смене площадки и выпуске новой ссылки.

- Реализация: [`services/scheduling/service.py::_link_by_token:95-99`](../../services/scheduling/service.py#L95)
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-RESET-01, R-SCHED-LINK-02
- ⚠ Расходится с [REQ-BOOK-07](../requirements/scheduling.md#req-book-07): Схема: по закрытой заявке ссылка не работает. Код: на закрытие заявки (books_out->closed) модуль не подписан, ссылка на сдачу (purpose=return) после закрытия остаётся активной.

## R-SCHED-FREE-SLOTS-01 — По ссылке видны только будущие свободные окна площадки и сферы заявки

`draft` · guard

Достоверность: реализует требование REQ-SLOT-05 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

free_slots возвращает окна площадки и сферы заявки, кроме удалённых, только с началом позже текущего момента и где действующих записей меньше capacity. Список отсортирован по времени.

- Реализация: [`services/scheduling/service.py::free_slots:102-123`](../../services/scheduling/service.py#L102), [`services/scheduling/api.py::slots:27-31`](../../services/scheduling/api.py#L27)
- Тесты: `tests/test_scheduling.py::test_free_slots_hide_full_windows`
- Роли: Клиент, Представитель клиента
- Связанные: R-SCHED-BOOK-01
- Реализует требования: [REQ-SLOT-05](../requirements/scheduling.md#req-slot-05)

## R-SCHED-BOOK-01 — Запись только в своё, будущее и не заполненное окно

`draft` · guard

Достоверность: реализует требование REQ-BOOK-03 · ⚠ открытый вопрос D-18: Нужна ли блокировка окна (SELECT … FOR UPDATE) или триггер на bookings? — уточни у пользователя

book отклоняет удалённое окно (NotFound), окно другой площадки или сферы («окно не на площадке или не в сфере заявки»), окно в прошлом («нельзя записаться на прошедшее время») и окно, где действующих записей уже не меньше capacity («в окне нет свободных мест»).

- Реализация: [`services/scheduling/service.py::book:130-137`](../../services/scheduling/service.py#L130)
- Тесты: `tests/test_scheduling.py::test_booking_only_on_own_venue_and_sphere`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-FREE-SLOTS-01, R-SCHED-BOOK-02
- Реализует требования: [REQ-BOOK-03](../requirements/scheduling.md#req-book-03)
- Оговорка: Число свободных мест проверяется подсчётом в коде без блокировки. При параллельных записях окно можно переполнить: в БД нет ограничения на число записей в окне.

## R-SCHED-BOOK-02 — У заявки не больше одной действующей записи

`draft` · invariant

Достоверность: поведение кода без бизнес-требования · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Частичный уникальный индекс uq_bookings_one_active не даёт создать вторую запись со статусом active на ту же заявку. В коде book такой проверки нет: повторная запись упадёт на ошибке целостности БД, а не на DomainError. Перенос сначала отменяет старую запись.

- Реализация: [`services/scheduling/service.py::book:139-151`](../../services/scheduling/service.py#L139)
- БД: [`uq_bookings_one_active`](../../migrations/versions/0001_initial.py#L282), [`bookings_status_check`](../../migrations/versions/0001_initial.py#L278), [`bookings_purpose_check`](../../migrations/versions/0001_initial.py#L277)
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-RESCHEDULE-01

## R-SCHED-BOOK-03 — Цель записи берётся из ссылки, кто записал — из запроса

`draft` · invariant

Достоверность: по требованию REQ-BOOK-02 · ⚠ код расходится с требованием REQ-BOOK-02 (D-04): Схема: оператор записывает в системе, клиент и представитель — по ссылке. Код: публичный эндпоинт POST /links/{token}/bookings принимает bo… — уточни у пользователя

У записи purpose берётся из ссылки (issue или return), booked_by — из тела запроса (по умолчанию client). CHECK bookings_booked_by_check допускает только client, representative, operator.

- Реализация: [`services/scheduling/service.py::book:139-147`](../../services/scheduling/service.py#L139), [`services/scheduling/api.py::book:35-37`](../../services/scheduling/api.py#L35)
- БД: [`bookings_booked_by_check`](../../migrations/versions/0001_initial.py#L279)
- Роли: Клиент, Представитель клиента
- Связанные: R-SCHED-CANCEL-02
- ⚠ Расходится с [REQ-BOOK-02](../requirements/scheduling.md#req-book-02): Схема: оператор записывает в системе, клиент и представитель — по ссылке. Код: публичный эндпоинт POST /links/{token}/bookings принимает booked_by=operator от кого угодно с токеном.

## R-SCHED-HOLD-01 — Книги закрепляются за заявкой при записи за книгами

`draft` · effect

Достоверность: реализует требование REQ-SPHERE-03 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

При записи с purpose=issue каждая книга заявки (brief.book_ids) записывается в scheduling.holds через merge, поэтому повторная запись не создаёт дублей (PK application_id+book_id). Запись на сдачу (return) книги не закрепляет.

- Реализация: [`services/scheduling/service.py::book:148-150`](../../services/scheduling/service.py#L148)
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-HOLD-02, R-SCHED-RESET-01
- Реализует требования: [REQ-SPHERE-03](../requirements/venues.md#req-sphere-03)

## R-SCHED-HOLD-02 — Отмена, перенос и неявка не освобождают книги

`draft` · invariant

Достоверность: реализует требование REQ-SPHERE-03 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

_cancel меняет только статус записи и публикует событие, scheduling.holds не трогает. Книги освобождаются только в reset_bookings (смена площадки, архив, дубль) и при выдаче.

- Реализация: [`services/scheduling/service.py::_cancel:178-190`](../../services/scheduling/service.py#L178)
- Роли: Клиент, Представитель клиента, Оператор, Проверяющий оператор
- Связанные: R-SCHED-HOLD-01, R-SCHED-ISSUE-03
- Реализует требования: [REQ-SPHERE-03](../requirements/venues.md#req-sphere-03)

## R-SCHED-BOOK-EVENT-01 — Запись на визит — письмо клиенту и представителю, событие в чате

`verified` · effect

Достоверность: реализует требование REQ-MAIL-02, REQ-CHAT-04 · проверено человеком 2026-10-23, с тех пор не менялось

После записи публикуется booking.created (application_id, booking_id, venue_id, starts_at, purpose). Подписчик notifications отправляет письмо типа booking получателям заявки по шаблону площадки и группы вида заявки. Обработчик chat пишет в чат «Запись на {starts_at}».

- Реализация: [`services/scheduling/service.py::book:152-162`](../../services/scheduling/service.py#L152), [`services/notifications/consumers.py::on_booking_created:10-17`](../../services/notifications/consumers.py#L10), [`services/chat/consumers.py::_handler:23-27`](../../services/chat/consumers.py#L23)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`, `tests/test_notifications.py::test_social_uses_social_templates`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-CANCEL-01
- Реализует требования: [REQ-MAIL-02](../requirements/notifications.md#req-mail-02), [REQ-CHAT-04](../requirements/chat.md#req-chat-04)

## R-SCHED-OPERATOR-BOOK-01 — Оператор записывает клиента только по своей заявке и при активной ссылке

`draft` · permission

Достоверность: реализует требование REQ-BOOK-02, REQ-ROLE-04 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

book_by_operator требует, чтобы заявка была закреплена за этим оператором («заявка закреплена за другим оператором») и у неё была действующая ссылка («по заявке нет действующей ссылки на запись»). Дальше выполняется обычная запись с booked_by=operator.

- Реализация: [`services/scheduling/service.py::book_by_operator:169-175`](../../services/scheduling/service.py#L169)
- Роли: Оператор
- Связанные: R-SCHED-BOOK-01
- Реализует требования: [REQ-BOOK-02](../requirements/scheduling.md#req-book-02), [REQ-ROLE-04](../requirements/roles.md#req-role-04)

## R-SCHED-CANCEL-01 — Отмена записи — письмо об отмене и событие в чате

`draft` · effect

Достоверность: реализует требование REQ-MAIL-02, REQ-CHAT-04 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Любая отмена (клиентом, оператором, удалением окна, неявкой, сбросом) идёт через _cancel. Статус записи становится no_show при причине no_show, иначе cancelled. Публикуется booking.cancelled с причиной: notifications отправляет письмо типа cancel, chat пишет «Запись на … отменена (reason)».

- Реализация: [`services/scheduling/service.py::_cancel:178-190`](../../services/scheduling/service.py#L178), [`services/notifications/consumers.py::on_booking_cancelled:21-28`](../../services/notifications/consumers.py#L21), [`services/chat/consumers.py::_handler:23-27`](../../services/chat/consumers.py#L23)
- БД: [`bookings_status_check`](../../migrations/versions/0001_initial.py#L278)
- Тесты: `tests/test_notifications.py::test_reschedule_sends_cancel_and_booking`
- Роли: Клиент, Представитель клиента, Оператор, Проверяющий оператор, Система (события и фоновые задачи)
- Связанные: R-SCHED-BOOK-EVENT-01, R-SCHED-NO-SHOW-01, R-SCHED-SLOT-05
- Реализует требования: [REQ-MAIL-02](../requirements/notifications.md#req-mail-02), [REQ-CHAT-04](../requirements/chat.md#req-chat-04)

## R-SCHED-CANCEL-02 — Клиент и представитель не отменяют визит менее чем за два дня

`draft` · guard

Достоверность: по требованию REQ-BOOK-04 · ⚠ код расходится с требованием REQ-BOOK-04 (D-04): Схема: менее чем за два дня отменить или перенести визит может только оператор. Код: роль определяется параметром by из запроса DELETE /boo… — уточни у пользователя

Отменить можно только действующую запись («запись не действует»). Если отменяет сторона клиента (CLIENT_SIDE = client, representative) и до начала окна меньше CLIENT_RESCHEDULE_MIN_DAYS суток (считается разница во времени, а не календарные даты) — DomainError «менее чем за два дня перенести или отменить визит может только оператор». Для остальных значений by ограничения нет.

- Реализация: [`services/scheduling/service.py::cancel_booking:195-203`](../../services/scheduling/service.py#L195), [`services/scheduling/api.py::cancel:41-42`](../../services/scheduling/api.py#L41)
- Настройки: `libs/settings.py::CLIENT_RESCHEDULE_MIN_DAYS`, `services/scheduling/service.py::CLIENT_SIDE`
- Тесты: `tests/test_scheduling.py::test_client_cannot_cancel_less_than_two_days_before`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-RESCHEDULE-01, R-SCHED-BOOK-03
- ⚠ Расходится с [REQ-BOOK-04](../requirements/scheduling.md#req-book-04): Схема: менее чем за два дня отменить или перенести визит может только оператор. Код: роль определяется параметром by из запроса DELETE /bookings/{booking_id}?by=..., без проверки, кто вызывает. Любой, передав by=operator, обходит ограничение, и личность оператора не сверяется. Текст ошибки «за два дня» зашит в строку и не зависит от настройки.

## R-SCHED-RESCHEDULE-01 — Перенос — это отмена и новая запись

`draft` · effect

Достоверность: реализует требование REQ-BOOK-04 · ⚠ открытый вопрос D-04: Нужно ли закрыть публичным эндпоинтам значения by и booked_by, отличные от client и representative, и пускать оператора только через book_b… — уточни у пользователя

reschedule отменяет текущую запись через cancel_booking (с проверкой двух дней для стороны клиента) и записывает на новое окно по действующей ссылке заявки, с тем же booked_by. Уходят два письма: об отмене и о новой записи. Отдельного события переноса нет.

- Реализация: [`services/scheduling/service.py::reschedule:206-210`](../../services/scheduling/service.py#L206)
- БД: [`uq_bookings_one_active`](../../migrations/versions/0001_initial.py#L282)
- Настройки: `libs/settings.py::CLIENT_RESCHEDULE_MIN_DAYS`
- Тесты: `tests/test_notifications.py::test_reschedule_sends_cancel_and_booking`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-SCHED-CANCEL-02, R-SCHED-CANCEL-01, R-SCHED-BOOK-EVENT-01
- Реализует требования: [REQ-BOOK-04](../requirements/scheduling.md#req-book-04)

## R-SCHED-NO-SHOW-01 — Неявка отменяет запись, клиент может записаться снова

`draft` · effect

Достоверность: реализует требование REQ-BOOK-05 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Проверяющий оператор площадки окна отмечает неявку по действующей записи: статус no_show, публикуется booking.cancelled с reason=no_show (письмо об отмене, событие в чате). Ссылка и закреплённые книги остаются, этап заявки не меняется, клиент может записаться снова.

- Реализация: [`services/scheduling/service.py::mark_no_show:213-220`](../../services/scheduling/service.py#L213)
- БД: [`bookings_status_check`](../../migrations/versions/0001_initial.py#L278)
- Тесты: `tests/test_scheduling.py::test_no_show_cancels_booking_and_allows_rebooking`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-CANCEL-01, R-SCHED-HOLD-02
- Реализует требования: [REQ-BOOK-05](../requirements/scheduling.md#req-book-05)

## R-SCHED-ISSUE-01 — Выдача книг — только по записи, на этапе «Ожидает выдачи», в выбранную дату

`draft` · guard

Достоверность: реализует требование REQ-ISSUE-01 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

issue_books требует действующую запись с purpose=issue («нет действующей записи за книгами»). Выдаёт проверяющий оператор площадки заявки («книги выдаёт проверяющий оператор площадки заявки»). Заявка должна быть на этапе awaiting_issue («выдача возможна только на этапе «Ожидает выдачи»»), а дата окна — совпадать с текущей датой («выдача только в выбранную дату»).

- Реализация: [`services/scheduling/service.py::issue_books:224-235`](../../services/scheduling/service.py#L224)
- Тесты: `tests/test_paid_flow.py::test_issue_only_on_booked_date`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-ISSUE-02, R-SCHED-ISSUE-03
- Реализует требования: [REQ-ISSUE-01](../requirements/loans.md#req-issue-01)

## R-SCHED-ISSUE-02 — Срок возврата — LOAN_PERIOD_DAYS от момента выдачи

`draft` · calculation

Достоверность: реализует требование REQ-RETURN-01 · ⚠ открытый вопрос D-16: Считать ли просрочку по loans.due_at и начислять ли штраф при позднем возврате в return_book? — уточни у пользователя

На каждую книгу заявки создаётся выдача (loan) со статусом out, issued_at = now и due_at = now + LOAN_PERIOD_DAYS (30) дней.

- Реализация: [`services/scheduling/service.py::issue_books:237-247`](../../services/scheduling/service.py#L237)
- БД: [`loans_status_check`](../../migrations/versions/0001_initial.py#L298)
- Настройки: `libs/settings.py::LOAN_PERIOD_DAYS`
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-OVERDUE-01
- Реализует требования: [REQ-RETURN-01](../requirements/loans.md#req-return-01)

## R-SCHED-ISSUE-03 — После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента»

`draft` · effect

Достоверность: реализует требование REQ-PROC-01, REQ-BOOK-01 · ⚠ код расходится с требованием REQ-SPHERE-03 (D-25): Схема (§8): книги освобождаются после отметки о возврате. Код: holds удаляются уже при выдаче. Открытые выдачи учитываются только в schedul… — уточни у пользователя

После выдачи запись получает статус done, все holds заявки удаляются и выпускается новая ссылка с purpose=return (прежняя гаснет). Публикуется books.issued: подписчик applications переводит заявку awaiting_issue->books_out от имени site_checker.

- Реализация: [`services/scheduling/service.py::issue_books:248-251`](../../services/scheduling/service.py#L248), [`services/applications/consumers.py::on_books_issued:67-69`](../../services/applications/consumers.py#L67), [`awaiting_issue->books_out`](../../bpm/application_process.yaml#L34)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`, `tests/test_kinds.py::test_social_application_skips_invoice`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-ISSUE-01, R-SCHED-HOLD-02, R-SCHED-LINK-02
- Реализует требования: [REQ-PROC-01](../requirements/process.md#req-proc-01), [REQ-BOOK-01](../requirements/scheduling.md#req-book-01)
- ⚠ Расходится с [REQ-SPHERE-03](../requirements/venues.md#req-sphere-03): Схема (§8): книги освобождаются после отметки о возврате. Код: holds удаляются уже при выдаче. Открытые выдачи учитываются только в scheduling.loans.

## R-SCHED-RETURN-01 — Возврат и утерю отмечает проверяющий оператор площадки заявки по каждой книге

`draft` · guard

Достоверность: реализует требование REQ-RETURN-02 · ⚠ открытый вопрос D-19: Гасить ли ссылку и записи на сдачу при закрытии заявки (или при возврате последней книги)? — уточни у пользователя

Возврат и утеря отмечаются по отдельной выдаче. Это может только проверяющий оператор площадки заявки («книги принимает проверяющий оператор площадки заявки») и только для выдачи в статусе out («книга уже возвращена или списана»). Возврат ставит status=returned, returned_at и флаг damaged; утеря ставит status=lost.

- Реализация: [`services/scheduling/service.py::_loan_for_checker:255-264`](../../services/scheduling/service.py#L255), [`services/scheduling/service.py::return_book:270-276`](../../services/scheduling/service.py#L270), [`services/scheduling/service.py::mark_lost:279-283`](../../services/scheduling/service.py#L279)
- БД: [`loans_status_check`](../../migrations/versions/0001_initial.py#L298)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-FINE-01, R-SCHED-CLOSE-01
- Реализует требования: [REQ-RETURN-02](../requirements/loans.md#req-return-02)
- Оговорка: Возврат не связан с записью на сдачу: return_book не требует записи и не закрывает её, поэтому запись с purpose=return остаётся в статусе active после приёма книг.

## R-SCHED-FINE-01 — Порча и утеря книги порождают штраф в billing

`verified` · effect

Достоверность: реализует требование REQ-FINE-03 · ⚠ код расходится с требованием REQ-CHAT-04 (D-26): Схема (§15): в чат попадают все события заявки. Код: loan.damaged и loan.lost в EVENT_TEXT чата нет, в чат они не попадают. — уточни у пользователя

При возврате с damaged=true публикуется loan.damaged, при отметке утери — loan.lost. Подписчики billing создают штраф заявки с видом damaged или lost (create_fine). Эти события в чат не пишутся.

- Реализация: [`services/scheduling/service.py::return_book:274-275`](../../services/scheduling/service.py#L274), [`services/scheduling/service.py::mark_lost:282`](../../services/scheduling/service.py#L282), [`services/billing/consumers.py::on_loan_damaged:48-50`](../../services/billing/consumers.py#L48), [`services/billing/consumers.py::on_loan_lost:43-45`](../../services/billing/consumers.py#L43)
- Роли: Проверяющий оператор
- Связанные: R-SCHED-RETURN-01, R-SCHED-OVERDUE-01
- Реализует требования: [REQ-FINE-03](../requirements/loans.md#req-fine-03)
- ⚠ Расходится с [REQ-CHAT-04](../requirements/chat.md#req-chat-04): Схема (§15): в чат попадают все события заявки. Код: loan.damaged и loan.lost в EVENT_TEXT чата нет, в чат они не попадают.

## R-SCHED-OVERDUE-01 — Фоновая задача отмечает просрочку через 30 дней с выдачи и создаёт штраф

`draft` · timer

Достоверность: по требованию REQ-FINE-04 · ⚠ код расходится с требованием REQ-FINE-04 (D-16, D-17): Срок просрочки зашит литералом timedelta(days=30), а не берётся из LOAN_PERIOD_DAYS или loans.due_at. Если настройку изменить, due_at и мом… — уточни у пользователя

flag_overdue выбирает выдачи со статусом out без флага overdue_flagged, у которых issued_at < now - 30 дней. Каждой ставится overdue_flagged=true (один раз) и публикуется loan.overdue: billing создаёт штраф overdue, chat пишет «Срыв срока возврата книги {book_id}». Срок задан литералом 30, а не настройкой LOAN_PERIOD_DAYS, и считается от issued_at, а не от due_at.

- Реализация: [`services/scheduling/jobs.py::flag_overdue:10-27`](../../services/scheduling/jobs.py#L10), [`services/billing/consumers.py::on_loan_overdue:38-40`](../../services/billing/consumers.py#L38)
- Настройки: `libs/settings.py::LOAN_PERIOD_DAYS`
- Роли: Система (события и фоновые задачи)
- Связанные: R-SCHED-ISSUE-02, R-SCHED-FINE-01
- ⚠ Расходится с [REQ-FINE-04](../requirements/loans.md#req-fine-04): Срок просрочки зашит литералом timedelta(days=30), а не берётся из LOAN_PERIOD_DAYS или loans.due_at. Если настройку изменить, due_at и момент начисления штрафа разойдутся. Схема: «месяц с выдачи», а не фиксированные 30 дней. Книга, возвращённая с опозданием до запуска задачи, штраф не получает.

## R-SCHED-RESET-01 — Архив и закрытие дублем сбрасывают записи, книги и ссылку

`draft` · effect

Достоверность: реализует требование REQ-ARCH-07, REQ-DEDUP-02 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

На application.archived и application.closed_duplicate вызывается reset_bookings: действующие записи отменяются с причиной archived или duplicate (booking.cancelled, письма об отмене, чат), holds заявки удаляются, все ссылки гаснут.

- Реализация: [`services/scheduling/consumers.py::on_archived:25-26`](../../services/scheduling/consumers.py#L25), [`services/scheduling/consumers.py::on_closed_duplicate:30-31`](../../services/scheduling/consumers.py#L30), [`services/scheduling/service.py::reset_bookings:286-299`](../../services/scheduling/service.py#L286)
- Роли: Система (события и фоновые задачи)
- Связанные: R-SCHED-LINK-03, R-SCHED-VENUE-CHANGE-01
- Реализует требования: [REQ-ARCH-07](../requirements/archive.md#req-arch-07), [REQ-DEDUP-02](../requirements/clients.md#req-dedup-02)

## R-SCHED-VENUE-CHANGE-01 — Смена площадки отменяет запись и выдаёт новую ссылку

`draft` · effect

Достоверность: реализует требование REQ-VENUE-05 · ⚠ код расходится с требованием REQ-VENUE-03 (D-09): Схема: у социальных заявок и заявок в долг площадку меняют только до формирования ссылки, после выдачи — никогда. Код change_venue блокируе… — уточни у пользователя

На application.venue_changed модуль сбрасывает записи (reason=venue_changed: письмо об отмене, освобождение книг, гашение ссылок). Если заявка на этапе awaiting_issue, выпускается новая ссылка purpose=issue. Проверяющий оператор новой площадки назначается в applications.change_venue.

- Реализация: [`services/scheduling/consumers.py::on_venue_changed:17-21`](../../services/scheduling/consumers.py#L17), [`services/scheduling/service.py::reset_bookings:286-299`](../../services/scheduling/service.py#L286)
- Роли: Оператор
- Связанные: R-SCHED-RESET-01, R-SCHED-LINK-01
- Реализует требования: [REQ-VENUE-05](../requirements/venues.md#req-venue-05)
- ⚠ Расходится с [REQ-VENUE-03](../requirements/venues.md#req-venue-03): Схема: у социальных заявок и заявок в долг площадку меняют только до формирования ссылки, после выдачи — никогда. Код change_venue блокирует смену только для paid на awaiting_issue и books_out. У debt/social на этапе books_out смена проходит: записи на сдачу отменяются, ссылка на сдачу гаснет, а новая не выпускается (выпуск только при awaiting_issue) — клиент не может записаться на сдачу. Письмо об отмене уходит по шаблону старой площадки (venue_id окна).

## R-SCHED-CLOSE-01 — Заявку нельзя закрыть, пока есть книги на руках

`draft` · guard

Достоверность: реализует требование REQ-PROC-09 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Guard settled перехода books_out->closed берёт число выдач со статусом out через scheduling.public.open_loans_count. Закрытие возможно только при нуле открытых выдач и нуле непогашенных штрафов. Возвращённые (returned) и утерянные (lost) книги не мешают закрытию.

- Реализация: [`services/scheduling/public.py::open_loans_count:7-10`](../../services/scheduling/public.py#L7), [`services/applications/guards.py::settled:10-14`](../../services/applications/guards.py#L10), [`books_out->closed`](../../bpm/application_process.yaml#L35), [`guard:settled`](../../bpm/application_process.yaml)
- Тесты: `tests/test_paid_flow.py::test_cannot_close_with_books_out`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-SCHED-RETURN-01, R-SCHED-FINE-01
- Реализует требования: [REQ-PROC-09](../requirements/process.md#req-proc-09)
