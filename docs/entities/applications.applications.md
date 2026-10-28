<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.applications
Миграция: [`migrations/versions/0001_initial.py:79`](../../migrations/versions/0001_initial.py#L79)

## Поля
- id: integer NOT NULL PK
- client_id: integer NOT NULL
- representative_id: integer NOT NULL
- sphere_id: integer NOT NULL
- venue_id: integer NOT NULL
- kind: text NOT NULL
- stage: text NOT NULL
- operator_id: integer NOT NULL
- reviewer_id: integer
- site_checker_id: integer NOT NULL
- review_started_at: timestamp with time zone
- booking_reached_at: timestamp with time zone
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- client_id → applications.clients
- representative_id → applications.representatives
- sphere_id → applications.spheres
- venue_id → applications.venues
- applications.application_books.application_id → сюда
- applications.attempts.application_id → сюда

## Ограничения и триггеры
- applications_kind_check (check на applications.applications): CHECK ((kind = ANY (ARRAY['paid'::text, 'debt'::text, 'social'::text]))) (migrations/versions/0001_initial.py:85)
- applications_stage_check (check на applications.applications): CHECK ((stage = ANY (ARRAY['draft'::text, 'on_review'::text, 'needs_rework'::text, 'awaiting_invoice'::text, … (migrations/versions/0001_initial.py:86)
- ix_applications_client_sphere (index на applications.applications): CREATE INDEX ix_applications_client_sphere ON applications.applications USING btree (client_id, sphere_id) (migrations/versions/0001_initial.py:94)
- trg_applications_core_immutable: BEFORE UPDATE OF sphere_id, representative_id ON applications.applications FOR EACH ROW EXECUTE FUNCTION applications.f… (migrations/versions/0001_initial.py:121)
  - forbid_core_change(): 'sphere and representative of an application cannot be changed'
- trg_applications_venue_lock: BEFORE UPDATE OF venue_id ON applications.applications FOR EACH ROW EXECUTE FUNCTION applications.forbid_venue_change() (migrations/versions/0001_initial.py:141)
  - applications.forbid_venue_change(): 'venue change forbidden after books were issued'; 'venue change forbidden after booking link for % application'

## ORM
- services/applications/models.py::Application:82 (orm_model)

## Этапы (процесс application, bpm/application_process.yaml)
- debt: draft → on_review → awaiting_issue → books_out → closed
- paid: draft → on_review → awaiting_invoice → awaiting_payment → awaiting_issue → books_out → closed
- social: draft → on_review → awaiting_issue → books_out → closed

## Пишут (код)
- services/applications/consumers.py::on_books_issued [stage]
- services/applications/consumers.py::on_client_updated [stage]
- services/applications/consumers.py::on_fully_paid [stage]
- services/applications/consumers.py::on_invoice_cancelled [stage]
- services/applications/consumers.py::on_invoice_issued [stage]
- services/applications/dedup.py::close_duplicates [stage]
- services/applications/service.py::approve [stage]
- services/applications/service.py::archive [stage]
- services/applications/service.py::assign_reviewer [reviewer_id]
- services/applications/service.py::change_books [books]
- services/applications/service.py::change_venue [site_checker_id, venue_id]
- services/applications/service.py::close [stage]
- services/applications/service.py::create_application
- services/applications/service.py::mark_ready_for_booking [booking_reached_at]
- services/applications/service.py::return_for_rework [stage]
- services/applications/service.py::submit_for_review [review_started_at, stage]
- services/applications/service.py::unarchive [books, review_started_at, site_checker_id, stage, venue_id]

## Правила
- R-APP-ACCESS-01 Оператор работает только со своими заявками (подкреплено кодом и тестами)
- R-APP-ARCHIVE-03 Ручной архив и его последствия — закрытие попытки, сброс записей, сообщение в чат (⚠ расхождение со схемой или открытый вопрос)
- R-APP-BOOKING-01 Готовность к записи фиксируется и запускает выдачу ссылки на запись (подкреплено кодом и тестами)
- R-APP-BOOKS-01 Книги меняют только в черновике или на доработке (⚠ расхождение со схемой или открытый вопрос)
- R-APP-CHAT-01 Каждая смена этапа заявки пишется в чат (слушатель ORM) (подкреплено кодом и тестами)
- R-APP-CLIENT-03 Обновление клиента возвращает его заявки из ожидания счёта или оплаты на проверку (⚠ расхождение со схемой или открытый вопрос)
- R-APP-CLOSE-01 Закрывает заявку проверяющий оператор её площадки после возврата книг и погашения штрафов (подкреплено кодом и тестами)
- R-APP-CORE-01 Сферу и представителя заявки сменить нельзя (проверено человеком)
- R-APP-CREATE-01 Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя (подкреплено кодом и тестами)
- R-APP-CREATE-02 Сфера заявки должна быть активна на площадке (подкреплено кодом и тестами)
- R-APP-CREATE-04 При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка (подкреплено кодом и тестами)
- R-APP-DEDUP-01 Заявка, первой дошедшая до записи, закрывает остальные заявки клиента по той же сфере (⚠ расхождение со схемой или открытый вопрос)
- R-APP-ISSUE-01 Выдача книг переводит заявку в «Книги у клиента» (подкреплено кодом и тестами)
- R-APP-PAY-01 Выставление счёта за книги переводит заявку в ожидание оплаты (подкреплено кодом и тестами)
- R-APP-PAY-02 Аннулирование счёта за книги возвращает заявку в ожидание счёта (подкреплено кодом и тестами)
- R-APP-PAY-03 Только полная оплата счёта за книги открывает выдачу (подкреплено кодом и тестами)
- R-APP-REVIEW-01 Отправка на проверку фиксирует начало проверки один раз (⚠ расхождение со схемой или открытый вопрос)
- R-APP-REVIEW-02 Проверяющего назначают только до прохождения проверки (⚠ расхождение со схемой или открытый вопрос)
- R-APP-REVIEW-03 Подтверждает или возвращает заявку только назначенный проверяющий (подкреплено кодом и тестами)
- R-APP-REVIEW-04 Заявку нельзя подтвердить без ФИО, паспорта и даты рождения клиента (подкреплено кодом и тестами)
- R-APP-REVIEW-05 Этап после проверки зависит от вида заявки и наличия действующего счёта (проверено человеком)
- R-APP-UNARCHIVE-01 Возврат из архива начинает новую попытку и новую проверку (подкреплено кодом и тестами)
- R-APP-UNARCHIVE-02 При возврате из архива площадку и книги меняют, только если заявка не доходила до записи (⚠ расхождение со схемой или открытый вопрос)
- R-APP-UNARCHIVE-03 После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново
 (⚠ расхождение со схемой или открытый вопрос)
- R-APP-VENUE-CHANGE-01 Смену площадки выполняет оператор заявки; закрытую заявку не меняют (подкреплено кодом и тестами)
- R-APP-VENUE-CHANGE-02 Платной заявке после оплаты площадку не меняют; после выдачи книг — никому (⚠ расхождение со схемой или открытый вопрос)
- R-APP-VENUE-CHANGE-03 Смена площадки переназначает проверяющего оператора и запускает реакции billing, scheduling и chat (⚠ расхождение со схемой или открытый вопрос)
- R-BILL-CANCEL-03 Аннулирование счёта за книги возвращает заявку в «Ожидает счёта» (подкреплено кодом и тестами)
- R-BILL-INVOICE-08 Выставление счёта за книги переводит заявку в «Ожидает оплаты» (проверено человеком)
- R-BILL-PROCESS-01 Полная оплата счёта за книги открывает выдачу и закрывает дубли (⚠ расхождение со схемой или открытый вопрос)
- R-SCHED-ISSUE-03 После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента» (⚠ расхождение со схемой или открытый вопрос)
- R-SCHEMA-APP-01 Оператора заявки переназначить нельзя (⚠ расхождение со схемой или открытый вопрос)
