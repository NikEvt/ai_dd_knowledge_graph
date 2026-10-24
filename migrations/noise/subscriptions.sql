-- Абонементы читателей: тарифы, абонементы, счета за месяц и платежи по ним.
CREATE SCHEMA subscriptions;

CREATE TABLE subscriptions.plans (
    id          serial PRIMARY KEY,
    code        varchar(32)   NOT NULL,
    name        varchar(200)  NOT NULL,
    kind        varchar(16)   NOT NULL,
    monthly_fee numeric(12,2) NOT NULL,
    max_books   integer       NOT NULL DEFAULT 5,
    archived    boolean       NOT NULL DEFAULT false,
    CONSTRAINT uq_plans_code UNIQUE (code),
    CONSTRAINT ck_plans_kind CHECK (kind IN ('regular', 'social', 'corporate')),
    CONSTRAINT ck_plans_fee CHECK (monthly_fee > 0),
    CONSTRAINT ck_plans_max_books CHECK (max_books BETWEEN 1 AND 50)
);

CREATE TABLE subscriptions.subscriptions (
    id           serial PRIMARY KEY,
    client_ref   varchar(64)  NOT NULL,
    plan_id      integer      NOT NULL REFERENCES subscriptions.plans (id),
    status       varchar(20)  NOT NULL DEFAULT 'pending',
    holder_name  varchar(200) NOT NULL,
    passport     varchar(20),
    birth_date   date,
    holder_check varchar(16)  NOT NULL DEFAULT 'pending',
    employer_ref varchar(64),
    paid_until   date,
    reminded_for date,
    created_at   timestamptz  NOT NULL,
    activated_at timestamptz,
    closed_at    timestamptz,
    CONSTRAINT ck_subscriptions_status
        CHECK (status IN ('pending', 'active', 'grace', 'expired', 'closed_duplicate')),
    CONSTRAINT ck_subscriptions_holder_check CHECK (holder_check IN ('pending', 'verified', 'rejected')),
    CONSTRAINT ck_subscriptions_paid_until CHECK (status IN ('pending', 'expired', 'closed_duplicate')
        OR paid_until IS NOT NULL),
    CONSTRAINT ck_subscriptions_closed CHECK ((status IN ('expired', 'closed_duplicate')) = (closed_at IS NOT NULL))
);

CREATE UNIQUE INDEX uq_subscriptions_one_active
    ON subscriptions.subscriptions (client_ref, plan_id)
    WHERE status IN ('active', 'grace');

CREATE INDEX ix_subscriptions_client ON subscriptions.subscriptions (client_ref);

CREATE TABLE subscriptions.invoices (
    id              serial PRIMARY KEY,
    subscription_id integer       NOT NULL REFERENCES subscriptions.subscriptions (id),
    period_start    date          NOT NULL,
    period_end      date          NOT NULL,
    amount          numeric(12,2) NOT NULL,
    paid_total      numeric(12,2) NOT NULL DEFAULT 0,
    status          varchar(8)    NOT NULL DEFAULT 'open',
    issued_at       timestamptz   NOT NULL,
    CONSTRAINT uq_invoices_period UNIQUE (subscription_id, period_start),
    CONSTRAINT ck_invoices_period CHECK (period_end > period_start),
    CONSTRAINT ck_invoices_amount CHECK (amount > 0),
    CONSTRAINT ck_invoices_paid_total CHECK (paid_total >= 0 AND paid_total <= amount),
    CONSTRAINT ck_invoices_status CHECK (status IN ('open', 'paid', 'void'))
);

CREATE UNIQUE INDEX uq_invoices_one_open
    ON subscriptions.invoices (subscription_id)
    WHERE status = 'open';

CREATE TABLE subscriptions.payments (
    id           serial PRIMARY KEY,
    invoice_id   integer       NOT NULL REFERENCES subscriptions.invoices (id),
    amount       numeric(12,2) NOT NULL,
    external_ref varchar(64),
    paid_at      timestamptz   NOT NULL,
    CONSTRAINT ck_payments_amount CHECK (amount > 0)
);

CREATE UNIQUE INDEX uq_payments_external_ref
    ON subscriptions.payments (external_ref)
    WHERE external_ref IS NOT NULL;

CREATE TABLE subscriptions.refunds (
    id              serial PRIMARY KEY,
    subscription_id integer       NOT NULL REFERENCES subscriptions.subscriptions (id),
    invoice_id      integer       NOT NULL REFERENCES subscriptions.invoices (id),
    amount          numeric(12,2) NOT NULL,
    status          varchar(8)    NOT NULL DEFAULT 'pending',
    created_at      timestamptz   NOT NULL,
    done_at         timestamptz,
    CONSTRAINT uq_refunds_invoice UNIQUE (invoice_id),
    CONSTRAINT ck_refunds_amount CHECK (amount > 0),
    CONSTRAINT ck_refunds_status CHECK (status IN ('pending', 'done')),
    CONSTRAINT ck_refunds_done CHECK ((status = 'done') = (done_at IS NOT NULL))
);

CREATE INDEX ix_refunds_pending ON subscriptions.refunds (created_at) WHERE status = 'pending';

CREATE TABLE subscriptions.status_history (
    id              bigserial PRIMARY KEY,
    subscription_id integer     NOT NULL REFERENCES subscriptions.subscriptions (id),
    old_status      varchar(20) NOT NULL,
    new_status      varchar(20) NOT NULL,
    changed_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions.notices (
    id              bigserial PRIMARY KEY,
    subscription_id integer     NOT NULL REFERENCES subscriptions.subscriptions (id),
    kind            varchar(32) NOT NULL,
    body            text        NOT NULL,
    created_at      timestamptz NOT NULL
);

-- Платёж принимается только в открытый счёт и не больше остатка по нему.
CREATE FUNCTION subscriptions.payments_guard() RETURNS trigger AS $$
DECLARE
    inv subscriptions.invoices%ROWTYPE;
BEGIN
    SELECT * INTO inv FROM subscriptions.invoices WHERE id = NEW.invoice_id FOR UPDATE;
    IF inv.status <> 'open' THEN
        RAISE EXCEPTION 'invoice % is not open', NEW.invoice_id;
    END IF;
    IF inv.paid_total + NEW.amount > inv.amount THEN
        RAISE EXCEPTION 'payment exceeds invoice % balance', NEW.invoice_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_guard
    BEFORE INSERT ON subscriptions.payments
    FOR EACH ROW EXECUTE FUNCTION subscriptions.payments_guard();

CREATE FUNCTION subscriptions.payments_apply() RETURNS trigger AS $$
BEGIN
    UPDATE subscriptions.invoices
       SET paid_total = paid_total + NEW.amount
     WHERE id = NEW.invoice_id;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payments_apply
    AFTER INSERT ON subscriptions.payments
    FOR EACH ROW EXECUTE FUNCTION subscriptions.payments_apply();

-- Закрытый абонемент не возвращается в работу: клиент оформляет новый.
CREATE FUNCTION subscriptions.subscriptions_terminal_guard() RETURNS trigger AS $$
BEGIN
    IF OLD.status IN ('expired', 'closed_duplicate') AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'subscription % is closed (%)', OLD.id, OLD.status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_terminal_guard
    BEFORE UPDATE OF status ON subscriptions.subscriptions
    FOR EACH ROW EXECUTE FUNCTION subscriptions.subscriptions_terminal_guard();

CREATE FUNCTION subscriptions.subscriptions_log_status() RETURNS trigger AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO subscriptions.status_history (subscription_id, old_status, new_status)
        VALUES (NEW.id, OLD.status, NEW.status);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_subscriptions_log_status
    AFTER UPDATE OF status ON subscriptions.subscriptions
    FOR EACH ROW EXECUTE FUNCTION subscriptions.subscriptions_log_status();
