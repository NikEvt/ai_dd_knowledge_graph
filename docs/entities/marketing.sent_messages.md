<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# marketing.sent_messages
Миграция: `marketing.sent_messages`

## Поля
- id: integer NOT NULL PK
- campaign_id: integer NOT NULL
- template_id: integer
- email: text NOT NULL
- segment: text NOT NULL
- body: text NOT NULL
- status: text NOT NULL
- skip_reason: text
- is_test: boolean NOT NULL
- created_at: timestamp with time zone NOT NULL
- sent_at: timestamp with time zone

## Связи (FK)
- template_id → marketing.campaign_templates
- campaign_id → marketing.campaigns

## Ограничения и триггеры
- sent_messages_check (check на marketing.sent_messages): CHECK (((status <> ALL (ARRAY['sent'::text, 'bounced'::text])) OR (sent_at IS NOT NULL)))
- sent_messages_status_check (check на marketing.sent_messages): CHECK ((status = ANY (ARRAY['queued'::text, 'sent'::text, 'skipped'::text, 'bounced'::text])))
- marketing.sent_messages_freeze_body(): 'письмо % уже отправлено, текст менять нельзя'
- sent_messages_bounced_idx (index на marketing.sent_messages): CREATE INDEX sent_messages_bounced_idx ON marketing.sent_messages USING btree (email) WHERE (status = 'bounce…
- sent_messages_campaign_email_uq (partial_unique_index на marketing.sent_messages): CREATE UNIQUE INDEX sent_messages_campaign_email_uq ON marketing.sent_messages USING btree (campaign_id, emai…

## ORM
- services/marketing/models.py::SentMessage:81 (orm_model)

## Пишут (код)
- services/marketing/service.py::deliver_messages
- services/marketing/service.py::exclude_address
- services/marketing/service.py::prepare_messages [body]
- services/marketing/service.py::purge_test_messages
- services/marketing/service.py::register_bounce [status]
- services/marketing/service.py::send_test_message

## Правила
- R-MARKETING-BOUNCE-01 Возврат регистрируется только по отправленному письму кампании (подкреплено кодом и тестами)
- R-MARKETING-DELIVERY-01 Все письма из очереди отмечаются отправленными одним обновлением (подкреплено кодом и тестами)
- R-MARKETING-MESSAGE-01 Текст отправленного письма неизменен (подкреплено кодом и тестами)
- R-MARKETING-PREPARE-01 Запуск кампании по цепочке событий готовит, отправляет письма и подводит итог (подкреплено кодом и тестами)
- R-MARKETING-PREPARE-02 Письма при подготовке: отписавшиеся не входят, отписанные и без шаблона пропускаются (подкреплено кодом и тестами)
- R-MARKETING-TEMPLATE-05 Текст письма подставляет $full_name, $email и $subject (подкреплено кодом и тестами)
- R-MARKETING-TEST-01 Тестовые письма — только до запуска, не больше MAX_TEST_MESSAGES и только при наличии шаблона (подкреплено кодом и тестами)
- R-MARKETING-TEST-02 Тестовые письма не входят в статистику, возвраты и уникальность адресатов (⚠ без тестов)
- R-MARKETING-TEST-03 Тестовые письма удаляются через TEST_MESSAGE_TTL_DAYS после отправки (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-02 Отписка исключает адрес из аудиторий и снимает ещё не ушедшие письма (подкреплено кодом и тестами)
- R-MARKETING-UNSUBSCRIBE-03 Отписка от площадки не влияет на рассылки других площадок (подкреплено кодом и тестами)
