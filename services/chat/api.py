from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.chat import service

router = APIRouter(prefix="/applications/{application_id}/messages", tags=["chat"])
Session = Annotated[AsyncSession, Depends(session)]


class MessageIn(BaseModel):
    author_id: int
    body: str


class MessageOut(BaseModel):
    id: int
    author_id: int | None
    body: str
    is_event: bool
    created_at: datetime


def _out(m) -> MessageOut:
    return MessageOut(
        id=m.id, author_id=m.author_id, body=m.body, is_event=m.is_event, created_at=m.created_at
    )


@router.get("")
async def list_(application_id: int, viewer_id: int, role: str, s: Session) -> list[MessageOut]:
    return [_out(m) for m in await service.list_messages(s, application_id, viewer_id, role)]


@router.post("", status_code=201)
async def post(application_id: int, body: MessageIn, s: Session) -> MessageOut:
    return _out(await service.post_message(s, application_id, body.author_id, body.body))
