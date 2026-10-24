<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.custodians
Миграция: `inventory.custodians`

## Поля
- venue_id: integer NOT NULL PK
- employee_id: integer NOT NULL PK

## ORM
- services/inventory/models.py::Custodian:16 (orm_model)

## Пишут (код)
- services/inventory/service.py::add_custodian
