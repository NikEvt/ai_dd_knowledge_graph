from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "billing"}


class AccountantAssignment(Base):
    __tablename__ = "accountant_assignments"
    __table_args__ = SCHEMA

    application_id: Mapped[int] = mapped_column(primary_key=True)
    accountant_id: Mapped[int]


class Fine(Base):
    __tablename__ = "fines"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    loan_id: Mapped[int | None]
    kind: Mapped[str]
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(default="open")
    paid_outside: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int]
    kind: Mapped[str]
    fine_id: Mapped[int | None] = mapped_column(ForeignKey("billing.fines.id"))
    amount: Mapped[Decimal]
    status: Mapped[str]
    issued_at: Mapped[datetime]
    payment_clock_started_at: Mapped[datetime]
    venue_id: Mapped[int]
    requisites: Mapped[dict[str, Any]]
    cancel_reason: Mapped[str | None]


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("billing.invoices.id"))
    amount: Mapped[Decimal]
    linked_at: Mapped[datetime]
    linked_by: Mapped[int]
    overpayment: Mapped[bool] = mapped_column(default=False)
    unlinked_at: Mapped[datetime | None]
    unlink_reason: Mapped[str | None]
    refunded: Mapped[bool] = mapped_column(default=False)


class FineRate(Base):
    __tablename__ = "fine_rates"
    __table_args__ = SCHEMA

    representative_id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[Decimal]
