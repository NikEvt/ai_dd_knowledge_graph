from datetime import timedelta

import pytest

from libs.errors import DomainError
from services.applications import jobs
from services.applications import service as apps
from tests.factories import (
    CLIENT_INCOMPLETE,
    OPERATOR,
    T0,
    act,
    application,
    invoice,
    new_application,
    pass_review,
    stage,
    submit,
    travel,
)


async def run_archive_job() -> list[int]:
    from libs import clock

    return await act(jobs.archive_stale, clock.now())


async def test_stuck_review_goes_to_archive_after_month() -> None:
    app_id = await new_application(client=CLIENT_INCOMPLETE)
    await submit(app_id)
    travel(T0 + timedelta(days=29))
    assert await run_archive_job() == []
    travel(T0 + timedelta(days=31))
    assert await run_archive_job() == [app_id]
    app = await application(app_id)
    assert app.stage == "archived"
    assert app.attempts[-1].outcome == "no_data"


async def test_unpaid_invoice_goes_to_archive_after_month() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    travel(T0 + timedelta(days=1))
    await invoice(app_id)
    travel(T0 + timedelta(days=32))
    assert await run_archive_job() == [app_id]
    assert (await application(app_id)).attempts[-1].outcome == "unpaid"


async def test_unarchive_starts_new_attempt_and_review() -> None:
    app_id = await new_application()
    await act(apps.archive, app_id, actor="operator", outcome="client_declined", operator_id=OPERATOR)
    await act(apps.unarchive, app_id, OPERATOR)
    app = await application(app_id)
    assert app.stage == "on_review"
    assert [a.no for a in app.attempts] == [1, 2]
    assert app.attempts[0].outcome == "client_declined"


async def test_paid_application_cannot_be_archived_by_operator_after_payment() -> None:
    from tests.factories import paid_application

    app_id, _ = await paid_application()
    with pytest.raises(DomainError):
        await act(apps.archive, app_id, actor="operator", outcome="client_declined", operator_id=OPERATOR)
    assert await stage(app_id) == "awaiting_issue"
