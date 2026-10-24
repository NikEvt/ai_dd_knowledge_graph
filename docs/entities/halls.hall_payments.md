<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_payments
Миграция: `halls.hall_payments`

## Поля
- id: integer NOT NULL PK
- invoice_id: integer NOT NULL
- amount: numeric NOT NULL
- external_ref: text
- recorded_by: integer NOT NULL
- paid_at: timestamp with time zone NOT NULL

## Связи (FK)
- invoice_id → halls.hall_invoices

## Ограничения и триггеры
- hall_payments_amount_check (check на halls.hall_payments): CHECK ((amount > (0)::numeric))
- hall_payments_external_ref_uq (partial_unique_index на halls.hall_payments): CREATE UNIQUE INDEX hall_payments_external_ref_uq ON halls.hall_payments USING btree (external_ref) WHERE (ex…
- trg_hall_payments_open_invoice: BEFORE INSERT ON halls.hall_payments FOR EACH ROW EXECUTE FUNCTION halls.forbid_payment_on_closed_invoice()
  - forbid_payment_on_closed_invoice(): 'счёт % закрыт, платёж не принимается'

## ORM
- services/halls/models.py::HallPayment:79 (orm_model)

## Пишут (код)
- services/halls/service.py::record_payment
- services/halls/service.py::reissue_invoice

## Правила
- R-HALLS-ACCESS-02 [draft] Права на внесение платежа по счёту зала не проверяются
- R-HALLS-INVOICE-02 [draft] У брони не больше одного действующего счёта
- R-HALLS-INVOICE-03 [draft] Закрытый счёт (paid/void) всегда имеет дату закрытия
- R-HALLS-PAYMENT-01 [draft] Платёж принимается только на открытый счёт неотменённой брони
- R-HALLS-PAYMENT-02 [draft] Сумма платежа положительна и не больше остатка по счёту
- R-HALLS-PAYMENT-03 [draft] Банковская ссылка платежа учитывается один раз
- R-HALLS-PAYMENT-04 [draft] Полная оплата закрывает счёт, любой платёж пересчитывает статус брони
- R-HALLS-VENUE-CHANGE-03 [draft] Смена площадки перевыставляет счёт по ставке нового зала с переносом платежей
