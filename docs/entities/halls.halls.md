<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.halls
Миграция: `halls.halls`

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- name: text NOT NULL
- capacity: integer NOT NULL
- hourly_rate: numeric NOT NULL
- active: boolean NOT NULL

## Связи (FK)
- halls.hall_bookings.hall_id → сюда

## Ограничения и триггеры
- halls_capacity_check (check на halls.halls): CHECK ((capacity > 0))
- halls_hourly_rate_check (check на halls.halls): CHECK ((hourly_rate > (0)::numeric))
- halls_venue_id_name_key (unique на halls.halls): UNIQUE (venue_id, name)

## ORM
- services/halls/models.py::Hall:22 (orm_model)

## Пишут (код)
- services/halls/service.py::create_hall
- services/halls/service.py::deactivate_hall [active]

## Правила
- R-HALLS-ACCESS-01 [draft] Залами, бронями и шаблонами управляет только менеджер, закреплённый за площадкой
- R-HALLS-HALL-01 [draft] Название зала обязательно и уникально в пределах площадки
- R-HALLS-HALL-02 [draft] Вместимость и почасовая ставка зала положительны — только на уровне БД
- R-HALLS-HALL-03 [draft] Зал нельзя вывести из аренды, пока в нём есть предстоящие брони
