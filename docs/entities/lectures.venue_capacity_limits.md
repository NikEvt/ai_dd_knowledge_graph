<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# lectures.venue_capacity_limits
Миграция: `lectures.venue_capacity_limits`

## Поля
- venue_id: integer NOT NULL PK
- max_capacity: integer NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Ограничения и триггеры
- venue_capacity_limits_max_capacity_check (check на lectures.venue_capacity_limits): CHECK ((max_capacity > 0))

## ORM
- services/lectures/models.py::VenueCapacityLimit:11 (orm_model)

## Пишут (код)
- services/lectures/service.py::apply_venue_limit [max_capacity, updated_at]

## Правила
- R-LECTURES-EVENT-06 Число мест и лимит площадки положительны (⚠ без тестов)
- R-LECTURES-LIMIT-01 Лимит мест площадки меняется асинхронно через событие, права не проверяются (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-02 Реплика лимита пишется подписчиком lectures.venue_limit_changed (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-03 Число мест будущих мероприятий без ручной настройки следует за лимитом (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-04 Рост лимита площадки отдаёт новые места листу ожидания (подкреплено кодом и тестами)
- R-LECTURES-LIMIT-05 Снижение лимита не проверяет регистрации и ручные мероприятия (⚠ без тестов)
