from datetime import timedelta

import pytest
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.lectures import service as lectures
from services.lectures.models import VenueCapacityLimit
from tests.factories import T0, act, travel
from tests.lectures_factories import (
    ANNA,
    BORIS,
    EVENING,
    HALL,
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
    set_limit,
    venues,
    wait,
)


@pytest.fixture(autouse=True)
async def _venues() -> None:
    await venues()


async def test_event_takes_venue_limit_by_default() -> None:
    event_id = await new_event(venue=ROOM)
    created = await lecture(event_id)
    assert created.capacity == 3
    assert created.capacity_manual is False
    assert created.status == "scheduled"


async def test_event_announced_at_least_a_day_ahead() -> None:
    with pytest.raises(DomainError, match="за сутки"):
        await new_event(starts_at=T0 + timedelta(hours=5))


async def test_event_on_venue_without_limit_rejected() -> None:
    with pytest.raises(DomainError, match="не задан лимит"):
        await new_event(venue=99)


async def test_capacity_above_venue_limit_rejected_by_db() -> None:
    with pytest.raises(DBAPIError, match="exceeds venue"):
        await new_event(venue=ROOM, capacity=4)


async def test_venue_cannot_host_two_events_at_once() -> None:
    await new_event()
    with pytest.raises(DomainError, match="занята"):
        await new_event(organizer=ORGANIZER_2, title="Другая лекция")
    await new_event(starts_at=EVENING + timedelta(hours=2))


async def test_only_organizer_changes_capacity() -> None:
    event_id = await new_event()
    with pytest.raises(AccessDenied):
        await act(lectures.change_capacity, event_id, ORGANIZER_2, 2)


async def test_capacity_cannot_drop_below_registered() -> None:
    event_id = await new_event()
    await fill(event_id, (ANNA, BORIS, VERA))
    with pytest.raises(DomainError, match="больше слушателей"):
        await act(lectures.change_capacity, event_id, ORGANIZER, 2)
    await act(lectures.change_capacity, event_id, ORGANIZER, 3)
    assert (await lecture(event_id)).capacity_manual is True


async def test_limit_change_updates_replica_and_untouched_events() -> None:
    default = await new_event()
    reduced = await new_event(starts_at=EVENING + timedelta(days=1), capacity=4)
    other_venue = await new_event(venue=LOFT)

    await set_limit(HALL, 8)

    async with db.sessionmaker()() as s:
        assert (await s.get(VenueCapacityLimit, HALL)).max_capacity == 8
    assert (await lecture(default)).capacity == 8
    assert (await lecture(reduced)).capacity == 4
    assert (await lecture(other_venue)).capacity == 10


async def test_limit_change_skips_past_and_cancelled_events() -> None:
    past = await new_event()
    cancelled = await new_event(starts_at=EVENING + timedelta(days=2))
    await act(lectures.cancel_event, cancelled, ORGANIZER)
    travel(EVENING + timedelta(hours=1))

    await set_limit(HALL, 7)

    assert (await lecture(past)).capacity == 5
    assert (await lecture(cancelled)).capacity == 5


async def test_manual_capacity_kept_even_when_it_matches_old_limit() -> None:
    tracking = await new_event()
    manual = await new_event(starts_at=EVENING + timedelta(days=1))
    await act(lectures.change_capacity, manual, ORGANIZER, 3)

    await set_limit(HALL, 3)
    assert (await lecture(tracking)).capacity == 3
    assert (await lecture(manual)).capacity == 3

    await set_limit(HALL, 6)
    assert (await lecture(tracking)).capacity == 6
    assert (await lecture(manual)).capacity == 3


async def test_restoring_full_capacity_follows_limit_again() -> None:
    event_id = await new_event()
    await act(lectures.change_capacity, event_id, ORGANIZER, 2)
    await act(lectures.change_capacity, event_id, ORGANIZER, 5)
    assert (await lecture(event_id)).capacity_manual is False

    await set_limit(HALL, 9)
    assert (await lecture(event_id)).capacity == 9


async def test_limit_increase_gives_new_seats_to_waitlist() -> None:
    await set_limit(ROOM, 2)
    event_id = await new_event(venue=ROOM)
    await fill(event_id, (ANNA, BORIS))
    await wait(event_id, VERA)

    await set_limit(ROOM, 3)

    assert await attendees(event_id) == [ANNA, BORIS, VERA]
    assert await kinds(VERA) == ["waitlist_promoted"]
