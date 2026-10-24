-- inventory: книжный фонд площадок, перемещения, межбиблиотечный абонемент

CREATE SCHEMA inventory;

-- Хранители фонда: кто отвечает за экземпляры на площадке
CREATE TABLE inventory.custodians (
    venue_id int NOT NULL,
    employee_id int NOT NULL,
    PRIMARY KEY (venue_id, employee_id)
);

-- Библиотеки-партнёры по МБА
CREATE TABLE inventory.partner_libraries (
    id serial PRIMARY KEY,
    code text NOT NULL UNIQUE CHECK (code ~ '^[A-Z0-9-]{2,16}$'),
    name text NOT NULL,
    daily_penalty numeric(12,2) NOT NULL CHECK (daily_penalty >= 0),
    max_active_loans int NOT NULL DEFAULT 5 CHECK (max_active_loans > 0),
    suspended boolean NOT NULL DEFAULT false
);

CREATE TABLE inventory.copies (
    id serial PRIMARY KEY,
    inventory_no text NOT NULL UNIQUE,
    book_ref int NOT NULL,
    venue_id int NOT NULL,
    state text NOT NULL DEFAULT 'available'
        CHECK (state IN ('available','on_loan','in_transit','lost','damaged','written_off')),
    acquired_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE INDEX ix_copies_book_venue ON inventory.copies (book_ref, venue_id);

CREATE TABLE inventory.transfers (
    id serial PRIMARY KEY,
    copy_id int NOT NULL REFERENCES inventory.copies,
    from_venue_id int NOT NULL,
    to_venue_id int NOT NULL,
    status text NOT NULL CHECK (status IN ('requested','in_transit','received','cancelled')),
    requested_by int NOT NULL,
    requested_at timestamptz NOT NULL,
    shipped_at timestamptz,
    closed_at timestamptz,
    cancel_reason text,
    CHECK (from_venue_id <> to_venue_id),
    CHECK ((status = 'requested') = (shipped_at IS NULL) OR status = 'cancelled'),
    CHECK ((status IN ('received','cancelled')) = (closed_at IS NOT NULL))
);
CREATE UNIQUE INDEX uq_transfers_one_open
    ON inventory.transfers (copy_id) WHERE status IN ('requested','in_transit');

CREATE TABLE inventory.ill_loans (
    id serial PRIMARY KEY,
    copy_id int NOT NULL REFERENCES inventory.copies,
    partner_id int NOT NULL REFERENCES inventory.partner_libraries,
    issued_by int NOT NULL,
    issued_at timestamptz NOT NULL,
    due_at timestamptz NOT NULL,
    returned_at timestamptz,
    status text NOT NULL CHECK (status IN ('out','returned','lost')),
    overdue_flagged boolean NOT NULL DEFAULT false,
    CHECK (due_at > issued_at),
    CHECK ((status = 'returned') = (returned_at IS NOT NULL))
);
CREATE UNIQUE INDEX uq_ill_loans_one_out
    ON inventory.ill_loans (copy_id) WHERE status = 'out';
CREATE INDEX ix_ill_loans_due ON inventory.ill_loans (due_at) WHERE status = 'out';

CREATE TABLE inventory.ill_penalties (
    id serial PRIMARY KEY,
    ill_loan_id int NOT NULL REFERENCES inventory.ill_loans,
    partner_id int NOT NULL REFERENCES inventory.partner_libraries,
    kind text NOT NULL CHECK (kind IN ('overdue','lost')),
    days int NOT NULL DEFAULT 0 CHECK (days >= 0),
    amount numeric(12,2) NOT NULL CHECK (amount >= 0),
    status text NOT NULL DEFAULT 'accruing' CHECK (status IN ('accruing','final','paid')),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    UNIQUE (ill_loan_id, kind)
);

CREATE TABLE inventory.write_offs (
    id serial PRIMARY KEY,
    copy_id int NOT NULL UNIQUE REFERENCES inventory.copies,
    reason text NOT NULL CHECK (reason IN ('lost','damaged','worn_out')),
    act_no text NOT NULL UNIQUE,
    ill_loan_id int REFERENCES inventory.ill_loans,
    note text,
    created_by int,
    created_at timestamptz NOT NULL
);

-- Остатки по изданию на площадке, пересчитываются по событиям
CREATE TABLE inventory.stock_levels (
    book_ref int NOT NULL,
    venue_id int NOT NULL,
    total int NOT NULL CHECK (total >= 0),
    available int NOT NULL CHECK (available >= 0),
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (book_ref, venue_id),
    CHECK (available <= total)
);

CREATE FUNCTION inventory.forbid_transfer_of_loaned_copy() RETURNS trigger AS $$
BEGIN
    IF NEW.venue_id IS DISTINCT FROM OLD.venue_id THEN
        IF OLD.state = 'on_loan' OR EXISTS (
            SELECT 1 FROM inventory.ill_loans l WHERE l.copy_id = OLD.id AND l.status = 'out'
        ) THEN
            RAISE EXCEPTION 'copy % is on loan and cannot change venue', OLD.inventory_no
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_copies_transfer_lock
    BEFORE UPDATE OF venue_id ON inventory.copies
    FOR EACH ROW EXECUTE FUNCTION inventory.forbid_transfer_of_loaned_copy();

CREATE FUNCTION inventory.forbid_written_off_change() RETURNS trigger AS $$
BEGIN
    IF OLD.state = 'written_off' THEN
        RAISE EXCEPTION 'copy % is written off', OLD.inventory_no USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_copies_written_off_final
    BEFORE UPDATE ON inventory.copies
    FOR EACH ROW EXECUTE FUNCTION inventory.forbid_written_off_change();

CREATE FUNCTION inventory.check_transfer_origin() RETURNS trigger AS $$
DECLARE
    current_venue int;
BEGIN
    SELECT venue_id INTO current_venue FROM inventory.copies WHERE id = NEW.copy_id;
    IF current_venue IS DISTINCT FROM NEW.from_venue_id THEN
        RAISE EXCEPTION 'copy % is not at venue %', NEW.copy_id, NEW.from_venue_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transfers_origin
    BEFORE INSERT ON inventory.transfers
    FOR EACH ROW EXECUTE FUNCTION inventory.check_transfer_origin();
