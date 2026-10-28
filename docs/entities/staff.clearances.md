<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.clearances
Миграция: `staff.clearances`

## Поля
- id: integer NOT NULL PK
- employee_id: integer NOT NULL
- kind: text NOT NULL
- briefing_id: integer
- granted_by: integer NOT NULL
- granted_at: timestamp with time zone NOT NULL
- expires_at: timestamp with time zone NOT NULL
- status: text NOT NULL
- revoked_at: timestamp with time zone
- revoke_reason: text

## Связи (FK)
- briefing_id → staff.briefings
- kind → staff.clearance_kinds
- employee_id → staff.employees

## Ограничения и триггеры
- clearances_period_check (check на staff.clearances): CHECK ((expires_at > granted_at))
- clearances_revoked_check (check на staff.clearances): CHECK (((status <> 'revoked'::text) OR (revoked_at IS NOT NULL)))
- clearances_status_check (check на staff.clearances): CHECK ((status = ANY (ARRAY['active'::text, 'revoked'::text, 'expired'::text])))
- clearances_active_uq (partial_unique_index на staff.clearances): CREATE UNIQUE INDEX clearances_active_uq ON staff.clearances USING btree (employee_id, kind) WHERE (status = …

## ORM
- services/staff/models.py::Clearance:107 (orm_model)

## Пишут (код)
- services/staff/jobs.py::expire_clearances [status]
- services/staff/service.py::_revoke [revoke_reason, revoked_at, status]
- services/staff/service.py::grant_clearance

## Правила
- R-STAFF-CLEARANCE-01 Допуск выдаётся действующему сотруднику с полной карточкой, один активный на вид (подкреплено кодом и тестами)
- R-STAFF-CLEARANCE-02 Для допуска с инструктажем нужен инструктаж по теме не старше 30 дней (подкреплено кодом и тестами)
- R-STAFF-CLEARANCE-03 Срок допуска — valid_days его вида от момента выдачи (подкреплено кодом и тестами)
- R-STAFF-CLEARANCE-04 Отдел кадров вручную отзывает только действующий допуск (⚠ без тестов)
- R-STAFF-CLEARANCE-05 Фоновая задача переводит допуски с наступившим сроком в expired (подкреплено кодом и тестами)
- R-STAFF-HR-01 Кадровые операции выполняет только действующий сотрудник отдела кадров (подкреплено кодом и тестами)
- R-STAFF-RECHECK-02 Изменение карточки отзывает допуски, требующие перепроверки этих полей (подкреплено кодом и тестами)
