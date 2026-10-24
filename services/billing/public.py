"""Внутренний API биллинга для других сервисов."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.billing.models import AccountantAssignment, Fine, Invoice, Payment


@dataclass(frozen=True)
class InvoiceBrief:
    id: int
    amount: Decimal
    paid_amount: Decimal
    issued_at: datetime
    payment_clock_started_at: datetime


async def paid_amount(session: AsyncSession, invoice_id: int) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id == invoice_id, Payment.unlinked_at.is_(None), Payment.refunded.is_(False)
        )
    )
    return Decimal(total)


async def active_books_invoice(session: AsyncSession, application_id: int) -> InvoiceBrief | None:
    inv = await session.scalar(
        select(Invoice).where(
            Invoice.application_id == application_id, Invoice.kind == "books", Invoice.status == "active"
        )
    )
    if inv is None:
        return None
    return InvoiceBrief(
        id=inv.id,
        amount=inv.amount,
        paid_amount=await paid_amount(session, inv.id),
        issued_at=inv.issued_at,
        payment_clock_started_at=inv.payment_clock_started_at,
    )


async def accountant_of(session: AsyncSession, application_id: int) -> int | None:
    a = await session.get(AccountantAssignment, application_id)
    return a.accountant_id if a else None


async def open_fines_count(session: AsyncSession, application_id: int) -> int:
    return await session.scalar(
        select(func.count()).where(Fine.application_id == application_id, Fine.status == "open")
    )
