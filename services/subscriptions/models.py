from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "subscriptions"}


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]
    name: Mapped[str]
    kind: Mapped[str]
    monthly_fee: Mapped[Decimal]
    max_books: Mapped[int] = mapped_column(default=5)
    archived: Mapped[bool] = mapped_column(default=False)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    client_ref: Mapped[str]
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.plans.id"))
    status: Mapped[str] = mapped_column(default="pending")
    holder_name: Mapped[str]
    passport: Mapped[str | None]
    birth_date: Mapped[date | None]
    holder_check: Mapped[str] = mapped_column(default="pending")
    employer_ref: Mapped[str | None]
    paid_until: Mapped[date | None]
    # paid_until, для которого уже отправлено напоминание о конце льготного периода
    reminded_for: Mapped[date | None]
    created_at: Mapped[datetime]
    activated_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.subscriptions.id"))
    period_start: Mapped[date]
    period_end: Mapped[date]
    amount: Mapped[Decimal]
    paid_total: Mapped[Decimal] = mapped_column(default=Decimal(0))
    status: Mapped[str] = mapped_column(default="open")
    issued_at: Mapped[datetime]


class Payment(Base):
    """Платёж по счёту. Остаток счёта (paid_total) пересчитывает триггер в БД."""

    __tablename__ = "payments"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.invoices.id"))
    amount: Mapped[Decimal]
    external_ref: Mapped[str | None]
    paid_at: Mapped[datetime]


class Refund(Base):
    """Возврат денег по счёту закрытого абонемента; проводит бухгалтерия."""

    __tablename__ = "refunds"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.subscriptions.id"))
    invoice_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.invoices.id"))
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime]
    done_at: Mapped[datetime | None]


class StatusChange(Base):
    """Журнал смены статусов; пишется триггером, из кода только читается."""

    __tablename__ = "status_history"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.subscriptions.id"))
    old_status: Mapped[str]
    new_status: Mapped[str]
    changed_at: Mapped[datetime]


class Notice(Base):
    """Уведомление держателю абонемента (рассылает отдельный воркер)."""

    __tablename__ = "notices"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.subscriptions.id"))
    kind: Mapped[str]
    body: Mapped[str]
    created_at: Mapped[datetime]
