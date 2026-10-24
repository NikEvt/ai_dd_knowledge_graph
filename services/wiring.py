"""Подключение обработчиков событий, слушателей ORM и условий процесса всех сервисов."""

import importlib
from pathlib import Path

MODULES = (
    "services.applications.listeners",
    "services.applications.consumers",
    "services.applications.guards",
    "services.billing.consumers",
    "services.billing.guards",
    "services.scheduling.consumers",
    "services.notifications.consumers",
    "services.chat.consumers",
)


CORE = ("applications", "billing", "scheduling", "notifications", "chat")


def load() -> None:
    for name in MODULES:
        importlib.import_module(name)
    # Платформенные сервисы: подписчики и слушатели подключаются автоматически
    for path in sorted(Path(__file__).parent.glob("*/consumers.py")):
        if path.parent.name not in CORE:
            importlib.import_module(f"services.{path.parent.name}.consumers")
