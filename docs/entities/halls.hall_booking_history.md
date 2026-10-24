<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_booking_history
Миграция: `halls.hall_booking_history`

## Поля
- id: integer NOT NULL PK
- booking_id: integer NOT NULL
- old_status: text
- new_status: text NOT NULL
- changed_at: timestamp with time zone NOT NULL

## Связи (FK)
- booking_id → halls.hall_bookings

## ORM
- services/halls/models.py::BookingHistory:54 (orm_model)
