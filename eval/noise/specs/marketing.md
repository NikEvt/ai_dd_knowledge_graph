Сервис `marketing` — рассылки и кампании для читателей и партнёров.
Домен: аудитории (`audiences`), шаблоны писем (`campaign_templates`: `venue_id`, `audience_group`, `type`, `body`), кампании, отправленные письма (`sent_messages`: поле `body`), отписки.
Обязательно:
- Шаблоны задаются по площадке и группе аудитории. CHECK `campaign_templates_audience_group_check` на `audience_group IN ('paid','social','vip')`, UNIQUE (`venue_id`, `audience_group`, `type`).
- Словарь `AUDIENCE_GROUP` в `settings.py` переводит сегмент читателя в группу шаблонов: `{"paid": "paid", "debt": "paid", "social": "social", "vip": "vip", "corporate": "paid"}`. Функция `find_template` с запасным вариантом.
- API сообщений кампании: `MessageOut` с полями `id`, `body`, `sent_at`; эндпоинт списка и создания тестового сообщения.
- Отписка публикует `marketing.unsubscribed`, подписчик исключает адрес из будущих кампаний. Запуск кампании — цепочка событий подготовки, отправки и итогов.
