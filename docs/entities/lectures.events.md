<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# lectures.events
Миграция: `lectures.events`

## Поля
- id: integer NOT NULL PK
- title: text NOT NULL
- venue_id: integer NOT NULL
- organizer_id: integer NOT NULL
- starts_at: timestamp with time zone NOT NULL
- capacity: integer NOT NULL
- capacity_manual: boolean NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- lectures.notifications.event_id → сюда
- lectures.registrations.event_id → сюда
- lectures.waitlist.event_id → сюда

## Ограничения и триггеры
- events_capacity_check (check на lectures.events): CHECK ((capacity > 0))
- events_status_check (check на lectures.events): CHECK ((status = ANY (ARRAY['scheduled'::text, 'cancelled'::text, 'finished'::text])))
- events_title_check (check на lectures.events): CHECK ((length(btrim(title)) > 0))
- events_upcoming_idx (index на lectures.events): CREATE INDEX events_upcoming_idx ON lectures.events USING btree (venue_id, starts_at) WHERE (status = 'schedu…
- events_venue_slot_uq (partial_unique_index на lectures.events): CREATE UNIQUE INDEX events_venue_slot_uq ON lectures.events USING btree (venue_id, starts_at) WHERE (status =…
- trg_lecture_capacity_limit: BEFORE INSERT OR UPDATE OF capacity, venue_id ON lectures.events FOR EACH ROW EXECUTE FUNCTION lectures.check_capacity()
  - check_capacity(): 'venue % has no capacity limit'; 'event capacity % exceeds venue % limit %'
- trg_lecture_touch: BEFORE UPDATE ON lectures.events FOR EACH ROW EXECUTE FUNCTION lectures.touch_updated_at()
  - touch_updated_at(): BEGIN IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at THEN NEW.updated_at := now(); END IF; R…

## ORM
- services/lectures/models.py::Lecture:22 (orm_model)

## Пишут (код)
- services/lectures/jobs.py::finish_past_events [status, updated_at]
- services/lectures/service.py::apply_venue_limit [capacity, updated_at]
- services/lectures/service.py::cancel_event [status, updated_at]
- services/lectures/service.py::change_capacity [capacity, capacity_manual, updated_at]
- services/lectures/service.py::create_event
- services/lectures/service.py::move_event [capacity, capacity_manual, updated_at, venue_id]

## Правила
- R-LECTURES-CANCEL-01 Отмена мероприятия аннулирует регистрации и лист ожидания (подкреплено кодом и тестами)
- R-LECTURES-CAPACITY-01 Нельзя сократить места ниже числа подтверждённых регистраций (подкреплено кодом и тестами)
- R-LECTURES-CAPACITY-02 Число мест, равное лимиту, снова следует за лимитом площадки (подкреплено кодом и тестами)
- R-LECTURES-CAPACITY-03 Новые места отдаются листу ожидания (подкреплено кодом и тестами)
- R-LECTURES-EVENT-01 Мероприятие объявляют не позднее чем за MIN_LEAD_TIME до начала (подкреплено кодом и тестами)
- R-LECTURES-EVENT-02 Тема мероприятия обязательна (⚠ без тестов)
- R-LECTURES-EVENT-03 Мероприятие возможно только на площадке с заданным лимитом мест (подкреплено кодом и тестами)
- R-LECTURES-EVENT-04 По умолчанию мест столько, сколько позволяет лимит площадки (подкреплено кодом и тестами)
- R-LECTURES-EVENT-05 Мест на мероприятии не больше лимита площадки — проверяет только БД (подкреплено кодом и тестами)
- R-LECTURES-EVENT-06 Число мест и лимит площадки положительны (⚠ без тестов)
- R-LECTURES-EVENT-07 Площадка не принимает два мероприятия с одним временем начала (подкреплено кодом и тестами)
- R-LECTURES-EVENT-08 Жизненный цикл мероприятия — scheduled, cancelled, finished (подкреплено кодом и тестами)
- R-LECTURES-FINISH-01 Мероприятие становится прошедшим через FINISH_AFTER после начала (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-02 Реплика лимита пишется подписчиком lectures.venue_limit_changed (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-03 Число мест будущих мероприятий без ручной настройки следует за лимитом (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-04 Рост лимита площадки отдаёт новые места листу ожидания (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-05 Снижение лимита не проверяет регистрации и ручные мероприятия (⚠ без тестов)
- R-LECTURES-MOVE-01 Переносят только на другую свободную площадку (подкреплено кодом и тестами)
- R-LECTURES-MOVE-02 Перенос аннулирует все регистрации и лист ожидания (подкреплено кодом и тестами)
