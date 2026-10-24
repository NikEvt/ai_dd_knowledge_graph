class DomainError(Exception):
    """Бизнес-правило запрещает действие."""


class AccessDenied(DomainError):
    """Действие не разрешено этому сотруднику."""


class NotFound(DomainError):
    """Объект не найден."""
