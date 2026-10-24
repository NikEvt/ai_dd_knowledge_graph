<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.books
Миграция: [`migrations/versions/0001_initial.py:49`](../../migrations/versions/0001_initial.py#L49)

## Поля
- id: integer NOT NULL PK
- sphere_id: integer NOT NULL
- title: text NOT NULL

## Связи (FK)
- sphere_id → applications.spheres
- applications.application_books.book_id → сюда
- applications.prices.book_id → сюда

## ORM
- services/applications/models.py::Book:41 (orm_model)
