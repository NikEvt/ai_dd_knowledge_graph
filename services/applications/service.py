"""Сценарии заявки: создание, проверка, смена площадки, архив, закрытие."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.bpm import engine as bpm
from libs.errors import AccessDenied, DomainError, NotFound
from services.applications import public
from services.applications.models import (
    Application,
    ApplicationBook,
    Attempt,
    Book,
    Client,
    Price,
    Representative,
    Venue,
    VenueSphere,
)
from services.applications.review import missing_client_fields
from services.billing import public as billing

PAID_VENUE_LOCKED_STAGES = ("awaiting_issue", "books_out")
TERMINAL_STAGES = ("closed", "closed_duplicate")
CLIENT_EDITABLE_FIELDS = ("full_name", "passport", "birth_date", "email")


async def load(session: AsyncSession, application_id: int) -> Application:
    app = await session.get(Application, application_id)
    if app is None:
        raise NotFound(f"заявка {application_id}")
    return app


def _require_operator(app: Application, operator_id: int) -> None:
    if app.operator_id != operator_id:
        raise AccessDenied("заявка закреплена за другим оператором")


async def _check_sphere_at_venue(session: AsyncSession, venue_id: int, sphere_id: int) -> None:
    vs = await session.get(VenueSphere, (venue_id, sphere_id))
    if vs is None or not vs.active:
        raise DomainError("на площадке нет сферы заявки")


async def _check_books(session: AsyncSession, venue_id: int, sphere_id: int, book_ids: list[int]) -> None:
    if not book_ids:
        raise DomainError("в заявке нет книг")
    found = (
        await session.scalars(
            select(Book.id)
            .join(Price, Price.book_id == Book.id)
            .where(Book.id.in_(book_ids), Book.sphere_id == sphere_id, Price.venue_id == venue_id)
        )
    ).all()
    if set(found) != set(book_ids):
        raise DomainError("книги не из сферы заявки или их нет в прайсе площадки")


async def create_client(session: AsyncSession, *, email: str, **fields: Any) -> Client:
    client = Client(email=email, **fields)
    session.add(client)
    await session.flush()
    return client


async def create_application(
    session: AsyncSession,
    *,
    operator_id: int,
    client_id: int,
    representative_id: int,
    sphere_id: int,
    venue_id: int,
    book_ids: list[int],
    social: bool = False,
) -> Application:
    venue = await session.get(Venue, venue_id)
    if venue is None:
        raise NotFound(f"площадка {venue_id}")
    rep = await session.get(Representative, representative_id)
    if rep is None:
        raise NotFound(f"представитель {representative_id}")
    await _check_sphere_at_venue(session, venue_id, sphere_id)
    await _check_books(session, venue_id, sphere_id, book_ids)

    if social:
        kind = "social"
    else:
        kind = "debt" if rep.debt_allowed else "paid"
    now = clock.now()
    app = Application(
        client_id=client_id,
        representative_id=representative_id,
        sphere_id=sphere_id,
        venue_id=venue_id,
        kind=kind,
        stage="draft",
        operator_id=operator_id,
        site_checker_id=venue.site_checker_id,
        created_at=now,
        books=[ApplicationBook(book_id=b) for b in book_ids],
        attempts=[Attempt(no=1, started_at=now)],
    )
    session.add(app)
    await session.flush()
    return app


async def submit_for_review(session: AsyncSession, application_id: int, operator_id: int) -> Application:
    app = await load(session, application_id)
    _require_operator(app, operator_id)
    await bpm.transition(session, app, "on_review", actor="operator")
    if app.review_started_at is None:
        app.review_started_at = clock.now()
    return app


async def assign_reviewer(session: AsyncSession, application_id: int, reviewer_id: int) -> Application:
    """Назначение делает руководитель проверяющих."""
    app = await load(session, application_id)
    if app.stage not in ("draft", "on_review", "needs_rework"):
        raise DomainError("проверяющего назначают до прохождения проверки")
    app.reviewer_id = reviewer_id
    return app


async def update_client(
    session: AsyncSession,
    client_id: int,
    reviewer_id: int,
    *,
    source_application_id: int | None = None,
    **fields: Any,
) -> Client:
    """Данные клиента обновляет проверяющий заявки, на проверке которой выяснилось изменение."""
    if source_application_id is not None:
        app = await load(session, source_application_id)
        if app.reviewer_id != reviewer_id:
            raise AccessDenied("обновляет данные клиента только проверяющий заявки")
    client = await session.get(Client, client_id)
    if client is None:
        raise NotFound(f"клиент {client_id}")
    unknown = set(fields) - set(CLIENT_EDITABLE_FIELDS)
    if unknown:
        raise DomainError(f"неизвестные поля клиента: {sorted(unknown)}")
    session.info["source_application_id"] = source_application_id
    for name, value in fields.items():
        setattr(client, name, value)
    await session.flush()
    return client


async def mark_ready_for_booking(session: AsyncSession, app: Application) -> None:
    if app.booking_reached_at is None:
        app.booking_reached_at = clock.now()
    events.publish(
        session,
        "application.ready_for_booking",
        {"application_id": app.id, "venue_id": app.venue_id, "sphere_id": app.sphere_id},
    )


async def approve(session: AsyncSession, application_id: int, reviewer_id: int) -> Application:
    app = await load(session, application_id)
    if app.reviewer_id is None:
        raise DomainError("на заявку не назначен проверяющий")
    if app.reviewer_id != reviewer_id:
        raise AccessDenied("заявку проверяет другой проверяющий")
    client = await session.get(Client, app.client_id)
    if missing := missing_client_fields(client):
        raise DomainError(f"не хватает данных клиента: {', '.join(missing)}")

    if app.kind == "paid":
        invoice = await billing.active_books_invoice(session, app.id)
        dst = "awaiting_payment" if invoice else "awaiting_invoice"
    else:
        dst = "awaiting_issue"
    await bpm.transition(session, app, dst, actor="reviewer")
    events.publish(session, "application.review_passed", {"application_id": app.id, "kind": app.kind})
    if dst == "awaiting_issue":
        await mark_ready_for_booking(session, app)
    return app


async def return_for_rework(
    session: AsyncSession, application_id: int, reviewer_id: int, reason: str
) -> Application:
    app = await load(session, application_id)
    if app.reviewer_id != reviewer_id:
        raise AccessDenied("заявку проверяет другой проверяющий")
    await bpm.transition(session, app, "needs_rework", actor="reviewer")
    return app


async def change_venue(
    session: AsyncSession, application_id: int, operator_id: int, new_venue_id: int
) -> Application:
    app = await load(session, application_id)
    _require_operator(app, operator_id)
    if app.stage in TERMINAL_STAGES:
        raise DomainError("заявка закрыта")
    if app.kind == "paid" and app.stage in PAID_VENUE_LOCKED_STAGES:
        raise DomainError("после оплаты площадку меняют только через возврат платежа")
    if new_venue_id == app.venue_id:
        return app
    venue = await session.get(Venue, new_venue_id)
    if venue is None:
        raise NotFound(f"площадка {new_venue_id}")
    await _check_sphere_at_venue(session, new_venue_id, app.sphere_id)
    await _check_books(session, new_venue_id, app.sphere_id, app.book_ids)

    old_venue_id = app.venue_id
    app.venue_id = new_venue_id
    app.site_checker_id = venue.site_checker_id
    await session.flush()
    events.publish(
        session,
        "application.venue_changed",
        {
            "application_id": app.id,
            "old_venue_id": old_venue_id,
            "new_venue_id": new_venue_id,
            "kind": app.kind,
            "stage": app.stage,
        },
    )
    return app


async def change_books(
    session: AsyncSession, application_id: int, operator_id: int, book_ids: list[int]
) -> Application:
    app = await load(session, application_id)
    _require_operator(app, operator_id)
    if app.stage not in ("draft", "needs_rework"):
        raise DomainError("книги меняют в черновике или на доработке")
    await _check_books(session, app.venue_id, app.sphere_id, book_ids)
    app.books = [ApplicationBook(book_id=b) for b in book_ids]
    return app


async def archive(
    session: AsyncSession,
    application_id: int,
    *,
    actor: str,
    outcome: str,
    operator_id: int | None = None,
) -> Application:
    app = await load(session, application_id)
    if actor == "operator":
        _require_operator(app, operator_id)
    await bpm.transition(session, app, "archived", actor=actor)
    attempt = app.attempts[-1]
    attempt.ended_at = clock.now()
    attempt.outcome = outcome
    events.publish(session, "application.archived", {"application_id": app.id, "outcome": outcome})
    return app


async def unarchive(
    session: AsyncSession,
    application_id: int,
    operator_id: int,
    *,
    venue_id: int | None = None,
    book_ids: list[int] | None = None,
) -> Application:
    app = await load(session, application_id)
    _require_operator(app, operator_id)
    if app.stage != "archived":
        raise DomainError("заявка не в архиве")
    price_before = await public.books_price(session, app.id)

    if venue_id is not None or book_ids is not None:
        if app.booking_reached_at is not None:
            raise DomainError("заявка уже доходила до записи: площадку и книги не меняют")
        new_venue_id = venue_id or app.venue_id
        new_books = book_ids or app.book_ids
        await _check_sphere_at_venue(session, new_venue_id, app.sphere_id)
        await _check_books(session, new_venue_id, app.sphere_id, new_books)
        if new_venue_id != app.venue_id:
            venue = await session.get(Venue, new_venue_id)
            app.venue_id = new_venue_id
            app.site_checker_id = venue.site_checker_id
        if book_ids is not None:
            app.books = [ApplicationBook(book_id=b) for b in new_books]
        await session.flush()

    price_after = await public.books_price(session, app.id)
    now = clock.now()
    app.attempts.append(Attempt(no=len(app.attempts) + 1, started_at=now))
    app.review_started_at = now
    await bpm.transition(session, app, "on_review", actor="operator")
    events.publish(
        session,
        "application.unarchived",
        {"application_id": app.id, "amount_changed": price_before != price_after},
    )
    return app


async def close(session: AsyncSession, application_id: int, site_checker_id: int) -> Application:
    app = await load(session, application_id)
    if app.site_checker_id != site_checker_id:
        raise AccessDenied("заявку закрывает проверяющий оператор её площадки")
    await bpm.transition(session, app, "closed", actor="site_checker")
    return app
