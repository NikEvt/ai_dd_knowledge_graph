"""Внутренняя отчётность: снимки метрик, определения отчётов, запуски, расписания выгрузок."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.reports import builders, settings
from services.reports.models import (
    IN_FLIGHT,
    ExportSchedule,
    MetricSnapshot,
    ReportDefinition,
    ReportRun,
    RunNotification,
)

# Снимки метрик -----------------------------------------------------------------


def _decimal(value: Decimal | int | str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation, TypeError, ValueError:
        raise DomainError(f"значение метрики должно быть числом: {value!r}") from None
    if not result.is_finite():
        raise DomainError("значение метрики должно быть конечным числом")
    return result


async def record_snapshot(
    session: AsyncSession,
    metric: str,
    value: Decimal | int | str,
    *,
    dimension: str = "",
    day: date | None = None,
) -> MetricSnapshot:
    """Записывает значение метрики за день; повторная запись за тот же день заменяет значение."""
    now = clock.now()
    stmt = insert(MetricSnapshot).values(
        metric=builders.metric_name(metric),
        dimension=dimension,
        day=day or now.date(),
        value=_decimal(value),
        taken_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="metric_snapshots_point",
        set_={"value": stmt.excluded.value, "taken_at": stmt.excluded.taken_at},
    )
    return await session.scalar(stmt.returning(MetricSnapshot).execution_options(populate_existing=True))


async def add_to_snapshot(
    session: AsyncSession, metric: str, delta: Decimal | int, *, dimension: str = "", day: date
) -> None:
    stmt = insert(MetricSnapshot).values(
        metric=metric, dimension=dimension, day=day, value=_decimal(delta), taken_at=clock.now()
    )
    await session.execute(
        stmt.on_conflict_do_update(
            constraint="metric_snapshots_point",
            set_={"value": MetricSnapshot.value + stmt.excluded.value, "taken_at": stmt.excluded.taken_at},
        )
    )


# Определения отчётов -------------------------------------------------------------


async def get_definition(session: AsyncSession, definition_id: int) -> ReportDefinition:
    definition = await session.get(ReportDefinition, definition_id)
    if definition is None:
        raise NotFound(f"отчёт {definition_id}")
    return definition


async def _owned_definition(session: AsyncSession, definition_id: int, by: int) -> ReportDefinition:
    definition = await get_definition(session, definition_id)
    if definition.owner_id != by:
        raise AccessDenied("настройки отчёта меняет только его владелец")
    return definition


async def _check_title_free(
    session: AsyncSession, owner_id: int, title: str, exclude_id: int | None = None
) -> None:
    query = select(ReportDefinition.id).where(
        ReportDefinition.owner_id == owner_id,
        ReportDefinition.is_active.is_(True),
        func.lower(ReportDefinition.title) == title.lower(),
    )
    if exclude_id is not None:
        query = query.where(ReportDefinition.id != exclude_id)
    if await session.scalar(query) is not None:
        raise DomainError(f"у вас уже есть действующий отчёт «{title}»")


async def create_definition(
    session: AsyncSession,
    *,
    owner_id: int,
    code: str,
    title: str,
    kind: str,
    params: dict[str, Any] | None = None,
) -> ReportDefinition:
    title = title.strip()
    if not title:
        raise DomainError("у отчёта должно быть название")
    normalized = builders.normalize_params(kind, params or {})
    builders.require_complete(kind, normalized)
    if await session.scalar(select(ReportDefinition.id).where(ReportDefinition.code == code)):
        raise DomainError(f"код отчёта {code} уже занят")
    await _check_title_free(session, owner_id, title)
    now = clock.now()
    definition = ReportDefinition(
        code=code,
        title=title,
        kind=kind,
        params=normalized,
        owner_id=owner_id,
        created_at=now,
        updated_at=now,
    )
    session.add(definition)
    await session.flush()
    return definition


async def update_definition(
    session: AsyncSession,
    definition_id: int,
    by: int,
    *,
    title: str | None = None,
    kind: str | None = None,
    params: dict[str, Any] | None = None,
) -> ReportDefinition:
    definition = await _owned_definition(session, definition_id, by)
    if not definition.is_active:
        raise DomainError("отчёт отключён, изменить его нельзя")
    if title is not None:
        title = title.strip()
        if not title:
            raise DomainError("у отчёта должно быть название")
        await _check_title_free(session, definition.owner_id, title, exclude_id=definition.id)
        definition.title = title
    new_kind = kind or definition.kind
    if kind is not None or params is not None:
        normalized = builders.normalize_params(new_kind, definition.params if params is None else params)
        builders.require_complete(new_kind, normalized)
        definition.kind = new_kind
        definition.params = normalized
    definition.updated_at = clock.now()
    await session.flush()
    return definition


async def deactivate_definition(session: AsyncSession, definition_id: int, by: int) -> ReportDefinition:
    definition = await _owned_definition(session, definition_id, by)
    if not definition.is_active:
        return definition
    definition.is_active = False
    definition.updated_at = clock.now()
    schedules = await session.scalars(
        select(ExportSchedule).where(
            ExportSchedule.definition_id == definition_id, ExportSchedule.is_active.is_(True)
        )
    )
    for schedule in schedules:
        schedule.is_active = False
    events.publish(
        session, "reports.definition_deactivated", {"definition_id": definition.id, "code": definition.code}
    )
    return definition


async def list_definitions(
    session: AsyncSession, *, owner_id: int | None = None, active_only: bool = True
) -> list[ReportDefinition]:
    query = select(ReportDefinition).order_by(ReportDefinition.id)
    if owner_id is not None:
        query = query.where(ReportDefinition.owner_id == owner_id)
    if active_only:
        query = query.where(ReportDefinition.is_active.is_(True))
    return list((await session.scalars(query)).all())


# Запуски ----------------------------------------------------------------------


async def get_run(session: AsyncSession, run_id: int) -> ReportRun:
    run = await session.get(ReportRun, run_id)
    if run is None:
        raise NotFound(f"запуск {run_id}")
    return run


async def _check_run_quota(session: AsyncSession, definition_id: int, requested_by: int) -> None:
    pending = await session.scalars(
        select(ReportRun.definition_id).where(
            ReportRun.requested_by == requested_by,
            ReportRun.schedule_id.is_(None),
            ReportRun.status.in_(IN_FLIGHT),
        )
    )
    pending_ids = pending.all()
    if definition_id in pending_ids:
        raise DomainError("по этому отчёту у вас уже есть незавершённый запуск")
    limit = settings.MAX_PENDING_RUNS_PER_USER
    if len(pending_ids) >= limit:
        raise DomainError(f"одновременно можно держать не больше {limit} незавершённых запусков")


async def request_run(
    session: AsyncSession,
    definition_id: int,
    requested_by: int,
    params: dict[str, Any] | None = None,
    *,
    schedule: ExportSchedule | None = None,
    now: datetime | None = None,
) -> ReportRun:
    definition = await get_definition(session, definition_id)
    if not definition.is_active:
        raise DomainError("отчёт отключён, запустить его нельзя")
    params = params or {}
    extra = set(params) - builders.RUN_OVERRIDABLE
    if extra:
        raise DomainError(f"при запуске нельзя менять параметры: {', '.join(sorted(extra))}")
    run_params = builders.normalize_params(definition.kind, params)
    if schedule is None:
        await _check_run_quota(session, definition_id, requested_by)

    run = ReportRun(
        definition_id=definition.id,
        schedule_id=schedule.id if schedule else None,
        scheduled_for=schedule.next_run_at if schedule else None,
        status="requested",
        params=run_params,
        requested_by=requested_by,
        requested_at=now or clock.now(),
    )
    session.add(run)
    await session.flush()
    events.publish(
        session,
        "reports.run_requested",
        {"run_id": run.id, "definition_id": definition.id, "scheduled": schedule is not None},
    )
    return run


def _finish(
    run: ReportRun, status: str, *, body: dict[str, Any] | None = None, error: str | None = None
) -> None:
    run.status = status
    run.body = body
    run.error = error
    run.finished_at = clock.now()


def _publish_cancelled(session: AsyncSession, run: ReportRun, reason: str) -> None:
    events.publish(
        session,
        "reports.run_cancelled",
        {"run_id": run.id, "definition_id": run.definition_id, "reason": reason},
    )


async def build_run(session: AsyncSession, run_id: int) -> ReportRun:
    """Строит отчёт по ожидающему запуску. Повторная доставка события ничего не меняет."""
    run = await session.get(ReportRun, run_id, with_for_update=True)
    if run is None or run.status != "requested":
        return run
    definition = await get_definition(session, run.definition_id)
    if not definition.is_active:
        _finish(run, "cancelled")
        _publish_cancelled(session, run, "definition_deactivated")
        return run

    run.status = "running"
    run.started_at = clock.now()
    await session.flush()
    try:
        body = await builders.build(session, definition, run)
    except DomainError as exc:
        _finish(run, "failed", error=str(exc))
        await session.flush()
        events.publish(
            session,
            "reports.run_failed",
            {"run_id": run.id, "definition_id": definition.id, "error": run.error},
        )
        return run

    _finish(run, "completed", body=body)
    await session.flush()
    events.publish(
        session,
        "reports.run_completed",
        {
            "run_id": run.id,
            "definition_id": definition.id,
            "code": definition.code,
            "schedule_id": run.schedule_id,
            "finished_on": run.finished_at.date().isoformat(),
        },
    )
    return run


async def cancel_run(session: AsyncSession, run_id: int, by: int) -> ReportRun:
    run = await get_run(session, run_id)
    if run.requested_by != by:
        raise AccessDenied("отменить запуск может только тот, кто его запросил")
    if run.status != "requested":
        raise DomainError("отменить можно только запуск, который ещё не начал строиться")
    _finish(run, "cancelled")
    _publish_cancelled(session, run, "by_user")
    return run


async def cancel_pending_for_definition(session: AsyncSession, definition_id: int) -> list[int]:
    runs = (
        await session.scalars(
            select(ReportRun)
            .where(ReportRun.definition_id == definition_id, ReportRun.status == "requested")
            .with_for_update(skip_locked=True)
        )
    ).all()
    for run in runs:
        _finish(run, "cancelled")
        _publish_cancelled(session, run, "definition_deactivated")
    return [run.id for run in runs]


async def list_runs(
    session: AsyncSession,
    *,
    definition_id: int | None = None,
    requested_by: int | None = None,
    status: str | None = None,
    limit: int = settings.RUNS_PAGE_LIMIT,
) -> list[ReportRun]:
    query = select(ReportRun).order_by(ReportRun.requested_at.desc(), ReportRun.id.desc())
    if definition_id is not None:
        query = query.where(ReportRun.definition_id == definition_id)
    if requested_by is not None:
        query = query.where(ReportRun.requested_by == requested_by)
    if status is not None:
        query = query.where(ReportRun.status == status)
    return list((await session.scalars(query.limit(min(limit, settings.RUNS_PAGE_LIMIT)))).all())


# Расписания выгрузок ---------------------------------------------------------------


def _recipients(recipients: list[int]) -> list[int]:
    unique = list(dict.fromkeys(recipients))
    if not unique:
        raise DomainError("у выгрузки должен быть хотя бы один получатель")
    if len(unique) > settings.MAX_RECIPIENTS:
        raise DomainError(f"у выгрузки не больше {settings.MAX_RECIPIENTS} получателей")
    return unique


async def create_schedule(
    session: AsyncSession,
    definition_id: int,
    by: int,
    *,
    every_hours: int,
    recipients: list[int],
    first_run_at: datetime | None = None,
) -> ExportSchedule:
    definition = await _owned_definition(session, definition_id, by)
    if not definition.is_active:
        raise DomainError("отчёт отключён, поставить его на расписание нельзя")
    if not settings.MIN_SCHEDULE_INTERVAL_HOURS <= every_hours <= settings.MAX_SCHEDULE_INTERVAL_HOURS:
        raise DomainError(
            f"интервал выгрузки — от {settings.MIN_SCHEDULE_INTERVAL_HOURS} "
            f"до {settings.MAX_SCHEDULE_INTERVAL_HOURS} часов"
        )
    now = clock.now()
    if first_run_at is not None and first_run_at < now:
        raise DomainError("первая выгрузка не может быть в прошлом")
    existing = await session.scalar(
        select(ExportSchedule.id).where(
            ExportSchedule.definition_id == definition_id, ExportSchedule.is_active.is_(True)
        )
    )
    if existing is not None:
        raise DomainError("у отчёта уже есть действующее расписание выгрузки")
    schedule = ExportSchedule(
        definition_id=definition_id,
        every_hours=every_hours,
        next_run_at=first_run_at or now,
        recipients=_recipients(recipients),
        created_by=by,
        created_at=now,
    )
    session.add(schedule)
    await session.flush()
    return schedule


async def deactivate_schedule(session: AsyncSession, schedule_id: int, by: int) -> ExportSchedule:
    schedule = await session.get(ExportSchedule, schedule_id)
    if schedule is None:
        raise NotFound(f"расписание {schedule_id}")
    definition = await get_definition(session, schedule.definition_id)
    if by not in (schedule.created_by, definition.owner_id):
        raise AccessDenied("отключить выгрузку может её автор или владелец отчёта")
    schedule.is_active = False
    return schedule


def advance(schedule: ExportSchedule, now: datetime) -> None:
    """Сдвигает следующую выгрузку за `now`; пропущенные интервалы не догоняются."""
    step = timedelta(hours=schedule.every_hours)
    while schedule.next_run_at <= now:
        schedule.next_run_at += step
    schedule.last_enqueued_at = now


# Уведомления ------------------------------------------------------------------


async def _notification_targets(
    session: AsyncSession, run: ReportRun, definition: ReportDefinition, kind: str
) -> list[int]:
    targets = [run.requested_by]
    if kind == "completed" and run.schedule_id is not None:
        schedule = await session.get(ExportSchedule, run.schedule_id)
        targets += [int(r) for r in schedule.recipients]
    if kind == "failed":
        targets.append(definition.owner_id)
    return list(dict.fromkeys(targets))


def _notification_text(run: ReportRun, definition: ReportDefinition, kind: str) -> str:
    match kind:
        case "completed":
            return f"Отчёт «{definition.title}» готов (запуск №{run.id})"
        case "failed":
            return f"Отчёт «{definition.title}» не построен (запуск №{run.id}): {run.error}"
        case _:
            return f"Запуск №{run.id} отчёта «{definition.title}» отменён: отчёт отключён"


async def notify_run_finished(session: AsyncSession, run_id: int, kind: str) -> list[int]:
    run = await session.get(ReportRun, run_id)
    if run is None:
        return []
    definition = await get_definition(session, run.definition_id)
    targets = await _notification_targets(session, run, definition, kind)
    body = _notification_text(run, definition, kind)
    now = clock.now()
    stmt = insert(RunNotification).values(
        [
            {"run_id": run.id, "recipient_id": r, "kind": kind, "body": body, "created_at": now}
            for r in targets
        ]
    )
    await session.execute(stmt.on_conflict_do_nothing(constraint="run_notifications_once"))
    return targets


async def inbox(
    session: AsyncSession, recipient_id: int, *, unread_only: bool = False
) -> list[RunNotification]:
    query = (
        select(RunNotification)
        .where(RunNotification.recipient_id == recipient_id)
        .order_by(RunNotification.created_at.desc(), RunNotification.id.desc())
    )
    if unread_only:
        query = query.where(RunNotification.read_at.is_(None))
    return list((await session.scalars(query)).all())


async def mark_read(session: AsyncSession, notification_id: int, recipient_id: int) -> RunNotification:
    notification = await session.get(RunNotification, notification_id)
    if notification is None:
        raise NotFound(f"уведомление {notification_id}")
    if notification.recipient_id != recipient_id:
        raise AccessDenied("уведомление адресовано другому сотруднику")
    if notification.read_at is None:
        notification.read_at = clock.now()
    return notification
