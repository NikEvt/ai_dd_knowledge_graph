from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from libs.errors import DomainError
from services.reports import service, settings
from services.reports.models import FINISHED, ExportSchedule, ReportDefinition, ReportRun


async def run_scheduled(session: AsyncSession, now: datetime) -> list[int]:
    """Ставит в очередь выгрузки, у которых подошёл срок."""
    schedules = (
        await session.scalars(
            select(ExportSchedule)
            .join(ReportDefinition, ReportDefinition.id == ExportSchedule.definition_id)
            .where(
                ExportSchedule.is_active.is_(True),
                ExportSchedule.next_run_at <= now,
                ReportDefinition.is_active.is_(True),
            )
            .order_by(ExportSchedule.next_run_at, ExportSchedule.id)
            .with_for_update(of=ExportSchedule, skip_locked=True)
        )
    ).all()
    run_ids = []
    for schedule in schedules:
        try:
            run = await service.request_run(
                session, schedule.definition_id, schedule.created_by, schedule=schedule, now=now
            )
        except DomainError:
            # Определение могли сломать после постановки на расписание — не держим остальные выгрузки.
            schedule.is_active = False
            continue
        run_ids.append(run.id)
        service.advance(schedule, now)
    return run_ids


async def fail_stuck_runs(session: AsyncSession, now: datetime) -> list[int]:
    runs = (
        await session.scalars(
            select(ReportRun)
            .where(
                ReportRun.status == "running",
                ReportRun.started_at < now - timedelta(minutes=settings.RUN_TIMEOUT_MINUTES),
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    for run in runs:
        run.status = "failed"
        run.error = "превышено время построения отчёта"
        run.finished_at = now
        events.publish(
            session,
            "reports.run_failed",
            {"run_id": run.id, "definition_id": run.definition_id, "error": run.error},
        )
    return [run.id for run in runs]


async def purge_old_runs(session: AsyncSession, now: datetime) -> int:
    """Удаляет завершённые запуски старше срока хранения; уведомления уходят каскадом."""
    deleted = await session.scalars(
        delete(ReportRun)
        .where(
            ReportRun.status.in_(FINISHED),
            ReportRun.finished_at < now - timedelta(days=settings.RETENTION_DAYS),
        )
        .returning(ReportRun.id)
    )
    return len(deleted.all())
