<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.attempts
Миграция: [`migrations/versions/0001_initial.py:102`](../../migrations/versions/0001_initial.py#L102)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- no: integer NOT NULL
- started_at: timestamp with time zone NOT NULL
- ended_at: timestamp with time zone
- outcome: text

## Связи (FK)
- application_id → applications.applications

## Ограничения и триггеры
- attempts_outcome_check (check на applications.attempts): CHECK ((outcome = ANY (ARRAY['no_data'::text, 'unpaid'::text, 'client_declined'::text, 'refund'::text, 'dupli… (migrations/versions/0001_initial.py:108)
- attempts_application_id_no_key (unique на applications.attempts): UNIQUE (application_id, no) (migrations/versions/0001_initial.py:109)

## ORM
- services/applications/models.py::Attempt:118 (orm_model)

## Пишут (код)
- services/applications/dedup.py::close_duplicates [ended_at, outcome]
- services/applications/service.py::archive [ended_at, outcome]
- services/applications/service.py::create_application
- services/applications/service.py::unarchive

## Правила
- R-APP-ACCESS-01 Оператор работает только со своими заявками (подкреплено кодом и тестами)
- R-APP-ARCHIVE-01 Заявка, застрявшая на проверке или доработке дольше REVIEW_ARCHIVE_DAYS, уходит в архив (⚠ расхождение со схемой или открытый вопрос)
- R-APP-ARCHIVE-02 Платная заявка без полной оплаты дольше PAYMENT_ARCHIVE_DAYS уходит в архив (⚠ расхождение со схемой или открытый вопрос)
- R-APP-ARCHIVE-03 Ручной архив и его последствия — закрытие попытки, сброс записей, сообщение в чат (⚠ расхождение со схемой или открытый вопрос)
- R-APP-CREATE-01 Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя (подкреплено кодом и тестами)
- R-APP-CREATE-02 Сфера заявки должна быть активна на площадке (подкреплено кодом и тестами)
- R-APP-CREATE-04 При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка (подкреплено кодом и тестами)
- R-APP-DEDUP-01 Заявка, первой дошедшая до записи, закрывает остальные заявки клиента по той же сфере (⚠ расхождение со схемой или открытый вопрос)
- R-APP-PAY-04 Возврат платежа по оплаченной заявке отправляет её в архив с отметкой «возврат» (⚠ расхождение со схемой или открытый вопрос)
- R-APP-UNARCHIVE-01 Возврат из архива начинает новую попытку и новую проверку (подкреплено кодом и тестами)
- R-APP-UNARCHIVE-02 При возврате из архива площадку и книги меняют, только если заявка не доходила до записи (⚠ расхождение со схемой или открытый вопрос)
- R-APP-UNARCHIVE-03 После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново
 (⚠ расхождение со схемой или открытый вопрос)
- R-SCHEMA-APP-01 Оператора заявки переназначить нельзя (⚠ расхождение со схемой или открытый вопрос)
