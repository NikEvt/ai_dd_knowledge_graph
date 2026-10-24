<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.campaigns
Миграция: `marketing.campaigns`

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- audience_id: integer NOT NULL
- type: text NOT NULL
- subject: text NOT NULL
- status: text NOT NULL
- created_by: integer NOT NULL
- created_at: timestamp with time zone NOT NULL
- scheduled_at: timestamp with time zone
- launched_at: timestamp with time zone
- finished_at: timestamp with time zone
- recipients_count: integer NOT NULL
- sent_count: integer NOT NULL
- skipped_count: integer NOT NULL

## Связи (FK)
- audience_id → marketing.audiences
- marketing.sent_messages.campaign_id → сюда

## Ограничения и триггеры
- campaigns_check (check на marketing.campaigns): CHECK (((status <> 'scheduled'::text) OR (scheduled_at IS NOT NULL)))
- campaigns_recipients_count_check (check на marketing.campaigns): CHECK ((recipients_count >= 0))
- campaigns_sent_count_check (check на marketing.campaigns): CHECK ((sent_count >= 0))
- campaigns_skipped_count_check (check на marketing.campaigns): CHECK ((skipped_count >= 0))
- campaigns_status_check (check на marketing.campaigns): CHECK ((status = ANY (ARRAY['draft'::text, 'scheduled'::text, 'preparing'::text, 'sending'::text, 'sent'::tex…
- marketing.campaigns_guard_status(): 'кампания % уже в статусе %'
- campaigns_scheduled_idx (index на marketing.campaigns): CREATE INDEX campaigns_scheduled_idx ON marketing.campaigns USING btree (scheduled_at) WHERE (status = 'sched…
- campaigns_audience_active_uq (partial_unique_index на marketing.campaigns): CREATE UNIQUE INDEX campaigns_audience_active_uq ON marketing.campaigns USING btree (audience_id) WHERE (stat…

## ORM
- services/marketing/models.py::Campaign:61 (orm_model)

## Пишут (код)
- services/marketing/service.py::cancel_campaign [status]
- services/marketing/service.py::create_campaign
- services/marketing/service.py::deliver_messages [finished_at, status]
- services/marketing/service.py::prepare_messages [recipients_count, status]
- services/marketing/service.py::schedule_campaign [scheduled_at, status]
- services/marketing/service.py::start [launched_at, status]
- services/marketing/service.py::summarize_campaign [sent_count, skipped_count]

## Правила
- R-MARKETING-AUDIENCE-03 [draft] Архивная аудитория закрыта для новых адресов, кампаний и запусков
- R-MARKETING-CAMPAIGN-01 [draft] Кампания создаётся с известным типом и темой, в статусе draft или scheduled
- R-MARKETING-CAMPAIGN-02 [draft] Кампанию планируют только в будущее и не дальше MAX_SCHEDULE_AHEAD_DAYS
- R-MARKETING-CAMPAIGN-03 [draft] Перенести или отменить можно только не запущенную кампанию
- R-MARKETING-CAMPAIGN-04 [draft] Отправленная или отменённая кампания больше не меняет статус
- R-MARKETING-DELIVERY-01 [draft] Все письма из очереди отмечаются отправленными одним обновлением
- R-MARKETING-LAUNCH-01 [draft] Условия запуска кампании и публикация marketing.campaign_launched
- R-MARKETING-LAUNCH-02 [draft] По аудитории одновременно идёт не больше одной кампании
- R-MARKETING-LAUNCH-03 [draft] Пауза между кампаниями одной аудитории отсчитывается от завершения предыдущей
- R-MARKETING-LAUNCH-04 [draft] Запланированную кампанию можно запустить вручную раньше срока
- R-MARKETING-LAUNCH-05 [draft] Фоновая задача запускает наступившие запланированные кампании, неудачные ждут следующего прогона
- R-MARKETING-PREPARE-01 [draft] Запуск кампании по цепочке событий готовит, отправляет письма и подводит итог
- R-MARKETING-PREPARE-02 [draft] Письма при подготовке: отписавшиеся не входят, отписанные и без шаблона пропускаются
- R-MARKETING-REPORT-01 [draft] Итоги кампании: sent_count — отправленные вместе с возвратами, skipped_count — пропущенные
- R-MARKETING-TEMPLATE-05 [draft] Текст письма подставляет $full_name, $email и $subject
- R-MARKETING-TEST-02 [draft] Тестовые письма не входят в статистику, возвраты и уникальность адресатов
- R-MARKETING-UNSUBSCRIBE-03 [draft] Отписка от площадки не влияет на рассылки других площадок
