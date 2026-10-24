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
- R-APP-ACCESS-01 [draft] Оператор работает только со своими заявками
- R-APP-ARCHIVE-01 [draft] Заявка, застрявшая на проверке или доработке дольше REVIEW_ARCHIVE_DAYS, уходит в архив
- R-APP-ARCHIVE-02 [draft] Платная заявка без полной оплаты дольше PAYMENT_ARCHIVE_DAYS уходит в архив
- R-APP-ARCHIVE-03 [draft] Ручной архив и его последствия — закрытие попытки, сброс записей, сообщение в чат
- R-APP-CREATE-01 [draft] Вид заявки определяется при создании по флагу «социальная» и признаку долга представителя
- R-APP-CREATE-02 [draft] Сфера заявки должна быть активна на площадке
- R-APP-CREATE-04 [draft] При создании заявки закрепляется проверяющий оператор площадки и открывается первая попытка
- R-APP-DEDUP-01 [draft] Заявка, первой дошедшая до записи, закрывает остальные заявки клиента по той же сфере
- R-APP-PAY-04 [verified] Возврат платежа по оплаченной заявке отправляет её в архив с отметкой «возврат»
- R-APP-UNARCHIVE-01 [draft] Возврат из архива начинает новую попытку и новую проверку
- R-APP-UNARCHIVE-02 [draft] При возврате из архива площадку и книги меняют, только если заявка не доходила до записи
- R-APP-UNARCHIVE-03 [draft] После возврата из архива счёт аннулируется при изменении суммы, иначе срок оплаты отсчитывается заново

- R-SCHEMA-APP-01 [draft] Оператора заявки переназначить нельзя
