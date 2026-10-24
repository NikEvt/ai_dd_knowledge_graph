"""T02: срок пользования книгами — 21 день вместо месяца."""

from datetime import timedelta

from sqlalchemy import select
from support import CHECKER, MSK, act, issue, paid_application, travel

from libs import clock, db
from services.billing.models import Fine
from services.scheduling import jobs
from services.scheduling import service as scheduling
from services.scheduling.models import Loan


async def _loans(app_id):
    async with db.sessionmaker()() as s:
        return list((await s.scalars(select(Loan).where(Loan.application_id == app_id))).all())


async def _fines(app_id):
    async with db.sessionmaker()() as s:
        return list((await s.scalars(select(Fine).where(Fine.application_id == app_id))).all())


async def test_t02_due_date_is_21_days() -> None:
    app_id, _ = await paid_application()
    await issue(app_id)
    [loan] = await _loans(app_id)
    assert loan.due_at - loan.issued_at == timedelta(days=21)


async def test_t02_overdue_after_21_days() -> None:
    app_id, _ = await paid_application()
    await issue(app_id)
    [loan] = await _loans(app_id)

    travel(loan.issued_at + timedelta(days=20))
    assert await act(jobs.flag_overdue, clock.now()) == []

    travel(loan.issued_at + timedelta(days=22))
    assert await act(jobs.flag_overdue, clock.now()) == [loan.id]
    [fine] = await _fines(app_id)
    assert fine.kind == "overdue"


async def test_t02_return_in_time_no_fine() -> None:
    app_id, _ = await paid_application()
    await issue(app_id)
    [loan] = await _loans(app_id)
    travel(loan.issued_at + timedelta(days=20))
    await act(scheduling.return_book, loan.id, CHECKER[MSK])
    travel(loan.issued_at + timedelta(days=40))
    assert await act(jobs.flag_overdue, clock.now()) == []
