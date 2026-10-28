<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.deals
Миграция: `partners.deals`

## Поля
- id: integer NOT NULL PK
- contract_id: integer NOT NULL
- external_ref: text NOT NULL
- amount: numeric NOT NULL
- on_credit: boolean NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- due_at: timestamp with time zone
- prepaid_at: timestamp with time zone
- closed_at: timestamp with time zone
- paid_at: timestamp with time zone
- overdue_flagged: boolean NOT NULL

## Связи (FK)
- contract_id → partners.contracts
- partners.commissions.deal_id → сюда

## Ограничения и триггеры
- deals_amount_check (check на partners.deals): CHECK ((amount > (0)::numeric))
- deals_check (check на partners.deals): CHECK ((on_credit = (due_at IS NOT NULL)))
- deals_check1 (check на partners.deals): CHECK (((NOT on_credit) OR ((status <> 'awaiting_prepayment'::text) AND (prepaid_at IS NULL))))
- deals_check2 (check на partners.deals): CHECK (((status <> 'closed'::text) OR (closed_at IS NOT NULL)))
- deals_status_check (check на partners.deals): CHECK ((status = ANY (ARRAY['awaiting_prepayment'::text, 'open'::text, 'closed'::text, 'cancelled'::text])))
- ix_deals_contract_unpaid_credit (index на partners.deals): CREATE INDEX ix_deals_contract_unpaid_credit ON partners.deals USING btree (contract_id) WHERE (on_credit AND…
- trg_contract_credit_limit: BEFORE INSERT ON partners.deals FOR EACH ROW EXECUTE FUNCTION partners.check_credit_limit()
  - check_credit_limit(): 'contract % does not allow credit deals'; 'credit limit of contract % exceeded, new deals are blocked'; 'deal exceeds credit limit of contract %: % + % > %'
- deals_contract_id_external_ref_key (unique на partners.deals): UNIQUE (contract_id, external_ref)

## ORM
- services/partners/models.py::Deal:65 (orm_model)

## Пишут (код)
- services/partners/jobs.py::flag_overdue_credit [overdue_flagged]
- services/partners/service.py::expire_contract
- services/partners/service.py::open_deal
- services/partners/service.py::register_payment [paid_at]
- services/partners/service.py::terminate_contract

## Правила
- R-PARTNERS-CONTRACT-05 Договор с истёкшим сроком переводится в expired (подкреплено кодом и тестами)
- R-PARTNERS-CONTRACT-06 Расторжение договора требует причины и отсутствия открытых сделок и долга (подкреплено кодом и тестами)
- R-PARTNERS-CREDIT-01 Кредитная задолженность — сумма неоплаченных неотменённых сделок в кредит (подкреплено кодом и тестами)
- R-PARTNERS-CREDIT-02 Кредитный лимит проверяет только триггер БД при вставке сделки (подкреплено кодом и тестами)
- R-PARTNERS-CREDIT-03 Просрочка оплаты кредитной сделки приостанавливает договор (подкреплено кодом и тестами)
- R-PARTNERS-DEAL-01 Сделка открывается только по действующему договору в сроке (подкреплено кодом и тестами)
- R-PARTNERS-DEAL-02 Режим сделки определяется договором — в кредит или с предоплатой (подкреплено кодом и тестами)
- R-PARTNERS-DEAL-03 Сделку без кредита закрывают только после предоплаты (подкреплено кодом и тестами)
- R-PARTNERS-DEAL-05 Оплата регистрируется только по кредитной сделке и один раз (подкреплено кодом и тестами)
- R-PARTNERS-DEAL-06 Оплату кредитной сделки регистрируют без проверки менеджера (⚠ без тестов)
