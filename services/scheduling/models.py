from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "scheduling"}


class VenueLimit(Base):
    """Реплика лимита мест площадки из админки (обновляется событием venue.settings_changed)."""

    __tablename__ = "venue_limits"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(primary_key=True)
    max_capacity: Mapped[int]


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    sphere_id: Mapped[int]
    starts_at: Mapped[datetime]
    capacity: Mapped[int]
    removed: Mapped[bool] = mapped_column(default=False)


class BookingLink(Base):
    __tablename__ = "booking_links"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    token: Mapped[str]
    purpose: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    slot_id: Mapped[int] = mapped_column(ForeignKey("scheduling.slots.id"))
    purpose: Mapped[str]
    status: Mapped[str]
    booked_by: Mapped[str]
    created_at: Mapped[datetime]


class Hold(Base):
    """Книги, закреплённые за заявкой с момента записи за книгами."""

    __tablename__ = "holds"
    __table_args__ = SCHEMA

    application_id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(primary_key=True)


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    book_id: Mapped[int]
    issued_at: Mapped[datetime]
    due_at: Mapped[datetime]
    returned_at: Mapped[datetime | None]
    status: Mapped[str]
    damaged: Mapped[bool] = mapped_column(default=False)
    overdue_flagged: Mapped[bool] = mapped_column(default=False)
