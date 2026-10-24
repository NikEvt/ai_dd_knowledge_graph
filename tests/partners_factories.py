"""Данные и типовые шаги сервиса partners."""

import itertools
from decimal import Decimal

from sqlalchemy import select

from libs import db
from services.partners import service as partners
from services.partners.models import Contract, OnboardingRequest, Partner
from tests.factories import act, read

MANAGER, MANAGER_2 = 701, 702
KPP = "770101001"

_serial = itertools.count(1)
_refs = itertools.count(1)


def make_inn(base: int | None = None) -> str:
    """Валидный ИНН юрлица с контрольной цифрой."""
    head = str(770_000_000 + (base if base is not None else next(_serial)))
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    control = sum(w * int(d) for w, d in zip(weights, head, strict=True)) % 11 % 10
    return head + str(control)


async def get(model, pk: int):
    async with db.sessionmaker()() as s:
        return await s.get(model, pk)


async def requests_for(inn: str) -> list[OnboardingRequest]:
    async with db.sessionmaker()() as s:
        rows = await s.scalars(
            select(OnboardingRequest).where(OnboardingRequest.inn == inn).order_by(OnboardingRequest.id)
        )
        return list(rows.all())


async def submit(inn: str | None = None, *, complete: bool = True, **kwargs) -> OnboardingRequest:
    fields = {
        "inn": inn or make_inn(),
        "contact_name": "Ирина Смирнова",
        "contact_email": "partner@example.org",
    }
    if complete:
        fields |= {"kpp": KPP, "legal_name": "ООО «Книжный агент»"}
    return await act(partners.submit_request, **(fields | kwargs))


async def onboard(
    inn: str | None = None, *, complete: bool = True, manager: int = MANAGER
) -> tuple[int, int]:
    """Заявка → одобрение → партнёр с черновиком договора. Возвращает (partner_id, contract_id)."""
    req = await submit(inn, complete=complete)
    await act(partners.approve_request, req.id, manager)
    req = await get(OnboardingRequest, req.id)
    contract = await read(partners.current_contract, req.partner_id)
    return req.partner_id, contract.id


async def active_contract(
    *,
    credit_limit: Decimal | None = None,
    pct: Decimal | None = None,
    manager: int = MANAGER,
) -> tuple[int, int]:
    partner_id, contract_id = await onboard(manager=manager)
    if pct is not None:
        await act(partners.change_commission_rate, contract_id, manager, pct)
    if credit_limit is not None:
        await act(partners.set_credit_terms, contract_id, manager, allowed=True, limit=credit_limit)
    await act(partners.activate_contract, contract_id, manager)
    return partner_id, contract_id


async def deal(
    contract_id: int, amount: Decimal | int, *, manager: int = MANAGER, prepay: bool = True
) -> int:
    d = await act(
        partners.open_deal, contract_id, manager, external_ref=f"D-{next(_refs)}", amount=Decimal(amount)
    )
    if prepay and d.status == "awaiting_prepayment":
        await act(partners.register_prepayment, d.id, manager)
    return d.id


async def closed_deal(contract_id: int, amount: Decimal | int, *, manager: int = MANAGER) -> int:
    deal_id = await deal(contract_id, amount, manager=manager)
    await act(partners.close_deal, deal_id, manager)
    return deal_id


async def contract(contract_id: int) -> Contract:
    return await get(Contract, contract_id)


async def partner(partner_id: int) -> Partner:
    return await get(Partner, partner_id)
