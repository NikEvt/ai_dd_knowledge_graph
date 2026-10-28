<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: applications

Источник: [`knowledge/rules/applications.yaml`](../../knowledge/rules/applications.yaml)

## R-APP-CREATE-01 — Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя

`draft` · calculation

Достоверность: реализует требование REQ-KIND-01 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 2 тестами

При создании заявки вид задаётся один раз: если оператор отметил заявку социальной — social, иначе debt, если представителю разрешено работать в долг (debt_allowed), иначе paid. Последующая смена debt_allowed у представителя на вид существующих заявок не влияет. Допустимые значения вида ограничены CHECK в БД.

- Реализация: [`services/applications/service.py::create_application:90-93`](../../services/applications/service.py#L90)
- БД: [`applications_kind_check`](../../migrations/versions/0001_initial.py#L85)
- Тесты: `tests/test_kinds.py::test_debt_kind_comes_from_representative`, `tests/test_kinds.py::test_social_application_skips_invoice`
- Роли: Оператор
- Связанные: R-APP-ADMIN-01
- Реализует требования: [REQ-KIND-01](../requirements/process.md#req-kind-01)

## R-APP-CREATE-02 — Сфера заявки должна быть активна на площадке

`draft` · guard

Достоверность: реализует требование REQ-SPHERE-01, REQ-VENUE-04, REQ-SPHERE-04 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Создание заявки, смена площадки и смена площадки при возврате из архива требуют, чтобы на площадке была запись venue_spheres для сферы заявки с active=true; иначе DomainError «на площадке нет сферы заявки».

- Реализация: [`services/applications/service.py::_check_sphere_at_venue:44-46`](../../services/applications/service.py#L44), [`services/applications/service.py::create_application:87-87`](../../services/applications/service.py#L87)
- Тесты: `tests/test_venue_change.py::test_new_venue_must_have_sphere`
- Роли: Оператор
- Связанные: R-APP-ADMIN-04, R-APP-VENUE-CHANGE-01, R-APP-UNARCHIVE-02
- Реализует требования: [REQ-SPHERE-01](../requirements/venues.md#req-sphere-01), [REQ-VENUE-04](../requirements/venues.md#req-venue-04), [REQ-SPHERE-04](../requirements/venues.md#req-sphere-04)

## R-APP-CREATE-03 — В заявке есть книги, и все они из сферы заявки и прайса площадки

`draft` · guard

Достоверность: реализует требование REQ-SPHERE-02 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Список книг не может быть пустым («в заявке нет книг»); каждая книга должна принадлежать сфере заявки и иметь цену в прайсе площадки заявки, иначе DomainError. Проверка выполняется при создании, смене книг, смене площадки и при возврате из архива с новыми площадкой или книгами.

- Реализация: [`services/applications/service.py::_check_books:50-60`](../../services/applications/service.py#L50)
- БД: [`prices_price_check`](../../migrations/versions/0001_initial.py#L58)
- Роли: Оператор
- Связанные: R-APP-CREATE-02, R-APP-BOOKS-01
- Реализует требования: [REQ-SPHERE-02](../requirements/venues.md#req-sphere-02)

## R-APP-CREATE-04 — При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка

`draft` · effect

Достоверность: реализует требование REQ-ROLE-08, REQ-ARCH-11 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Новая заявка создаётся в этапе draft; оператор-создатель закрепляется за ней, site_checker_id берётся из площадки, создаётся попытка №1 с датой начала. Номер попытки уникален в пределах заявки (UNIQUE в БД).

- Реализация: [`services/applications/service.py::create_application:94-109`](../../services/applications/service.py#L94)
- БД: [`attempts_application_id_no_key`](../../migrations/versions/0001_initial.py#L109), [`applications_stage_check`](../../migrations/versions/0001_initial.py#L86)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Оператор
- Связанные: R-APP-ACCESS-01
- Реализует требования: [REQ-ROLE-08](../requirements/roles.md#req-role-08), [REQ-ARCH-11](../requirements/archive.md#req-arch-11)

## R-APP-ACCESS-01 — Оператор работает только со своими заявками

`draft` · permission

Достоверность: реализует требование REQ-ROLE-04 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

Отправка на проверку, смена площадки, смена книг, ручной архив и возврат из архива доступны только оператору, закреплённому за заявкой (operator_id); иначе AccessDenied «заявка закреплена за другим оператором».

- Реализация: [`services/applications/service.py::_require_operator:39-40`](../../services/applications/service.py#L39), [`services/applications/service.py::submit_for_review:115-115`](../../services/applications/service.py#L115), [`services/applications/service.py::change_venue:203-203`](../../services/applications/service.py#L203), [`services/applications/service.py::change_books:238-238`](../../services/applications/service.py#L238), [`services/applications/service.py::archive:255-256`](../../services/applications/service.py#L255), [`services/applications/service.py::unarchive:274-274`](../../services/applications/service.py#L274)
- Тесты: `tests/test_review.py::test_operator_works_only_with_own_applications`
- Роли: Оператор
- Реализует требования: [REQ-ROLE-04](../requirements/roles.md#req-role-04)

## R-APP-CORE-01 — Сферу и представителя заявки сменить нельзя

`verified` · invariant

Достоверность: реализует требование REQ-PROC-04 · проверено человеком 2026-10-23, с тех пор не менялось

Триггер БД запрещает UPDATE sphere_id и representative_id заявки (check_violation). В коде сервиса нет операций, меняющих эти поля; для другой сферы или представителя создаётся новая заявка.

- БД: [`trg_applications_core_immutable`](../../migrations/versions/0001_initial.py#L121), [`forbid_core_change`](../../migrations/versions/0001_initial.py#L112)
- Связанные: R-APP-UNARCHIVE-02
- Реализует требования: [REQ-PROC-04](../requirements/process.md#req-proc-04)

## R-APP-BOOKS-01 — Книги меняют только в черновике или на доработке

`draft` · guard

Достоверность: реализует требование REQ-PROC-07 · ⚠ код расходится с требованием REQ-INV-07 (D-25): Схема (§4): если после выставления счёта до оплаты меняются книги, счёт аннулируется и выставляется заново. Код: после проверки книги меняю… — уточни у пользователя

Оператор заявки может заменить список книг только на этапах draft и needs_rework; иначе DomainError «книги меняют в черновике или на доработке». Новые книги проходят проверку сферы и прайса.

- Реализация: [`services/applications/service.py::change_books:239-242`](../../services/applications/service.py#L239)
- Роли: Оператор
- Связанные: R-APP-CREATE-03, R-APP-UNARCHIVE-02
- Реализует требования: [REQ-PROC-07](../requirements/process.md#req-proc-07)
- ⚠ Расходится с [REQ-INV-07](../requirements/billing.md#req-inv-07): Схема (§4): если после выставления счёта до оплаты меняются книги, счёт аннулируется и выставляется заново. Код: после проверки книги меняются только через архив и возврат из него (R-APP-UNARCHIVE-02); других путей смены книг нет.

## R-APP-REVIEW-01 — Отправка на проверку фиксирует начало проверки один раз

`draft` · effect

Достоверность: реализует требование REQ-ARCH-01 · ⚠ открытый вопрос D-06: С какого момента считать месяц для повторной проверки после обновления данных клиента — с первой проверки или с возврата на проверку? — уточни у пользователя

Оператор заявки переводит её из draft или needs_rework в on_review. Поле review_started_at заполняется только при первой отправке и не сбрасывается при возврате с доработки — от него считается срок автоархива (сбрасывается только при возврате из архива).

- Реализация: [`services/applications/service.py::submit_for_review:116-118`](../../services/applications/service.py#L116), [`draft->on_review`](../../bpm/application_process.yaml#L20), [`needs_rework->on_review`](../../bpm/application_process.yaml#L20)
- Тесты: `tests/test_review.py::test_incomplete_client_goes_to_rework`, `tests/test_archive.py::test_stuck_review_goes_to_archive_after_month`
- Роли: Оператор
- Связанные: R-APP-ARCHIVE-01, R-APP-ACCESS-01
- Реализует требования: [REQ-ARCH-01](../requirements/archive.md#req-arch-01)

## R-APP-REVIEW-02 — Проверяющего назначают только до прохождения проверки

`draft` · permission

Достоверность: по требованию REQ-ROLE-05 · ⚠ код расходится с требованием REQ-ROLE-05 (D-03): Схема: назначает и переназначает только руководитель проверяющих. Код: роль вызывающего не проверяется, назначить может любой вызывающий. — уточни у пользователя

Назначить или переназначить проверяющего можно, пока заявка в draft, on_review или needs_rework; иначе DomainError «проверяющего назначают до прохождения проверки». Проверка роли (руководитель проверяющих) в коде отсутствует — указана только в docstring.

- Реализация: [`services/applications/service.py::assign_reviewer:125-127`](../../services/applications/service.py#L125)
- Тесты: `tests/test_review.py::test_only_assigned_reviewer_approves`
- Роли: Руководитель проверяющих
- Связанные: R-APP-REVIEW-03
- ⚠ Расходится с [REQ-ROLE-05](../requirements/roles.md#req-role-05): Схема: назначает и переназначает только руководитель проверяющих. Код: роль вызывающего не проверяется, назначить может любой вызывающий.

## R-APP-REVIEW-03 — Подтверждает или возвращает заявку только назначенный проверяющий

`draft` · permission

Достоверность: реализует требование REQ-ROLE-06, REQ-PROC-03 · извлечено ИИ из кода, подкреплено кодом и 3 тестами

Без назначенного проверяющего заявку подтвердить нельзя (DomainError «на заявку не назначен проверяющий»); подтверждение и возврат на доработку выполняет только reviewer_id заявки, иначе AccessDenied «заявку проверяет другой проверяющий». Возврат переводит on_review -> needs_rework.

- Реализация: [`services/applications/service.py::approve:169-172`](../../services/applications/service.py#L169), [`services/applications/service.py::return_for_rework:193-195`](../../services/applications/service.py#L193), [`on_review->needs_rework`](../../bpm/application_process.yaml#L21)
- Тесты: `tests/test_review.py::test_approve_requires_assigned_reviewer`, `tests/test_review.py::test_only_assigned_reviewer_approves`, `tests/test_review.py::test_incomplete_client_goes_to_rework`
- Роли: Проверяющий
- Связанные: R-APP-REVIEW-02, R-APP-REVIEW-04
- Реализует требования: [REQ-ROLE-06](../requirements/roles.md#req-role-06), [REQ-PROC-03](../requirements/process.md#req-proc-03)

## R-APP-REVIEW-04 — Заявку нельзя подтвердить без ФИО, паспорта и даты рождения клиента

`draft` · guard

Достоверность: реализует требование REQ-CLIENT-03 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

При подтверждении проверяются обязательные поля клиента из REQUIRED_CLIENT_FIELDS (full_name, passport, birth_date); если чего-то нет — DomainError «не хватает данных клиента: …».

- Реализация: [`services/applications/service.py::approve:173-175`](../../services/applications/service.py#L173), [`services/applications/review.py::missing_client_fields:6-7`](../../services/applications/review.py#L6)
- Настройки: `services/applications/review.py::REQUIRED_CLIENT_FIELDS`
- Тесты: `tests/test_review.py::test_incomplete_client_goes_to_rework`
- Роли: Проверяющий
- Связанные: R-APP-REVIEW-03, R-APP-CLIENT-02
- Реализует требования: [REQ-CLIENT-03](../requirements/clients.md#req-client-03)

## R-APP-REVIEW-05 — Этап после проверки зависит от вида заявки и наличия действующего счёта

`verified` · effect

Достоверность: реализует требование REQ-PROC-01 · проверено человеком 2026-10-23, с тех пор не менялось

После подтверждения платная заявка уходит в awaiting_payment, если по ней есть действующий счёт за книги (после возврата из архива или повторной проверки), иначе в awaiting_invoice; заявки в долг и социальные сразу уходят в awaiting_issue и становятся готовыми к записи. Публикуется application.review_passed.

- Реализация: [`services/applications/service.py::approve:177-185`](../../services/applications/service.py#L177), [`on_review->awaiting_invoice`](../../bpm/application_process.yaml#L23), [`on_review->awaiting_payment`](../../bpm/application_process.yaml#L24), [`on_review->awaiting_issue`](../../bpm/application_process.yaml#L25), [`guard:has_active_invoice`](../../bpm/application_process.yaml)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`, `tests/test_kinds.py::test_debt_application_skips_invoice`, `tests/test_kinds.py::test_social_application_skips_invoice`
- Роли: Проверяющий
- Связанные: R-APP-BOOKING-01, R-APP-DEDUP-01
- Реализует требования: [REQ-PROC-01](../requirements/process.md#req-proc-01)

## R-APP-BOOKING-01 — Готовность к записи фиксируется и запускает выдачу ссылки на запись

`draft` · effect

Достоверность: реализует требование REQ-PROC-08, REQ-BOOK-01 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

При переходе в awaiting_issue (после проверки debt/social или после полной оплаты paid) заполняется booking_reached_at (один раз) и публикуется application.ready_for_booking; scheduling по нему формирует публичную ссылку на запись (issue_link).

- Реализация: [`services/applications/service.py::mark_ready_for_booking:158-164`](../../services/applications/service.py#L158), [`services/scheduling/consumers.py::on_ready_for_booking:13-13`](../../services/scheduling/consumers.py#L13)
- Тесты: `tests/test_kinds.py::test_debt_application_skips_invoice`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-REVIEW-05, R-APP-PAY-03, R-APP-UNARCHIVE-02
- Реализует требования: [REQ-PROC-08](../requirements/process.md#req-proc-08), [REQ-BOOK-01](../requirements/scheduling.md#req-book-01)

## R-APP-CLIENT-01 — Данные клиента обновляет проверяющий заявки-источника

`draft` · permission

Достоверность: по требованию REQ-CLIENT-02 · ⚠ код расходится с требованием REQ-CLIENT-02 (D-03): Схема: данные клиента обновляет только проверяющий. Код: при вызове без source_application_id роль и закрепление не проверяются — обновить … — уточни у пользователя

Если указана заявка-источник, обновить клиента может только её проверяющий (AccessDenied иначе). Разрешены только поля CLIENT_EDITABLE_FIELDS (full_name, passport, birth_date, email), прочие — DomainError «неизвестные поля клиента». Без source_application_id проверка прав не выполняется.

- Реализация: [`services/applications/service.py::update_client:140-153`](../../services/applications/service.py#L140)
- Настройки: `services/applications/service.py::CLIENT_EDITABLE_FIELDS`
- Тесты: `tests/test_review.py::test_incomplete_client_goes_to_rework`
- Роли: Проверяющий
- Связанные: R-APP-CLIENT-02
- ⚠ Расходится с [REQ-CLIENT-02](../requirements/clients.md#req-client-02): Схема: данные клиента обновляет только проверяющий. Код: при вызове без source_application_id роль и закрепление не проверяются — обновить данные может кто угодно.

## R-APP-CLIENT-02 — Изменение ФИО, паспорта или даты рождения клиента публикует client.updated (слушатель ORM)

`draft` · effect

Достоверность: реализует требование REQ-CLIENT-04 · извлечено ИИ из кода, есть код, нет тестов — сверь с кодом

Слушатель before_flush при изменении полей TRACKED_FIELDS (full_name, passport, birth_date) неявно ставит clients.updated_at и публикует client.updated с полями и source_application_id (из session.info). Изменение email событие не порождает.

- Реализация: [`services/applications/listeners.py::_domain_events:23-36`](../../services/applications/listeners.py#L23)
- Настройки: `services/applications/listeners.py::TRACKED_FIELDS`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-CLIENT-01, R-APP-CLIENT-03
- Реализует требования: [REQ-CLIENT-04](../requirements/clients.md#req-client-04)

## R-APP-CLIENT-03 — Обновление клиента возвращает его заявки из ожидания счёта или оплаты на проверку

`draft` · effect

Достоверность: реализует требование REQ-CLIENT-04 · ⚠ открытый вопрос D-06: С какого момента считать месяц для повторной проверки после обновления данных клиента — с первой проверки или с возврата на проверку? — уточни у пользователя

По client.updated все заявки клиента на этапах awaiting_invoice и awaiting_payment, кроме заявки-источника, переводятся системой в on_review. Заявки на awaiting_issue и дальше не перепроверяются; review_started_at при этом не сбрасывается.

- Реализация: [`services/applications/consumers.py::on_client_updated:52-63`](../../services/applications/consumers.py#L52), [`awaiting_invoice->on_review`](../../bpm/application_process.yaml#L32), [`awaiting_payment->on_review`](../../bpm/application_process.yaml#L32)
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-CLIENT-02, R-APP-ARCHIVE-01
- Реализует требования: [REQ-CLIENT-04](../requirements/clients.md#req-client-04)
- Оговорка: Схема: перепроверка не должна приводить к потере заявки. Код: review_started_at остаётся от первой проверки, поэтому возвращённая на проверку заявка, у которой проверка началась больше REVIEW_ARCHIVE_DAYS назад, при ближайшем запуске archive_stale уходит в архив с outcome=no_data.

## R-APP-PAY-01 — Выставление счёта за книги переводит заявку в ожидание оплаты

`draft` · effect

Достоверность: реализует требование REQ-PROC-01 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

По invoice.issued с invoice_kind=books заявка на этапе awaiting_invoice переводится в awaiting_payment (actor accountant). Счета на штраф этап не меняют.

- Реализация: [`services/applications/consumers.py::on_invoice_issued:14-18`](../../services/applications/consumers.py#L14), [`awaiting_invoice->awaiting_payment`](../../bpm/application_process.yaml#L27)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Бухгалтер
- Связанные: R-APP-PAY-02
- Реализует требования: [REQ-PROC-01](../requirements/process.md#req-proc-01)

## R-APP-PAY-02 — Аннулирование счёта за книги возвращает заявку в ожидание счёта

`draft` · effect

Достоверность: реализует требование REQ-PROC-01 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

По invoice.cancelled с invoice_kind=books заявка на этапе awaiting_payment переводится системой в awaiting_invoice; на других этапах событие игнорируется.

- Реализация: [`services/applications/consumers.py::on_invoice_cancelled:23-27`](../../services/applications/consumers.py#L23), [`awaiting_payment->awaiting_invoice`](../../bpm/application_process.yaml#L28)
- Тесты: `tests/test_venue_change.py::test_venue_change_before_payment_reissues_invoice`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-PAY-01, R-APP-VENUE-CHANGE-03
- Реализует требования: [REQ-PROC-01](../requirements/process.md#req-proc-01)

## R-APP-PAY-03 — Только полная оплата счёта за книги открывает выдачу

`draft` · effect

Достоверность: реализует требование REQ-KIND-02 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

По payment.fully_paid (invoice_kind=books) заявка в awaiting_payment переводится в awaiting_issue при выполнении guard fully_paid, отмечается готовой к записи и закрывает дубли клиента по сфере. Частичная оплата этап не меняет.

- Реализация: [`services/applications/consumers.py::on_fully_paid:32-39`](../../services/applications/consumers.py#L32), [`awaiting_payment->awaiting_issue`](../../bpm/application_process.yaml#L29), [`guard:fully_paid`](../../bpm/application_process.yaml)
- Тесты: `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-BOOKING-01, R-APP-DEDUP-01
- Реализует требования: [REQ-KIND-02](../requirements/process.md#req-kind-02)

## R-APP-PAY-04 — Возврат платежа по оплаченной заявке отправляет её в архив с отметкой «возврат»

`verified` · effect

Достоверность: реализует требование REQ-ARCH-05 · ⚠ открытый вопрос D-12: Нужен ли отдельный сценарий «возврат ради смены площадки» без архива и закрытия попытки? — уточни у пользователя

По payment.refunded (invoice_kind=books) заявка на этапе awaiting_issue архивируется от имени главного бухгалтера с outcome=refund. Возврат на других этапах этап заявки не меняет.

- Реализация: [`services/applications/consumers.py::on_payment_refunded:74-78`](../../services/applications/consumers.py#L74), [`awaiting_issue->archived`](../../bpm/application_process.yaml#L40)
- БД: [`attempts_outcome_check`](../../migrations/versions/0001_initial.py#L108)
- Роли: Главный бухгалтер
- Связанные: R-APP-ARCHIVE-03, R-APP-VENUE-CHANGE-02
- Реализует требования: [REQ-ARCH-05](../requirements/archive.md#req-arch-05)

## R-APP-ISSUE-01 — Выдача книг переводит заявку в «Книги у клиента»

`draft` · effect

Достоверность: реализует требование REQ-PROC-01 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

По books.issued (scheduling.issue_books) заявка переводится awaiting_issue -> books_out от имени проверяющего оператора площадки.

- Реализация: [`services/applications/consumers.py::on_books_issued:68-69`](../../services/applications/consumers.py#L68), [`awaiting_issue->books_out`](../../bpm/application_process.yaml#L34)
- Тесты: `tests/test_kinds.py::test_social_application_skips_invoice`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-APP-CLOSE-01
- Реализует требования: [REQ-PROC-01](../requirements/process.md#req-proc-01)

## R-APP-CLOSE-01 — Закрывает заявку проверяющий оператор её площадки после возврата книг и погашения штрафов

`draft` · guard

Достоверность: реализует требование REQ-PROC-09 · извлечено ИИ из кода, подкреплено кодом и 2 тестами

Переход books_out -> closed выполняет только site_checker заявки (AccessDenied иначе) и только при guard settled: нет открытых выдач (scheduling.open_loans_count) и непогашенных штрафов (billing.open_fines_count).

- Реализация: [`services/applications/service.py::close:309-311`](../../services/applications/service.py#L309), [`services/applications/guards.py::settled:12-14`](../../services/applications/guards.py#L12), [`books_out->closed`](../../bpm/application_process.yaml#L35), [`guard:settled`](../../bpm/application_process.yaml)
- Тесты: `tests/test_paid_flow.py::test_cannot_close_with_books_out`, `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Проверяющий оператор
- Связанные: R-APP-ISSUE-01
- Реализует требования: [REQ-PROC-09](../requirements/process.md#req-proc-09)

## R-APP-VENUE-CHANGE-01 — Смену площадки выполняет оператор заявки; закрытую заявку не меняют

`draft` · guard

Достоверность: реализует требование REQ-VENUE-03, REQ-PROC-05 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Площадку меняет только закреплённый оператор; для заявок closed и closed_duplicate — DomainError «заявка закрыта». На новой площадке должна быть активна сфера заявки и все книги должны быть в её прайсе. Смена на ту же площадку ничего не делает.

- Реализация: [`services/applications/service.py::change_venue:203-214`](../../services/applications/service.py#L203)
- БД: [`trg_applications_venue_lock`](../../migrations/versions/0001_initial.py#L141)
- Настройки: `services/applications/service.py::TERMINAL_STAGES`
- Тесты: `tests/test_venue_change.py::test_new_venue_must_have_sphere`
- Роли: Оператор
- Связанные: R-APP-CREATE-02, R-APP-CREATE-03, R-APP-VENUE-CHANGE-02, R-APP-VENUE-CHANGE-03
- Реализует требования: [REQ-VENUE-03](../requirements/venues.md#req-venue-03), [REQ-PROC-05](../requirements/process.md#req-proc-05)

## R-APP-VENUE-CHANGE-02 — Платной заявке после оплаты площадку не меняют; после выдачи книг — никому

`draft` · invariant

Достоверность: реализует требование REQ-VENUE-03 · ⚠ открытый вопрос D-05: Запрещать ли смену площадки при любой привязанной оплате (paid_amount > 0) до её возврата или отвязки? — уточни у пользователя

Код запрещает смену площадки платной заявки на этапах PAID_VENUE_LOCKED_STAGES (awaiting_issue, books_out): «после оплаты площадку меняют только через возврат платежа». Триггер БД дополнительно запрещает смену для любой заявки на books_out, closed, closed_duplicate, а для social и debt — на любом этапе, кроме draft, on_review, needs_rework, archived (после формирования ссылки на запись). Для social/debt запрет есть только в БД — пользователь получит ошибку check_violation, а не DomainError.

- Реализация: [`services/applications/service.py::change_venue:206-207`](../../services/applications/service.py#L206)
- БД: [`trg_applications_venue_lock`](../../migrations/versions/0001_initial.py#L141), [`applications.forbid_venue_change`](../../migrations/versions/0001_initial.py#L125)
- Настройки: `services/applications/service.py::PAID_VENUE_LOCKED_STAGES`
- Тесты: `tests/test_venue_change.py::test_paid_venue_change_after_payment_forbidden`
- Роли: Оператор
- Связанные: R-APP-VENUE-CHANGE-01, R-APP-PAY-04
- Реализует требования: [REQ-VENUE-03](../requirements/venues.md#req-venue-03)
- Оговорка: Схема: social/debt меняют площадку только до формирования ссылки на запись. Код сервиса этого не проверяет — запрет срабатывает только в триггере БД на flush, без доменного сообщения.

## R-APP-VENUE-CHANGE-03 — Смена площадки переназначает проверяющего оператора и запускает реакции billing, scheduling и chat

`draft` · effect

Достоверность: реализует требование REQ-ROLE-08 · ⚠ код расходится с требованием REQ-INV-07 (D-05): Схема: до оплаты счёт аннулируется и выставляется заново по прайсу и реквизитам новой площадки. Код: при частичной оплате (paid_amount > 0)… — уточни у пользователя

При смене площадки за заявкой закрепляется site_checker новой площадки и публикуется application.venue_changed. Billing аннулирует действующий счёт за книги без оплат (дальше invoice.cancelled возвращает заявку в awaiting_invoice); scheduling сбрасывает записи и, если заявка в awaiting_issue, выдаёт новую ссылку; чат фиксирует смену.

- Реализация: [`services/applications/service.py::change_venue:216-230`](../../services/applications/service.py#L216), [`services/billing/consumers.py::on_venue_changed:14-16`](../../services/billing/consumers.py#L14), [`services/scheduling/consumers.py::on_venue_changed:18-21`](../../services/scheduling/consumers.py#L18), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24), [`awaiting_payment->awaiting_invoice`](../../bpm/application_process.yaml#L28)
- Тесты: `tests/test_venue_change.py::test_venue_change_reassigns_site_checker`, `tests/test_venue_change.py::test_venue_change_before_payment_reissues_invoice`
- Роли: Оператор
- Связанные: R-APP-PAY-02, R-APP-VENUE-CHANGE-01
- Реализует требования: [REQ-ROLE-08](../requirements/roles.md#req-role-08)
- ⚠ Расходится с [REQ-INV-07](../requirements/billing.md#req-inv-07): Схема: до оплаты счёт аннулируется и выставляется заново по прайсу и реквизитам новой площадки. Код: при частичной оплате (paid_amount > 0) счёт не аннулируется, а заявка остаётся в awaiting_payment со счётом на реквизиты и цены старой площадки.

## R-APP-ARCHIVE-01 — Заявка, застрявшая на проверке или доработке дольше REVIEW_ARCHIVE_DAYS, уходит в архив

`draft` · timer

Достоверность: по требованию REQ-ARCH-01 · ⚠ код расходится с требованием REQ-ARCH-01 (D-06, D-10, D-17): Схема: месяц. Код: фиксированные 30 дней из настройки. Схема §9 (платная): уходит в архив, если за месяц не получены данные для счёта — зая… — уточни у пользователя

Фоновая задача archive_stale (по docstring — раз в час) архивирует заявки любого вида на этапах on_review и needs_rework, у которых review_started_at старше REVIEW_ARCHIVE_DAYS (30 дней), с outcome=no_data от имени system. Draft-заявки автоматически не архивируются.

- Реализация: [`services/applications/jobs.py::archive_stale:17-27`](../../services/applications/jobs.py#L17), [`on_review->archived`](../../bpm/application_process.yaml#L37), [`needs_rework->archived`](../../bpm/application_process.yaml#L37)
- БД: [`attempts_outcome_check`](../../migrations/versions/0001_initial.py#L108)
- Настройки: `libs/settings.py::REVIEW_ARCHIVE_DAYS`
- Тесты: `tests/test_archive.py::test_stuck_review_goes_to_archive_after_month`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-REVIEW-01, R-APP-ARCHIVE-03, R-APP-CLIENT-03
- ⚠ Расходится с [REQ-ARCH-01](../requirements/archive.md#req-arch-01): Схема: месяц. Код: фиксированные 30 дней из настройки. Схема §9 (платная): уходит в архив, если за месяц не получены данные для счёта — заявки на awaiting_invoice (без выставленного счёта) задача не архивирует никогда.

## R-APP-ARCHIVE-02 — Платная заявка без полной оплаты дольше PAYMENT_ARCHIVE_DAYS уходит в архив

`draft` · timer

Достоверность: реализует требование REQ-ARCH-02 · ⚠ открытый вопрос D-11: Запрещать ли оператору архив при paid_amount > 0 и фиксировать ли outcome=client_declined при ручном архиве вместо произвольного значения? — уточни у пользователя

archive_stale архивирует платные заявки на awaiting_payment, если действующий счёт за книги оплачен не полностью и payment_clock_started_at старше PAYMENT_ARCHIVE_DAYS (30 дней); outcome=unpaid, actor system. Отсчёт идёт от выставления счёта или от возврата из архива.

- Реализация: [`services/applications/jobs.py::archive_stale:29-40`](../../services/applications/jobs.py#L29), [`awaiting_payment->archived`](../../bpm/application_process.yaml#L38)
- БД: [`attempts_outcome_check`](../../migrations/versions/0001_initial.py#L108)
- Настройки: `libs/settings.py::PAYMENT_ARCHIVE_DAYS`
- Тесты: `tests/test_archive.py::test_unpaid_invoice_goes_to_archive_after_month`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-ARCHIVE-03, R-APP-UNARCHIVE-03
- Реализует требования: [REQ-ARCH-02](../requirements/archive.md#req-arch-02)
- Оговорка: Код архивирует и частично оплаченные заявки (paid_amount < amount) как unpaid; возврат поступившей части платежа при этом не инициируется — схема этот случай не описывает.

## R-APP-ARCHIVE-03 — Ручной архив и его последствия — закрытие попытки, сброс записей, сообщение в чат

`draft` · effect

Достоверность: реализует требование REQ-ARCH-04, REQ-ARCH-06 · ⚠ открытый вопрос D-11: Запрещать ли оператору архив при paid_amount > 0 и фиксировать ли outcome=client_declined при ручном архиве вместо произвольного значения? — уточни у пользователя

Оператор заявки отправляет в архив заявку на этапах draft, on_review, needs_rework, awaiting_invoice или awaiting_payment (любой вид); из awaiting_issue в архив уводит только chief_accountant (возврат платежа); после books_out архив невозможен. Архив закрывает текущую попытку (ended_at, outcome) и публикует application.archived — scheduling сбрасывает записи, чат фиксирует событие.

- Реализация: [`services/applications/service.py::archive:255-261`](../../services/applications/service.py#L255), [`services/scheduling/consumers.py::on_archived:26-26`](../../services/scheduling/consumers.py#L26), [`draft->archived`](../../bpm/application_process.yaml#L39), [`on_review->archived`](../../bpm/application_process.yaml#L37), [`needs_rework->archived`](../../bpm/application_process.yaml#L37), [`awaiting_invoice->archived`](../../bpm/application_process.yaml#L39), [`awaiting_payment->archived`](../../bpm/application_process.yaml#L38), [`awaiting_issue->archived`](../../bpm/application_process.yaml#L40)
- БД: [`attempts_outcome_check`](../../migrations/versions/0001_initial.py#L108)
- Тесты: `tests/test_archive.py::test_paid_application_cannot_be_archived_by_operator_after_payment`, `tests/test_archive.py::test_unarchive_starts_new_attempt_and_review`
- Роли: Оператор, Главный бухгалтер, Система (события и фоновые задачи)
- Связанные: R-APP-ACCESS-01, R-APP-PAY-04, R-APP-ARCHIVE-01, R-APP-ARCHIVE-02
- Реализует требования: [REQ-ARCH-04](../requirements/archive.md#req-arch-04), [REQ-ARCH-06](../requirements/archive.md#req-arch-06)

## R-APP-UNARCHIVE-01 — Возврат из архива начинает новую попытку и новую проверку

`draft` · effect

Достоверность: реализует требование REQ-ARCH-08 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Только оператор заявки и только из этапа archived (иначе DomainError «заявка не в архиве») возвращает заявку: добавляется попытка с номером N+1, review_started_at сбрасывается на текущий момент, заявка переходит в on_review. Число попыток не ограничено.

- Реализация: [`services/applications/service.py::unarchive:274-303`](../../services/applications/service.py#L274), [`archived->on_review`](../../bpm/application_process.yaml#L41)
- БД: [`attempts_application_id_no_key`](../../migrations/versions/0001_initial.py#L109)
- Тесты: `tests/test_archive.py::test_unarchive_starts_new_attempt_and_review`
- Роли: Оператор
- Связанные: R-APP-UNARCHIVE-02, R-APP-UNARCHIVE-03
- Реализует требования: [REQ-ARCH-08](../requirements/archive.md#req-arch-08)

## R-APP-UNARCHIVE-02 — При возврате из архива площадку и книги меняют, только если заявка не доходила до записи

`draft` · guard

Достоверность: реализует требование REQ-ARCH-09 · ⚠ открытый вопрос D-12: Нужен ли отдельный сценарий «возврат ради смены площадки» без архива и закрытия попытки? — уточни у пользователя

Новые площадку или книги при возврате из архива можно указать, только если booking_reached_at пуст; иначе DomainError «заявка уже доходила до записи». Новые значения проходят проверку сферы и прайса, при смене площадки переназначается site_checker. Сфера остаётся прежней.

- Реализация: [`services/applications/service.py::unarchive:279-292`](../../services/applications/service.py#L279)
- БД: [`trg_applications_venue_lock`](../../migrations/versions/0001_initial.py#L141)
- Роли: Оператор
- Связанные: R-APP-BOOKING-01, R-APP-CORE-01, R-APP-UNARCHIVE-03
- Реализует требования: [REQ-ARCH-09](../requirements/archive.md#req-arch-09)

## R-APP-UNARCHIVE-03 — После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново

`draft` · effect

Достоверность: по требованию REQ-ARCH-10 · ⚠ код расходится с требованием REQ-ARCH-10 (D-14): Схема: новый счёт выставляется после проверки, если сумма изменилась. Код: счёт аннулируется сразу при возврате из архива, до проверки; сра… — уточни у пользователя

unarchive сравнивает стоимость книг по прайсу площадки до и после изменений (books_price, без надбавки) и публикует application.unarchived с amount_changed. Billing при изменении суммы аннулирует действующий счёт за книги, иначе сбрасывает payment_clock_started_at на текущий момент.

- Реализация: [`services/applications/service.py::unarchive:277-303`](../../services/applications/service.py#L277), [`services/billing/consumers.py::on_unarchived:28-35`](../../services/billing/consumers.py#L28)
- Роли: Оператор
- Связанные: R-APP-UNARCHIVE-01, R-APP-ARCHIVE-02, R-APP-CALC-01
- ⚠ Расходится с [REQ-ARCH-10](../requirements/archive.md#req-arch-10): Схема: новый счёт выставляется после проверки, если сумма изменилась. Код: счёт аннулируется сразу при возврате из архива, до проверки; сравнивается только цена по прайсу без надбавки.

## R-APP-DEDUP-01 — Заявка, первой дошедшая до записи, закрывает остальные заявки клиента по той же сфере

`draft` · effect

Достоверность: по требованию REQ-DEDUP-01 · ⚠ код расходится с требованием REQ-DEDUP-01 (D-01, D-21): Схема: остаётся та заявка, что первой дошла до записи. Код: OPEN_STAGES включает awaiting_issue, поэтому более поздний «победитель» (наприм… — уточни у пользователя

close_duplicates вызывается при полной оплате платной заявки и при прохождении проверки заявки в долг (подписчик application.review_passed с kind=debt). Все другие заявки клиента по той же сфере на этапах OPEN_STAGES (включая awaiting_issue и archived) того же трека (не-social с не-social) переводятся в closed_duplicate; незакрытая попытка закрывается с outcome=duplicate.

- Реализация: [`services/applications/dedup.py::close_duplicates:26-50`](../../services/applications/dedup.py#L26), [`services/applications/dedup.py::_same_track:22-22`](../../services/applications/dedup.py#L22), [`services/applications/consumers.py::on_review_passed:44-47`](../../services/applications/consumers.py#L44), [`services/applications/consumers.py::on_fully_paid:39-39`](../../services/applications/consumers.py#L39), [`awaiting_issue->closed_duplicate`](../../bpm/application_process.yaml#L43)
- БД: [`ix_applications_client_sphere`](../../migrations/versions/0001_initial.py#L94), [`attempts_outcome_check`](../../migrations/versions/0001_initial.py#L108)
- Настройки: `services/applications/dedup.py::OPEN_STAGES`
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-PAY-03, R-APP-REVIEW-05, R-APP-DEDUP-02
- ⚠ Расходится с [REQ-DEDUP-01](../requirements/clients.md#req-dedup-01): Схема: остаётся та заявка, что первой дошла до записи. Код: OPEN_STAGES включает awaiting_issue, поэтому более поздний «победитель» (например, заявка в долг, прошедшая проверку после оплаты платной) закрывает уже дошедшую до записи и оплаченную заявку. Для социальных заявок дедупликация не запускается вообще.

## R-APP-DEDUP-02 — Закрытие дубля аннулирует его неоплаченные счета и сбрасывает записи

`draft` · effect

Достоверность: реализует требование REQ-DEDUP-02 · ⚠ открытый вопрос D-01: Если у клиента уже есть оплаченная заявка на «Ожидает выдачи», должна ли более поздняя заявка в долг закрыться сама как дубль, а не закрыва… — уточни у пользователя

По application.closed_duplicate billing аннулирует все действующие счета заявки без оплат, scheduling сбрасывает записи, чат фиксирует закрытие как дубль. Оплаченные счета дубля остаются действующими.

- Реализация: [`services/billing/consumers.py::on_closed_duplicate:21-23`](../../services/billing/consumers.py#L21), [`services/scheduling/consumers.py::on_closed_duplicate:31-31`](../../services/scheduling/consumers.py#L31), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Роли: Система (события и фоновые задачи)
- Связанные: R-APP-DEDUP-01
- Реализует требования: [REQ-DEDUP-02](../requirements/clients.md#req-dedup-02)

## R-APP-CHAT-01 — Каждая смена этапа заявки пишется в чат (слушатель ORM)

`draft` · effect

Достоверность: реализует требование REQ-CHAT-04 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

Слушатель before_flush публикует application.stage_changed (from, to) при любом изменении поля stage заявки; чат-сервис записывает событие в ленту заявки. Тот же обработчик чата пишет venue_changed, archived, unarchived, closed_duplicate, invoice.issued и invoice.cancelled.

- Реализация: [`services/applications/listeners.py::_domain_events:14-22`](../../services/applications/listeners.py#L14), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- БД: [`applications_stage_check`](../../migrations/versions/0001_initial.py#L86)
- Тесты: `tests/test_chat_api.py::test_stage_changes_appear_in_chat`
- Роли: Система (события и фоновые задачи)
- Реализует требования: [REQ-CHAT-04](../requirements/chat.md#req-chat-04)

## R-APP-CALC-01 — Стоимость книг заявки — сумма цен прайса текущей площадки, надбавку берёт billing у представителя

`draft` · calculation

Достоверность: реализует требование REQ-PRICE-01, REQ-VENUE-02 · извлечено ИИ из кода, подкреплено кодом, ограничением БД и 1 тестом

books_price суммирует цены книг заявки по прайсу её текущей площадки; markup_pct возвращает надбавку представителя. Обе функции использует billing при выставлении счёта за книги (например, 100 по прайсу + 10% = 110). Цена в прайсе положительна, надбавка неотрицательна (CHECK).

- Реализация: [`services/applications/public.py::books_price:68-73`](../../services/applications/public.py#L68), [`services/applications/public.py::markup_pct:80-80`](../../services/applications/public.py#L80)
- БД: [`prices_price_check`](../../migrations/versions/0001_initial.py#L58), [`representatives_markup_pct_check`](../../migrations/versions/0001_initial.py#L66)
- Тесты: `tests/test_paid_flow.py::test_paid_application_full_path`
- Роли: Бухгалтер
- Связанные: R-APP-ADMIN-01, R-APP-UNARCHIVE-03
- Реализует требования: [REQ-PRICE-01](../requirements/billing.md#req-price-01), [REQ-VENUE-02](../requirements/venues.md#req-venue-02)

## R-APP-NOTIFY-01 — Письма по заявке получают только клиент и представитель

`draft` · config

Достоверность: реализует требование REQ-MAIL-01 · извлечено ИИ из кода, подкреплено кодом и 1 тестом

recipients возвращает email клиента и email представителя заявки; notifications использует его как список адресатов всех писем.

- Реализация: [`services/applications/public.py::recipients:88-90`](../../services/applications/public.py#L88)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`
- Роли: Клиент, Представитель клиента
- Реализует требования: [REQ-MAIL-01](../requirements/notifications.md#req-mail-01)

## R-APP-ADMIN-01 — Администратор задаёт надбавку и разрешение работать в долг для представителя

`verified` · config

Достоверность: реализует требование REQ-ADMIN-01 · ⚠ открытый вопрос D-08: Будет ли в проекте админка с проверкой роли admin, или настройки сознательно ведутся вне системы (миграциями или скриптами)? — уточни у пользователя

set_representative_terms меняет markup_pct и debt_allowed представителя. debt_allowed влияет только на вид новых заявок; markup_pct используется при выставлении следующих счетов, уже выставленные не пересчитываются. Надбавка не может быть отрицательной (CHECK).

- Реализация: [`services/applications/admin.py::set_representative_terms:19-20`](../../services/applications/admin.py#L19)
- БД: [`representatives_markup_pct_check`](../../migrations/versions/0001_initial.py#L66)
- Роли: Администратор
- Связанные: R-APP-CREATE-01, R-APP-CALC-01
- Реализует требования: [REQ-ADMIN-01](../requirements/admin.md#req-admin-01)

## R-APP-ADMIN-02 — Реквизиты площадки задаёт администратор; без них счёт не выставить

`verified` · config

Достоверность: реализует требование REQ-ADMIN-02, REQ-INV-03 · ⚠ открытый вопрос D-08: Будет ли в проекте админка с проверкой роли admin, или настройки сознательно ведутся вне системы (миграциями или скриптами)? — уточни у пользователя

set_venue_requisites записывает реквизиты организации площадки. billing читает их через get_venue и отказывает в выставлении счёта, если реквизиты не заполнены: и счёта за книги (issue_books_invoice), и счёта на штраф (issue_fine_invoice).

- Реализация: [`services/applications/admin.py::set_venue_requisites:28-28`](../../services/applications/admin.py#L28), [`services/applications/public.py::get_venue:58-61`](../../services/applications/public.py#L58), [`services/billing/service.py::issue_books_invoice:42-44`](../../services/billing/service.py#L42), [`services/billing/service.py::issue_fine_invoice:185-187`](../../services/billing/service.py#L185)
- Тесты: `tests/test_paid_flow.py::test_invoice_requires_venue_requisites`
- Роли: Администратор
- Реализует требования: [REQ-ADMIN-02](../requirements/admin.md#req-admin-02), [REQ-INV-03](../requirements/billing.md#req-inv-03)

## R-APP-ADMIN-03 — Максимум мест в окне площадки положителен и передаётся в scheduling событием

`draft` · config

Достоверность: реализует требование REQ-SLOT-03 · ⚠ открытый вопрос D-08: Будет ли в проекте админка с проверкой роли admin, или настройки сознательно ведутся вне системы (миграциями или скриптами)? — уточни у пользователя

set_venue_max_capacity отклоняет значение меньше 1 (DomainError, плюс CHECK в БД), сохраняет max_slot_capacity и публикует venue.settings_changed; scheduling обновляет VenueLimit площадки, которым ограничивается число мест в окнах.

- Реализация: [`services/applications/admin.py::set_venue_max_capacity:36-44`](../../services/applications/admin.py#L36), [`services/scheduling/consumers.py::on_venue_settings_changed:36-40`](../../services/scheduling/consumers.py#L36)
- БД: [`venues_max_slot_capacity_check`](../../migrations/versions/0001_initial.py#L33)
- Роли: Администратор
- Реализует требования: [REQ-SLOT-03](../requirements/scheduling.md#req-slot-03)

## R-APP-ADMIN-04 — Отключение сферы на площадке запрещает новые заявки, действующие доводятся до конца

`draft` · config

Достоверность: реализует требование REQ-SPHERE-04 · ⚠ открытый вопрос D-08: Будет ли в проекте админка с проверкой роли admin, или настройки сознательно ведутся вне системы (миграциями или скриптами)? — уточни у пользователя

set_sphere_active включает или выключает пару площадка–сфера (создаёт запись, если её нет). Неактивная сфера блокирует создание заявки, смену площадки на эту площадку и возврат из архива со сменой площадки или книг; на действующие заявки отключение не влияет.

- Реализация: [`services/applications/admin.py::set_sphere_active:50-54`](../../services/applications/admin.py#L50), [`services/applications/service.py::_check_sphere_at_venue:44-46`](../../services/applications/service.py#L44)
- Роли: Администратор
- Связанные: R-APP-CREATE-02
- Реализует требования: [REQ-SPHERE-04](../requirements/venues.md#req-sphere-04)
