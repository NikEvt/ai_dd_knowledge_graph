# Сегмент читателя -> группа шаблонов писем.
AUDIENCE_GROUP = {
    "paid": "paid",
    "debt": "paid",
    "social": "social",
    "vip": "vip",
    "corporate": "paid",
}
# Группа, шаблон которой берётся, если для группы читателя на площадке шаблона нет.
FALLBACK_GROUP = "paid"

CAMPAIGN_TYPES = ("newsletter", "event", "promo")

# Сколько адресов может быть в одной аудитории.
MAX_AUDIENCE_SIZE = 5_000
# Длина текста шаблона.
MAX_TEMPLATE_LENGTH = 10_000
# Тестовых писем на одну кампанию.
MAX_TEST_MESSAGES = 5
# Тестовые письма удаляются через столько дней после отправки.
TEST_MESSAGE_TTL_DAYS = 14
# Не чаще одной кампании в столько дней на аудиторию.
MIN_DAYS_BETWEEN_CAMPAIGNS = 3
# Насколько вперёд можно запланировать кампанию.
MAX_SCHEDULE_AHEAD_DAYS = 90
# После стольких возвратов адрес отписывается от всех рассылок.
BOUNCE_LIMIT = 3
