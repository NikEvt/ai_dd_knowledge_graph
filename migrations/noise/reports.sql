-- Внутренняя отчётность: снимки метрик, определения отчётов, запуски и расписания выгрузок.

CREATE SCHEMA reports;

CREATE TABLE reports.metric_snapshots (
    id bigserial PRIMARY KEY,
    metric text NOT NULL,
    dimension text NOT NULL DEFAULT '',
    day date NOT NULL,
    value numeric(14, 2) NOT NULL,
    taken_at timestamptz NOT NULL,
    CONSTRAINT metric_snapshots_metric_format CHECK (metric ~ '^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$'),
    CONSTRAINT metric_snapshots_dimension_len CHECK (length(dimension) <= 64),
    CONSTRAINT metric_snapshots_point UNIQUE (metric, dimension, day)
);

CREATE INDEX metric_snapshots_metric_day ON reports.metric_snapshots (metric, day);

CREATE TABLE reports.report_definitions (
    id serial PRIMARY KEY,
    code text NOT NULL UNIQUE,
    title text NOT NULL,
    kind text NOT NULL,
    params jsonb NOT NULL DEFAULT '{}'::jsonb,
    owner_id integer NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT report_definitions_kind CHECK (kind IN ('metric_summary', 'metric_trend', 'run_audit')),
    CONSTRAINT report_definitions_code_format CHECK (code ~ '^[a-z][a-z0-9_-]{2,63}$'),
    CONSTRAINT report_definitions_title_not_blank CHECK (btrim(title) <> ''),
    CONSTRAINT report_definitions_params_object CHECK (jsonb_typeof(params) = 'object')
);

CREATE UNIQUE INDEX report_definitions_owner_title_active
    ON reports.report_definitions (owner_id, lower(title))
    WHERE is_active;

CREATE TABLE reports.export_schedules (
    id serial PRIMARY KEY,
    definition_id integer NOT NULL REFERENCES reports.report_definitions (id),
    every_hours integer NOT NULL,
    next_run_at timestamptz NOT NULL,
    recipients jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_by integer NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    last_enqueued_at timestamptz,
    created_at timestamptz NOT NULL,
    CONSTRAINT export_schedules_interval CHECK (every_hours BETWEEN 1 AND 744),
    CONSTRAINT export_schedules_recipients_array CHECK (jsonb_typeof(recipients) = 'array')
);

CREATE UNIQUE INDEX export_schedules_one_active
    ON reports.export_schedules (definition_id)
    WHERE is_active;

CREATE TABLE reports.report_runs (
    id bigserial PRIMARY KEY,
    definition_id integer NOT NULL REFERENCES reports.report_definitions (id),
    schedule_id integer REFERENCES reports.export_schedules (id),
    scheduled_for timestamptz,
    status text NOT NULL DEFAULT 'requested',
    params jsonb NOT NULL DEFAULT '{}'::jsonb,
    body jsonb,
    error text,
    requested_by integer NOT NULL,
    requested_at timestamptz NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    CONSTRAINT report_runs_status CHECK (status IN ('requested', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT report_runs_body_on_completion CHECK ((status = 'completed') = (body IS NOT NULL)),
    CONSTRAINT report_runs_error_on_failure CHECK (status <> 'failed' OR error IS NOT NULL),
    CONSTRAINT report_runs_finished CHECK (
        (status IN ('completed', 'failed', 'cancelled')) = (finished_at IS NOT NULL)
    ),
    CONSTRAINT report_runs_schedule_slot CHECK ((schedule_id IS NULL) = (scheduled_for IS NULL))
);

CREATE INDEX report_runs_requested_at ON reports.report_runs (requested_at);
CREATE INDEX report_runs_definition ON reports.report_runs (definition_id, requested_at DESC);

CREATE UNIQUE INDEX report_runs_schedule_once
    ON reports.report_runs (schedule_id, scheduled_for)
    WHERE schedule_id IS NOT NULL;

CREATE UNIQUE INDEX report_runs_one_in_flight
    ON reports.report_runs (definition_id, requested_by)
    WHERE schedule_id IS NULL AND status IN ('requested', 'running');

CREATE TABLE reports.run_notifications (
    id bigserial PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES reports.report_runs (id) ON DELETE CASCADE,
    recipient_id integer NOT NULL,
    kind text NOT NULL,
    body text NOT NULL,
    created_at timestamptz NOT NULL,
    read_at timestamptz,
    CONSTRAINT run_notifications_kind CHECK (kind IN ('completed', 'failed', 'cancelled')),
    CONSTRAINT run_notifications_once UNIQUE (run_id, recipient_id)
);

CREATE INDEX run_notifications_unread
    ON reports.run_notifications (recipient_id)
    WHERE read_at IS NULL;

-- Завершённый запуск — документ: его нельзя переписать, только удалить по сроку хранения.
CREATE FUNCTION reports.report_runs_immutable() RETURNS trigger AS $$
BEGIN
    IF OLD.status IN ('completed', 'failed', 'cancelled') THEN
        RAISE EXCEPTION 'запуск % уже завершён (%), изменять его нельзя', OLD.id, OLD.status
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_report_runs_immutable
    BEFORE UPDATE ON reports.report_runs
    FOR EACH ROW EXECUTE FUNCTION reports.report_runs_immutable();

CREATE FUNCTION reports.report_runs_transition() RETURNS trigger AS $$
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;
    IF NOT (
        (OLD.status = 'requested' AND NEW.status IN ('running', 'failed', 'cancelled'))
        OR (OLD.status = 'running' AND NEW.status IN ('completed', 'failed'))
    ) THEN
        RAISE EXCEPTION 'недопустимый переход запуска %: % -> %', OLD.id, OLD.status, NEW.status
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_report_runs_transition
    BEFORE UPDATE OF status ON reports.report_runs
    FOR EACH ROW EXECUTE FUNCTION reports.report_runs_transition();

-- Тип отчёта определяет формат body; после первых запусков менять его нельзя.
CREATE FUNCTION reports.report_definitions_kind_locked() RETURNS trigger AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM reports.report_runs r WHERE r.definition_id = OLD.id) THEN
        RAISE EXCEPTION 'у отчёта % уже есть запуски, тип менять нельзя', OLD.code
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_report_definitions_kind_locked
    BEFORE UPDATE OF kind ON reports.report_definitions
    FOR EACH ROW
    WHEN (OLD.kind IS DISTINCT FROM NEW.kind)
    EXECUTE FUNCTION reports.report_definitions_kind_locked();
