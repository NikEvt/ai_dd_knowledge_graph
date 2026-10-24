from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.halls import service


@subscribe("halls.invoice_issued")
async def on_invoice_issued(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.send_email(session, payload["booking_id"], "invoice", {"amount": payload["amount"]})


@subscribe("halls.payment_received")
async def on_payment_received(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.apply_payments(session, payload["booking_id"])


@subscribe("halls.booking_prepaid")
async def on_booking_prepaid(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.send_email(session, payload["booking_id"], "prepaid", {"paid": payload["paid"]})


@subscribe("halls.booking_confirmed")
async def on_booking_confirmed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.send_email(session, payload["booking_id"], "confirmed")


@subscribe("halls.venue_changed")
async def on_venue_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.reissue_invoice(session, payload["booking_id"])


@subscribe("halls.booking_cancelled")
async def on_booking_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.void_invoice(session, payload["booking_id"])
    await service.send_email(session, payload["booking_id"], "cancel", {"reason": payload["reason"]})
