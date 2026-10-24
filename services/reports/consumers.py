from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.reports import service, settings


@subscribe("reports.run_requested")
async def on_run_requested(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.build_run(session, payload["run_id"])


@subscribe("reports.run_completed")
async def on_run_completed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.notify_run_finished(session, payload["run_id"], "completed")


@subscribe("reports.run_completed")
async def count_completed_run(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_to_snapshot(
        session,
        settings.RUNS_COMPLETED_METRIC,
        1,
        dimension=payload["code"],
        day=date.fromisoformat(payload["finished_on"]),
    )


@subscribe("reports.run_failed")
async def on_run_failed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.notify_run_finished(session, payload["run_id"], "failed")


@subscribe("reports.run_cancelled")
async def on_run_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    # Сам отменивший знает об отмене; сообщаем только об отменах по отключению отчёта.
    if payload["reason"] != "by_user":
        await service.notify_run_finished(session, payload["run_id"], "cancelled")


@subscribe("reports.definition_deactivated")
async def on_definition_deactivated(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.cancel_pending_for_definition(session, payload["definition_id"])
