from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.errors import DomainError
from services.marketing import service, settings
from services.marketing.models import Campaign


async def launch_due(session: AsyncSession, now: datetime) -> list[int]:
    """Запускает запланированные кампании, время которых пришло.

    Кампания, которую сейчас запустить нельзя (например, аудитории недавно писали),
    остаётся запланированной и попадёт в следующий прогон.
    """
    due = (
        await session.scalars(
            select(Campaign)
            .where(Campaign.status == "scheduled", Campaign.scheduled_at <= now)
            .order_by(Campaign.scheduled_at, Campaign.id)
            .with_for_update(skip_locked=True)
        )
    ).all()
    launched = []
    for campaign in due:
        try:
            async with session.begin_nested():
                await service.start(session, campaign, now)
        except DomainError:
            continue
        launched.append(campaign.id)
    return launched


async def purge_test_messages(session: AsyncSession, now: datetime) -> int:
    return await service.purge_test_messages(
        session, now - timedelta(days=settings.TEST_MESSAGE_TTL_DAYS)
    )
