<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.managers
Миграция: `marketing.managers`

## Поля
- id: integer NOT NULL PK
- manager_id: integer NOT NULL
- venue_id: integer
- full_name: text NOT NULL

## Ограничения и триггеры
- managers_network_uq (partial_unique_index на marketing.managers): CREATE UNIQUE INDEX managers_network_uq ON marketing.managers USING btree (manager_id) WHERE (venue_id IS NUL…
- managers_venue_uq (partial_unique_index на marketing.managers): CREATE UNIQUE INDEX managers_venue_uq ON marketing.managers USING btree (manager_id, venue_id) WHERE (venue_i…

## ORM
- services/marketing/models.py::Manager:11 (orm_model)

## Пишут (код)
- services/marketing/service.py::add_manager

## Правила
- R-MARKETING-ACCESS-04 Менеджер закрепляется за площадкой или сетью не более одного раза (⚠ без тестов)
