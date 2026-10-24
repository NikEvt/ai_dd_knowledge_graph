<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# notifications.templates
Миграция: [`migrations/versions/0001_initial.py:305`](../../migrations/versions/0001_initial.py#L305)

## Поля
- id: integer NOT NULL PK
- venue_id: integer NOT NULL
- kind_group: text NOT NULL
- type: text NOT NULL
- body: text NOT NULL

## Связи (FK)
- notifications.emails.template_id → сюда

## Ограничения и триггеры
- templates_kind_group_check (check на notifications.templates): CHECK ((kind_group = ANY (ARRAY['paid'::text, 'social'::text]))) (migrations/versions/0001_initial.py:308)
- templates_type_check (check на notifications.templates): CHECK ((type = ANY (ARRAY['booking'::text, 'cancel'::text]))) (migrations/versions/0001_initial.py:309)
- templates_venue_id_kind_group_type_key (unique на notifications.templates): UNIQUE (venue_id, kind_group, type) (migrations/versions/0001_initial.py:311)

## ORM
- services/notifications/models.py::Template:12 (orm_model)

## Пишут (код)
- services/notifications/service.py::set_template [body]

## Правила
- R-NOTIF-TEMPLATE-04 [draft] Один шаблон на площадку, группу и тип письма
- R-NOTIF-TEMPLATE-05 [draft] Допустимые группы шаблонов — paid и social, типы — booking и cancel
- R-NOTIF-TEMPLATE-06 [draft] Сохранение шаблона создаёт его или заменяет текст
- R-NOTIF-TEMPLATE-07 [draft] Настройка шаблонов не ограничена ролью администратора
- R-NOTIF-TYPES-01 [draft] Существует только два типа писем — booking и cancel
