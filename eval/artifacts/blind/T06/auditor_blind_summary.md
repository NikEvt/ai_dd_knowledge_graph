**Что поменять.** В `TEMPLATE_GROUP` для вида `"debt"` указать группу `"debt"` (`services/notifications/config.py:4`). В `find_template` добавить запасной вариант: ищем шаблон группы debt, а если на площадке его нет — шаблон paid той же площадки и того же типа. Затем новой миграцией `0002` расширить CHECK на `notifications.templates.kind_group` до `('paid','debt','social')` (сейчас он в `migrations/versions/0001_initial.py:308`). И добавить тесты в `tests/test_notifications.py`: debt берёт свой шаблон, без него берёт paid (на TVR есть только paid), отдельно cancel и настройка через `set_template`.

**Что легко пропустить:**
- **CHECK в БД.** Без миграции администратор не сохранит шаблон debt: `set_template` ничего не проверяет и упадёт только при `flush`. Имя ограничения Postgres сгенерировал сам (скорее всего `templates_kind_group_check`), его нужно сверить в БД.
- **FK из писем.** На шаблоны ссылаются `notifications.emails.template_id`, поэтому `downgrade` новой миграции не может просто удалить шаблоны debt. Кроме того, CHECK на `emails.status` не допускает новых статусов: запасной шаблон должен давать обычный `sent`.
- **Отправка идёт через события.** Письма шлются не по прямым вызовам, а через `booking.created` и `booking.cancelled` из scheduling. Отмены бывают из многих мест: перенос, удаление окна, неявка, архив, дубль. Все они автоматически пойдут по группе debt.
- **Вид заявки фиксируется при создании.** Он берётся из `debt_allowed` представителя, поэтому смена условий представителя на уже созданные заявки не влияет.
- **BPM, триггеры заявок и billing задача не затрагивает.**

Файлы `chat/models.py`, `chat/app.py`, `billing/models.py`, `billing/app.py`, `scheduling/models.py`, `scheduling/app.py`, `libs/clock.py`, `libs/errors.py`, `tests/test_chat_api.py` и `tests/test_review.py` я не читал целиком, а проверил поиском по шаблонам и видам заявок: упоминаний там нет. Папок `knowledge/`, `docs/`, `AGENTS.md` и `memory-bank/` в проекте нет.
