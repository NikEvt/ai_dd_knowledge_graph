-- Сотрудники площадок, смены, инструктажи и допуски.

CREATE SCHEMA staff;

CREATE TABLE staff.employees (
    id serial PRIMARY KEY,
    full_name text,
    passport text,
    snils text,
    birth_date date,
    role text NOT NULL,
    hired_at timestamptz NOT NULL,
    dismissed_at timestamptz,
    updated_at timestamptz NOT NULL,
    CONSTRAINT employees_role_check CHECK (role IN ('librarian', 'cashier', 'guard', 'manager', 'hr')),
    CONSTRAINT employees_snils_format CHECK (snils ~ '^[0-9]{3}-[0-9]{3}-[0-9]{3} [0-9]{2}$'),
    CONSTRAINT employees_passport_format CHECK (passport ~ '^[0-9]{4} [0-9]{6}$'),
    CONSTRAINT employees_birth_date_check CHECK (birth_date > DATE '1900-01-01'),
    CONSTRAINT employees_dismissal_check CHECK (dismissed_at IS NULL OR dismissed_at >= hired_at),
    CONSTRAINT employees_snils_key UNIQUE (snils)
);

-- Паспорт может повторно появиться только после увольнения прежней записи.
CREATE UNIQUE INDEX employees_passport_active_uq ON staff.employees (passport) WHERE dismissed_at IS NULL;

CREATE TABLE staff.sites (
    id serial PRIMARY KEY,
    name text NOT NULL,
    max_shift_staff int NOT NULL,
    responsible_id int REFERENCES staff.employees (id),
    CONSTRAINT sites_name_key UNIQUE (name),
    CONSTRAINT sites_max_shift_staff_check CHECK (max_shift_staff BETWEEN 1 AND 20)
);

CREATE TABLE staff.assignments (
    id serial PRIMARY KEY,
    employee_id int NOT NULL REFERENCES staff.employees (id),
    site_id int NOT NULL REFERENCES staff.sites (id),
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    CONSTRAINT assignments_period_check CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE UNIQUE INDEX assignments_current_uq ON staff.assignments (employee_id) WHERE ended_at IS NULL;
CREATE INDEX assignments_site_idx ON staff.assignments (site_id) WHERE ended_at IS NULL;

CREATE TABLE staff.clearance_kinds (
    code text PRIMARY KEY,
    title text NOT NULL,
    valid_days int NOT NULL,
    briefing_topic text,
    recheck_fields text[] NOT NULL DEFAULT '{}',
    CONSTRAINT clearance_kinds_valid_days_check CHECK (valid_days BETWEEN 1 AND 1095)
);

CREATE TABLE staff.shifts (
    id serial PRIMARY KEY,
    site_id int NOT NULL REFERENCES staff.sites (id),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    capacity int NOT NULL,
    min_staff int NOT NULL DEFAULT 1,
    required_clearance text REFERENCES staff.clearance_kinds (code),
    status text NOT NULL DEFAULT 'planned',
    understaffed boolean NOT NULL DEFAULT false,
    created_by int NOT NULL REFERENCES staff.employees (id),
    CONSTRAINT shifts_period_check CHECK (ends_at > starts_at),
    CONSTRAINT shifts_capacity_check CHECK (capacity BETWEEN 1 AND 20),
    CONSTRAINT shifts_min_staff_check CHECK (min_staff BETWEEN 0 AND capacity),
    CONSTRAINT shifts_status_check CHECK (status IN ('planned', 'cancelled', 'done'))
);

CREATE UNIQUE INDEX shifts_planned_uq ON staff.shifts (site_id, starts_at, coalesce(required_clearance, ''))
    WHERE status = 'planned';

CREATE TABLE staff.shift_members (
    id serial PRIMARY KEY,
    shift_id int NOT NULL REFERENCES staff.shifts (id),
    employee_id int NOT NULL REFERENCES staff.employees (id),
    status text NOT NULL DEFAULT 'assigned',
    assigned_at timestamptz NOT NULL,
    removed_at timestamptz,
    removed_reason text,
    CONSTRAINT shift_members_status_check CHECK (status IN ('assigned', 'removed')),
    CONSTRAINT shift_members_removal_check CHECK ((status = 'removed') = (removed_at IS NOT NULL))
);

CREATE UNIQUE INDEX shift_members_assigned_uq ON staff.shift_members (shift_id, employee_id)
    WHERE status = 'assigned';
CREATE INDEX shift_members_employee_idx ON staff.shift_members (employee_id) WHERE status = 'assigned';

CREATE TABLE staff.briefings (
    id serial PRIMARY KEY,
    employee_id int NOT NULL REFERENCES staff.employees (id),
    site_id int NOT NULL REFERENCES staff.sites (id),
    topic text NOT NULL,
    instructor_id int NOT NULL REFERENCES staff.employees (id),
    held_at timestamptz NOT NULL,
    CONSTRAINT briefings_instructor_check CHECK (instructor_id <> employee_id),
    CONSTRAINT briefings_once_key UNIQUE (employee_id, topic, held_at)
);

CREATE TABLE staff.clearances (
    id serial PRIMARY KEY,
    employee_id int NOT NULL REFERENCES staff.employees (id),
    kind text NOT NULL REFERENCES staff.clearance_kinds (code),
    briefing_id int REFERENCES staff.briefings (id),
    granted_by int NOT NULL REFERENCES staff.employees (id),
    granted_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'active',
    revoked_at timestamptz,
    revoke_reason text,
    CONSTRAINT clearances_period_check CHECK (expires_at > granted_at),
    CONSTRAINT clearances_status_check CHECK (status IN ('active', 'revoked', 'expired')),
    CONSTRAINT clearances_revoked_check CHECK (status <> 'revoked' OR revoked_at IS NOT NULL)
);

CREATE UNIQUE INDEX clearances_active_uq ON staff.clearances (employee_id, kind) WHERE status = 'active';

CREATE TABLE staff.alerts (
    id serial PRIMARY KEY,
    recipient_id int REFERENCES staff.employees (id),
    site_id int NOT NULL REFERENCES staff.sites (id),
    shift_id int REFERENCES staff.shifts (id),
    kind text NOT NULL,
    body text NOT NULL,
    created_at timestamptz NOT NULL,
    read_at timestamptz,
    CONSTRAINT alerts_kind_check CHECK (kind IN ('understaffed', 'no_responsible'))
);

CREATE UNIQUE INDEX alerts_unread_uq ON staff.alerts (shift_id, kind) WHERE read_at IS NULL;

-- Вместимость смены ограничена максимумом площадки и не может стать меньше уже назначенных.
CREATE FUNCTION staff.check_shift_capacity() RETURNS trigger AS $$
DECLARE
    site_max int;
    taken int;
BEGIN
    SELECT max_shift_staff INTO site_max FROM staff.sites WHERE id = NEW.site_id;
    IF NEW.capacity > site_max THEN
        RAISE EXCEPTION 'shift capacity % exceeds site maximum %', NEW.capacity, site_max
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        SELECT count(*) INTO taken FROM staff.shift_members
            WHERE shift_id = NEW.id AND status = 'assigned';
        IF taken > NEW.capacity THEN
            RAISE EXCEPTION 'shift % already has % staff', NEW.id, taken
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_shift_capacity
    BEFORE INSERT OR UPDATE OF capacity, site_id ON staff.shifts
    FOR EACH ROW EXECUTE FUNCTION staff.check_shift_capacity();

CREATE FUNCTION staff.check_shift_members() RETURNS trigger AS $$
DECLARE
    cap int;
    taken int;
BEGIN
    IF NEW.status <> 'assigned' THEN
        RETURN NEW;
    END IF;
    SELECT capacity INTO cap FROM staff.shifts WHERE id = NEW.shift_id FOR UPDATE;
    SELECT count(*) INTO taken FROM staff.shift_members
        WHERE shift_id = NEW.shift_id AND status = 'assigned' AND id <> NEW.id;
    IF taken >= cap THEN
        RAISE EXCEPTION 'shift % is full: % staff', NEW.shift_id, cap
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_shift_members_limit
    BEFORE INSERT OR UPDATE OF status ON staff.shift_members
    FOR EACH ROW EXECUTE FUNCTION staff.check_shift_members();

CREATE FUNCTION staff.check_site_max_staff() RETURNS trigger AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM staff.shifts
        WHERE site_id = NEW.id AND status = 'planned' AND capacity > NEW.max_shift_staff
    ) THEN
        RAISE EXCEPTION 'site % has planned shifts above % staff', NEW.id, NEW.max_shift_staff
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_site_max_shift_staff
    BEFORE UPDATE OF max_shift_staff ON staff.sites
    FOR EACH ROW EXECUTE FUNCTION staff.check_site_max_staff();
