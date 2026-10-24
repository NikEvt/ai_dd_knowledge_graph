import httpx
import pytest

from libs import events
from services.halls.app import app
from tests.halls_factories import (
    ACCOUNTANT,
    CENTER,
    EVENT_END,
    EVENT_START,
    MANAGER,
    PANORAMA_HALL,
    email_types,
    seed_halls,
)


@pytest.fixture(autouse=True)
async def halls_data(world: None) -> None:
    await seed_halls()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://halls") as c:
        yield c


async def test_booking_lifecycle_over_http(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/bookings",
        json={
            "manager_id": MANAGER[CENTER],
            "hall_id": 1,
            "client_ref": "client:anna",
            "event_kind": "birthday",
            "guests": 30,
            "starts_at": EVENT_START.isoformat(),
            "ends_at": EVENT_END.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert (created["status"], created["amount"]) == ("draft", "20000.00")

    r = await client.post(
        f"/invoices/{created['invoice_id']}/payments",
        json={"amount": "20000", "recorded_by": ACCOUNTANT, "external_ref": "bank-1"},
    )
    assert r.status_code == 201
    await events.dispatch_pending()

    r = await client.get(f"/bookings/{created['id']}")
    assert (r.json()["status"], r.json()["paid"]) == ("confirmed", "20000.00")
    assert await email_types(created["id"]) == ["invoice", "confirmed"]

    r = await client.post(
        f"/bookings/{created['id']}/venue", json={"manager_id": MANAGER[CENTER], "hall_id": PANORAMA_HALL}
    )
    assert r.status_code == 409
    assert "до подтверждения" in r.json()["detail"]

    r = await client.delete(f"/bookings/{created['id']}", params={"manager_id": 999})
    assert r.status_code == 403
