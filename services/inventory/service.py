"""Книжный фонд: учёт экземпляров, перемещения между площадками, МБА и списания."""

import re
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.inventory import settings
from services.inventory.models import (
    ON_BALANCE,
    OPEN_TRANSFER,
    Copy,
    Custodian,
    IllLoan,
    IllPenalty,
    PartnerLibrary,
    StockLevel,
    Transfer,
    WriteOff,
)

INVENTORY_NO = re.compile(r"^[А-ЯA-Z]{1,4}-\d{4,8}$")
DAY = timedelta(days=1)


def days_late(due_at: datetime, at: datetime) -> int:
    """Число начатых суток просрочки."""
    delta = at - due_at
    if delta <= timedelta(0):
        return 0
    return delta.days + (1 if delta % DAY else 0)


async def _require_custodian(session: AsyncSession, venue_id: int, employee_id: int) -> None:
    if await session.get(Custodian, (venue_id, employee_id)) is None:
        raise AccessDenied("сотрудник не является хранителем фонда этой площадки")


async def _copy(session: AsyncSession, copy_id: int) -> Copy:
    copy = await session.get(Copy, copy_id, with_for_update=True)
    if copy is None:
        raise NotFound(f"экземпляр {copy_id}")
    return copy


def _set_state(copy: Copy, state: str) -> None:
    copy.state = state
    copy.updated_at = clock.now()


def _stock_event(session: AsyncSession, topic: str, copy: Copy, **extra) -> None:
    payload = {"copy_id": copy.id, "book_ref": copy.book_ref, "venue_ids": [copy.venue_id]}
    payload.update(extra)
    events.publish(session, topic, payload)


async def _open_transfer(session: AsyncSession, copy_id: int) -> Transfer | None:
    return await session.scalar(
        select(Transfer).where(Transfer.copy_id == copy_id, Transfer.status.in_(OPEN_TRANSFER))
    )


# Экземпляры и остатки ---------------------------------------------------------


async def add_custodian(session: AsyncSession, venue_id: int, employee_id: int) -> None:
    await session.merge(Custodian(venue_id=venue_id, employee_id=employee_id))


async def register_copy(
    session: AsyncSession, *, custodian_id: int, venue_id: int, book_ref: int, inventory_no: str
) -> Copy:
    await _require_custodian(session, venue_id, custodian_id)
    inventory_no = inventory_no.strip().upper()
    if not INVENTORY_NO.match(inventory_no):
        raise DomainError("инвентарный номер должен иметь вид «ШИФР-00000»")
    if await session.scalar(select(Copy.id).where(Copy.inventory_no == inventory_no)):
        raise DomainError(f"инвентарный номер {inventory_no} уже занят")
    now = clock.now()
    copy = Copy(
        inventory_no=inventory_no,
        book_ref=book_ref,
        venue_id=venue_id,
        state="available",
        acquired_at=now,
        updated_at=now,
    )
    session.add(copy)
    await session.flush()
    _stock_event(session, "inventory.copy_registered", copy, inventory_no=inventory_no)
    return copy


async def get_copy(session: AsyncSession, copy_id: int) -> Copy:
    copy = await session.get(Copy, copy_id)
    if copy is None:
        raise NotFound(f"экземпляр {copy_id}")
    return copy


async def recount_stock(session: AsyncSession, book_ref: int, venue_id: int) -> StockLevel:
    total, available = (
        await session.execute(
            select(
                func.count().filter(Copy.state.in_(ON_BALANCE)),
                func.count().filter(Copy.state == "available"),
            ).where(Copy.book_ref == book_ref, Copy.venue_id == venue_id)
        )
    ).one()
    now = clock.now()
    stmt = insert(StockLevel).values(
        book_ref=book_ref, venue_id=venue_id, total=total, available=available, updated_at=now
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[StockLevel.book_ref, StockLevel.venue_id],
            set_={"total": total, "available": available, "updated_at": now},
        )
    )
    return await session.get(StockLevel, (book_ref, venue_id), populate_existing=True)


async def stock(session: AsyncSession, book_ref: int, venue_id: int) -> tuple[int, int]:
    level = await session.get(StockLevel, (book_ref, venue_id))
    return (level.total, level.available) if level else (0, 0)


async def reconcile_venue(session: AsyncSession, copy_id: int, venue_id: int, custodian_id: int) -> Copy:
    """Исправление места хранения по итогам инвентаризации, без оформления перемещения."""
    copy = await _copy(session, copy_id)
    await _require_custodian(session, venue_id, custodian_id)
    if copy.venue_id == venue_id:
        return copy
    if await _open_transfer(session, copy.id):
        raise DomainError("по экземпляру оформлено перемещение")
    previous = copy.venue_id
    copy.venue_id = venue_id
    copy.updated_at = clock.now()
    await session.flush()
    _stock_event(session, "inventory.copy_relocated", copy, venue_ids=[previous, venue_id])
    return copy


# Перемещения ------------------------------------------------------------------


async def request_transfer(
    session: AsyncSession, copy_id: int, to_venue_id: int, custodian_id: int
) -> Transfer:
    copy = await _copy(session, copy_id)
    await _require_custodian(session, copy.venue_id, custodian_id)
    if copy.venue_id == to_venue_id:
        raise DomainError("экземпляр уже находится на этой площадке")
    if copy.state == "on_loan":
        raise DomainError("экземпляр выдан, перемещение невозможно до возврата")
    if copy.state != "available":
        raise DomainError("перемещать можно только экземпляр, доступный на площадке")
    if await _open_transfer(session, copy.id):
        raise DomainError("по экземпляру уже есть незавершённое перемещение")
    remaining = await session.scalar(
        select(func.count()).where(
            Copy.book_ref == copy.book_ref,
            Copy.venue_id == copy.venue_id,
            Copy.state == "available",
            Copy.id != copy.id,
        )
    )
    if remaining < settings.MIN_COPIES_ON_VENUE:
        raise DomainError("на площадке должен остаться хотя бы один экземпляр издания")
    transfer = Transfer(
        copy_id=copy.id,
        from_venue_id=copy.venue_id,
        to_venue_id=to_venue_id,
        status="requested",
        requested_by=custodian_id,
        requested_at=clock.now(),
    )
    session.add(transfer)
    await session.flush()
    return transfer


async def _transfer(session: AsyncSession, transfer_id: int) -> Transfer:
    transfer = await session.get(Transfer, transfer_id, with_for_update=True)
    if transfer is None:
        raise NotFound(f"перемещение {transfer_id}")
    return transfer


async def ship_transfer(session: AsyncSession, transfer_id: int, custodian_id: int) -> Transfer:
    transfer = await _transfer(session, transfer_id)
    await _require_custodian(session, transfer.from_venue_id, custodian_id)
    if transfer.status != "requested":
        raise DomainError("отправить можно только оформленное перемещение")
    copy = await _copy(session, transfer.copy_id)
    if copy.state != "available":
        raise DomainError("экземпляр недоступен для отправки")
    _set_state(copy, "in_transit")
    transfer.status = "in_transit"
    transfer.shipped_at = clock.now()
    _stock_event(session, "inventory.transfer_shipped", copy, transfer_id=transfer.id)
    return transfer


async def receive_transfer(session: AsyncSession, transfer_id: int, custodian_id: int) -> Transfer:
    transfer = await _transfer(session, transfer_id)
    await _require_custodian(session, transfer.to_venue_id, custodian_id)
    if transfer.status != "in_transit":
        raise DomainError("принять можно только отправленный экземпляр")
    copy = await _copy(session, transfer.copy_id)
    copy.venue_id = transfer.to_venue_id
    _set_state(copy, "available")
    transfer.status = "received"
    transfer.closed_at = clock.now()
    await session.flush()
    _stock_event(
        session,
        "inventory.transfer_received",
        copy,
        transfer_id=transfer.id,
        venue_ids=[transfer.from_venue_id, transfer.to_venue_id],
    )
    return transfer


async def cancel_transfer(
    session: AsyncSession, transfer_id: int, custodian_id: int | None, *, reason: str
) -> Transfer:
    """custodian_id=None — отмена системой (истёк срок заявки)."""
    transfer = await _transfer(session, transfer_id)
    if custodian_id is not None and not await session.scalar(
        select(func.count()).where(
            Custodian.employee_id == custodian_id,
            Custodian.venue_id.in_((transfer.from_venue_id, transfer.to_venue_id)),
        )
    ):
        raise AccessDenied("отменить перемещение может хранитель одной из площадок")
    if transfer.status not in OPEN_TRANSFER:
        raise DomainError("перемещение уже завершено")
    copy = await _copy(session, transfer.copy_id)
    if transfer.status == "in_transit":
        _set_state(copy, "available")
    transfer.status = "cancelled"
    transfer.cancel_reason = reason
    transfer.closed_at = clock.now()
    _stock_event(session, "inventory.transfer_cancelled", copy, transfer_id=transfer.id, reason=reason)
    return transfer


# МБА --------------------------------------------------------------------------


async def register_partner(
    session: AsyncSession, *, code: str, name: str, daily_penalty: Decimal, max_active_loans: int = 5
) -> PartnerLibrary:
    if await session.scalar(select(PartnerLibrary.id).where(PartnerLibrary.code == code)):
        raise DomainError(f"библиотека с кодом {code} уже зарегистрирована")
    partner = PartnerLibrary(
        code=code, name=name, daily_penalty=daily_penalty, max_active_loans=max_active_loans
    )
    session.add(partner)
    await session.flush()
    return partner


async def partner_debt(session: AsyncSession, partner_id: int) -> Decimal:
    return await session.scalar(
        select(func.coalesce(func.sum(IllPenalty.amount), 0)).where(
            IllPenalty.partner_id == partner_id, IllPenalty.status != "paid"
        )
    )


async def issue_ill(session: AsyncSession, copy_id: int, partner_id: int, custodian_id: int) -> IllLoan:
    copy = await _copy(session, copy_id)
    await _require_custodian(session, copy.venue_id, custodian_id)
    partner = await session.get(PartnerLibrary, partner_id)
    if partner is None:
        raise NotFound(f"библиотека {partner_id}")
    if partner.suspended:
        raise DomainError("выдачи библиотеке приостановлены")
    if copy.state != "available":
        raise DomainError("экземпляр недоступен для выдачи")
    if await _open_transfer(session, copy.id):
        raise DomainError("по экземпляру оформлено перемещение")

    now = clock.now()
    active = (
        await session.scalars(
            select(IllLoan).where(IllLoan.partner_id == partner_id, IllLoan.status == "out")
        )
    ).all()
    if any(loan.due_at < now for loan in active):
        raise DomainError("у библиотеки есть просроченные выдачи")
    if len(active) >= partner.max_active_loans:
        raise DomainError("превышен лимит одновременных выдач библиотеке")
    if await partner_debt(session, partner_id) > settings.ILL_PARTNER_DEBT_LIMIT:
        raise DomainError("у библиотеки неоплаченные пени сверх лимита")

    loan = IllLoan(
        copy_id=copy.id,
        partner_id=partner_id,
        issued_by=custodian_id,
        issued_at=now,
        due_at=now + timedelta(days=settings.ILL_LOAN_PERIOD_DAYS),
        status="out",
    )
    session.add(loan)
    _set_state(copy, "on_loan")
    await session.flush()
    _stock_event(session, "inventory.ill_issued", copy, ill_loan_id=loan.id, partner_id=partner_id)
    return loan


async def _out_loan(session: AsyncSession, loan_id: int, custodian_id: int) -> tuple[IllLoan, Copy]:
    loan = await session.get(IllLoan, loan_id, with_for_update=True)
    if loan is None:
        raise NotFound(f"выдача по МБА {loan_id}")
    copy = await _copy(session, loan.copy_id)
    await _require_custodian(session, copy.venue_id, custodian_id)
    if loan.status != "out":
        raise DomainError("выдача уже закрыта")
    return loan, copy


async def renew_ill(session: AsyncSession, loan_id: int, custodian_id: int) -> IllLoan:
    loan, _ = await _out_loan(session, loan_id, custodian_id)
    if loan.due_at < clock.now():
        raise DomainError("просроченную выдачу продлить нельзя")
    max_due = loan.issued_at + timedelta(
        days=settings.ILL_LOAN_PERIOD_DAYS + settings.ILL_RENEWAL_DAYS * settings.ILL_MAX_RENEWALS
    )
    new_due = loan.due_at + timedelta(days=settings.ILL_RENEWAL_DAYS)
    if new_due > max_due:
        raise DomainError("выдача уже продлевалась")
    loan.due_at = new_due
    return loan


async def return_ill(
    session: AsyncSession, loan_id: int, custodian_id: int, *, damaged: bool = False
) -> IllLoan:
    loan, copy = await _out_loan(session, loan_id, custodian_id)
    now = clock.now()
    loan.status = "returned"
    loan.returned_at = now
    _set_state(copy, "damaged" if damaged else "available")
    _stock_event(
        session,
        "inventory.ill_returned",
        copy,
        ill_loan_id=loan.id,
        partner_id=loan.partner_id,
        due_at=loan.due_at.isoformat(),
        returned_at=now.isoformat(),
    )
    if damaged:
        _stock_event(session, "inventory.copy_damaged", copy, ill_loan_id=loan.id, note="возврат по МБА")
    return loan


async def report_ill_lost(session: AsyncSession, loan_id: int, custodian_id: int) -> IllLoan:
    loan, copy = await _out_loan(session, loan_id, custodian_id)
    loan.status = "lost"
    _set_state(copy, "lost")
    _stock_event(
        session, "inventory.copy_lost", copy, ill_loan_id=loan.id, note="утеряна библиотекой-партнёром"
    )
    return loan


# Утеря, порча, списание -------------------------------------------------------


async def _on_shelf(session: AsyncSession, copy_id: int, custodian_id: int) -> Copy:
    copy = await _copy(session, copy_id)
    await _require_custodian(session, copy.venue_id, custodian_id)
    if copy.state == "on_loan":
        raise DomainError("экземпляр выдан по МБА, оформите утерю или возврат по выдаче")
    if copy.state != "available":
        raise DomainError("экземпляр уже выбыл из фонда или находится в пути")
    if await _open_transfer(session, copy.id):
        raise DomainError("по экземпляру оформлено перемещение")
    return copy


async def mark_lost(session: AsyncSession, copy_id: int, custodian_id: int, note: str | None = None) -> Copy:
    copy = await _on_shelf(session, copy_id, custodian_id)
    _set_state(copy, "lost")
    _stock_event(session, "inventory.copy_lost", copy, custodian_id=custodian_id, note=note)
    return copy


async def mark_damaged(
    session: AsyncSession, copy_id: int, custodian_id: int, note: str | None = None
) -> Copy:
    copy = await _on_shelf(session, copy_id, custodian_id)
    _set_state(copy, "damaged")
    _stock_event(session, "inventory.copy_damaged", copy, custodian_id=custodian_id, note=note)
    return copy


async def write_off_worn(
    session: AsyncSession, copy_id: int, custodian_id: int, note: str | None = None
) -> WriteOff:
    copy = await _on_shelf(session, copy_id, custodian_id)
    return await write_off(session, copy, "worn_out", by=custodian_id, note=note)


async def write_off(
    session: AsyncSession,
    copy: Copy,
    reason: str,
    *,
    by: int | None = None,
    ill_loan_id: int | None = None,
    note: str | None = None,
) -> WriteOff:
    existing = await session.scalar(select(WriteOff).where(WriteOff.copy_id == copy.id))
    if existing is not None:
        return existing
    now = clock.now()
    act = WriteOff(
        copy_id=copy.id,
        reason=reason,
        act_no=f"СП-{now.year}-{copy.id:06d}",
        ill_loan_id=ill_loan_id,
        note=note,
        created_by=by,
        created_at=now,
    )
    session.add(act)
    _set_state(copy, "written_off")
    await session.flush()
    _stock_event(session, "inventory.copy_written_off", copy, write_off_id=act.id, reason=reason)
    return act


# Пени по МБА ------------------------------------------------------------------


async def _penalty(session: AsyncSession, loan: IllLoan, kind: str) -> IllPenalty:
    penalty = await session.scalar(
        select(IllPenalty).where(IllPenalty.ill_loan_id == loan.id, IllPenalty.kind == kind)
    )
    if penalty is None:
        now = clock.now()
        penalty = IllPenalty(
            ill_loan_id=loan.id,
            partner_id=loan.partner_id,
            kind=kind,
            days=0,
            amount=Decimal(0),
            status="accruing",
            created_at=now,
            updated_at=now,
        )
        session.add(penalty)
    return penalty


async def accrue_overdue(
    session: AsyncSession, loan_id: int, days: int, *, final: bool = False
) -> IllPenalty:
    loan = await session.get(IllLoan, loan_id)
    partner = await session.get(PartnerLibrary, loan.partner_id)
    penalty = await _penalty(session, loan, "overdue")
    if penalty.status != "accruing":
        return penalty
    penalty.days = min(days, settings.ILL_PENALTY_MAX_DAYS)
    penalty.amount = partner.daily_penalty * penalty.days
    penalty.updated_at = clock.now()
    if final:
        penalty.status = "final"
    await session.flush()
    events.publish(
        session,
        "inventory.ill_penalty_accrued",
        {"penalty_id": penalty.id, "partner_id": loan.partner_id, "ill_loan_id": loan.id},
    )
    return penalty


async def charge_lost_copy(session: AsyncSession, loan_id: int) -> IllPenalty:
    loan = await session.get(IllLoan, loan_id)
    overdue = await session.scalar(
        select(IllPenalty).where(IllPenalty.ill_loan_id == loan.id, IllPenalty.kind == "overdue")
    )
    if overdue is not None and overdue.status == "accruing":
        overdue.status = "final"
    penalty = await _penalty(session, loan, "lost")
    penalty.amount = settings.ILL_LOST_COMPENSATION
    penalty.status = "final"
    penalty.updated_at = clock.now()
    await session.flush()
    events.publish(
        session,
        "inventory.ill_penalty_accrued",
        {"penalty_id": penalty.id, "partner_id": loan.partner_id, "ill_loan_id": loan.id},
    )
    return penalty


async def penalties(session: AsyncSession, partner_id: int) -> list[IllPenalty]:
    rows = await session.scalars(
        select(IllPenalty).where(IllPenalty.partner_id == partner_id).order_by(IllPenalty.id)
    )
    return list(rows.all())


async def settle_penalty(session: AsyncSession, penalty_id: int) -> IllPenalty:
    penalty = await session.get(IllPenalty, penalty_id, with_for_update=True)
    if penalty is None:
        raise NotFound(f"пени {penalty_id}")
    if penalty.status == "accruing":
        raise DomainError("пени ещё начисляются: экземпляр не возвращён")
    if penalty.status == "paid":
        raise DomainError("пени уже оплачены")
    penalty.status = "paid"
    penalty.updated_at = clock.now()
    partner = await session.get(PartnerLibrary, penalty.partner_id)
    await session.flush()
    if partner.suspended and await partner_debt(session, partner.id) <= settings.ILL_PARTNER_DEBT_LIMIT:
        partner.suspended = False
        events.publish(session, "inventory.partner_resumed", {"partner_id": partner.id})
    return penalty


async def review_partner_debt(session: AsyncSession, partner_id: int) -> PartnerLibrary:
    partner = await session.get(PartnerLibrary, partner_id, with_for_update=True)
    if not partner.suspended and await partner_debt(session, partner_id) > settings.ILL_PARTNER_DEBT_LIMIT:
        partner.suspended = True
        events.publish(session, "inventory.partner_suspended", {"partner_id": partner_id})
    return partner
