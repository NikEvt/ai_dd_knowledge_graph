"""Внутренний API сервиса заявок для других сервисов (в проде — HTTP-клиент)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.errors import NotFound
from services.applications.models import Application, ApplicationBook, Client, Price, Representative, Venue


@dataclass(frozen=True)
class ApplicationBrief:
    id: int
    client_id: int
    representative_id: int
    sphere_id: int
    venue_id: int
    kind: str
    stage: str
    operator_id: int
    reviewer_id: int | None
    site_checker_id: int
    book_ids: list[int]


@dataclass(frozen=True)
class VenueInfo:
    id: int
    city: str
    requisites: dict[str, Any] | None
    max_slot_capacity: int
    site_checker_id: int


async def get_brief(session: AsyncSession, application_id: int) -> ApplicationBrief:
    app = await session.get(Application, application_id)
    if app is None:
        raise NotFound(f"заявка {application_id}")
    return ApplicationBrief(
        id=app.id,
        client_id=app.client_id,
        representative_id=app.representative_id,
        sphere_id=app.sphere_id,
        venue_id=app.venue_id,
        kind=app.kind,
        stage=app.stage,
        operator_id=app.operator_id,
        reviewer_id=app.reviewer_id,
        site_checker_id=app.site_checker_id,
        book_ids=app.book_ids,
    )


async def get_venue(session: AsyncSession, venue_id: int) -> VenueInfo:
    v = await session.get(Venue, venue_id)
    if v is None:
        raise NotFound(f"площадка {venue_id}")
    return VenueInfo(v.id, v.city, v.requisites, v.max_slot_capacity, v.site_checker_id)


async def books_price(session: AsyncSession, application_id: int) -> Decimal:
    app = await session.get(Application, application_id)
    if app is None:
        raise NotFound(f"заявка {application_id}")
    total = await session.scalar(
        select(func.coalesce(func.sum(Price.price), 0))
        .join(ApplicationBook, ApplicationBook.book_id == Price.book_id)
        .where(ApplicationBook.application_id == application_id, Price.venue_id == app.venue_id)
    )
    return Decimal(total)


async def markup_pct(session: AsyncSession, representative_id: int) -> Decimal:
    rep = await session.get(Representative, representative_id)
    if rep is None:
        raise NotFound(f"представитель {representative_id}")
    return rep.markup_pct


async def recipients(session: AsyncSession, application_id: int) -> list[str]:
    """Письма получают только клиент и представитель."""
    app = await session.get(Application, application_id)
    if app is None:
        raise NotFound(f"заявка {application_id}")
    client = await session.get(Client, app.client_id)
    rep = await session.get(Representative, app.representative_id)
    return [client.email, rep.email]
