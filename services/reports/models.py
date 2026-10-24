from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "reports"}

FINISHED = ("completed", "failed", "cancelled")
IN_FLIGHT = ("requested", "running")


class MetricSnapshot(Base):
    """Значение метрики за день в разрезе (dimension пустая строка — без разреза)."""

    __tablename__ = "metric_snapshots"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    metric: Mapped[str]
    dimension: Mapped[str] = mapped_column(default="")
    day: Mapped[date]
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    taken_at: Mapped[datetime]


class ReportDefinition(Base):
    __tablename__ = "report_definitions"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]
    title: Mapped[str]
    kind: Mapped[str]
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    owner_id: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ExportSchedule(Base):
    __tablename__ = "export_schedules"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("reports.report_definitions.id"))
    every_hours: Mapped[int]
    next_run_at: Mapped[datetime]
    recipients: Mapped[list[Any]] = mapped_column(default=list)
    created_by: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    last_enqueued_at: Mapped[datetime | None]
    created_at: Mapped[datetime]


class ReportRun(Base):
    __tablename__ = "report_runs"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("reports.report_definitions.id"))
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("reports.export_schedules.id"))
    scheduled_for: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(default="requested")
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    body: Mapped[dict[str, Any] | None]
    error: Mapped[str | None]
    requested_by: Mapped[int]
    requested_at: Mapped[datetime]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class RunNotification(Base):
    __tablename__ = "run_notifications"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("reports.report_runs.id", ondelete="CASCADE"))
    recipient_id: Mapped[int]
    kind: Mapped[str]
    body: Mapped[str]
    created_at: Mapped[datetime]
    read_at: Mapped[datetime | None]
