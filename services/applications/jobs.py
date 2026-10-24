"""Фоновые задачи сервиса заявок (запускаются планировщиком раз в час)."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import settings
from services.applications import service
from services.applications.models import Application
from services.billing import public as billing


async def archive_stale(session: AsyncSession, now: datetime) -> list[int]:
    archived: list[int] = []

    no_data = (
        await session.scalars(
            select(Application).where(
                Application.stage.in_(("on_review", "needs_rework")),
                Application.review_started_at < now - timedelta(days=settings.REVIEW_ARCHIVE_DAYS),
            )
        )
    ).all()
    for app in no_data:
        await service.archive(session, app.id, actor="system", outcome="no_data")
        archived.append(app.id)

    awaiting_payment = (
        await session.scalars(
            select(Application).where(Application.kind == "paid", Application.stage == "awaiting_payment")
        )
    ).all()
    for app in awaiting_payment:
        invoice = await billing.active_books_invoice(session, app.id)
        if invoice is None or invoice.paid_amount >= invoice.amount:
            continue
        if invoice.payment_clock_started_at < now - timedelta(days=settings.PAYMENT_ARCHIVE_DAYS):
            await service.archive(session, app.id, actor="system", outcome="unpaid")
            archived.append(app.id)
    return archived
