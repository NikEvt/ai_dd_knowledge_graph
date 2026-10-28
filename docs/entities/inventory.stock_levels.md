<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.stock_levels
Миграция: `inventory.stock_levels`

## Поля
- book_ref: integer NOT NULL PK
- venue_id: integer NOT NULL PK
- total: integer NOT NULL
- available: integer NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Ограничения и триггеры
- stock_levels_available_check (check на inventory.stock_levels): CHECK ((available >= 0))
- stock_levels_check (check на inventory.stock_levels): CHECK ((available <= total))
- stock_levels_total_check (check на inventory.stock_levels): CHECK ((total >= 0))

## ORM
- services/inventory/models.py::StockLevel:111 (orm_model)

## Правила
- R-INVENTORY-STOCK-03 Остатки в БД неотрицательны, и доступных не больше общего числа (⚠ без тестов)
