<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# lectures.waitlist
Миграция: `lectures.waitlist`

## Поля
- id: integer NOT NULL PK
- event_id: integer NOT NULL
- listener_id: integer NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- closed_at: timestamp with time zone

## Связи (FK)
- event_id → lectures.events

## Ограничения и триггеры
- waitlist_check (check на lectures.waitlist): CHECK (((status = 'waiting'::text) = (closed_at IS NULL)))
- waitlist_status_check (check на lectures.waitlist): CHECK ((status = ANY (ARRAY['waiting'::text, 'promoted'::text, 'left'::text, 'cancelled'::text, 'expired'::te…
- waitlist_queue_idx (index на lectures.waitlist): CREATE INDEX waitlist_queue_idx ON lectures.waitlist USING btree (event_id, created_at, id) WHERE (status = '…
- waitlist_waiting_uq (partial_unique_index на lectures.waitlist): CREATE UNIQUE INDEX waitlist_waiting_uq ON lectures.waitlist USING btree (event_id, listener_id) WHERE (statu…

## ORM
- services/lectures/models.py::WaitlistEntry:54 (orm_model)

## Пишут (код)
- services/lectures/jobs.py::close_waitlists [closed_at, status]
- services/lectures/service.py::_drop_audience [closed_at, status]
- services/lectures/service.py::fill_from_waitlist [closed_at, status]
- services/lectures/service.py::join_waitlist
- services/lectures/service.py::leave_waitlist [closed_at, status]
- services/lectures/service.py::register [closed_at, status]

## Правила
- R-LECTURES-CANCEL-01 Отмена мероприятия аннулирует регистрации и лист ожидания (подкреплено кодом и тестами)
- R-LECTURES-MOVE-02 Перенос аннулирует все регистрации и лист ожидания (подкреплено кодом и тестами)
- R-LECTURES-REG-01 Регистрация и лист ожидания закрываются за REGISTRATION_CLOSES_BEFORE до начала (подкреплено кодом и тестами)
- R-LECTURES-REG-02 Одна действующая регистрация слушателя на мероприятие (подкреплено кодом и тестами)
- R-LECTURES-REG-03 У слушателя не больше MAX_ACTIVE_REGISTRATIONS регистраций на будущие мероприятия (подкреплено кодом и тестами)
- R-LECTURES-REG-04 Без свободных мест регистрация отклоняется с предложением листа ожидания (подкреплено кодом и тестами)
- R-LECTURES-REG-06 Прямая регистрация закрывает свою запись в листе ожидания (⚠ без тестов)
- R-LECTURES-WAITLIST-01 В лист ожидания встают только когда мест нет (подкреплено кодом и тестами)
- R-LECTURES-WAITLIST-02 Одна ожидающая запись слушателя на мероприятие (⚠ без тестов)
- R-LECTURES-WAITLIST-03 Длина листа ожидания ограничена WAITLIST_MAX_SIZE (⚠ без тестов)
- R-LECTURES-WAITLIST-04 Лист ожидания — очередь по времени записи (подкреплено кодом и тестами)
- R-LECTURES-WAITLIST-05 Покинуть лист ожидания может только сам слушатель (подкреплено кодом и тестами)
- R-LECTURES-WAITLIST-06 Свободные места автоматически получают первые в листе ожидания (подкреплено кодом и тестами)
- R-LECTURES-WAITLIST-07 Лист ожидания истекает, когда закрывается регистрация (подкреплено кодом и тестами)
- R-LECTURES-WAITLIST-08 Закрытая запись листа ожидания всегда имеет closed_at (⚠ без тестов)
