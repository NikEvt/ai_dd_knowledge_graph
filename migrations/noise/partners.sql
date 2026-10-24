-- Партнёрские агентства: заявки на подключение, договоры, сделки, комиссии.

CREATE SCHEMA partners;

CREATE TABLE partners.onboarding_requests (
    id serial PRIMARY KEY,
    inn text NOT NULL CHECK (inn ~ '^[0-9]{10}$'),
    kpp text CHECK (kpp ~ '^[0-9]{9}$'),
    legal_name text,
    contact_name text NOT NULL,
    contact_email text NOT NULL CHECK (contact_email LIKE '%_@_%'),
    contact_phone text,
    status text NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','approved','rejected','duplicate','expired')),
    submitted_at timestamptz NOT NULL,
    decided_at timestamptz,
    decided_by int,
    reject_reason text,
    partner_id int,
    CHECK (status <> 'rejected' OR reject_reason IS NOT NULL),
    CHECK (status = 'open' OR decided_at IS NOT NULL)
);

CREATE UNIQUE INDEX ux_onboarding_requests_open_inn
    ON partners.onboarding_requests (inn) WHERE status = 'open';

CREATE TABLE partners.partners (
    id serial PRIMARY KEY,
    inn text NOT NULL UNIQUE CHECK (inn ~ '^[0-9]{10}$'),
    kpp text CHECK (kpp ~ '^[0-9]{9}$'),
    legal_name text CHECK (legal_name IS NULL OR length(btrim(legal_name)) > 0),
    contact_name text,
    contact_email text CHECK (contact_email LIKE '%_@_%'),
    contact_phone text,
    manager_id int NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE partners.contracts (
    id serial PRIMARY KEY,
    partner_id int NOT NULL REFERENCES partners.partners (id),
    number text NOT NULL UNIQUE,
    commission_pct numeric(5,2) NOT NULL CHECK (commission_pct >= 0 AND commission_pct <= 100),
    credit_allowed boolean NOT NULL DEFAULT false,
    credit_limit numeric(12,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','active','suspended','expired','terminated')),
    suspend_reason text,
    valid_from date NOT NULL,
    valid_to date NOT NULL,
    activated_at timestamptz,
    created_at timestamptz NOT NULL,
    CHECK (valid_to >= valid_from),
    CHECK (credit_allowed OR credit_limit = 0),
    CHECK (status <> 'suspended' OR suspend_reason IS NOT NULL)
);

-- У партнёра не больше одного действующего договора
CREATE UNIQUE INDEX ux_contracts_partner_current
    ON partners.contracts (partner_id) WHERE status IN ('draft','active','suspended');

CREATE TABLE partners.deals (
    id serial PRIMARY KEY,
    contract_id int NOT NULL REFERENCES partners.contracts (id),
    external_ref text NOT NULL,
    amount numeric(12,2) NOT NULL CHECK (amount > 0),
    on_credit boolean NOT NULL,
    status text NOT NULL CHECK (status IN ('awaiting_prepayment','open','closed','cancelled')),
    created_at timestamptz NOT NULL,
    due_at timestamptz,
    prepaid_at timestamptz,
    closed_at timestamptz,
    paid_at timestamptz,
    overdue_flagged boolean NOT NULL DEFAULT false,
    UNIQUE (contract_id, external_ref),
    CHECK (on_credit = (due_at IS NOT NULL)),
    CHECK (NOT on_credit OR (status <> 'awaiting_prepayment' AND prepaid_at IS NULL)),
    CHECK (status <> 'closed' OR closed_at IS NOT NULL)
);

CREATE INDEX ix_deals_contract_unpaid_credit
    ON partners.deals (contract_id) WHERE on_credit AND paid_at IS NULL AND status <> 'cancelled';

CREATE TABLE partners.payouts (
    id serial PRIMARY KEY,
    partner_id int NOT NULL REFERENCES partners.partners (id),
    period date NOT NULL CHECK (extract(day FROM period) = 1),
    total numeric(12,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    commissions_count int NOT NULL DEFAULT 0 CHECK (commissions_count >= 0),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
    UNIQUE (partner_id, period)
);

CREATE TABLE partners.commissions (
    id serial PRIMARY KEY,
    deal_id int NOT NULL UNIQUE REFERENCES partners.deals (id),
    contract_id int NOT NULL REFERENCES partners.contracts (id),
    partner_id int NOT NULL REFERENCES partners.partners (id),
    base_amount numeric(12,2) NOT NULL CHECK (base_amount > 0),
    rate_pct numeric(5,2) NOT NULL CHECK (rate_pct >= 0 AND rate_pct <= 100),
    amount numeric(12,2) NOT NULL CHECK (amount >= base_amount),
    accrued_at timestamptz NOT NULL,
    payout_id int REFERENCES partners.payouts (id)
);

-- Сделки: работа в кредит и лимит договора

CREATE FUNCTION partners.check_credit_limit() RETURNS trigger AS $$
DECLARE
    c partners.contracts%ROWTYPE;
    exposure numeric(12,2);
BEGIN
    SELECT * INTO c FROM partners.contracts WHERE id = NEW.contract_id FOR UPDATE;
    IF NEW.on_credit AND NOT c.credit_allowed THEN
        RAISE EXCEPTION 'contract % does not allow credit deals', c.number
            USING ERRCODE = 'check_violation';
    END IF;
    SELECT coalesce(sum(amount), 0) INTO exposure
    FROM partners.deals
    WHERE contract_id = NEW.contract_id AND on_credit AND paid_at IS NULL AND status <> 'cancelled';
    IF exposure > c.credit_limit THEN
        RAISE EXCEPTION 'credit limit of contract % exceeded, new deals are blocked', c.number
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.on_credit AND exposure + NEW.amount > c.credit_limit THEN
        RAISE EXCEPTION 'deal exceeds credit limit of contract %: % + % > %',
            c.number, exposure, NEW.amount, c.credit_limit
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contract_credit_limit
    BEFORE INSERT ON partners.deals
    FOR EACH ROW EXECUTE FUNCTION partners.check_credit_limit();

-- Договор активируется только при заполненных реквизитах партнёра

CREATE FUNCTION partners.check_partner_requisites() RETURNS trigger AS $$
DECLARE
    p partners.partners%ROWTYPE;
BEGIN
    IF NEW.status = 'active' AND OLD.status = 'draft' THEN
        SELECT * INTO p FROM partners.partners WHERE id = NEW.partner_id;
        IF p.inn IS NULL OR p.kpp IS NULL OR coalesce(btrim(p.legal_name), '') = '' THEN
            RAISE EXCEPTION 'partner % has incomplete requisites', p.id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contract_requisites
    BEFORE UPDATE OF status ON partners.contracts
    FOR EACH ROW EXECUTE FUNCTION partners.check_partner_requisites();

-- Начисленная комиссия не пересчитывается

CREATE FUNCTION partners.forbid_commission_change() RETURNS trigger AS $$
BEGIN
    IF NEW.amount <> OLD.amount OR NEW.rate_pct <> OLD.rate_pct OR NEW.base_amount <> OLD.base_amount THEN
        RAISE EXCEPTION 'accrued commission % cannot be recalculated', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_commission_frozen
    BEFORE UPDATE ON partners.commissions
    FOR EACH ROW EXECUTE FUNCTION partners.forbid_commission_change();

-- История условий договора для сверки с партнёром

CREATE TABLE partners.contract_history (
    id serial PRIMARY KEY,
    contract_id int NOT NULL REFERENCES partners.contracts (id),
    field text NOT NULL CHECK (field IN ('commission_pct','credit_allowed','credit_limit','status')),
    old_value text,
    new_value text,
    changed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_contract_history_contract ON partners.contract_history (contract_id, id);

CREATE FUNCTION partners.log_contract_change() RETURNS trigger AS $$
BEGIN
    IF NEW.commission_pct IS DISTINCT FROM OLD.commission_pct THEN
        INSERT INTO partners.contract_history (contract_id, field, old_value, new_value)
        VALUES (NEW.id, 'commission_pct', OLD.commission_pct::text, NEW.commission_pct::text);
    END IF;
    IF NEW.credit_allowed IS DISTINCT FROM OLD.credit_allowed THEN
        INSERT INTO partners.contract_history (contract_id, field, old_value, new_value)
        VALUES (NEW.id, 'credit_allowed', OLD.credit_allowed::text, NEW.credit_allowed::text);
    END IF;
    IF NEW.credit_limit IS DISTINCT FROM OLD.credit_limit THEN
        INSERT INTO partners.contract_history (contract_id, field, old_value, new_value)
        VALUES (NEW.id, 'credit_limit', OLD.credit_limit::text, NEW.credit_limit::text);
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO partners.contract_history (contract_id, field, old_value, new_value)
        VALUES (NEW.id, 'status', OLD.status, NEW.status);
    END IF;
    RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contract_history
    AFTER UPDATE ON partners.contracts
    FOR EACH ROW EXECUTE FUNCTION partners.log_contract_change();
