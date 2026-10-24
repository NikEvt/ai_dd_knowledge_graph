"""Константы сервиса сотрудников."""

# Без этих полей карточки сотрудника нельзя допустить к сменам и оформить допуск.
REQUIRED_EMPLOYEE_FIELDS = ("full_name", "passport", "snils", "birth_date")

ROLES = ("librarian", "cashier", "guard", "manager", "hr")
# Кто ведёт кадровые операции: приём, перевод, увольнение, допуски.
HR_ROLES = ("hr",)
# Кого можно назначить ответственным за площадку.
RESPONSIBLE_ROLES = ("manager",)

# Максимум сотрудников на смене для новой площадки.
MAX_SHIFT_STAFF = 6
# Жёсткий потолок для любой площадки (совпадает с CHECK в staff.sql).
SHIFT_STAFF_CEILING = 20

MIN_EMPLOYEE_AGE = 18
MAX_SHIFT_HOURS = 12
# Минимальный отдых между сменами одного сотрудника.
MIN_REST_HOURS = 8
# Смены планируются не дальше чем на столько дней вперёд.
PLANNING_HORIZON_DAYS = 60

# Инструктаж годится для оформления допуска, если проведён не раньше чем столько дней назад.
BRIEFING_VALID_DAYS = 30
