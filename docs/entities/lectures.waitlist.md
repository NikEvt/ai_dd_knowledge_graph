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
- R-LECTURES-CANCEL-01 [draft] Отмена мероприятия аннулирует регистрации и лист ожидания
- R-LECTURES-MOVE-02 [draft] Перенос аннулирует все регистрации и лист ожидания
- R-LECTURES-REG-01 [draft] Регистрация и лист ожидания закрываются за REGISTRATION_CLOSES_BEFORE до начала
- R-LECTURES-REG-02 [draft] Одна действующая регистрация слушателя на мероприятие
- R-LECTURES-REG-03 [draft] У слушателя не больше MAX_ACTIVE_REGISTRATIONS регистраций на будущие мероприятия
- R-LECTURES-REG-04 [draft] Без свободных мест регистрация отклоняется с предложением листа ожидания
- R-LECTURES-REG-06 [draft] Прямая регистрация закрывает свою запись в листе ожидания
- R-LECTURES-WAITLIST-01 [draft] В лист ожидания встают только когда мест нет
- R-LECTURES-WAITLIST-02 [draft] Одна ожидающая запись слушателя на мероприятие
- R-LECTURES-WAITLIST-03 [draft] Длина листа ожидания ограничена WAITLIST_MAX_SIZE
- R-LECTURES-WAITLIST-04 [draft] Лист ожидания — очередь по времени записи
- R-LECTURES-WAITLIST-05 [draft] Покинуть лист ожидания может только сам слушатель
- R-LECTURES-WAITLIST-06 [draft] Свободные места автоматически получают первые в листе ожидания
- R-LECTURES-WAITLIST-07 [draft] Лист ожидания истекает, когда закрывается регистрация
- R-LECTURES-WAITLIST-08 [draft] Закрытая запись листа ожидания всегда имеет closed_at
