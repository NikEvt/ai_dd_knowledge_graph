from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

type Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]

_handlers: defaultdict[str, list[Handler]] = defaultdict(list)


def subscribe(topic: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        if fn not in _handlers[topic]:
            _handlers[topic].append(fn)
        return fn

    return register


def handlers(topic: str) -> list[Handler]:
    return list(_handlers.get(topic, ()))
