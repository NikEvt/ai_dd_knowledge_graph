<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.loans
Миграция: [`migrations/versions/0001_initial.py:291`](../../migrations/versions/0001_initial.py#L291)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- book_id: integer NOT NULL
- issued_at: timestamp with time zone NOT NULL
- due_at: timestamp with time zone NOT NULL
- returned_at: timestamp with time zone
- status: text NOT NULL
- damaged: boolean NOT NULL
- overdue_flagged: boolean NOT NULL

## Ограничения и триггеры
- loans_status_check (check на scheduling.loans): CHECK ((status = ANY (ARRAY['out'::text, 'returned'::text, 'lost'::text]))) (migrations/versions/0001_initial.py:298)

## ORM
- services/scheduling/models.py::Loan:67 (orm_model)

## Пишут (код)
- services/scheduling/jobs.py::flag_overdue [overdue_flagged]
- services/scheduling/service.py::issue_books
- services/scheduling/service.py::mark_lost [status]
- services/scheduling/service.py::return_book [damaged, returned_at, status]

## Правила
- R-CHAT-EVENTS-08 [draft] Срыв срока возврата книги пишется в чат
- R-SCHED-FINE-01 [verified] Порча и утеря книги порождают штраф в billing
- R-SCHED-ISSUE-01 [draft] Выдача книг — только по записи, на этапе «Ожидает выдачи», в выбранную дату
- R-SCHED-ISSUE-02 [draft] Срок возврата — LOAN_PERIOD_DAYS от момента выдачи
- R-SCHED-ISSUE-03 [draft] После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента»
- R-SCHED-OVERDUE-01 [draft] Фоновая задача отмечает просрочку через 30 дней с выдачи и создаёт штраф
- R-SCHED-RETURN-01 [draft] Возврат и утерю отмечает проверяющий оператор площадки заявки по каждой книге
- R-SCHEMA-FINE-01 [draft] О просрочке представителю сообщает оператор по почте
