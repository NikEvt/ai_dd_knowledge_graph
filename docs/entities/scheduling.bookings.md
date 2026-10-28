<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.bookings
Миграция: [`migrations/versions/0001_initial.py:273`](../../migrations/versions/0001_initial.py#L273)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- slot_id: integer NOT NULL
- purpose: text NOT NULL
- status: text NOT NULL
- booked_by: text NOT NULL
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- slot_id → scheduling.slots

## Ограничения и триггеры
- bookings_booked_by_check (check на scheduling.bookings): CHECK ((booked_by = ANY (ARRAY['client'::text, 'representative'::text, 'operator'::text]))) (migrations/versions/0001_initial.py:279)
- bookings_purpose_check (check на scheduling.bookings): CHECK ((purpose = ANY (ARRAY['issue'::text, 'return'::text]))) (migrations/versions/0001_initial.py:277)
- bookings_status_check (check на scheduling.bookings): CHECK ((status = ANY (ARRAY['active'::text, 'cancelled'::text, 'no_show'::text, 'done'::text]))) (migrations/versions/0001_initial.py:278)
- uq_bookings_one_active (partial_unique_index на scheduling.bookings): CREATE UNIQUE INDEX uq_bookings_one_active ON scheduling.bookings USING btree (application_id) WHERE (status … (migrations/versions/0001_initial.py:282)

## ORM
- services/scheduling/models.py::Booking:44 (orm_model)

## Пишут (код)
- services/scheduling/service.py::_cancel [status]
- services/scheduling/service.py::book
- services/scheduling/service.py::issue_books [status]

## Правила
- R-SCHED-BOOK-01 Запись только в своё, будущее и не заполненное окно (⚠ расхождение с требованием или открытый вопрос)
- R-SCHED-BOOK-02 У заявки не больше одной действующей записи (⚠ без тестов)
- R-SCHED-BOOK-03 Цель записи берётся из ссылки, кто записал — из запроса (⚠ расхождение с требованием или открытый вопрос)
- R-SCHED-BOOK-EVENT-01 Запись на визит — письмо клиенту и представителю, событие в чате (проверено человеком)
- R-SCHED-CANCEL-01 Отмена записи — письмо об отмене и событие в чате (подкреплено кодом и тестами)
- R-SCHED-HOLD-01 Книги закрепляются за заявкой при записи за книгами (⚠ без тестов)
- R-SCHED-HOLD-02 Отмена, перенос и неявка не освобождают книги (⚠ без тестов)
- R-SCHED-ISSUE-01 Выдача книг — только по записи, на этапе «Ожидает выдачи», в выбранную дату (подкреплено кодом и тестами)
- R-SCHED-ISSUE-02 Срок возврата — LOAN_PERIOD_DAYS от момента выдачи (⚠ расхождение с требованием или открытый вопрос)
- R-SCHED-ISSUE-03 После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента» (⚠ расхождение с требованием или открытый вопрос)
- R-SCHED-NO-SHOW-01 Неявка отменяет запись, клиент может записаться снова (подкреплено кодом и тестами)
- R-SCHED-RESCHEDULE-01 Перенос — это отмена и новая запись (⚠ расхождение с требованием или открытый вопрос)
- R-SCHED-SLOT-05 Удаление окна отменяет записи на него (⚠ без тестов)
