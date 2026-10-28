<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# reports.run_notifications
Миграция: `reports.run_notifications`

## Поля
- id: bigint NOT NULL PK
- run_id: bigint NOT NULL
- recipient_id: integer NOT NULL
- kind: text NOT NULL
- body: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- read_at: timestamp with time zone

## Связи (FK)
- run_id → reports.report_runs

## Ограничения и триггеры
- run_notifications_kind (check на reports.run_notifications): CHECK ((kind = ANY (ARRAY['completed'::text, 'failed'::text, 'cancelled'::text])))
- run_notifications_unread (index на reports.run_notifications): CREATE INDEX run_notifications_unread ON reports.run_notifications USING btree (recipient_id) WHERE (read_at …
- run_notifications_once (unique на reports.run_notifications): UNIQUE (run_id, recipient_id)

## ORM
- services/reports/models.py::RunNotification:78 (orm_model)

## Пишут (код)
- services/reports/service.py::mark_read [read_at]

## Правила
- R-REPORTS-NOTIFY-04 Не больше одного уведомления на запуск и получателя (подкреплено кодом и тестами)
- R-REPORTS-NOTIFY-05 Отметить уведомление прочитанным может только его адресат (⚠ без тестов)
