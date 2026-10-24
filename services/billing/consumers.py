from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock
from libs.events import subscribe
from services.billing import service
from services.billing.models import Invoice
from services.billing.public import active_books_invoice, paid_amount


@subscribe("application.venue_changed")
async def on_venue_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    invoice = await active_books_invoice(session, payload["application_id"])
    if invoice is not None and invoice.paid_amount == 0:
        await service.cancel_invoice(session, invoice.id, reason="venue_changed")


@subscribe("application.closed_duplicate")
async def on_closed_duplicate(session: AsyncSession, payload: dict[str, Any]) -> None:
    for invoice in await service.active_invoices(session, payload["application_id"]):
        if await paid_amount(session, invoice.id) == 0:
            await service.cancel_invoice(session, invoice.id, reason="duplicate")


@subscribe("application.unarchived")
async def on_unarchived(session: AsyncSession, payload: dict[str, Any]) -> None:
    brief = await active_books_invoice(session, payload["application_id"])
    if brief is None:
        return
    if payload["amount_changed"]:
        await service.cancel_invoice(session, brief.id, reason="amount_changed")
    else:
        invoice = await session.get(Invoice, brief.id)
        invoice.payment_clock_started_at = clock.now()


@subscribe("loan.overdue")
async def on_loan_overdue(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.create_fine(session, payload["application_id"], payload["loan_id"], "overdue")


@subscribe("loan.lost")
async def on_loan_lost(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.create_fine(session, payload["application_id"], payload["loan_id"], "lost")


@subscribe("loan.damaged")
async def on_loan_damaged(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.create_fine(session, payload["application_id"], payload["loan_id"], "damaged")
