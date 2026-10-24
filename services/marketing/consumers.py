from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.marketing import service


@subscribe("marketing.campaign_launched")
async def on_campaign_launched(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.prepare_messages(session, payload["campaign_id"])


@subscribe("marketing.campaign_prepared")
async def on_campaign_prepared(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.deliver_messages(session, payload["campaign_id"])


@subscribe("marketing.campaign_finished")
async def on_campaign_finished(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.summarize_campaign(session, payload["campaign_id"])


@subscribe("marketing.unsubscribed")
async def on_unsubscribed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.exclude_address(session, payload["email"], payload["venue_id"])


@subscribe("marketing.message_bounced")
async def on_message_bounced(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.handle_bounce(session, payload["email"])
