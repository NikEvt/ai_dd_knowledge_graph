import httpx
import pytest

from libs import events
from services.partners.app import app
from services.partners.models import OnboardingRequest
from tests.partners_factories import MANAGER, MANAGER_2, active_contract, get, make_inn


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://partners") as c:
        yield c


async def call(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    r = await client.request(method, url, **kwargs)
    await events.dispatch_pending()
    return r


async def test_partner_connected_through_api(client: httpx.AsyncClient) -> None:
    r = await call(
        client,
        "POST",
        "/partners/requests",
        json={"inn": make_inn(), "contact_name": "Олег", "contact_email": "oleg@example.org"},
    )
    assert r.status_code == 201
    request_id = r.json()["request_id"]
    r = await call(client, "POST", f"/partners/requests/{request_id}/decision", json={"manager_id": MANAGER})
    assert r.json() == {"status": "approved"}
    partner_id = (await get(OnboardingRequest, request_id)).partner_id

    r = await call(client, "POST", "/contracts/1/activate", params={"manager_id": MANAGER})
    assert r.status_code == 409
    assert "КПП, наименование" in r.json()["detail"]

    r = await call(
        client,
        "PATCH",
        f"/partners/{partner_id}/requisites",
        json={"manager_id": MANAGER, "kpp": "770101001", "legal_name": "ООО «Агент»"},
    )
    assert r.json() == {"missing": []}
    r = await call(client, "POST", "/contracts/1/activate", params={"manager_id": MANAGER})
    assert r.json() == {"status": "active"}

    r = await call(
        client,
        "POST",
        "/contracts/1/deals",
        json={"manager_id": MANAGER, "external_ref": "A-1", "amount": "10"},
    )
    assert r.json()["status"] == "awaiting_prepayment"


async def test_credit_limit_and_commissions_via_api(client: httpx.AsyncClient) -> None:
    partner_id, contract_id = await active_contract(credit_limit=1000)
    r = await call(
        client,
        "POST",
        f"/contracts/{contract_id}/deals",
        json={"manager_id": MANAGER, "external_ref": "C-1", "amount": "800"},
    )
    assert r.json()["status"] == "open"
    deal_id = r.json()["deal_id"]

    r = await call(
        client,
        "POST",
        f"/contracts/{contract_id}/deals",
        json={"manager_id": MANAGER, "external_ref": "C-2", "amount": "300"},
    )
    assert r.status_code == 409
    assert "credit limit" in r.json()["detail"]

    await call(client, "POST", f"/deals/{deal_id}/close", params={"manager_id": MANAGER})
    r = await call(client, "GET", f"/partners/{partner_id}/commissions")
    assert [c["amount"] for c in r.json()] == ["880.00"]
    r = await call(client, "GET", f"/contracts/{contract_id}")
    assert r.json()["credit_used"] == "800.00"

    r = await call(client, "POST", f"/deals/{deal_id}/payment")
    assert r.status_code == 200
    r = await call(client, "GET", f"/partners/{partner_id}/payouts")
    assert [(p["total"], p["commissions"], p["status"]) for p in r.json()] == [("880.00", 1, "open")]


async def test_contract_terms_through_api(client: httpx.AsyncClient) -> None:
    _, contract_id = await active_contract()
    r = await call(
        client, "PUT", f"/contracts/{contract_id}/rate", json={"manager_id": MANAGER, "commission_pct": "50"}
    )
    assert r.status_code == 409
    r = await call(
        client, "PUT", f"/contracts/{contract_id}/rate", json={"manager_id": MANAGER_2, "commission_pct": "5"}
    )
    assert r.status_code == 403
    await call(
        client, "PUT", f"/contracts/{contract_id}/rate", json={"manager_id": MANAGER, "commission_pct": "5"}
    )
    await call(
        client,
        "PUT",
        f"/contracts/{contract_id}/credit",
        json={"manager_id": MANAGER, "allowed": True, "limit": "2500"},
    )
    r = await call(client, "GET", f"/contracts/{contract_id}/history")
    assert [(h["field"], h["new_value"]) for h in r.json()] == [
        ("status", "active"),
        ("commission_pct", "5.00"),
        ("credit_allowed", "true"),
        ("credit_limit", "2500.00"),
    ]
    r = await call(
        client,
        "POST",
        f"/contracts/{contract_id}/termination",
        json={"manager_id": MANAGER, "reason": "по соглашению сторон"},
    )
    assert r.json() == {"status": "terminated"}
    r = await call(client, "GET", "/contracts/999")
    assert r.status_code == 404
