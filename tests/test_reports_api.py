import httpx
import pytest

from libs import events
from services.reports.app import app
from tests.reports_factories import ANALYST, ANALYST_2, LOANS, MANAGER


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://reports") as c:
        yield c


async def _definition(client: httpx.AsyncClient, code: str = "loans-weekly") -> int:
    r = await client.post(
        "/reports/definitions",
        json={
            "owner_id": ANALYST,
            "code": code,
            "title": f"Отчёт {code}",
            "kind": "metric_summary",
            "params": {"metrics": [LOANS]},
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_run_requested_then_built(client: httpx.AsyncClient) -> None:
    r = await client.post("/reports/snapshots", json={"metric": LOANS, "value": "12.5"})
    assert r.status_code == 201
    def_id = await _definition(client)

    r = await client.post(f"/reports/definitions/{def_id}/runs", json={"requested_by": ANALYST})
    assert r.status_code == 202
    queued = r.json()
    assert queued["status"] == "requested" and queued["body"] is None

    await events.dispatch_pending()
    r = await client.get(f"/reports/runs/{queued['id']}")
    assert r.status_code == 200
    done = r.json()
    assert done["id"] == queued["id"]
    assert done["status"] == "completed"
    assert done["body"]["metrics"][LOANS]["total"] == "12.50"

    r = await client.get("/reports/notifications", params={"recipient_id": ANALYST, "unread_only": True})
    [note] = r.json()
    r = await client.post(f"/reports/notifications/{note['id']}/read", params={"recipient_id": MANAGER})
    assert r.status_code == 403
    r = await client.post(f"/reports/notifications/{note['id']}/read", params={"recipient_id": ANALYST})
    assert r.json()["read"] is True


async def test_list_runs_filters(client: httpx.AsyncClient) -> None:
    await client.post("/reports/snapshots", json={"metric": LOANS, "value": 1})
    first, second = await _definition(client, "first"), await _definition(client, "second")
    for def_id, who in ((first, ANALYST), (second, ANALYST), (first, ANALYST_2)):
        r = await client.post(f"/reports/definitions/{def_id}/runs", json={"requested_by": who})
        assert r.status_code == 202
    await events.dispatch_pending()
    pending = await client.post(f"/reports/definitions/{second}/runs", json={"requested_by": ANALYST_2})

    r = await client.get("/reports/runs", params={"definition_id": first})
    assert len(r.json()) == 2
    r = await client.get("/reports/runs", params={"requested_by": ANALYST_2, "status": "requested"})
    assert [x["id"] for x in r.json()] == [pending.json()["id"]]
    r = await client.get("/reports/runs", params={"status": "completed", "limit": 2})
    assert [set(x) >= {"id", "status", "body"} for x in r.json()] == [True, True]


async def test_errors_mapped_to_http(client: httpx.AsyncClient) -> None:
    def_id = await _definition(client)
    assert (await client.get("/reports/runs/999")).status_code == 404
    r = await client.post(f"/reports/definitions/{def_id}/runs", json={"requested_by": ANALYST})
    run_id = r.json()["id"]

    r = await client.post(f"/reports/runs/{run_id}/cancel", params={"by": ANALYST_2})
    assert r.status_code == 403
    r = await client.post(f"/reports/definitions/{def_id}/runs", json={"requested_by": ANALYST})
    assert r.status_code == 409
    assert "незавершённый запуск" in r.json()["detail"]
    r = await client.post(f"/reports/runs/{run_id}/cancel", params={"by": ANALYST})
    assert r.json()["status"] == "cancelled"
