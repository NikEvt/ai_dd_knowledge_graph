<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# applications.clients
Миграция: [`migrations/versions/0001_initial.py:70`](../../migrations/versions/0001_initial.py#L70)

## Поля
- id: integer NOT NULL PK
- full_name: text
- passport: text
- birth_date: date
- email: text NOT NULL
- updated_at: timestamp with time zone

## Связи (FK)
- applications.applications.client_id → сюда

## ORM
- services/applications/models.py::Client:70 (orm_model)

## Пишут (код)
- services/applications/listeners.py::_domain_events [updated_at]
- services/applications/service.py::create_client

## Правила
- R-APP-CHAT-01 Каждая смена этапа заявки пишется в чат (слушатель ORM) (подкреплено кодом и тестами)
- R-APP-CLIENT-02 Изменение ФИО, паспорта или даты рождения клиента публикует client.updated (слушатель ORM) (⚠ без тестов)
- R-CHAT-EVENTS-02 Каждая смена этапа заявки появляется в чате (⚠ расхождение с требованием или открытый вопрос)
- R-SCHEMA-CLIENT-01 Клиент заводится один раз оператором, данные общие для всех заявок (⚠ расхождение с требованием или открытый вопрос)
