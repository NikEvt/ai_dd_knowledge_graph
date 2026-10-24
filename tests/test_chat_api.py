import httpx
import pytest

from services.chat.app import app
from tests.factories import ADMIN, CHIEF, OPERATOR, REVIEWER, new_application, pass_review


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://chat") as c:
        yield c


async def test_operator_posts_and_reads(client: httpx.AsyncClient) -> None:
    app_id = await new_application()
    r = await client.post(f"/applications/{app_id}/messages", json={"author_id": OPERATOR, "body": "Привет"})
    assert r.status_code == 201
    r = await client.get(
        f"/applications/{app_id}/messages", params={"viewer_id": OPERATOR, "role": "operator"}
    )
    assert r.status_code == 200
    assert r.json()[-1]["body"] == "Привет"
    assert r.json()[-1]["is_event"] is False


async def test_stage_changes_appear_in_chat(client: httpx.AsyncClient) -> None:
    app_id = await new_application()
    await pass_review(app_id)
    r = await client.get(
        f"/applications/{app_id}/messages", params={"viewer_id": REVIEWER, "role": "reviewer"}
    )
    events = [m["body"] for m in r.json() if m["is_event"]]
    assert "Этап: draft → on_review" in events
    assert "Этап: on_review → awaiting_invoice" in events


async def test_admin_reads_chief_accountant_does_not(client: httpx.AsyncClient) -> None:
    app_id = await new_application()
    r = await client.get(f"/applications/{app_id}/messages", params={"viewer_id": ADMIN, "role": "admin"})
    assert r.status_code == 200
    r = await client.get(
        f"/applications/{app_id}/messages", params={"viewer_id": CHIEF, "role": "chief_accountant"}
    )
    assert r.status_code == 403


async def test_outsider_cannot_post(client: httpx.AsyncClient) -> None:
    app_id = await new_application()
    r = await client.post(f"/applications/{app_id}/messages", json={"author_id": 999, "body": "x"})
    assert r.status_code == 403
