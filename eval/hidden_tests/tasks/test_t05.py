"""T05: СНИЛС клиента (поле snils) обязателен для проверки; его изменение — изменение данных клиента."""

from datetime import date

import pytest
from support import (
    CLIENT_A,
    OPERATOR,
    REP_PLAIN,
    REVIEWER,
    act,
    invoice,
    new_application,
    pass_review,
    stage,
    submit,
)

from libs.errors import DomainError
from services.applications import service as apps


async def test_t05_snils_required_for_review() -> None:
    client = await act(
        apps.create_client,
        email="new@example.org",
        full_name="Галина Орлова",
        passport="4510 000099",
        birth_date=date(1991, 7, 7),
    )
    app_id = await new_application(client=client.id)
    await submit(app_id)
    with pytest.raises(DomainError):
        await act(apps.approve, app_id, REVIEWER)

    await act(apps.update_client, client.id, REVIEWER, source_application_id=app_id, snils="123-456-789 01")
    await act(apps.approve, app_id, REVIEWER)
    assert await stage(app_id) == "awaiting_invoice"


async def test_t05_snils_change_sends_other_applications_to_review() -> None:
    waiting = await new_application()
    await pass_review(waiting)
    await invoice(waiting)
    assert await stage(waiting) == "awaiting_payment"

    current = await new_application(rep=REP_PLAIN)
    await submit(current)
    await act(apps.update_client, CLIENT_A, REVIEWER, source_application_id=current, snils="999-999-999 99")

    assert await stage(waiting) == "on_review"
    assert await stage(current) == "on_review"


async def test_t05_operator_cannot_set_snils_after_review() -> None:
    app_id = await new_application()
    await submit(app_id)
    with pytest.raises(DomainError):
        await act(apps.update_client, CLIENT_A, OPERATOR, source_application_id=app_id,
                  snils="111-111-111 11")
