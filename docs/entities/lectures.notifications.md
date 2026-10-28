<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# lectures.notifications
Миграция: `lectures.notifications`

## Поля
- id: integer NOT NULL PK
- listener_id: integer NOT NULL
- event_id: integer NOT NULL
- kind: text NOT NULL
- body: text NOT NULL
- dedup_key: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- sent_at: timestamp with time zone

## Связи (FK)
- event_id → lectures.events

## Ограничения и триггеры
- notifications_kind_check (check на lectures.notifications): CHECK ((kind = ANY (ARRAY['registered'::text, 'registration_cancelled'::text, 'event_moved'::text, 'event_can…
- notifications_listener_idx (index на lectures.notifications): CREATE INDEX notifications_listener_idx ON lectures.notifications USING btree (listener_id, created_at)
- notifications_dedup_key_key (unique на lectures.notifications): UNIQUE (dedup_key)

## ORM
- services/lectures/models.py::Notification:66 (orm_model)

## Правила
- R-LECTURES-NOTIFY-01 Повторная доставка события не дублирует уведомление (подкреплено кодом и тестами)
- R-LECTURES-NOTIFY-02 Тип уведомления об отмене регистрации зависит от причины (подкреплено кодом и тестами)
- R-LECTURES-NOTIFY-03 Слушатели из листа ожидания получают уведомление о переносе или отмене (подкреплено кодом и тестами)
- R-LECTURES-NOTIFY-04 Продвижение из листа ожидания сопровождается уведомлением (подкреплено кодом и тестами)
- R-LECTURES-REMIND-01 Напоминание о мероприятии — один раз за REMINDER_AHEAD до начала (подкреплено кодом и тестами)
