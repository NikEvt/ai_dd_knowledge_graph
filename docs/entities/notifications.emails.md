<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# notifications.emails
Миграция: [`migrations/versions/0001_initial.py:314`](../../migrations/versions/0001_initial.py#L314)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- recipients: jsonb NOT NULL
- type: text NOT NULL
- template_id: integer
- body: text NOT NULL
- status: text NOT NULL
- created_at: timestamp with time zone NOT NULL

## Связи (FK)
- template_id → notifications.templates

## Ограничения и триггеры
- emails_status_check (check на notifications.emails): CHECK ((status = ANY (ARRAY['sent'::text, 'no_template'::text]))) (migrations/versions/0001_initial.py:321)
- emails_type_check (check на notifications.emails): CHECK ((type = ANY (ARRAY['booking'::text, 'cancel'::text]))) (migrations/versions/0001_initial.py:318)

## ORM
- services/notifications/models.py::Email:23 (orm_model)

## Пишут (код)
- services/notifications/service.py::send

## Правила
- R-APP-NOTIFY-01 Письма по заявке получают только клиент и представитель (подкреплено кодом и тестами)
- R-NOTIF-BOOKING-01 При записи на визит отправляется письмо о записи (подкреплено кодом и тестами)
- R-NOTIF-CANCEL-01 Любая отмена записи даёт письмо об отмене (подкреплено кодом и тестами)
- R-NOTIF-LOG-01 Каждое письмо сохраняется в журнале emails (подкреплено кодом и тестами)
- R-NOTIF-LOG-02 Статус письма — только sent или no_template (⚠ без тестов)
- R-NOTIF-MISSING-01 Без шаблона письмо фиксируется со статусом no_template (⚠ без тестов)
- R-NOTIF-RECIPIENTS-01 Письма получают только клиент и представитель (подкреплено кодом и тестами)
- R-NOTIF-RENDER-01 Текст письма — шаблон с подстановкой $starts_at (подкреплено кодом и тестами)
- R-NOTIF-RESET-01 Архивирование, дубль и смена площадки отправляют письмо об отмене (⚠ расхождение с требованием или открытый вопрос)
- R-NOTIF-TEMPLATE-01 Шаблон выбирается по площадке, группе вида заявки и типу письма (подкреплено кодом и тестами)
- R-NOTIF-TYPES-01 Существует только два типа писем — booking и cancel (⚠ расхождение с требованием или открытый вопрос)
