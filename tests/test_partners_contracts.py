from decimal import Decimal

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.partners import service as partners
from services.partners.models import Contract, Deal
from tests.factories import act, read
from tests.partners_factories import (
    MANAGER,
    MANAGER_2,
    active_contract,
    closed_deal,
    contract,
    deal,
    get,
    onboard,
)


async def test_contract_not_activated_without_requisites() -> None:
    partner_id, contract_id = await onboard(complete=False)
    with pytest.raises(DomainError, match="не заполнены реквизиты: КПП, наименование"):
        await act(partners.activate_contract, contract_id, MANAGER)
    with pytest.raises(DBAPIError, match="incomplete requisites"):
        async with db.sessionmaker().begin() as s:
            await s.execute(update(Contract).where(Contract.id == contract_id).values(status="active"))

    await act(partners.update_requisites, partner_id, MANAGER, kpp="770101001", legal_name="АО «Чтение»")
    activated = await act(partners.activate_contract, contract_id, MANAGER)
    assert activated.status == "active"
    assert activated.activated_at is not None


async def test_required_requisites_cannot_be_cleared_on_active_contract() -> None:
    partner_id, _ = await active_contract()
    with pytest.raises(DomainError, match="обязательные реквизиты"):
        await act(partners.update_requisites, partner_id, MANAGER, legal_name="")
    with pytest.raises(DomainError, match="нельзя изменить поля: inn"):
        await act(partners.update_requisites, partner_id, MANAGER, inn="7700000017")
    await act(partners.update_requisites, partner_id, MANAGER, contact_phone="+7 495 000-00-00")


async def test_contract_managed_only_by_partner_manager() -> None:
    _, contract_id = await onboard()
    with pytest.raises(AccessDenied):
        await act(partners.activate_contract, contract_id, MANAGER_2)
    with pytest.raises(AccessDenied):
        await act(partners.change_commission_rate, contract_id, MANAGER_2, Decimal(5))


async def test_commission_rate_bounds() -> None:
    _, contract_id = await active_contract()
    with pytest.raises(DomainError, match="ставка комиссии"):
        await act(partners.change_commission_rate, contract_id, MANAGER, Decimal(31))
    with pytest.raises(DomainError, match="лимит кредита выше"):
        await act(partners.set_credit_terms, contract_id, MANAGER, allowed=True, limit=Decimal(600_000))


async def test_deal_without_credit_needs_prepayment() -> None:
    _, contract_id = await active_contract()
    deal_id = await deal(contract_id, 1000, prepay=False)
    d = await get(Deal, deal_id)
    assert (d.status, d.on_credit, d.due_at) == ("awaiting_prepayment", False, None)
    with pytest.raises(DomainError, match="после предоплаты"):
        await act(partners.close_deal, deal_id, MANAGER)

    await act(partners.register_prepayment, deal_id, MANAGER)
    await act(partners.close_deal, deal_id, MANAGER)
    assert (await get(Deal, deal_id)).status == "closed"


async def test_credit_deal_goes_without_prepayment() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(5000))
    deal_id = await deal(contract_id, 3000, prepay=False)
    d = await get(Deal, deal_id)
    assert (d.status, d.on_credit) == ("open", True)
    assert d.due_at is not None
    assert await read(partners.credit_exposure, contract_id) == Decimal(3000)


async def test_credit_limit_blocks_new_deal() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(5000))
    await deal(contract_id, 3000)
    with pytest.raises(DBAPIError, match="deal exceeds credit limit"):
        await deal(contract_id, 2500)
    await deal(contract_id, 2000)
    assert await read(partners.credit_exposure, contract_id) == Decimal(5000)


async def test_lowered_limit_blocks_all_deals_until_paid() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(5000))
    first = await closed_deal(contract_id, 4000)
    await act(partners.set_credit_terms, contract_id, MANAGER, allowed=True, limit=Decimal(1000))
    with pytest.raises(DBAPIError, match="new deals are blocked"):
        await deal(contract_id, 100)

    await act(partners.register_payment, first)
    assert await read(partners.credit_exposure, contract_id) == Decimal(0)
    await deal(contract_id, 900)


async def test_terminated_contract_can_be_renewed() -> None:
    partner_id, contract_id = await active_contract(credit_limit=Decimal(3000), pct=Decimal(15))
    credit_deal = await closed_deal(contract_id, 1000)
    pending = await deal(contract_id, 200)
    with pytest.raises(DomainError, match="незакрытые сделки"):
        await act(partners.terminate_contract, contract_id, MANAGER, "смена агентства")
    await act(partners.cancel_deal, pending, MANAGER)
    with pytest.raises(DomainError, match="задолженность"):
        await act(partners.terminate_contract, contract_id, MANAGER, "смена агентства")

    await act(partners.register_payment, credit_deal)
    with pytest.raises(DomainError, match="действующий договор"):
        await act(partners.renew_contract, partner_id, MANAGER)
    await act(partners.terminate_contract, contract_id, MANAGER, "смена агентства")
    assert (await contract(contract_id)).status == "terminated"

    renewed = await act(partners.renew_contract, partner_id, MANAGER)
    assert renewed.id != contract_id
    assert renewed.number.endswith("-2")
    assert (renewed.status, renewed.commission_pct, renewed.credit_limit) == (
        "draft",
        Decimal(15),
        Decimal(3000),
    )


async def test_cancelled_deal_releases_credit() -> None:
    _, contract_id = await active_contract(credit_limit=Decimal(1000))
    deal_id = await deal(contract_id, 1000)
    await act(partners.cancel_deal, deal_id, MANAGER)
    assert await read(partners.credit_exposure, contract_id) == Decimal(0)
    with pytest.raises(DomainError, match="уже оплачена или отменена"):
        await act(partners.register_payment, deal_id)
