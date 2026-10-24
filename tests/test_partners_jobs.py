from datetime import timedelta
from decimal import Decimal

import pytest

from libs import clock
from libs.errors import DomainError
from services.partners import jobs, settings
from services.partners import service as partners
from services.partners.models import Deal, OnboardingRequest
from tests.factories import T0, act, travel
from tests.partners_factories import active_contract, closed_deal, contract, deal, get, submit


async def run(job) -> list[int]:
    return await act(job, clock.now())


async def test_overdue_credit_suspends_contract() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(10_000))
    deal_id = await closed_deal(contract_id, 1000)

    travel(T0 + timedelta(days=settings.CREDIT_PAYMENT_DAYS - 1))
    assert await run(jobs.flag_overdue_credit) == []

    travel(T0 + timedelta(days=settings.CREDIT_PAYMENT_DAYS, hours=1))
    assert await run(jobs.flag_overdue_credit) == [deal_id]
    assert await run(jobs.flag_overdue_credit) == []
    c = await contract(contract_id)
    assert (c.status, c.suspend_reason) == ("suspended", "credit_overdue")
    with pytest.raises(DomainError, match="приостановлен"):
        await deal(contract_id, 100)


async def test_paying_all_overdue_deals_resumes_contract() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(10_000))
    first = await closed_deal(contract_id, 1000)
    second = await closed_deal(contract_id, 2000)
    travel(T0 + timedelta(days=settings.CREDIT_PAYMENT_DAYS + 1))
    await run(jobs.flag_overdue_credit)

    await act(partners.register_payment, first)
    assert (await contract(contract_id)).status == "suspended"
    await act(partners.register_payment, second)
    assert (await contract(contract_id)).status == "active"
    await deal(contract_id, 100)


async def test_contract_expires_after_term() -> None:
    _, contract_id = await active_contract()
    pending = await deal(contract_id, 500, prepay=False)
    c = await contract(contract_id)

    travel(T0 + timedelta(days=settings.CONTRACT_TERM_DAYS))
    assert await run(jobs.expire_contracts) == []
    travel(T0 + timedelta(days=settings.CONTRACT_TERM_DAYS + 1))
    assert await run(jobs.expire_contracts) == [contract_id]
    assert (await contract(contract_id)).status == "expired"
    assert (await get(Deal, pending)).status == "cancelled"
    assert c.valid_to == T0.date() + timedelta(days=settings.CONTRACT_TERM_DAYS)


async def test_stale_requests_expire() -> None:
    old = await submit()
    travel(T0 + timedelta(days=10))
    fresh = await submit()

    travel(T0 + timedelta(days=settings.ONBOARDING_REQUEST_TTL_DAYS + 1))
    assert await run(jobs.expire_requests) == [old.id]
    assert (await get(OnboardingRequest, old.id)).status == "expired"
    assert (await get(OnboardingRequest, fresh.id)).status == "open"
    # после истечения агентство может подать заявку заново
    await submit(old.inn)
