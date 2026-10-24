from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError

from libs import clock, db
from libs.errors import DomainError
from services.partners import jobs
from services.partners import service as partners
from services.partners.models import Commission, Payout
from tests.factories import T0, act, read, travel
from tests.partners_factories import MANAGER, active_contract, closed_deal, deal, get


async def test_commission_accrued_on_deal_closed() -> None:
    partner_id, contract_id = await active_contract(pct=Decimal("12.5"))
    deal_id = await closed_deal(contract_id, 1000)

    [c] = await read(partners.commissions, partner_id)
    assert (c.deal_id, c.base_amount, c.rate_pct) == (deal_id, Decimal(1000), Decimal("12.5"))
    assert c.amount == Decimal("1125.00")
    assert c.accrued_at == T0

    # повторная доставка deal_closed не начисляет второй раз
    assert await act(partners.accrue_commission, deal_id) is None
    assert len(await read(partners.commissions, partner_id)) == 1


async def test_rate_change_does_not_touch_accrued_commission() -> None:
    partner_id, contract_id = await active_contract(pct=Decimal(10))
    await closed_deal(contract_id, 2000)
    await act(partners.change_commission_rate, contract_id, MANAGER, Decimal(20))
    await closed_deal(contract_id, 2000)

    old, new = await read(partners.commissions, partner_id)
    assert (old.rate_pct, old.amount) == (Decimal(10), Decimal("2200.00"))
    assert (new.rate_pct, new.amount) == (Decimal(20), Decimal("2400.00"))

    changes = [
        (h.field, h.old_value, h.new_value) for h in await read(partners.contract_history, contract_id)
    ]
    assert changes == [("status", "draft", "active"), ("commission_pct", "10.00", "20.00")]


async def test_accrued_commission_is_frozen_in_database() -> None:
    partner_id, contract_id = await active_contract()
    await closed_deal(contract_id, 500)
    [c] = await read(partners.commissions, partner_id)
    with pytest.raises(DBAPIError, match="cannot be recalculated"):
        async with db.sessionmaker().begin() as s:
            await s.execute(update(Commission).where(Commission.id == c.id).values(rate_pct=Decimal(25)))


async def test_no_commission_for_cancelled_deal() -> None:
    partner_id, contract_id = await active_contract()
    deal_id = await deal(contract_id, 800)
    await act(partners.cancel_deal, deal_id, MANAGER)
    assert await act(partners.accrue_commission, deal_id) is None
    assert await read(partners.commissions, partner_id) == []
    with pytest.raises(DomainError, match="уже закрыта или отменена"):
        await act(partners.close_deal, deal_id, MANAGER)


async def test_commissions_collected_into_monthly_payout() -> None:
    partner_id, contract_id = await active_contract(pct=Decimal(10))
    await closed_deal(contract_id, 1000)
    await closed_deal(contract_id, 500)

    first, second = await read(partners.commissions, partner_id)
    assert first.payout_id == second.payout_id is not None
    payout = await get(Payout, first.payout_id)
    assert (payout.period, payout.total, payout.commissions_count) == (
        date(2026, 3, 1),
        Decimal("1650.00"),
        2,
    )


async def test_closed_payout_period() -> None:
    partner_id, contract_id = await active_contract()
    await closed_deal(contract_id, 1000)
    [c] = await read(partners.commissions, partner_id)
    with pytest.raises(DomainError, match="после его окончания"):
        await act(partners.close_payout, c.payout_id)

    travel(T0 + timedelta(days=31))
    assert await act(jobs.close_payouts, clock.now()) == [c.payout_id]
    assert await act(jobs.close_payouts, clock.now()) == []
    with pytest.raises(DomainError, match="уже закрыта"):
        await act(partners.close_payout, c.payout_id)

    await closed_deal(contract_id, 1000)
    _, april = await read(partners.commissions, partner_id)
    march_payout, april_payout = await read(partners.payouts, partner_id)
    assert april.payout_id == april_payout.id
    assert (march_payout.status, march_payout.total) == ("closed", Decimal("1100.00"))
    assert (april_payout.period, april_payout.status) == (date(2026, 4, 1), "open")
