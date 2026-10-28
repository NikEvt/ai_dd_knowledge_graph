<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_bookings
Миграция: `halls.hall_bookings`

## Поля
- id: integer NOT NULL PK
- hall_id: integer NOT NULL
- venue_id: integer NOT NULL
- client_ref: text NOT NULL
- event_kind: text NOT NULL
- guests: integer NOT NULL
- starts_at: timestamp with time zone NOT NULL
- ends_at: timestamp with time zone NOT NULL
- status: text NOT NULL
- created_by: integer NOT NULL
- created_at: timestamp with time zone NOT NULL
- confirmed_at: timestamp with time zone
- cancelled_at: timestamp with time zone
- cancel_reason: text

## Связи (FK)
- hall_id → halls.halls
- halls.hall_booking_history.booking_id → сюда
- halls.hall_emails.booking_id → сюда
- halls.hall_invoices.booking_id → сюда

## Ограничения и триггеры
- hall_bookings_check (check на halls.hall_bookings): CHECK ((ends_at > starts_at))
- hall_bookings_check1 (check на halls.hall_bookings): CHECK (((status = 'cancelled'::text) = (cancelled_at IS NOT NULL)))
- hall_bookings_check2 (check на halls.hall_bookings): CHECK (((status <> ALL (ARRAY['confirmed'::text, 'held'::text])) OR (confirmed_at IS NOT NULL)))
- hall_bookings_client_ref_check (check на halls.hall_bookings): CHECK ((length(TRIM(BOTH FROM client_ref)) > 0))
- hall_bookings_event_kind_check (check на halls.hall_bookings): CHECK ((event_kind = ANY (ARRAY['wedding'::text, 'birthday'::text, 'party'::text, 'corporate'::text, 'confere…
- hall_bookings_guests_check (check на halls.hall_bookings): CHECK ((guests > 0))
- hall_bookings_status_check (check на halls.hall_bookings): CHECK ((status = ANY (ARRAY['draft'::text, 'prepaid'::text, 'confirmed'::text, 'held'::text, 'cancelled'::tex…
- hall_bookings_status_created_idx (index на halls.hall_bookings): CREATE INDEX hall_bookings_status_created_idx ON halls.hall_bookings USING btree (status, created_at)
- hall_bookings_hall_start_uq (partial_unique_index на halls.hall_bookings): CREATE UNIQUE INDEX hall_bookings_hall_start_uq ON halls.hall_bookings USING btree (hall_id, starts_at) WHERE…
- trg_hall_bookings_history: AFTER INSERT OR UPDATE OF status ON halls.hall_bookings FOR EACH ROW EXECUTE FUNCTION halls.log_status_change()
  - log_status_change(): BEGIN IF TG_OP = 'INSERT' THEN INSERT INTO halls.hall_booking_history (booking_id, old_status, new_…
- trg_hall_bookings_venue_lock: BEFORE UPDATE OF venue_id ON halls.hall_bookings FOR EACH ROW EXECUTE FUNCTION halls.forbid_venue_change()
  - halls.forbid_venue_change(): 'бронь % подтверждена, площадку сменить нельзя'

## ORM
- services/halls/models.py::HallBooking:34 (orm_model)

## Пишут (код)
- services/halls/service.py::_cancel [cancel_reason, cancelled_at, status]
- services/halls/service.py::apply_payments [confirmed_at, status]
- services/halls/service.py::change_venue [hall_id, venue_id]
- services/halls/service.py::create_booking
- services/halls/service.py::mark_held [status]

## Правила
- R-HALLS-ACCESS-01 Залами, бронями и шаблонами управляет только менеджер, закреплённый за площадкой (подкреплено кодом и тестами)
- R-HALLS-BOOKING-01 Вид мероприятия — из фиксированного списка (⚠ без тестов)
- R-HALLS-BOOKING-02 Число гостей положительно и не больше вместимости зала (подкреплено кодом и тестами)
- R-HALLS-BOOKING-03 Зал бронируется не позже чем за 2 дня и не дальше чем на 365 дней вперёд (подкреплено кодом и тестами)
- R-HALLS-BOOKING-04 Аренда длится от 2 до 12 часов (подкреплено кодом и тестами)
- R-HALLS-BOOKING-05 Брони одного зала не пересекаются с учётом часа на уборку (подкреплено кодом и тестами)
- R-HALLS-BOOKING-06 Новая бронь создаётся черновиком, и на неё сразу выставляется счёт (подкреплено кодом и тестами)
- R-HALLS-BOOKING-07 Ссылка на клиента в брони не может быть пустой — только на уровне БД (⚠ без тестов)
- R-HALLS-CANCEL-01 Отменить можно любую бронь, кроме уже отменённой и проведённой (подкреплено кодом и тестами)
- R-HALLS-STATUS-01 Полностью оплаченная бронь подтверждается, клиенту уходит письмо (подкреплено кодом и тестами)
- R-HALLS-STATUS-02 Оплата половины счёта делает черновик предоплаченным (подкреплено кодом и тестами)
- R-HALLS-STATUS-03 Предоплаченная бронь возвращается в черновик, если после перевыставления не хватает предоплаты (подкреплено кодом и тестами)
- R-HALLS-STATUS-04 Статусы брони и согласованность дат отмены и подтверждения (⚠ без тестов)
- R-HALLS-STATUS-05 История статусов брони пишется триггером БД (подкреплено кодом и тестами)
- R-HALLS-TIMER-02 Подтверждённая бронь после окончания мероприятия становится проведённой (подкреплено кодом и тестами)
- R-HALLS-VENUE-CHANGE-01 Бронь переносится на другую площадку только до подтверждения (подкреплено кодом и тестами)
- R-HALLS-VENUE-CHANGE-02 Триггер БД запрещает менять площадку подтверждённой или проведённой брони (подкреплено кодом и тестами)
