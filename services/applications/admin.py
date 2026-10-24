"""Админка: условия представителей, реквизиты и лимиты площадок, сферы площадок."""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from libs.errors import DomainError, NotFound
from services.applications.models import Representative, Venue, VenueSphere


async def set_representative_terms(
    session: AsyncSession, representative_id: int, *, markup_pct: Decimal, debt_allowed: bool
) -> Representative:
    rep = await session.get(Representative, representative_id)
    if rep is None:
        raise NotFound(f"представитель {representative_id}")
    rep.markup_pct = markup_pct
    rep.debt_allowed = debt_allowed
    return rep


async def set_venue_requisites(session: AsyncSession, venue_id: int, requisites: dict[str, Any]) -> Venue:
    venue = await session.get(Venue, venue_id)
    if venue is None:
        raise NotFound(f"площадка {venue_id}")
    venue.requisites = requisites
    return venue


async def set_venue_max_capacity(session: AsyncSession, venue_id: int, max_capacity: int) -> Venue:
    venue = await session.get(Venue, venue_id)
    if venue is None:
        raise NotFound(f"площадка {venue_id}")
    if max_capacity < 1:
        raise DomainError("максимум мест должен быть положительным")
    old = venue.max_slot_capacity
    venue.max_slot_capacity = max_capacity
    events.publish(
        session,
        "venue.settings_changed",
        {"venue_id": venue_id, "max_capacity": max_capacity, "old_max_capacity": old},
    )
    return venue


async def set_sphere_active(session: AsyncSession, venue_id: int, sphere_id: int, active: bool) -> None:
    """Площадка перестаёт работать со сферой: действующие заявки доводятся до конца, новые не создаются."""
    vs = await session.get(VenueSphere, (venue_id, sphere_id))
    if vs is None:
        session.add(VenueSphere(venue_id=venue_id, sphere_id=sphere_id, active=active))
    else:
        vs.active = active
