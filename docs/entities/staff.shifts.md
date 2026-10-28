<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.shifts
Миграция: `staff.shifts`

## Поля
- id: integer NOT NULL PK
- site_id: integer NOT NULL
- starts_at: timestamp with time zone NOT NULL
- ends_at: timestamp with time zone NOT NULL
- capacity: integer NOT NULL
- min_staff: integer NOT NULL
- required_clearance: text
- status: text NOT NULL
- understaffed: boolean NOT NULL
- created_by: integer NOT NULL

## Связи (FK)
- required_clearance → staff.clearance_kinds
- created_by → staff.employees
- site_id → staff.sites
- staff.alerts.shift_id → сюда
- staff.shift_members.shift_id → сюда

## Ограничения и триггеры
- shifts_capacity_check (check на staff.shifts): CHECK (((capacity >= 1) AND (capacity <= 20)))
- shifts_min_staff_check (check на staff.shifts): CHECK (((min_staff >= 0) AND (min_staff <= capacity)))
- shifts_period_check (check на staff.shifts): CHECK ((ends_at > starts_at))
- shifts_status_check (check на staff.shifts): CHECK ((status = ANY (ARRAY['planned'::text, 'cancelled'::text, 'done'::text])))
- shifts_planned_uq (partial_unique_index на staff.shifts): CREATE UNIQUE INDEX shifts_planned_uq ON staff.shifts USING btree (site_id, starts_at, COALESCE(required_clea…
- trg_shift_capacity: BEFORE INSERT OR UPDATE OF capacity, site_id ON staff.shifts FOR EACH ROW EXECUTE FUNCTION staff.check_shift_capacity()
  - check_shift_capacity(): 'shift capacity % exceeds site maximum %'; 'shift % already has % staff'

## ORM
- services/staff/models.py::Shift:66 (orm_model)

## Пишут (код)
- services/staff/jobs.py::close_finished_shifts [status]
- services/staff/service.py::assign_to_shift [understaffed]
- services/staff/service.py::cancel_shift [status]
- services/staff/service.py::check_staffing [understaffed]
- services/staff/service.py::create_shift

## Правила
- R-STAFF-CANCEL-01 Отменить можно только запланированную смену, её состав снимается без уведомлений (подкреплено кодом и тестами)
- R-STAFF-MEMBER-01 На смену ставят действующего сотрудника своей площадки с полной карточкой (подкреплено кодом и тестами)
- R-STAFF-MEMBER-02 На смену с обязательным допуском ставят только при действующем допуске (подкреплено кодом и тестами)
- R-STAFF-MEMBER-03 Смену нельзя переукомплектовать, сотрудника нельзя назначить дважды (подкреплено кодом и тестами)
- R-STAFF-MEMBER-04 Между сменами сотрудника не меньше 8 часов отдыха (подкреплено кодом и тестами)
- R-STAFF-MEMBER-05 Назначение до минимального состава снимает пометку недоукомплектованности (подкреплено кодом и тестами)
- R-STAFF-SHIFT-01 Смена планируется в будущем, не дальше 60 дней и длится не больше 12 часов (подкреплено кодом и тестами)
- R-STAFF-SHIFT-02 Вместимость смены ограничена максимумом площадки, минимальный состав — вместимостью (подкреплено кодом и тестами)
- R-STAFF-SHIFT-03 Вместимость смены нельзя уменьшить ниже числа назначенных сотрудников (подкреплено кодом и тестами)
- R-STAFF-SHIFT-04 Нет двух запланированных смен площадки с одним началом и одним видом допуска (⚠ без тестов)
- R-STAFF-SHIFT-05 Новая смена с ненулевым минимумом сразу помечена недоукомплектованной, без уведомления (подкреплено кодом и тестами)
- R-STAFF-SHIFT-CLOSE-01 Фоновая задача закрывает завершившиеся смены (подкреплено кодом и тестами)
- R-STAFF-SITE-RESP-01 Сменами и инструктажами площадки управляет только её ответственный (подкреплено кодом и тестами)
- R-STAFF-STAFFING-01 Снятие сотрудника ниже минимума помечает смену недоукомплектованной (подкреплено кодом и тестами)
