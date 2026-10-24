import pytest
from sqlalchemy.exc import IntegrityError

from libs import clock, db
from libs.errors import DomainError
from services.partners import service as partners
from services.partners import settings
from services.partners.models import Contract, OnboardingRequest, Partner
from tests.factories import act
from tests.partners_factories import (
    KPP,
    MANAGER,
    get,
    make_inn,
    onboard,
    requests_for,
    submit,
)


async def test_request_with_bad_inn_is_refused() -> None:
    inn = make_inn()
    broken = inn[:-1] + str((int(inn[-1]) + 1) % 10)
    with pytest.raises(DomainError, match="ИНН"):
        await submit(broken)
    with pytest.raises(DomainError, match="КПП"):
        await submit(kpp="12345")


async def test_approved_request_creates_partner_with_draft_contract() -> None:
    inn = make_inn()
    partner_id, contract_id = await onboard(inn)

    partner = await get(Partner, partner_id)
    assert (partner.inn, partner.kpp, partner.manager_id) == (inn, KPP, MANAGER)
    contract = await get(Contract, contract_id)
    assert contract.status == "draft"
    assert contract.commission_pct == settings.DEFAULT_COMMISSION_PCT
    assert contract.credit_allowed is False
    [req] = await requests_for(inn)
    assert (req.status, req.partner_id, req.decided_by) == ("approved", partner_id, MANAGER)


async def test_new_request_supersedes_open_one() -> None:
    inn = make_inn()
    first = await submit(inn, complete=False)
    second = await submit(inn, legal_name="ООО «Книжный агент»", kpp=KPP)

    rows = await requests_for(inn)
    assert [(r.id, r.status) for r in rows] == [(first.id, "duplicate"), (second.id, "open")]
    assert rows[0].decided_at == clock.now()


async def test_only_one_open_request_per_inn_in_database() -> None:
    inn = make_inn()
    await submit(inn)
    with pytest.raises(IntegrityError, match="ux_onboarding_requests_open_inn"):
        async with db.sessionmaker().begin() as s:
            s.add(
                OnboardingRequest(
                    inn=inn, contact_name="Дубль", contact_email="dup@example.org", submitted_at=clock.now()
                )
            )


async def test_close_duplicates_keeps_given_request() -> None:
    inn = make_inn()
    req = await submit(inn)
    assert await act(partners.close_duplicates, inn, keep_id=req.id) == []
    assert (await get(OnboardingRequest, req.id)).status == "open"

    assert await act(partners.close_duplicates, inn) == [req.id]
    assert (await get(OnboardingRequest, req.id)).status == "duplicate"


async def test_request_decided_only_once() -> None:
    req = await submit()
    with pytest.raises(DomainError, match="причину"):
        await act(partners.reject_request, req.id, MANAGER, "  ")
    await act(partners.reject_request, req.id, MANAGER, "нет лицензии")
    with pytest.raises(DomainError, match="уже принято решение"):
        await act(partners.approve_request, req.id, MANAGER)


async def test_connected_partner_cannot_apply_again() -> None:
    inn = make_inn()
    partner_id, contract_id = await onboard(inn)
    await act(partners.activate_contract, contract_id, MANAGER)
    with pytest.raises(DomainError, match="уже подключён"):
        await submit(inn)
