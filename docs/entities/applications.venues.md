<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.venues
Миграция: [`migrations/versions/0001_initial.py:29`](../../migrations/versions/0001_initial.py#L29)

## Поля
- id: integer NOT NULL PK
- city: text NOT NULL
- requisites: jsonb
- max_slot_capacity: integer NOT NULL
- site_checker_id: integer NOT NULL

## Связи (FK)
- applications.applications.venue_id → сюда
- applications.prices.venue_id → сюда
- applications.venue_spheres.venue_id → сюда

## Ограничения и триггеры
- venues_max_slot_capacity_check (check на applications.venues): CHECK ((max_slot_capacity > 0)) (migrations/versions/0001_initial.py:33)

## ORM
- services/applications/models.py::Venue:13 (orm_model)

## Пишут (код)
- services/applications/admin.py::set_venue_max_capacity [max_slot_capacity]
- services/applications/admin.py::set_venue_requisites [requisites]

## Правила
- R-APP-ADMIN-02 [verified] Реквизиты площадки задаёт администратор; без них счёт не выставить
- R-APP-ADMIN-03 [draft] Максимум мест в окне площадки положителен и передаётся в scheduling событием
