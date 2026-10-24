# Слепой аудит против эталона

Итого recall 79/79 = 1.00; hidden 48/48 = 1.00

## T01 — социальная заявка — смена площадки после ссылки на запись

recall 14/14, hidden 12/12, стоимость $0.96, входных токенов 449,950

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `application.ready_for_booking` (event, affected): Событие выпускает первую ссылку и выставляет booking_reached_at; при смене площадки оно не публикуется повторно, ссылку перевыпускает подписчик scheduling.
- `awaiting_issue->books_out` (bpm, affected): Этот переход (выдача) — граница, после которой площадку менять нельзя: проверка должна запрещать смену в books_out.
- `libs/web.py::install_error_handlers` (code, risk): Ошибка триггера приходит как DBAPIError и превращается в 409 с английским текстом; без явной Python-проверки debt/books_out пользователь увидит сырое сообщение БД.
- `migrations/versions/0001_initial.py::UPGRADE` (code, risk): Правка функции прямо в 0001 не дойдёт до уже развёрнутых БД; нужна отдельная ревизия. Хелпер _statements живёт в 0001 и в новую миграцию не импортируется.
- `migrations/versions/0002_social_venue_change.py::upgrade` (code, change): Нужна новая миграция (down_revision='0001') с CREATE OR REPLACE FUNCTION applications.forbid_venue_change() и downgrade, который возвращает старое тело функции.
- `on_review->awaiting_issue` (bpm, affected): На этом переходе для debt/social формируется ссылка на запись (mark_ready_for_booking) — с этого момента и действует снимаемое ограничение.
- `scheduling.holds` (db, affected): Холды книг, поставленные при записи на старой площадке, удаляются в reset_bookings и появятся снова при новой записи.
- `services/applications/api.py::change_venue` (code, affected): HTTP-эндпоинт смены площадки — через него оператор получит новое поведение.
- `services/applications/service.py::PAID_VENUE_LOCKED_STAGES` (config, change): Правило блокировки по стадиям задано отдельно от триггера и только для paid; при доработке его стоит обобщить по видам заявок (например, словарь kind→стадии), иначе Python и БД разойдутся.
- `services/applications/service.py::TERMINAL_STAGES` (config, risk): В TERMINAL_STAGES нет books_out, поэтому для social в books_out Python-проверка не срабатывает и запрет держится только на триггере (ответ 409 с текстом из БД).
- `services/applications/service.py::unarchive` (code, risk): Здесь есть родственное правило «дошла до записи — площадку не меняют» (booking_reached_at) без учёта вида заявки; надо решить, согласовывать ли его с новым правилом для social.
- `services/billing/service.py::create_fine` (code, affected): Ставки штрафов берутся по текущему venue_id заявки, поэтому после смены площадки применяются ставки новой площадки.
- `services/chat/service.py::participants` (code, affected): Участники чата считаются через site_checker_id: после смены площадки доступ к чату переходит к проверяющему новой площадки.
- `services/scheduling/service.py::book` (code, affected): Запись проверяет, что слот на площадке заявки; после смены площадки подходят только слоты новой.
- `services/scheduling/service.py::free_slots` (code, affected): Список свободных окон по новой ссылке строится по brief.venue_id, то есть по новой площадке.
- `services/scheduling/service.py::issue_books` (code, affected): Книги выдаёт site_checker площадки заявки, а он переназначается при смене площадки; выдача возможна только в awaiting_issue — это и есть граница «вплоть до выдачи».
- `tests/test_kinds.py::test_social_application_skips_invoice` (code, risk): Регрессионный путь social: awaiting_issue → выдача → books_out; должен остаться зелёным.
- `tests/test_venue_change.py::test_paid_venue_change_after_payment_forbidden` (code, risk): Если при обобщении PAID_VENUE_LOCKED_STAGES поменять текст ошибки, тест проверяет match='возврат платежа' и упадёт.
- `uq_bookings_one_active` (db, risk): Пока старая запись не отменена, новую запись на новой площадке сделать нельзя: сброс в reset_bookings обязателен.

## T02 — срок пользования 21 день

recall 9/9, hidden 5/5, стоимость $0.90, входных токенов 561,099

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `billing.fines` (db, affected): Штрафы за просрочку начнут записываться в эту таблицу раньше.
- `books_out->closed` (bpm, affected): Переход защищён условием `settled`, и на него влияет ранний штраф за просрочку.
- `scheduling.loans` (db, risk): Структуру таблицы менять не нужно (`due_at` считает приложение, значения по умолчанию в БД нет), но у уже выданных книг `due_at` остаётся +30: надо решить, нужна ли миграция данных, и проверка по `due_at` сохранит им старый срок.
- `services/applications/jobs.py::archive_stale` (code, risk): Соседняя фоновая задача с теми же «30 днями», которую при правке легко принять за срок пользования книгами.
- `services/applications/service.py::close` (code, affected): Выполняет переход `books_out->closed`; при открытом штрафе за просрочку переход отклонит условие.
- `services/billing/service.py::create_fine` (code, risk): Если для представителя и площадки нет `FineRate`, функция выбрасывает `DomainError`, и обработчик события падает; при более раннем наступлении просрочки это случится раньше.
- `services/scheduling/models.py::Loan` (code, affected): В модели есть поля `due_at` и `overdue_flagged`, на них опирается правильная проверка просрочки.
- `tests/factories.py::issue` (code, affected): Это готовый помощник для нового теста: он выдаёт книги в момент T0+3д 1ч, и от этой даты считаются 21 день и `due_at`.
- `tests/factories.py::seed` (code, affected): Заполняет `FineRate` с видом `overdue` для всех представителей и площадок, без этого тест штрафа за просрочку упадёт.
- `tests/test_loans.py::test_overdue_after_loan_period` (code, change): Тестов на срок выдачи и просрочку нет; нужен новый тест: `due_at` = выдача + 21 день, на 20-й день просрочки нет, после 21-го есть и создан штраф `overdue`.

## T03 — выдача после оплаты 50%

recall 14/14, hidden 11/11, стоимость $0.97, входных токенов 470,193

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `application.stage_changed` (event, affected): Слушатель ORM `before_flush` публикует смену этапа awaiting_payment→awaiting_issue в новый момент; её подхватывает лента чата.
- `awaiting_issue->archived` (bpm, affected): Этот переход (актор chief_accountant) используется при возврате платежа и теперь срабатывает для заявок, оплаченных частично.
- `billing.fines` (db, risk): Поле `fines.status` (open/paid) питает `open_fines_count` и условие `settled`; преждевременный `paid` откроет закрытие заявки с непогашенным штрафом.
- `books_out->closed` (bpm, risk): Переход защищён только условием `settled`, которое не учитывает недоплату по счёту за книги.
- `libs/events/relay.py::consume_forever` (code, risk): В проде воркеры подписываются на явный список топиков, который в репозитории не задан; новый топик о пороге нужно добавить в конфигурацию воркера сервиса заявок.
- `libs/settings.py::BOOKS_ISSUE_PAYMENT_SHARE` (config, change): Новая единая настройка порога 50%. Без неё порог разойдётся копиями по `link_payment`, условию `fully_paid` и фоновой задаче `archive_stale`, где сейчас по-своему повторяется сравнение «оплачено >= сумма».
- `libs/settings.py::PAYMENT_ARCHIVE_DAYS` (config, affected): Смысл настройки («счёт не оплачен») меняется на «не набран порог для выдачи»; стоит поправить комментарий.
- `on_review->awaiting_payment` (bpm, risk): Путь возврата на проверку при уже набранном пороге: из awaiting_payment такую заявку ничто не переведёт дальше.
- `payment.linked` (event, affected): Событие о привязке платежа публикуется по-прежнему; доплаты после выдачи будут продолжать приходить по уже выданной заявке.
- `services/applications/service.py::PAID_VENUE_LOCKED_STAGES` (code, affected): Смена площадки в awaiting_issue запрещена с текстом «после оплаты…»; теперь это действует уже после 50% оплаты.
- `services/applications/service.py::approve` (code, risk): Если порог набран, пока заявка была на повторной проверке (событие проигнорировано из-за `stage != awaiting_payment`), `approve` ставит её в awaiting_payment, и она там застревает: повторного события не будет.
- `services/billing/consumers.py::on_unarchived` (code, risk): При изменении суммы вызывает `cancel_invoice`, который упадёт, если к счёту остались привязаны платежи; при оплате частями такое вероятнее.
- `services/billing/consumers.py::on_venue_changed` (code, affected): Счёт аннулируется только если платежей нет (`paid_amount == 0`); частично оплаченный счёт при смене площадки до записи остаётся активным.
- `services/billing/public.py::active_books_invoice` (code, change): `InvoiceBrief` отдаёт только amount и paid_amount, и каждый потребитель сравнивает их сам; удобное место для общего признака «порог для выдачи достигнут», чтобы условие и фоновая задача считали одинаково.
- `services/billing/service.py::issue_fine_invoice` (code, risk): Счета на штрафы идут через тот же `link_payment`; порог должен зависеть от `invoice.kind`, иначе штраф получит `status="paid"` при 50%.
- `services/billing/service.py::refund_payment` (code, affected): Публикует `payment.refunded`, по которому заявку на этапе awaiting_issue отправляют в архив; при частичной оплате это происходит чаще.
- `services/billing/service.py::unlink_payment` (code, risk): Отвязка платежа не публикует события и не откатывает этап; после отвязки оплата может опуститься ниже 50%, а заявка останется в awaiting_issue.
- `services/chat/consumers.py::EVENT_TEXT` (config, affected): Лента чата пишет смену этапа и `payment.linked`; `payment.fully_paid` в словаре нет, поэтому если вводится новое событие о пороге, текст для него нужно добавить сознательно (или явно не добавлять).
- `services/scheduling/consumers.py::on_closed_duplicate` (code, affected): Сбрасывает записи и закреплённые книги у закрытых дублей, теперь в момент 50% оплаты победителя.
- `services/scheduling/service.py::issue_books` (code, affected): Выдача разрешена на этапе awaiting_issue, значит книги физически выдаются при недоплаченном счёте.
- `tests/factories.py::pay` (code, affected): Помощник по умолчанию платит всю сумму; на нём держатся `paid_application` и многие тесты, и для новых тестов нужны частичные суммы.
- `tests/test_archive.py::test_unpaid_invoice_goes_to_archive_after_month` (code, change): Нужен парный тест: заявка с оплатой не ниже порога в архив по сроку не уходит.
- `tests/test_paid_flow.py::test_fine_invoice_requires_full_payment` (code, change): Нужен новый тест: частичная оплата счёта на штраф (≥50%) не переводит штраф в `paid` и не даёт закрыть заявку.
- `tests/test_paid_flow.py::test_partial_payment_does_not_open_issue` (code, change): Тест проходит и сейчас (50 < 55), но его смысл нужно уточнить и добавить проверки: ровно 55 из 110 → awaiting_issue и ссылка на запись; 54.99 → остаётся awaiting_payment.
- `trg_invoices_cancel_guard` (db, risk): Триггер БД запрещает аннулировать счёт с привязанными платежами; это касается сценариев аннулирования для частично оплаченных счетов.

## T04 — дубли между социальной и платной заявками

recall 10/10, hidden 7/7, стоимость $0.92, входных токенов 487,010

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `applications.applications` (db, affected): CHECK по `stage` уже включает `closed_duplicate`, а CHECK по `kind` — все три вида; для этой задачи схему менять не нужно.
- `applications.attempts` (db, affected): Проигравшему пишется `outcome = 'duplicate'`; это значение должно проходить CHECK по outcome.
- `archived->closed_duplicate` (bpm, affected): Архивные заявки другой дорожки тоже попадут под закрытие как дубли, потому что `archived` входит в `OPEN_STAGES` и в `from` перехода.
- `awaiting_issue->closed_duplicate` (bpm, affected): Переход разрешён для всех видов заявок без ограничения `kinds`, поэтому через него можно закрыть платную заявку, уже оплаченную и ждущую выдачи.
- `awaiting_payment->awaiting_issue` (bpm, affected): Момент, когда платная заявка доходит до записи и закрывает дубли, теперь включая социальные.
- `awaiting_payment->closed_duplicate` (bpm, affected): Платная заявка в ожидании оплаты теперь может закрыться из-за прохождения проверки социальной заявки.
- `booking.cancelled` (event, affected): Отмена записи проигравшей заявки вызывает письмо клиенту и представителю.
- `ix_applications_client_sphere` (db, affected): Индекс, по которому ищутся заявки клиента по сфере в `close_duplicates`.
- `libs/events/outbox.py::dispatch_pending` (code, risk): Обработчики идут по порядку событий; `review_passed` и `ready_for_booking` обрабатываются отдельно, поэтому ссылка на запись может выдаться заявке, которую тут же закроют, и наоборот.
- `migrations/versions/0001_initial.py` (code, risk): Новая миграция схемы не нужна, но уже существующие в БД открытые пары «социальная + платная/долговая» новое правило задним числом не закроет; возможно, нужна миграция данных.
- `on_review->awaiting_issue` (bpm, affected): Путь social/debt через проверку сразу к записи; на нём социальная заявка становится победителем.
- `services/applications/dedup.py::OPEN_STAGES` (config, risk): Включает `awaiting_issue`, поэтому более поздний победитель закроет заявку, которая уже раньше дошла до записи; между дорожками это противоречит правилу «остаётся та, что первой дошла до записи».
- `services/applications/dedup.py::close_duplicates` (code, change): Пропускает другие заявки через `_same_track`, поэтому сейчас закрывает только дубли в той же дорожке; этот вызов нужно убрать.
- `services/applications/listeners.py::_domain_events` (code, affected): Слушатель ORM `before_flush` публикует `application.stage_changed` при переводе проигравшего в `closed_duplicate`.
- `services/applications/service.py::TERMINAL_STAGES` (config, risk): Список закрытых этапов продублирован здесь, в `OPEN_STAGES`, в `from` BPM-перехода и в `services/chat/service.py::post_message`; при правке набора этапов легко рассинхронизировать.
- `services/applications/service.py::mark_ready_for_booking` (code, affected): Ставит `booking_reached_at` социальной заявке при одобрении; это поле — признак «дошла до записи», на него можно опереться при выборе победителя.
- `services/applications/service.py::unarchive` (code, affected): Социальная заявка, возвращённая из архива, при повторном одобрении снова станет победителем и закроет открытые платные или долговые дубли.
- `services/billing/service.py::take_application` (code, affected): Бухгалтер может быть закреплён и за социальной заявкой; при её закрытии как дубля закрепление не снимается.
- `services/chat/consumers.py::EVENT_TEXT` (config, affected): Пишет в ленту чата «Заявка закрыта как дубль заявки {winner_id}» и смену этапа; теперь и для пар разных дорожек.
- `services/notifications/config.py::TEMPLATE_GROUP` (config, risk): У площадки TVR нет social-шаблонов, поэтому письмо об отмене для социального дубля там уйдёт со статусом `no_template`.
- `services/notifications/consumers.py::on_booking_cancelled` (code, affected): Отправит письмо об отмене по шаблону группы проигравшей заявки (social или paid).
- `tests/test_dedup.py` (code, change): Тестов на дубли сейчас нет вообще; нужны новые: социальная против платной, платная против социальной, долговая против социальной, и что заявка, уже дошедшая до записи, не закрывается.
- `trg_invoices_cancel_guard` (db, risk): Триггер БД запрещает аннулировать счёт с привязанным платежом; это вторая линия защиты для оплаченного проигравшего дубля.

## T05 — СНИЛС клиента

recall 12/12, hidden 4/4, стоимость $0.94, входных токенов 600,427

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `application.review_passed` (event, affected): Для клиентов без СНИЛС событие не публикуется, поэтому для debt-заявок не срабатывает close_duplicates в on_review_passed.
- `application.stage_changed` (event, affected): Возврат заявок на проверку из-за СНИЛС через тот же before_flush публикует stage_changed.
- `awaiting_invoice->on_review` (bpm, affected): Системный переход при обновлении данных клиента начнёт срабатывать и при смене СНИЛС.
- `awaiting_payment->on_review` (bpm, affected): Системный переход при обновлении данных клиента начнёт срабатывать и при смене СНИЛС.
- `libs/settings.py::REVIEW_ARCHIVE_DAYS` (config, affected): Срок, за который заявки без СНИЛС уйдут в архив фоновой задачей.
- `migrations/versions/0002_client_snils.py::upgrade` (code, change): Новая ревизия Alembic: conftest накатывает миграции до head, поэтому без неё тестовая БД останется без колонки. Имя файла условное.
- `on_review->archived` (bpm, risk): Возврат на проверку из-за client.updated не сбрасывает review_started_at, поэтому archive_stale может сразу архивировать старую заявку, которую вернули после смены СНИЛС. Проблема уже есть, но новое событие будет чаще её вызывать.
- `on_review->awaiting_invoice` (bpm, affected): Для платных заявок клиентов без СНИЛС переход теперь недостижим: approve отклоняет заявку раньше.
- `on_review->awaiting_issue` (bpm, affected): Заявки debt и social без СНИЛС тоже не пройдут проверку, поэтому не будет ни ready_for_booking, ни ссылки на запись.
- `on_review->awaiting_payment` (bpm, affected): Переход тоже закрыт для клиентов без СНИЛС. Заявка, возвращённая на проверку при активном счёте, пойдёт сюда через guard has_active_invoice.
- `on_review->needs_rework` (bpm, affected): Это штатный путь, если СНИЛС нет: проверяющий возвращает заявку на доработку.
- `services/applications/jobs.py::archive_stale` (code, affected): Заявки клиентов без СНИЛС зависнут в on_review/needs_rework и через REVIEW_ARCHIVE_DAYS уйдут в архив с outcome no_data; это затронет существующих клиентов, у которых СНИЛС ещё нет.
- `services/applications/service.py::create_client` (code, affected): Функция принимает произвольные **fields и после изменения модели сможет сохранить snils при создании клиента.
- `services/billing/guards.py::has_active_invoice` (code, affected): После возврата заявки на проверку из-за смены СНИЛС счёт остаётся активным, и повторный approve пойдёт через этот guard в awaiting_payment.
- `services/chat/consumers.py::EVENT_TEXT` (config, affected): Чат подписан на application.stage_changed через словарь, а не через decorator-импорт, и запишет в ленту возврат на проверку.
- `tests/test_archive.py::test_stuck_review_goes_to_archive_after_month` (code, risk): Тест опирается на то, что CLIENT_INCOMPLETE неполный. Если в seed добавить ему snils, тест не сломается, но если добавить passport, сломается; snils у него нужно оставить None.
- `tests/test_paid_flow.py::test_paid_application_full_path` (code, risk): Этот тест и вообще все сценарии через pass_review (test_kinds, test_scheduling, test_notifications, test_chat_api, test_venue_change, test_archive) сломаются, если в seed не добавить snils.
- `tests/test_review.py` (code, change): Нужны новые тесты: без СНИЛС approve падает, а смена snils проверяющим публикует client.updated и возвращает другие заявки клиента из awaiting_invoice/awaiting_payment в on_review.
- `tests/test_review.py::test_incomplete_client_goes_to_rework` (code, change): Тест дозаполняет только passport и birth_date и ждёт awaiting_invoice; без snils в update_client approve снова выдаст «не хватает данных».

## T06 — шаблоны писем для долга

recall 8/8, hidden 4/4, стоимость $0.86, входных токенов 542,255

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `applications.applications` (db, affected): Ограничение CHECK kind IN ('paid','debt','social') задаёт полный набор видов, и каждый должен быть ключом TEMPLATE_GROUP, иначе будет KeyError.
- `booking.cancelled` (event, affected): Событие публикует scheduling._cancel из cancel_booking, reschedule, remove_slot, mark_no_show и reset_bookings (archived/duplicate/venue_changed), и каждый из этих путей шлёт письмо cancel по группе debt.
- `booking.created` (event, affected): Событие публикует scheduling.book, в том числе при reschedule и book_by_operator; через него меняется письмо для заявок в долг.
- `migrations/versions/0001_initial.py::UPGRADE` (code, risk): Ограничение можно соблазниться поправить прямо в применённой миграции 0001, но так уже развёрнутые БД не обновятся; менять нужно отдельной миграцией.
- `notifications.emails` (db, risk): emails.template_id ссылается по FK на templates, поэтому downgrade новой миграции не сможет просто удалить шаблоны debt, на которые уже ссылаются письма; кроме того, CHECK status IN ('sent','no_template') запрещает вводить новые статусы, например 'fallback'.
- `services/applications/admin.py::set_representative_terms` (code, affected): Смена debt_allowed влияет на группу шаблонов только для новых заявок, а уже созданные продолжают получать письма по старому виду.
- `services/applications/public.py::get_brief` (code, affected): Отдаёт brief.kind, по которому notifications выбирает группу шаблонов.
- `services/applications/service.py::create_application` (code, affected): Вид debt фиксируется при создании по rep.debt_allowed, поэтому группа шаблонов определяется видом заявки, а не текущими условиями представителя.
- `services/scheduling/service.py::_cancel` (code, affected): Единственная точка публикации booking.cancelled, через неё косвенно запускаются письма cancel.
- `tests/conftest.py::migrated_db` (code, affected): Тесты прогоняют alembic upgrade head, поэтому новая миграция применяется в них автоматически и должна корректно выполняться через exec_driver_sql или op.execute.
- `tests/factories.py::seed` (code, risk): Сид создаёт шаблоны только групп paid и social (у TVR только paid); если добавить сюда шаблоны debt, изменятся письма для debt-заявок во всех тестах, а без них можно проверить запасной вариант.
- `tests/test_notifications.py::test_social_uses_social_templates` (code, change): Рядом с этим тестом нужно добавить новые: debt берёт шаблон debt, запасной paid при отсутствии debt (например, на TVR), отмена debt по шаблону cancel, set_template с kind_group='debt'.
- `tests/test_scheduling.py::test_booking_only_on_own_venue_and_sphere` (code, risk): В тестах scheduling debt-заявки (rep=2) записываются на визит и шлют письма; поиск шаблона не должен падать, если шаблона debt нет.

## T07 — новый максимум мест для будущих окон

recall 8/8, hidden 5/5, стоимость $0.95, входных токенов 574,162

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `booking.cancelled` (event, risk): Если для переполненных окон выбрать отмену лишних записей через _cancel, сработают письма (notifications) и лента чата.
- `libs/clock.py::now` (code, affected): Будущие окна определяются через starts_at > clock.now(); в тестах время заморожено на T0, это нужно учесть для прошедших окон.
- `libs/events/outbox.py::dispatch_pending` (code, affected): В тестах событие доставляется синхронно в отдельной транзакции после act(), поэтому окна меняются только после dispatch, а не в транзакции админки.
- `libs/events/relay.py::consume_forever` (code, risk): В проде доставка как минимум один раз (xack после обработчика): повторная обработка события должна быть безопасной; с фильтром capacity == old_max из payload она безопасна.
- `scheduling.slots` (db, affected): Таблица окон с CHECK (capacity > 0); здесь выполняется массовый UPDATE.
- `services/applications/models.py::Venue` (code, risk): Максимум хранится в двух местах (applications.venues.max_slot_capacity и scheduling.venue_limits.max_capacity); если взять old из реплики, а не из payload, при рассинхроне правило применится к другому значению.
- `services/applications/public.py::get_venue` (code, affected): VenueInfo.max_slot_capacity — третий способ узнать максимум; использовать его в scheduling вместо реплики нельзя, иначе триггер и сервис будут расходиться.
- `services/chat/consumers.py::EVENT_TEXT` (config, risk): Если добавить venue.settings_changed или новое событие про окно в ленту чата, обработчик упадёт: в payload нет application_id.
- `services/scheduling/api.py::slots` (code, affected): Публичный API отдаёт capacity окна (SlotOut), клиенты увидят новое значение.
- `services/scheduling/models.py::VenueLimit` (code, affected): ORM-модель реплики: её старое значение можно взять как запасной источник old_max, а docstring описывает, что обновляется только лимит.
- `services/scheduling/service.py::_active_bookings` (code, risk): При уменьшении максимума у окна может быть больше активных записей, чем новый capacity: reduce_capacity такое запрещает, а массовое обновление нет — получится переполненное окно, нужно решить, что с ним делать.
- `services/scheduling/service.py::apply_venue_max_capacity` (code, change): Массовое обновление окон (venue_id, capacity == old, starts_at > clock.now()) по стилю модуля лучше вынести в отдельную функцию сервиса, как reset_bookings или issue_link; имя функции условное.
- `services/scheduling/service.py::book` (code, affected): Проверка «нет свободных мест» сравнивает число активных записей со Slot.capacity.
- `services/scheduling/service.py::create_slot` (code, risk): Окно, созданное с явным capacity, равным максимуму, не отличить от окна по умолчанию, а окно с явным меньшим capacity под правило не попадёт; без флага в схеме это неоднозначность.
- `services/scheduling/service.py::free_slots` (code, affected): Видимость свободных окон зависит от Slot.capacity, поэтому после смены максимума выдача окон клиенту изменится.
- `services/wiring.py::MODULES` (config, affected): Обработчик подключается через services.scheduling.consumers в wiring.load(); если логику вынести в новый модуль, его нужно добавить сюда.
- `tests/factories.py::seed` (code, affected): В тестах MSK/KZN имеют лимит 3, TVR — 2, ADMIN уже объявлен; окна создаёт factories.slot, максимум меняется через act(admin.set_venue_max_capacity, ...).
- `tests/test_scheduling.py` (code, change): Нужны тесты: окно со старым максимумом получает новый при увеличении и при уменьшении; окно, уменьшенное проверяющим, не меняется; прошедшее окно не меняется; окна других площадок не меняются.
- `tests/test_scheduling.py::test_slot_capacity_cannot_exceed_venue_maximum` (code, risk): Существующий тест на триггер должен остаться зелёным: само правило «capacity ≤ максимум» не меняется.

## T08 — контрольная локальная задача — переименование поля API чата

recall 4/4, hidden 0/0, стоимость $0.31, входных токенов 117,465

**Пропущено аудитором (проверить: связь действительно скрытая или эталон ошибочен):**
- нет

**Найдено аудитором, нет в эталоне (решить: добавить в эталон или отклонить):**
- `application.stage_changed` (event, affected): Подписчик чата превращает событие в сообщение ленты; тест проверяет его текст через API, поэтому цепочка событие → чат → API затронута переименованием.
- `chat.messages` (db, affected): Столбец `body text NOT NULL` остаётся как есть, миграция не нужна.
- `services/chat/api.py::list_` (code, affected): Эндпоинт GET списка сообщений, его JSON-ответ меняет поле с `body` на `text` через MessageOut и `_out`.
- `services/chat/api.py::post` (code, change): Передаёт в сервис `body.body`; после переименования это `body.text`, где `body` — имя параметра запроса, и его можно переименовать для ясности.
- `services/chat/consumers.py::EVENT_TEXT` (config, affected): Словарь шаблонов событий, которые через `_handler` и `log_event` попадают в чат; их текст теперь будет виден клиентам в поле `text`.
- `services/chat/models.py::Message` (code, affected): ORM-атрибут `body` по задаче остаётся (хранение не меняется), и API должен явно отображать его в `text`.
- `services/chat/service.py::log_event` (code, affected): Сохраняет текст системных событий в `body`; в API эти сообщения теперь будут отдаваться в поле `text`.
- `services/chat/service.py::post_message` (code, affected): Принимает позиционный аргумент `body` и пишет его в `Message.body`; сигнатуру можно не менять, но это граница, где API-имя `text` переходит в столбец `body`.
- `services/notifications/models.py::Email` (code, risk): Поле `body` письма читается в `notifications/service.py:52` и `tests/test_notifications.py:24`, трогать его нельзя.
- `services/notifications/models.py::Template` (code, risk): Здесь тоже есть поле `body` (шаблоны уведомлений), но к чату оно не относится; при массовой замене его легко ошибочно переименовать.
- `tests/test_chat_api.py::test_operator_posts_and_reads` (code, change): Отправляет `{"body": ...}` и проверяет `r.json()[-1]["body"]`; без правки получит 422 и KeyError.
- `tests/test_chat_api.py::test_outsider_cannot_post` (code, change): Отправляет `{"body": "x"}`; после переименования вернётся 422 (нет обязательного `text`) вместо ожидаемого 403, и тест упадёт.
- `tests/test_chat_api.py::test_stage_changes_appear_in_chat` (code, change): Читает `m["body"]` у событийных сообщений, после переименования будет KeyError.
- `trg_chat_messages_immutable` (db, risk): Триггер запрещает UPDATE и DELETE в `chat.messages`; любая попытка решить задачу миграцией с переименованием или переносом данных упадёт.
