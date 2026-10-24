from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "lectures"}


class VenueCapacityLimit(Base):
    """Реплика лимита мест площадки (обновляется событием lectures.venue_limit_changed)."""

    __tablename__ = "venue_capacity_limits"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(primary_key=True)
    max_capacity: Mapped[int]
    updated_at: Mapped[datetime]


class Lecture(Base):
    __tablename__ = "events"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    venue_id: Mapped[int]
    organizer_id: Mapped[int]
    starts_at: Mapped[datetime]
    capacity: Mapped[int]
    # Организатор задал число мест сам, и оно меньше лимита площадки.
    capacity_manual: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(default="scheduled")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("lectures.events.id"))
    listener_id: Mapped[int]
    status: Mapped[str]
    source: Mapped[str] = mapped_column(default="direct")
    created_at: Mapped[datetime]
    cancelled_at: Mapped[datetime | None]
    cancel_reason: Mapped[str | None]
    attended_at: Mapped[datetime | None]


class WaitlistEntry(Base):
    __tablename__ = "waitlist"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("lectures.events.id"))
    listener_id: Mapped[int]
    status: Mapped[str] = mapped_column(default="waiting")
    created_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    listener_id: Mapped[int]
    event_id: Mapped[int] = mapped_column(ForeignKey("lectures.events.id"))
    kind: Mapped[str]
    body: Mapped[str]
    dedup_key: Mapped[str]
    created_at: Mapped[datetime]
    sent_at: Mapped[datetime | None]
