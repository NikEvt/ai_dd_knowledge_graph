"""Регрессия: заявки, проверка, смена площадки, данные клиента, дедупликация."""

from datetime import date

import pytest
from sqlalchemy import select, update
from support import (
    BOOK_H2,
    CHECKER,
    CLIENT_A,
    CLIENT_INCOMPLETE,
    KZN,
    LAW,
    BOOK_L1,
    OPERATOR,
    REP_DEBT,
    REP_PLAIN,
    REVIEWER,
    TVR,
    act,
    application,
    invoice,
    issue,
    new_application,
    paid_application,
    pass_review,
    read,
    stage,
    submit,
)

from libs import db
from libs.errors import DomainError
from services.applications import admin
from services.applications import service as apps
from services.applications.models import Application
from services.billing.public import active_books_invoice


async def test_gt_app_sphere_and_representative_immutable() -> None:
    app_id = await new_application()
    with pytest.raises(Exception, match="cannot be changed"):
        async with db.sessionmaker().begin() as s:
            await s.execute(update(Application).where(Application.id == app_id).values(sphere_id=LAW))


async def test_gt_app_new_application_needs_sphere_at_venue() -> None:
    with pytest.raises(DomainError):
        await new_application(venue=TVR, sphere=LAW, books=(BOOK_L1,))


async def test_gt_app_inactive_sphere_blocks_new_but_not_existing() -> None:
    existing = await new_application()
    await act(admin.set_sphere_active, 1, 1, False)
    with pytest.raises(DomainError):
        await new_application(client=2)
    await pass_review(existing)
    assert await stage(existing) == "awaiting_invoice"


async def test_gt_venue_paid_before_payment_reissues_invoice() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    await invoice(app_id)
    await act(apps.change_venue, app_id, OPERATOR, KZN)
    assert await read(active_books_invoice, app_id) is None
    assert await stage(app_id) == "awaiting_invoice"
    app = await application(app_id)
    assert app.site_checker_id == CHECKER[KZN]


async def test_gt_venue_paid_after_payment_forbidden() -> None:
    app_id, _ = await paid_application()
    with pytest.raises(DomainError):
        await act(apps.change_venue, app_id, OPERATOR, KZN)


async def test_gt_venue_social_locked_after_link() -> None:
    """Заменяется задачей T01 для социальных заявок."""
    app_id = await new_application(social=True)
    await pass_review(app_id)
    with pytest.raises(Exception):  # noqa: B017
        await act(apps.change_venue, app_id, OPERATOR, KZN)


async def test_gt_venue_debt_locked_after_link() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    with pytest.raises(Exception):  # noqa: B017
        await act(apps.change_venue, app_id, OPERATOR, KZN)


async def test_gt_venue_forbidden_after_issue() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    await issue(app_id)
    with pytest.raises(Exception):  # noqa: B017
        await act(apps.change_venue, app_id, OPERATOR, KZN)


async def test_gt_review_incomplete_client_blocks_approve() -> None:
    app_id = await new_application(client=CLIENT_INCOMPLETE)
    await submit(app_id)
    with pytest.raises(DomainError):
        await act(apps.approve, app_id, REVIEWER)


async def test_gt_client_update_sends_other_apps_to_review() -> None:
    waiting = await new_application()
    await pass_review(waiting)
    await invoice(waiting)
    current = await new_application(rep=REP_PLAIN)
    await submit(current)
    await act(apps.update_client, CLIENT_A, REVIEWER, source_application_id=current, passport="4510 777777")
    assert await stage(waiting) == "on_review"


async def test_gt_client_update_does_not_touch_booking_stage() -> None:
    booked, _ = await paid_application()
    current = await new_application(rep=REP_PLAIN, sphere=LAW, books=(BOOK_L1,))
    await submit(current)
    await act(apps.update_client, CLIENT_A, REVIEWER, source_application_id=current, birth_date=date(1990, 5, 2))
    assert await stage(booked) == "awaiting_issue"


async def test_gt_client_email_change_does_not_resend_to_review() -> None:
    waiting = await new_application()
    await pass_review(waiting)
    await invoice(waiting)
    current = await new_application(rep=REP_PLAIN)
    await submit(current)
    await act(apps.update_client, CLIENT_A, REVIEWER, source_application_id=current, email="anna2@example.org")
    assert await stage(waiting) == "awaiting_payment"


async def test_gt_dedup_paid_payment_closes_duplicate() -> None:
    loser = await new_application(rep=REP_PLAIN)
    await pass_review(loser)
    await invoice(loser)
    winner, _ = await paid_application()
    assert await stage(winner) == "awaiting_issue"
    assert await stage(loser) == "closed_duplicate"
    assert await read(active_books_invoice, loser) is None


async def test_gt_dedup_debt_review_closes_duplicate() -> None:
    loser = await new_application()
    await submit(loser)
    winner = await new_application(rep=REP_DEBT)
    await pass_review(winner)
    assert await stage(loser) == "closed_duplicate"


async def test_gt_dedup_social_paid_independent() -> None:
    """Заменяется задачей T04."""
    social = await new_application(social=True, rep=REP_PLAIN)
    await pass_review(social)
    paid, _ = await paid_application()
    assert await stage(social) == "awaiting_issue"
    assert await stage(paid) == "awaiting_issue"


async def test_gt_dedup_other_sphere_independent() -> None:
    other = await new_application(sphere=LAW, books=(BOOK_L1,), rep=REP_PLAIN)
    await submit(other)
    await paid_application()
    assert await stage(other) == "on_review"


async def test_gt_books_change_only_in_draft_or_rework() -> None:
    app_id = await new_application()
    await act(apps.change_books, app_id, OPERATOR, [BOOK_H2])
    await pass_review(app_id)
    with pytest.raises(DomainError):
        await act(apps.change_books, app_id, OPERATOR, [1])


async def test_gt_debt_kind_from_admin_flag() -> None:
    app_id = await new_application(rep=REP_DEBT)
    async with db.sessionmaker()() as s:
        assert (await s.scalar(select(Application.kind).where(Application.id == app_id))) == "debt"
