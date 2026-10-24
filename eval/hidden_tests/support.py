"""Снимок tests/factories.py на v0 для скрытых тестов: не зависит от изменений исполнителя в tests/."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from libs import clock, db, events
from services.applications import service as apps
from services.applications.models import (
    Book,
    Client,
    Price,
    Representative,
    Sphere,
    Venue,
    VenueSphere,
)
from services.billing import service as billing
from services.billing.models import FineRate, Invoice
from services.notifications.models import Template
from services.scheduling import service as scheduling
from services.scheduling.models import VenueLimit

T0 = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)

OPERATOR, OPERATOR_2 = 101, 102
REVIEWER, REVIEWER_2 = 201, 202
CHECKER = {1: 301, 2: 302, 3: 303}
ACCOUNTANT, ACCOUNTANT_2 = 401, 402
CHIEF = 501
ADMIN = 601

# Справочники
MSK, KZN, TVR = 1, 2, 3
HISTORY, LAW = 1, 2
BOOK_H1, BOOK_H2, BOOK_L1 = 1, 2, 3
REP_PAID, REP_DEBT, REP_PLAIN = 1, 2, 3
CLIENT_A, CLIENT_B, CLIENT_INCOMPLETE = 1, 2, 3

SEEDED_TABLES = (
    "applications.venues",
    "applications.spheres",
    "applications.books",
    "applications.representatives",
    "applications.clients",
)


async def truncate_all() -> None:
    names = ", ".join(f"{t.schema}.{t.name}" for t in db.Base.metadata.sorted_tables)
    async with db.engine().begin() as conn:
        await conn.exec_driver_sql(f"TRUNCATE {names} RESTART IDENTITY CASCADE")


async def seed() -> None:
    async with db.sessionmaker().begin() as s:
        s.add_all(
            [
                Venue(
                    id=MSK,
                    city="Москва",
                    requisites={"inn": "7701000001"},
                    max_slot_capacity=3,
                    site_checker_id=CHECKER[MSK],
                ),
                Venue(
                    id=KZN,
                    city="Казань",
                    requisites={"inn": "1601000002"},
                    max_slot_capacity=3,
                    site_checker_id=CHECKER[KZN],
                ),
                Venue(
                    id=TVR, city="Тверь", requisites=None, max_slot_capacity=2, site_checker_id=CHECKER[TVR]
                ),
                Sphere(id=HISTORY, name="История"),
                Sphere(id=LAW, name="Право"),
                Representative(
                    id=REP_PAID, name="Агентство Север", email="rep1@example.org", markup_pct=Decimal(10)
                ),
                Representative(id=REP_DEBT, name="Фонд Юг", email="rep2@example.org", debt_allowed=True),
                Representative(id=REP_PLAIN, name="Частный агент", email="rep3@example.org"),
                Client(
                    id=CLIENT_A,
                    full_name="Анна Петрова",
                    passport="4510 000001",
                    birth_date=date(1990, 5, 1),
                    email="anna@example.org",
                ),
                Client(
                    id=CLIENT_B,
                    full_name="Борис Сидоров",
                    passport="4510 000002",
                    birth_date=date(1985, 2, 3),
                    email="boris@example.org",
                ),
                Client(
                    id=CLIENT_INCOMPLETE,
                    full_name="Вера Ким",
                    passport=None,
                    birth_date=None,
                    email="vera@example.org",
                ),
            ]
        )
        await s.flush()
        s.add_all(
            [
                Book(id=BOOK_H1, sphere_id=HISTORY, title="История Руси"),
                Book(id=BOOK_H2, sphere_id=HISTORY, title="Новое время"),
                Book(id=BOOK_L1, sphere_id=LAW, title="Гражданское право"),
                VenueSphere(venue_id=MSK, sphere_id=HISTORY),
                VenueSphere(venue_id=MSK, sphere_id=LAW),
                VenueSphere(venue_id=KZN, sphere_id=HISTORY),
                VenueSphere(venue_id=KZN, sphere_id=LAW),
                VenueSphere(venue_id=TVR, sphere_id=HISTORY),
            ]
        )
        await s.flush()
        prices = {
            MSK: {BOOK_H1: 100, BOOK_H2: 150, BOOK_L1: 200},
            KZN: {BOOK_H1: 120, BOOK_H2: 160, BOOK_L1: 210},
            TVR: {BOOK_H1: 90, BOOK_H2: 140},
        }
        for venue_id, row in prices.items():
            for book_id, price in row.items():
                s.add(Price(venue_id=venue_id, book_id=book_id, price=Decimal(price)))
        for venue_id, limit in ((MSK, 3), (KZN, 3), (TVR, 2)):
            s.add(VenueLimit(venue_id=venue_id, max_capacity=limit))
        for venue_id in (MSK, KZN):
            for group in ("paid", "social"):
                for type_ in ("booking", "cancel"):
                    s.add(
                        Template(
                            venue_id=venue_id,
                            kind_group=group,
                            type=type_,
                            body=f"V{venue_id} {group} {type_}: $starts_at",
                        )
                    )
        for type_ in ("booking", "cancel"):
            s.add(Template(venue_id=TVR, kind_group="paid", type=type_, body=f"V3 paid {type_}: $starts_at"))
        for rep in (REP_PAID, REP_DEBT, REP_PLAIN):
            for venue_id in (MSK, KZN, TVR):
                for kind, amount in (("overdue", 50), ("lost", 500), ("damaged", 200)):
                    s.add(
                        FineRate(representative_id=rep, venue_id=venue_id, kind=kind, amount=Decimal(amount))
                    )
    async with db.engine().begin() as conn:
        for table in SEEDED_TABLES:
            await conn.exec_driver_sql(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 100)")
        # Если исполнитель добавил обязательные поля клиента (T05), заполняем их у полных клиентов.
        has_snils = await conn.exec_driver_sql(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'applications' AND table_name = 'clients' AND column_name = 'snils'"
        )
        if has_snils.first():
            await conn.exec_driver_sql(
                f"UPDATE applications.clients SET snils = '000-000-000 ' || lpad(id::text, 2, '0') "
                f"WHERE id IN ({CLIENT_A}, {CLIENT_B})"
            )


async def act(fn, *args, **kwargs):
    """Выполнить шаг в отдельной транзакции и доставить все события."""
    async with db.sessionmaker().begin() as s:
        result = await fn(s, *args, **kwargs)
    await events.dispatch_pending()
    return result


async def read(fn, *args, **kwargs):
    async with db.sessionmaker()() as s:
        return await fn(s, *args, **kwargs)


def travel(at: datetime) -> None:
    clock.freeze(at)


async def new_application(
    *,
    client: int = CLIENT_A,
    rep: int = REP_PAID,
    sphere: int = HISTORY,
    venue: int = MSK,
    books: tuple[int, ...] = (BOOK_H1,),
    social: bool = False,
    operator: int = OPERATOR,
) -> int:
    app = await act(
        apps.create_application,
        operator_id=operator,
        client_id=client,
        representative_id=rep,
        sphere_id=sphere,
        venue_id=venue,
        book_ids=list(books),
        social=social,
    )
    return app.id


async def submit(app_id: int, operator: int = OPERATOR, reviewer: int = REVIEWER) -> None:
    await act(apps.submit_for_review, app_id, operator)
    await act(apps.assign_reviewer, app_id, reviewer)


async def pass_review(app_id: int, operator: int = OPERATOR, reviewer: int = REVIEWER) -> None:
    await submit(app_id, operator, reviewer)
    await act(apps.approve, app_id, reviewer)


async def invoice(app_id: int, accountant: int = ACCOUNTANT) -> Invoice:
    await act(billing.take_application, app_id, accountant)
    return await act(billing.issue_books_invoice, app_id, accountant)


async def pay(inv: Invoice, amount: Decimal | None = None) -> None:
    await act(billing.link_payment, inv.id, inv.amount if amount is None else amount, CHIEF)


async def paid_application(**kwargs) -> tuple[int, Invoice]:
    app_id = await new_application(**kwargs)
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv)
    return app_id, inv


async def application(app_id: int):
    return await read(apps.load, app_id)


async def stage(app_id: int) -> str:
    return (await application(app_id)).stage


async def slot(venue: int, sphere: int, starts_at: datetime, capacity: int | None = None) -> int:
    created = await act(
        scheduling.create_slot,
        site_checker_id=CHECKER[venue],
        venue_id=venue,
        sphere_id=sphere,
        starts_at=starts_at,
        capacity=capacity,
    )
    return created.id


async def token(app_id: int) -> str | None:
    link = await read(scheduling.active_link, app_id)
    return link.token if link else None


async def book(app_id: int, slot_id: int, by: str = "client") -> int:
    booking = await act(scheduling.book, token=await token(app_id), slot_id=slot_id, booked_by=by)
    return booking.id


async def issue(
    app_id: int, venue: int = MSK, sphere: int = HISTORY, day: datetime | None = None
) -> list[int]:
    """Записать на выдачу и выдать книги; возвращает id выдач."""
    when = day or T0 + timedelta(days=3, hours=1)
    slot_id = await slot(venue, sphere, when)
    booking_id = await book(app_id, slot_id)
    travel(when)
    loans = await act(scheduling.issue_books, booking_id, CHECKER[venue])
    return [loan.id for loan in loans]
