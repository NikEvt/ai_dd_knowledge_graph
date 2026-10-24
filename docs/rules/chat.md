<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: chat

Источник: [`knowledge/rules/chat.yaml`](../../knowledge/rules/chat.yaml)

## R-CHAT-PARTICIPANTS-01 — Участники чата — оператор, проверяющий оператор, проверяющий и бухгалтер заявки

`draft` · permission · §15 Чат заявки

Участники чата заявки определяются в момент запроса. Это оператор и проверяющий оператор заявки (поля operator_id и site_checker_id из applications.get_brief), проверяющий, если он уже назначен (reviewer_id не пуст), и бухгалтер, закреплённый за заявкой в billing (billing.accountant_of). Этот набор используется и для записи в чат, и для чтения.

- Реализация: [`services/chat/service.py::participants:15-22`](../../services/chat/service.py#L15)
- Тесты: `tests/test_chat_api.py::test_operator_posts_and_reads`, `tests/test_chat_api.py::test_outsider_cannot_post`
- Роли: Оператор, Проверяющий оператор, Проверяющий, Бухгалтер
- Связанные: R-CHAT-POST-02, R-CHAT-READ-02, R-CHAT-PARTICIPANTS-02

## R-CHAT-PARTICIPANTS-02 — Доступ к чату следует за текущим закреплением сотрудника

`draft` · permission · §15 Чат заявки

Участников не хранят отдельно: при каждом обращении их заново собирают по текущим значениям в заявке и в billing. Если бухгалтер забрал заявку у коллеги или проверяющего переназначили, прежний сотрудник сразу теряет право писать и читать чат. Проверяющий, который ещё не назначен, доступа к чату не имеет.

- Реализация: [`services/chat/service.py::participants:16-21`](../../services/chat/service.py#L16)
- Роли: Бухгалтер, Проверяющий
- Связанные: R-CHAT-PARTICIPANTS-01

## R-CHAT-POST-01 — После закрытия заявки писать в чат нельзя

`verified` · guard · §15 Чат заявки

Если заявка на этапе closed или closed_duplicate, post_message отклоняет сообщение с ошибкой DomainError «после закрытия заявки чат доступен только для чтения». Эта проверка выполняется раньше проверки участника. Этап archived закрытием не считается, и в архивной заявке писать можно.

- Реализация: [`services/chat/service.py::post_message:26-28`](../../services/chat/service.py#L26)
- Роли: Оператор, Проверяющий оператор, Проверяющий, Бухгалтер
- Связанные: R-CHAT-EVENTS-05

## R-CHAT-POST-02 — Писать в чат могут только закреплённые за заявкой сотрудники

`draft` · permission · §17 Сводная таблица: кто что может

post_message пропускает сообщение, только если author_id входит в участники заявки. В остальных случаях — AccessDenied «писать в чат могут только закреплённые за заявкой сотрудники» (HTTP 403). Поэтому администратор, главный бухгалтер, руководитель проверяющих, а также клиент и представитель писать в чат не могут.

- Реализация: [`services/chat/service.py::post_message:29-30`](../../services/chat/service.py#L29), [`services/chat/api.py::post:39-41`](../../services/chat/api.py#L39)
- Тесты: `tests/test_chat_api.py::test_outsider_cannot_post`, `tests/test_chat_api.py::test_operator_posts_and_reads`
- Роли: Оператор, Проверяющий оператор, Проверяющий, Бухгалтер
- Связанные: R-CHAT-PARTICIPANTS-01, R-CHAT-AUTH-01

## R-CHAT-POST-03 — Сообщение сотрудника записывается как обычное, с автором и временем

`draft` · effect · §15 Чат заявки

Сообщение сотрудника сохраняется в chat.messages с is_event=false, указанным author_id и created_at=clock.now(). API возвращает 201 и созданное сообщение.

- Реализация: [`services/chat/service.py::post_message:31-36`](../../services/chat/service.py#L31)
- БД: [`messages_check`](../../migrations/versions/0001_initial.py#L334)
- Тесты: `tests/test_chat_api.py::test_operator_posts_and_reads`
- Роли: Оператор, Проверяющий оператор, Проверяющий, Бухгалтер
- Связанные: R-CHAT-DB-01
- ⚠ Расхождение со схемой: Схема: к сообщениям можно прикреплять файлы. Код: у сообщения есть только текст (body), поддержки вложений нет ни в модели, ни в API.

## R-CHAT-READ-01 — Главный бухгалтер и руководитель проверяющих не видят чат

`draft` · permission · §15 Чат заявки

list_messages сразу отклоняет роли из NO_CHAT_ROLES (chief_accountant, reviewer_lead) с ошибкой AccessDenied «эта роль не видит чат заявки» (HTTP 403). Проверка выполняется раньше проверки участника, поэтому запрет действует, даже если id сотрудника совпадает с одним из участников.

- Реализация: [`services/chat/service.py::list_messages:51-52`](../../services/chat/service.py#L51)
- Настройки: `services/chat/service.py::NO_CHAT_ROLES`
- Тесты: `tests/test_chat_api.py::test_admin_reads_chief_accountant_does_not`
- Роли: Главный бухгалтер, Руководитель проверяющих
- Связанные: R-CHAT-CONFIG-01, R-CHAT-READ-02

## R-CHAT-READ-02 — Чат видят участники заявки и администратор

`draft` · permission · §15 Чат заявки

Читать чат может роль admin (по любой заявке, проверки участника нет) или сотрудник, чей viewer_id входит в участники заявки. Остальным — AccessDenied «чат видят только закреплённые сотрудники и администратор». Клиент и представитель в чат не попадают, потому что их нет среди участников.

- Реализация: [`services/chat/service.py::list_messages:53-54`](../../services/chat/service.py#L53), [`services/chat/api.py::list_:34-36`](../../services/chat/api.py#L34)
- Тесты: `tests/test_chat_api.py::test_admin_reads_chief_accountant_does_not`, `tests/test_chat_api.py::test_operator_posts_and_reads`, `tests/test_chat_api.py::test_stage_changes_appear_in_chat`
- Роли: Администратор, Оператор, Проверяющий оператор, Проверяющий, Бухгалтер
- Связанные: R-CHAT-PARTICIPANTS-01, R-CHAT-READ-01, R-CHAT-AUTH-01

## R-CHAT-READ-03 — Один чат на заявку, общий для всех попыток, в порядке создания

`draft` · invariant · §15 Чат заявки

Сообщения привязаны только к application_id, отдельной сущности «чат» и привязки к попытке нет. list_messages возвращает все сообщения заявки, и сотрудников, и событий, в порядке id. История сохраняется при уходе в архив и возврате из него.

- Реализация: [`services/chat/service.py::list_messages:55-58`](../../services/chat/service.py#L55)
- Тесты: `tests/test_chat_api.py::test_operator_posts_and_reads`
- Связанные: R-CHAT-READ-02

## R-CHAT-READ-04 — Администратор чат только читает

`draft` · permission · §3 Администратор

Роль admin обходит проверку участника только при чтении (list_messages). Записи в чат это не касается: администратора нет среди участников, поэтому post_message от его имени отклоняется с AccessDenied.

- Реализация: [`services/chat/service.py::list_messages:53-54`](../../services/chat/service.py#L53), [`services/chat/service.py::post_message:29-30`](../../services/chat/service.py#L29)
- Тесты: `tests/test_chat_api.py::test_admin_reads_chief_accountant_does_not`
- Роли: Администратор
- Связанные: R-CHAT-READ-02, R-CHAT-POST-02

## R-CHAT-AUTH-01 — Личность и роль в API чата берутся из параметров запроса без проверки

`draft` · permission

GET принимает viewer_id и role как query-параметры, POST принимает author_id в теле. Сервис чата не сверяет их с аутентифицированным пользователем и с реальной ролью сотрудника: проверки прав в list_messages и post_message доверяют переданным значениям.

- Реализация: [`services/chat/api.py::list_:35-36`](../../services/chat/api.py#L35), [`services/chat/api.py::post:40-41`](../../services/chat/api.py#L40)
- Связанные: R-CHAT-READ-01, R-CHAT-READ-02, R-CHAT-POST-02
- ⚠ Расхождение со схемой: Схема: доступ к чату определяется ролью сотрудника и закреплением за заявкой. Код: роль приходит от клиента API — если передать role=admin, проверка участника для чтения отключается.

## R-CHAT-CONFIG-01 — Список ролей без доступа к чату задан константой NO_CHAT_ROLES

`draft` · config

Роли, которым запрещено читать чат, заданы константой модуля NO_CHAT_ROLES = ("chief_accountant", "reviewer_lead") в services/chat/service.py, а не в libs/settings.py.

- Реализация: [`services/chat/service.py::NO_CHAT_ROLES:12-12`](../../services/chat/service.py#L12)
- Настройки: `services/chat/service.py::NO_CHAT_ROLES`
- Тесты: `tests/test_chat_api.py::test_admin_reads_chief_accountant_does_not`
- Роли: Главный бухгалтер, Руководитель проверяющих
- Связанные: R-CHAT-READ-01

## R-CHAT-DB-01 — Сообщение без автора допустимо только для события (CHECK в БД)

`verified` · invariant

CHECK messages_check на chat.messages требует is_event OR author_id IS NOT NULL. Сообщение сотрудника обязано иметь автора, автоматическая запись события может быть без автора. В коде это соответствует log_event (author_id=None, is_event=true) и post_message (author_id задан).

- Реализация: [`services/chat/service.py::log_event:40-42`](../../services/chat/service.py#L40), [`services/chat/service.py::post_message:31-33`](../../services/chat/service.py#L31)
- БД: [`messages_check`](../../migrations/versions/0001_initial.py#L334)
- Связанные: R-CHAT-POST-03, R-CHAT-EVENTS-01

## R-CHAT-DB-02 — Сообщения чата нельзя редактировать и удалять (триггер БД)

`draft` · invariant · §15 Чат заявки

Триггер trg_chat_messages_immutable (BEFORE UPDATE OR DELETE, FOR EACH ROW) вызывает chat.forbid_message_changes, которая бросает исключение «chat messages cannot be edited or deleted» с кодом check_violation. В коде операций редактирования и удаления нет, запрет держится только на БД.

- БД: [`trg_chat_messages_immutable`](../../migrations/versions/0001_initial.py#L342), [`forbid_message_changes`](../../migrations/versions/0001_initial.py#L337)

## R-CHAT-EVENTS-01 — 11 топиков из EVENT_TEXT автоматически пишутся в чат системными сообщениями

`verified` · effect · §15 Чат заявки

Модуль подписывает обработчик _handler на каждый топик из EVENT_TEXT: при загрузке модуля проходит по словарю и регистрирует обработчик через subscribe. Обработчик подставляет payload события в шаблон (template.format(**payload)) и вызывает log_event: запись в chat.messages с is_event=true, author_id=NULL, application_id из payload. В чат попадают только топики из EVENT_TEXT; например, payment.refunded, payment.fully_paid, books.issued, loan.lost, loan.damaged, application.review_passed, application.ready_for_booking и client.updated туда не пишутся.

- Реализация: [`services/chat/consumers.py::<module>:30-31`](../../services/chat/consumers.py#L30), [`services/chat/consumers.py::_handler:23-27`](../../services/chat/consumers.py#L23), [`services/chat/service.py::log_event:39-45`](../../services/chat/service.py#L39)
- БД: [`messages_check`](../../migrations/versions/0001_initial.py#L334)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Тесты: `tests/test_chat_api.py::test_stage_changes_appear_in_chat`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-CONFIG-02, R-CHAT-DB-01

## R-CHAT-CONFIG-02 — Набор событий для чата и их тексты заданы словарём EVENT_TEXT

`draft` · config

Словарь EVENT_TEXT в services/chat/consumers.py одновременно определяет, на какие топики подписан чат, и текст записи для каждого. Новое событие попадёт в чат, только если добавить его в словарь. Плейсхолдеры шаблона должны совпадать с ключами payload, иначе обработчик упадёт с KeyError.

- Реализация: [`services/chat/consumers.py::EVENT_TEXT:8-20`](../../services/chat/consumers.py#L8), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-01, R-CHAT-EVENTS-07

## R-CHAT-EVENTS-02 — Каждая смена этапа заявки появляется в чате

`draft` · effect · §15 Чат заявки

Слушатель ORM before_flush в applications (_domain_events) публикует application.stage_changed при любом изменении поля stage, в payload передаются from и to. Чат записывает «Этап: {from} → {to}» с кодами этапов, например «Этап: draft → on_review».

- Реализация: [`services/applications/listeners.py::_domain_events:16-22`](../../services/applications/listeners.py#L16), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Тесты: `tests/test_chat_api.py::test_stage_changes_appear_in_chat`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-01

## R-CHAT-EVENTS-03 — Смена площадки, архив, возврат из архива и закрытие как дубль пишутся в чат

`verified` · effect · §15 Чат заявки

Чат обрабатывает события application.venue_changed («Площадка изменена: {old_venue_id} → {new_venue_id}»), application.archived («Заявка ушла в архив ({outcome})»), application.unarchived («Заявка возвращена из архива») и application.closed_duplicate («Заявка закрыта как дубль заявки {winner_id}»). Архив, возврат из архива и закрытие дублем меняют stage, поэтому рядом появляется ещё запись application.stage_changed. Смена площадки (change_venue) этап не меняет, и записи stage_changed рядом с ней нет.

- Реализация: [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-02

## R-CHAT-EVENTS-04 — Выставление и аннулирование счёта и привязка платежа пишутся в чат

`draft` · effect · §15 Чат заявки

Подписки на события billing: invoice.issued («Выставлен счёт {invoice_id} на {amount}», и для счёта за книги, и для штрафа), invoice.cancelled («Счёт {invoice_id} аннулирован ({reason})»), payment.linked («Привязан платёж {amount} к счёту {invoice_id}»).

- Реализация: [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-07

## R-CHAT-EVENTS-05 — События пишутся в чат и после закрытия заявки

`draft` · effect

log_event, в отличие от post_message, не проверяет этап заявки. Системные записи о событиях добавляются и в заявку на этапе closed или closed_duplicate — например, аннулирование счёта по дублю после его закрытия.

- Реализация: [`services/chat/service.py::log_event:39-45`](../../services/chat/service.py#L39)
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-POST-01

## R-CHAT-EVENTS-06 — Запись, отмена, перенос и неявка видны в чате как события брони

`verified` · effect · §15 Чат заявки

Чат обрабатывает booking.created («Запись на {starts_at}») и booking.cancelled («Запись на {starts_at} отменена ({reason})»). Отдельного события переноса нет: reschedule отменяет запись (reason=cancelled) и создаёт новую, поэтому в чате появляются две записи. Неявка выглядит как отмена с причиной «no_show».

- Реализация: [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-01
- ⚠ Расхождение со схемой: Схема называет перенос и неявку отдельными событиями чата. Код: перенос не отличить от отмены с новой записью, неявка показывается кодом причины «no_show» внутри текста об отмене.

## R-CHAT-EVENTS-07 — Часть событий заявки в чат не попадает

`draft` · effect · §15 Чат заявки

Топиков payment.fully_paid, payment.refunded, books.issued, loan.damaged, loan.lost, application.review_passed и application.ready_for_booking нет в EVENT_TEXT, поэтому в чат они не пишутся. Выдача книг видна только через смену этапа. Отвязка платежа (unlink_payment) и назначение проверяющего или бухгалтера событий не публикуют и в чате тоже не отражаются.

- Реализация: [`services/chat/consumers.py::EVENT_TEXT:8-20`](../../services/chat/consumers.py#L8)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-CONFIG-02, R-CHAT-EVENTS-04
- ⚠ Расхождение со схемой: Схема: в чат автоматически попадают все события заявки, включая назначения и платежи. Код: назначения, возврат и отвязка платежа, порча и утеря книг в чате не фиксируются.

## R-CHAT-EVENTS-08 — Срыв срока возврата книги пишется в чат

`draft` · timer · §15 Чат заявки

Фоновая задача scheduling flag_overdue отмечает выданные книги (status=out), у которых с issued_at прошло больше 30 дней, и публикует loan.overdue. Чат записывает «Срыв срока возврата книги {book_id}». Срок 30 дней задан литералом timedelta(days=30) в jobs.py, а не настройкой.

- Реализация: [`services/scheduling/jobs.py::flag_overdue:11-26`](../../services/scheduling/jobs.py#L11), [`services/chat/consumers.py::_handler:24-25`](../../services/chat/consumers.py#L24)
- Настройки: `services/chat/consumers.py::EVENT_TEXT`
- Роли: Система (события и фоновые задачи)
- Связанные: R-CHAT-EVENTS-01
