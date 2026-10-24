from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.halls import service
from services.halls.models import Hall, HallBooking

router = APIRouter(tags=["halls"])
Session = Annotated[AsyncSession, Depends(session)]


class HallIn(BaseModel):
    manager_id: int
    name: str
    capacity: int = Field(gt=0)
    hourly_rate: Decimal = Field(gt=0)


class HallOut(BaseModel):
    id: int
    venue_id: int
    name: str
    capacity: int
    hourly_rate: Decimal

    @classmethod
    def of(cls, h: Hall) -> HallOut:
        return cls(id=h.id, venue_id=h.venue_id, name=h.name, capacity=h.capacity, hourly_rate=h.hourly_rate)


class BookingIn(BaseModel):
    manager_id: int
    hall_id: int
    client_ref: str
    event_kind: str
    guests: int
    starts_at: datetime
    ends_at: datetime


class BookingOut(BaseModel):
    id: int
    hall_id: int
    venue_id: int
    client_ref: str
    event_kind: str
    status: str
    starts_at: datetime
    ends_at: datetime
    invoice_id: int | None
    amount: Decimal | None
    paid: Decimal


class VenueChangeIn(BaseModel):
    manager_id: int
    hall_id: int


class PaymentIn(BaseModel):
    amount: Decimal
    recorded_by: int
    external_ref: str | None = None


async def _booking_out(s: AsyncSession, b: HallBooking) -> BookingOut:
    invoice = await service.active_invoice(s, b.id)
    return BookingOut(
        id=b.id,
        hall_id=b.hall_id,
        venue_id=b.venue_id,
        client_ref=b.client_ref,
        event_kind=b.event_kind,
        status=b.status,
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        invoice_id=invoice.id if invoice else None,
        amount=invoice.amount if invoice else None,
        paid=await service.paid_total(s, invoice.id) if invoice else Decimal(0),
    )


@router.get("/venues/{venue_id}/halls")
async def list_halls(venue_id: int, s: Session) -> list[HallOut]:
    return [HallOut.of(h) for h in await service.venue_halls(s, venue_id)]


@router.post("/venues/{venue_id}/halls", status_code=201)
async def create_hall(venue_id: int, body: HallIn, s: Session) -> HallOut:
    hall = await service.create_hall(
        s,
        manager_id=body.manager_id,
        venue_id=venue_id,
        name=body.name,
        capacity=body.capacity,
        hourly_rate=body.hourly_rate,
    )
    return HallOut.of(hall)


@router.post("/bookings", status_code=201)
async def create_booking(body: BookingIn, s: Session) -> BookingOut:
    b = await service.create_booking(s, **body.model_dump())
    return await _booking_out(s, b)


@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: int, s: Session) -> BookingOut:
    return await _booking_out(s, await service.get_booking(s, booking_id))


@router.post("/bookings/{booking_id}/venue")
async def change_venue(booking_id: int, body: VenueChangeIn, s: Session) -> BookingOut:
    b = await service.change_venue(s, booking_id, body.manager_id, body.hall_id)
    return await _booking_out(s, b)


@router.delete("/bookings/{booking_id}")
async def cancel_booking(booking_id: int, manager_id: int, s: Session) -> None:
    await service.cancel_booking(s, booking_id, manager_id)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def record_payment(invoice_id: int, body: PaymentIn, s: Session) -> dict[str, int]:
    p = await service.record_payment(s, invoice_id, body.amount, body.recorded_by, body.external_ref)
    return {"payment_id": p.id}
