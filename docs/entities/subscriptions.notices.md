<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.notices
Миграция: `subscriptions.notices`

## Поля
- id: bigint NOT NULL PK
- subscription_id: integer NOT NULL
- kind: character varying NOT NULL
- body: text NOT NULL
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- subscription_id → subscriptions.subscriptions

## ORM
- services/subscriptions/models.py::Notice:101 (orm_model)

## Пишут (код)
- services/subscriptions/service.py::add_notice

## Правила
- R-SUBSCRIPTIONS-NOTICE-01 [draft] События абонемента превращаются в уведомления держателю
