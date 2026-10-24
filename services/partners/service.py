"""Партнёрские агентства: подключение, договоры, сделки в кредит и комиссии."""

import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.partners import settings
from services.partners.models import (
    Commission,
    Contract,
    ContractHistory,
    Deal,
    OnboardingRequest,
    Partner,
    Payout,
)

CURRENT_CONTRACT = ("draft", "active", "suspended")
EDITABLE_FIELDS = ("kpp", "legal_name", "contact_name", "contact_email", "contact_phone")
CENT = Decimal("0.01")

_INN_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)


def inn_valid(inn: str) -> bool:
    if not re.fullmatch(r"\d{10}", inn or ""):
        return False
    digits = [int(c) for c in inn]
    control = sum(w * d for w, d in zip(_INN_WEIGHTS, digits, strict=False)) % 11 % 10
    return control == digits[9]


def _check_kpp(kpp: str | None) -> None:
    if kpp is not None and not re.fullmatch(r"\d{9}", kpp):
        raise DomainError("КПП должен состоять из 9 цифр")


def missing_requisites(partner: Partner) -> list[str]:
    return [f for f in settings.REQUIRED_PARTNER_FIELDS if not (getattr(partner, f) or "").strip()]


# Заявки на подключение ---------------------------------------------------------


async def _request(session: AsyncSession, request_id: int) -> OnboardingRequest:
    req = await session.get(OnboardingRequest, request_id)
    if req is None:
        raise NotFound(f"заявка на подключение {request_id}")
    return req


async def close_duplicates(session: AsyncSession, inn: str, *, keep_id: int | None = None) -> list[int]:
    """Закрывает открытые заявки с тем же ИНН, кроме keep_id. Возвращает id закрытых."""
    query = select(OnboardingRequest).where(OnboardingRequest.inn == inn, OnboardingRequest.status == "open")
    if keep_id is not None:
        query = query.where(OnboardingRequest.id != keep_id)
    duplicates = (await session.scalars(query.with_for_update())).all()
    now = clock.now()
    for req in duplicates:
        req.status = "duplicate"
        req.decided_at = now
        events.publish(
            session,
            "partners.request_closed_duplicate",
            {"request_id": req.id, "inn": inn, "superseded_by": keep_id},
        )
    await session.flush()
    return [req.id for req in duplicates]


async def submit_request(
    session: AsyncSession,
    *,
    inn: str,
    contact_name: str,
    contact_email: str,
    kpp: str | None = None,
    legal_name: str | None = None,
    contact_phone: str | None = None,
) -> OnboardingRequest:
    if not inn_valid(inn):
        raise DomainError("некорректный ИНН")
    _check_kpp(kpp)
    connected = await session.scalar(
        select(Contract.id)
        .join(Partner, Partner.id == Contract.partner_id)
        .where(Partner.inn == inn, Contract.status.in_(("active", "suspended")))
    )
    if connected is not None:
        raise DomainError("партнёр с таким ИНН уже подключён")

    # Повторная заявка заменяет предыдущую: агентство прислало уточнённые данные
    await close_duplicates(session, inn)
    req = OnboardingRequest(
        inn=inn,
        kpp=kpp,
        legal_name=legal_name,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        submitted_at=clock.now(),
    )
    session.add(req)
    await session.flush()
    events.publish(session, "partners.request_submitted", {"request_id": req.id, "inn": inn})
    return req


async def _decide(session: AsyncSession, request_id: int, manager_id: int) -> OnboardingRequest:
    req = await _request(session, request_id)
    if req.status != "open":
        raise DomainError("по заявке уже принято решение")
    req.decided_at = clock.now()
    req.decided_by = manager_id
    return req


async def approve_request(session: AsyncSession, request_id: int, manager_id: int) -> OnboardingRequest:
    req = await _decide(session, request_id, manager_id)
    req.status = "approved"
    events.publish(session, "partners.request_approved", {"request_id": req.id, "manager_id": manager_id})
    return req


async def reject_request(
    session: AsyncSession, request_id: int, manager_id: int, reason: str
) -> OnboardingRequest:
    if not reason.strip():
        raise DomainError("укажите причину отказа")
    req = await _decide(session, request_id, manager_id)
    req.status = "rejected"
    req.reject_reason = reason
    events.publish(session, "partners.request_rejected", {"request_id": req.id, "reason": reason})
    return req


async def _next_contract_number(session: AsyncSession, partner: Partner) -> str:
    n = await session.scalar(select(func.count()).where(Contract.partner_id == partner.id))
    return f"АГ-{partner.inn[-4:]}/{partner.id}-{n + 1}"


async def onboard(session: AsyncSession, request_id: int, manager_id: int) -> Partner:
    """Заводит партнёра по одобренной заявке (или дополняет существующего) и черновик договора."""
    req = await _request(session, request_id)
    now = clock.now()
    partner = await session.scalar(select(Partner).where(Partner.inn == req.inn))
    if partner is None:
        partner = Partner(inn=req.inn, manager_id=manager_id, created_at=now, updated_at=now)
        session.add(partner)
    for field in ("kpp", "legal_name", "contact_name", "contact_email", "contact_phone"):
        value = getattr(req, field)
        if value:
            setattr(partner, field, value)
    partner.updated_at = now
    await session.flush()

    contract = await session.scalar(
        select(Contract).where(Contract.partner_id == partner.id, Contract.status.in_(CURRENT_CONTRACT))
    )
    if contract is None:
        today = now.date()
        contract = Contract(
            partner_id=partner.id,
            number=await _next_contract_number(session, partner),
            commission_pct=settings.DEFAULT_COMMISSION_PCT,
            valid_from=today,
            valid_to=today + timedelta(days=settings.CONTRACT_TERM_DAYS),
            created_at=now,
        )
        session.add(contract)
        await session.flush()
    events.publish(
        session,
        "partners.partner_onboarded",
        {"request_id": req.id, "partner_id": partner.id, "contract_id": contract.id},
    )
    return partner


async def link_request(session: AsyncSession, request_id: int, partner_id: int) -> None:
    req = await _request(session, request_id)
    req.partner_id = partner_id


# Партнёры и договоры -----------------------------------------------------------


async def _partner_for_manager(session: AsyncSession, partner_id: int, manager_id: int) -> Partner:
    partner = await session.get(Partner, partner_id)
    if partner is None:
        raise NotFound(f"партнёр {partner_id}")
    if partner.manager_id != manager_id:
        raise AccessDenied("партнёр закреплён за другим менеджером")
    return partner


async def _contract_for_manager(session: AsyncSession, contract_id: int, manager_id: int) -> Contract:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise NotFound(f"договор {contract_id}")
    await _partner_for_manager(session, contract.partner_id, manager_id)
    return contract


async def current_contract(session: AsyncSession, partner_id: int) -> Contract | None:
    return await session.scalar(
        select(Contract).where(Contract.partner_id == partner_id, Contract.status.in_(CURRENT_CONTRACT))
    )


async def update_requisites(
    session: AsyncSession, partner_id: int, manager_id: int, **fields: str | None
) -> Partner:
    partner = await _partner_for_manager(session, partner_id, manager_id)
    unknown = set(fields) - set(EDITABLE_FIELDS)
    if unknown:
        raise DomainError(f"нельзя изменить поля: {', '.join(sorted(unknown))}")
    if "kpp" in fields:
        _check_kpp(fields["kpp"])
    contract = await current_contract(session, partner_id)
    if contract is not None and contract.status != "draft":
        cleared = [f for f in settings.REQUIRED_PARTNER_FIELDS if f in fields and not fields[f]]
        if cleared:
            raise DomainError("нельзя удалить обязательные реквизиты партнёра с действующим договором")
    for name, value in fields.items():
        setattr(partner, name, value)
    partner.updated_at = clock.now()
    await session.flush()
    return partner


async def activate_contract(session: AsyncSession, contract_id: int, manager_id: int) -> Contract:
    contract = await _contract_for_manager(session, contract_id, manager_id)
    if contract.status != "draft":
        raise DomainError("активировать можно только черновик договора")
    partner = await session.get(Partner, contract.partner_id)
    missing = missing_requisites(partner)
    if missing:
        titles = ", ".join(settings.REQUISITE_TITLES[f] for f in missing)
        raise DomainError(f"у партнёра не заполнены реквизиты: {titles}")
    if contract.valid_to < clock.now().date():
        raise DomainError("срок действия договора истёк")
    contract.status = "active"
    contract.activated_at = clock.now()
    await session.flush()
    events.publish(
        session,
        "partners.contract_activated",
        {"contract_id": contract.id, "partner_id": contract.partner_id},
    )
    return contract


def _check_rate(pct: Decimal) -> None:
    if pct < 0 or pct > settings.MAX_COMMISSION_PCT:
        raise DomainError(f"ставка комиссии должна быть от 0 до {settings.MAX_COMMISSION_PCT}%")


async def change_commission_rate(
    session: AsyncSession, contract_id: int, manager_id: int, pct: Decimal
) -> Contract:
    contract = await _contract_for_manager(session, contract_id, manager_id)
    if contract.status not in CURRENT_CONTRACT:
        raise DomainError("договор закрыт")
    _check_rate(pct)
    old = contract.commission_pct
    contract.commission_pct = pct
    events.publish(
        session,
        "partners.contract_rate_changed",
        {"contract_id": contract.id, "old_pct": str(old), "new_pct": str(pct)},
    )
    return contract


async def set_credit_terms(
    session: AsyncSession, contract_id: int, manager_id: int, *, allowed: bool, limit: Decimal = Decimal(0)
) -> Contract:
    contract = await _contract_for_manager(session, contract_id, manager_id)
    if contract.status not in CURRENT_CONTRACT:
        raise DomainError("договор закрыт")
    if limit < 0:
        raise DomainError("лимит кредита не может быть отрицательным")
    if limit > settings.MAX_CREDIT_LIMIT:
        raise DomainError("лимит кредита выше допустимого без согласования")
    contract.credit_allowed = allowed
    contract.credit_limit = limit if allowed else Decimal(0)
    await session.flush()
    return contract


async def credit_exposure(session: AsyncSession, contract_id: int) -> Decimal:
    """Сумма неоплаченных сделок в кредит по договору."""
    total = await session.scalar(
        select(func.coalesce(func.sum(Deal.amount), 0)).where(
            Deal.contract_id == contract_id,
            Deal.on_credit.is_(True),
            Deal.paid_at.is_(None),
            Deal.status != "cancelled",
        )
    )
    return Decimal(total)


async def suspend_contract(session: AsyncSession, contract_id: int, reason: str) -> bool:
    contract = await session.get(Contract, contract_id, with_for_update=True)
    if contract is None or contract.status != "active":
        return False
    contract.status = "suspended"
    contract.suspend_reason = reason
    events.publish(session, "partners.contract_suspended", {"contract_id": contract.id, "reason": reason})
    return True


async def resume_if_settled(session: AsyncSession, contract_id: int) -> bool:
    contract = await session.get(Contract, contract_id, with_for_update=True)
    if contract is None or contract.status != "suspended" or contract.suspend_reason != "credit_overdue":
        return False
    still_overdue = await session.scalar(
        select(func.count()).where(
            Deal.contract_id == contract_id,
            Deal.overdue_flagged.is_(True),
            Deal.paid_at.is_(None),
            Deal.status != "cancelled",
        )
    )
    if still_overdue:
        return False
    contract.status = "active"
    contract.suspend_reason = None
    events.publish(session, "partners.contract_resumed", {"contract_id": contract.id})
    return True


# Сделки ------------------------------------------------------------------------


def _in_force(contract: Contract, today: date) -> None:
    if contract.status == "suspended":
        raise DomainError("договор приостановлен, новые сделки запрещены")
    if contract.status != "active":
        raise DomainError("договор не действует")
    if not contract.valid_from <= today <= contract.valid_to:
        raise DomainError("сделка вне срока действия договора")


async def open_deal(
    session: AsyncSession, contract_id: int, manager_id: int, *, external_ref: str, amount: Decimal
) -> Deal:
    contract = await _contract_for_manager(session, contract_id, manager_id)
    now = clock.now()
    _in_force(contract, now.date())
    if amount <= 0:
        raise DomainError("сумма сделки должна быть положительной")
    exists = await session.scalar(
        select(Deal.id).where(Deal.contract_id == contract_id, Deal.external_ref == external_ref)
    )
    if exists is not None:
        raise DomainError(f"сделка {external_ref} уже заведена")

    # В кредит — без предоплаты; лимит проверяет триггер на вставке
    on_credit = contract.credit_allowed
    deal = Deal(
        contract_id=contract_id,
        external_ref=external_ref,
        amount=amount,
        on_credit=on_credit,
        status="open" if on_credit else "awaiting_prepayment",
        created_at=now,
        due_at=now + timedelta(days=settings.CREDIT_PAYMENT_DAYS) if on_credit else None,
    )
    session.add(deal)
    await session.flush()
    events.publish(
        session,
        "partners.deal_created",
        {"deal_id": deal.id, "contract_id": contract_id, "on_credit": on_credit, "amount": str(amount)},
    )
    return deal


async def _deal_for_manager(session: AsyncSession, deal_id: int, manager_id: int) -> tuple[Deal, Contract]:
    deal = await session.get(Deal, deal_id)
    if deal is None:
        raise NotFound(f"сделка {deal_id}")
    contract = await _contract_for_manager(session, deal.contract_id, manager_id)
    return deal, contract


async def register_prepayment(session: AsyncSession, deal_id: int, manager_id: int) -> Deal:
    deal, _ = await _deal_for_manager(session, deal_id, manager_id)
    if deal.status != "awaiting_prepayment":
        raise DomainError("сделка не ожидает предоплаты")
    deal.prepaid_at = clock.now()
    deal.status = "open"
    return deal


async def close_deal(session: AsyncSession, deal_id: int, manager_id: int) -> Deal:
    deal, contract = await _deal_for_manager(session, deal_id, manager_id)
    if deal.status == "awaiting_prepayment":
        raise DomainError("сделка без кредита закрывается только после предоплаты")
    if deal.status != "open":
        raise DomainError("сделка уже закрыта или отменена")
    deal.status = "closed"
    deal.closed_at = clock.now()
    events.publish(
        session,
        "partners.deal_closed",
        {
            "deal_id": deal.id,
            "contract_id": contract.id,
            "partner_id": contract.partner_id,
            "amount": str(deal.amount),
        },
    )
    return deal


async def cancel_deal(session: AsyncSession, deal_id: int, manager_id: int) -> Deal:
    deal, _ = await _deal_for_manager(session, deal_id, manager_id)
    if deal.status not in ("awaiting_prepayment", "open"):
        raise DomainError("закрытую сделку отменить нельзя")
    deal.status = "cancelled"
    events.publish(session, "partners.deal_cancelled", {"deal_id": deal.id, "contract_id": deal.contract_id})
    return deal


async def register_payment(session: AsyncSession, deal_id: int) -> Deal:
    """Партнёр оплатил сделку, проведённую в кредит."""
    deal = await session.get(Deal, deal_id)
    if deal is None:
        raise NotFound(f"сделка {deal_id}")
    if not deal.on_credit:
        raise DomainError("сделка оплачена предоплатой")
    if deal.paid_at is not None or deal.status == "cancelled":
        raise DomainError("сделка уже оплачена или отменена")
    deal.paid_at = clock.now()
    events.publish(session, "partners.deal_paid", {"deal_id": deal.id, "contract_id": deal.contract_id})
    return deal


# Комиссии ----------------------------------------------------------------------


def commission_amount(base: Decimal, pct: Decimal) -> Decimal:
    return (base * (1 + pct / 100)).quantize(CENT, rounding=ROUND_HALF_UP)


async def accrue_commission(session: AsyncSession, deal_id: int) -> Commission | None:
    if await session.scalar(select(Commission).where(Commission.deal_id == deal_id)) is not None:
        return None
    deal = await session.get(Deal, deal_id)
    if deal is None or deal.status != "closed":
        return None
    contract = await session.get(Contract, deal.contract_id)
    commission = Commission(
        deal_id=deal.id,
        contract_id=contract.id,
        partner_id=contract.partner_id,
        base_amount=deal.amount,
        rate_pct=contract.commission_pct,
        amount=commission_amount(deal.amount, contract.commission_pct),
        accrued_at=clock.now(),
    )
    session.add(commission)
    await session.flush()
    events.publish(
        session,
        "partners.commission_accrued",
        {
            "commission_id": commission.id,
            "partner_id": commission.partner_id,
            "amount": str(commission.amount),
        },
    )
    return commission


async def add_to_payout(session: AsyncSession, commission_id: int) -> Payout | None:
    commission = await session.get(Commission, commission_id, with_for_update=True)
    if commission is None or commission.payout_id is not None:
        return None
    period = commission.accrued_at.date().replace(day=1)
    payout = await session.scalar(
        select(Payout)
        .where(Payout.partner_id == commission.partner_id, Payout.period == period)
        .with_for_update()
    )
    if payout is None or payout.status == "closed":
        if payout is not None:
            # Ведомость уже закрыта — комиссия уходит в следующую
            period = (period + timedelta(days=32)).replace(day=1)
        payout = await _open_payout(session, commission.partner_id, period)
    payout.total += commission.amount
    payout.commissions_count += 1
    commission.payout_id = payout.id
    return payout


async def _open_payout(session: AsyncSession, partner_id: int, period: date) -> Payout:
    payout = await session.scalar(
        select(Payout).where(Payout.partner_id == partner_id, Payout.period == period)
    )
    if payout is None:
        payout = Payout(partner_id=partner_id, period=period, total=Decimal(0), commissions_count=0)
        session.add(payout)
        await session.flush()
    return payout


async def close_payout(session: AsyncSession, payout_id: int) -> Payout:
    payout = await session.get(Payout, payout_id)
    if payout is None:
        raise NotFound(f"ведомость {payout_id}")
    if payout.status != "open":
        raise DomainError("ведомость уже закрыта")
    if payout.period >= clock.now().date().replace(day=1):
        raise DomainError("ведомость текущего месяца закрывается после его окончания")
    payout.status = "closed"
    events.publish(
        session,
        "partners.payout_closed",
        {"payout_id": payout.id, "partner_id": payout.partner_id, "total": str(payout.total)},
    )
    return payout


async def commissions(session: AsyncSession, partner_id: int) -> list[Commission]:
    rows = await session.scalars(
        select(Commission).where(Commission.partner_id == partner_id).order_by(Commission.id)
    )
    return list(rows.all())


async def expire_contract(session: AsyncSession, contract: Contract) -> None:
    contract.status = "expired"
    contract.suspend_reason = None
    await session.execute(
        update(Deal)
        .where(Deal.contract_id == contract.id, Deal.status == "awaiting_prepayment")
        .values(status="cancelled")
    )
    events.publish(session, "partners.contract_expired", {"contract_id": contract.id})


async def terminate_contract(
    session: AsyncSession, contract_id: int, manager_id: int, reason: str
) -> Contract:
    contract = await _contract_for_manager(session, contract_id, manager_id)
    if contract.status not in CURRENT_CONTRACT:
        raise DomainError("договор уже закрыт")
    if not reason.strip():
        raise DomainError("укажите причину расторжения")
    open_deals = await session.scalar(
        select(func.count()).where(Deal.contract_id == contract_id, Deal.status == "open")
    )
    if open_deals:
        raise DomainError("по договору есть незакрытые сделки")
    if await credit_exposure(session, contract_id) > 0:
        raise DomainError("партнёр не погасил задолженность по сделкам в кредит")
    await session.execute(
        update(Deal)
        .where(Deal.contract_id == contract_id, Deal.status == "awaiting_prepayment")
        .values(status="cancelled")
    )
    contract.status = "terminated"
    contract.suspend_reason = None
    events.publish(session, "partners.contract_terminated", {"contract_id": contract.id, "reason": reason})
    return contract


async def renew_contract(session: AsyncSession, partner_id: int, manager_id: int) -> Contract:
    """Новый черновик договора на условиях последнего закрытого."""
    partner = await _partner_for_manager(session, partner_id, manager_id)
    if await current_contract(session, partner_id) is not None:
        raise DomainError("у партнёра уже есть действующий договор")
    previous = await session.scalar(
        select(Contract).where(Contract.partner_id == partner_id).order_by(Contract.id.desc()).limit(1)
    )
    now = clock.now()
    contract = Contract(
        partner_id=partner_id,
        number=await _next_contract_number(session, partner),
        commission_pct=previous.commission_pct if previous else settings.DEFAULT_COMMISSION_PCT,
        credit_allowed=previous.credit_allowed if previous else False,
        credit_limit=previous.credit_limit if previous else Decimal(0),
        valid_from=now.date(),
        valid_to=now.date() + timedelta(days=settings.CONTRACT_TERM_DAYS),
        created_at=now,
    )
    session.add(contract)
    await session.flush()
    return contract


async def contract_history(session: AsyncSession, contract_id: int) -> list[ContractHistory]:
    rows = await session.scalars(
        select(ContractHistory).where(ContractHistory.contract_id == contract_id).order_by(ContractHistory.id)
    )
    return list(rows.all())


async def payouts(session: AsyncSession, partner_id: int) -> list[Payout]:
    rows = await session.scalars(
        select(Payout).where(Payout.partner_id == partner_id).order_by(Payout.period)
    )
    return list(rows.all())
