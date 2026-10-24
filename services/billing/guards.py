from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.bpm import engine as bpm
from services.billing.public import active_books_invoice


@bpm.guard("fully_paid")
async def fully_paid(session: AsyncSession, app: Any) -> bool:
    invoice = await active_books_invoice(session, app.id)
    return invoice is not None and invoice.paid_amount >= invoice.amount


@bpm.guard("has_active_invoice")
async def has_active_invoice(session: AsyncSession, app: Any) -> bool:
    return await active_books_invoice(session, app.id) is not None
