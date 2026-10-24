"""Регрессия: счета, платежи, архив и попытки, штрафы."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from support import (
    ACCOUNTANT,
    CHECKER,
    CHIEF,
    MSK,
    OPERATOR,
    REP_DEBT,
    T0,
    act,
    application,
    invoice,
    issue,
    new_application,
    paid_application,
    pass_review,
    pay,
    read,
    stage,
    travel,
)

from libs import clock, db
from libs.errors import DomainError
from services.applications import jobs as app_jobs
from services.applications import service as apps
from services.billing import service as billing
from services.billing.models import Fine, Invoice
from services.billing.public import active_books_invoice
from services.scheduling import jobs as sched_jobs
from services.scheduling import service as scheduling
from services.scheduling.models import Loan


async def test_gt_invoice_amount_includes_markup() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    assert inv.amount == Decimal("110.00")


async def test_gt_invoice_price_fixed_after_issue() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    from services.applications.admin import set_representative_terms

    await act(set_representative_terms, 1, markup_pct=Decimal(50), debt_allowed=False)
    assert (await read(active_books_invoice, app_id)).amount == inv.amount


async def test_gt_one_active_books_invoice() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    await invoice(app_id)
    async with db.sessionmaker()() as s:
        first = await s.scalar(select(Invoice).where(Invoice.application_id == app_id))
    with pytest.raises(Exception, match="uq_invoices_one_active_books"):
        async with db.sessionmaker().begin() as s:
            s.add(
                Invoice(
                    application_id=app_id,
                    kind="books",
                    amount=Decimal(1),
                    status="active",
                    issued_at=clock.now(),
                    payment_clock_started_at=clock.now(),
                    venue_id=first.venue_id,
                    requisites=first.requisites,
                )
            )


async def test_gt_cannot_cancel_invoice_with_payment() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv, Decimal("10.00"))
    with pytest.raises(DomainError):
        await act(billing.cancel_invoice, inv.id, "test")


async def test_gt_payment_to_cancelled_invoice_forbidden() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await act(billing.cancel_invoice, inv.id, "test")
    with pytest.raises(DomainError):
        await pay(inv)


async def test_gt_partial_payment_keeps_waiting() -> None:
    """Заменяется задачей T03."""
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv, Decimal("100.00"))
    assert await stage(app_id) == "awaiting_payment"


async def test_gt_overpayment_flagged() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    payment = await act(billing.link_payment, inv.id, Decimal("200.00"), CHIEF)
    assert payment.overpayment is True
    assert await stage(app_id) == "awaiting_issue"


async def test_gt_refund_after_payment_archives_with_refund() -> None:
    app_id, inv = await paid_application()
    async with db.sessionmaker()() as s:
        from services.billing.models import Payment

        payment = await s.scalar(select(Payment).where(Payment.invoice_id == inv.id))
    await act(billing.refund_payment, payment.id, "клиент передумал")
    app = await application(app_id)
    assert app.stage == "archived"
    assert app.attempts[-1].outcome == "refund"


async def test_gt_archive_review_timeout_any_kind() -> None:
    debt = await new_application(rep=REP_DEBT)
    await act(apps.submit_for_review, debt, OPERATOR)
    travel(T0 + timedelta(days=31))
    assert await act(app_jobs.archive_stale, clock.now()) == [debt]


async def test_gt_archive_link_issued_social_never_auto_archived() -> None:
    social = await new_application(social=True)
    await pass_review(social)
    travel(T0 + timedelta(days=120))
    assert await act(app_jobs.archive_stale, clock.now()) == []


async def test_gt_unarchive_same_amount_keeps_invoice_and_restarts_clock() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    travel(T0 + timedelta(days=31))
    await act(app_jobs.archive_stale, clock.now())
    assert await stage(app_id) == "archived"
    await act(apps.unarchive, app_id, OPERATOR)
    await act(apps.approve, app_id, 201)
    assert await stage(app_id) == "awaiting_payment"
    kept = await read(active_books_invoice, app_id)
    assert kept.id == inv.id
    travel(T0 + timedelta(days=50))
    assert await act(app_jobs.archive_stale, clock.now()) == []


async def test_gt_unarchive_changed_books_cancels_invoice() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    await invoice(app_id)
    await act(apps.archive, app_id, actor="operator", outcome="client_declined", operator_id=OPERATOR)
    await act(apps.unarchive, app_id, OPERATOR, book_ids=[1, 2])
    assert await read(active_books_invoice, app_id) is None


async def test_gt_fine_for_lost_book() -> None:
    app_id, _ = await paid_application()
    [loan_id] = await issue(app_id)
    await act(scheduling.mark_lost, loan_id, CHECKER[MSK])
    async with db.sessionmaker()() as s:
        [fine] = (await s.scalars(select(Fine).where(Fine.application_id == app_id))).all()
    assert (fine.kind, fine.amount) == ("lost", Decimal("500.00"))
    with pytest.raises(DomainError):
        await act(apps.close, app_id, CHECKER[MSK])


async def test_gt_fine_invoice_and_close_for_paid() -> None:
    app_id, _ = await paid_application()
    [loan_id] = await issue(app_id)
    await act(scheduling.return_book, loan_id, CHECKER[MSK], damaged=True)
    async with db.sessionmaker()() as s:
        fine = await s.scalar(select(Fine).where(Fine.application_id == app_id))
    fine_inv = await act(billing.issue_fine_invoice, fine.id, ACCOUNTANT)
    await act(billing.link_payment, fine_inv.id, fine_inv.amount, CHIEF)
    await act(apps.close, app_id, CHECKER[MSK])
    assert await stage(app_id) == "closed"


async def test_gt_debt_fine_paid_outside_by_operator() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    [loan_id] = await issue(app_id)
    await act(scheduling.mark_lost, loan_id, CHECKER[MSK])
    async with db.sessionmaker()() as s:
        fine = await s.scalar(select(Fine).where(Fine.application_id == app_id))
    with pytest.raises(DomainError):
        await act(billing.issue_fine_invoice, fine.id, ACCOUNTANT)
    await act(billing.mark_fine_paid_outside, fine.id, OPERATOR)
    await act(apps.close, app_id, CHECKER[MSK])


async def test_gt_loan_due_30_days() -> None:
    """Заменяется задачей T02."""
    app_id, _ = await paid_application()
    await issue(app_id)
    async with db.sessionmaker()() as s:
        loan = await s.scalar(select(Loan).where(Loan.application_id == app_id))
    assert loan.due_at - loan.issued_at == timedelta(days=30)


async def test_gt_overdue_after_30_days() -> None:
    """Заменяется задачей T02."""
    app_id, _ = await paid_application()
    await issue(app_id)
    async with db.sessionmaker()() as s:
        loan = await s.scalar(select(Loan).where(Loan.application_id == app_id))
    travel(loan.issued_at + timedelta(days=29))
    assert await act(sched_jobs.flag_overdue, clock.now()) == []
    travel(loan.issued_at + timedelta(days=31))
    assert await act(sched_jobs.flag_overdue, clock.now()) == [loan.id]
