<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.status_history
Миграция: `subscriptions.status_history`

## Поля
- id: bigint NOT NULL PK
- subscription_id: integer NOT NULL
- old_status: character varying NOT NULL
- new_status: character varying NOT NULL
- changed_at: timestamp with time zone NOT NULL

## Связи (FK)
- subscription_id → subscriptions.subscriptions

## ORM
- services/subscriptions/models.py::StatusChange:88 (orm_model)

## Правила
- R-SUBSCRIPTIONS-STATUS-03 [draft] Журнал смены статусов абонемента пишет триггер БД
