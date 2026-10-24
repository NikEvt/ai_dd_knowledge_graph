from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "halls"}


class HallManager(Base):
    """Менеджер, закреплённый за площадкой: ведёт её залы и брони."""

    __tablename__ = "hall_managers"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(primary_key=True)


class Hall(Base):
    __tablename__ = "halls"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    name: Mapped[str]
    capacity: Mapped[int]
    hourly_rate: Mapped[Decimal]
    active: Mapped[bool] = mapped_column(default=True)


class HallBooking(Base):
    __tablename__ = "hall_bookings"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.halls.id"))
    venue_id: Mapped[int]
    client_ref: Mapped[str]
    event_kind: Mapped[str]
    guests: Mapped[int]
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(default="draft")
    created_by: Mapped[int]
    created_at: Mapped[datetime]
    confirmed_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    cancel_reason: Mapped[str | None]


class BookingHistory(Base):
    """Заполняется триггером при каждой смене статуса брони."""

    __tablename__ = "hall_booking_history"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("halls.hall_bookings.id"))
    old_status: Mapped[str | None]
    new_status: Mapped[str]
    changed_at: Mapped[datetime]


class HallInvoice(Base):
    __tablename__ = "hall_invoices"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("halls.hall_bookings.id"))
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(default="open")
    issued_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]


class HallPayment(Base):
    __tablename__ = "hall_payments"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("halls.hall_invoices.id"))
    amount: Mapped[Decimal]
    external_ref: Mapped[str | None]
    recorded_by: Mapped[int]
    paid_at: Mapped[datetime]


class HallTemplate(Base):
    __tablename__ = "hall_templates"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int]
    kind_group: Mapped[str]
    type: Mapped[str]
    body: Mapped[str]


class HallEmail(Base):
    __tablename__ = "hall_emails"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("halls.hall_bookings.id"))
    client_ref: Mapped[str]
    type: Mapped[str]
    template_id: Mapped[int | None] = mapped_column(ForeignKey("halls.hall_templates.id"))
    body: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime]
