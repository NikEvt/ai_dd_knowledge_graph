from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.inventory import service, settings
from services.inventory.models import IllLoan, IllPenalty, Transfer


async def flag_overdue_ill(session: AsyncSession, now: datetime) -> list[int]:
    loans = (
        await session.scalars(
            select(IllLoan).where(
                IllLoan.status == "out",
                IllLoan.overdue_flagged.is_(False),
                IllLoan.due_at < now,
            )
        )
    ).all()
    for loan in loans:
        loan.overdue_flagged = True
        events.publish(
            session,
            "inventory.ill_overdue",
            {
                "ill_loan_id": loan.id,
                "copy_id": loan.copy_id,
                "partner_id": loan.partner_id,
                "days_overdue": service.days_late(loan.due_at, now),
            },
        )
    return [loan.id for loan in loans]


async def accrue_ill_penalties(session: AsyncSession, now: datetime) -> int:
    """Ежедневный пересчёт пеней по ещё не возвращённым просроченным выдачам."""
    rows = (
        await session.execute(
            select(IllLoan.id, IllLoan.due_at)
            .join(IllPenalty, IllPenalty.ill_loan_id == IllLoan.id)
            .where(IllLoan.status == "out", IllPenalty.kind == "overdue", IllPenalty.status == "accruing")
        )
    ).all()
    for loan_id, due_at in rows:
        await service.accrue_overdue(session, loan_id, service.days_late(due_at, now))
    return len(rows)


async def expire_stale_transfers(session: AsyncSession, now: datetime) -> list[int]:
    stale = (
        await session.scalars(
            select(Transfer.id).where(
                Transfer.status == "requested",
                Transfer.requested_at < now - timedelta(days=settings.TRANSFER_REQUEST_TTL_DAYS),
            )
        )
    ).all()
    for transfer_id in stale:
        await service.cancel_transfer(session, transfer_id, None, reason="expired")
    return list(stale)
