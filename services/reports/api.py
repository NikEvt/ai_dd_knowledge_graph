from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.reports import service, settings
from services.reports.models import ReportDefinition, ReportRun, RunNotification

router = APIRouter(prefix="/reports", tags=["reports"])
Session = Annotated[AsyncSession, Depends(session)]


class DefinitionIn(BaseModel):
    owner_id: int
    code: str
    title: str
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)


class DefinitionOut(BaseModel):
    id: int
    code: str
    title: str
    kind: str
    params: dict[str, Any]
    owner_id: int
    is_active: bool

    @classmethod
    def of(cls, d: ReportDefinition) -> DefinitionOut:
        return cls(
            id=d.id,
            code=d.code,
            title=d.title,
            kind=d.kind,
            params=d.params,
            owner_id=d.owner_id,
            is_active=d.is_active,
        )


class RunIn(BaseModel):
    requested_by: int
    params: dict[str, Any] = Field(default_factory=dict)


class RunOut(BaseModel):
    id: int
    definition_id: int
    status: str
    params: dict[str, Any]
    body: dict[str, Any] | None
    error: str | None
    requested_at: datetime
    finished_at: datetime | None

    @classmethod
    def of(cls, r: ReportRun) -> RunOut:
        return cls(
            id=r.id,
            definition_id=r.definition_id,
            status=r.status,
            params=r.params,
            body=r.body,
            error=r.error,
            requested_at=r.requested_at,
            finished_at=r.finished_at,
        )


class SnapshotIn(BaseModel):
    metric: str
    value: Decimal
    dimension: str = ""
    day: date | None = None


class ScheduleIn(BaseModel):
    created_by: int
    every_hours: int
    recipients: list[int]
    first_run_at: datetime | None = None


class NotificationOut(BaseModel):
    id: int
    run_id: int
    kind: str
    body: str
    read: bool

    @classmethod
    def of(cls, n: RunNotification) -> NotificationOut:
        return cls(id=n.id, run_id=n.run_id, kind=n.kind, body=n.body, read=n.read_at is not None)


@router.post("/snapshots", status_code=201)
async def record_snapshot(body: SnapshotIn, s: Session) -> dict[str, int]:
    snap = await service.record_snapshot(s, body.metric, body.value, dimension=body.dimension, day=body.day)
    return {"snapshot_id": snap.id}


@router.post("/definitions", status_code=201)
async def create_definition(body: DefinitionIn, s: Session) -> DefinitionOut:
    d = await service.create_definition(
        s, owner_id=body.owner_id, code=body.code, title=body.title, kind=body.kind, params=body.params
    )
    return DefinitionOut.of(d)


@router.get("/definitions")
async def definitions(s: Session, owner_id: int | None = None) -> list[DefinitionOut]:
    return [DefinitionOut.of(d) for d in await service.list_definitions(s, owner_id=owner_id)]


@router.delete("/definitions/{definition_id}")
async def deactivate_definition(definition_id: int, by: int, s: Session) -> DefinitionOut:
    return DefinitionOut.of(await service.deactivate_definition(s, definition_id, by))


@router.post("/definitions/{definition_id}/runs", status_code=202)
async def request_run(definition_id: int, body: RunIn, s: Session) -> RunOut:
    run = await service.request_run(s, definition_id, body.requested_by, body.params)
    return RunOut.of(run)


@router.post("/definitions/{definition_id}/schedules", status_code=201)
async def create_schedule(definition_id: int, body: ScheduleIn, s: Session) -> dict[str, Any]:
    schedule = await service.create_schedule(
        s,
        definition_id,
        body.created_by,
        every_hours=body.every_hours,
        recipients=body.recipients,
        first_run_at=body.first_run_at,
    )
    return {"schedule_id": schedule.id, "next_run_at": schedule.next_run_at}


@router.get("/runs")
async def runs(
    s: Session,
    definition_id: int | None = None,
    requested_by: int | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=settings.RUNS_PAGE_LIMIT)] = settings.RUNS_PAGE_LIMIT,
) -> list[RunOut]:
    found = await service.list_runs(
        s, definition_id=definition_id, requested_by=requested_by, status=status, limit=limit
    )
    return [RunOut.of(r) for r in found]


@router.get("/runs/{run_id}")
async def run(run_id: int, s: Session) -> RunOut:
    return RunOut.of(await service.get_run(s, run_id))


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: int, by: int, s: Session) -> RunOut:
    return RunOut.of(await service.cancel_run(s, run_id, by))


@router.get("/notifications")
async def notifications(recipient_id: int, s: Session, unread_only: bool = False) -> list[NotificationOut]:
    found = await service.inbox(s, recipient_id, unread_only=unread_only)
    return [NotificationOut.of(n) for n in found]


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: int, recipient_id: int, s: Session) -> NotificationOut:
    return NotificationOut.of(await service.mark_read(s, notification_id, recipient_id))
