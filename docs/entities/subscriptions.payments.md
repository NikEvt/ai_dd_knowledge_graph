<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.payments
Миграция: `subscriptions.payments`

## Поля
- id: integer NOT NULL PK
- invoice_id: integer NOT NULL
- amount: numeric NOT NULL
- external_ref: character varying
- paid_at: timestamp with time zone NOT NULL

## Связи (FK)
- invoice_id → subscriptions.invoices

## Ограничения и триггеры
- ck_payments_amount (check на subscriptions.payments): CHECK ((amount > (0)::numeric))
- uq_payments_external_ref (partial_unique_index на subscriptions.payments): CREATE UNIQUE INDEX uq_payments_external_ref ON subscriptions.payments USING btree (external_ref) WHERE (exte…
- trg_payments_apply: AFTER INSERT ON subscriptions.payments FOR EACH ROW EXECUTE FUNCTION subscriptions.payments_apply()
  - payments_apply(): BEGIN UPDATE subscriptions.invoices SET paid_total = paid_total + NEW.amount WHERE id = NEW.invoice…
- trg_payments_guard: BEFORE INSERT ON subscriptions.payments FOR EACH ROW EXECUTE FUNCTION subscriptions.payments_guard()
  - payments_guard(): 'invoice % is not open'; 'payment exceeds invoice % balance'

## ORM
- services/subscriptions/models.py::Payment:60 (orm_model)

## Пишут (код)
- services/subscriptions/service.py::record_payment

## Правила
- R-SUBSCRIPTIONS-PAYMENT-01 Платёж принимается только по открытому счёту, в пределах остатка и с положительной суммой (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-PAYMENT-02 Внешний платёж с одним и тем же external_ref учитывается один раз (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-PAYMENT-03 Оплаченную сумму счёта считает триггер БД, полная оплата закрывает счёт (подкреплено кодом и тестами)
