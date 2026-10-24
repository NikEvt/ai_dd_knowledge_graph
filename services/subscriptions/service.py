"""Абонементы читателей: оформление, счета за месяц, оплата, активация и данные держателя."""

import re
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.subscriptions import settings
from services.subscriptions.models import Invoice, Notice, Payment, Plan, Subscription

PLAN_KINDS = ("regular", "social", "corporate")
LIVE = ("active", "grace")
OPEN = ("pending", "active", "grace")
CLOSED = ("expired", "closed_duplicate")
HOLDER_FIELDS = ("holder_name", "passport", "birth_date")

PASSPORT_RE = re.compile(r"^\d{4} \d{6}$")


def add_months(day: date, months: int) -> date:
    year, month = divmod(day.month - 1 + months, 12)
    year += day.year
    month += 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def period_for(start: date) -> tuple[date, date]:
    """Оплачиваемый месяц: с start по тот же день следующего месяца не включительно."""
    return start, add_months(start, 1) - timedelta(days=1)


def age_on(birth_date: date, day: date) -> int:
    return day.year - birth_date.year - ((day.month, day.day) < (birth_date.month, birth_date.day))


def fully_paid(invoice: Invoice) -> bool:
    return invoice.paid_total >= invoice.amount


def _same_track(a: Plan, b: Plan) -> bool:
    # Социальный абонемент и платный (обычный или корпоративный) могут действовать одновременно.
    return (a.kind == "social") == (b.kind == "social")


# --- тарифы ---


async def create_plan(
    session: AsyncSession, *, code: str, name: str, kind: str, monthly_fee: Decimal, max_books: int = 5
) -> Plan:
    if kind not in PLAN_KINDS:
        raise DomainError(f"неизвестный вид тарифа: {kind}")
    if monthly_fee <= 0:
        raise DomainError("стоимость тарифа должна быть больше нуля")
    if await session.scalar(select(Plan.id).where(Plan.code == code)) is not None:
        raise DomainError(f"тариф с кодом {code} уже есть")
    plan = Plan(code=code, name=name, kind=kind, monthly_fee=monthly_fee, max_books=max_books)
    session.add(plan)
    await session.flush()
    return plan


async def archive_plan(session: AsyncSession, plan_id: int) -> Plan:
    plan = await get_plan(session, plan_id)
    plan.archived = True
    return plan


async def get_plan(session: AsyncSession, plan_id: int) -> Plan:
    plan = await session.get(Plan, plan_id)
    if plan is None:
        raise NotFound(f"тариф {plan_id}")
    return plan


async def list_plans(session: AsyncSession) -> list[Plan]:
    rows = await session.scalars(select(Plan).where(Plan.archived.is_(False)).order_by(Plan.monthly_fee))
    return list(rows.all())


# --- абонементы ---


async def get_subscription(session: AsyncSession, subscription_id: int) -> Subscription:
    sub = await session.get(Subscription, subscription_id)
    if sub is None:
        raise NotFound(f"абонемент {subscription_id}")
    return sub


async def client_subscriptions(session: AsyncSession, client_ref: str) -> list[Subscription]:
    rows = await session.scalars(
        select(Subscription).where(Subscription.client_ref == client_ref).order_by(Subscription.id)
    )
    return list(rows.all())


def _validate_holder(
    plan: Plan, holder_name: str, passport: str | None, birth_date: date | None, today: date
) -> None:
    if not holder_name.strip():
        raise DomainError("не указано имя держателя абонемента")
    if passport is not None and not PASSPORT_RE.match(passport):
        raise DomainError("паспорт указывается в формате «1234 567890»")
    if birth_date is not None:
        if birth_date >= today:
            raise DomainError("дата рождения должна быть в прошлом")
        if age_on(birth_date, today) < settings.MIN_HOLDER_AGE:
            raise DomainError(f"абонемент оформляется с {settings.MIN_HOLDER_AGE} лет")
    if plan.kind == "social" and (passport is None or birth_date is None):
        raise DomainError("для социального тарифа нужны паспорт и дата рождения")


def _social_eligible(birth_date: date, today: date) -> bool:
    age = age_on(birth_date, today)
    return age <= settings.SOCIAL_MAX_STUDENT_AGE or age >= settings.SOCIAL_MIN_SENIOR_AGE


async def create_subscription(
    session: AsyncSession,
    *,
    client_ref: str,
    plan_id: int,
    holder_name: str,
    passport: str | None = None,
    birth_date: date | None = None,
    employer_ref: str | None = None,
) -> Subscription:
    plan = await get_plan(session, plan_id)
    if plan.archived:
        raise DomainError("тариф больше не продаётся")
    if plan.kind == "corporate" and not employer_ref:
        raise DomainError("для корпоративного тарифа нужна организация-работодатель")
    if plan.kind != "corporate" and employer_ref:
        raise DomainError("организация указывается только для корпоративного тарифа")
    today = clock.now().date()
    _validate_holder(plan, holder_name, passport, birth_date, today)
    # Право на социальный тариф при изменении данных проверяет сверка держателя (recheck_holder).
    if plan.kind == "social" and not _social_eligible(birth_date, today):
        raise DomainError("социальный тариф доступен студентам и пенсионерам")

    existing = await session.scalar(
        select(Subscription.id).where(
            Subscription.client_ref == client_ref,
            Subscription.plan_id == plan_id,
            Subscription.status.in_(LIVE),
        )
    )
    if existing is not None:
        raise DomainError("у клиента уже есть действующий абонемент на этот тариф — его можно продлить")
    pending = await session.scalar(
        select(func.count()).where(Subscription.client_ref == client_ref, Subscription.status == "pending")
    )
    if pending >= settings.MAX_PENDING_PER_CLIENT:
        raise DomainError("у клиента слишком много неоплаченных абонементов")

    sub = Subscription(
        client_ref=client_ref,
        plan_id=plan_id,
        holder_name=holder_name.strip(),
        passport=passport,
        birth_date=birth_date,
        employer_ref=employer_ref,
        created_at=clock.now(),
    )
    session.add(sub)
    await session.flush()
    await issue_invoice(session, sub, today)
    events.publish(
        session,
        "subscriptions.created",
        {"subscription_id": sub.id, "client_ref": client_ref, "plan_id": plan_id},
    )
    return sub


async def update_holder(
    session: AsyncSession,
    subscription_id: int,
    *,
    client_ref: str,
    holder_name: str | None = None,
    passport: str | None = None,
    birth_date: date | None = None,
) -> Subscription:
    sub = await get_subscription(session, subscription_id)
    if sub.client_ref != client_ref:
        raise AccessDenied("абонемент оформлен на другого клиента")
    if sub.status in CLOSED:
        raise DomainError("абонемент закрыт, данные держателя не меняются")
    plan = await get_plan(session, sub.plan_id)

    new = {
        "holder_name": holder_name.strip() if holder_name is not None else sub.holder_name,
        "passport": passport if passport is not None else sub.passport,
        "birth_date": birth_date if birth_date is not None else sub.birth_date,
    }
    _validate_holder(plan, new["holder_name"], new["passport"], new["birth_date"], clock.now().date())
    changed = [f for f in HOLDER_FIELDS if getattr(sub, f) != new[f]]
    if not changed:
        return sub
    for field in changed:
        setattr(sub, field, new[field])
    sub.holder_check = "pending"
    events.publish(
        session, "subscriptions.holder_updated", {"subscription_id": sub.id, "changed": changed}
    )
    return sub


async def recheck_holder(session: AsyncSession, subscription_id: int) -> Subscription:
    """Сверка данных держателя. Без паспорта и даты рождения абонемент не подтверждается."""
    sub = await get_subscription(session, subscription_id)
    if sub.status in CLOSED or sub.holder_check != "pending":
        return sub
    plan = await get_plan(session, sub.plan_id)
    today = clock.now().date()
    reason = None
    if sub.passport is None or sub.birth_date is None:
        reason = "не хватает паспорта или даты рождения"
    elif plan.kind == "social" and not _social_eligible(sub.birth_date, today):
        reason = "держатель не подходит под условия социального тарифа"
    if reason is None:
        sub.holder_check = "verified"
        return sub
    sub.holder_check = "rejected"
    events.publish(session, "subscriptions.holder_rejected", {"subscription_id": sub.id, "reason": reason})
    return sub


# --- счета и платежи ---


async def open_invoice(session: AsyncSession, subscription_id: int) -> Invoice | None:
    return await session.scalar(
        select(Invoice).where(Invoice.subscription_id == subscription_id, Invoice.status == "open")
    )


async def issue_invoice(session: AsyncSession, sub: Subscription, period_start: date) -> Invoice:
    if await open_invoice(session, sub.id) is not None:
        raise DomainError("по абонементу уже есть неоплаченный счёт")
    plan = await get_plan(session, sub.plan_id)
    start, end = period_for(period_start)
    invoice = Invoice(
        subscription_id=sub.id,
        period_start=start,
        period_end=end,
        amount=plan.monthly_fee,
        issued_at=clock.now(),
    )
    session.add(invoice)
    await session.flush()
    events.publish(
        session,
        "subscriptions.invoice_issued",
        {
            "subscription_id": sub.id,
            "invoice_id": invoice.id,
            "amount": str(invoice.amount),
            "period_start": start.isoformat(),
        },
    )
    return invoice


async def record_payment(
    session: AsyncSession, invoice_id: int, amount: Decimal, *, external_ref: str | None = None
) -> Payment:
    invoice = await session.get(Invoice, invoice_id, with_for_update=True)
    if invoice is None:
        raise NotFound(f"счёт {invoice_id}")
    if invoice.status != "open":
        raise DomainError("счёт уже оплачен или аннулирован")
    if amount <= 0:
        raise DomainError("сумма платежа должна быть больше нуля")
    if amount > invoice.amount - invoice.paid_total:
        raise DomainError("сумма больше остатка по счёту")
    if external_ref is not None:
        seen = await session.scalar(select(Payment.id).where(Payment.external_ref == external_ref))
        if seen is not None:
            raise DomainError(f"платёж {external_ref} уже учтён")

    payment = Payment(invoice_id=invoice.id, amount=amount, external_ref=external_ref, paid_at=clock.now())
    session.add(payment)
    await session.flush()
    await session.refresh(invoice, ["paid_total"])
    if fully_paid(invoice):
        invoice.status = "paid"
        events.publish(
            session,
            "subscriptions.payment_completed",
            {"subscription_id": invoice.subscription_id, "invoice_id": invoice.id},
        )
    return payment


async def void_open_invoices(session: AsyncSession, subscription_id: int) -> list[Invoice]:
    invoices = (
        await session.scalars(
            select(Invoice).where(Invoice.subscription_id == subscription_id, Invoice.status == "open")
        )
    ).all()
    for invoice in invoices:
        invoice.status = "void"
        if invoice.paid_total > 0:
            events.publish(
                session,
                "subscriptions.refund_required",
                {
                    "subscription_id": subscription_id,
                    "invoice_id": invoice.id,
                    "amount": str(invoice.paid_total),
                },
            )
    return list(invoices)


# --- жизненный цикл ---


async def close_duplicates(session: AsyncSession, sub: Subscription) -> list[int]:
    """Закрывает другие открытые абонементы клиента того же направления (платное или социальное)."""
    plan = await get_plan(session, sub.plan_id)
    rows = (
        await session.execute(
            select(Subscription, Plan)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.client_ref == sub.client_ref,
                Subscription.id != sub.id,
                Subscription.status.in_(OPEN),
            )
            .order_by(Subscription.id)
        )
    ).all()
    closed = []
    for other, other_plan in rows:
        if not _same_track(plan, other_plan):
            continue
        other.status = "closed_duplicate"
        other.closed_at = clock.now()
        closed.append(other.id)
        events.publish(
            session,
            "subscriptions.closed_duplicate",
            {"subscription_id": other.id, "kept_id": sub.id, "client_ref": sub.client_ref},
        )
    await session.flush()
    return closed


async def apply_payment(session: AsyncSession, subscription_id: int, invoice_id: int) -> Subscription:
    sub = await get_subscription(session, subscription_id)
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or not fully_paid(invoice):
        raise DomainError("счёт не оплачен полностью")

    if sub.status in CLOSED:
        # Деньги пришли на уже закрытый абонемент — возвращаем клиенту.
        events.publish(
            session,
            "subscriptions.refund_required",
            {"subscription_id": sub.id, "invoice_id": invoice.id, "amount": str(invoice.paid_total)},
        )
        return sub

    if sub.status == "pending":
        await close_duplicates(session, sub)
        sub.status = "active"
        sub.activated_at = clock.now()
        sub.paid_until = invoice.period_end
        events.publish(
            session,
            "subscriptions.activated",
            {"subscription_id": sub.id, "paid_until": sub.paid_until.isoformat()},
        )
        return sub

    sub.status = "active"
    sub.paid_until = max(sub.paid_until, invoice.period_end)
    events.publish(
        session,
        "subscriptions.renewed",
        {"subscription_id": sub.id, "paid_until": sub.paid_until.isoformat()},
    )
    return sub


async def add_notice(session: AsyncSession, subscription_id: int, kind: str, body: str) -> Notice:
    notice = Notice(subscription_id=subscription_id, kind=kind, body=body, created_at=clock.now())
    session.add(notice)
    return notice


async def notices(session: AsyncSession, subscription_id: int) -> list[Notice]:
    rows = await session.scalars(
        select(Notice).where(Notice.subscription_id == subscription_id).order_by(Notice.id)
    )
    return list(rows.all())
