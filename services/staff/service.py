"""Сотрудники площадок: кадровые операции, смены, инструктажи и допуски."""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.staff import settings
from services.staff.models import (
    Alert,
    Assignment,
    Briefing,
    Clearance,
    ClearanceKind,
    Employee,
    Shift,
    ShiftMember,
    Site,
)

EDITABLE_FIELDS = ("full_name", "passport", "snils", "birth_date", "role")


# --- проверки ----------------------------------------------------------------


async def _employee(session: AsyncSession, employee_id: int) -> Employee:
    employee = await session.get(Employee, employee_id)
    if employee is None:
        raise NotFound(f"сотрудник {employee_id}")
    return employee


async def _site(session: AsyncSession, site_id: int) -> Site:
    site = await session.get(Site, site_id)
    if site is None:
        raise NotFound(f"площадка {site_id}")
    return site


async def _shift(session: AsyncSession, shift_id: int) -> Shift:
    shift = await session.get(Shift, shift_id)
    if shift is None:
        raise NotFound(f"смена {shift_id}")
    return shift


async def _require_hr(session: AsyncSession, actor_id: int) -> Employee:
    actor = await session.get(Employee, actor_id)
    if actor is None or not actor.active or actor.role not in settings.HR_ROLES:
        raise AccessDenied("кадровые операции выполняет только отдел кадров")
    return actor


async def _require_responsible(session: AsyncSession, site_id: int, actor_id: int) -> Site:
    site = await _site(session, site_id)
    if site.responsible_id != actor_id:
        raise AccessDenied("сменами площадки управляет только ответственный за площадку")
    return site


def missing_fields(employee: Employee) -> list[str]:
    return [f for f in settings.REQUIRED_EMPLOYEE_FIELDS if not getattr(employee, f)]


def snils_valid(snils: str) -> bool:
    digits = snils.replace("-", "").replace(" ", "")
    if len(digits) != 11 or not digits.isdigit():
        return False
    body, control = digits[:9], int(digits[9:])
    total = sum(int(d) * (9 - i) for i, d in enumerate(body))
    if total > 101:
        total %= 101
    return (0 if total in (100, 101) else total) == control


def _validate_card(fields: dict[str, Any]) -> None:
    role = fields.get("role")
    if role is not None and role not in settings.ROLES:
        raise DomainError(f"неизвестная должность «{role}»")
    snils = fields.get("snils")
    if snils and not snils_valid(snils):
        raise DomainError("СНИЛС не проходит проверку контрольного числа")
    birth: date | None = fields.get("birth_date")
    if birth is not None:
        today = clock.now().date()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < settings.MIN_EMPLOYEE_AGE:
            raise DomainError(f"сотрудник должен быть не моложе {settings.MIN_EMPLOYEE_AGE} лет")


# --- сотрудники и площадки ---------------------------------------------------


async def hire_employee(
    session: AsyncSession,
    hr_id: int,
    *,
    role: str,
    full_name: str | None = None,
    passport: str | None = None,
    snils: str | None = None,
    birth_date: date | None = None,
) -> Employee:
    await _require_hr(session, hr_id)
    card = {
        "role": role,
        "full_name": full_name,
        "passport": passport,
        "snils": snils,
        "birth_date": birth_date,
    }
    _validate_card(card)
    now = clock.now()
    employee = Employee(**card, hired_at=now, updated_at=now)
    session.add(employee)
    await session.flush()
    events.publish(session, "staff.employee_hired", {"employee_id": employee.id, "role": role})
    return employee


async def update_employee(session: AsyncSession, employee_id: int, hr_id: int, **changes: Any) -> Employee:
    await _require_hr(session, hr_id)
    unknown = set(changes) - set(EDITABLE_FIELDS)
    if unknown:
        raise DomainError(f"поля нельзя изменить: {', '.join(sorted(unknown))}")
    employee = await _employee(session, employee_id)
    if not employee.active:
        raise DomainError("карточка уволенного сотрудника закрыта для изменений")
    _validate_card(changes)
    for name, value in changes.items():
        setattr(employee, name, value)
    await session.flush()
    return employee


async def dismiss_employee(session: AsyncSession, employee_id: int, hr_id: int) -> Employee:
    await _require_hr(session, hr_id)
    employee = await _employee(session, employee_id)
    if not employee.active:
        raise DomainError("сотрудник уже уволен")
    now = clock.now()
    employee.dismissed_at = now
    site_id = await current_site(session, employee_id)
    await _close_assignment(session, employee_id, now)
    events.publish(session, "staff.employee_dismissed", {"employee_id": employee_id, "site_id": site_id})
    return employee


async def create_site(
    session: AsyncSession, hr_id: int, name: str, max_shift_staff: int | None = None
) -> Site:
    await _require_hr(session, hr_id)
    site = Site(name=name, max_shift_staff=max_shift_staff or settings.MAX_SHIFT_STAFF)
    session.add(site)
    await session.flush()
    return site


async def set_site_max_staff(session: AsyncSession, site_id: int, hr_id: int, value: int) -> Site:
    await _require_hr(session, hr_id)
    if not 1 <= value <= settings.SHIFT_STAFF_CEILING:
        raise DomainError(f"на смене может быть от 1 до {settings.SHIFT_STAFF_CEILING} сотрудников")
    site = await _site(session, site_id)
    site.max_shift_staff = value
    await session.flush()
    return site


async def current_site(session: AsyncSession, employee_id: int) -> int | None:
    return await session.scalar(
        select(Assignment.site_id).where(Assignment.employee_id == employee_id, Assignment.ended_at.is_(None))
    )


async def _close_assignment(
    session: AsyncSession, employee_id: int, now: datetime
) -> tuple[Assignment | None, bool]:
    """Закрывает текущее закрепление; возвращает его и признак, был ли сотрудник ответственным."""
    current = await session.scalar(
        select(Assignment).where(Assignment.employee_id == employee_id, Assignment.ended_at.is_(None))
    )
    if current is None:
        return None, False
    current.ended_at = now
    site = await session.get(Site, current.site_id)
    was_responsible = site.responsible_id == employee_id
    if was_responsible:
        site.responsible_id = None
    await session.flush()
    return current, was_responsible


async def transfer_employee(session: AsyncSession, employee_id: int, site_id: int, hr_id: int) -> Assignment:
    """Закрепить сотрудника за площадкой; если он работал на другой — перевести."""
    await _require_hr(session, hr_id)
    employee = await _employee(session, employee_id)
    if not employee.active:
        raise DomainError("уволенного сотрудника нельзя закрепить за площадкой")
    await _site(session, site_id)
    if await current_site(session, employee_id) == site_id:
        raise DomainError("сотрудник уже работает на этой площадке")
    now = clock.now()
    old, was_responsible = await _close_assignment(session, employee_id, now)
    assignment = Assignment(employee_id=employee_id, site_id=site_id, started_at=now)
    session.add(assignment)
    await session.flush()
    if old is not None:
        events.publish(
            session,
            "staff.employee_transferred",
            {
                "employee_id": employee_id,
                "from_site_id": old.site_id,
                "to_site_id": site_id,
                "was_responsible": was_responsible,
            },
        )
    return assignment


async def appoint_responsible(session: AsyncSession, site_id: int, employee_id: int, hr_id: int) -> Site:
    await _require_hr(session, hr_id)
    site = await _site(session, site_id)
    employee = await _employee(session, employee_id)
    if employee.role not in settings.RESPONSIBLE_ROLES:
        raise DomainError("ответственным за площадку может быть только руководитель")
    if await current_site(session, employee_id) != site_id:
        raise DomainError("ответственный должен работать на этой площадке")
    site.responsible_id = employee_id
    await session.flush()
    return site


# --- смены -------------------------------------------------------------------


async def create_shift(
    session: AsyncSession,
    *,
    site_id: int,
    responsible_id: int,
    starts_at: datetime,
    ends_at: datetime,
    capacity: int | None = None,
    min_staff: int = 1,
    required_clearance: str | None = None,
) -> Shift:
    site = await _require_responsible(session, site_id, responsible_id)
    now = clock.now()
    if starts_at <= now:
        raise DomainError("нельзя запланировать смену на прошедшее время")
    if starts_at > now + timedelta(days=settings.PLANNING_HORIZON_DAYS):
        raise DomainError(f"смены планируются не дальше чем на {settings.PLANNING_HORIZON_DAYS} дней")
    if ends_at <= starts_at or ends_at - starts_at > timedelta(hours=settings.MAX_SHIFT_HOURS):
        raise DomainError(f"смена длится от нуля до {settings.MAX_SHIFT_HOURS} часов")
    if required_clearance is not None and await session.get(ClearanceKind, required_clearance) is None:
        raise NotFound(f"вид допуска {required_clearance}")
    capacity = site.max_shift_staff if capacity is None else capacity
    if min_staff > capacity:
        raise DomainError("минимальный состав смены больше её вместимости")
    shift = Shift(
        site_id=site_id,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        min_staff=min_staff,
        required_clearance=required_clearance,
        understaffed=min_staff > 0,
        created_by=responsible_id,
    )
    session.add(shift)
    await session.flush()
    return shift


async def roster(session: AsyncSession, shift_id: int) -> list[int]:
    rows = await session.scalars(
        select(ShiftMember.employee_id)
        .where(ShiftMember.shift_id == shift_id, ShiftMember.status == "assigned")
        .order_by(ShiftMember.id)
    )
    return list(rows.all())


async def _staff_count(session: AsyncSession, shift_id: int) -> int:
    return await session.scalar(
        select(func.count()).where(ShiftMember.shift_id == shift_id, ShiftMember.status == "assigned")
    )


async def active_clearance(session: AsyncSession, employee_id: int, kind: str) -> Clearance | None:
    return await session.scalar(
        select(Clearance).where(
            Clearance.employee_id == employee_id, Clearance.kind == kind, Clearance.status == "active"
        )
    )


async def _check_rest(session: AsyncSession, shift: Shift, employee_id: int) -> None:
    rest = timedelta(hours=settings.MIN_REST_HOURS)
    clash = await session.scalar(
        select(Shift.id)
        .join(ShiftMember, ShiftMember.shift_id == Shift.id)
        .where(
            ShiftMember.employee_id == employee_id,
            ShiftMember.status == "assigned",
            Shift.status == "planned",
            Shift.id != shift.id,
            Shift.starts_at < shift.ends_at + rest,
            Shift.ends_at + rest > shift.starts_at,
        )
        .limit(1)
    )
    if clash is not None:
        raise DomainError(
            f"между сменами сотрудника должно быть не меньше {settings.MIN_REST_HOURS} часов отдыха"
        )


async def assign_to_shift(
    session: AsyncSession, shift_id: int, employee_id: int, responsible_id: int
) -> ShiftMember:
    shift = await _shift(session, shift_id)
    await _require_responsible(session, shift.site_id, responsible_id)
    if shift.status != "planned" or shift.starts_at <= clock.now():
        raise DomainError("смена уже прошла или отменена")
    employee = await _employee(session, employee_id)
    if not employee.active:
        raise DomainError("сотрудник уволен")
    missing = missing_fields(employee)
    if missing:
        raise DomainError(f"в карточке сотрудника не заполнено: {', '.join(missing)}")
    if await current_site(session, employee_id) != shift.site_id:
        raise DomainError("сотрудник не закреплён за площадкой смены")
    if shift.required_clearance is not None:
        # истечение допуска до смены отрабатывает jobs.expire_clearances
        if await active_clearance(session, employee_id, shift.required_clearance) is None:
            raise DomainError("у сотрудника нет действующего допуска для этой смены")
    if employee_id in await roster(session, shift_id):
        raise DomainError("сотрудник уже назначен на смену")
    if await _staff_count(session, shift_id) >= shift.capacity:
        raise DomainError("смена полностью укомплектована")
    await _check_rest(session, shift, employee_id)

    member = ShiftMember(shift_id=shift_id, employee_id=employee_id, assigned_at=clock.now())
    session.add(member)
    await session.flush()
    if shift.understaffed and await _staff_count(session, shift_id) >= shift.min_staff:
        shift.understaffed = False
    return member


async def _remove_member(session: AsyncSession, member: ShiftMember, shift: Shift, reason: str) -> None:
    member.status = "removed"
    member.removed_at = clock.now()
    member.removed_reason = reason
    events.publish(
        session,
        "staff.shift_member_removed",
        {
            "shift_id": shift.id,
            "site_id": shift.site_id,
            "employee_id": member.employee_id,
            "reason": reason,
        },
    )


async def remove_from_shift(
    session: AsyncSession, shift_id: int, employee_id: int, responsible_id: int
) -> None:
    shift = await _shift(session, shift_id)
    await _require_responsible(session, shift.site_id, responsible_id)
    member = await session.scalar(
        select(ShiftMember).where(
            ShiftMember.shift_id == shift_id,
            ShiftMember.employee_id == employee_id,
            ShiftMember.status == "assigned",
        )
    )
    if member is None:
        raise NotFound(f"сотрудник {employee_id} на смене {shift_id}")
    await _remove_member(session, member, shift, reason="manual")


async def cancel_shift(session: AsyncSession, shift_id: int, responsible_id: int) -> Shift:
    shift = await _shift(session, shift_id)
    await _require_responsible(session, shift.site_id, responsible_id)
    if shift.status != "planned":
        raise DomainError("отменить можно только запланированную смену")
    shift.status = "cancelled"
    members = (
        await session.scalars(
            select(ShiftMember).where(ShiftMember.shift_id == shift_id, ShiftMember.status == "assigned")
        )
    ).all()
    for member in members:
        await _remove_member(session, member, shift, reason="shift_cancelled")
    return shift


async def drop_from_future_shifts(
    session: AsyncSession,
    employee_id: int,
    *,
    reason: str,
    site_id: int | None = None,
    clearance_kind: str | None = None,
) -> list[int]:
    """Снимает сотрудника с ещё не начавшихся смен (всех, площадки или требующих допуска)."""
    query = (
        select(ShiftMember, Shift)
        .join(Shift, Shift.id == ShiftMember.shift_id)
        .where(
            ShiftMember.employee_id == employee_id,
            ShiftMember.status == "assigned",
            Shift.status == "planned",
            Shift.starts_at > clock.now(),
        )
        .order_by(Shift.starts_at)
    )
    if site_id is not None:
        query = query.where(Shift.site_id == site_id)
    if clearance_kind is not None:
        query = query.where(Shift.required_clearance == clearance_kind)
    dropped = []
    for member, shift in await session.execute(query):
        await _remove_member(session, member, shift, reason=reason)
        dropped.append(shift.id)
    return dropped


async def check_staffing(session: AsyncSession, shift_id: int) -> bool:
    """Помечает смену недоукомплектованной; True, если пометка появилась только что."""
    shift = await _shift(session, shift_id)
    if shift.status != "planned" or shift.starts_at <= clock.now() or shift.understaffed:
        return False
    staffed = await _staff_count(session, shift_id)
    if staffed >= shift.min_staff:
        return False
    shift.understaffed = True
    events.publish(
        session,
        "staff.shift_understaffed",
        {"shift_id": shift.id, "site_id": shift.site_id, "staffed": staffed, "min_staff": shift.min_staff},
    )
    return True


async def site_shifts(session: AsyncSession, site_id: int, since: datetime, until: datetime) -> list[Shift]:
    rows = await session.scalars(
        select(Shift)
        .where(Shift.site_id == site_id, Shift.starts_at >= since, Shift.starts_at < until)
        .order_by(Shift.starts_at, Shift.id)
    )
    return list(rows.all())


# --- инструктажи и допуски ---------------------------------------------------


async def hold_briefing(
    session: AsyncSession, *, site_id: int, employee_id: int, topic: str, instructor_id: int
) -> Briefing:
    await _require_responsible(session, site_id, instructor_id)
    if instructor_id == employee_id:
        raise DomainError("инструктаж нельзя провести самому себе")
    if await current_site(session, employee_id) != site_id:
        raise DomainError("инструктаж проводится на площадке, где работает сотрудник")
    briefing = Briefing(
        employee_id=employee_id,
        site_id=site_id,
        topic=topic,
        instructor_id=instructor_id,
        held_at=clock.now(),
    )
    session.add(briefing)
    await session.flush()
    return briefing


async def _fresh_briefing(session: AsyncSession, employee_id: int, topic: str) -> Briefing | None:
    since = clock.now() - timedelta(days=settings.BRIEFING_VALID_DAYS)
    return await session.scalar(
        select(Briefing)
        .where(Briefing.employee_id == employee_id, Briefing.topic == topic, Briefing.held_at >= since)
        .order_by(Briefing.held_at.desc())
        .limit(1)
    )


async def grant_clearance(session: AsyncSession, employee_id: int, kind: str, hr_id: int) -> Clearance:
    await _require_hr(session, hr_id)
    employee = await _employee(session, employee_id)
    if not employee.active:
        raise DomainError("сотрудник уволен")
    missing = missing_fields(employee)
    if missing:
        raise DomainError(f"в карточке сотрудника не заполнено: {', '.join(missing)}")
    clearance_kind = await session.get(ClearanceKind, kind)
    if clearance_kind is None:
        raise NotFound(f"вид допуска {kind}")
    if await active_clearance(session, employee_id, kind) is not None:
        raise DomainError("у сотрудника уже есть действующий допуск этого вида")
    briefing = None
    if clearance_kind.briefing_topic:
        briefing = await _fresh_briefing(session, employee_id, clearance_kind.briefing_topic)
        if briefing is None:
            raise DomainError(
                f"для допуска нужен инструктаж «{clearance_kind.briefing_topic}» "
                f"не старше {settings.BRIEFING_VALID_DAYS} дней"
            )
    now = clock.now()
    clearance = Clearance(
        employee_id=employee_id,
        kind=kind,
        briefing_id=briefing.id if briefing else None,
        granted_by=hr_id,
        granted_at=now,
        expires_at=now + timedelta(days=clearance_kind.valid_days),
    )
    session.add(clearance)
    await session.flush()
    events.publish(
        session,
        "staff.clearance_granted",
        {"clearance_id": clearance.id, "employee_id": employee_id, "kind": kind},
    )
    return clearance


def _revoke(session: AsyncSession, clearance: Clearance, reason: str) -> None:
    clearance.status = "revoked"
    clearance.revoked_at = clock.now()
    clearance.revoke_reason = reason
    events.publish(
        session,
        "staff.clearance_revoked",
        {
            "clearance_id": clearance.id,
            "employee_id": clearance.employee_id,
            "kind": clearance.kind,
            "reason": reason,
        },
    )


async def revoke_clearance(session: AsyncSession, clearance_id: int, hr_id: int, reason: str) -> Clearance:
    await _require_hr(session, hr_id)
    clearance = await session.get(Clearance, clearance_id)
    if clearance is None:
        raise NotFound(f"допуск {clearance_id}")
    if clearance.status != "active":
        raise DomainError("допуск уже не действует")
    _revoke(session, clearance, reason)
    return clearance


async def revoke_all_clearances(session: AsyncSession, employee_id: int, reason: str) -> list[Clearance]:
    clearances = (
        await session.scalars(
            select(Clearance).where(Clearance.employee_id == employee_id, Clearance.status == "active")
        )
    ).all()
    for clearance in clearances:
        _revoke(session, clearance, reason)
    return list(clearances)


async def revoke_for_recheck(session: AsyncSession, employee_id: int, fields: list[str]) -> list[Clearance]:
    """Отзывает допуски, виды которых требуют перепроверки при изменении этих полей."""
    clearances = (
        await session.scalars(
            select(Clearance)
            .join(ClearanceKind, ClearanceKind.code == Clearance.kind)
            .where(
                Clearance.employee_id == employee_id,
                Clearance.status == "active",
                ClearanceKind.recheck_fields.overlap(fields),
            )
            .order_by(Clearance.id)
        )
    ).all()
    for clearance in clearances:
        _revoke(session, clearance, "recheck")
    return list(clearances)


# --- уведомления ответственных ----------------------------------------------


async def raise_alert(
    session: AsyncSession, *, site_id: int, kind: str, body: str, shift_id: int | None = None
) -> Alert | None:
    if shift_id is not None:
        duplicate = await session.scalar(
            select(Alert.id).where(Alert.shift_id == shift_id, Alert.kind == kind, Alert.read_at.is_(None))
        )
        if duplicate is not None:
            return None
    site = await _site(session, site_id)
    alert = Alert(
        recipient_id=site.responsible_id,
        site_id=site_id,
        shift_id=shift_id,
        kind=kind,
        body=body,
        created_at=clock.now(),
    )
    session.add(alert)
    await session.flush()
    return alert


async def alerts_for_site(session: AsyncSession, site_id: int, *, unread_only: bool = True) -> list[Alert]:
    query = select(Alert).where(Alert.site_id == site_id).order_by(Alert.id)
    if unread_only:
        query = query.where(Alert.read_at.is_(None))
    return list((await session.scalars(query)).all())


async def mark_alert_read(session: AsyncSession, alert_id: int, reader_id: int) -> Alert:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise NotFound(f"уведомление {alert_id}")
    site = await _site(session, alert.site_id)
    if reader_id not in (alert.recipient_id, site.responsible_id):
        raise AccessDenied("уведомление адресовано другому сотруднику")
    alert.read_at = alert.read_at or clock.now()
    return alert
