from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from libs import db, events
from libs.errors import AccessDenied, DomainError
from services.staff import service as staff
from services.staff.models import Clearance, Employee
from tests.factories import T0, act, read, travel
from tests.staff_factories import CASH, FIRE, RARE, card, cleared, hire, put_on, roster, shift, staff_world


async def _clearance(clearance_id: int) -> Clearance:
    async def get(s, cid):
        return await s.get(Clearance, cid)

    return await read(get, clearance_id)


async def test_only_hr_hires() -> None:
    w = await staff_world()
    with pytest.raises(AccessDenied):
        await act(staff.hire_employee, w.boss_north, role="librarian", **card())


async def test_card_is_validated_on_hire() -> None:
    w = await staff_world()
    bad_snils = card() | {"snils": "112-233-445 96"}
    with pytest.raises(DomainError, match="СНИЛС"):
        await act(staff.hire_employee, w.hr, role="cashier", **bad_snils)
    minor = card() | {"birth_date": date(2010, 1, 1)}
    with pytest.raises(DomainError, match="не моложе 18"):
        await act(staff.hire_employee, w.hr, role="cashier", **minor)
    with pytest.raises(DomainError, match="должность"):
        await act(staff.hire_employee, w.hr, role="janitor", **card())
    assert staff.snils_valid("112-233-445 95")
    with pytest.raises(IntegrityError, match="employees_passport_format"):
        await act(staff.hire_employee, w.hr, role="guard", **(card() | {"passport": "45 00 12"}))


async def test_incomplete_card_is_saved_but_lists_missing_fields() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north, passport=None, snils=None)

    async def get(s):
        return await s.get(Employee, employee_id)

    employee = await read(get)
    assert staff.missing_fields(employee) == ["passport", "snils"]
    with pytest.raises(DomainError, match="не заполнено: passport, snils"):
        await act(staff.grant_clearance, employee_id, RARE, w.hr)


async def test_passport_reused_only_after_dismissal() -> None:
    w = await staff_world()
    first = card()
    employee_id = await hire(w, w.north, **first)
    clone = first | {"snils": card()["snils"]}
    with pytest.raises(IntegrityError, match="employees_passport_active_uq"):
        await hire(w, None, **clone)
    await act(staff.dismiss_employee, employee_id, w.hr)
    assert await hire(w, None, **clone) != employee_id


async def test_tracked_change_publishes_employee_updated() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north)
    travel(T0 + timedelta(hours=2))
    async with db.sessionmaker().begin() as s:
        await staff.update_employee(s, employee_id, w.hr, full_name="Новая Фамилия", role="cashier")
        pending = (
            await s.scalars(
                select(events.OutboxEvent).where(events.OutboxEvent.topic == "staff.employee_updated")
            )
        ).all()
        employee = await s.get(Employee, employee_id)
    assert [e.payload for e in pending] == [{"employee_id": employee_id, "fields": ["full_name", "role"]}]
    assert employee.updated_at == T0 + timedelta(hours=2)
    await events.dispatch_pending()


async def test_card_change_revokes_clearances_needing_recheck() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north, role="cashier")
    cash = await cleared(w, employee_id, CASH)
    fire = await cleared(w, employee_id, FIRE)
    rare = await cleared(w, employee_id, RARE)

    await act(staff.update_employee, employee_id, w.hr, full_name="Сотрудник Переименованный")

    assert (await _clearance(cash)).status == "revoked"
    assert (await _clearance(cash)).revoke_reason == "recheck"
    assert (await _clearance(fire)).status == "active"
    assert (await _clearance(rare)).status == "active"


async def test_same_value_is_not_a_change() -> None:
    w = await staff_world()
    fields = card()
    employee_id = await hire(w, w.north, **fields)
    cash = await cleared(w, employee_id, CASH)
    await act(staff.update_employee, employee_id, w.hr, passport=fields["passport"])
    assert (await _clearance(cash)).status == "active"


async def test_regrant_after_recheck_needs_fresh_briefing() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north, role="cashier")
    await cleared(w, employee_id, CASH)
    await act(staff.update_employee, employee_id, w.hr, passport="4600 123456")
    # инструктаж ещё свежий — допуск можно оформить заново
    await act(staff.grant_clearance, employee_id, CASH, w.hr)
    with pytest.raises(DomainError, match="уже есть"):
        await act(staff.grant_clearance, employee_id, CASH, w.hr)
    travel(T0 + timedelta(days=40))
    await act(staff.update_employee, employee_id, w.hr, passport="4600 654321")
    with pytest.raises(DomainError, match="инструктаж «Кассовая дисциплина»"):
        await act(staff.grant_clearance, employee_id, CASH, w.hr)


async def test_dismissal_closes_card_and_releases_everything() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north)
    rare = await cleared(w, employee_id, RARE)
    shift_id = await shift(w, w.north, min_staff=0)
    await put_on(w, shift_id, employee_id)
    await act(staff.dismiss_employee, employee_id, w.hr)

    assert (await _clearance(rare)).status == "revoked"
    assert await roster(shift_id) == []
    assert await read(staff.current_site, employee_id) is None
    with pytest.raises(DomainError, match="уволенного"):
        await act(staff.update_employee, employee_id, w.hr, full_name="Кто-то")
    with pytest.raises(DomainError, match="уже уволен"):
        await act(staff.dismiss_employee, employee_id, w.hr)
