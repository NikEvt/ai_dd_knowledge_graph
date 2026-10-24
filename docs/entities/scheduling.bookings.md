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
- R-SCHED-BOOK-01 [draft] Запись только в своё, будущее и не заполненное окно
- R-SCHED-BOOK-02 [draft] У заявки не больше одной действующей записи
- R-SCHED-BOOK-03 [draft] Цель записи берётся из ссылки, кто записал — из запроса
- R-SCHED-BOOK-EVENT-01 [verified] Запись на визит — письмо клиенту и представителю, событие в чате
- R-SCHED-CANCEL-01 [draft] Отмена записи — письмо об отмене и событие в чате
- R-SCHED-HOLD-01 [draft] Книги закрепляются за заявкой при записи за книгами
- R-SCHED-HOLD-02 [draft] Отмена, перенос и неявка не освобождают книги
- R-SCHED-ISSUE-01 [draft] Выдача книг — только по записи, на этапе «Ожидает выдачи», в выбранную дату
- R-SCHED-ISSUE-02 [draft] Срок возврата — LOAN_PERIOD_DAYS от момента выдачи
- R-SCHED-ISSUE-03 [draft] После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента»
- R-SCHED-NO-SHOW-01 [draft] Неявка отменяет запись, клиент может записаться снова
- R-SCHED-RESCHEDULE-01 [draft] Перенос — это отмена и новая запись
- R-SCHED-SLOT-05 [draft] Удаление окна отменяет записи на него
