<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.venue_spheres
Миграция: [`migrations/versions/0001_initial.py:42`](../../migrations/versions/0001_initial.py#L42)

## Поля
- venue_id: integer NOT NULL PK
- sphere_id: integer NOT NULL PK
- active: boolean NOT NULL

## Связи (FK)
- sphere_id → applications.spheres
- venue_id → applications.venues

## ORM
- services/applications/models.py::VenueSphere:32 (orm_model)

## Пишут (код)
- services/applications/admin.py::set_sphere_active [active]

## Правила
- R-APP-ADMIN-04 [draft] Отключение сферы на площадке запрещает новые заявки, действующие доводятся до конца
