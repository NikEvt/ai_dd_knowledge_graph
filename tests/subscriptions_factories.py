"""Тарифы, абонементы и оплата для тестов сервиса абонементов."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from services.subscriptions import service
from services.subscriptions.models import Invoice, Notice, Payment, StatusChange
from tests.factories import act, read

CLIENT_1, CLIENT_2 = "client-1", "client-2"
PASSPORT = "4510 123456"
ADULT = date(1990, 5, 1)
STUDENT = date(2006, 9, 15)
SENIOR = date(1958, 1, 20)


async def plans() -> dict[str, int]:
    created = {}
    for code, name, kind, fee in (
        ("std", "Обычный", "regular", Decimal(600)),
        ("soc", "Социальный", "social", Decimal(150)),
        ("corp", "Корпоративный", "corporate", Decimal(450)),
        ("std-plus", "Обычный плюс", "regular", Decimal(900)),
    ):
        plan = await act(service.create_plan, code=code, name=name, kind=kind, monthly_fee=fee)
        created[code] = plan.id
    return created


async def subscribe(
    plan_id: int,
    *,
    client: str = CLIENT_1,
    holder_name: str = "Анна Петрова",
    passport: str | None = PASSPORT,
    birth_date: date | None = ADULT,
    employer_ref: str | None = None,
) -> int:
    sub = await act(
        service.create_subscription,
        client_ref=client,
        plan_id=plan_id,
        holder_name=holder_name,
        passport=passport,
        birth_date=birth_date,
        employer_ref=employer_ref,
    )
    return sub.id


async def subscription(sub_id: int):
    return await read(service.get_subscription, sub_id)


async def status(sub_id: int) -> str:
    return (await subscription(sub_id)).status


async def open_invoice(sub_id: int) -> Invoice | None:
    return await read(service.open_invoice, sub_id)


async def pay(sub_id: int, amount: Decimal | None = None, external_ref: str | None = None) -> Payment:
    invoice = await open_invoice(sub_id)
    assert invoice is not None, f"у абонемента {sub_id} нет открытого счёта"
    due = invoice.amount - invoice.paid_total if amount is None else amount
    return await act(service.record_payment, invoice.id, due, external_ref=external_ref)


async def active(plan_id: int, **kwargs) -> int:
    sub_id = await subscribe(plan_id, **kwargs)
    await pay(sub_id)
    return sub_id


async def invoices(sub_id: int) -> list[Invoice]:
    async def _load(s):
        rows = await s.scalars(select(Invoice).where(Invoice.subscription_id == sub_id).order_by(Invoice.id))
        return list(rows.all())

    return await read(_load)


async def notice_kinds(sub_id: int) -> list[str]:
    return [n.kind for n in await read(service.notices, sub_id)]


async def all_notices(sub_id: int) -> list[Notice]:
    return await read(service.notices, sub_id)


async def history(sub_id: int) -> list[tuple[str, str]]:
    async def _load(s):
        rows = await s.scalars(
            select(StatusChange).where(StatusChange.subscription_id == sub_id).order_by(StatusChange.id)
        )
        return [(r.old_status, r.new_status) for r in rows.all()]

    return await read(_load)
