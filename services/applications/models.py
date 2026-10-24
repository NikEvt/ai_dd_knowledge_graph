from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.db import Base

SCHEMA = {"schema": "applications"}


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str]
    requisites: Mapped[dict[str, Any] | None]
    max_slot_capacity: Mapped[int]
    site_checker_id: Mapped[int]


class Sphere(Base):
    __tablename__ = "spheres"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class VenueSphere(Base):
    __tablename__ = "venue_spheres"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(ForeignKey("applications.venues.id"), primary_key=True)
    sphere_id: Mapped[int] = mapped_column(ForeignKey("applications.spheres.id"), primary_key=True)
    active: Mapped[bool] = mapped_column(default=True)


class Book(Base):
    __tablename__ = "books"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    sphere_id: Mapped[int] = mapped_column(ForeignKey("applications.spheres.id"))
    title: Mapped[str]


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = SCHEMA

    venue_id: Mapped[int] = mapped_column(ForeignKey("applications.venues.id"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("applications.books.id"), primary_key=True)
    price: Mapped[Decimal]


class Representative(Base):
    __tablename__ = "representatives"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    markup_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    debt_allowed: Mapped[bool] = mapped_column(default=False)


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str | None]
    passport: Mapped[str | None]
    birth_date: Mapped[date | None]
    email: Mapped[str]
    updated_at: Mapped[datetime | None]


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("applications.clients.id"))
    representative_id: Mapped[int] = mapped_column(ForeignKey("applications.representatives.id"))
    sphere_id: Mapped[int] = mapped_column(ForeignKey("applications.spheres.id"))
    venue_id: Mapped[int] = mapped_column(ForeignKey("applications.venues.id"))
    kind: Mapped[str]
    stage: Mapped[str]
    operator_id: Mapped[int]
    reviewer_id: Mapped[int | None]
    site_checker_id: Mapped[int]
    review_started_at: Mapped[datetime | None]
    booking_reached_at: Mapped[datetime | None]
    created_at: Mapped[datetime]

    books: Mapped[list[ApplicationBook]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    attempts: Mapped[list[Attempt]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="Attempt.no"
    )

    @property
    def book_ids(self) -> list[int]:
        return sorted(b.book_id for b in self.books)


class ApplicationBook(Base):
    __tablename__ = "application_books"
    __table_args__ = SCHEMA

    application_id: Mapped[int] = mapped_column(ForeignKey("applications.applications.id"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("applications.books.id"), primary_key=True)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = SCHEMA

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.applications.id"))
    no: Mapped[int]
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    outcome: Mapped[str | None]
