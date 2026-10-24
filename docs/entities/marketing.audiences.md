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
- R-MARKETING-AUDIENCE-01 [draft] Название аудитории непустое и уникально в пределах площадки
- R-MARKETING-AUDIENCE-02 [draft] Нельзя архивировать аудиторию с запланированной или идущей кампанией
- R-MARKETING-AUDIENCE-03 [draft] Архивная аудитория закрыта для новых адресов, кампаний и запусков
- R-MARKETING-LAUNCH-03 [draft] Пауза между кампаниями одной аудитории отсчитывается от завершения предыдущей
- R-MARKETING-REPORT-01 [draft] Итоги кампании: sent_count — отправленные вместе с возвратами, skipped_count — пропущенные
- R-MARKETING-TEST-02 [draft] Тестовые письма не входят в статистику, возвраты и уникальность адресатов
