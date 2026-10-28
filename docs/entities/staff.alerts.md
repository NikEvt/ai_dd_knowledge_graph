<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.alerts
Миграция: `staff.alerts`

## Поля
- id: integer NOT NULL PK
- recipient_id: integer
- site_id: integer NOT NULL
- shift_id: integer
- kind: text NOT NULL
- body: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- read_at: timestamp with time zone

## Связи (FK)
- recipient_id → staff.employees
- shift_id → staff.shifts
- site_id → staff.sites

## Ограничения и триггеры
- alerts_kind_check (check на staff.alerts): CHECK ((kind = ANY (ARRAY['understaffed'::text, 'no_responsible'::text])))
- alerts_unread_uq (partial_unique_index на staff.alerts): CREATE UNIQUE INDEX alerts_unread_uq ON staff.alerts USING btree (shift_id, kind) WHERE (read_at IS NULL)

## ORM
- services/staff/models.py::Alert:123 (orm_model)

## Пишут (код)
- services/staff/service.py::mark_alert_read [read_at]
- services/staff/service.py::raise_alert

## Правила
- R-STAFF-ALERT-01 Ответственный получает одно непрочитанное уведомление о недоукомплектованной смене (подкреплено кодом и тестами)
- R-STAFF-ALERT-02 Уведомление отмечает прочитанным адресат или текущий ответственный площадки (подкреплено кодом и тестами)
- R-STAFF-SITE-RESP-04 При переводе ответственного создаётся уведомление «нет ответственного» без адресата (подкреплено кодом и тестами)
