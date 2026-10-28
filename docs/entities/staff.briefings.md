<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.briefings
Миграция: `staff.briefings`

## Поля
- id: integer NOT NULL PK
- employee_id: integer NOT NULL
- site_id: integer NOT NULL
- topic: text NOT NULL
- instructor_id: integer NOT NULL
- held_at: timestamp with time zone NOT NULL

## Связи (FK)
- employee_id → staff.employees
- site_id → staff.sites
- staff.clearances.briefing_id → сюда

## Ограничения и триггеры
- briefings_instructor_check (check на staff.briefings): CHECK ((instructor_id <> employee_id))
- briefings_once_key (unique на staff.briefings): UNIQUE (employee_id, topic, held_at)

## ORM
- services/staff/models.py::Briefing:95 (orm_model)

## Пишут (код)
- services/staff/service.py::hold_briefing

## Правила
- R-STAFF-BRIEFING-01 Инструктаж проводит ответственный площадки другому сотруднику этой площадки (⚠ без тестов)
- R-STAFF-SITE-RESP-01 Сменами и инструктажами площадки управляет только её ответственный (подкреплено кодом и тестами)
