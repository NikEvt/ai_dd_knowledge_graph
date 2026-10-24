import pytest

from libs.errors import DomainError
from services.billing import service as billing
from tests.factories import (
    ACCOUNTANT,
    REP_DEBT,
    act,
    application,
    issue,
    new_application,
    pass_review,
    stage,
    token,
)


async def test_debt_kind_comes_from_representative() -> None:
    app_id = await new_application(rep=REP_DEBT)
    assert (await application(app_id)).kind == "debt"


async def test_debt_application_skips_invoice() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    assert await stage(app_id) == "awaiting_issue"
    assert await token(app_id) is not None
    with pytest.raises(DomainError):
        await act(billing.take_application, app_id, ACCOUNTANT)


async def test_social_application_skips_invoice() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    assert await stage(app_id) == "awaiting_issue"
    await issue(app_id)
    assert await stage(app_id) == "books_out"


async def test_no_books_invoice_for_social() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    await act(billing.take_application, app_id, ACCOUNTANT)
    with pytest.raises(DomainError):
        await act(billing.issue_books_invoice, app_id, ACCOUNTANT)
