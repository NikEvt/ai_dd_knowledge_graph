<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# staff.employees
Миграция: `staff.employees`

## Поля
- id: integer NOT NULL PK
- full_name: text
- passport: text
- snils: text
- birth_date: date
- role: text NOT NULL
- hired_at: timestamp with time zone NOT NULL
- dismissed_at: timestamp with time zone
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- staff.alerts.recipient_id → сюда
- staff.assignments.employee_id → сюда
- staff.briefings.employee_id → сюда
- staff.clearances.employee_id → сюда
- staff.shift_members.employee_id → сюда
- staff.shifts.created_by → сюда
- staff.sites.responsible_id → сюда

## Ограничения и триггеры
- employees_birth_date_check (check на staff.employees): CHECK ((birth_date > '1900-01-01'::date))
- employees_dismissal_check (check на staff.employees): CHECK (((dismissed_at IS NULL) OR (dismissed_at >= hired_at)))
- employees_passport_format (check на staff.employees): CHECK ((passport ~ '^[0-9]{4} [0-9]{6}$'::text))
- employees_role_check (check на staff.employees): CHECK ((role = ANY (ARRAY['librarian'::text, 'cashier'::text, 'guard'::text, 'manager'::text, 'hr'::text])))
- employees_snils_format (check на staff.employees): CHECK ((snils ~ '^[0-9]{3}-[0-9]{3}-[0-9]{3} [0-9]{2}$'::text))
- employees_passport_active_uq (partial_unique_index на staff.employees): CREATE UNIQUE INDEX employees_passport_active_uq ON staff.employees USING btree (passport) WHERE (dismissed_a…
- employees_snils_key (unique на staff.employees): UNIQUE (snils)

## ORM
- services/staff/models.py::Employee:12 (orm_model)

## Пишут (код)
- services/staff/service.py::dismiss_employee [dismissed_at]
- services/staff/service.py::hire_employee

## Правила
- R-STAFF-CARD-01 [draft] Должность сотрудника выбирается из закрытого списка
- R-STAFF-CARD-02 [draft] СНИЛС проверяется по контрольному числу в коде и по формату в БД
- R-STAFF-CARD-03 [draft] Сотрудник должен быть не моложе 18 лет
- R-STAFF-CARD-04 [draft] Формат паспорта проверяется только в БД
- R-STAFF-CARD-05 [draft] Паспорт уникален среди работающих, СНИЛС уникален навсегда
- R-STAFF-DISMISS-01 [draft] Увольнение закрывает карточку и закрепление за площадкой
- R-STAFF-HIRE-01 [draft] Неполную карточку принимают, но такой сотрудник не допускается к сменам и допускам
- R-STAFF-HR-01 [draft] Кадровые операции выполняет только действующий сотрудник отдела кадров
- R-STAFF-SITE-RESP-03 [draft] Перевод или увольнение ответственного оставляет площадку без ответственного
