<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.clearance_kinds
Миграция: `staff.clearance_kinds`

## Поля
- code: text NOT NULL PK
- title: text NOT NULL
- valid_days: integer NOT NULL
- briefing_topic: text
- recheck_fields: ARRAY NOT NULL

## Связи (FK)
- staff.clearances.kind → сюда
- staff.shifts.required_clearance → сюда

## Ограничения и триггеры
- clearance_kinds_valid_days_check (check на staff.clearance_kinds): CHECK (((valid_days >= 1) AND (valid_days <= 1095)))

## ORM
- services/staff/models.py::ClearanceKind:54 (orm_model)

## Правила
- R-STAFF-CLEARANCE-03 [draft] Срок допуска — valid_days его вида от момента выдачи
