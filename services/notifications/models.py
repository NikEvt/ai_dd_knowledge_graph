from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "notifications"}


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    kind_group: Mapped[str]
    type: Mapped[str]
    body: Mapped[str]


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    recipients: Mapped[list[Any]]
    type: Mapped[str]
    template_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.templates.id"))
    body: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime]
