<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# chat.messages
Миграция: [`migrations/versions/0001_initial.py:327`](../../migrations/versions/0001_initial.py#L327)

## Поля
- id: integer NOT NULL PK
- application_id: integer NOT NULL
- author_id: integer
- body: text NOT NULL
- is_event: boolean NOT NULL
- created_at: timestamp with time zone NOT NULL

## Ограничения и триггеры
- messages_check (check на chat.messages): CHECK ((is_event OR (author_id IS NOT NULL))) (migrations/versions/0001_initial.py:334)
- trg_chat_messages_immutable: BEFORE DELETE OR UPDATE ON chat.messages FOR EACH ROW EXECUTE FUNCTION chat.forbid_message_changes() (migrations/versions/0001_initial.py:342)
  - forbid_message_changes(): 'chat messages cannot be edited or deleted'

## ORM
- services/chat/models.py::Message:8 (orm_model)

## Пишут (код)
- services/chat/service.py::log_event
- services/chat/service.py::post_message

## Правила
- R-CHAT-DB-01 Сообщение без автора допустимо только для события (CHECK в БД) (проверено человеком)
- R-CHAT-DB-02 Сообщения чата нельзя редактировать и удалять (триггер БД) (⚠ без тестов)
- R-CHAT-EVENTS-01 11 топиков из EVENT_TEXT автоматически пишутся в чат системными сообщениями (проверено человеком)
- R-CHAT-EVENTS-05 События пишутся в чат и после закрытия заявки (⚠ без тестов)
- R-CHAT-POST-01 После закрытия заявки писать в чат нельзя (проверено человеком)
- R-CHAT-POST-02 Писать в чат могут только закреплённые за заявкой сотрудники (подкреплено кодом и тестами)
- R-CHAT-POST-03 Сообщение сотрудника записывается как обычное, с автором и временем (⚠ расхождение с требованием или открытый вопрос)
- R-CHAT-READ-04 Администратор чат только читает (подкреплено кодом и тестами)
