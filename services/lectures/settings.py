from datetime import timedelta

# Мероприятие можно объявить не позднее чем за столько до начала.
MIN_LEAD_TIME = timedelta(hours=24)
# Регистрация и продвижение из листа ожидания закрываются за столько до начала.
REGISTRATION_CLOSES_BEFORE = timedelta(hours=1)
# Сколько действующих регистраций на будущие мероприятия может быть у одного слушателя.
MAX_ACTIVE_REGISTRATIONS = 3
# Длина листа ожидания одного мероприятия.
WAITLIST_MAX_SIZE = 20
# Напоминание слушателям рассылается за столько до начала.
REMINDER_AHEAD = timedelta(hours=24)
# Мероприятие считается прошедшим через столько после начала.
FINISH_AFTER = timedelta(hours=3)
# Отметка слушателей на входе открывается за столько до начала.
CHECK_IN_OPENS_BEFORE = timedelta(minutes=30)
# Сколько уведомлений отправляется за один проход рассылки.
NOTIFICATION_BATCH = 100
