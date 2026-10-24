from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "inventory"}

# Состояния, в которых экземпляр ещё числится в фонде площадки
ON_BALANCE = ("available", "on_loan", "in_transit")
OPEN_TRANSFER = ("requested", "in_transit")


class Custodian(Base):
    """Хранитель фонда площадки."""

    __tablename__ = "custodians"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(primary_key=True)


class PartnerLibrary(Base):
    __tablename__ = "partner_libraries"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]
    name: Mapped[str]
    daily_penalty: Mapped[Decimal]
    max_active_loans: Mapped[int] = mapped_column(default=5)
    suspended: Mapped[bool] = mapped_column(default=False)


class Copy(Base):
    __tablename__ = "copies"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_no: Mapped[str]
    book_ref: Mapped[int]
    venue_id: Mapped[int]
    state: Mapped[str] = mapped_column(default="available")
    acquired_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("inventory.copies.id"))
    from_venue_id: Mapped[int]
    to_venue_id: Mapped[int]
    status: Mapped[str]
    requested_by: Mapped[int]
    requested_at: Mapped[datetime]
    shipped_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    cancel_reason: Mapped[str | None]


class IllLoan(Base):
    __tablename__ = "ill_loans"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("inventory.copies.id"))
    partner_id: Mapped[int] = mapped_column(ForeignKey("inventory.partner_libraries.id"))
    issued_by: Mapped[int]
    issued_at: Mapped[datetime]
    due_at: Mapped[datetime]
    returned_at: Mapped[datetime | None]
    status: Mapped[str]
    overdue_flagged: Mapped[bool] = mapped_column(default=False)


class IllPenalty(Base):
    __tablename__ = "ill_penalties"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    ill_loan_id: Mapped[int] = mapped_column(ForeignKey("inventory.ill_loans.id"))
    partner_id: Mapped[int] = mapped_column(ForeignKey("inventory.partner_libraries.id"))
    kind: Mapped[str]
    days: Mapped[int] = mapped_column(default=0)
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(default="accruing")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class WriteOff(Base):
    __tablename__ = "write_offs"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("inventory.copies.id"))
    reason: Mapped[str]
    act_no: Mapped[str]
    ill_loan_id: Mapped[int | None] = mapped_column(ForeignKey("inventory.ill_loans.id"))
    note: Mapped[str | None]
    created_by: Mapped[int | None]
    created_at: Mapped[datetime]


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = SCHEMA

    book_ref: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(primary_key=True)
    total: Mapped[int]
    available: Mapped[int]
    updated_at: Mapped[datetime]
