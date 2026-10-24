from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "marketing"}


class Manager(Base):
    """Менеджер рассылок площадки; без venue_id — менеджер всей сети."""

    __tablename__ = "managers"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int]
    venue_id: Mapped[int | None]
    full_name: Mapped[str]


class Audience(Base):
    __tablename__ = "audiences"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    name: Mapped[str]
    created_by: Mapped[int]
    created_at: Mapped[datetime]
    archived: Mapped[bool] = mapped_column(default=False)
    last_campaign_at: Mapped[datetime | None]


class AudienceMember(Base):
    __tablename__ = "audience_members"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    audience_id: Mapped[int] = mapped_column(ForeignKey("marketing.audiences.id"))
    email: Mapped[str]
    full_name: Mapped[str]
    segment: Mapped[str]
    opted_out: Mapped[bool] = mapped_column(default=False)
    added_at: Mapped[datetime]


class CampaignTemplate(Base):
    __tablename__ = "campaign_templates"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int | None]
    audience_group: Mapped[str]
    type: Mapped[str]
    body: Mapped[str]
    updated_at: Mapped[datetime]


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    audience_id: Mapped[int] = mapped_column(ForeignKey("marketing.audiences.id"))
    type: Mapped[str]
    subject: Mapped[str]
    status: Mapped[str]
    created_by: Mapped[int]
    created_at: Mapped[datetime]
    scheduled_at: Mapped[datetime | None]
    launched_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    recipients_count: Mapped[int] = mapped_column(default=0)
    sent_count: Mapped[int] = mapped_column(default=0)
    skipped_count: Mapped[int] = mapped_column(default=0)


class SentMessage(Base):
    __tablename__ = "sent_messages"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("marketing.campaigns.id"))
    template_id: Mapped[int | None] = mapped_column(ForeignKey("marketing.campaign_templates.id"))
    email: Mapped[str]
    segment: Mapped[str]
    body: Mapped[str]
    status: Mapped[str]
    skip_reason: Mapped[str | None]
    is_test: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
    sent_at: Mapped[datetime | None]


class Unsubscription(Base):
    """Отписка адреса от рассылок площадки; без venue_id — от всех рассылок сети."""

    __tablename__ = "unsubscriptions"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    venue_id: Mapped[int | None]
    reason: Mapped[str]
    created_at: Mapped[datetime]
