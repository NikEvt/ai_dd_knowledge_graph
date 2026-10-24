from decimal import Decimal

# Доля счёта, после оплаты которой бронь считается предоплаченной.
PREPAY_SHARE = Decimal("0.5")
# Бронь без предоплаты отменяется через столько дней после создания.
UNPAID_CANCEL_DAYS = 30
# Бронировать зал можно не раньше чем за столько дней до мероприятия...
MIN_LEAD_DAYS = 2
# ...и не дальше чем на столько дней вперёд.
BOOKING_HORIZON_DAYS = 365
# Длительность аренды, часы.
MIN_DURATION_HOURS = 2
MAX_DURATION_HOURS = 12
# Время на уборку зала между мероприятиями.
CLEANUP_MINUTES = 60

# Группа шаблонов писем по виду мероприятия.
TEMPLATE_GROUP = {
    "wedding": "private",
    "birthday": "private",
    "party": "private",
    "corporate": "corporate",
    "conference": "corporate",
}
EVENT_KINDS = tuple(TEMPLATE_GROUP)

# Статусы, в которых бронь занимает зал.
ACTIVE_STATUSES = ("draft", "prepaid", "confirmed")
