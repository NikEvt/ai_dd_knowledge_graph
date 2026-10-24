from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.scheduling import service

router = APIRouter(tags=["scheduling"])
Session = Annotated[AsyncSession, Depends(session)]


class SlotOut(BaseModel):
    id: int
    starts_at: datetime
    capacity: int


class BookingIn(BaseModel):
    slot_id: int
    booked_by: str = "client"


@router.get("/links/{token}/slots")
async def slots(token: str, s: Session) -> list[SlotOut]:
    return [
        SlotOut(id=x.id, starts_at=x.starts_at, capacity=x.capacity)
        for x in await service.free_slots(s, token)
    ]


@router.post("/links/{token}/bookings", status_code=201)
async def book(token: str, body: BookingIn, s: Session) -> dict[str, int]:
    b = await service.book(s, token=token, slot_id=body.slot_id, booked_by=body.booked_by)
    return {"booking_id": b.id}


@router.delete("/bookings/{booking_id}")
async def cancel(booking_id: int, by: str, s: Session) -> None:
    await service.cancel_booking(s, booking_id, by=by)
