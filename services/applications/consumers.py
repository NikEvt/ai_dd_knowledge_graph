from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.bpm import engine as bpm
from libs.events import subscribe
from services.applications import dedup, service
from services.applications.models import Application


@subscribe("invoice.issued")
async def on_invoice_issued(session: AsyncSession, payload: dict[str, Any]) -> None:
    if payload["invoice_kind"] != "books":
        return
    app = await service.load(session, payload["application_id"])
    if app.stage == "awaiting_invoice":
        await bpm.transition(session, app, "awaiting_payment", actor="accountant")


@subscribe("invoice.cancelled")
async def on_invoice_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    if payload["invoice_kind"] != "books":
        return
    app = await service.load(session, payload["application_id"])
    if app.stage == "awaiting_payment":
        await bpm.transition(session, app, "awaiting_invoice", actor="system")


@subscribe("payment.fully_paid")
async def on_fully_paid(session: AsyncSession, payload: dict[str, Any]) -> None:
    if payload["invoice_kind"] != "books":
        return
    app = await service.load(session, payload["application_id"])
    if app.stage != "awaiting_payment":
        return
    await bpm.transition(session, app, "awaiting_issue", actor="system")
    await service.mark_ready_for_booking(session, app)
    await dedup.close_duplicates(session, app)


@subscribe("application.review_passed")
async def on_review_passed(session: AsyncSession, payload: dict[str, Any]) -> None:
    if payload["kind"] != "debt":
        return
    app = await service.load(session, payload["application_id"])
    await dedup.close_duplicates(session, app)


@subscribe("client.updated")
async def on_client_updated(session: AsyncSession, payload: dict[str, Any]) -> None:
    others = (
        await session.scalars(
            select(Application).where(
                Application.client_id == payload["client_id"],
                Application.stage.in_(("awaiting_invoice", "awaiting_payment")),
            )
        )
    ).all()
    for app in others:
        if app.id == payload.get("source_application_id"):
            continue
        await bpm.transition(session, app, "on_review", actor="system")


@subscribe("books.issued")
async def on_books_issued(session: AsyncSession, payload: dict[str, Any]) -> None:
    app = await service.load(session, payload["application_id"])
    await bpm.transition(session, app, "books_out", actor="site_checker")


@subscribe("payment.refunded")
async def on_payment_refunded(session: AsyncSession, payload: dict[str, Any]) -> None:
    if payload["invoice_kind"] != "books":
        return
    app = await service.load(session, payload["application_id"])
    if app.stage == "awaiting_issue":
        await service.archive(session, app.id, actor="chief_accountant", outcome="refund")
