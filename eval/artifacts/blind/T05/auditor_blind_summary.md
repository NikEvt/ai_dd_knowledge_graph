**Что изменить.** СНИЛС нужно вписать в три разных кортежа с полями клиента. Они дублируют друг друга, но списки в них разные:
- `REQUIRED_CLIENT_FIELDS` (review.py:3) — проверка при approve;
- `CLIENT_EDITABLE_FIELDS` (service.py:28) — что разрешено обновлять проверяющему;
- `TRACKED_FIELDS` (listeners.py:9) — что запускает `client.updated`.

Кроме этого нужны поле `Client.snils` в модели и новая миграция 0002 с колонкой `text NULL` в `applications.clients`.

**Неочевидные связи.**
- «Последствия как при смене паспорта» не видны по импортам. ORM-слушатель `before_flush`, подключённый через `services/wiring.py`, публикует `client.updated`. На событие подписан `on_client_updated`, который по BPM-переходам `awaiting_invoice|awaiting_payment->on_review` возвращает другие заявки клиента на проверку. Это порождает `application.stage_changed` и запись в чате.
- Если забыть `TRACKED_FIELDS`, тесты пройдут, но последствий не будет. Вдобавок `source_application_id` останется в `session.info`.

**Тесты.**
- В seed `tests/factories.py` клиентам A и B нужно добавить snils, иначе упадут почти все тесты через `pass_review`.
- В `test_incomplete_client_goes_to_rework` нужно передавать snils.
- Нужны новые тесты: отказ в approve без СНИЛС и возврат на проверку другой заявки клиента при смене СНИЛС.

**Побочный эффект в работе.** Существующие клиенты без СНИЛС не пройдут проверку, а через `REVIEW_ARCHIVE_DAYS` их заявки уйдут в архив задачей `archive_stale`.

**Чего в проекте нет.** HTTP-эндпоинта для данных клиента нет, триггеров БД на `clients` нет, других подписчиков `client.updated` нет. Всё перепроверено поиском.
