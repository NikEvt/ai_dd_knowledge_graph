<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.refunds
Миграция: `subscriptions.refunds`

## Поля
- id: integer NOT NULL PK
- subscription_id: integer NOT NULL
- invoice_id: integer NOT NULL
- amount: numeric NOT NULL
- status: character varying NOT NULL
- created_at: timestamp with time zone NOT NULL
- done_at: timestamp with time zone

## Связи (FK)
- invoice_id → subscriptions.invoices
- subscription_id → subscriptions.subscriptions

## Ограничения и триггеры
- ck_refunds_amount (check на subscriptions.refunds): CHECK ((amount > (0)::numeric))
- ck_refunds_done (check на subscriptions.refunds): CHECK ((((status)::text = 'done'::text) = (done_at IS NOT NULL)))
- ck_refunds_status (check на subscriptions.refunds): CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'done'::character varying])::text[])))
- ix_refunds_pending (index на subscriptions.refunds): CREATE INDEX ix_refunds_pending ON subscriptions.refunds USING btree (created_at) WHERE ((status)::text = 'pe…
- uq_refunds_invoice (unique на subscriptions.refunds): UNIQUE (invoice_id)

## ORM
- services/subscriptions/models.py::Refund:73 (orm_model)
