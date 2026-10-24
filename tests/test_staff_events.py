from datetime import timedelta

import httpx
import pytest

from libs.errors import AccessDenied
from services.staff import jobs
from services.staff import service as staff
from services.staff.app import app
from services.staff.models import Shift
from tests.factories import T0, act, read, travel
from tests.staff_factories import (
    CASH,
    RARE,
    TOMORROW,
    card,
    cleared,
    hire,
    put_on,
    roster,
    shift,
    staff_world,
)


async def _shift(shift_id: int) -> Shift:
    async def get(s):
        return await s.get(Shift, shift_id)

    return await read(get)


async def test_transfer_drops_future_shifts_at_old_site_only() -> None:
    w = await staff_world()
    employee_id = await hire(w, w.north)
    running = await shift(w, w.north, starts_at=T0 + timedelta(hours=1), hours=4)
    soon = await shift(w, w.north, min_staff=0)
    later = await shift(w, w.north, starts_at=TOMORROW + timedelta(days=2, hours=9), min_staff=0)
    for shift_id in (running, soon, later):
        await put_on(w, shift_id, employee_id)

    travel(T0 + timedelta(hours=2))
    await act(staff.transfer_employee, employee_id, w.south, w.hr)

    assert await roster(running) == [employee_id]
    assert await roster(soon) == []
    assert await roster(later) == []
    assert await read(staff.current_site, employee_id) == w.south
    south_shift = await shift(w, w.south)
    await put_on(w, south_shift, employee_id, site=w.south)
    assert await roster(south_shift) == [employee_id]


async def test_transfer_leaves_shift_understaffed_and_alerts_responsible() -> None:
    w = await staff_world()
    a, b = await hire(w, w.north), await hire(w, w.north)
    shift_id = await shift(w, w.north, min_staff=2)
    await put_on(w, shift_id, a)
    await put_on(w, shift_id, b)
    assert (await _shift(shift_id)).understaffed is False

    await act(staff.transfer_employee, a, w.south, w.hr)

    assert (await _shift(shift_id)).understaffed is True
    alerts = await read(staff.alerts_for_site, w.north)
    assert [(x.kind, x.shift_id, x.recipient_id) for x in alerts] == [
        ("understaffed", shift_id, w.boss_north)
    ]
    assert alerts[0].body == "На смене 1 из минимум 2 сотрудников"


async def test_passport_change_chain_reaches_responsible() -> None:
    """Смена паспорта -> отзыв кассового допуска -> снятие с кассовой смены -> уведомление."""
    w = await staff_world()
    cashier = await hire(w, w.north, role="cashier")
    await cleared(w, cashier, CASH)
    cash_shift = await shift(w, w.north, clearance=CASH)
    plain_shift = await shift(w, w.north, starts_at=TOMORROW + timedelta(days=1, hours=9))
    await put_on(w, cash_shift, cashier)
    await put_on(w, plain_shift, cashier)

    await act(staff.update_employee, cashier, w.hr, passport="4601 000777")

    assert await read(staff.active_clearance, cashier, CASH) is None
    assert await roster(cash_shift) == []
    assert await roster(plain_shift) == [cashier]
    alerts = await read(staff.alerts_for_site, w.north)
    assert [(x.kind, x.shift_id) for x in alerts] == [("understaffed", cash_shift)]


async def test_understaffed_alert_is_not_duplicated_until_read() -> None:
    w = await staff_world()
    a, b = await hire(w, w.north), await hire(w, w.north)
    shift_id = await shift(w, w.north)
    await put_on(w, shift_id, a)
    await act(staff.remove_from_shift, shift_id, a, w.boss_north)
    await put_on(w, shift_id, b)
    await act(staff.remove_from_shift, shift_id, b, w.boss_north)
    alerts = await read(staff.alerts_for_site, w.north)
    assert len(alerts) == 1

    with pytest.raises(AccessDenied):
        await act(staff.mark_alert_read, alerts[0].id, w.boss_south)
    await act(staff.mark_alert_read, alerts[0].id, w.boss_north)
    await put_on(w, shift_id, a)
    await act(staff.remove_from_shift, shift_id, a, w.boss_north)
    assert len(await read(staff.alerts_for_site, w.north)) == 1


async def test_transferred_responsible_leaves_site_without_one() -> None:
    w = await staff_world()
    await act(staff.transfer_employee, w.boss_north, w.south, w.hr)

    alerts = await read(staff.alerts_for_site, w.north)
    assert [(x.kind, x.recipient_id) for x in alerts] == [("no_responsible", None)]
    with pytest.raises(AccessDenied):
        await shift(w, w.north)
    new_boss = await hire(w, w.north, role="manager")
    await act(staff.appoint_responsible, w.north, new_boss, w.hr)
    w.boss_north = new_boss
    assert await shift(w, w.north)


async def test_expire_job_drops_employee_from_shifts_needing_clearance() -> None:
    w = await staff_world()
    keeper = await hire(w, w.north)
    await cleared(w, keeper, RARE)
    early = await shift(w, w.north, clearance=RARE, starts_at=T0 + timedelta(days=5))
    late = await shift(w, w.north, clearance=RARE, starts_at=T0 + timedelta(days=25))
    await put_on(w, early, keeper)
    await put_on(w, late, keeper)

    assert await act(jobs.expire_clearances, now=T0 + timedelta(days=19)) == []
    travel(T0 + timedelta(days=20))
    assert len(await act(jobs.expire_clearances, now=T0 + timedelta(days=20))) == 1

    assert await roster(early) == [keeper]
    assert await roster(late) == []
    assert (await _shift(late)).understaffed is True
    assert await read(staff.active_clearance, keeper, RARE) is None


async def test_close_finished_shifts_job() -> None:
    w = await staff_world()
    first = await shift(w, w.north, starts_at=T0 + timedelta(hours=1), hours=4)
    second = await shift(w, w.north)
    closed = await act(jobs.close_finished_shifts, now=T0 + timedelta(hours=6))
    assert closed == [first]
    assert (await _shift(second)).status == "planned"
    # закрытые смены больше не мешают уменьшить максимум площадки
    await act(staff.set_site_max_staff, w.north, w.hr, 6)


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://staff") as c:
        yield c


async def test_api_hire_and_plan_shift(client: httpx.AsyncClient) -> None:
    w = await staff_world()
    fields = card() | {"role": "guard"}
    fields["birth_date"] = fields["birth_date"].isoformat()
    r = await client.post("/employees", params={"actor_id": w.hr}, json=fields)
    assert r.status_code == 201, r.text
    employee_id = r.json()["id"]
    assert r.json()["missing_fields"] == []
    r = await client.post(
        f"/employees/{employee_id}/transfer", params={"actor_id": w.hr}, json={"site_id": w.north}
    )
    assert r.status_code == 200

    starts = TOMORROW + timedelta(hours=9)
    r = await client.post(
        "/shifts",
        params={"actor_id": w.boss_north},
        json={
            "site_id": w.north,
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=6)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    shift_id = r.json()["id"]
    r = await client.post(
        f"/shifts/{shift_id}/members", params={"actor_id": w.boss_north}, json={"employee_id": employee_id}
    )
    assert r.status_code == 201
    r = await client.get(
        f"/sites/{w.north}/shifts",
        params={"since": T0.isoformat(), "until": (T0 + timedelta(days=3)).isoformat()},
    )
    assert [(x["id"], x["staff"], x["understaffed"]) for x in r.json()] == [(shift_id, [employee_id], False)]


async def test_api_errors_map_to_statuses(client: httpx.AsyncClient) -> None:
    w = await staff_world()
    r = await client.post("/employees", params={"actor_id": w.boss_north}, json={"role": "guard"})
    assert r.status_code == 403
    r = await client.patch("/employees/999", params={"actor_id": w.hr}, json={"full_name": "Х"})
    assert r.status_code == 404
    starts = TOMORROW + timedelta(hours=9)
    r = await client.post(
        "/shifts",
        params={"actor_id": w.boss_south},
        json={
            "site_id": w.south,
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=6)).isoformat(),
            "capacity": 5,
        },
    )
    assert r.status_code == 409
    assert "exceeds site maximum" in r.json()["detail"]
