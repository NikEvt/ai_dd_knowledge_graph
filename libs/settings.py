import os

DB_PORT = os.environ.get("DB_PORT", "55432")
DATABASE_URL = os.environ.get("DATABASE_URL", f"postgresql+asyncpg://erp:erp@localhost:{DB_PORT}/erp")
REDIS_URL = os.environ.get("REDIS_URL", f"redis://localhost:{os.environ.get('REDIS_PORT', '56379')}/0")

# Срок пользования книгами с даты выдачи.
LOAN_PERIOD_DAYS = 30
# Заявка уходит в архив, если с начала проверки прошло столько дней, а данные не получены.
REVIEW_ARCHIVE_DAYS = 30
# Платная заявка уходит в архив, если счёт не оплачен за столько дней.
PAYMENT_ARCHIVE_DAYS = 30
# Клиент может перенести или отменить визит не позднее чем за столько дней.
CLIENT_RESCHEDULE_MIN_DAYS = 2
