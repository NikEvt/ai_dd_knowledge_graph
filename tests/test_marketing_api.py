from datetime import timedelta

import httpx
import pytest

from libs import events
from services.marketing import jobs
from services.marketing.app import app
from services.marketing.settings import MAX_TEST_MESSAGES
from tests import marketing_factories as mf
from tests.factories import T0, act, travel


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://marketing") as c:
        yield c


@pytest.fixture(autouse=True)
async def staff() -> None:
    await mf.staff()


async def _campaign(client: httpx.AsyncClient) -> int:
    await mf.templates()
    r = await client.post(
        "/marketing/audiences", json={"manager_id": mf.MANAGER, "venue_id": mf.VENUE, "name": "Читатели"}
    )
    assert r.status_code == 201
    audience_id = r.json()["audience_id"]
    for email, full_name, segment in mf.READERS:
        r = await client.post(
            f"/marketing/audiences/{audience_id}/members",
            json={"manager_id": mf.MANAGER, "email": email, "full_name": full_name, "segment": segment},
        )
        assert r.status_code == 201
    r = await client.post(
        "/marketing/campaigns",
        json={"manager_id": mf.MANAGER, "audience_id": audience_id, "type": "newsletter", "subject": "Акция"},
    )
    assert r.status_code == 201
    return r.json()["campaign_id"]


async def test_test_message_then_campaign_messages(client: httpx.AsyncClient) -> None:
    campaign_id = await _campaign(client)
    r = await client.post(
        f"/marketing/campaigns/{campaign_id}/messages/test",
        json={"manager_id": mf.MANAGER, "email": "qa@example.org", "full_name": "Тестер", "segment": "vip"},
    )
    assert r.status_code == 201
    assert r.json()["body"] == "[1/vip] Акция. Здравствуйте, Тестер!"
    assert set(r.json()) == {"id", "body", "sent_at"}

    r = await client.post(f"/marketing/campaigns/{campaign_id}/launch", params={"manager_id": mf.MANAGER})
    assert r.status_code == 200
    assert r.json()["status"] == "preparing"
    await events.dispatch_pending()

    r = await client.get(f"/marketing/campaigns/{campaign_id}/messages", params={"manager_id": mf.MANAGER})
    assert r.status_code == 200
    bodies = [m["body"] for m in r.json()]
    assert bodies[0] == "[1/vip] Акция. Здравствуйте, Тестер!"
    assert "[1/paid] Акция. Здравствуйте, Анна Петрова!" in bodies
    assert len(bodies) == 4
    assert all(m["sent_at"] == T0.isoformat().replace("+00:00", "Z") for m in r.json())

    r = await client.post(
        f"/marketing/campaigns/{campaign_id}/messages/test",
        json={"manager_id": mf.MANAGER, "email": "qa@example.org"},
    )
    assert r.status_code == 409
    assert "до запуска кампании" in r.json()["detail"]


async def test_test_messages_are_limited_and_purged(client: httpx.AsyncClient) -> None:
    campaign_id = await _campaign(client)
    url = f"/marketing/campaigns/{campaign_id}/messages/test"
    for n in range(MAX_TEST_MESSAGES):
        r = await client.post(url, json={"manager_id": mf.MANAGER, "email": f"qa{n}@example.org"})
        assert r.status_code == 201
    r = await client.post(url, json={"manager_id": mf.MANAGER, "email": "qa@example.org"})
    assert r.status_code == 409
    assert "тестовых писем" in r.json()["detail"]

    assert await act(jobs.purge_test_messages, T0 + timedelta(days=13)) == 0
    travel(T0 + timedelta(days=15))
    assert await act(jobs.purge_test_messages, T0 + timedelta(days=15)) == MAX_TEST_MESSAGES
    r = await client.get(f"/marketing/campaigns/{campaign_id}/messages", params={"manager_id": mf.MANAGER})
    assert r.json() == []


async def test_access_and_missing_campaign(client: httpx.AsyncClient) -> None:
    campaign_id = await _campaign(client)
    r = await client.get(f"/marketing/campaigns/{campaign_id}/messages", params={"manager_id": mf.MANAGER_2})
    assert r.status_code == 403
    r = await client.get("/marketing/campaigns/999/messages", params={"manager_id": mf.MANAGER})
    assert r.status_code == 404
    assert r.json()["detail"] == "кампания 999"
    template = {"manager_id": mf.MANAGER, "venue_id": mf.VENUE, "type": "promo", "body": "x"}
    r = await client.put("/marketing/templates", json={**template, "audience_group": "debt"})
    assert r.status_code == 409


async def test_schedule_cancel_and_report(client: httpx.AsyncClient) -> None:
    campaign_id = await _campaign(client)
    url = f"/marketing/campaigns/{campaign_id}"
    params = {"manager_id": mf.MANAGER}

    for at, status in ((T0 - timedelta(hours=1), 409), (T0 + timedelta(days=1), 200)):
        r = await client.post(
            f"{url}/schedule", json={"manager_id": mf.MANAGER, "scheduled_at": at.isoformat()}
        )
        assert r.status_code == status
    assert r.json()["status"] == "scheduled"
    assert r.json()["scheduled_at"].startswith("2026-03-03T09:00")

    r = await client.post("/marketing/audiences/1/archive", params=params)
    assert r.status_code == 409
    r = await client.post(f"{url}/cancel", params=params)
    assert r.json()["status"] == "cancelled"
    r = await client.post("/marketing/audiences/1/archive", params=params)
    assert r.status_code == 204

    # отчёт по запущенной кампании разбивает пропуски по причинам
    await mf.template("vip", type_="event")
    launched = await mf.launched(await mf.audience("Гости вечера"), type_="event")
    r = await client.get(f"/marketing/campaigns/{launched}", params=params)
    assert r.status_code == 200
    report = r.json()
    assert (report["status"], report["recipients_count"], report["sent_count"]) == ("sent", 3, 1)
    assert report["skipped_by_reason"] == {"no_template": 2}


async def test_unsubscribe_and_bounce_endpoints(client: httpx.AsyncClient) -> None:
    campaign_id = await _campaign(client)
    r = await client.post("/marketing/unsubscribe", json={"email": "Boris@Example.org"})
    assert r.status_code == 204
    await events.dispatch_pending()
    assert [m.opted_out for m in await mf.members("boris@example.org")] == [True]

    await client.post(f"/marketing/campaigns/{campaign_id}/launch", params={"manager_id": mf.MANAGER})
    await events.dispatch_pending()
    sent = await mf.messages(campaign_id)
    assert set(sent) == {"anna@example.org", "vika@example.org"}

    r = await client.post(f"/marketing/messages/{sent['anna@example.org'].id}/bounce")
    assert r.status_code == 204
    r = await client.post("/marketing/messages/999/bounce")
    assert r.status_code == 404
