<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# scheduling.venue_limits
Миграция: [`migrations/versions/0001_initial.py:230`](../../migrations/versions/0001_initial.py#L230)

## Поля
- venue_id: integer NOT NULL PK
- max_capacity: integer NOT NULL

## Ограничения и триггеры
- venue_limits_max_capacity_check (check на scheduling.venue_limits): CHECK ((max_capacity > 0)) (migrations/versions/0001_initial.py:232)

## ORM
- services/scheduling/models.py::VenueLimit:11 (orm_model)

## Пишут (код)
- services/scheduling/consumers.py::on_venue_settings_changed [max_capacity]

## Правила
- R-APP-ADMIN-03 [draft] Максимум мест в окне площадки положителен и передаётся в scheduling событием
- R-SCHED-VENUE-LIMIT-01 [draft] Максимум мест площадки реплицируется из админки событием
