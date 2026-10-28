<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.write_offs
Миграция: `inventory.write_offs`

## Поля
- id: integer NOT NULL PK
- copy_id: integer NOT NULL
- reason: text NOT NULL
- act_no: text NOT NULL
- ill_loan_id: integer
- note: text
- created_by: integer
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- copy_id → inventory.copies
- ill_loan_id → inventory.ill_loans

## Ограничения и триггеры
- write_offs_reason_check (check на inventory.write_offs): CHECK ((reason = ANY (ARRAY['lost'::text, 'damaged'::text, 'worn_out'::text])))
- write_offs_act_no_key (unique на inventory.write_offs): UNIQUE (act_no)
- write_offs_copy_id_key (unique на inventory.write_offs): UNIQUE (copy_id)

## ORM
- services/inventory/models.py::WriteOff:97 (orm_model)

## Пишут (код)
- services/inventory/service.py::write_off

## Правила
- R-INVENTORY-WRITEOFF-03 Списанный экземпляр нельзя изменить (триггер БД) (подкреплено кодом и тестами)
- R-INVENTORY-WRITEOFF-04 Один акт списания на экземпляр с номером СП-год-id (подкреплено кодом и тестами)
