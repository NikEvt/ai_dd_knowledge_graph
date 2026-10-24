<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# events.outbox
Миграция: [`migrations/versions/0001_initial.py:348`](../../migrations/versions/0001_initial.py#L348)

## Поля
- id: bigint NOT NULL PK
- topic: text NOT NULL
- payload: jsonb NOT NULL
- created_at: timestamp with time zone NOT NULL
- processed_at: timestamp with time zone

## Ограничения и триггеры
- ix_outbox_pending (index на events.outbox): CREATE INDEX ix_outbox_pending ON events.outbox USING btree (id) WHERE (processed_at IS NULL) (migrations/versions/0001_initial.py:355)

## ORM
- libs/events/outbox.py::OutboxEvent:18 (orm_model)

## Пишут (код)
- libs/events/outbox.py::dispatch_pending
- libs/events/outbox.py::publish
- libs/events/relay.py::relay_forever
