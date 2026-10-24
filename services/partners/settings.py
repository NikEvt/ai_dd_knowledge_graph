from decimal import Decimal

# Без этих реквизитов договор с партнёром не активируется.
REQUIRED_PARTNER_FIELDS = ("inn", "kpp", "legal_name")

REQUISITE_TITLES = {"inn": "ИНН", "kpp": "КПП", "legal_name": "наименование"}

# Ставка комиссии нового договора и допустимый максимум.
DEFAULT_COMMISSION_PCT = Decimal(10)
MAX_COMMISSION_PCT = Decimal(30)

# Максимальный лимит кредита, который менеджер выставляет без согласования.
MAX_CREDIT_LIMIT = Decimal(500_000)

# Срок оплаты сделки, проведённой в кредит.
CREDIT_PAYMENT_DAYS = 14

# Срок действия договора по умолчанию.
CONTRACT_TERM_DAYS = 365

# Заявка на подключение без решения закрывается через столько дней.
ONBOARDING_REQUEST_TTL_DAYS = 30
