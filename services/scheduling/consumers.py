from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.applications import public as applications
from services.scheduling import service
from services.scheduling.models import VenueLimit


@subscribe("application.ready_for_booking")
async def on_ready_for_booking(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.issue_link(session, payload["application_id"], "issue")


@subscribe("application.venue_changed")
async def on_venue_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.reset_bookings(session, payload["application_id"], reason="venue_changed")
    brief = await applications.get_brief(session, payload["application_id"])
    if brief.stage == "awaiting_issue":
        await service.issue_link(session, brief.id, "issue")


@subscribe("application.archived")
async def on_archived(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.reset_bookings(session, payload["application_id"], reason="archived")


@subscribe("application.closed_duplicate")
async def on_closed_duplicate(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.reset_bookings(session, payload["application_id"], reason="duplicate")


@subscribe("venue.settings_changed")
async def on_venue_settings_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    limit = await session.get(VenueLimit, payload["venue_id"])
    if limit is None:
        session.add(VenueLimit(venue_id=payload["venue_id"], max_capacity=payload["max_capacity"]))
    else:
        limit.max_capacity = payload["max_capacity"]
