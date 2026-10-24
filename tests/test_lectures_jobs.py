from datetime import timedelta

import httpx
import pytest

from libs import events
from services.lectures import jobs
from services.lectures.app import app
from tests.factories import act
from tests.lectures_factories import (
    ANNA,
    BORIS,
    EVENING,
    GLEB,
    HALL,
    ORGANIZER,
    ROOM,
    VERA,
    fill,
    kinds,
    lecture,
    new_event,
    register,
    venues,
    wait,
    waitlist_entry,
)


@pytest.fixture(autouse=True)
async def _venues() -> None:
    await venues()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://lectures") as c:
        yield c


async def test_waitlist_expires_when_registration_closes() -> None:
    event_id = await new_event(venue=ROOM)
    await fill(event_id, (ANNA, BORIS, VERA))
    entry = await wait(event_id, GLEB)

    assert await act(jobs.close_waitlists, EVENING - timedelta(hours=2)) == []
    assert await act(jobs.close_waitlists, EVENING - timedelta(minutes=30)) == [entry]

    assert (await waitlist_entry(entry)).status == "expired"
    assert await kinds(GLEB) == ["waitlist_expired"]


async def test_reminder_sent_once_a_day_ahead() -> None:
    soon = await new_event()
    later = await new_event(starts_at=EVENING + timedelta(days=3))
    await register(soon, ANNA)
    await register(later, ANNA)

    now = EVENING - timedelta(hours=20)
    assert await act(jobs.send_reminders, now) == 1
    await act(jobs.send_reminders, now + timedelta(hours=1))

    assert await kinds(ANNA) == ["registered", "registered", "reminder"]
    assert (await lecture(soon)).status == "scheduled"


async def test_past_events_finished() -> None:
    event_id = await new_event()
    assert await act(jobs.finish_past_events, EVENING + timedelta(hours=1)) == []
    assert await act(jobs.finish_past_events, EVENING + timedelta(hours=3)) == [event_id]
    assert (await lecture(event_id)).status == "finished"


async def test_api_flow(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/events",
        json={
            "organizer_id": ORGANIZER,
            "title": "Открытая лекция",
            "venue_id": HALL,
            "starts_at": EVENING.isoformat(),
            "capacity": 1,
        },
    )
    assert r.status_code == 201
    event_id = r.json()["event_id"]

    r = await client.post(f"/events/{event_id}/registrations", json={"listener_id": ANNA})
    assert r.status_code == 201
    registration_id = r.json()["registration_id"]
    r = await client.post(f"/events/{event_id}/registrations", json={"listener_id": BORIS})
    assert r.status_code == 409
    r = await client.post(f"/events/{event_id}/waitlist", json={"listener_id": BORIS})
    assert r.json()["position"] == 1

    r = await client.delete(f"/registrations/{registration_id}", params={"listener_id": BORIS})
    assert r.status_code == 403
    r = await client.delete(f"/registrations/{registration_id}", params={"listener_id": ANNA})
    assert r.status_code == 200

    r = await client.put(f"/venues/{HALL}/capacity-limit", json={"max_capacity": 2})
    assert r.status_code == 202
    await events.dispatch_pending()

    r = await client.put(f"/events/{event_id}/capacity", json={"organizer_id": ORGANIZER, "capacity": 3})
    assert r.status_code == 409
    assert "exceeds venue" in r.json()["detail"]
    r = await client.get("/events", params={"venue_id": HALL})
    assert [(e["id"], e["capacity"], e["free_seats"]) for e in r.json()] == [(event_id, 1, 0)]
    r = await client.get(f"/listeners/{BORIS}/notifications")
    assert [n["kind"] for n in r.json()] == ["waitlist_promoted"]
