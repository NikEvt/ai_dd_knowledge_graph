from datetime import date

import pytest

from libs.errors import AccessDenied, DomainError
from services.applications import service as apps
from tests.factories import (
    CLIENT_INCOMPLETE,
    OPERATOR,
    OPERATOR_2,
    REVIEWER,
    REVIEWER_2,
    act,
    new_application,
    stage,
    submit,
)


async def test_approve_requires_assigned_reviewer() -> None:
    app_id = await new_application()
    await act(apps.submit_for_review, app_id, OPERATOR)
    with pytest.raises(DomainError, match="не назначен"):
        await act(apps.approve, app_id, REVIEWER)


async def test_only_assigned_reviewer_approves() -> None:
    app_id = await new_application()
    await submit(app_id)
    with pytest.raises(AccessDenied):
        await act(apps.approve, app_id, REVIEWER_2)


async def test_incomplete_client_goes_to_rework() -> None:
    app_id = await new_application(client=CLIENT_INCOMPLETE)
    await submit(app_id)
    with pytest.raises(DomainError, match="не хватает"):
        await act(apps.approve, app_id, REVIEWER)

    await act(apps.return_for_rework, app_id, REVIEWER, "нужен паспорт")
    assert await stage(app_id) == "needs_rework"
    await act(apps.submit_for_review, app_id, OPERATOR)
    await act(
        apps.update_client,
        CLIENT_INCOMPLETE,
        REVIEWER,
        source_application_id=app_id,
        passport="4510 000003",
        birth_date=date(2000, 1, 1),
    )
    await act(apps.approve, app_id, REVIEWER)
    assert await stage(app_id) == "awaiting_invoice"


async def test_operator_works_only_with_own_applications() -> None:
    app_id = await new_application(operator=OPERATOR)
    with pytest.raises(AccessDenied):
        await act(apps.submit_for_review, app_id, OPERATOR_2)
