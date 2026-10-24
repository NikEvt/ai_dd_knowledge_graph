Сервис `halls` — аренда залов площадок под частные мероприятия.
Домен: залы (`halls`) принадлежат площадкам (`venue_id` — просто число, без FK на ядро). Бронирования залов (`hall_bookings`): клиент (`client_ref`), дата и время, статус (`draft`, `prepaid`, `confirmed`, `held`, `cancelled`). Счета на аренду и платежи в своих таблицах.
Обязательно:
- Смена площадки бронирования (`change_venue`) разрешена до подтверждения. После `confirmed` её запрещает триггер `trg_hall_bookings_venue_lock` (функция `halls.forbid_venue_change`).
- Предоплата 50%: бронь переходит в `prepaid`, когда платежи покрывают половину счёта (`PREPAY_SHARE`). Полная оплата делает бронь `confirmed`. Функция `is_fully_paid`.
- Отмена брони публикует `halls.booking_cancelled`, подписчик рассылает письмо об отмене по шаблонам сервиса. Таблица `hall_templates` с колонкой `kind_group` и CHECK (`corporate`, `private`). Словарь `TEMPLATE_GROUP` в `settings.py`.
- Фоновая задача: неоплаченная бронь отменяется через `UNPAID_CANCEL_DAYS = 30` дней после создания.
