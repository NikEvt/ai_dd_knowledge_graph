"""initial schema

Revision ID: 0001
Revises: 0000
"""

from alembic import op

revision = "0001"
down_revision = "0000"
branch_labels = None
depends_on = None

STAGES = (
    "'draft','on_review','needs_rework','awaiting_invoice','awaiting_payment',"
    "'awaiting_issue','books_out','closed','archived','closed_duplicate'"
)

UPGRADE = f"""
CREATE SCHEMA applications;
CREATE SCHEMA billing;
CREATE SCHEMA scheduling;
CREATE SCHEMA notifications;
CREATE SCHEMA chat;
CREATE SCHEMA events;

-- applications ---------------------------------------------------------------

CREATE TABLE applications.venues (
    id serial PRIMARY KEY,
    city text NOT NULL,
    requisites jsonb,
    max_slot_capacity int NOT NULL CHECK (max_slot_capacity > 0),
    site_checker_id int NOT NULL
);

CREATE TABLE applications.spheres (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE applications.venue_spheres (
    venue_id int NOT NULL REFERENCES applications.venues,
    sphere_id int NOT NULL REFERENCES applications.spheres,
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY (venue_id, sphere_id)
);

CREATE TABLE applications.books (
    id serial PRIMARY KEY,
    sphere_id int NOT NULL REFERENCES applications.spheres,
    title text NOT NULL
);

CREATE TABLE applications.prices (
    venue_id int NOT NULL REFERENCES applications.venues,
    book_id int NOT NULL REFERENCES applications.books,
    price numeric(12,2) NOT NULL CHECK (price > 0),
    PRIMARY KEY (venue_id, book_id)
);

CREATE TABLE applications.representatives (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL,
    markup_pct numeric(5,2) NOT NULL DEFAULT 0 CHECK (markup_pct >= 0),
    debt_allowed boolean NOT NULL DEFAULT false
);

CREATE TABLE applications.clients (
    id serial PRIMARY KEY,
    full_name text,
    passport text,
    birth_date date,
    email text NOT NULL,
    updated_at timestamptz
);

CREATE TABLE applications.applications (
    id serial PRIMARY KEY,
    client_id int NOT NULL REFERENCES applications.clients,
    representative_id int NOT NULL REFERENCES applications.representatives,
    sphere_id int NOT NULL REFERENCES applications.spheres,
    venue_id int NOT NULL REFERENCES applications.venues,
    kind text NOT NULL CHECK (kind IN ('paid','debt','social')),
    stage text NOT NULL CHECK (stage IN ({STAGES})),
    operator_id int NOT NULL,
    reviewer_id int,
    site_checker_id int NOT NULL,
    review_started_at timestamptz,
    booking_reached_at timestamptz,
    created_at timestamptz NOT NULL
);
CREATE INDEX ix_applications_client_sphere ON applications.applications (client_id, sphere_id);

CREATE TABLE applications.application_books (
    application_id int NOT NULL REFERENCES applications.applications ON DELETE CASCADE,
    book_id int NOT NULL REFERENCES applications.books,
    PRIMARY KEY (application_id, book_id)
);

CREATE TABLE applications.attempts (
    id serial PRIMARY KEY,
    application_id int NOT NULL REFERENCES applications.applications ON DELETE CASCADE,
    no int NOT NULL,
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    outcome text CHECK (outcome IN ('no_data','unpaid','client_declined','refund','duplicate')),
    UNIQUE (application_id, no)
);

CREATE FUNCTION applications.forbid_core_change() RETURNS trigger AS $$
BEGIN
    IF NEW.sphere_id <> OLD.sphere_id OR NEW.representative_id <> OLD.representative_id THEN
        RAISE EXCEPTION 'sphere and representative of an application cannot be changed'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_applications_core_immutable
    BEFORE UPDATE OF sphere_id, representative_id ON applications.applications
    FOR EACH ROW EXECUTE FUNCTION applications.forbid_core_change();

CREATE FUNCTION applications.forbid_venue_change() RETURNS trigger AS $$
BEGIN
    IF NEW.venue_id IS DISTINCT FROM OLD.venue_id THEN
        IF OLD.stage IN ('books_out','closed','closed_duplicate') THEN
            RAISE EXCEPTION 'venue change forbidden after books were issued'
                USING ERRCODE = 'check_violation';
        END IF;
        IF OLD.kind IN ('social','debt')
           AND OLD.stage NOT IN ('draft','on_review','needs_rework','archived') THEN
            RAISE EXCEPTION 'venue change forbidden after booking link for % application', OLD.kind
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_applications_venue_lock
    BEFORE UPDATE OF venue_id ON applications.applications
    FOR EACH ROW EXECUTE FUNCTION applications.forbid_venue_change();

-- billing --------------------------------------------------------------------

CREATE TABLE billing.accountant_assignments (
    application_id int PRIMARY KEY,
    accountant_id int NOT NULL
);

CREATE TABLE billing.fines (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    loan_id int,
    kind text NOT NULL CHECK (kind IN ('overdue','lost','damaged')),
    amount numeric(12,2) NOT NULL CHECK (amount >= 0),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','paid')),
    paid_outside boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL
);

CREATE TABLE billing.invoices (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    kind text NOT NULL CHECK (kind IN ('books','fine')),
    fine_id int REFERENCES billing.fines,
    amount numeric(12,2) NOT NULL CHECK (amount > 0),
    status text NOT NULL CHECK (status IN ('active','cancelled')),
    issued_at timestamptz NOT NULL,
    payment_clock_started_at timestamptz NOT NULL,
    venue_id int NOT NULL,
    requisites jsonb NOT NULL,
    cancel_reason text,
    CHECK ((kind = 'fine') = (fine_id IS NOT NULL))
);
CREATE UNIQUE INDEX uq_invoices_one_active_books
    ON billing.invoices (application_id) WHERE kind = 'books' AND status = 'active';

CREATE TABLE billing.payments (
    id serial PRIMARY KEY,
    invoice_id int NOT NULL REFERENCES billing.invoices,
    amount numeric(12,2) NOT NULL CHECK (amount > 0),
    linked_at timestamptz NOT NULL,
    linked_by int NOT NULL,
    overpayment boolean NOT NULL DEFAULT false,
    unlinked_at timestamptz,
    unlink_reason text,
    refunded boolean NOT NULL DEFAULT false,
    CHECK (unlinked_at IS NULL OR unlink_reason IS NOT NULL)
);

CREATE TABLE billing.fine_rates (
    representative_id int NOT NULL,
    venue_id int NOT NULL,
    kind text NOT NULL CHECK (kind IN ('overdue','lost','damaged')),
    amount numeric(12,2) NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (representative_id, venue_id, kind)
);

CREATE FUNCTION billing.forbid_cancel_paid_invoice() RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'cancelled' AND OLD.status = 'active' AND EXISTS (
        SELECT 1 FROM billing.payments p
        WHERE p.invoice_id = OLD.id AND p.unlinked_at IS NULL AND NOT p.refunded
    ) THEN
        RAISE EXCEPTION 'invoice % has a linked payment', OLD.id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoices_cancel_guard
    BEFORE UPDATE OF status ON billing.invoices
    FOR EACH ROW EXECUTE FUNCTION billing.forbid_cancel_paid_invoice();

CREATE FUNCTION billing.forbid_payment_to_cancelled() RETURNS trigger AS $$
BEGIN
    IF (SELECT status FROM billing.invoices WHERE id = NEW.invoice_id) <> 'active' THEN
        RAISE EXCEPTION 'payment cannot be linked to a cancelled invoice' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_active_invoice
    BEFORE INSERT ON billing.payments
    FOR EACH ROW EXECUTE FUNCTION billing.forbid_payment_to_cancelled();

-- scheduling -----------------------------------------------------------------

CREATE TABLE scheduling.venue_limits (
    venue_id int PRIMARY KEY,
    max_capacity int NOT NULL CHECK (max_capacity > 0)
);

CREATE TABLE scheduling.slots (
    id serial PRIMARY KEY,
    venue_id int NOT NULL,
    sphere_id int NOT NULL,
    starts_at timestamptz NOT NULL,
    capacity int NOT NULL CHECK (capacity > 0),
    removed boolean NOT NULL DEFAULT false
);

CREATE FUNCTION scheduling.check_slot_capacity() RETURNS trigger AS $$
DECLARE
    lim int;
BEGIN
    SELECT max_capacity INTO lim FROM scheduling.venue_limits WHERE venue_id = NEW.venue_id;
    IF lim IS NULL THEN
        RAISE EXCEPTION 'no capacity limit for venue %', NEW.venue_id USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.capacity > lim THEN
        RAISE EXCEPTION 'slot capacity % exceeds venue maximum %', NEW.capacity, lim
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_slot_capacity_limit
    BEFORE INSERT OR UPDATE OF capacity ON scheduling.slots
    FOR EACH ROW EXECUTE FUNCTION scheduling.check_slot_capacity();

CREATE TABLE scheduling.booking_links (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    token text NOT NULL UNIQUE,
    purpose text NOT NULL CHECK (purpose IN ('issue','return')),
    active boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX uq_booking_links_one_active
    ON scheduling.booking_links (application_id) WHERE active;

CREATE TABLE scheduling.bookings (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    slot_id int NOT NULL REFERENCES scheduling.slots,
    purpose text NOT NULL CHECK (purpose IN ('issue','return')),
    status text NOT NULL CHECK (status IN ('active','cancelled','no_show','done')),
    booked_by text NOT NULL CHECK (booked_by IN ('client','representative','operator')),
    created_at timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_bookings_one_active
    ON scheduling.bookings (application_id) WHERE status = 'active';

CREATE TABLE scheduling.holds (
    application_id int NOT NULL,
    book_id int NOT NULL,
    PRIMARY KEY (application_id, book_id)
);

CREATE TABLE scheduling.loans (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    book_id int NOT NULL,
    issued_at timestamptz NOT NULL,
    due_at timestamptz NOT NULL,
    returned_at timestamptz,
    status text NOT NULL CHECK (status IN ('out','returned','lost')),
    damaged boolean NOT NULL DEFAULT false,
    overdue_flagged boolean NOT NULL DEFAULT false
);

-- notifications --------------------------------------------------------------

CREATE TABLE notifications.templates (
    id serial PRIMARY KEY,
    venue_id int NOT NULL,
    kind_group text NOT NULL CHECK (kind_group IN ('paid','social')),
    type text NOT NULL CHECK (type IN ('booking','cancel')),
    body text NOT NULL,
    UNIQUE (venue_id, kind_group, type)
);

CREATE TABLE notifications.emails (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    recipients jsonb NOT NULL,
    type text NOT NULL CHECK (type IN ('booking','cancel')),
    template_id int REFERENCES notifications.templates,
    body text NOT NULL,
    status text NOT NULL CHECK (status IN ('sent','no_template')),
    created_at timestamptz NOT NULL
);

-- chat -----------------------------------------------------------------------

CREATE TABLE chat.messages (
    id serial PRIMARY KEY,
    application_id int NOT NULL,
    author_id int,
    body text NOT NULL,
    is_event boolean NOT NULL,
    created_at timestamptz NOT NULL,
    CHECK (is_event OR author_id IS NOT NULL)
);

CREATE FUNCTION chat.forbid_message_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'chat messages cannot be edited or deleted' USING ERRCODE = 'check_violation';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_chat_messages_immutable
    BEFORE UPDATE OR DELETE ON chat.messages
    FOR EACH ROW EXECUTE FUNCTION chat.forbid_message_changes();

-- events ---------------------------------------------------------------------

CREATE TABLE events.outbox (
    id bigserial PRIMARY KEY,
    topic text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    processed_at timestamptz
);
CREATE INDEX ix_outbox_pending ON events.outbox (id) WHERE processed_at IS NULL;
"""


def _statements(sql: str):
    """asyncpg не выполняет несколько команд за раз: режем по `;`, не трогая тела функций."""
    buf: list[str] = []
    inside_body = False
    for line in sql.splitlines():
        if not inside_body and line.lstrip().startswith("--"):
            continue
        buf.append(line)
        if line.count("$$") % 2:
            inside_body = not inside_body
        if not inside_body and line.rstrip().endswith(";"):
            yield "\n".join(buf)
            buf = []


def upgrade() -> None:
    bind = op.get_bind()
    for statement in _statements(UPGRADE):
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    for schema in ("events", "chat", "notifications", "scheduling", "billing", "applications"):
        op.execute(f"DROP SCHEMA {schema} CASCADE")
