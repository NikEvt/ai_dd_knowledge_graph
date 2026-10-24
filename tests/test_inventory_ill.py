from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from libs import db
from libs.errors import DomainError
from services.inventory import jobs, settings
from services.inventory import service as inventory
from services.inventory.models import IllLoan, PartnerLibrary, WriteOff
from tests import inventory_factories as inv
from tests.factories import MSK, T0, act, read, travel


@pytest.fixture(autouse=True)
async def custodians(world: None) -> None:
    await inv.staff()


async def _penalties(partner_id: int) -> dict[str, tuple[int, Decimal, str]]:
    return {p.kind: (p.days, p.amount, p.status) for p in await read(inventory.penalties, partner_id)}


async def test_ill_loan_due_in_thirty_days() -> None:
    copy_id = await inv.copy()
    loan_id = await inv.lend(copy_id, await inv.partner())
    loan = await inv.get(IllLoan, loan_id)
    assert loan.due_at == T0 + timedelta(days=settings.ILL_LOAN_PERIOD_DAYS)
    assert await inv.state(copy_id) == "on_loan"
    assert await inv.stock() == (1, 0)


async def test_overdue_flag_accrues_penalty() -> None:
    copy_id = await inv.copy()
    partner_id = await inv.partner(daily_penalty="20.00")
    loan_id = await inv.lend(copy_id, partner_id)
    now = T0 + timedelta(days=30, hours=5)
    assert await act(jobs.flag_overdue_ill, now=T0 + timedelta(days=29)) == []
    assert await act(jobs.flag_overdue_ill, now=now) == [loan_id]
    assert await act(jobs.flag_overdue_ill, now=now) == []
    assert await _penalties(partner_id) == {"overdue": (1, Decimal("20.00"), "accruing")}

    await act(jobs.accrue_ill_penalties, now=T0 + timedelta(days=40))
    assert await _penalties(partner_id) == {"overdue": (10, Decimal("200.00"), "accruing")}


async def test_penalty_is_capped() -> None:
    partner_id = await inv.partner(daily_penalty="1.00")
    await inv.lend(await inv.copy(), partner_id)
    await act(jobs.flag_overdue_ill, now=T0 + timedelta(days=30 + 200))
    days, amount, _ = (await _penalties(partner_id))["overdue"]
    assert days == settings.ILL_PENALTY_MAX_DAYS
    assert amount == Decimal(settings.ILL_PENALTY_MAX_DAYS)


async def test_late_return_finalizes_penalty() -> None:
    copy_id = await inv.copy()
    partner_id = await inv.partner(daily_penalty="20.00")
    loan_id = await inv.lend(copy_id, partner_id)
    await act(jobs.flag_overdue_ill, now=T0 + timedelta(days=31))
    travel(T0 + timedelta(days=33, hours=1))
    await act(inventory.return_ill, loan_id, inv.KEEPER[MSK])
    assert await _penalties(partner_id) == {"overdue": (4, Decimal("80.00"), "final")}
    assert await inv.state(copy_id) == "available"
    assert await inv.stock() == (1, 1)


async def test_late_return_before_job_still_charges() -> None:
    partner_id = await inv.partner(daily_penalty="20.00")
    loan_id = await inv.lend(await inv.copy(), partner_id)
    travel(T0 + timedelta(days=32))
    await act(inventory.return_ill, loan_id, inv.KEEPER[MSK])
    assert await _penalties(partner_id) == {"overdue": (2, Decimal("40.00"), "final")}


async def test_timely_return_has_no_penalty() -> None:
    partner_id = await inv.partner()
    loan_id = await inv.lend(await inv.copy(), partner_id)
    travel(T0 + timedelta(days=30))
    await act(inventory.return_ill, loan_id, inv.KEEPER[MSK])
    assert await _penalties(partner_id) == {}
    with pytest.raises(DomainError, match="закрыта"):
        await act(inventory.return_ill, loan_id, inv.KEEPER[MSK])


async def test_partner_with_overdue_loan_gets_nothing_new() -> None:
    first, second = await inv.copies(2)
    partner_id = await inv.partner()
    await inv.lend(first, partner_id)
    travel(T0 + timedelta(days=31))
    with pytest.raises(DomainError, match="просроченные"):
        await inv.lend(second, partner_id)


async def test_active_loans_limit() -> None:
    first, second = await inv.copies(2)
    partner_id = await inv.partner(max_active_loans=1)
    await inv.lend(first, partner_id)
    with pytest.raises(DomainError, match="лимит"):
        await inv.lend(second, partner_id)


async def test_renewal_only_once_and_not_when_overdue() -> None:
    partner_id = await inv.partner()
    loan_id = await inv.lend(await inv.copy(), partner_id)
    await act(inventory.renew_ill, loan_id, inv.KEEPER[MSK])
    assert (await inv.get(IllLoan, loan_id)).due_at == T0 + timedelta(days=44)
    with pytest.raises(DomainError, match="продлевалась"):
        await act(inventory.renew_ill, loan_id, inv.KEEPER[MSK])

    other = await inv.lend(await inv.copy(), partner_id)
    travel(T0 + timedelta(days=31))
    with pytest.raises(DomainError, match="просроченную"):
        await act(inventory.renew_ill, other, inv.KEEPER[MSK])


async def test_damaged_on_return_is_written_off() -> None:
    copy_id = await inv.copy()
    loan_id = await inv.lend(copy_id, await inv.partner())
    await act(inventory.return_ill, loan_id, inv.KEEPER[MSK], damaged=True)
    async with db.sessionmaker()() as s:
        act_ = await s.scalar(select(WriteOff).where(WriteOff.copy_id == copy_id))
    assert (act_.reason, act_.ill_loan_id) == ("damaged", loan_id)
    assert await inv.state(copy_id) == "written_off"
    assert await inv.stock() == (0, 0)


async def test_loss_by_partner_charges_and_suspends() -> None:
    lost, spare = await inv.copies(2)
    partner_id = await inv.partner()
    loan_id = await inv.lend(lost, partner_id)
    await act(inventory.report_ill_lost, loan_id, inv.KEEPER[MSK])

    assert await inv.state(lost) == "written_off"
    assert await _penalties(partner_id) == {"lost": (0, settings.ILL_LOST_COMPENSATION, "final")}
    assert (await inv.get(PartnerLibrary, partner_id)).suspended
    assert await inv.stock() == (1, 1)
    with pytest.raises(DomainError, match="приостановлены"):
        await inv.lend(spare, partner_id)


async def test_settling_debt_resumes_partner() -> None:
    copies = await inv.copies(2)
    partner_id = await inv.partner()
    await act(inventory.report_ill_lost, await inv.lend(copies[0], partner_id), inv.KEEPER[MSK])
    (penalty,) = await read(inventory.penalties, partner_id)
    await act(inventory.settle_penalty, penalty.id)
    assert not (await inv.get(PartnerLibrary, partner_id)).suspended
    await inv.lend(copies[1], partner_id)
