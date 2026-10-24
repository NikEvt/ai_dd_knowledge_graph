from datetime import timedelta

import pytest

from libs.errors import DomainError
from services.scheduling import service as scheduling
from tests.factories import (
    CHECKER,
    HISTORY,
    KZN,
    LAW,
    MSK,
    T0,
    act,
    book,
    new_application,
    pass_review,
    read,
    slot,
    token,
    travel,
)


async def test_slot_in_past_forbidden() -> None:
    with pytest.raises(DomainError, match="прошедшее"):
        await slot(MSK, HISTORY, T0 - timedelta(hours=1))


async def test_checker_can_only_reduce_capacity() -> None:
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    await act(scheduling.reduce_capacity, slot_id, CHECKER[MSK], 1)
    with pytest.raises(DomainError):
        await act(scheduling.reduce_capacity, slot_id, CHECKER[MSK], 2)


async def test_slot_capacity_cannot_exceed_venue_maximum() -> None:
    with pytest.raises(Exception, match="exceeds venue maximum"):
        await slot(MSK, HISTORY, T0 + timedelta(days=5), capacity=10)


async def test_booking_only_on_own_venue_and_sphere() -> None:
    app_id = await new_application(rep=2)
    await pass_review(app_id)
    other_venue = await slot(KZN, HISTORY, T0 + timedelta(days=5))
    other_sphere = await slot(MSK, LAW, T0 + timedelta(days=5))
    for slot_id in (other_venue, other_sphere):
        with pytest.raises(DomainError):
            await book(app_id, slot_id)


async def test_free_slots_hide_full_windows() -> None:
    app_id = await new_application(rep=2)
    await pass_review(app_id)
    full = await slot(MSK, HISTORY, T0 + timedelta(days=5), capacity=1)
    free = await slot(MSK, HISTORY, T0 + timedelta(days=6))
    other = await new_application(rep=2, client=2)
    await pass_review(other)
    await book(other, full)
    slots = await read(scheduling.free_slots, await token(app_id))
    assert [s.id for s in slots] == [free]


async def test_client_cannot_cancel_less_than_two_days_before() -> None:
    app_id = await new_application(rep=2)
    await pass_review(app_id)
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=3))
    booking_id = await book(app_id, slot_id)
    travel(T0 + timedelta(days=2))
    with pytest.raises(DomainError, match="два"):
        await act(scheduling.cancel_booking, booking_id, by="client")
    await act(scheduling.cancel_booking, booking_id, by="operator")


async def test_no_show_cancels_booking_and_allows_rebooking() -> None:
    app_id = await new_application(rep=2)
    await pass_review(app_id)
    first = await slot(MSK, HISTORY, T0 + timedelta(days=3))
    second = await slot(MSK, HISTORY, T0 + timedelta(days=6))
    booking_id = await book(app_id, first)
    travel(T0 + timedelta(days=3, hours=2))
    await act(scheduling.mark_no_show, booking_id, CHECKER[MSK])
    await book(app_id, second)
