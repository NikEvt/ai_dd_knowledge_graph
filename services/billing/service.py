"""Счета, платежи и штрафы."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.applications import public as applications
from services.billing.models import AccountantAssignment, Fine, FineRate, Invoice, Payment
from services.billing.public import paid_amount

CENT = Decimal("0.01")


async def take_application(session: AsyncSession, application_id: int, accountant_id: int) -> None:
    """Бухгалтер сам закрепляет заявку за собой, в том числе забирая у коллеги."""
    brief = await applications.get_brief(session, application_id)
    if brief.kind == "debt":
        raise DomainError("у заявки в долг нет бухгалтера")
    assignment = await session.get(AccountantAssignment, application_id)
    if assignment is None:
        session.add(AccountantAssignment(application_id=application_id, accountant_id=accountant_id))
    else:
        assignment.accountant_id = accountant_id


async def _require_accountant(session: AsyncSession, application_id: int, accountant_id: int) -> None:
    assignment = await session.get(AccountantAssignment, application_id)
    if assignment is None or assignment.accountant_id != accountant_id:
        raise AccessDenied("заявка закреплена за другим бухгалтером")


async def issue_books_invoice(session: AsyncSession, application_id: int, accountant_id: int) -> Invoice:
    await _require_accountant(session, application_id, accountant_id)
    brief = await applications.get_brief(session, application_id)
    if brief.kind != "paid":
        raise DomainError("счёт за книги выставляется только по платной заявке")
    if brief.stage != "awaiting_invoice":
        raise DomainError("счёт выставляется после прохождения проверки")
    venue = await applications.get_venue(session, brief.venue_id)
    if not venue.requisites:
        raise DomainError("у площадки не заполнены реквизиты организации")

    price = await applications.books_price(session, application_id)
    markup = await applications.markup_pct(session, brief.representative_id)
    amount = (price * (1 + markup / 100)).quantize(CENT, ROUND_HALF_UP)
    now = clock.now()
    invoice = Invoice(
        application_id=application_id,
        kind="books",
        amount=amount,
        status="active",
        issued_at=now,
        payment_clock_started_at=now,
        venue_id=venue.id,
        requisites=venue.requisites,
    )
    session.add(invoice)
    await session.flush()
    events.publish(
        session,
        "invoice.issued",
        {
            "application_id": application_id,
            "invoice_id": invoice.id,
            "invoice_kind": "books",
            "amount": str(amount),
        },
    )
    return invoice


async def cancel_invoice(session: AsyncSession, invoice_id: int, reason: str) -> Invoice:
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFound(f"счёт {invoice_id}")
    if invoice.status != "active":
        return invoice
    if await paid_amount(session, invoice_id) > 0:
        raise DomainError("к счёту привязан платёж: сначала отвязать или вернуть")
    invoice.status = "cancelled"
    invoice.cancel_reason = reason
    events.publish(
        session,
        "invoice.cancelled",
        {
            "application_id": invoice.application_id,
            "invoice_id": invoice.id,
            "invoice_kind": invoice.kind,
            "reason": reason,
        },
    )
    return invoice


async def link_payment(session: AsyncSession, invoice_id: int, amount: Decimal, chief_id: int) -> Payment:
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFound(f"счёт {invoice_id}")
    if invoice.status != "active":
        raise DomainError("платёж нельзя привязать к аннулированному счёту")
    before = await paid_amount(session, invoice_id)
    payment = Payment(invoice_id=invoice_id, amount=amount, linked_at=clock.now(), linked_by=chief_id)
    after = before + amount
    if after > invoice.amount:
        payment.overpayment = True
    session.add(payment)
    await session.flush()
    events.publish(
        session,
        "payment.linked",
        {"application_id": invoice.application_id, "invoice_id": invoice.id, "amount": str(amount)},
    )
    if before < invoice.amount <= after:
        if invoice.kind == "fine":
            fine = await session.get(Fine, invoice.fine_id)
            fine.status = "paid"
        events.publish(
            session,
            "payment.fully_paid",
            {
                "application_id": invoice.application_id,
                "invoice_id": invoice.id,
                "invoice_kind": invoice.kind,
            },
        )
    return payment


async def unlink_payment(session: AsyncSession, payment_id: int, reason: str) -> Payment:
    if not reason:
        raise DomainError("отвязка платежа требует причины")
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise NotFound(f"платёж {payment_id}")
    payment.unlinked_at = clock.now()
    payment.unlink_reason = reason
    return payment


async def refund_payment(session: AsyncSession, payment_id: int, reason: str) -> Payment:
    if not reason:
        raise DomainError("возврат платежа требует причины")
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise NotFound(f"платёж {payment_id}")
    invoice = await session.get(Invoice, payment.invoice_id)
    payment.refunded = True
    events.publish(
        session,
        "payment.refunded",
        {
            "application_id": invoice.application_id,
            "invoice_id": invoice.id,
            "invoice_kind": invoice.kind,
            "reason": reason,
        },
    )
    return payment


async def create_fine(session: AsyncSession, application_id: int, loan_id: int | None, kind: str) -> Fine:
    brief = await applications.get_brief(session, application_id)
    rate = await session.get(FineRate, (brief.representative_id, brief.venue_id, kind))
    if rate is None:
        raise DomainError(f"размер штрафа {kind} не настроен для представителя и площадки")
    fine = Fine(
        application_id=application_id, loan_id=loan_id, kind=kind, amount=rate.amount, created_at=clock.now()
    )
    session.add(fine)
    await session.flush()
    return fine


async def issue_fine_invoice(session: AsyncSession, fine_id: int, accountant_id: int) -> Invoice:
    fine = await session.get(Fine, fine_id)
    if fine is None:
        raise NotFound(f"штраф {fine_id}")
    brief = await applications.get_brief(session, fine.application_id)
    if brief.kind == "debt":
        raise DomainError("по заявке в долг штраф оплачивается вне системы")
    await _require_accountant(session, fine.application_id, accountant_id)
    venue = await applications.get_venue(session, brief.venue_id)
    if not venue.requisites:
        raise DomainError("у площадки не заполнены реквизиты организации")
    now = clock.now()
    invoice = Invoice(
        application_id=fine.application_id,
        kind="fine",
        fine_id=fine.id,
        amount=fine.amount,
        status="active",
        issued_at=now,
        payment_clock_started_at=now,
        venue_id=venue.id,
        requisites=venue.requisites,
    )
    session.add(invoice)
    await session.flush()
    events.publish(
        session,
        "invoice.issued",
        {
            "application_id": fine.application_id,
            "invoice_id": invoice.id,
            "invoice_kind": "fine",
            "amount": str(fine.amount),
        },
    )
    return invoice


async def mark_fine_paid_outside(session: AsyncSession, fine_id: int, operator_id: int) -> Fine:
    """По заявке в долг погашение отмечает оператор по данным главного бухгалтера."""
    fine = await session.get(Fine, fine_id)
    if fine is None:
        raise NotFound(f"штраф {fine_id}")
    brief = await applications.get_brief(session, fine.application_id)
    if brief.kind != "debt":
        raise DomainError("вне системы гасятся только штрафы по заявкам в долг")
    if brief.operator_id != operator_id:
        raise AccessDenied("заявка закреплена за другим оператором")
    fine.status = "paid"
    fine.paid_outside = True
    return fine


async def active_invoices(session: AsyncSession, application_id: int) -> list[Invoice]:
    return list(
        (
            await session.scalars(
                select(Invoice).where(Invoice.application_id == application_id, Invoice.status == "active")
            )
        ).all()
    )
