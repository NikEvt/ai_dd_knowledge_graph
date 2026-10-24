import pytest

from libs.errors import DomainError
from services.applications import service as apps
from services.billing.public import active_books_invoice
from tests.factories import (
    BOOK_L1,
    CHECKER,
    KZN,
    LAW,
    OPERATOR,
    TVR,
    act,
    application,
    invoice,
    new_application,
    paid_application,
    pass_review,
    read,
    stage,
)


async def test_venue_change_reassigns_site_checker() -> None:
    app_id = await new_application()
    await act(apps.change_venue, app_id, OPERATOR, KZN)
    app = await application(app_id)
    assert app.venue_id == KZN
    assert app.site_checker_id == CHECKER[KZN]


async def test_new_venue_must_have_sphere() -> None:
    app_id = await new_application(sphere=LAW, books=(BOOK_L1,))
    with pytest.raises(DomainError, match="сферы"):
        await act(apps.change_venue, app_id, OPERATOR, TVR)


async def test_venue_change_before_payment_reissues_invoice() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    await invoice(app_id)
    assert await stage(app_id) == "awaiting_payment"

    await act(apps.change_venue, app_id, OPERATOR, KZN)
    assert await read(active_books_invoice, app_id) is None
    assert await stage(app_id) == "awaiting_invoice"

    inv = await invoice(app_id)
    assert inv.venue_id == KZN


async def test_paid_venue_change_after_payment_forbidden() -> None:
    app_id, _ = await paid_application()
    with pytest.raises(DomainError, match="возврат платежа"):
        await act(apps.change_venue, app_id, OPERATOR, KZN)
