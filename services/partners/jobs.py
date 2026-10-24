from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.partners import service, settings
from services.partners.models import Contract, Deal, OnboardingRequest, Payout


async def flag_overdue_credit(session: AsyncSession, now: datetime) -> list[int]:
    deals = (
        await session.scalars(
            select(Deal).where(
                Deal.on_credit.is_(True),
                Deal.paid_at.is_(None),
                Deal.status != "cancelled",
                Deal.overdue_flagged.is_(False),
                Deal.due_at < now,
            )
        )
    ).all()
    for deal in deals:
        deal.overdue_flagged = True
        events.publish(
            session,
            "partners.credit_overdue",
            {"deal_id": deal.id, "contract_id": deal.contract_id, "amount": str(deal.amount)},
        )
    return [deal.id for deal in deals]


async def expire_contracts(session: AsyncSession, now: datetime) -> list[int]:
    contracts = (
        await session.scalars(
            select(Contract).where(
                Contract.status.in_(("active", "suspended")), Contract.valid_to < now.date()
            )
        )
    ).all()
    for contract in contracts:
        await service.expire_contract(session, contract)
    return [c.id for c in contracts]


async def expire_requests(session: AsyncSession, now: datetime) -> list[int]:
    stale = (
        await session.scalars(
            select(OnboardingRequest).where(
                OnboardingRequest.status == "open",
                OnboardingRequest.submitted_at < now - timedelta(days=settings.ONBOARDING_REQUEST_TTL_DAYS),
            )
        )
    ).all()
    for req in stale:
        req.status = "expired"
        req.decided_at = now
    return [req.id for req in stale]


async def close_payouts(session: AsyncSession, now: datetime) -> list[int]:
    """Закрывает ведомости прошедших месяцев."""
    month_start = now.date().replace(day=1)
    due = (
        await session.scalars(
            select(Payout.id).where(Payout.status == "open", Payout.period < month_start).order_by(Payout.id)
        )
    ).all()
    for payout_id in due:
        await service.close_payout(session, payout_id)
    return list(due)
