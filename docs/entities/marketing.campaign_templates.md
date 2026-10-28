<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.campaign_templates
Миграция: `marketing.campaign_templates`

## Поля
- id: integer NOT NULL PK
- venue_id: integer
- audience_group: text NOT NULL
- type: text NOT NULL
- body: text NOT NULL
- updated_at: timestamp with time zone NOT NULL

## Связи (FK)
- marketing.sent_messages.template_id → сюда

## Ограничения и триггеры
- campaign_templates_audience_group_check (check на marketing.campaign_templates): CHECK ((audience_group = ANY (ARRAY['paid'::text, 'social'::text, 'vip'::text])))
- campaign_templates_body_check (check на marketing.campaign_templates): CHECK ((length(body) > 0))
- campaign_templates_default_uq (partial_unique_index на marketing.campaign_templates): CREATE UNIQUE INDEX campaign_templates_default_uq ON marketing.campaign_templates USING btree (audience_group…
- campaign_templates_venue_group_type_uq (unique на marketing.campaign_templates): UNIQUE (venue_id, audience_group, type)

## ORM
- services/marketing/models.py::CampaignTemplate:49 (orm_model)

## Пишут (код)
- services/marketing/service.py::set_template [body, updated_at]

## Правила
- R-MARKETING-ACCESS-02 Шаблоны сети задаёт только менеджер сети (подкреплено кодом и тестами)
- R-MARKETING-TEMPLATE-03 Проверки шаблона: группа, тип кампании, непустой текст, длина (подкреплено кодом и тестами)
- R-MARKETING-TEMPLATE-04 Один шаблон на площадку (или сеть), группу и тип; повторная запись обновляет его (подкреплено кодом и тестами)
