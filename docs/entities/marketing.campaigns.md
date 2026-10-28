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
- R-MARKETING-AUDIENCE-03 Архивная аудитория закрыта для новых адресов, кампаний и запусков (подкреплено кодом и тестами)
- R-MARKETING-CAMPAIGN-01 Кампания создаётся с известным типом и темой, в статусе draft или scheduled (подкреплено кодом и тестами)
- R-MARKETING-CAMPAIGN-02 Кампанию планируют только в будущее и не дальше MAX_SCHEDULE_AHEAD_DAYS (подкреплено кодом и тестами)
- R-MARKETING-CAMPAIGN-03 Перенести или отменить можно только не запущенную кампанию (подкреплено кодом и тестами)
- R-MARKETING-CAMPAIGN-04 Отправленная или отменённая кампания больше не меняет статус (подкреплено кодом и тестами)
- R-MARKETING-DELIVERY-01 Все письма из очереди отмечаются отправленными одним обновлением (подкреплено кодом и тестами)
- R-MARKETING-LAUNCH-01 Условия запуска кампании и публикация marketing.campaign_launched (подкреплено кодом и тестами)
- R-MARKETING-LAUNCH-02 По аудитории одновременно идёт не больше одной кампании (подкреплено кодом и тестами)
- R-MARKETING-LAUNCH-03 Пауза между кампаниями одной аудитории отсчитывается от завершения предыдущей (подкреплено кодом и тестами)
- R-MARKETING-LAUNCH-04 Запланированную кампанию можно запустить вручную раньше срока (⚠ без тестов)
- R-MARKETING-LAUNCH-05 Фоновая задача запускает наступившие запланированные кампании, неудачные ждут следующего прогона (подкреплено кодом и тестами)
- R-MARKETING-PREPARE-01 Запуск кампании по цепочке событий готовит, отправляет письма и подводит итог (подкреплено кодом и тестами)
- R-MARKETING-PREPARE-02 Письма при подготовке: отписавшиеся не входят, отписанные и без шаблона пропускаются (подкреплено кодом и тестами)
- R-MARKETING-REPORT-01 Итоги кампании: sent_count — отправленные вместе с возвратами, skipped_count — пропущенные (подкреплено кодом и тестами)
- R-MARKETING-TEMPLATE-05 Текст письма подставляет $full_name, $email и $subject (подкреплено кодом и тестами)
- R-MARKETING-TEST-02 Тестовые письма не входят в статистику, возвраты и уникальность адресатов (⚠ без тестов)
- R-MARKETING-UNSUBSCRIBE-03 Отписка от площадки не влияет на рассылки других площадок (подкреплено кодом и тестами)
