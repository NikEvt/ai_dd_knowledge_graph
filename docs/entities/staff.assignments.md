<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.assignments
Миграция: `staff.assignments`

## Поля
- id: integer NOT NULL PK
- employee_id: integer NOT NULL
- site_id: integer NOT NULL
- started_at: timestamp with time zone NOT NULL
- ended_at: timestamp with time zone

## Связи (FK)
- employee_id → staff.employees
- site_id → staff.sites

## Ограничения и триггеры
- assignments_period_check (check на staff.assignments): CHECK (((ended_at IS NULL) OR (ended_at >= started_at)))
- assignments_site_idx (index на staff.assignments): CREATE INDEX assignments_site_idx ON staff.assignments USING btree (site_id) WHERE (ended_at IS NULL)
- assignments_current_uq (partial_unique_index на staff.assignments): CREATE UNIQUE INDEX assignments_current_uq ON staff.assignments USING btree (employee_id) WHERE (ended_at IS …

## ORM
- services/staff/models.py::Assignment:41 (orm_model)

## Пишут (код)
- services/staff/service.py::_close_assignment [ended_at]
- services/staff/service.py::transfer_employee

## Правила
- R-STAFF-SITE-RESP-03 [draft] Перевод или увольнение ответственного оставляет площадку без ответственного
- R-STAFF-TRANSFER-01 [draft] Сотрудник одновременно закреплён только за одной площадкой
