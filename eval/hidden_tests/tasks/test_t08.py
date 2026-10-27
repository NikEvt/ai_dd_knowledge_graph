"""T08: в API чата поле body переименовано в text (запрос и ответ)."""

import httpx
import pytest
from support import OPERATOR, new_application

from services.chat.app import app


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://chat") as c:
        yield c


async def test_t08_post_and_list_use_text(client: httpx.AsyncClient) -> None:
    app_id = await new_application()
    r = await client.post(f"/applications/{app_id}/messages", json={"author_id": OPERATOR, "text": "Привет"})
    assert r.status_code == 201
    assert r.json()["text"] == "Привет"
    r = await client.get(f"/applications/{app_id}/messages",
                         params={"viewer_id": OPERATOR, "role": "operator"})
    last = r.json()[-1]
    assert last["text"] == "Привет"
    assert "body" not in last
