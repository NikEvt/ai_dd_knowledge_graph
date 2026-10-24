from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.partners import service


@subscribe("partners.request_approved")
async def on_request_approved(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.onboard(session, payload["request_id"], payload["manager_id"])


@subscribe("partners.partner_onboarded")
async def on_partner_onboarded(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.link_request(session, payload["request_id"], payload["partner_id"])


@subscribe("partners.deal_closed")
async def on_deal_closed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.accrue_commission(session, payload["deal_id"])


@subscribe("partners.commission_accrued")
async def on_commission_accrued(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_to_payout(session, payload["commission_id"])


@subscribe("partners.credit_overdue")
async def on_credit_overdue(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.suspend_contract(session, payload["contract_id"], reason="credit_overdue")


@subscribe("partners.deal_paid")
async def on_deal_paid(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.resume_if_settled(session, payload["contract_id"])
