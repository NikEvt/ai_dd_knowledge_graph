from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "partners"}


class OnboardingRequest(Base):
    __tablename__ = "onboarding_requests"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    inn: Mapped[str]
    kpp: Mapped[str | None]
    legal_name: Mapped[str | None]
    contact_name: Mapped[str]
    contact_email: Mapped[str]
    contact_phone: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="open")
    submitted_at: Mapped[datetime]
    decided_at: Mapped[datetime | None]
    decided_by: Mapped[int | None]
    reject_reason: Mapped[str | None]
    partner_id: Mapped[int | None]


class Partner(Base):
    __tablename__ = "partners"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    inn: Mapped[str]
    kpp: Mapped[str | None]
    legal_name: Mapped[str | None]
    contact_name: Mapped[str | None]
    contact_email: Mapped[str | None]
    contact_phone: Mapped[str | None]
    manager_id: Mapped[int]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.partners.id"))
    number: Mapped[str]
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    credit_allowed: Mapped[bool] = mapped_column(default=False)
    credit_limit: Mapped[Decimal] = mapped_column(default=Decimal(0))
    status: Mapped[str] = mapped_column(default="draft")
    suspend_reason: Mapped[str | None]
    valid_from: Mapped[date]
    valid_to: Mapped[date]
    activated_at: Mapped[datetime | None]
    created_at: Mapped[datetime]


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("partners.contracts.id"))
    external_ref: Mapped[str]
    amount: Mapped[Decimal]
    on_credit: Mapped[bool]
    status: Mapped[str]
    created_at: Mapped[datetime]
    due_at: Mapped[datetime | None]
    prepaid_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    paid_at: Mapped[datetime | None]
    overdue_flagged: Mapped[bool] = mapped_column(default=False)


class Payout(Base):
    """Ведомость выплаты комиссии партнёру за месяц."""

    __tablename__ = "payouts"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.partners.id"))
    period: Mapped[date]
    total: Mapped[Decimal] = mapped_column(default=Decimal(0))
    commissions_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="open")


class Commission(Base):
    __tablename__ = "commissions"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("partners.deals.id"))
    contract_id: Mapped[int] = mapped_column(ForeignKey("partners.contracts.id"))
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.partners.id"))
    base_amount: Mapped[Decimal]
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    amount: Mapped[Decimal]
    accrued_at: Mapped[datetime]
    payout_id: Mapped[int | None] = mapped_column(ForeignKey("partners.payouts.id"))


class ContractHistory(Base):
    """Журнал изменений условий договора, ведёт триггер trg_contract_history."""

    __tablename__ = "contract_history"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("partners.contracts.id"))
    field: Mapped[str]
    old_value: Mapped[str | None]
    new_value: Mapped[str | None]
    changed_at: Mapped[datetime]
