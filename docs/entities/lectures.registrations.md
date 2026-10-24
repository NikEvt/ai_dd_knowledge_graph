<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# lectures.registrations
Миграция: `lectures.registrations`

## Поля
- id: integer NOT NULL PK
- event_id: integer NOT NULL
- listener_id: integer NOT NULL
- status: text NOT NULL
- source: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- cancelled_at: timestamp with time zone
- cancel_reason: text
- attended_at: timestamp with time zone

## Связи (FK)
- event_id → lectures.events

## Ограничения и триггеры
- registrations_check (check на lectures.registrations): CHECK (((status = 'cancelled'::text) = (cancelled_at IS NOT NULL)))
- registrations_check1 (check на lectures.registrations): CHECK (((status = 'attended'::text) = (attended_at IS NOT NULL)))
- registrations_source_check (check на lectures.registrations): CHECK ((source = ANY (ARRAY['direct'::text, 'waitlist'::text])))
- registrations_status_check (check на lectures.registrations): CHECK ((status = ANY (ARRAY['confirmed'::text, 'attended'::text, 'cancelled'::text])))
- registrations_listener_idx (index на lectures.registrations): CREATE INDEX registrations_listener_idx ON lectures.registrations USING btree (listener_id) WHERE (status = '…
- registrations_active_uq (partial_unique_index на lectures.registrations): CREATE UNIQUE INDEX registrations_active_uq ON lectures.registrations USING btree (event_id, listener_id) WHE…
- trg_registration_seat: BEFORE INSERT OR UPDATE OF status ON lectures.registrations FOR EACH ROW WHEN ((new.status = 'confirmed'::text)) EXECUT…
  - check_seat_available(): 'event % is not open for registration'; 'event % is full'

## ORM
- services/lectures/models.py::Registration:39 (orm_model)

## Пишут (код)
- services/lectures/service.py::_cancel [cancel_reason, cancelled_at, status]
- services/lectures/service.py::fill_from_waitlist
- services/lectures/service.py::register

## Правила
- R-LECTURES-CANCEL-REG-01 [draft] Регистрацию отменяет только сам слушатель и только до начала
- R-LECTURES-REG-01 [draft] Регистрация и лист ожидания закрываются за REGISTRATION_CLOSES_BEFORE до начала
- R-LECTURES-REG-02 [draft] Одна действующая регистрация слушателя на мероприятие
- R-LECTURES-REG-03 [draft] У слушателя не больше MAX_ACTIVE_REGISTRATIONS регистраций на будущие мероприятия
- R-LECTURES-REG-04 [draft] Без свободных мест регистрация отклоняется с предложением листа ожидания
- R-LECTURES-REG-05 [draft] БД не допускает перебора мест и регистраций на незапланированное мероприятие
- R-LECTURES-REG-06 [draft] Прямая регистрация закрывает свою запись в листе ожидания
- R-LECTURES-REG-07 [draft] Согласованность статуса регистрации и меток времени
- R-LECTURES-WAITLIST-06 [draft] Свободные места автоматически получают первые в листе ожидания
