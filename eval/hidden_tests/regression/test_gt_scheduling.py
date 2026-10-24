"""Регрессия: расписание, запись, письма, чат."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update
from support import (
    CHECKER,
    HISTORY,
    MSK,
    REP_DEBT,
    T0,
    TVR,
    act,
    book,
    new_application,
    paid_application,
    pass_review,
    slot,
    travel,
)

from libs import db
from libs.errors import AccessDenied, DomainError
from services.applications import admin
from services.chat import service as chat
from services.chat.models import Message
from services.notifications.models import Email
from services.scheduling import service as scheduling


async def _emails(app_id):
    async with db.sessionmaker()() as s:
        return list((await s.scalars(select(Email).where(Email.application_id == app_id).order_by(Email.id))).all())


async def test_gt_slot_capacity_limited_by_venue_max() -> None:
    with pytest.raises(Exception, match="exceeds venue maximum"):
        await slot(MSK, HISTORY, T0 + timedelta(days=5), capacity=4)


async def test_gt_admin_max_capacity_reaches_scheduling() -> None:
    await act(admin.set_venue_max_capacity, TVR, 6)
    slot_id = await slot(TVR, HISTORY, T0 + timedelta(days=5), capacity=6)
    assert slot_id


async def test_gt_checker_only_own_venue() -> None:
    with pytest.raises(AccessDenied):
        await act(
            scheduling.create_slot,
            site_checker_id=CHECKER[TVR],
            venue_id=MSK,
            sphere_id=HISTORY,
            starts_at=T0 + timedelta(days=5),
        )


async def test_gt_booking_holds_books_until_issue() -> None:
    app_id = await new_application(rep=REP_DEBT, books=(1, 2))
    await pass_review(app_id)
    await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    from services.scheduling.models import Hold

    async with db.sessionmaker()() as s:
        held = (await s.scalars(select(Hold.book_id).where(Hold.application_id == app_id))).all()
    assert sorted(held) == [1, 2]


async def test_gt_operator_can_cancel_late() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    booking_id = await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=3)))
    travel(T0 + timedelta(days=2, hours=12))
    with pytest.raises(DomainError):
        await act(scheduling.cancel_booking, booking_id, by="representative")
    await act(scheduling.cancel_booking, booking_id, by="operator")


async def test_gt_removed_slot_cancels_booking_with_email() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    await book(app_id, slot_id)
    await act(scheduling.remove_slot, slot_id, CHECKER[MSK])
    assert [e.type for e in await _emails(app_id)] == ["booking", "cancel"]


async def test_gt_debt_uses_paid_templates() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    [email] = await _emails(app_id)
    assert email.body.startswith("V1 paid booking")


async def test_gt_no_show_sends_cancel_email() -> None:
    app_id, _ = await paid_application()
    booking_id = await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=3)))
    travel(T0 + timedelta(days=3, hours=2))
    await act(scheduling.mark_no_show, booking_id, CHECKER[MSK])
    assert [e.type for e in await _emails(app_id)] == ["booking", "cancel"]


async def test_gt_archive_releases_booking() -> None:
    app_id, inv = await paid_application()
    booking_id = await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    from services.billing import service as billing
    from services.billing.models import Payment

    async with db.sessionmaker()() as s:
        payment = await s.scalar(select(Payment).where(Payment.invoice_id == inv.id))
    await act(billing.refund_payment, payment.id, "клиент передумал")
    from services.scheduling.models import Booking

    async with db.sessionmaker()() as s:
        assert (await s.get(Booking, booking_id)).status == "cancelled"


async def test_gt_chat_messages_immutable() -> None:
    app_id = await new_application()
    msg = await act(chat.post_message, app_id, 101, "текст")
    with pytest.raises(Exception, match="cannot be edited"):
        async with db.sessionmaker().begin() as s:
            await s.execute(update(Message).where(Message.id == msg.id).values(body="другой"))


async def test_gt_chat_reviewer_lead_cannot_read() -> None:
    app_id = await new_application()
    with pytest.raises(AccessDenied):
        await act(chat.list_messages, app_id, 700, "reviewer_lead")


async def test_gt_chat_events_logged() -> None:
    app_id, _ = await paid_application()
    async with db.sessionmaker()() as s:
        bodies = (await s.scalars(select(Message.body).where(Message.application_id == app_id))).all()
    assert any(b.startswith("Выставлен счёт") for b in bodies)
    assert any(b.startswith("Привязан платёж") for b in bodies)
    assert "Этап: awaiting_payment → awaiting_issue" in bodies
