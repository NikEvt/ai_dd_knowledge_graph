<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.contract_history
Миграция: `partners.contract_history`

## Поля
- id: integer NOT NULL PK
- contract_id: integer NOT NULL
- field: text NOT NULL
- old_value: text
- new_value: text
- changed_at: timestamp with time zone NOT NULL

## Связи (FK)
- contract_id → partners.contracts

## Ограничения и триггеры
- contract_history_field_check (check на partners.contract_history): CHECK ((field = ANY (ARRAY['commission_pct'::text, 'credit_allowed'::text, 'credit_limit'::text, 'status'::te…
- ix_contract_history_contract (index на partners.contract_history): CREATE INDEX ix_contract_history_contract ON partners.contract_history USING btree (contract_id, id)

## ORM
- services/partners/models.py::ContractHistory:112 (orm_model)

## Правила
- R-PARTNERS-CONTRACT-07 Изменения условий договора журналируются триггером БД (подкреплено кодом и тестами)
