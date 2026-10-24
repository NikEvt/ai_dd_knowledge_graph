-- marketing: рассылки и кампании для читателей и партнёров

CREATE SCHEMA marketing;

-- Менеджеры рассылок. Строка без venue_id — менеджер всей сети.
CREATE TABLE marketing.managers (
    id serial PRIMARY KEY,
    manager_id int NOT NULL,
    venue_id int,
    full_name text NOT NULL
);

CREATE UNIQUE INDEX managers_network_uq ON marketing.managers (manager_id) WHERE venue_id IS NULL;
CREATE UNIQUE INDEX managers_venue_uq ON marketing.managers (manager_id, venue_id) WHERE venue_id IS NOT NULL;

CREATE TABLE marketing.audiences (
    id serial PRIMARY KEY,
    venue_id int NOT NULL,
    name text NOT NULL CHECK (length(trim(name)) > 0),
    created_by int NOT NULL,
    created_at timestamptz NOT NULL,
    archived boolean NOT NULL DEFAULT false,
    last_campaign_at timestamptz,
    CONSTRAINT audiences_venue_name_uq UNIQUE (venue_id, name)
);

CREATE TABLE marketing.audience_members (
    id serial PRIMARY KEY,
    audience_id int NOT NULL REFERENCES marketing.audiences (id) ON DELETE CASCADE,
    email text NOT NULL CHECK (position('@' IN email) > 1),
    full_name text NOT NULL,
    segment text NOT NULL CHECK (segment IN ('paid', 'debt', 'social', 'vip', 'corporate')),
    opted_out boolean NOT NULL DEFAULT false,
    added_at timestamptz NOT NULL
);

CREATE UNIQUE INDEX audience_members_email_uq ON marketing.audience_members (audience_id, email);
CREATE INDEX audience_members_email_idx ON marketing.audience_members (email) WHERE NOT opted_out;

-- Шаблоны писем. Строка без venue_id — шаблон сети по умолчанию.
CREATE TABLE marketing.campaign_templates (
    id serial PRIMARY KEY,
    venue_id int,
    audience_group text NOT NULL,
    type text NOT NULL,
    body text NOT NULL CHECK (length(body) > 0),
    updated_at timestamptz NOT NULL,
    CONSTRAINT campaign_templates_audience_group_check CHECK (audience_group IN ('paid', 'social', 'vip')),
    CONSTRAINT campaign_templates_venue_group_type_uq UNIQUE (venue_id, audience_group, type)
);

CREATE UNIQUE INDEX campaign_templates_default_uq
    ON marketing.campaign_templates (audience_group, type) WHERE venue_id IS NULL;

CREATE TABLE marketing.campaigns (
    id serial PRIMARY KEY,
    venue_id int NOT NULL,
    audience_id int NOT NULL REFERENCES marketing.audiences (id),
    type text NOT NULL,
    subject text NOT NULL,
    status text NOT NULL
        CHECK (status IN ('draft', 'scheduled', 'preparing', 'sending', 'sent', 'cancelled')),
    created_by int NOT NULL,
    created_at timestamptz NOT NULL,
    scheduled_at timestamptz,
    launched_at timestamptz,
    finished_at timestamptz,
    recipients_count int NOT NULL DEFAULT 0 CHECK (recipients_count >= 0),
    sent_count int NOT NULL DEFAULT 0 CHECK (sent_count >= 0),
    skipped_count int NOT NULL DEFAULT 0 CHECK (skipped_count >= 0),
    CHECK (status <> 'scheduled' OR scheduled_at IS NOT NULL)
);

-- По одной аудитории одновременно идёт не больше одной кампании.
CREATE UNIQUE INDEX campaigns_audience_active_uq
    ON marketing.campaigns (audience_id) WHERE status IN ('preparing', 'sending');
CREATE INDEX campaigns_scheduled_idx ON marketing.campaigns (scheduled_at) WHERE status = 'scheduled';

CREATE TABLE marketing.sent_messages (
    id serial PRIMARY KEY,
    campaign_id int NOT NULL REFERENCES marketing.campaigns (id) ON DELETE CASCADE,
    template_id int REFERENCES marketing.campaign_templates (id) ON DELETE SET NULL,
    email text NOT NULL,
    segment text NOT NULL,
    body text NOT NULL,
    status text NOT NULL CHECK (status IN ('queued', 'sent', 'skipped', 'bounced')),
    skip_reason text,
    is_test boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL,
    sent_at timestamptz,
    CHECK (status NOT IN ('sent', 'bounced') OR sent_at IS NOT NULL)
);

CREATE UNIQUE INDEX sent_messages_campaign_email_uq
    ON marketing.sent_messages (campaign_id, email) WHERE NOT is_test;
CREATE INDEX sent_messages_bounced_idx ON marketing.sent_messages (email) WHERE status = 'bounced';

-- Отписки. Строка без venue_id — отписка от всех рассылок сети.
CREATE TABLE marketing.unsubscriptions (
    id serial PRIMARY KEY,
    email text NOT NULL,
    venue_id int,
    reason text NOT NULL CHECK (reason IN ('reader', 'bounce', 'complaint', 'operator')),
    created_at timestamptz NOT NULL
);

CREATE UNIQUE INDEX unsubscriptions_network_uq ON marketing.unsubscriptions (email) WHERE venue_id IS NULL;
CREATE UNIQUE INDEX unsubscriptions_venue_uq
    ON marketing.unsubscriptions (email, venue_id) WHERE venue_id IS NOT NULL;

-- Адреса хранятся в нижнем регистре без пробелов
CREATE FUNCTION marketing.normalize_email() RETURNS trigger AS $$
BEGIN
    NEW.email := lower(trim(NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audience_members_normalize_email
    BEFORE INSERT OR UPDATE OF email ON marketing.audience_members
    FOR EACH ROW EXECUTE FUNCTION marketing.normalize_email();

CREATE TRIGGER unsubscriptions_normalize_email
    BEFORE INSERT OR UPDATE OF email ON marketing.unsubscriptions
    FOR EACH ROW EXECUTE FUNCTION marketing.normalize_email();

-- Завершённая или отменённая кампания больше не меняет статус
CREATE FUNCTION marketing.campaigns_guard_status() RETURNS trigger AS $$
BEGIN
    IF OLD.status IN ('sent', 'cancelled') AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'кампания % уже в статусе %', OLD.id, OLD.status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER campaigns_guard_status
    BEFORE UPDATE OF status ON marketing.campaigns
    FOR EACH ROW EXECUTE FUNCTION marketing.campaigns_guard_status();

-- Текст отправленного письма не меняется: это то, что получил читатель
CREATE FUNCTION marketing.sent_messages_freeze_body() RETURNS trigger AS $$
BEGIN
    IF OLD.sent_at IS NOT NULL AND NEW.body IS DISTINCT FROM OLD.body THEN
        RAISE EXCEPTION 'письмо % уже отправлено, текст менять нельзя', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sent_messages_freeze_body
    BEFORE UPDATE ON marketing.sent_messages
    FOR EACH ROW EXECUTE FUNCTION marketing.sent_messages_freeze_body();
