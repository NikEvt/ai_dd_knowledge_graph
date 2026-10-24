from datetime import UTC, date, datetime

import pytest

from libs.errors import AccessDenied, DomainError
from services.subscriptions import service
from tests.factories import act, travel
from tests.subscriptions_factories import (
    CLIENT_2,
    PASSPORT,
    SENIOR,
    active,
    all_notices,
    notice_kinds,
    plans,
    subscribe,
    subscription,
)


async def test_complete_holder_is_verified() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    assert (await subscription(sub_id)).holder_check == "verified"


async def test_holder_without_passport_is_rejected() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"], passport=None)
    assert (await subscription(sub_id)).holder_check == "rejected"
    rejected = [n for n in await all_notices(sub_id) if n.kind == "holder_rejected"]
    assert "паспорта" in rejected[0].body


async def test_holder_update_sends_subscription_to_recheck() -> None:
    p = await plans()
    sub_id = await active(p["std"], passport=None)
    assert (await subscription(sub_id)).holder_check == "rejected"

    await act(service.update_holder, sub_id, client_ref="client-1", passport=PASSPORT)
    sub = await subscription(sub_id)
    assert sub.passport == PASSPORT
    assert sub.holder_check == "verified"
    assert sub.status == "active"


async def test_unchanged_holder_data_is_not_rechecked() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"], passport=None)
    await act(service.update_holder, sub_id, client_ref="client-1", holder_name="Анна Петрова")
    assert await notice_kinds(sub_id) == ["invoice", "holder_rejected"]


async def test_holder_updated_only_by_owner() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    with pytest.raises(AccessDenied):
        await act(service.update_holder, sub_id, client_ref=CLIENT_2, holder_name="Чужой")


async def test_closed_subscription_holder_is_frozen() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    await active(p["std"])
    with pytest.raises(DomainError, match="закрыт"):
        await act(service.update_holder, first, client_ref="client-1", holder_name="Анна П.")


async def test_social_plan_needs_eligible_holder() -> None:
    p = await plans()
    with pytest.raises(DomainError, match="студентам и пенсионерам"):
        await subscribe(p["soc"])
    with pytest.raises(DomainError, match="паспорт и дата рождения"):
        await subscribe(p["soc"], passport=None, birth_date=SENIOR)
    assert await subscribe(p["soc"], birth_date=SENIOR)


async def test_student_social_plan_rejected_on_recheck_after_birthday() -> None:
    p = await plans()
    sub_id = await active(p["soc"], birth_date=date(2002, 3, 10))
    assert (await subscription(sub_id)).holder_check == "verified"

    travel(datetime(2026, 3, 11, 9, 0, tzinfo=UTC))
    await act(service.update_holder, sub_id, client_ref="client-1", holder_name="Анна Сергеевна Петрова")
    sub = await subscription(sub_id)
    assert sub.holder_check == "rejected"
    rejected = [n for n in await all_notices(sub_id) if n.kind == "holder_rejected"]
    assert "социального тарифа" in rejected[0].body


async def test_corporate_plan_requires_employer() -> None:
    p = await plans()
    with pytest.raises(DomainError, match="работодатель"):
        await subscribe(p["corp"])
    with pytest.raises(DomainError, match="только для корпоративного"):
        await subscribe(p["std"], employer_ref="org-15")


async def test_archived_plan_not_sold() -> None:
    p = await plans()
    await act(service.archive_plan, p["std-plus"])
    with pytest.raises(DomainError, match="не продаётся"):
        await subscribe(p["std-plus"])
