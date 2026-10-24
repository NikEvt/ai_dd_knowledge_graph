<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# Сверка источников: схема, код, БД

Проект реализует подмножество общей схемы (`knowledge/sources/erp-library.md`) с упрощениями.
Расхождения фиксируются здесь и в `knowledge/reconciliation.yaml`; код не исправляется.

## Расхождения (29)

| ID | Важность | Расхождение | Схема | Код / БД | Правила | Вопрос |
|---|---|---|---|---|---|---|
| D-01 | high | Дедупликация закрывает заявку, которая уже дошла до записи | §6: остаётся та заявка, что первой дошла до записи (платная — при полной оплате, в долг — при прохождении проверки) | services/applications/dedup.py::OPEN_STAGES:10 включает awaiting_issue; dedup.py::close_duplicates:25 вызывается из consumers.py::on_review_passed:43 и on_fully_paid:31 без проверки, что у других заявок booking_reached_at пуст<br>БД: ix_applications_client_sphere — обычный индекс, не уникальный | R-APP-DEDUP-01, R-APP-DEDUP-02, R-BILL-PROCESS-01 | Если у клиента уже есть оплаченная заявка на «Ожидает выдачи», должна ли более поздняя заявка в долг закрыться сама как дубль, а не закрывать оплаченную? |
| D-02 | high | Ссылка на запись нигде не отправляется клиенту | §13: ссылка формируется и уходит на «Ожидает выдачи» и когда книги у клиента; §1: клиент работает только по ссылке из письма | services/scheduling/consumers.py::on_ready_for_booking:12 и scheduling/service.py::issue_books:223 создают ссылку; notifications подписан только на booking.created и booking.cancelled (notifications/consumers.py:9,20)<br>БД: emails_type_check, templates_type_check — только booking и cancel | R-SCHEMA-NOTIF-01, R-SCHEMA-NOTIF-02, R-SCHED-LINK-01, R-NOTIF-TYPES-01, R-NOTIF-RENDER-02 | Как клиент получает токен ссылки — нужен ли тип письма «ссылка на запись» (за книгами и на сдачу), в том числе после смены площадки? |
| D-03 | high | Роли и закрепление сотрудников в большинстве действий не проверяются | §2, §3, §17: проверяющего назначает только руководитель проверяющих; привязку, отвязку и возврат платежа выполняет только главный бухгалтер; аннулирует счёт закреплённый бухгалтер; данные клиента обновляет проверяющий | applications/service.py::assign_reviewer:122 (без исполнителя); update_client:131 (без source_application_id проверки нет); billing/service.py::link_payment:98 (chief_id из тела запроса), unlink_payment:132, refund_payment:143, cancel_invoice:75 (без исполнителя); chat/api.py::list_:35 (role из query) | R-APP-REVIEW-02, R-APP-CLIENT-01, R-BILL-PAYMENT-03, R-BILL-REFUND-01, R-BILL-UNLINK-01, R-BILL-CANCEL-02, R-CHAT-AUTH-01, R-SCHEMA-ROLE-01 | Где должна проверяться роль — в сервисах (тогда нужен справочник сотрудников) или во внешнем шлюзе аутентификации, которому сервисы доверяют? |
| D-04 | high | Ограничение «за два дня» и признак оператора обходятся параметром запроса | §2 Клиент, §13: менее чем за два дня переносит или отменяет только оператор; оператор записывает в системе, клиент и представитель — по ссылке | services/scheduling/api.py::cancel:41 — by из query; scheduling/service.py::cancel_booking:193 доверяет by; api.py::book:35 — booked_by=operator принимается от любого обладателя токена<br>БД: bookings_booked_by_check — только допустимые значения, не источник | R-SCHED-CANCEL-02, R-SCHED-BOOK-03, R-SCHED-RESCHEDULE-01 | Нужно ли закрыть публичным эндпоинтам значения by и booked_by, отличные от client и representative, и пускать оператора только через book_by_operator с проверкой закрепления? |
| D-05 | high | После проверки заявка с частичной оплатой меняет площадку, а счёт остаётся старым | §7: до оплаты счёт аннулируется и выставляется по прайсу и реквизитам новой площадки; после оплаты смена — только через возврат | services/applications/service.py::change_venue:199 блокирует paid только на awaiting_issue и books_out; services/billing/consumers.py::on_venue_changed:13 аннулирует счёт только при paid_amount = 0<br>БД: trg_invoices_cancel_guard не даёт аннулировать счёт с платежом | R-APP-VENUE-CHANGE-02, R-APP-VENUE-CHANGE-03, R-BILL-VENUE-CHANGE-01 | Запрещать ли смену площадки при любой привязанной оплате (paid_amount > 0) до её возврата или отвязки? |
| D-06 | high | Возвращённая на проверку из-за обновления клиента заявка сразу уходит в архив по старому сроку | §6: другие заявки клиента, не дошедшие до записи, снова уходят на проверку; §5: архив — если месяц с начала проверки оператор не получил данные | services/applications/consumers.py::on_client_updated:51 не сбрасывает review_started_at; services/applications/jobs.py::archive_stale:14 архивирует on_review с review_started_at старше REVIEW_ARCHIVE_DAYS | R-APP-CLIENT-03, R-APP-ARCHIVE-01, R-APP-REVIEW-01 | С какого момента считать месяц для повторной проверки после обновления данных клиента — с первой проверки или с возврата на проверку? |
| D-07 | high | Без настроенной ставки штраф не создаётся, и заявку можно закрыть | §14: штраф начисляется за утерю, порчу и просрочку; пока штрафы не погашены, заявку закрыть нельзя | services/billing/service.py::create_fine:164 поднимает DomainError, если ставки нет, внутри обработчиков on_loan_overdue:39, on_loan_lost:44, on_loan_damaged:49; guard settled видит 0 открытых штрафов<br>БД: fine_rates_amount_check допускает 0, а invoices_amount_check требует amount > 0 | R-BILL-FINE-02, R-BILL-FINE-SETTLED-01, R-SCHEMA-ADMIN-01 | Что делать при отсутствии ставки — блокировать выдачу книг, пока ставки не настроены, или создавать штраф без суммы, который ждёт настройки? Как гасить штраф с нулевой ставкой? |
| D-08 | medium | Ставки штрафов, шаблоны и прочие настройки админки не связаны с ролью администратора | §2 Администратор, §17: надбавки, работу в долг, штрафы, шаблоны, реквизиты и максимум мест настраивает только администратор | services/applications/admin.py::set_representative_terms:13, set_venue_requisites:24, set_venue_max_capacity:32, set_sphere_active:48 и services/notifications/service.py::set_template:15 — без исполнителя и без HTTP-входа; сеттера fine_rates нет | R-APP-ADMIN-01, R-APP-ADMIN-02, R-APP-ADMIN-03, R-APP-ADMIN-04, R-NOTIF-TEMPLATE-07, R-SCHEMA-ADMIN-01 | Будет ли в проекте админка с проверкой роли admin, или настройки сознательно ведутся вне системы (миграциями или скриптами)? |
| D-09 | medium | Запрет смены площадки для social и debt после ссылки есть только в триггере; текст R-SCHED-VENUE-CHANGE-01 неточен | §7, §9: social и debt меняют площадку только до формирования ссылки; после выдачи — никому | services/applications/service.py::change_venue:199 доменной проверки нет; на flush (строка 219) срабатывает триггер с check_violation вместо DomainError<br>БД: trg_applications_venue_lock / forbid_venue_change запрещает смену на books_out, closed и closed_duplicate для всех видов, а для social/debt — вне draft, on_review, needs_rework и archived. Поэтому сценарий «debt/social на books_out меняет площадку» из R-SCHED-VENUE-CHANGE-01 в БД невозможен | R-APP-VENUE-CHANGE-02, R-SCHED-VENUE-CHANGE-01 | Перенести ли запрет в сервис (с доменным сообщением) и поправить формулировку расхождения в R-SCHED-VENUE-CHANGE-01? |
| D-10 | medium | Платную заявку без выставленного счёта автоархив не берёт | §9 Платная: в архив, если за месяц с начала проверки не получены данные для счёта; §5: «месяц» | services/applications/jobs.py::archive_stale:20 — только on_review и needs_rework; awaiting_invoice никогда не архивируется; срок — 30 дней из settings.REVIEW_ARCHIVE_DAYS | R-APP-ARCHIVE-01 | Должна ли заявка, которая месяц висит в «Ожидает счёта», уходить в архив, и от какой даты считать этот месяц? Месяц — это календарный месяц или 30 дней? |
| D-11 | medium | Ручной архив оператором возможен при частичной оплате; отметка «клиент передумал» не ставится | §5: оператор отправляет в архив неоплаченную заявку, если клиент передумал; оплаченную — через возврат у главного бухгалтера; история хранит «клиент передумал» | services/applications/service.py::archive:246 принимает actor и outcome от вызывающего, оплату не проверяет; при actor≠operator закрепление не проверяется. bpm/application_process.yaml:39 разрешает оператору awaiting_payment->archived. Значение client_declined в коде не используется, HTTP-маршрута архива нет<br>БД: attempts_outcome_check допускает client_declined — мёртвое значение | R-APP-ARCHIVE-03, R-APP-ARCHIVE-02 | Запрещать ли оператору архив при paid_amount > 0 и фиксировать ли outcome=client_declined при ручном архиве вместо произвольного значения? |
| D-12 | medium | Возврат платежа «для смены площадки» всегда уводит заявку в архив | §2 Главный бухгалтер, §7: возврат оформляется при смене площадки после оплаты или если клиент передумал; смена площадки после оплаты — через возврат и новую оплату | services/applications/consumers.py::on_payment_refunded:73 на awaiting_issue всегда архивирует с outcome=refund; после этого unarchive:265 не даёт сменить площадку, потому что booking_reached_at заполнен. Сменить площадку можно только так: возврат из архива → проверка → awaiting_payment → change_venue | R-APP-PAY-04, R-APP-PAY-04, R-APP-UNARCHIVE-02 | Нужен ли отдельный сценарий «возврат ради смены площадки» без архива и закрытия попытки? |
| D-13 | medium | Отвязка или возврат платежа после полной оплаты не откатывают выдачу и штраф | §9, §11: выдачу по платной заявке открывает только полная оплата; штраф гасится оплатой | services/billing/service.py::unlink_payment:132 не публикует событие; refund_payment:143 по счёту на штраф не возвращает fines.status в open; issue_fine_invoice:177 не проверяет, оплачен ли штраф и есть ли по нему действующий счёт<br>БД: uq_invoices_one_active_books действует только для kind='books' | R-BILL-UNLINK-01, R-BILL-REFUND-01, R-BILL-FINE-INVOICE-01, R-BILL-FINE-PAY-01 | Должна ли отвязка или возврат оплаты возвращать заявку в «Ожидает оплаты», а штраф — в open? Можно ли выставлять второй счёт на тот же штраф? |
| D-14 | medium | Возврат из архива аннулирует счёт до проверки и по цене без надбавки | §5: если до архива был неоплаченный счёт, новый выставляется после проверки, только если сумма изменилась | services/applications/service.py::unarchive:265 сравнивает books_price без markup_pct; services/billing/consumers.py::on_unarchived:27 сразу аннулирует счёт, а при частичной оплате cancel_invoice поднимает DomainError внутри обработчика<br>БД: trg_invoices_cancel_guard | R-APP-UNARCHIVE-03, R-BILL-UNARCHIVE-01 | Сравнивать полную сумму счёта (с надбавкой) и аннулировать после проверки, а не при возврате? Что делать с частично оплаченным счётом? |
| D-15 | medium | Частично оплаченный счёт заявки-дубля остаётся действующим | §6: выставленный по второй заявке счёт аннулируется | services/billing/consumers.py::on_closed_duplicate:20 аннулирует только счета с paid_amount = 0<br>БД: trg_invoices_cancel_guard | R-BILL-DUPLICATE-01, R-APP-DEDUP-02 | Должен ли главный бухгалтер получать задачу на возврат частичной оплаты по дублю? |
| D-16 | medium | Срок просрочки задан литералом и отсчитывается от issued_at, а не от due_at | §14: срок пользования — месяц с даты выдачи; срыв система отмечает автоматически | services/scheduling/jobs.py::flag_overdue:16 — timedelta(days=30) вместо settings.LOAN_PERIOD_DAYS или loans.due_at; книгу, возвращённую с опозданием до запуска задачи, не штрафуют | R-SCHED-OVERDUE-01, R-SCHED-ISSUE-02, R-CHAT-EVENTS-08 | Считать ли просрочку по loans.due_at и начислять ли штраф при позднем возврате в return_book? |
| D-17 | medium | Фоновые задачи не запускаются из репозитория | §5, §14: автоархив и отметка срыва срока выполняются автоматически | services/applications/jobs.py::archive_stale:14 и services/scheduling/jobs.py::flag_overdue:10 вызываются только из тестов; планировщика нет | R-APP-ARCHIVE-01, R-APP-ARCHIVE-02, R-BILL-ARCHIVE-01, R-SCHED-OVERDUE-01 | Где и с какой периодичностью запускаются задачи (в docstring — раз в час), и кто за этим следит? |
| D-18 | medium | Окно можно переполнить параллельными записями | §12: максимум мест на окно задаёт администратор; §2 Клиент: нельзя записаться на занятое время | services/scheduling/service.py::book:136 считает записи без блокировки<br>БД: ограничения на число записей в окне нет; trg_slot_capacity_limit проверяет только capacity окна, а не записи | R-SCHED-BOOK-01, R-SCHED-SLOT-03 | Нужна ли блокировка окна (SELECT … FOR UPDATE) или триггер на bookings? |
| D-19 | medium | После закрытия заявки ссылка на сдачу и запись на сдачу остаются активными | §13: по закрытой заявке ссылка не работает | scheduling не подписан на переход books_out->closed; services/scheduling/service.py::return_book:267 не закрывает запись с purpose=return<br>БД: uq_booking_links_one_active | R-SCHED-LINK-03, R-SCHED-RETURN-01 | Гасить ли ссылку и записи на сдачу при закрытии заявки (или при возврате последней книги)? |
| D-20 | low | Бухгалтер может взять заявку любого этапа и вида, кроме debt | §2 Бухгалтер: берёт в работу платные заявки, прошедшие проверку; §3: у социальной заявки бухгалтера нет, пока не понадобится штраф | services/billing/service.py::take_application:17 проверяет только kind≠debt<br>БД: PK billing.accountant_assignments(application_id) | R-BILL-ASSIGN-01, R-BILL-ASSIGN-02 | Ограничить ли закрепление этапами от awaiting_invoice (для paid) и наличием штрафа (для social)? |
| D-21 | medium | Социальные заявки между собой не дедуплицируются | §6: две заявки клиента по одной сфере — остаётся одна; исключение только между социальными и платными | services/applications/consumers.py::on_review_passed:43 вызывает close_duplicates только для debt; для social вызова нет | R-APP-DEDUP-01 | Должна ли вторая социальная заявка клиента по той же сфере закрываться как дубль? |
| D-22 | medium | Нет истории действий «кто и когда» | §16: все значимые действия сохраняются в истории заявки, удалить её нельзя | libs/bpm/engine.py::transition:53 не сохраняет actor; services/applications/listeners.py::_domain_events пишет stage_changed без исполнителя<br>БД: неизменяем только chat.messages (trg_chat_messages_immutable) | R-SCHEMA-HIST-01, R-CHAT-EVENTS-02, R-CHAT-EVENTS-07 | Считать ли ленту чата историей заявки (тогда в событиях нужен исполнитель) или нужен отдельный журнал аудита? |
| D-23 | medium | Заявку и данные клиента видит кто угодно; клиент заводится повторно | §16: проверяющий оператор видит только свою площадку; §2 Клиент: заявку не видит; §6: клиент заводится один раз | services/applications/api.py::get:55 без проверки; services/applications/service.py::create_client:63 без проверки дублей и роли<br>БД: у applications.clients нет уникальных ключей | R-SCHEMA-ACCESS-01, R-SCHEMA-CLIENT-01 | По какому признаку считать клиента тем же (паспорт, ФИО и дата рождения), и нужен ли уникальный индекс? |
| D-24 | low | Письма об отмене уходят по архивной заявке и не содержат новой ссылки | §5: пока заявка в архиве, письма не отправляются; §7: при смене площадки — письмо об отмене и новая ссылка | services/notifications/consumers.py::on_booking_cancelled:21 передаёт только starts_at; services/notifications/service.py::send:42 не проверяет этап | R-NOTIF-RESET-01, R-NOTIF-RENDER-02 | Отправлять ли письмо об отмене в момент архивации и добавлять ли в письмо после смены площадки новую ссылку? |
| D-25 | low | Книги и заявка — упрощения в смене книг и освобождении книг | §4: смена книг после счёта до оплаты — аннулировать и выставить счёт заново; §8: книги освобождаются после отметки о возврате | services/applications/service.py::change_books:239 — только draft и needs_rework; services/scheduling/service.py::issue_books:223 удаляет holds при выдаче | R-APP-BOOKS-01, R-SCHED-ISSUE-03 | Достаточно ли менять книги после проверки только через архив, и подтверждаете ли, что после выдачи книги учитываются в scheduling.loans, а не в holds? |
| D-26 | low | Чат неполон относительно схемы | §15: в чат попадают все события (назначения, платежи, перенос, неявка); к сообщениям прикрепляют файлы | services/chat/consumers.py::EVENT_TEXT — нет payment.fully_paid, payment.refunded, loan.lost, loan.damaged, books.issued и назначений; у chat.messages только body<br>БД: messages_check | R-CHAT-EVENTS-06, R-CHAT-EVENTS-07, R-CHAT-POST-03, R-SCHED-FINE-01 | Какие события обязательны в чате для первой версии и нужны ли вложения? |
| D-27 | low | Ограничение БД без правила — уникальное имя сферы | §1: сфера — тематический раздел; об уникальности названия не сказано | <br>БД: spheres_name_key (UNIQUE spheres.name) | R-SCHEMA-SPHERE-01 | Подтверждаете ли, что название сферы глобально уникально (а не в пределах площадки)? |
| D-28 | low | Удаление заявки не запрещено в БД | §4: удалить заявку нельзя | операции удаления нет<br>БД: application_books и attempts — ON DELETE CASCADE; триггера, запрещающего DELETE, нет | R-SCHEMA-APP-02, R-SCHEMA-APP-01 | Добавить ли триггер, запрещающий DELETE заявок и UPDATE operator_id? |
| D-29 | low | Снижение максимума площадки не трогает уже созданные окна | §12: в окне не больше мест, чем максимум площадки | services/scheduling/consumers.py::on_venue_settings_changed:35 обновляет только venue_limits<br>БД: trg_slot_capacity_limit срабатывает только на INSERT и UPDATE OF capacity | R-SCHED-VENUE-LIMIT-01, R-SCHED-SLOT-03 | Уменьшать ли capacity существующих будущих окон, если администратор снизил максимум? |

## Детерминированная сверка

### Ограничения БД без правил (скрытые правила) (9)

- ck_refunds_amount
- ck_refunds_done
- ck_refunds_status
- marketing.campaigns_guard_status
- marketing.sent_messages_freeze_body
- onboarding_requests_contact_email_check
- onboarding_requests_status_check
- sites_name_key
- uq_refunds_invoice

### ORM-модели и реальная схема БД (0)

- нет

### Проверки в коде, не покрытые правилами (1)

- services/reports/builders.py::build:181 DomainError: f'неизвестный тип отчёта: {other}'

### Литералы вместо настроек (5)

- services/partners/service.py::add_to_payout:498: литерал 32 совпадает с 
- services/scheduling/jobs.py::flag_overdue:16: литерал 30 совпадает с services/inventory/settings.py::ILL_LOAN_PERIOD_DAYS, libs/settings.py::LOAN_PERIOD_DAYS, services/subscriptions/settings.py::GRACE_DAYS, services/staff/settings.py::BRIEFING_VALID_DAYS, services/reports/settings.py::RETENTION_DAYS, services/partners/settings.py::ONBOARDING_REQUEST_TTL_DAYS, services/halls/settings.py::UNPAID_CANCEL_DAYS, libs/settings.py::REVIEW_ARCHIVE_DAYS, libs/settings.py::PAYMENT_ARCHIVE_DAYS
- services/subscriptions/jobs.py::expire_overdue:19: литерал 30 совпадает с services/subscriptions/settings.py::GRACE_DAYS, services/staff/settings.py::BRIEFING_VALID_DAYS, services/reports/settings.py::RETENTION_DAYS, services/partners/settings.py::ONBOARDING_REQUEST_TTL_DAYS, services/inventory/settings.py::ILL_LOAN_PERIOD_DAYS, services/halls/settings.py::UNPAID_CANCEL_DAYS, libs/settings.py::REVIEW_ARCHIVE_DAYS, libs/settings.py::PAYMENT_ARCHIVE_DAYS, libs/settings.py::LOAN_PERIOD_DAYS (вероятно services/subscriptions/settings.py::GRACE_DAYS)
- services/subscriptions/jobs.py::issue_renewal_invoices:82: литерал 1 совпадает с 
- services/subscriptions/service.py::period_for:34: литерал 1 совпадает с 

### События без подписчиков или публикаторов (28)

- halls.booking_created: нет подписчиков
- halls.booking_held: нет подписчиков
- inventory.copy_damaged: нет публикаторов
- inventory.copy_lost: нет публикаторов
- inventory.copy_registered: нет публикаторов
- inventory.copy_relocated: нет публикаторов
- inventory.copy_written_off: нет публикаторов
- inventory.ill_issued: нет публикаторов
- inventory.ill_returned: нет публикаторов
- inventory.partner_resumed: нет подписчиков
- inventory.partner_suspended: нет подписчиков
- inventory.transfer_cancelled: нет публикаторов
- inventory.transfer_received: нет публикаторов
- inventory.transfer_shipped: нет публикаторов
- partners.contract_activated: нет подписчиков
- partners.contract_expired: нет подписчиков
- partners.contract_rate_changed: нет подписчиков
- partners.contract_resumed: нет подписчиков
- partners.contract_suspended: нет подписчиков
- partners.contract_terminated: нет подписчиков
- partners.deal_cancelled: нет подписчиков
- partners.deal_created: нет подписчиков
- partners.payout_closed: нет подписчиков
- partners.request_closed_duplicate: нет подписчиков
- partners.request_rejected: нет подписчиков
- partners.request_submitted: нет подписчиков
- staff.clearance_granted: нет подписчиков
- staff.employee_hired: нет подписчиков

### Модули с обработчиками вне services/wiring.py (9)

- services.halls.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.inventory.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.lectures.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.marketing.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.partners.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.reports.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.staff.consumers: регистрирует обработчики, но не подключён в services/wiring.py
- services.staff.listeners: регистрирует обработчики, но не подключён в services/wiring.py
- services.subscriptions.consumers: регистрирует обработчики, но не подключён в services/wiring.py

### Условия процесса без реализации или неиспользуемые (0)

- нет

### Переходы процесса, которые код не выполняет (0)

- нет

### Роли схемы, которые код не проверяет (3)

- admin (Администратор): нет параметра-исполнителя в коде и переходов процесса
- representative (Представитель клиента): нет параметра-исполнителя в коде и переходов процесса
- reviewer_lead (Руководитель проверяющих): нет параметра-исполнителя в коде и переходов процесса

### Фоновые задачи без запуска в репозитории (24)

- services/applications/jobs.py::archive_stale: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/halls/jobs.py::cancel_unpaid: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/halls/jobs.py::close_past_events: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/inventory/jobs.py::accrue_ill_penalties: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/inventory/jobs.py::expire_stale_transfers: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/inventory/jobs.py::flag_overdue_ill: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/lectures/jobs.py::close_waitlists: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/lectures/jobs.py::finish_past_events: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/lectures/jobs.py::send_reminders: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/marketing/jobs.py::launch_due: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/marketing/jobs.py::purge_test_messages: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/partners/jobs.py::close_payouts: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/partners/jobs.py::expire_contracts: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/partners/jobs.py::expire_requests: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/partners/jobs.py::flag_overdue_credit: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/reports/jobs.py::fail_stuck_runs: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/reports/jobs.py::purge_old_runs: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/reports/jobs.py::run_scheduled: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/scheduling/jobs.py::flag_overdue: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/staff/jobs.py::close_finished_shifts: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/staff/jobs.py::expire_clearances: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/subscriptions/jobs.py::expire_overdue: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/subscriptions/jobs.py::expire_stale_pending: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория
- services/subscriptions/jobs.py::issue_renewal_invoices: фоновая задача не вызывается из кода (только из тестов) — планировщик вне репозитория

### Правила с расхождением со схемой (62)

- R-APP-ARCHIVE-01: Схема: месяц. Код: фиксированные 30 дней из настройки. Схема §9 (платная): уходит в архив, если за месяц не получены данные для счёта — заявки на awaiting_invoice (без выставленного счёта) задача не архивирует никогда.
- R-APP-ARCHIVE-02: Код архивирует и частично оплаченные заявки (paid_amount < amount) как unpaid; возврат поступившей части платежа при этом не инициируется — схема этот случай не описывает.
- R-APP-BOOKS-01: Схема (§4): если после выставления счёта до оплаты меняются книги, счёт аннулируется и выставляется заново. Код: после проверки книги меняются только через архив и возврат из него (R-APP-UNARCHIVE-02); других путей смены книг нет.
- R-APP-CLIENT-01: Схема: данные клиента обновляет только проверяющий. Код: при вызове без source_application_id роль и закрепление не проверяются — обновить данные может кто угодно.
- R-APP-CLIENT-03: Схема: перепроверка не должна приводить к потере заявки. Код: review_started_at остаётся от первой проверки, поэтому возвращённая на проверку заявка, у которой проверка началась больше REVIEW_ARCHIVE_DAYS назад, при ближайшем запуске archive_stale уходит в архив с outcome=no_data.
- R-APP-DEDUP-01: Схема: остаётся та заявка, что первой дошла до записи. Код: OPEN_STAGES включает awaiting_issue, поэтому более поздний «победитель» (например, заявка в долг, прошедшая проверку после оплаты платной) закрывает уже дошедшую до записи и оплаченную заявку. Для социальных заявок дедупликация не запускается вообще.
- R-APP-REVIEW-02: Схема: назначает и переназначает только руководитель проверяющих. Код: роль вызывающего не проверяется, назначить может любой вызывающий.
- R-APP-UNARCHIVE-03: Схема: новый счёт выставляется после проверки, если сумма изменилась. Код: счёт аннулируется сразу при возврате из архива, до проверки; сравнивается только цена по прайсу без надбавки.
- R-APP-VENUE-CHANGE-02: Схема: social/debt меняют площадку только до формирования ссылки на запись. Код сервиса этого не проверяет — запрет срабатывает только в триггере БД на flush, без доменного сообщения.
- R-APP-VENUE-CHANGE-03: Схема: до оплаты счёт аннулируется и выставляется заново по прайсу и реквизитам новой площадки. Код: при частичной оплате (paid_amount > 0) счёт не аннулируется, а заявка остаётся в awaiting_payment со счётом на реквизиты и цены старой площадки.
- R-BILL-ASSIGN-01: Схема: бухгалтер берёт в работу платные заявки, прошедшие проверку. Код не проверяет этап и роль: заявку можно взять на любом этапе, в том числе в черновике или после закрытия.
- R-BILL-CANCEL-02: Схема: аннулирует счёт бухгалтер, закреплённый за заявкой. Код cancel_invoice не проверяет роль и закрепление, причину не требует. HTTP-маршрута для него нет: вызывается только подписчиками.
- R-BILL-DUPLICATE-01: Схема: счёт заявки-дубля аннулируется. Код: частично оплаченный счёт заявки-дубля остаётся действующим, возврат по нему автоматически не инициируется.
- R-BILL-FINE-02: Если ставка не настроена, DomainError поднимается внутри обработчика loan.overdue, loan.lost или loan.damaged: штраф не создаётся, а заявку можно закрыть без него. Нулевую ставку БД допускает, но счёт на неё не выставить (invoices_amount_check требует amount > 0).
- R-BILL-FINE-INVOICE-01: Код не проверяет, оплачен ли уже штраф и есть ли по нему действующий счёт. На один штраф можно выставить несколько счетов: уникальный индекс действует только для kind='books'.
- R-BILL-PAYMENT-03: Схема: привязывает платежи только главный бухгалтер. Код не проверяет роль: chief_id приходит в теле запроса POST /invoices/{invoice_id}/payments и только записывается в linked_by.
- R-BILL-REFUND-01: Схема: возврат оформляет только главный бухгалтер. Код не проверяет роль, повторный возврат и возврат отвязанного платежа. Статус штрафа (paid) при возврате платежа по счёту на штраф обратно не меняется.
- R-BILL-UNARCHIVE-01: Решение «сумма изменилась» принимает публикатор (флаг amount_changed), billing сумму не пересчитывает. Если amount_changed=true, а по счёту есть частичная оплата, cancel_invoice поднимет DomainError внутри обработчика события.
- R-BILL-UNLINK-01: Код не проверяет роль главного бухгалтера и не публикует событие. Если отвязать платёж после полной оплаты, заявка остаётся в «Ожидает выдачи», а оплаченный по нему штраф — в статусе paid. Повторная отвязка перезаписывает unlinked_at и причину.
- R-BILL-VENUE-CHANGE-01: Схема: после оплаты площадку меняют только через возврат платежа. Код: счёт с частичной оплатой подписчик не аннулирует и ошибку не поднимает. Если смена площадки прошла (запрет в applications рассчитан на полную оплату), счёт остаётся на реквизитах и цене старой площадки. Счета на штрафы при смене площадки не трогаются.
- R-CHAT-AUTH-01: Схема: доступ к чату определяется ролью сотрудника и закреплением за заявкой. Код: роль приходит от клиента API — если передать role=admin, проверка участника для чтения отключается.
- R-CHAT-EVENTS-06: Схема называет перенос и неявку отдельными событиями чата. Код: перенос не отличить от отмены с новой записью, неявка показывается кодом причины «no_show» внутри текста об отмене.
- R-CHAT-EVENTS-07: Схема: в чат автоматически попадают все события заявки, включая назначения и платежи. Код: назначения, возврат и отвязка платежа, порча и утеря книг в чате не фиксируются.
- R-CHAT-POST-03: Схема: к сообщениям можно прикреплять файлы. Код: у сообщения есть только текст (body), поддержки вложений нет ни в модели, ни в API.
- R-INVENTORY-COPY-01: Формат номера проверяет только код. CHECK на inventory.copies.inventory_no нет, поэтому прямая запись в БД может сохранить номер в любом формате.
- R-INVENTORY-COPY-03: В срезе графа у inventory.copy_registered и других событий остатка не указан публикатор: их публикует _stock_event(topic=…), и экстрактор такой вызов не распознаёт.
- R-INVENTORY-CUSTODIAN-01: В общей схеме роли «хранитель фонда» нет: в модели ролей проекта (operator, admin и т.д.) её тоже нет. Полномочия держатся только на таблице inventory.custodians, а employee_id приходит в теле запроса (custodian_id) и не сверяется с аутентифицированным пользователем.
- R-INVENTORY-ILL-04: Число продлений нигде не хранится: оно выводится из разницы due_at и issued_at. Поэтому смена ILL_LOAN_PERIOD_DAYS или ILL_RENEWAL_DAYS меняет лимит и для уже действующих выдач.
- R-INVENTORY-ILL-07: Компенсация одинакова для любых изданий и партнёров и не зависит от стоимости книги.
- R-INVENTORY-PARTNER-02: На inventory.partner_suspended нет подписчиков: никого не уведомляют.
- R-INVENTORY-PARTNER-03: На inventory.partner_resumed нет подписчиков. Приостановка снимается только оплатой, другого пути (например, вручную) нет.
- R-INVENTORY-PENALTY-02: В репозитории не найден планировщик, запускающий эту задачу: она вызывается только из тестов.
- R-INVENTORY-PENALTY-03: В докстринге задача названа ежедневной, но расписание в коде не задано и планировщик в репозитории не найден.
- R-INVENTORY-PENALTY-06: Если выдача просрочена, но flag_overdue_ill ещё не отработал, пеня за просрочку при утере не начисляется вовсе: on_ill_returned при утере не вызывается, а пени overdue ещё нет.
- R-INVENTORY-PENALTY-07: В settle_penalty нет проверки прав и HTTP-маршрута; связи с платежами billing нет, оплата отмечается прямым вызовом.
- R-INVENTORY-RECONCILE-01: Код проверяет только хранителя площадки назначения, площадку-источник не проверяет: хранитель любой площадки может «забрать» к себе экземпляр чужой. Состояние экземпляра код не проверяет, его блокирует только триггер БД. У функции нет HTTP-маршрута.
- R-INVENTORY-STOCK-02: На inventory.copy_lost и inventory.copy_damaged on_stock_changed не подписан: остаток после утери или порчи пересчитывается только через последующее copy_written_off. Пока событие списания не обработано, total и available включают экземпляр в состоянии lost/damaged по старому значению.
- R-INVENTORY-TRANSFER-04: Текст ошибки «хотя бы один» зашит в код и не меняется вместе с MIN_COPIES_ON_VENUE. Учитываются только уже оформленные перемещения: два одновременных запроса по разным экземплярам могут вместе вывести площадку ниже минимума (ограничения в БД нет).
- R-INVENTORY-TRANSFER-08: В репозитории не найден планировщик, вызывающий jobs.py модуля inventory: задача запускается только из тестов. Для перемещений, застрявших в in_transit, таймера нет.
- R-LECTURES-EVENT-01: В тексте ошибки срок записан литералом («за сутки»), а проверка берёт его из настройки MIN_LEAD_TIME. Если настройку поменять, сообщение станет неверным.
- R-NOTIF-RENDER-02: Схема (§7): при смене площадки клиент и представитель получают письмо об отмене и новую ссылку. Код: в письме об отмене нет ссылки, а отдельного письма со ссылкой модуль не отправляет.
- R-NOTIF-RESET-01: Схема (§5): пока заявка в архиве, письма не отправляются. Код: в момент архивирования письмо об отмене всё-таки уходит. В send нет проверки этапа и архивного статуса, поэтому любое событие booking.* по заявке в архиве тоже приведёт к письму.
- R-NOTIF-TEMPLATE-07: Схема (§2, §17): шаблоны писем настраивает только администратор в админке. Код: в set_template нет проверки роли и нет точки входа для администратора.
- R-SCHED-BOOK-01: Число свободных мест проверяется подсчётом в коде без блокировки. При параллельных записях окно можно переполнить: в БД нет ограничения на число записей в окне.
- R-SCHED-BOOK-03: Схема: оператор записывает в системе, клиент и представитель — по ссылке. Код: публичный эндпоинт POST /links/{token}/bookings принимает booked_by=operator от кого угодно с токеном.
- R-SCHED-CANCEL-02: Схема: менее чем за два дня отменить или перенести визит может только оператор. Код: роль определяется параметром by из запроса DELETE /bookings/{booking_id}?by=..., без проверки, кто вызывает. Любой, передав by=operator, обходит ограничение, и личность оператора не сверяется. Текст ошибки «за два дня» зашит в строку и не зависит от настройки.
- R-SCHED-FINE-01: Схема (§15): в чат попадают все события заявки. Код: loan.damaged и loan.lost в EVENT_TEXT чата нет, в чат они не попадают.
- R-SCHED-ISSUE-03: Схема (§8): книги освобождаются после отметки о возврате. Код: holds удаляются уже при выдаче. Открытые выдачи учитываются только в scheduling.loans.
- R-SCHED-LINK-03: Схема: по закрытой заявке ссылка не работает. Код: на закрытие заявки (books_out->closed) модуль не подписан, ссылка на сдачу (purpose=return) после закрытия остаётся активной.
- R-SCHED-OVERDUE-01: Срок просрочки зашит литералом timedelta(days=30), а не берётся из LOAN_PERIOD_DAYS или loans.due_at. Если настройку изменить, due_at и момент начисления штрафа разойдутся. Схема: «месяц с выдачи», а не фиксированные 30 дней. Книга, возвращённая с опозданием до запуска задачи, штраф не получает.
- R-SCHED-RETURN-01: Возврат не связан с записью на сдачу: return_book не требует записи и не закрывает её, поэтому запись с purpose=return остаётся в статусе active после приёма книг.
- R-SCHED-VENUE-CHANGE-01: Схема: у социальных заявок и заявок в долг площадку меняют только до формирования ссылки, после выдачи — никогда. Код change_venue блокирует смену только для paid на awaiting_issue и books_out. У debt/social на этапе books_out смена проходит: записи на сдачу отменяются, ссылка на сдачу гаснет, а новая не выпускается (выпуск только при awaiting_issue) — клиент не может записаться на сдачу. Письмо об отмене уходит по шаблону старой площадки (venue_id окна).
- R-SCHEMA-ACCESS-01: в проекте не реализовано: GET /applications/{application_id} (services/applications/api.py::get) отдаёт заявку без идентификации и проверки роли
- R-SCHEMA-ADMIN-01: в проекте не реализовано: billing.fine_rates только читается в services/billing/service.py::create_fine; функции или эндпоинта для записи ставок нет ни в applications/admin.py, ни в billing
- R-SCHEMA-APP-01: реализовано неявно: operator_id задаётся только при создании и в коде нигде не меняется; в БД защиты нет — trg_applications_core_immutable охраняет только sphere_id и representative_id
- R-SCHEMA-APP-02: реализовано неявно: в коде нет операции удаления, но в БД запрета нет — у application_books и attempts стоит ON DELETE CASCADE, и DELETE заявки удалит вместе с ней историю попыток
- R-SCHEMA-CLIENT-01: реализовано частично: create_client не проверяет роль; у applications.clients нет уникальности (паспорт, ФИО+дата рождения), поэтому один и тот же клиент может быть заведён дважды — и тогда дедупликация по client_id+sphere_id не сработает
- R-SCHEMA-FINE-01: реализовано частично: система только пишет в чат «Срыв срока возврата книги»; задачи или напоминания оператору нет, факт уведомления не фиксируется
- R-SCHEMA-HIST-01: в проекте не реализовано: libs/bpm/engine.py::transition принимает actor, но не сохраняет его; application.stage_changed передаёт только from и to, без исполнителя. Единственный неизменяемый журнал — chat.messages (события без автора). Назначение проверяющего, бухгалтера и отвязка платежа нигде не фиксируются
- R-SCHEMA-NOTIF-01: в проекте не реализовано: scheduling.issue_link создаёт токен, но на application.ready_for_booking и books.issued notifications не подписан, а emails_type_check и templates_type_check допускают только booking и cancel — письма со ссылкой нет
- R-SCHEMA-NOTIF-02: в проекте не реализовано: нет операции повторной отправки и нет типа письма со ссылкой
- R-SCHEMA-ROLE-01: в проекте не реализовано: справочника сотрудников и ролей нет, идентификаторы (operator_id, reviewer_id, chief_id, accountant_id) и роль чата приходят из запроса; один и тот же id может действовать в нескольких ролях

### Правила с неразрешёнными ссылками (2)

- R-MARKETING-CAMPAIGN-04: campaigns_guard_status
- R-MARKETING-MESSAGE-01: sent_messages_freeze_body
