from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.scheduling.models import Loan


async def open_loans_count(session: AsyncSession, application_id: int) -> int:
    return await session.scalar(
        select(func.count()).where(Loan.application_id == application_id, Loan.status == "out")
    )
