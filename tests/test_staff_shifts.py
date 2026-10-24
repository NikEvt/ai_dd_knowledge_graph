from datetime import timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.staff import service as staff
from services.staff.models import Shift, ShiftMember
from tests.factories import T0, act, read
from tests.staff_factories import CASH, RARE, TOMORROW, cleared, hire, put_on, roster, shift, staff_world


async def test_only_site_responsible_plans_shifts() -> None:
    w = await staff_world()
    with pytest.raises(AccessDenied, match="ответственный"):
        await act(
            staff.create_shift,
            site_id=w.north,
            responsible_id=w.boss_south,
            starts_at=TOMORROW,
            ends_at=TOMORROW + timedelta(hours=8),
        )


async def test_shift_time_rules() -> None:
    w = await staff_world()
    with pytest.raises(DomainError, match="прошедшее"):
        await shift(w, w.north, starts_at=T0 - timedelta(hours=1))
    with pytest.raises(DomainError, match="12 часов"):
        await shift(w, w.north, hours=13)
    with pytest.raises(DomainError, match="60 дней"):
        await shift(w, w.north, starts_at=T0 + timedelta(days=61))


async def test_capacity_bounded_by_site_maximum() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.south)
    shifts = await read(staff.site_shifts, w.south, T0, T0 + timedelta(days=7))
    assert [(s.id, s.capacity) for s in shifts] == [(shift_id, 3)]
    with pytest.raises(IntegrityError, match="exceeds site maximum 3"):
        await shift(w, w.south, capacity=4)
    with pytest.raises(IntegrityError, match="shifts_capacity_check"):
        await shift(w, w.north, capacity=0, min_staff=0)


async def test_site_maximum_cannot_drop_below_planned_shifts() -> None:
    w = await staff_world()
    await shift(w, w.north, capacity=5)
    with pytest.raises(IntegrityError, match="planned shifts above 4"):
        await act(staff.set_site_max_staff, w.north, w.hr, 4)
    await act(staff.set_site_max_staff, w.north, w.hr, 5)
    with pytest.raises(DomainError, match="от 1 до 20"):
        await act(staff.set_site_max_staff, w.north, w.hr, 21)


async def test_full_shift_refuses_more_staff() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.north, capacity=2)
    a, b, c = [await hire(w, w.north) for _ in range(3)]
    await put_on(w, shift_id, a)
    await put_on(w, shift_id, b)
    with pytest.raises(DomainError, match="укомплектована"):
        await put_on(w, shift_id, c)
    assert await roster(shift_id) == [a, b]


async def test_member_limit_trigger_guards_direct_inserts() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.north, capacity=1)
    a, b = await hire(w, w.north), await hire(w, w.north)
    await put_on(w, shift_id, a)
    with pytest.raises(IntegrityError, match=f"shift {shift_id} is full"):
        async with db.sessionmaker().begin() as s:
            s.add(ShiftMember(shift_id=shift_id, employee_id=b, assigned_at=T0))


async def test_capacity_cannot_shrink_below_roster() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.north, capacity=3, min_staff=0)
    for _ in range(2):
        await put_on(w, shift_id, await hire(w, w.north))
    with pytest.raises(IntegrityError, match="already has 2 staff"):
        async with db.sessionmaker().begin() as s:
            await s.execute(update(Shift).where(Shift.id == shift_id).values(capacity=1))


async def test_shift_admission_needs_full_card_and_own_site() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.north)
    employee_id = await hire(w, w.north, birth_date=None)
    with pytest.raises(DomainError, match="не заполнено: birth_date"):
        await put_on(w, shift_id, employee_id)
    stranger = await hire(w, w.south)
    with pytest.raises(DomainError, match="не закреплён"):
        await put_on(w, shift_id, stranger)


async def test_rest_between_shifts() -> None:
    w = await staff_world()
    day = await shift(w, w.north, starts_at=TOMORROW + timedelta(hours=8), hours=10)
    night = await shift(w, w.north, starts_at=TOMORROW + timedelta(hours=22), hours=8)
    next_day = await shift(w, w.north, starts_at=TOMORROW + timedelta(days=1, hours=10), hours=8)
    employee_id = await hire(w, w.north)
    await put_on(w, day, employee_id)
    with pytest.raises(DomainError, match="8 часов отдыха"):
        await put_on(w, night, employee_id)
    await put_on(w, next_day, employee_id)


async def test_shift_with_clearance_requires_active_one() -> None:
    w = await staff_world()
    cash_shift = await shift(w, w.north, clearance=CASH)
    rare_shift = await shift(w, w.north, clearance=RARE, starts_at=TOMORROW + timedelta(days=2, hours=9))
    employee_id = await hire(w, w.north, role="cashier")
    with pytest.raises(DomainError, match="допуска"):
        await put_on(w, cash_shift, employee_id)
    await cleared(w, employee_id, CASH)
    await put_on(w, cash_shift, employee_id)
    with pytest.raises(DomainError, match="допуска"):
        await put_on(w, rare_shift, employee_id)


async def test_cancel_shift_releases_staff() -> None:
    w = await staff_world()
    shift_id = await shift(w, w.north)
    employee_id = await hire(w, w.north)
    await put_on(w, shift_id, employee_id)
    await act(staff.cancel_shift, shift_id, w.boss_north)
    assert await roster(shift_id) == []
    assert await read(staff.alerts_for_site, w.north) == []
    with pytest.raises(DomainError, match="отменена"):
        await put_on(w, shift_id, employee_id)
