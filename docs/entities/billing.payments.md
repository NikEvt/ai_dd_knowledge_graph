<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# billing.payments
Миграция: [`migrations/versions/0001_initial.py:180`](../../migrations/versions/0001_initial.py#L180)

## Поля
- id: integer NOT NULL PK
- invoice_id: integer NOT NULL
- amount: numeric NOT NULL
- linked_at: timestamp with time zone NOT NULL
- linked_by: integer NOT NULL
- overpayment: boolean NOT NULL
- unlinked_at: timestamp with time zone
- unlink_reason: text
- refunded: boolean NOT NULL

## Связи (FK)
- invoice_id → billing.invoices

## Ограничения и триггеры
- payments_amount_check (check на billing.payments): CHECK ((amount > (0)::numeric)) (migrations/versions/0001_initial.py:183)
- payments_check (check на billing.payments): CHECK (((unlinked_at IS NULL) OR (unlink_reason IS NOT NULL))) (migrations/versions/0001_initial.py:190)
- trg_payments_active_invoice: BEFORE INSERT ON billing.payments FOR EACH ROW EXECUTE FUNCTION billing.forbid_payment_to_cancelled() (migrations/versions/0001_initial.py:224)
  - forbid_payment_to_cancelled(): 'payment cannot be linked to a cancelled invoice'

## ORM
- services/billing/models.py::Payment:52 (orm_model)

## Пишут (код)
- services/billing/service.py::link_payment [overpayment]
- services/billing/service.py::refund_payment [refunded]
- services/billing/service.py::unlink_payment [unlink_reason, unlinked_at]

## Правила
- R-BILL-FINE-PAY-01 [draft] Полная оплата счёта на штраф гасит штраф
- R-BILL-PAYMENT-01 [draft] Платёж нельзя привязать к аннулированному счёту
- R-BILL-PAYMENT-03 [verified] Привязка платежа фиксирует, кто привязал; переплата помечается флагом
- R-BILL-PAYMENT-04 [draft] Полная оплата публикуется один раз — когда сумма впервые достигает суммы счёта
- R-BILL-REFUND-01 [verified] Возврат платежа требует причины и исключает платёж из оплаченной суммы
- R-BILL-UNLINK-01 [draft] Отвязка платежа требует причины
