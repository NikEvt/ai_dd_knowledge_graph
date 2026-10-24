<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.ill_penalties
Миграция: `inventory.ill_penalties`

## Поля
- id: integer NOT NULL PK
- ill_loan_id: integer NOT NULL
- partner_id: integer NOT NULL
- kind: text NOT NULL
- days: integer NOT NULL
- amount: numeric NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- ill_loan_id → inventory.ill_loans
- partner_id → inventory.partner_libraries

## Ограничения и триггеры
- ill_penalties_amount_check (check на inventory.ill_penalties): CHECK ((amount >= (0)::numeric))
- ill_penalties_days_check (check на inventory.ill_penalties): CHECK ((days >= 0))
- ill_penalties_kind_check (check на inventory.ill_penalties): CHECK ((kind = ANY (ARRAY['overdue'::text, 'lost'::text])))
- ill_penalties_status_check (check на inventory.ill_penalties): CHECK ((status = ANY (ARRAY['accruing'::text, 'final'::text, 'paid'::text])))
- ill_penalties_ill_loan_id_kind_key (unique на inventory.ill_penalties): UNIQUE (ill_loan_id, kind)

## ORM
- services/inventory/models.py::IllPenalty:82 (orm_model)

## Пишут (код)
- services/inventory/service.py::_penalty
- services/inventory/service.py::accrue_overdue [amount, days, status, updated_at]
- services/inventory/service.py::charge_lost_copy [amount, status, updated_at]
- services/inventory/service.py::settle_penalty [status, updated_at]

## Правила
- R-INVENTORY-ILL-07 [draft] Утеря экземпляра партнёром списывает его и начисляет компенсацию
- R-INVENTORY-PARTNER-03 [draft] Оплата пеней возобновляет выдачи, когда долг опускается до лимита
- R-INVENTORY-PENALTY-03 [draft] Пени по невозвращённым выдачам ежедневно пересчитываются
- R-INVENTORY-PENALTY-04 [draft] Пени за просрочку — дневная ставка партнёра × дни, не более ILL_PENALTY_MAX_DAYS
- R-INVENTORY-PENALTY-06 [draft] При утере партнёром пени за просрочку замораживаются на последнем начислении
- R-INVENTORY-PENALTY-07 [draft] Оплатить можно только итоговые пени
