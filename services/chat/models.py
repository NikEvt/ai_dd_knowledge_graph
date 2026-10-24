from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "chat"}

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    author_id: Mapped[int | None]
    body: Mapped[str]
    is_event: Mapped[bool]
    created_at: Mapped[datetime]
