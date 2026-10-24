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
- R-HALLS-ACCESS-01 [draft] Залами, бронями и шаблонами управляет только менеджер, закреплённый за площадкой
- R-HALLS-BOOKING-01 [draft] Вид мероприятия — из фиксированного списка
- R-HALLS-BOOKING-02 [draft] Число гостей положительно и не больше вместимости зала
- R-HALLS-BOOKING-03 [draft] Зал бронируется не позже чем за 2 дня и не дальше чем на 365 дней вперёд
- R-HALLS-BOOKING-04 [draft] Аренда длится от 2 до 12 часов
- R-HALLS-BOOKING-05 [draft] Брони одного зала не пересекаются с учётом часа на уборку
- R-HALLS-BOOKING-06 [draft] Новая бронь создаётся черновиком, и на неё сразу выставляется счёт
- R-HALLS-BOOKING-07 [draft] Ссылка на клиента в брони не может быть пустой — только на уровне БД
- R-HALLS-CANCEL-01 [draft] Отменить можно любую бронь, кроме уже отменённой и проведённой
- R-HALLS-STATUS-01 [draft] Полностью оплаченная бронь подтверждается, клиенту уходит письмо
- R-HALLS-STATUS-02 [draft] Оплата половины счёта делает черновик предоплаченным
- R-HALLS-STATUS-03 [draft] Предоплаченная бронь возвращается в черновик, если после перевыставления не хватает предоплаты
- R-HALLS-STATUS-04 [draft] Статусы брони и согласованность дат отмены и подтверждения
- R-HALLS-STATUS-05 [draft] История статусов брони пишется триггером БД
- R-HALLS-TIMER-02 [draft] Подтверждённая бронь после окончания мероприятия становится проведённой
- R-HALLS-VENUE-CHANGE-01 [draft] Бронь переносится на другую площадку только до подтверждения
- R-HALLS-VENUE-CHANGE-02 [draft] Триггер БД запрещает менять площадку подтверждённой или проведённой брони
