"""Исполнение процесса заявки по описанию bpm/application_process.yaml."""

from collections.abc import Awaitable, Callable
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from libs.errors import DomainError

PROCESS_FILE = Path(__file__).resolve().parents[2] / "bpm" / "application_process.yaml"

type Guard = Callable[[AsyncSession, Any], Awaitable[bool]]

GUARDS: dict[str, Guard] = {}


class TransitionError(DomainError):
    pass


def guard(name: str) -> Callable[[Guard], Guard]:
    def register(fn: Guard) -> Guard:
        GUARDS[name] = fn
        return fn

    return register


@cache
def process() -> dict[str, Any]:
    return yaml.safe_load(PROCESS_FILE.read_text(encoding="utf-8"))


def _as_list(value: str | list[str]) -> list[str]:
    return value if isinstance(value, list) else [value]


def find_transition(kind: str, src: str, dst: str, actor: str) -> dict[str, Any] | None:
    for t in process()["transitions"]:
        if src not in _as_list(t["from"]) or t["to"] != dst:
            continue
        if actor not in _as_list(t["actor"]):
            continue
        if "kinds" in t and kind not in t["kinds"]:
            continue
        return t
    return None


async def transition(session: AsyncSession, app: Any, dst: str, actor: str) -> None:
    rule = find_transition(app.kind, app.stage, dst, actor)
    if rule is None:
        raise TransitionError(f"{app.kind}: переход {app.stage} -> {dst} для {actor} не разрешён")
    if name := rule.get("guard"):
        check = GUARDS.get(name)
        if check is None:
            raise TransitionError(f"условие {name} не зарегистрировано")
        if not await check(session, app):
            raise TransitionError(f"{app.stage} -> {dst}: не выполнено условие {name}")
    app.stage = dst
