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
- R-APP-NOTIFY-01 [draft] Письма по заявке получают только клиент и представитель
- R-NOTIF-BOOKING-01 [draft] При записи на визит отправляется письмо о записи
- R-NOTIF-CANCEL-01 [draft] Любая отмена записи даёт письмо об отмене
- R-NOTIF-LOG-01 [draft] Каждое письмо сохраняется в журнале emails
- R-NOTIF-LOG-02 [draft] Статус письма — только sent или no_template
- R-NOTIF-MISSING-01 [draft] Без шаблона письмо фиксируется со статусом no_template
- R-NOTIF-RECIPIENTS-01 [draft] Письма получают только клиент и представитель
- R-NOTIF-RENDER-01 [draft] Текст письма — шаблон с подстановкой $starts_at
- R-NOTIF-RESET-01 [verified] Архивирование, дубль и смена площадки отправляют письмо об отмене
- R-NOTIF-TEMPLATE-01 [draft] Шаблон выбирается по площадке, группе вида заявки и типу письма
- R-NOTIF-TYPES-01 [draft] Существует только два типа писем — booking и cancel
