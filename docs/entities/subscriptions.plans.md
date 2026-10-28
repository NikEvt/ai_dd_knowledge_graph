<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# subscriptions.plans
Миграция: `subscriptions.plans`

## Поля
- id: integer NOT NULL PK
- code: character varying NOT NULL
- name: character varying NOT NULL
- kind: character varying NOT NULL
- monthly_fee: numeric NOT NULL
- max_books: integer NOT NULL
- archived: boolean NOT NULL

## Связи (FK)
- subscriptions.subscriptions.plan_id → сюда

## Ограничения и триггеры
- ck_plans_fee (check на subscriptions.plans): CHECK ((monthly_fee > (0)::numeric))
- ck_plans_kind (check на subscriptions.plans): CHECK (((kind)::text = ANY ((ARRAY['regular'::character varying, 'social'::character varying, 'corporate'::ch…
- ck_plans_max_books (check на subscriptions.plans): CHECK (((max_books >= 1) AND (max_books <= 50)))
- uq_plans_code (unique на subscriptions.plans): UNIQUE (code)

## ORM
- services/subscriptions/models.py::Plan:12 (orm_model)

## Пишут (код)
- services/subscriptions/service.py::archive_plan [archived]
- services/subscriptions/service.py::create_plan

## Правила
- R-SUBSCRIPTIONS-PLAN-01 Тариф создаётся только известного вида, с положительной ценой и уникальным кодом (⚠ без тестов)
- R-SUBSCRIPTIONS-PLAN-02 Архивный тариф не продаётся и не показывается, но действующие абонементы на нём продлеваются (подкреплено кодом и тестами)
