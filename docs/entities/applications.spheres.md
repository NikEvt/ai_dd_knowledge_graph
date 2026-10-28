<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.spheres
Миграция: [`migrations/versions/0001_initial.py:37`](../../migrations/versions/0001_initial.py#L37)

## Поля
- id: integer NOT NULL PK
- name: text NOT NULL

## Связи (FK)
- applications.applications.sphere_id → сюда
- applications.books.sphere_id → сюда
- applications.venue_spheres.sphere_id → сюда

## Ограничения и триггеры
- spheres_name_key (unique на applications.spheres): UNIQUE (name) (migrations/versions/0001_initial.py:39)

## ORM
- services/applications/models.py::Sphere:24 (orm_model)

## Правила
- R-SCHEMA-SPHERE-01 Название сферы уникально (⚠ расхождение со схемой или открытый вопрос)
