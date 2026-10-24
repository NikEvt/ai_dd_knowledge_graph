from datetime import timedelta

from sqlalchemy import select

from libs import db
from services.notifications.models import Email
from services.scheduling import service as scheduling
from tests.factories import HISTORY, MSK, T0, act, book, new_application, paid_application, pass_review, slot


async def emails(app_id: int) -> list[Email]:
    async with db.sessionmaker()() as s:
        return list(
            (await s.scalars(select(Email).where(Email.application_id == app_id).order_by(Email.id))).all()
        )


async def test_booking_email_goes_to_client_and_representative() -> None:
    app_id, _ = await paid_application()
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    await book(app_id, slot_id)
    [email] = await emails(app_id)
    assert email.type == "booking"
    assert email.body.startswith("V1 paid booking")
    assert email.recipients == ["anna@example.org", "rep1@example.org"]


async def test_social_uses_social_templates() -> None:
    app_id = await new_application(social=True)
    await pass_review(app_id)
    slot_id = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    await book(app_id, slot_id)
    [email] = await emails(app_id)
    assert email.body.startswith("V1 social booking")


async def test_reschedule_sends_cancel_and_booking() -> None:
    app_id, _ = await paid_application()
    first = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    second = await slot(MSK, HISTORY, T0 + timedelta(days=6))
    booking_id = await book(app_id, first)
    await act(scheduling.reschedule, booking_id, second, by="client")
    assert [e.type for e in await emails(app_id)] == ["booking", "cancel", "booking"]
