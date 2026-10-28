<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.audiences
Миграция: `marketing.audiences`

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- name: text NOT NULL
- created_by: integer NOT NULL
- created_at: timestamp with time zone NOT NULL
- archived: boolean NOT NULL
- last_campaign_at: timestamp with time zone

## Связи (FK)
- marketing.audience_members.audience_id → сюда
- marketing.campaigns.audience_id → сюда

## Ограничения и триггеры
- audiences_name_check (check на marketing.audiences): CHECK ((length(TRIM(BOTH FROM name)) > 0))
- audiences_venue_name_uq (unique на marketing.audiences): UNIQUE (venue_id, name)

## ORM
- services/marketing/models.py::Audience:23 (orm_model)

## Пишут (код)
- services/marketing/service.py::archive_audience [archived]
- services/marketing/service.py::create_audience
- services/marketing/service.py::summarize_campaign [last_campaign_at]

## Правила
- R-MARKETING-AUDIENCE-01 Название аудитории непустое и уникально в пределах площадки (подкреплено кодом и тестами)
- R-MARKETING-AUDIENCE-02 Нельзя архивировать аудиторию с запланированной или идущей кампанией (подкреплено кодом и тестами)
- R-MARKETING-AUDIENCE-03 Архивная аудитория закрыта для новых адресов, кампаний и запусков (подкреплено кодом и тестами)
- R-MARKETING-LAUNCH-03 Пауза между кампаниями одной аудитории отсчитывается от завершения предыдущей (подкреплено кодом и тестами)
- R-MARKETING-REPORT-01 Итоги кампании: sent_count — отправленные вместе с возвратами, skipped_count — пропущенные (подкреплено кодом и тестами)
- R-MARKETING-TEST-02 Тестовые письма не входят в статистику, возвраты и уникальность адресатов (⚠ без тестов)
