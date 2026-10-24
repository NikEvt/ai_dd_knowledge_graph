<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.ill_loans
Миграция: `inventory.ill_loans`

## Поля
- id: integer NOT NULL PK
- copy_id: integer NOT NULL
- partner_id: integer NOT NULL
- issued_by: integer NOT NULL
- issued_at: timestamp with time zone NOT NULL
- due_at: timestamp with time zone NOT NULL
- returned_at: timestamp with time zone
- status: text NOT NULL
- overdue_flagged: boolean NOT NULL

## Связи (FK)
- copy_id → inventory.copies
- partner_id → inventory.partner_libraries
- inventory.ill_penalties.ill_loan_id → сюда
- inventory.write_offs.ill_loan_id → сюда

## Ограничения и триггеры
- ill_loans_check (check на inventory.ill_loans): CHECK ((due_at > issued_at))
- ill_loans_check1 (check на inventory.ill_loans): CHECK (((status = 'returned'::text) = (returned_at IS NOT NULL)))
- ill_loans_status_check (check на inventory.ill_loans): CHECK ((status = ANY (ARRAY['out'::text, 'returned'::text, 'lost'::text])))
- ix_ill_loans_due (index на inventory.ill_loans): CREATE INDEX ix_ill_loans_due ON inventory.ill_loans USING btree (due_at) WHERE (status = 'out'::text)
- uq_ill_loans_one_out (partial_unique_index на inventory.ill_loans): CREATE UNIQUE INDEX uq_ill_loans_one_out ON inventory.ill_loans USING btree (copy_id) WHERE (status = 'out'::…

## ORM
- services/inventory/models.py::IllLoan:67 (orm_model)

## Пишут (код)
- services/inventory/jobs.py::flag_overdue_ill [overdue_flagged]
- services/inventory/service.py::issue_ill

## Правила
- R-INVENTORY-CUSTODIAN-01 [draft] Операции с фондом площадки выполняет только её хранитель
- R-INVENTORY-ILL-01 [draft] Выдача по МБА только доступного экземпляра без открытого перемещения
- R-INVENTORY-ILL-02 [draft] Партнёр без новых выдач при приостановке, просрочке, лимите или долге
- R-INVENTORY-ILL-03 [draft] Срок выдачи по МБА — ILL_LOAN_PERIOD_DAYS от момента выдачи
- R-INVENTORY-ILL-05 [draft] Закрытую выдачу по МБА нельзя вернуть, продлить или объявить утерянной
- R-INVENTORY-PENALTY-02 [draft] Просроченная выдача помечается один раз и начинает начислять пени
