"""Чат заявки: переписка закреплённых сотрудников и лента событий."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock
from libs.errors import AccessDenied, DomainError
from services.applications import public as applications
from services.billing import public as billing
from services.chat.models import Message

NO_CHAT_ROLES = ("chief_accountant", "reviewer_lead")


async def participants(session: AsyncSession, application_id: int) -> set[int]:
    brief = await applications.get_brief(session, application_id)
    ids = {brief.operator_id, brief.site_checker_id}
    if brief.reviewer_id:
        ids.add(brief.reviewer_id)
    if accountant := await billing.accountant_of(session, application_id):
        ids.add(accountant)
    return ids


async def post_message(session: AsyncSession, application_id: int, author_id: int, body: str) -> Message:
    brief = await applications.get_brief(session, application_id)
    if brief.stage in ("closed", "closed_duplicate"):
        raise DomainError("после закрытия заявки чат доступен только для чтения")
    if author_id not in await participants(session, application_id):
        raise AccessDenied("писать в чат могут только закреплённые за заявкой сотрудники")
    msg = Message(
        application_id=application_id, author_id=author_id, body=body, is_event=False, created_at=clock.now()
    )
    session.add(msg)
    await session.flush()
    return msg


async def log_event(session: AsyncSession, application_id: int, text: str) -> Message:
    msg = Message(
        application_id=application_id, author_id=None, body=text, is_event=True, created_at=clock.now()
    )
    session.add(msg)
    await session.flush()
    return msg


async def list_messages(
    session: AsyncSession, application_id: int, viewer_id: int, role: str
) -> list[Message]:
    if role in NO_CHAT_ROLES:
        raise AccessDenied("эта роль не видит чат заявки")
    if role != "admin" and viewer_id not in await participants(session, application_id):
        raise AccessDenied("чат видят только закреплённые сотрудники и администратор")
    rows = await session.scalars(
        select(Message).where(Message.application_id == application_id).order_by(Message.id)
    )
    return list(rows.all())
