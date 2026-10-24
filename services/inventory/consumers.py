from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.inventory import service


@subscribe("inventory.copy_registered")
@subscribe("inventory.copy_relocated")
@subscribe("inventory.copy_written_off")
@subscribe("inventory.transfer_shipped")
@subscribe("inventory.transfer_received")
@subscribe("inventory.transfer_cancelled")
@subscribe("inventory.ill_issued")
@subscribe("inventory.ill_returned")
async def on_stock_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    for venue_id in payload["venue_ids"]:
        await service.recount_stock(session, payload["book_ref"], venue_id)


@subscribe("inventory.copy_lost")
async def on_copy_lost(session: AsyncSession, payload: dict[str, Any]) -> None:
    copy = await service.get_copy(session, payload["copy_id"])
    loan_id = payload.get("ill_loan_id")
    await service.write_off(
        session, copy, "lost", by=payload.get("custodian_id"), ill_loan_id=loan_id, note=payload.get("note")
    )
    if loan_id is not None:
        await service.charge_lost_copy(session, loan_id)


@subscribe("inventory.copy_damaged")
async def on_copy_damaged(session: AsyncSession, payload: dict[str, Any]) -> None:
    copy = await service.get_copy(session, payload["copy_id"])
    await service.write_off(
        session,
        copy,
        "damaged",
        by=payload.get("custodian_id"),
        ill_loan_id=payload.get("ill_loan_id"),
        note=payload.get("note"),
    )


@subscribe("inventory.ill_overdue")
async def on_ill_overdue(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.accrue_overdue(session, payload["ill_loan_id"], payload["days_overdue"])


@subscribe("inventory.ill_returned")
async def on_ill_returned(session: AsyncSession, payload: dict[str, Any]) -> None:
    days = service.days_late(
        datetime.fromisoformat(payload["due_at"]), datetime.fromisoformat(payload["returned_at"])
    )
    if days:
        await service.accrue_overdue(session, payload["ill_loan_id"], days, final=True)


@subscribe("inventory.ill_penalty_accrued")
async def on_penalty_accrued(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.review_partner_debt(session, payload["partner_id"])
