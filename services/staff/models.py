from datetime import date, datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from libs.db import Base

SCHEMA = {"schema": "staff"}


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str | None]
    passport: Mapped[str | None]
    snils: Mapped[str | None]
    birth_date: Mapped[date | None]
    role: Mapped[str]
    hired_at: Mapped[datetime]
    dismissed_at: Mapped[datetime | None]
    updated_at: Mapped[datetime]

    @property
    def active(self) -> bool:
        return self.dismissed_at is None


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    max_shift_staff: Mapped[int]
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("staff.employees.id"))


class Assignment(Base):
    """Закрепление сотрудника за площадкой; текущее — без ended_at."""

    __tablename__ = "assignments"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("staff.sites.id"))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]


class ClearanceKind(Base):
    __tablename__ = "clearance_kinds"
    __table_args__ = SCHEMA

    code: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    valid_days: Mapped[int]
    briefing_topic: Mapped[str | None]
    # Изменение этих полей карточки требует повторной проверки и отзывает допуск.
    recheck_fields: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("staff.sites.id"))
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    capacity: Mapped[int]
    min_staff: Mapped[int] = mapped_column(default=1)
    required_clearance: Mapped[str | None] = mapped_column(ForeignKey("staff.clearance_kinds.code"))
    status: Mapped[str] = mapped_column(default="planned")
    understaffed: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))


class ShiftMember(Base):
    __tablename__ = "shift_members"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    shift_id: Mapped[int] = mapped_column(ForeignKey("staff.shifts.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    status: Mapped[str] = mapped_column(default="assigned")
    assigned_at: Mapped[datetime]
    removed_at: Mapped[datetime | None]
    removed_reason: Mapped[str | None]


class Briefing(Base):
    __tablename__ = "briefings"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("staff.sites.id"))
    topic: Mapped[str]
    instructor_id: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    held_at: Mapped[datetime]


class Clearance(Base):
    __tablename__ = "clearances"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    kind: Mapped[str] = mapped_column(ForeignKey("staff.clearance_kinds.code"))
    briefing_id: Mapped[int | None] = mapped_column(ForeignKey("staff.briefings.id"))
    granted_by: Mapped[int] = mapped_column(ForeignKey("staff.employees.id"))
    granted_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(default="active")
    revoked_at: Mapped[datetime | None]
    revoke_reason: Mapped[str | None]


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("staff.employees.id"))
    site_id: Mapped[int] = mapped_column(ForeignKey("staff.sites.id"))
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("staff.shifts.id"))
    kind: Mapped[str]
    body: Mapped[str]
    created_at: Mapped[datetime]
    read_at: Mapped[datetime | None]
