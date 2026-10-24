import httpx
import pytest

from libs.events import dispatch_pending
from services.subscriptions.app import app
from tests.subscriptions_factories import CLIENT_1, CLIENT_2, PASSPORT, plans


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://subs") as c:
        yield c


async def test_subscribe_and_pay_over_api(client: httpx.AsyncClient) -> None:
    p = await plans()
    r = await client.get("/plans")
    assert [x["code"] for x in r.json()] == ["soc", "corp", "std", "std-plus"]

    r = await client.post(
        "/subscriptions",
        json={
            "client_ref": CLIENT_1,
            "plan_id": p["std"],
            "holder_name": "Анна Петрова",
            "passport": PASSPORT,
            "birth_date": "1990-05-01",
        },
    )
    assert r.status_code == 201
    sub_id, invoice_id = r.json()["subscription_id"], r.json()["invoice_id"]

    r = await client.post(f"/invoices/{invoice_id}/payments", json={"amount": "600.00"})
    assert r.status_code == 201
    await dispatch_pending()

    r = await client.get(f"/subscriptions/{sub_id}")
    assert r.json()["status"] == "active"
    assert r.json()["paid_until"] == "2026-04-01"
    assert r.json()["holder_check"] == "verified"

    r = await client.get(f"/clients/{CLIENT_1}/subscriptions")
    assert [x["id"] for x in r.json()] == [sub_id]


async def test_api_maps_domain_errors(client: httpx.AsyncClient) -> None:
    p = await plans()
    r = await client.post(
        "/subscriptions", json={"client_ref": CLIENT_1, "plan_id": p["std"], "holder_name": "Анна"}
    )
    sub_id, invoice_id = r.json()["subscription_id"], r.json()["invoice_id"]

    r = await client.put(f"/subscriptions/{sub_id}/holder", json={"client_ref": CLIENT_2, "holder_name": "X"})
    assert r.status_code == 403

    r = await client.post(f"/invoices/{invoice_id}/payments", json={"amount": "1000"})
    assert r.status_code == 409
    assert "остатка" in r.json()["detail"]

    r = await client.get("/subscriptions/999")
    assert r.status_code == 404
