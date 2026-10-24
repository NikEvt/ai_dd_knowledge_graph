<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# billing.fine_rates
Миграция: [`migrations/versions/0001_initial.py:193`](../../migrations/versions/0001_initial.py#L193)

## Поля
- representative_id: integer NOT NULL PK
- venue_id: integer NOT NULL PK
- kind: text NOT NULL PK
- amount: numeric NOT NULL

## Ограничения и триггеры
- fine_rates_amount_check (check на billing.fine_rates): CHECK ((amount >= (0)::numeric)) (migrations/versions/0001_initial.py:197)
- fine_rates_kind_check (check на billing.fine_rates): CHECK ((kind = ANY (ARRAY['overdue'::text, 'lost'::text, 'damaged'::text]))) (migrations/versions/0001_initial.py:196)

## ORM
- services/billing/models.py::FineRate:67 (orm_model)

## Правила
- R-BILL-FINE-02 [draft] Размер штрафа берётся из ставки по представителю, площадке и виду
