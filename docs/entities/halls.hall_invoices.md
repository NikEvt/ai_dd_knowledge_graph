<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_invoices
Миграция: `halls.hall_invoices`

## Поля
- id: integer NOT NULL PK
- booking_id: integer NOT NULL
- amount: numeric NOT NULL
- status: text NOT NULL
- issued_at: timestamp with time zone NOT NULL
- closed_at: timestamp with time zone

## Связи (FK)
- booking_id → halls.hall_bookings
- halls.hall_payments.invoice_id → сюда

## Ограничения и триггеры
- hall_invoices_amount_check (check на halls.hall_invoices): CHECK ((amount > (0)::numeric))
- hall_invoices_check (check на halls.hall_invoices): CHECK (((status = 'open'::text) = (closed_at IS NULL)))
- hall_invoices_status_check (check на halls.hall_invoices): CHECK ((status = ANY (ARRAY['open'::text, 'paid'::text, 'void'::text])))
- hall_invoices_booking_active_uq (partial_unique_index на halls.hall_invoices): CREATE UNIQUE INDEX hall_invoices_booking_active_uq ON halls.hall_invoices USING btree (booking_id) WHERE (st…

## ORM
- services/halls/models.py::HallInvoice:67 (orm_model)

## Пишут (код)
- services/halls/service.py::issue_invoice
- services/halls/service.py::record_payment [closed_at, status]
- services/halls/service.py::reissue_invoice [closed_at, status]
- services/halls/service.py::void_invoice [closed_at, status]

## Правила
- R-HALLS-ACCESS-02 [draft] Права на внесение платежа по счёту зала не проверяются
- R-HALLS-CANCEL-02 [draft] Отмена брони аннулирует открытый счёт и отправляет письмо об отмене
- R-HALLS-INVOICE-01 [draft] Сумма счёта — почасовая ставка зала за фактические минуты аренды
- R-HALLS-INVOICE-02 [draft] У брони не больше одного действующего счёта
- R-HALLS-INVOICE-03 [draft] Закрытый счёт (paid/void) всегда имеет дату закрытия
- R-HALLS-INVOICE-04 [draft] При выставлении счёта клиенту уходит письмо со счётом
- R-HALLS-PAYMENT-01 [draft] Платёж принимается только на открытый счёт неотменённой брони
- R-HALLS-PAYMENT-02 [draft] Сумма платежа положительна и не больше остатка по счёту
- R-HALLS-PAYMENT-03 [draft] Банковская ссылка платежа учитывается один раз
- R-HALLS-PAYMENT-04 [draft] Полная оплата закрывает счёт, любой платёж пересчитывает статус брони
- R-HALLS-VENUE-CHANGE-03 [draft] Смена площадки перевыставляет счёт по ставке нового зала с переносом платежей
