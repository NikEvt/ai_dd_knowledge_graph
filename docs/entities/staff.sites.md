<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.sites
Миграция: `staff.sites`

## Поля
- id: integer NOT NULL PK
- name: text NOT NULL
- max_shift_staff: integer NOT NULL
- responsible_id: integer

## Связи (FK)
- responsible_id → staff.employees
- staff.alerts.site_id → сюда
- staff.assignments.site_id → сюда
- staff.briefings.site_id → сюда
- staff.shifts.site_id → сюда

## Ограничения и триггеры
- sites_max_shift_staff_check (check на staff.sites): CHECK (((max_shift_staff >= 1) AND (max_shift_staff <= 20)))
- trg_site_max_shift_staff: BEFORE UPDATE OF max_shift_staff ON staff.sites FOR EACH ROW EXECUTE FUNCTION staff.check_site_max_staff()
  - check_site_max_staff(): 'site % has planned shifts above % staff'
- sites_name_key (unique на staff.sites): UNIQUE (name)

## ORM
- services/staff/models.py::Site:31 (orm_model)

## Пишут (код)
- services/staff/service.py::_close_assignment [responsible_id]
- services/staff/service.py::appoint_responsible [responsible_id]
- services/staff/service.py::create_site
- services/staff/service.py::set_site_max_staff [max_shift_staff]

## Правила
- R-STAFF-SITE-01 Максимум сотрудников на смене для новой площадки — 6 (⚠ без тестов)
- R-STAFF-SITE-02 Максимум смены площадки — от 1 до 20 (подкреплено кодом и тестами)
- R-STAFF-SITE-03 Максимум площадки нельзя опустить ниже вместимости её запланированных смен (подкреплено кодом и тестами)
- R-STAFF-SITE-RESP-02 Ответственным за площадку назначается руководитель, работающий на этой площадке (подкреплено кодом и тестами)
- R-STAFF-SITE-RESP-03 Перевод или увольнение ответственного оставляет площадку без ответственного (подкреплено кодом и тестами)
- R-STAFF-TRANSFER-01 Сотрудник одновременно закреплён только за одной площадкой (подкреплено кодом и тестами)
