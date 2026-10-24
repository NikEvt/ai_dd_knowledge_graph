"""Письма клиенту и представителю: о записи и об отмене записи."""

from string import Template as Text
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock
from services.applications import public as applications
from services.notifications.config import TEMPLATE_GROUP
from services.notifications.models import Email, Template


async def set_template(
    session: AsyncSession, *, venue_id: int, kind_group: str, type_: str, body: str
) -> Template:
    tpl = await session.scalar(
        select(Template).where(
            Template.venue_id == venue_id, Template.kind_group == kind_group, Template.type == type_
        )
    )
    if tpl is None:
        tpl = Template(venue_id=venue_id, kind_group=kind_group, type=type_, body=body)
        session.add(tpl)
    else:
        tpl.body = body
    await session.flush()
    return tpl


async def find_template(session: AsyncSession, venue_id: int, kind: str, type_: str) -> Template | None:
    return await session.scalar(
        select(Template).where(
            Template.venue_id == venue_id,
            Template.kind_group == TEMPLATE_GROUP[kind],
            Template.type == type_,
        )
    )


async def send(
    session: AsyncSession, *, application_id: int, type_: str, venue_id: int, context: dict[str, Any]
) -> Email:
    brief = await applications.get_brief(session, application_id)
    tpl = await find_template(session, venue_id, brief.kind, type_)
    email = Email(
        application_id=application_id,
        recipients=await applications.recipients(session, application_id),
        type=type_,
        template_id=tpl.id if tpl else None,
        body=Text(tpl.body).safe_substitute(context) if tpl else "",
        status="sent" if tpl else "no_template",
        created_at=clock.now(),
    )
    session.add(email)
    await session.flush()
    return email
