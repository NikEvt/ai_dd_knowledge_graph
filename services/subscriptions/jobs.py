from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.subscriptions import service, settings
from services.subscriptions.models import Invoice, Subscription


async def expire_overdue(session: AsyncSession, now: datetime) -> dict[str, list[int]]:
    """Конец оплаченного месяца переводит абонемент в grace, конец льготного периода — в expired."""
    today = now.date()
    expired = (
        await session.scalars(
            select(Subscription)
            .where(
                Subscription.status.in_(service.LIVE),
                Subscription.paid_until + timedelta(days=30) < today,
            )
            .order_by(Subscription.id)
        )
    ).all()
    for sub in expired:
        sub.status = "expired"
        sub.closed_at = now
        events.publish(session, "subscriptions.expired", {"subscription_id": sub.id, "reason": "unpaid"})
    await session.flush()

    overdue = (
        await session.scalars(
            select(Subscription)
            .where(Subscription.status == "active", Subscription.paid_until < today)
            .order_by(Subscription.id)
        )
    ).all()
    for sub in overdue:
        sub.status = "grace"
        grace_until = sub.paid_until + timedelta(days=settings.GRACE_DAYS)
        events.publish(
            session,
            "subscriptions.grace_started",
            {"subscription_id": sub.id, "grace_until": grace_until.isoformat()},
        )
    return {"expired": [s.id for s in expired], "grace": [s.id for s in overdue]}


async def expire_stale_pending(session: AsyncSession, now: datetime) -> list[int]:
    stale = (
        await session.scalars(
            select(Subscription)
            .where(
                Subscription.status == "pending",
                Subscription.created_at < now - timedelta(days=settings.PENDING_TTL_DAYS),
            )
            .order_by(Subscription.id)
        )
    ).all()
    for sub in stale:
        sub.status = "expired"
        sub.closed_at = now
        events.publish(session, "subscriptions.expired", {"subscription_id": sub.id, "reason": "not_paid"})
    return [s.id for s in stale]


async def issue_renewal_invoices(session: AsyncSession, now: datetime) -> list[int]:
    horizon = now.date() + timedelta(days=settings.RENEWAL_INVOICE_DAYS)
    has_open = select(Invoice.id).where(Invoice.subscription_id == Subscription.id, Invoice.status == "open")
    subs = (
        await session.scalars(
            select(Subscription)
            .where(
                Subscription.status.in_(service.LIVE),
                Subscription.paid_until <= horizon,
                ~has_open.exists(),
            )
            .order_by(Subscription.id)
        )
    ).all()
    issued = []
    for sub in subs:
        invoice = await service.issue_invoice(session, sub, sub.paid_until + timedelta(days=1))
        issued.append(invoice.id)
    return issued
