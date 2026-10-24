from datetime import timedelta
from decimal import Decimal

import pytest

from libs.errors import DomainError
from services.applications import service as apps
from services.billing import service as billing
from services.scheduling import service as scheduling
from tests.factories import (
    ACCOUNTANT,
    ACCOUNTANT_2,
    CHECKER,
    MSK,
    T0,
    TVR,
    act,
    application,
    invoice,
    issue,
    new_application,
    paid_application,
    pass_review,
    pay,
    stage,
    token,
)


async def test_paid_application_full_path() -> None:
    app_id = await new_application()
    assert await stage(app_id) == "draft"

    await pass_review(app_id)
    assert await stage(app_id) == "awaiting_invoice"

    inv = await invoice(app_id)
    assert inv.amount == Decimal("110.00")  # 100 по прайсу Москвы + 10% надбавки представителя
    assert await stage(app_id) == "awaiting_payment"

    await pay(inv)
    assert await stage(app_id) == "awaiting_issue"
    assert await token(app_id) is not None

    loans = await issue(app_id)
    assert await stage(app_id) == "books_out"

    for loan_id in loans:
        await act(scheduling.return_book, loan_id, CHECKER[MSK])
    await act(apps.close, app_id, CHECKER[MSK])
    assert await stage(app_id) == "closed"


async def test_invoice_requires_assigned_accountant() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    await act(billing.take_application, app_id, ACCOUNTANT)
    with pytest.raises(DomainError):
        await act(billing.issue_books_invoice, app_id, ACCOUNTANT_2)
    await act(billing.take_application, app_id, ACCOUNTANT_2)
    inv = await act(billing.issue_books_invoice, app_id, ACCOUNTANT_2)
    assert inv.status == "active"


async def test_invoice_requires_venue_requisites() -> None:
    app_id = await new_application(venue=TVR)
    await pass_review(app_id)
    await act(billing.take_application, app_id, ACCOUNTANT)
    with pytest.raises(DomainError, match="реквизиты"):
        await act(billing.issue_books_invoice, app_id, ACCOUNTANT)


async def test_partial_payment_does_not_open_issue() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv, Decimal("50.00"))
    assert await stage(app_id) == "awaiting_payment"
    await pay(inv, Decimal("60.00"))
    assert await stage(app_id) == "awaiting_issue"


async def test_issue_only_on_booked_date() -> None:
    app_id, _ = await paid_application()
    from tests.factories import book, slot, travel

    slot_id = await slot(MSK, 1, T0 + timedelta(days=3))
    booking_id = await book(app_id, slot_id)
    travel(T0 + timedelta(days=2))
    with pytest.raises(DomainError, match="дату"):
        await act(scheduling.issue_books, booking_id, CHECKER[MSK])


async def test_cannot_close_with_books_out() -> None:
    app_id, _ = await paid_application()
    await issue(app_id)
    with pytest.raises(DomainError):
        await act(apps.close, app_id, CHECKER[MSK])
    assert (await application(app_id)).stage == "books_out"
