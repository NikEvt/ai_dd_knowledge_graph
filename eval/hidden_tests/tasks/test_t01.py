"""T01: смена площадки социальной заявки после формирования ссылки на запись (до выдачи книг)."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from support import (
    CHECKER,
    HISTORY,
    KZN,
    MSK,
    OPERATOR,
    REP_DEBT,
    T0,
    act,
    application,
    book,
    issue,
    new_application,
    pass_review,
    slot,
    token,
)

from libs import db
from services.applications import service as apps
from services.chat.models import Message
from services.notifications.models import Email
from services.scheduling.models import Booking, Hold


async def _rows(model, app_id):
    order = model.id if hasattr(model, "id") else model.book_id
    async with db.sessionmaker()() as s:
        query = select(model).where(model.application_id == app_id).order_by(order)
        return list((await s.scalars(query)).all())


async def test_t01_social_venue_change_after_link() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    old_token = await token(app_id)
    assert old_token is not None

    await act(apps.change_venue, app_id, OPERATOR, KZN)

    app = await application(app_id)
    assert app.venue_id == KZN
    assert app.site_checker_id == CHECKER[KZN]
    new_token = await token(app_id)
    assert new_token is not None and new_token != old_token


async def test_t01_social_venue_change_cancels_booking_and_notifies() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    await book(app_id, slot_id)

    await act(apps.change_venue, app_id, OPERATOR, KZN)

    [booking] = await _rows(Booking, app_id)
    assert booking.status == "cancelled"
    assert await _rows(Hold, app_id) == []
    emails = await _rows(Email, app_id)
    assert [e.type for e in emails] == ["booking", "cancel"]
    assert emails[-1].status == "sent"
    assert emails[-1].body.startswith("V1 social cancel")
    chat = [m.body for m in await _rows(Message, app_id) if m.is_event]
    assert f"Площадка изменена: {MSK} → {KZN}" in chat


async def test_t01_social_venue_change_forbidden_after_issue() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    await issue(app_id)
    with pytest.raises(Exception):  # noqa: B017
        await act(apps.change_venue, app_id, OPERATOR, KZN)
    assert (await application(app_id)).venue_id == MSK


async def test_t01_debt_rule_unchanged() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    with pytest.raises(Exception):  # noqa: B017
        await act(apps.change_venue, app_id, OPERATOR, KZN)
    assert (await application(app_id)).venue_id == MSK
