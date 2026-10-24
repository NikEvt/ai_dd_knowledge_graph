from datetime import timedelta

import pytest
from sqlalchemy.exc import DBAPIError

from libs import clock, db
from libs.errors import AccessDenied, DomainError
from services.lectures import consumers
from services.lectures import service as lectures
from services.lectures.models import Registration
from tests.factories import act, read, travel
from tests.lectures_factories import (
    ANNA,
    BORIS,
    DINA,
    EGOR,
    EVENING,
    GLEB,
    LISTENERS,
    LOFT,
    ORGANIZER,
    ORGANIZER_2,
    ROOM,
    VERA,
    attendees,
    fill,
    kinds,
    lecture,
    new_event,
    notices,
    register,
    registration,
    venues,
    wait,
    waitlist_entry,
)


@pytest.fixture(autouse=True)
async def _venues() -> None:
    await venues()


async def test_registration_confirmed_with_notice() -> None:
    event_id = await new_event(title="Рукописи XVIII века")
    reg_id = await register(event_id, ANNA)
    assert (await registration(reg_id)).status == "confirmed"
    [notice] = await notices(ANNA)
    assert notice.kind == "registered"
    assert "Рукописи XVIII века" in notice.body


async def test_full_event_sends_to_waitlist() -> None:
    event_id = await new_event(venue=ROOM)
    with pytest.raises(DomainError, match="свободные места"):
        await wait(event_id, GLEB)
    await fill(event_id, (ANNA, BORIS, VERA))
    with pytest.raises(DomainError, match="лист ожидания"):
        await register(event_id, GLEB)
    first = await wait(event_id, GLEB)
    second = await wait(event_id, DINA)
    assert await read(lectures.waitlist_position, first) == 1
    assert await read(lectures.waitlist_position, second) == 2


async def test_listener_limit_on_active_registrations() -> None:
    ids = [await new_event(starts_at=EVENING + timedelta(days=d)) for d in range(4)]
    for event_id in ids[:3]:
        await register(event_id, ANNA)
    with pytest.raises(DomainError, match="максимальное число"):
        await register(ids[3], ANNA)


async def test_registration_closes_an_hour_before_start() -> None:
    event_id = await new_event()
    travel(EVENING - timedelta(minutes=50))
    with pytest.raises(DomainError, match="закрыта"):
        await register(event_id, ANNA)


async def test_cancellation_gives_seat_to_first_in_waitlist() -> None:
    event_id = await new_event(venue=ROOM)
    anna, _, _ = await fill(event_id, (ANNA, BORIS, VERA))
    gleb = await wait(event_id, GLEB)
    dina = await wait(event_id, DINA)

    await act(lectures.cancel_registration, anna, ANNA)

    assert await attendees(event_id) == [BORIS, VERA, GLEB]
    assert (await waitlist_entry(gleb)).status == "promoted"
    assert await read(lectures.waitlist_position, dina) == 1
    assert await kinds(ANNA) == ["registered", "registration_cancelled"]
    assert await kinds(GLEB) == ["waitlist_promoted"]
    assert await kinds(DINA) == []


async def test_left_waitlist_entry_is_skipped() -> None:
    event_id = await new_event(venue=ROOM)
    regs = await fill(event_id, (ANNA, BORIS, VERA))
    gleb = await wait(event_id, GLEB)
    await wait(event_id, DINA)
    await act(lectures.leave_waitlist, gleb, GLEB)

    await act(lectures.remove_listener, regs[1], ORGANIZER)

    assert await attendees(event_id) == [ANNA, VERA, DINA]


async def test_only_listener_cancels_own_registration() -> None:
    event_id = await new_event()
    reg_id = await register(event_id, ANNA)
    with pytest.raises(AccessDenied):
        await act(lectures.cancel_registration, reg_id, BORIS)
    with pytest.raises(AccessDenied):
        await act(lectures.remove_listener, reg_id, ORGANIZER_2)


async def test_organizer_adds_seats_for_waitlist() -> None:
    event_id = await new_event(capacity=2)
    await fill(event_id, (ANNA, BORIS))
    for listener in (VERA, GLEB, DINA):
        await wait(event_id, listener)

    await act(lectures.change_capacity, event_id, ORGANIZER, 4)

    assert await attendees(event_id) == [ANNA, BORIS, VERA, GLEB]
    assert await kinds(DINA) == []


async def test_move_to_other_venue_cancels_registrations_and_notifies() -> None:
    event_id = await new_event(venue=ROOM)
    regs = await fill(event_id, (ANNA, BORIS, VERA))
    gleb = await wait(event_id, GLEB)

    await act(lectures.move_event, event_id, ORGANIZER, venue_id=LOFT)

    moved = await lecture(event_id)
    assert (moved.venue_id, moved.capacity) == (LOFT, 10)
    assert await attendees(event_id) == []
    for reg_id in regs:
        assert (await registration(reg_id)).cancel_reason == "venue_changed"
    for listener in (ANNA, BORIS, VERA):
        assert await kinds(listener) == ["registered", "event_moved"]
    # Лист ожидания относился к прежней площадке: никого не переводим, всех уведомляем.
    assert (await waitlist_entry(gleb)).status == "cancelled"
    assert await kinds(GLEB) == ["event_moved"]


async def test_new_registrations_after_move_go_to_new_venue() -> None:
    event_id = await new_event(venue=ROOM)
    await fill(event_id, (ANNA, BORIS))
    await act(lectures.move_event, event_id, ORGANIZER, venue_id=LOFT, capacity=4)
    await register(event_id, EGOR)
    await register(event_id, ANNA)
    assert await attendees(event_id) == [EGOR, ANNA]
    assert (await lecture(event_id)).capacity_manual is True


async def test_move_capacity_above_new_limit_rejected() -> None:
    event_id = await new_event(venue=LOFT)
    reg_id = await register(event_id, ANNA)
    with pytest.raises(DBAPIError, match="exceeds venue"):
        await act(lectures.move_event, event_id, ORGANIZER, venue_id=ROOM, capacity=6)
    assert (await registration(reg_id)).status == "confirmed"
    assert (await lecture(event_id)).venue_id == LOFT


async def test_cancel_event_notifies_registered_and_waitlisted() -> None:
    event_id = await new_event(venue=ROOM)
    await fill(event_id, (ANNA, BORIS, VERA))
    await wait(event_id, GLEB)

    await act(lectures.cancel_event, event_id, ORGANIZER)

    assert (await lecture(event_id)).status == "cancelled"
    assert await attendees(event_id) == []
    assert (await kinds(ANNA))[-1] == "event_cancelled"
    assert await kinds(GLEB) == ["event_cancelled"]
    with pytest.raises(DomainError, match="закрыта"):
        await register(event_id, DINA)


async def test_redelivered_event_does_not_duplicate_notice() -> None:
    event_id = await new_event()
    reg_id = await register(event_id, ANNA)
    payload = {"registration_id": reg_id, "event_id": event_id, "listener_id": ANNA}
    async with db.sessionmaker().begin() as s:
        await consumers.on_registration_created(s, payload)
    assert await kinds(ANNA) == ["registered"]


async def test_database_refuses_overbooking() -> None:
    event_id = await new_event(venue=ROOM)
    await fill(event_id, LISTENERS[:3])
    with pytest.raises(DBAPIError, match="is full"):
        async with db.sessionmaker().begin() as s:
            s.add(
                Registration(event_id=event_id, listener_id=EGOR, status="confirmed", created_at=clock.now())
            )
