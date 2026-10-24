<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.holds
Миграция: [`migrations/versions/0001_initial.py:285`](../../migrations/versions/0001_initial.py#L285)

## Поля
- application_id: integer NOT NULL PK
- book_id: integer NOT NULL PK

## ORM
- services/scheduling/models.py::Hold:57 (orm_model)

## Пишут (код)
- services/scheduling/service.py::book
- services/scheduling/service.py::issue_books
- services/scheduling/service.py::reset_bookings

## Правила
- R-SCHED-BOOK-01 [draft] Запись только в своё, будущее и не заполненное окно
- R-SCHED-BOOK-02 [draft] У заявки не больше одной действующей записи
- R-SCHED-BOOK-03 [draft] Цель записи берётся из ссылки, кто записал — из запроса
- R-SCHED-BOOK-EVENT-01 [verified] Запись на визит — письмо клиенту и представителю, событие в чате
- R-SCHED-HOLD-01 [draft] Книги закрепляются за заявкой при записи за книгами
- R-SCHED-ISSUE-01 [draft] Выдача книг — только по записи, на этапе «Ожидает выдачи», в выбранную дату
- R-SCHED-ISSUE-02 [draft] Срок возврата — LOAN_PERIOD_DAYS от момента выдачи
- R-SCHED-ISSUE-03 [draft] После выдачи — запись выполнена, книги откреплены, ссылка на сдачу, этап «Книги у клиента»
- R-SCHED-RESET-01 [draft] Архив и закрытие дублем сбрасывают записи, книги и ссылку
- R-SCHED-VENUE-CHANGE-01 [draft] Смена площадки отменяет запись и выдаёт новую ссылку
