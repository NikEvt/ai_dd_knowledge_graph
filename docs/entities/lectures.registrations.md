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
- R-LECTURES-CANCEL-REG-01 Регистрацию отменяет только сам слушатель и только до начала (подкреплено кодом и тестами)
- R-LECTURES-REG-01 Регистрация и лист ожидания закрываются за REGISTRATION_CLOSES_BEFORE до начала (подкреплено кодом и тестами)
- R-LECTURES-REG-02 Одна действующая регистрация слушателя на мероприятие (подкреплено кодом и тестами)
- R-LECTURES-REG-03 У слушателя не больше MAX_ACTIVE_REGISTRATIONS регистраций на будущие мероприятия (подкреплено кодом и тестами)
- R-LECTURES-REG-04 Без свободных мест регистрация отклоняется с предложением листа ожидания (подкреплено кодом и тестами)
- R-LECTURES-REG-05 БД не допускает перебора мест и регистраций на незапланированное мероприятие (подкреплено кодом и тестами)
- R-LECTURES-REG-06 Прямая регистрация закрывает свою запись в листе ожидания (⚠ без тестов)
- R-LECTURES-REG-07 Согласованность статуса регистрации и меток времени (⚠ без тестов)
- R-LECTURES-WAITLIST-06 Свободные места автоматически получают первые в листе ожидания (подкреплено кодом и тестами)
