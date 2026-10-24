<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.commissions
Миграция: `partners.commissions`

## Поля
- id: integer NOT NULL PK
- deal_id: integer NOT NULL
- contract_id: integer NOT NULL
- partner_id: integer NOT NULL
- base_amount: numeric NOT NULL
- rate_pct: numeric NOT NULL
- amount: numeric NOT NULL
- accrued_at: timestamp with time zone NOT NULL
- payout_id: integer

## Связи (FK)
- contract_id → partners.contracts
- deal_id → partners.deals
- partner_id → partners.partners
- payout_id → partners.payouts

## Ограничения и триггеры
- commissions_base_amount_check (check на partners.commissions): CHECK ((base_amount > (0)::numeric))
- commissions_check (check на partners.commissions): CHECK ((amount >= base_amount))
- commissions_rate_pct_check (check на partners.commissions): CHECK (((rate_pct >= (0)::numeric) AND (rate_pct <= (100)::numeric)))
- trg_commission_frozen: BEFORE UPDATE ON partners.commissions FOR EACH ROW EXECUTE FUNCTION partners.forbid_commission_change()
  - forbid_commission_change(): 'accrued commission % cannot be recalculated'
- commissions_deal_id_key (unique на partners.commissions): UNIQUE (deal_id)

## ORM
- services/partners/models.py::Commission:97 (orm_model)

## Пишут (код)
- services/partners/service.py::accrue_commission
- services/partners/service.py::add_to_payout [payout_id]

## Правила
- R-PARTNERS-COMMISSION-01 [draft] Комиссия начисляется один раз при закрытии сделки
- R-PARTNERS-COMMISSION-02 [draft] Сумма комиссии включает базу сделки
- R-PARTNERS-COMMISSION-03 [draft] Начисленная комиссия не пересчитывается
- R-PARTNERS-PAYOUT-01 [draft] Комиссия попадает в месячную ведомость партнёра
