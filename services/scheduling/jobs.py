from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.scheduling.models import Loan


async def flag_overdue(session: AsyncSession, now: datetime) -> list[int]:
    loans = (
        await session.scalars(
            select(Loan).where(
                Loan.status == "out",
                Loan.overdue_flagged.is_(False),
                Loan.issued_at < now - timedelta(days=30),
            )
        )
    ).all()
    for loan in loans:
        loan.overdue_flagged = True
        events.publish(
            session,
            "loan.overdue",
            {"application_id": loan.application_id, "loan_id": loan.id, "book_id": loan.book_id},
        )
    return [loan.id for loan in loans]
