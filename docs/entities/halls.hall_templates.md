<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# halls.hall_templates
Миграция: `halls.hall_templates`

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- kind_group: text NOT NULL
- type: text NOT NULL
- body: text NOT NULL

## Связи (FK)
- halls.hall_emails.template_id → сюда

## Ограничения и триггеры
- hall_templates_kind_group_check (check на halls.hall_templates): CHECK ((kind_group = ANY (ARRAY['corporate'::text, 'private'::text])))
- hall_templates_type_check (check на halls.hall_templates): CHECK ((type = ANY (ARRAY['invoice'::text, 'prepaid'::text, 'confirmed'::text, 'cancel'::text])))
- hall_templates_venue_id_kind_group_type_key (unique на halls.hall_templates): UNIQUE (venue_id, kind_group, type)

## ORM
- services/halls/models.py::HallTemplate:91 (orm_model)

## Пишут (код)
- services/halls/service.py::set_template [body]

## Правила
- R-HALLS-ACCESS-01 [draft] Залами, бронями и шаблонами управляет только менеджер, закреплённый за площадкой
- R-HALLS-EMAIL-02 [draft] Шаблон письма — один на площадку, группу и тип
