from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.lectures import service

router = APIRouter(tags=["lectures"])
Session = Annotated[AsyncSession, Depends(session)]


class VenueLimitIn(BaseModel):
    max_capacity: int = Field(gt=0)


class EventIn(BaseModel):
    organizer_id: int
    title: str
    venue_id: int
    starts_at: datetime
    capacity: int | None = Field(default=None, gt=0)


class EventOut(BaseModel):
    id: int
    title: str
    venue_id: int
    starts_at: datetime
    capacity: int
    free_seats: int


class CapacityIn(BaseModel):
    organizer_id: int
    capacity: int = Field(gt=0)


class MoveIn(BaseModel):
    organizer_id: int
    venue_id: int
    capacity: int | None = Field(default=None, gt=0)


class OrganizerIn(BaseModel):
    organizer_id: int


class ListenerIn(BaseModel):
    listener_id: int


class NotificationOut(BaseModel):
    event_id: int
    kind: str
    body: str
    created_at: datetime


@router.put("/venues/{venue_id}/capacity-limit", status_code=202)
async def set_limit(venue_id: int, body: VenueLimitIn, s: Session) -> None:
    await service.set_venue_capacity_limit(s, venue_id, body.max_capacity)


@router.post("/events", status_code=201)
async def create_event(body: EventIn, s: Session) -> dict[str, int]:
    lecture = await service.create_event(s, **body.model_dump())
    return {"event_id": lecture.id}


@router.get("/events")
async def list_events(s: Session, venue_id: int | None = None) -> list[EventOut]:
    return [
        EventOut(
            id=x.id,
            title=x.title,
            venue_id=x.venue_id,
            starts_at=x.starts_at,
            capacity=x.capacity,
            free_seats=free,
        )
        for x, free in await service.upcoming(s, venue_id)
    ]


@router.put("/events/{event_id}/capacity")
async def change_capacity(event_id: int, body: CapacityIn, s: Session) -> None:
    await service.change_capacity(s, event_id, body.organizer_id, body.capacity)


@router.post("/events/{event_id}/move")
async def move_event(event_id: int, body: MoveIn, s: Session) -> None:
    await service.move_event(s, event_id, body.organizer_id, venue_id=body.venue_id, capacity=body.capacity)


@router.post("/events/{event_id}/cancel")
async def cancel_event(event_id: int, body: OrganizerIn, s: Session) -> None:
    await service.cancel_event(s, event_id, body.organizer_id)


@router.post("/events/{event_id}/registrations", status_code=201)
async def register(event_id: int, body: ListenerIn, s: Session) -> dict[str, int]:
    r = await service.register(s, event_id, body.listener_id)
    return {"registration_id": r.id}


@router.delete("/registrations/{registration_id}")
async def cancel_registration(registration_id: int, listener_id: int, s: Session) -> None:
    await service.cancel_registration(s, registration_id, listener_id)


@router.post("/events/{event_id}/waitlist", status_code=201)
async def join_waitlist(event_id: int, body: ListenerIn, s: Session) -> dict[str, int]:
    entry = await service.join_waitlist(s, event_id, body.listener_id)
    return {"waitlist_id": entry.id, "position": await service.waitlist_position(s, entry.id)}


@router.delete("/waitlist/{entry_id}")
async def leave_waitlist(entry_id: int, listener_id: int, s: Session) -> None:
    await service.leave_waitlist(s, entry_id, listener_id)


@router.get("/listeners/{listener_id}/notifications")
async def listener_notifications(listener_id: int, s: Session) -> list[NotificationOut]:
    return [
        NotificationOut(event_id=n.event_id, kind=n.kind, body=n.body, created_at=n.created_at)
        for n in await service.notifications(s, listener_id)
    ]
