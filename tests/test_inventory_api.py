import httpx
import pytest

from libs import events
from services.inventory.app import app
from tests import inventory_factories as inv
from tests.factories import BOOK_L1, KZN, MSK


@pytest.fixture(autouse=True)
async def custodians(world: None) -> None:
    await inv.staff()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://inventory") as c:
        yield c


async def test_register_and_read_stock(client: httpx.AsyncClient) -> None:
    body = {"custodian_id": inv.KEEPER[MSK], "venue_id": MSK, "book_ref": BOOK_L1, "inventory_no": "ПР-00001"}
    r = await client.post("/copies", json=body)
    assert r.status_code == 201
    assert r.json()["state"] == "available"
    await events.dispatch_pending()
    r = await client.get(f"/venues/{MSK}/stock/{BOOK_L1}")
    assert r.json() == {"total": 1, "available": 1}

    r = await client.post("/copies", json=body | {"venue_id": KZN, "custodian_id": inv.KEEPER[KZN]})
    assert r.status_code == 409


async def test_lend_and_return_over_http(client: httpx.AsyncClient) -> None:
    copy_id = await inv.copy()
    partner_id = await inv.partner()
    r = await client.post(
        "/ill-loans", json={"custodian_id": inv.KEEPER[MSK], "copy_id": copy_id, "partner_id": partner_id}
    )
    assert r.status_code == 201
    loan_id = r.json()["id"]
    r = await client.post(
        f"/copies/{copy_id}/transfers", json={"custodian_id": inv.KEEPER[MSK], "to_venue_id": KZN}
    )
    assert r.status_code == 409
    r = await client.post(f"/ill-loans/{loan_id}/return", json={"custodian_id": inv.KEEPER[MSK]})
    assert r.json()["status"] == "returned"
    r = await client.get("/copies/999999")
    assert r.status_code == 404
