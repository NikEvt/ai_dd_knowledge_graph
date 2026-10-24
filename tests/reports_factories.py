"""Данные и типовые шаги сервиса отчётности для тестов."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import update

from libs import clock, db
from libs.events import OutboxEvent
from services.reports import service
from services.reports.models import ExportSchedule, ReportRun, RunNotification
from tests.factories import T0, act, read

ANALYST, ANALYST_2, MANAGER, DIRECTOR = 701, 702, 703, 704

LOANS = "loans.issued"
FINES = "billing.fines_amount"


async def snapshot(metric: str, value: int | str, *, days_ago: int = 0, dimension: str = "") -> None:
    await act(
        service.record_snapshot,
        metric,
        Decimal(value),
        dimension=dimension,
        day=(T0 - timedelta(days=days_ago)).date(),
    )


async def series(metric: str, values: list[int], *, dimension: str = "") -> None:
    """Снимки за последние len(values) дней, последний — за день T0."""
    for days_ago, value in zip(range(len(values) - 1, -1, -1), values, strict=True):
        await snapshot(metric, value, days_ago=days_ago, dimension=dimension)


async def definition(
    code: str = "loans-weekly",
    *,
    kind: str = "metric_summary",
    params: dict[str, Any] | None = None,
    owner: int = ANALYST,
    title: str | None = None,
) -> int:
    if params is None:
        params = {"metrics": [LOANS]} if kind == "metric_summary" else {}
        if kind == "metric_trend":
            params = {"metric": LOANS}
    created = await act(
        service.create_definition,
        owner_id=owner,
        code=code,
        title=title or f"Отчёт {code}",
        kind=kind,
        params=params,
    )
    return created.id


async def run(definition_id: int, *, by: int = ANALYST, params: dict[str, Any] | None = None) -> int:
    """Запросить запуск и доставить события — отчёт строится подписчиком."""
    created = await act(service.request_run, definition_id, by, params)
    return created.id


async def run_pending(definition_id: int, *, by: int = ANALYST, params: dict[str, Any] | None = None) -> int:
    """Запуск, который воркер построения ещё не взял: остаётся в статусе requested.

    Событие reports.run_requested помечаем обработанным, чтобы последующие шаги теста его не доставили.
    """
    async with db.sessionmaker().begin() as s:
        created = await service.request_run(s, definition_id, by, params)
        await s.flush()
        await s.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.topic == "reports.run_requested",
                OutboxEvent.payload["run_id"].as_integer() == created.id,
            )
            .values(processed_at=clock.now())
        )
    return created.id


async def schedule(
    definition_id: int,
    *,
    by: int = ANALYST,
    every_hours: int = 24,
    recipients: tuple[int, ...] = (MANAGER,),
    first_run_at: datetime | None = None,
) -> int:
    created = await act(
        service.create_schedule,
        definition_id,
        by,
        every_hours=every_hours,
        recipients=list(recipients),
        first_run_at=first_run_at,
    )
    return created.id


async def job(fn, now: datetime):
    """Выполнить фоновую задачу на момент `now` и доставить события."""
    return await act(fn, now)


async def load_run(run_id: int) -> ReportRun:
    return await read(service.get_run, run_id)


async def load_schedule(schedule_id: int) -> ExportSchedule:
    async with db.sessionmaker()() as s:
        return await s.get(ExportSchedule, schedule_id)


async def inbox(recipient_id: int) -> list[RunNotification]:
    return await read(service.inbox, recipient_id)


async def sql(statement: str) -> None:
    async with db.engine().begin() as conn:
        await conn.exec_driver_sql(statement)
