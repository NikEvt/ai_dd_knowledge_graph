from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.notifications import service


@subscribe("booking.created")
async def on_booking_created(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.send(
        session,
        application_id=payload["application_id"],
        type_="booking",
        venue_id=payload["venue_id"],
        context={"starts_at": payload["starts_at"]},
    )


@subscribe("booking.cancelled")
async def on_booking_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.send(
        session,
        application_id=payload["application_id"],
        type_="cancel",
        venue_id=payload["venue_id"],
        context={"starts_at": payload["starts_at"]},
    )
