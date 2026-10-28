<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_emails
Миграция: `halls.hall_emails`

## Поля
- id: integer NOT NULL PK
- booking_id: integer NOT NULL
- client_ref: text NOT NULL
- type: text NOT NULL
- template_id: integer
- body: text NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- booking_id → halls.hall_bookings
- template_id → halls.hall_templates

## Ограничения и триггеры
- hall_emails_status_check (check на halls.hall_emails): CHECK ((status = ANY (ARRAY['sent'::text, 'no_template'::text])))
- hall_emails_booking_idx (index на halls.hall_emails): CREATE INDEX hall_emails_booking_idx ON halls.hall_emails USING btree (booking_id)

## ORM
- services/halls/models.py::HallEmail:102 (orm_model)

## Пишут (код)
- services/halls/service.py::send_email

## Правила
- R-HALLS-EMAIL-01 Письмо клиенту берётся из шаблона площадки по группе вида мероприятия (подкреплено кодом и тестами)
