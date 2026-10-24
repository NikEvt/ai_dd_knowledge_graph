<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# partners.payouts
Миграция: `partners.payouts`

## Поля
- id: integer NOT NULL PK
- partner_id: integer NOT NULL
- period: date NOT NULL
- total: numeric NOT NULL
- commissions_count: integer NOT NULL
- status: text NOT NULL

## Связи (FK)
- partner_id → partners.partners
- partners.commissions.payout_id → сюда

## Ограничения и триггеры
- payouts_commissions_count_check (check на partners.payouts): CHECK ((commissions_count >= 0))
- payouts_period_check (check на partners.payouts): CHECK ((EXTRACT(day FROM period) = (1)::numeric))
- payouts_status_check (check на partners.payouts): CHECK ((status = ANY (ARRAY['open'::text, 'closed'::text])))
- payouts_total_check (check на partners.payouts): CHECK ((total >= (0)::numeric))
- payouts_partner_id_period_key (unique на partners.payouts): UNIQUE (partner_id, period)

## ORM
- services/partners/models.py::Payout:83 (orm_model)

## Пишут (код)
- services/partners/service.py::_open_payout
- services/partners/service.py::add_to_payout [commissions_count, total]
- services/partners/service.py::close_payout [status]

## Правила
- R-PARTNERS-PAYOUT-01 [draft] Комиссия попадает в месячную ведомость партнёра
- R-PARTNERS-PAYOUT-02 [draft] Ведомость закрывается только после окончания месяца
