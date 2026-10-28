<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.prices
Миграция: [`migrations/versions/0001_initial.py:55`](../../migrations/versions/0001_initial.py#L55)

## Поля
- venue_id: integer NOT NULL PK
- book_id: integer NOT NULL PK
- price: numeric NOT NULL

## Связи (FK)
- book_id → applications.books
- venue_id → applications.venues

## Ограничения и триггеры
- prices_price_check (check на applications.prices): CHECK ((price > (0)::numeric)) (migrations/versions/0001_initial.py:58)

## ORM
- services/applications/models.py::Price:50 (orm_model)

## Правила
- R-APP-CALC-01 Стоимость книг заявки — сумма цен прайса текущей площадки, надбавку берёт billing у представителя (подкреплено кодом и тестами)
- R-APP-CREATE-03 В заявке есть книги, и все они из сферы заявки и прайса площадки (⚠ без тестов)
