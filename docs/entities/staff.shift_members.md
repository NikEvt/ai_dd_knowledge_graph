<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.shift_members
Миграция: `staff.shift_members`

## Поля
- id: integer NOT NULL PK
- shift_id: integer NOT NULL
- employee_id: integer NOT NULL
- status: text NOT NULL
- assigned_at: timestamp with time zone NOT NULL
- removed_at: timestamp with time zone
- removed_reason: text

## Связи (FK)
- employee_id → staff.employees
- shift_id → staff.shifts

## Ограничения и триггеры
- shift_members_removal_check (check на staff.shift_members): CHECK (((status = 'removed'::text) = (removed_at IS NOT NULL)))
- shift_members_status_check (check на staff.shift_members): CHECK ((status = ANY (ARRAY['assigned'::text, 'removed'::text])))
- shift_members_employee_idx (index на staff.shift_members): CREATE INDEX shift_members_employee_idx ON staff.shift_members USING btree (employee_id) WHERE (status = 'ass…
- shift_members_assigned_uq (partial_unique_index на staff.shift_members): CREATE UNIQUE INDEX shift_members_assigned_uq ON staff.shift_members USING btree (shift_id, employee_id) WHER…
- trg_shift_members_limit: BEFORE INSERT OR UPDATE OF status ON staff.shift_members FOR EACH ROW EXECUTE FUNCTION staff.check_shift_members()
  - check_shift_members(): 'shift % is full: % staff'

## ORM
- services/staff/models.py::ShiftMember:82 (orm_model)

## Пишут (код)
- services/staff/service.py::_remove_member [removed_at, removed_reason, status]
- services/staff/service.py::assign_to_shift

## Правила
- R-STAFF-MEMBER-01 На смену ставят действующего сотрудника своей площадки с полной карточкой (подкреплено кодом и тестами)
- R-STAFF-MEMBER-02 На смену с обязательным допуском ставят только при действующем допуске (подкреплено кодом и тестами)
- R-STAFF-MEMBER-03 Смену нельзя переукомплектовать, сотрудника нельзя назначить дважды (подкреплено кодом и тестами)
- R-STAFF-MEMBER-04 Между сменами сотрудника не меньше 8 часов отдыха (подкреплено кодом и тестами)
- R-STAFF-MEMBER-05 Назначение до минимального состава снимает пометку недоукомплектованности (подкреплено кодом и тестами)
- R-STAFF-MEMBER-06 Снятие со смены сохраняет запись с причиной и публикует staff.shift_member_removed (подкреплено кодом и тестами)
- R-STAFF-SITE-RESP-01 Сменами и инструктажами площадки управляет только её ответственный (подкреплено кодом и тестами)
