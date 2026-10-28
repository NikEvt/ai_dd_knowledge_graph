<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.invoices
Миграция: `subscriptions.invoices`

## Поля
- id: integer NOT NULL PK
- subscription_id: integer NOT NULL
- period_start: date NOT NULL
- period_end: date NOT NULL
- amount: numeric NOT NULL
- paid_total: numeric NOT NULL
- status: character varying NOT NULL
- issued_at: timestamp with time zone NOT NULL

## Связи (FK)
- subscription_id → subscriptions.subscriptions
- subscriptions.payments.invoice_id → сюда
- subscriptions.refunds.invoice_id → сюда

## Ограничения и триггеры
- ck_invoices_amount (check на subscriptions.invoices): CHECK ((amount > (0)::numeric))
- ck_invoices_paid_total (check на subscriptions.invoices): CHECK (((paid_total >= (0)::numeric) AND (paid_total <= amount)))
- ck_invoices_period (check на subscriptions.invoices): CHECK ((period_end > period_start))
- ck_invoices_status (check на subscriptions.invoices): CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'paid'::character varying, 'void'::character …
- uq_invoices_one_open (partial_unique_index на subscriptions.invoices): CREATE UNIQUE INDEX uq_invoices_one_open ON subscriptions.invoices USING btree (subscription_id) WHERE ((stat…
- uq_invoices_period (unique на subscriptions.invoices): UNIQUE (subscription_id, period_start)

## ORM
- services/subscriptions/models.py::Invoice:46 (orm_model)

## Пишут (код)
- services/subscriptions/service.py::issue_invoice
- services/subscriptions/service.py::record_payment [status]
- services/subscriptions/service.py::void_open_invoices [status]

## Правила
- R-SUBSCRIPTIONS-DEDUP-02 У закрытого дубля аннулируются открытые счета, частичная оплата подлежит возврату (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-EXPIRE-01 При закрытии абонемента по сроку его открытые счета аннулируются (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-INVOICE-01 По абонементу может быть только один открытый счёт (⚠ без тестов)
- R-SUBSCRIPTIONS-INVOICE-02 Счёт выставляется за календарный месяц по текущей цене тарифа (⚠ без тестов)
- R-SUBSCRIPTIONS-PAYMENT-01 Платёж принимается только по открытому счёту, в пределах остатка и с положительной суммой (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-PAYMENT-02 Внешний платёж с одним и тем же external_ref учитывается один раз (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-PAYMENT-03 Оплаченную сумму счёта считает триггер БД, полная оплата закрывает счёт (подкреплено кодом и тестами)
- R-SUBSCRIPTIONS-RENEWAL-01 Счёт за следующий месяц выставляется за 7 дней до конца оплаченного периода (подкреплено кодом и тестами)
