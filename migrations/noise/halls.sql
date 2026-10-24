-- Аренда залов площадок под частные мероприятия.
CREATE SCHEMA halls;

CREATE TABLE halls.hall_managers (
    venue_id integer NOT NULL,
    manager_id integer NOT NULL,
    PRIMARY KEY (venue_id, manager_id)
);

CREATE TABLE halls.halls (
    id serial PRIMARY KEY,
    venue_id integer NOT NULL,
    name text NOT NULL,
    capacity integer NOT NULL CHECK (capacity > 0),
    hourly_rate numeric(12, 2) NOT NULL CHECK (hourly_rate > 0),
    active boolean NOT NULL DEFAULT true,
    UNIQUE (venue_id, name)
);

CREATE TABLE halls.hall_bookings (
    id serial PRIMARY KEY,
    hall_id integer NOT NULL REFERENCES halls.halls (id),
    venue_id integer NOT NULL,
    client_ref text NOT NULL CHECK (length(trim(client_ref)) > 0),
    event_kind text NOT NULL
        CHECK (event_kind IN ('wedding', 'birthday', 'party', 'corporate', 'conference')),
    guests integer NOT NULL CHECK (guests > 0),
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'prepaid', 'confirmed', 'held', 'cancelled')),
    created_by integer NOT NULL,
    created_at timestamptz NOT NULL,
    confirmed_at timestamptz,
    cancelled_at timestamptz,
    cancel_reason text,
    CHECK (ends_at > starts_at),
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),
    CHECK (status NOT IN ('confirmed', 'held') OR confirmed_at IS NOT NULL)
);

CREATE UNIQUE INDEX hall_bookings_hall_start_uq
    ON halls.hall_bookings (hall_id, starts_at)
    WHERE status <> 'cancelled';

CREATE INDEX hall_bookings_status_created_idx ON halls.hall_bookings (status, created_at);

CREATE TABLE halls.hall_booking_history (
    id serial PRIMARY KEY,
    booking_id integer NOT NULL REFERENCES halls.hall_bookings (id),
    old_status text,
    new_status text NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE halls.hall_invoices (
    id serial PRIMARY KEY,
    booking_id integer NOT NULL REFERENCES halls.hall_bookings (id),
    amount numeric(12, 2) NOT NULL CHECK (amount > 0),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'paid', 'void')),
    issued_at timestamptz NOT NULL,
    closed_at timestamptz,
    CHECK ((status = 'open') = (closed_at IS NULL))
);

-- У брони не больше одного действующего счёта.
CREATE UNIQUE INDEX hall_invoices_booking_active_uq
    ON halls.hall_invoices (booking_id)
    WHERE status <> 'void';

CREATE TABLE halls.hall_payments (
    id serial PRIMARY KEY,
    invoice_id integer NOT NULL REFERENCES halls.hall_invoices (id),
    amount numeric(12, 2) NOT NULL CHECK (amount > 0),
    external_ref text,
    recorded_by integer NOT NULL,
    paid_at timestamptz NOT NULL
);

CREATE UNIQUE INDEX hall_payments_external_ref_uq
    ON halls.hall_payments (external_ref)
    WHERE external_ref IS NOT NULL;

CREATE TABLE halls.hall_templates (
    id serial PRIMARY KEY,
    venue_id integer NOT NULL,
    kind_group text NOT NULL CHECK (kind_group IN ('corporate', 'private')),
    type text NOT NULL CHECK (type IN ('invoice', 'prepaid', 'confirmed', 'cancel')),
    body text NOT NULL,
    UNIQUE (venue_id, kind_group, type)
);

CREATE TABLE halls.hall_emails (
    id serial PRIMARY KEY,
    booking_id integer NOT NULL REFERENCES halls.hall_bookings (id),
    client_ref text NOT NULL,
    type text NOT NULL,
    template_id integer REFERENCES halls.hall_templates (id),
    body text NOT NULL,
    status text NOT NULL CHECK (status IN ('sent', 'no_template')),
    created_at timestamptz NOT NULL
);

CREATE INDEX hall_emails_booking_idx ON halls.hall_emails (booking_id);

CREATE FUNCTION halls.forbid_venue_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status IN ('confirmed', 'held') AND NEW.venue_id IS DISTINCT FROM OLD.venue_id THEN
        RAISE EXCEPTION 'бронь % подтверждена, площадку сменить нельзя', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_hall_bookings_venue_lock
    BEFORE UPDATE OF venue_id ON halls.hall_bookings
    FOR EACH ROW EXECUTE FUNCTION halls.forbid_venue_change();

CREATE FUNCTION halls.log_status_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO halls.hall_booking_history (booking_id, old_status, new_status)
        VALUES (NEW.id, NULL, NEW.status);
    ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO halls.hall_booking_history (booking_id, old_status, new_status)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_hall_bookings_history
    AFTER INSERT OR UPDATE OF status ON halls.hall_bookings
    FOR EACH ROW EXECUTE FUNCTION halls.log_status_change();

CREATE FUNCTION halls.forbid_payment_on_closed_invoice() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    invoice_status text;
BEGIN
    SELECT status INTO invoice_status FROM halls.hall_invoices WHERE id = NEW.invoice_id;
    IF invoice_status IS DISTINCT FROM 'open' THEN
        RAISE EXCEPTION 'счёт % закрыт, платёж не принимается', NEW.invoice_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_hall_payments_open_invoice
    BEFORE INSERT ON halls.hall_payments
    FOR EACH ROW EXECUTE FUNCTION halls.forbid_payment_on_closed_invoice();
