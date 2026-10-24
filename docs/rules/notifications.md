<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Правила: notifications

Источник: [`knowledge/rules/notifications.yaml`](../../knowledge/rules/notifications.yaml)

## R-NOTIF-BOOKING-01 — При записи на визит отправляется письмо о записи

`draft` · effect · §13 Запись на визит и письма

Подписчик notifications на событие booking.created (его публикует scheduling при записи по ссылке, записи оператором и при второй половине переноса) создаёт письмо типа booking. Площадка для поиска шаблона берётся из payload события, в контекст подстановки передаётся только starts_at.

- Реализация: [`services/notifications/consumers.py::on_booking_created:9-17`](../../services/notifications/consumers.py#L9), [`services/notifications/service.py::send:42-58`](../../services/notifications/service.py#L42)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`, `tests/test_notifications.py::test_social_uses_social_templates`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-NOTIF-RECIPIENTS-01, R-NOTIF-TEMPLATE-01, R-NOTIF-RENDER-01

## R-NOTIF-CANCEL-01 — Любая отмена записи даёт письмо об отмене

`draft` · effect · §13 Запись на визит и письма

Подписчик notifications на booking.cancelled создаёт письмо типа cancel. Событие публикуется при каждой отмене действующей записи: отмена клиентом, представителем или оператором, неявка (no_show), удаление окна (slot_removed), смена площадки (venue_changed), архивирование (archived), дубль (duplicate). Причину модуль не различает: на все случаи уходит одно и то же письмо об отмене.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20), [`services/notifications/service.py::send:42-58`](../../services/notifications/service.py#L42)
- Тесты: `tests/test_notifications.py::test_reschedule_sends_cancel_and_booking`
- Роли: Клиент, Представитель клиента, Оператор, Проверяющий оператор, Система (события и фоновые задачи)
- Связанные: R-NOTIF-RENDER-02, R-NOTIF-NOSHOW-01, R-NOTIF-RESET-01, R-NOTIF-SLOT-01

## R-NOTIF-RESCHEDULE-01 — Перенос даёт письмо об отмене и письмо о новой записи

`draft` · effect · §13 Запись на визит и письма

Отдельного письма о переносе нет. Перенос в scheduling — это отмена записи (booking.cancelled) и новая запись (booking.created), поэтому по нему уходят два письма: cancel, затем booking.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20), [`services/notifications/consumers.py::on_booking_created:9-17`](../../services/notifications/consumers.py#L9)
- Тесты: `tests/test_notifications.py::test_reschedule_sends_cancel_and_booking`
- Роли: Клиент, Представитель клиента, Оператор
- Связанные: R-NOTIF-BOOKING-01, R-NOTIF-CANCEL-01

## R-NOTIF-NOSHOW-01 — Неявка отправляет письмо об отмене

`verified` · effect · §13 Запись на визит и письма

Когда проверяющий оператор отмечает неявку, scheduling отменяет запись с reason=no_show и публикует booking.cancelled. Notifications отправляет на него обычное письмо об отмене, а не отдельный тип письма.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20)
- Роли: Проверяющий оператор
- Связанные: R-NOTIF-CANCEL-01, R-NOTIF-RENDER-02

## R-NOTIF-SLOT-01 — Удаление окна с записями рассылает письма об отмене

`verified` · effect · §12 Расписание площадок

Когда проверяющий оператор удаляет окно расписания, каждая действующая запись в нём отменяется с reason=slot_removed, и каждый записанный клиент со своим представителем получает письмо об отмене.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20)
- Роли: Проверяющий оператор
- Связанные: R-NOTIF-CANCEL-01

## R-NOTIF-RESET-01 — Архивирование, дубль и смена площадки отправляют письмо об отмене

`verified` · effect · §5 Архив и попытки

При архивировании заявки, признании её дублем и смене площадки scheduling сбрасывает действующие записи (reset_bookings с reason archived, duplicate или venue_changed). На каждую отменённую запись notifications отправляет письмо об отмене. Сам метод send этап заявки не проверяет. То, что по заявке в архиве письма потом не идут, держится только на том, что scheduling гасит ссылку на запись.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20), [`services/notifications/service.py::send:42-58`](../../services/notifications/service.py#L42)
- Роли: Оператор, Система (события и фоновые задачи)
- Связанные: R-NOTIF-CANCEL-01
- ⚠ Расхождение со схемой: Схема (§5): пока заявка в архиве, письма не отправляются. Код: в момент архивирования письмо об отмене всё-таки уходит. В send нет проверки этапа и архивного статуса, поэтому любое событие booking.* по заявке в архиве тоже приведёт к письму.

## R-NOTIF-RECIPIENTS-01 — Письма получают только клиент и представитель

`draft` · invariant · §13 Запись на визит и письма

Получатели письма — email клиента и email представителя заявки, именно в этом порядке. Список берётся из applications.public.recipients в момент отправки и сохраняется в письме. Сотрудники писем не получают.

- Реализация: [`services/notifications/service.py::send:49-49`](../../services/notifications/service.py#L49), [`services/applications/public.py::recipients:83-90`](../../services/applications/public.py#L83)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`
- Роли: Клиент, Представитель клиента
- Связанные: R-NOTIF-CHAT-01

## R-NOTIF-CHAT-01 — События записи параллельно попадают в чат заявки

`draft` · effect · §13 Запись на визит и письма

У booking.created и booking.cancelled два подписчика: notifications (письмо) и chat (consumers.py::_handler пишет в чат заявки «Запись на {starts_at}» или «Запись на {starts_at} отменена ({reason})»). Так сотрудники узнают о событиях записи, не получая писем.

- Реализация: [`services/notifications/consumers.py::on_booking_created:9-17`](../../services/notifications/consumers.py#L9), [`services/notifications/consumers.py::on_booking_cancelled:20-28`](../../services/notifications/consumers.py#L20)
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-RECIPIENTS-01

## R-NOTIF-TEMPLATE-01 — Шаблон выбирается по площадке, группе вида заявки и типу письма

`draft` · guard · §13 Запись на визит и письма

find_template ищет шаблон по тройке (venue_id из события, группа вида заявки через TEMPLATE_GROUP, тип письма booking или cancel). Вид заявки берётся из get_brief на момент отправки.

- Реализация: [`services/notifications/service.py::find_template:32-39`](../../services/notifications/service.py#L32), [`services/notifications/service.py::send:45-46`](../../services/notifications/service.py#L45)
- Настройки: `services/notifications/config.py::TEMPLATE_GROUP`
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`, `tests/test_notifications.py::test_social_uses_social_templates`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-TEMPLATE-02, R-NOTIF-TEMPLATE-04, R-NOTIF-MISSING-01

## R-NOTIF-TEMPLATE-02 — Заявки в долг используют шаблоны платных заявок

`draft` · config · §13 Запись на визит и письма

TEMPLATE_GROUP сопоставляет вид заявки группе шаблонов: paid→paid, debt→paid, social→social. Для заявок в долг отдельных шаблонов нет, берутся шаблоны платных.

- Реализация: [`services/notifications/config.py::TEMPLATE_GROUP:2-6`](../../services/notifications/config.py#L2), [`services/notifications/service.py::find_template:36-36`](../../services/notifications/service.py#L36)
- Настройки: `services/notifications/config.py::TEMPLATE_GROUP`
- Тесты: `tests/test_notifications.py::test_social_uses_social_templates`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-TEMPLATE-01, R-NOTIF-TEMPLATE-03

## R-NOTIF-TEMPLATE-03 — Вид заявки без записи в TEMPLATE_GROUP ломает отправку

`draft` · config

find_template обращается к TEMPLATE_GROUP[kind] напрямую, без значения по умолчанию. Если появится вид заявки, которого нет в словаре, обработчик booking.* упадёт с KeyError, а не создаст письмо со статусом no_template.

- Реализация: [`services/notifications/service.py::find_template:36-36`](../../services/notifications/service.py#L36)
- Настройки: `services/notifications/config.py::TEMPLATE_GROUP`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-TEMPLATE-02, R-NOTIF-MISSING-01

## R-NOTIF-TEMPLATE-04 — Один шаблон на площадку, группу и тип письма

`draft` · invariant · §13 Запись на визит и письма

На каждую комбинацию (venue_id, kind_group, type) в notifications.templates допускается не больше одного шаблона: это гарантирует уникальный индекс БД. Код опирается на это и делает upsert в set_template и scalar-выборку в find_template.

- Реализация: [`services/notifications/service.py::set_template:18-27`](../../services/notifications/service.py#L18)
- БД: [`templates_venue_id_kind_group_type_key`](../../migrations/versions/0001_initial.py#L311)
- Роли: Администратор
- Связанные: R-NOTIF-TEMPLATE-05, R-NOTIF-TEMPLATE-06

## R-NOTIF-TEMPLATE-05 — Допустимые группы шаблонов — paid и social, типы — booking и cancel

`draft` · invariant · §13 Запись на визит и письма

Ограничения CHECK в БД разрешают в notifications.templates только kind_group из {paid, social} и type из {booking, cancel}. Группы debt в БД нет: долговые заявки сводятся к paid через TEMPLATE_GROUP. set_template значения сам не проверяет, недопустимое отклонит БД.

- Реализация: [`services/notifications/service.py::set_template:15-29`](../../services/notifications/service.py#L15)
- БД: [`templates_kind_group_check`](../../migrations/versions/0001_initial.py#L308), [`templates_type_check`](../../migrations/versions/0001_initial.py#L309)
- Роли: Администратор
- Связанные: R-NOTIF-TEMPLATE-02, R-NOTIF-TYPES-01

## R-NOTIF-TEMPLATE-06 — Сохранение шаблона создаёт его или заменяет текст

`draft` · effect · §13 Запись на визит и письма

set_template ищет шаблон по (venue_id, kind_group, type). Если шаблона нет, создаёт его, если есть, перезаписывает только body. Уже отправленные письма хранят свой текст и при смене шаблона не меняются.

- Реализация: [`services/notifications/service.py::set_template:18-28`](../../services/notifications/service.py#L18)
- БД: [`templates_venue_id_kind_group_type_key`](../../migrations/versions/0001_initial.py#L311)
- Роли: Администратор
- Связанные: R-NOTIF-TEMPLATE-04, R-NOTIF-TEMPLATE-07, R-NOTIF-LOG-01

## R-NOTIF-TEMPLATE-07 — Настройка шаблонов не ограничена ролью администратора

`draft` · permission · §17 Сводная таблица: кто что может

У set_template нет параметра пользователя и проверки роли, а в приложении notifications нет HTTP-эндпоинтов (app.py только подключает wiring и обработчики ошибок). Кто может настраивать шаблоны, в модуле не задано.

- Реализация: [`services/notifications/service.py::set_template:15-29`](../../services/notifications/service.py#L15)
- Роли: Администратор
- Связанные: R-NOTIF-TEMPLATE-06
- ⚠ Расхождение со схемой: Схема (§2, §17): шаблоны писем настраивает только администратор в админке. Код: в set_template нет проверки роли и нет точки входа для администратора.

## R-NOTIF-MISSING-01 — Без шаблона письмо фиксируется со статусом no_template

`draft` · effect

Если для площадки, группы и типа шаблон не найден, send не бросает ошибку. Письмо сохраняется со status=no_template, template_id=NULL и пустым body. Запись или отмена визита при этом проходит.

- Реализация: [`services/notifications/service.py::send:51-53`](../../services/notifications/service.py#L51)
- БД: [`emails_status_check`](../../migrations/versions/0001_initial.py#L321)
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-TEMPLATE-01, R-NOTIF-LOG-02

## R-NOTIF-RENDER-01 — Текст письма — шаблон с подстановкой $starts_at

`draft` · calculation

Тело письма собирается через string.Template.safe_substitute из тела шаблона и контекста. Обработчики передают в контекст только starts_at (время окна в ISO-формате). Неизвестные плейсхолдеры остаются в тексте как есть, ошибки нет.

- Реализация: [`services/notifications/service.py::send:52-52`](../../services/notifications/service.py#L52), [`services/notifications/consumers.py::on_booking_created:16-16`](../../services/notifications/consumers.py#L16), [`services/notifications/consumers.py::on_booking_cancelled:27-27`](../../services/notifications/consumers.py#L27)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-RENDER-02

## R-NOTIF-RENDER-02 — В письмо об отмене не попадают причина и новая ссылка

`verified` · effect · §7 Площадки и цены

Payload booking.cancelled содержит reason, но on_booking_cancelled передаёт в контекст только starts_at. Поэтому письмо об отмене одинаково при отмене клиентом, неявке, удалении окна, архивировании и смене площадки, и ссылки на новую запись в нём нет.

- Реализация: [`services/notifications/consumers.py::on_booking_cancelled:22-28`](../../services/notifications/consumers.py#L22)
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-CANCEL-01, R-NOTIF-RENDER-01
- ⚠ Расхождение со схемой: Схема (§7): при смене площадки клиент и представитель получают письмо об отмене и новую ссылку. Код: в письме об отмене нет ссылки, а отдельного письма со ссылкой модуль не отправляет.

## R-NOTIF-TYPES-01 — Существует только два типа писем — booking и cancel

`draft` · invariant · §13 Запись на визит и письма

notifications.emails и notifications.templates ограничением CHECK допускают только type из {booking, cancel}. Писем о переносе, выдаче, счетах, штрафах или архиве в модуле нет.

- Реализация: [`services/notifications/consumers.py::on_booking_created:14-14`](../../services/notifications/consumers.py#L14), [`services/notifications/consumers.py::on_booking_cancelled:25-25`](../../services/notifications/consumers.py#L25)
- БД: [`emails_type_check`](../../migrations/versions/0001_initial.py#L318), [`templates_type_check`](../../migrations/versions/0001_initial.py#L309)
- Тесты: `tests/test_notifications.py::test_reschedule_sends_cancel_and_booking`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-RESCHEDULE-01, R-NOTIF-TEMPLATE-05

## R-NOTIF-LOG-01 — Каждое письмо сохраняется в журнале emails

`draft` · effect

send записывает в notifications.emails заявку, список получателей, тип, ссылку на шаблон, готовый текст, статус и created_at (clock.now()). Запись идёт в той же сессии, что и обработка события. Реальной доставки (SMTP и т. п.) в модуле нет: status=sent значит «письмо сформировано».

- Реализация: [`services/notifications/service.py::send:47-57`](../../services/notifications/service.py#L47)
- Тесты: `tests/test_notifications.py::test_booking_email_goes_to_client_and_representative`
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-MISSING-01, R-NOTIF-LOG-02

## R-NOTIF-LOG-02 — Статус письма — только sent или no_template

`draft` · invariant

Ограничение CHECK в БД разрешает в notifications.emails.status только sent и no_template. Код выставляет sent, если шаблон найден, и no_template, если нет. Статусов доставки или ошибки отправки нет.

- Реализация: [`services/notifications/service.py::send:53-53`](../../services/notifications/service.py#L53)
- БД: [`emails_status_check`](../../migrations/versions/0001_initial.py#L321)
- Роли: Система (события и фоновые задачи)
- Связанные: R-NOTIF-MISSING-01, R-NOTIF-LOG-01
