"""T06: отдельные шаблоны писем для заявок в долг (группа debt) с откатом на шаблоны платных."""

from datetime import timedelta

from sqlalchemy import select
from support import HISTORY, MSK, REP_DEBT, T0, act, book, new_application, paid_application, pass_review, slot

from libs import db
from services.notifications import service as notifications
from services.notifications.models import Email


async def _emails(app_id):
    async with db.sessionmaker()() as s:
        return list((await s.scalars(select(Email).where(Email.application_id == app_id).order_by(Email.id))).all())


async def _set_debt_templates() -> None:
    for type_ in ("booking", "cancel"):
        await act(
            notifications.set_template,
            venue_id=MSK,
            kind_group="debt",
            type_=type_,
            body=f"V1 debt {type_}: $starts_at",
        )


async def test_t06_debt_uses_debt_template() -> None:
    await _set_debt_templates()
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    [email] = await _emails(app_id)
    assert email.body.startswith("V1 debt booking")


async def test_t06_debt_falls_back_to_paid_template() -> None:
    app_id = await new_application(rep=REP_DEBT)
    await pass_review(app_id)
    await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    [email] = await _emails(app_id)
    assert email.status == "sent"
    assert email.body.startswith("V1 paid booking")


async def test_t06_paid_ignores_debt_template() -> None:
    await _set_debt_templates()
    app_id, _ = await paid_application()
    await book(app_id, await slot(MSK, HISTORY, T0 + timedelta(days=5)))
    [email] = await _emails(app_id)
    assert email.body.startswith("V1 paid booking")
