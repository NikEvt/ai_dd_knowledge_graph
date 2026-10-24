-- Открытые лекции и мероприятия на площадках библиотеки.

CREATE SCHEMA lectures;

-- Реплика лимитов мест площадок. Пишется только подписчиком lectures.venue_limit_changed.
CREATE TABLE lectures.venue_capacity_limits (
    venue_id integer PRIMARY KEY,
    max_capacity integer NOT NULL CHECK (max_capacity > 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE lectures.events (
    id serial PRIMARY KEY,
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    venue_id integer NOT NULL,
    organizer_id integer NOT NULL,
    starts_at timestamptz NOT NULL,
    capacity integer NOT NULL CHECK (capacity > 0),
    capacity_manual boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'cancelled', 'finished')),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);

-- Одна площадка не может принимать два мероприятия одновременно.
CREATE UNIQUE INDEX events_venue_slot_uq
    ON lectures.events (venue_id, starts_at)
    WHERE status = 'scheduled';

CREATE INDEX events_upcoming_idx ON lectures.events (venue_id, starts_at) WHERE status = 'scheduled';

CREATE TABLE lectures.registrations (
    id serial PRIMARY KEY,
    event_id integer NOT NULL REFERENCES lectures.events (id),
    listener_id integer NOT NULL,
    status text NOT NULL CHECK (status IN ('confirmed', 'attended', 'cancelled')),
    source text NOT NULL DEFAULT 'direct' CHECK (source IN ('direct', 'waitlist')),
    created_at timestamptz NOT NULL,
    cancelled_at timestamptz,
    cancel_reason text,
    attended_at timestamptz,
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),
    CHECK ((status = 'attended') = (attended_at IS NOT NULL))
);

CREATE UNIQUE INDEX registrations_active_uq
    ON lectures.registrations (event_id, listener_id)
    WHERE status = 'confirmed';

CREATE INDEX registrations_listener_idx ON lectures.registrations (listener_id) WHERE status = 'confirmed';

CREATE TABLE lectures.waitlist (
    id serial PRIMARY KEY,
    event_id integer NOT NULL REFERENCES lectures.events (id),
    listener_id integer NOT NULL,
    status text NOT NULL DEFAULT 'waiting'
        CHECK (status IN ('waiting', 'promoted', 'left', 'cancelled', 'expired')),
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    CHECK ((status = 'waiting') = (closed_at IS NULL))
);

CREATE UNIQUE INDEX waitlist_waiting_uq
    ON lectures.waitlist (event_id, listener_id)
    WHERE status = 'waiting';

CREATE INDEX waitlist_queue_idx ON lectures.waitlist (event_id, created_at, id) WHERE status = 'waiting';

CREATE TABLE lectures.notifications (
    id serial PRIMARY KEY,
    listener_id integer NOT NULL,
    event_id integer NOT NULL REFERENCES lectures.events (id),
    kind text NOT NULL CHECK (kind IN (
        'registered', 'registration_cancelled', 'event_moved', 'event_cancelled',
        'waitlist_promoted', 'waitlist_expired', 'reminder'
    )),
    body text NOT NULL,
    dedup_key text NOT NULL,
    created_at timestamptz NOT NULL,
    sent_at timestamptz,
    UNIQUE (dedup_key)
);

CREATE INDEX notifications_listener_idx ON lectures.notifications (listener_id, created_at);

CREATE FUNCTION lectures.check_capacity() RETURNS trigger AS $$
DECLARE
    venue_limit integer;
BEGIN
    SELECT max_capacity INTO venue_limit
    FROM lectures.venue_capacity_limits
    WHERE venue_id = NEW.venue_id;
    IF venue_limit IS NULL THEN
        RAISE EXCEPTION 'venue % has no capacity limit', NEW.venue_id;
    END IF;
    IF NEW.capacity > venue_limit THEN
        RAISE EXCEPTION 'event capacity % exceeds venue % limit %', NEW.capacity, NEW.venue_id, venue_limit;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lecture_capacity_limit
    BEFORE INSERT OR UPDATE OF capacity, venue_id ON lectures.events
    FOR EACH ROW EXECUTE FUNCTION lectures.check_capacity();

CREATE FUNCTION lectures.check_seat_available() RETURNS trigger AS $$
DECLARE
    ev record;
    taken integer;
BEGIN
    SELECT capacity, status INTO ev FROM lectures.events WHERE id = NEW.event_id FOR UPDATE;
    IF ev.status <> 'scheduled' THEN
        RAISE EXCEPTION 'event % is not open for registration', NEW.event_id;
    END IF;
    SELECT count(*) INTO taken
    FROM lectures.registrations
    WHERE event_id = NEW.event_id AND status = 'confirmed' AND id <> NEW.id;
    IF taken >= ev.capacity THEN
        RAISE EXCEPTION 'event % is full', NEW.event_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_registration_seat
    BEFORE INSERT OR UPDATE OF status ON lectures.registrations
    FOR EACH ROW WHEN (NEW.status = 'confirmed')
    EXECUTE FUNCTION lectures.check_seat_available();

CREATE FUNCTION lectures.touch_updated_at() RETURNS trigger AS $$
BEGIN
    IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at THEN
        NEW.updated_at := now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lecture_touch
    BEFORE UPDATE ON lectures.events
    FOR EACH ROW EXECUTE FUNCTION lectures.touch_updated_at();
