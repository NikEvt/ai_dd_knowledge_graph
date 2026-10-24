"""Данные сервиса сотрудников для тестов."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import count

from libs import db
from services.staff import service as staff
from services.staff.models import ClearanceKind, Employee
from tests.factories import T0, act, read

CASH, FIRE, RARE = "cash_desk", "fire_safety", "rare_books"
CASH_TOPIC, FIRE_TOPIC = "Кассовая дисциплина", "Пожарная безопасность"

TOMORROW = T0.replace(hour=0) + timedelta(days=1)

_seq = count(1)


@dataclass
class StaffWorld:
    hr: int
    north: int
    south: int
    boss_north: int
    boss_south: int

    def boss(self, site: int) -> int:
        return {self.north: self.boss_north, self.south: self.boss_south}[site]


def snils(n: int) -> str:
    body = f"{100_000_000 + n:09d}"
    total = sum(int(d) * (9 - i) for i, d in enumerate(body))
    if total > 101:
        total %= 101
    control = 0 if total in (100, 101) else total
    return f"{body[:3]}-{body[3:6]}-{body[6:]} {control:02d}"


def card(n: int | None = None) -> dict:
    n = next(_seq) if n is None else n
    return {
        "full_name": f"Сотрудник {n}",
        "passport": f"4500 {n:06d}",
        "snils": snils(n),
        "birth_date": date(1990, 1, 1) + timedelta(days=n),
    }


async def staff_world() -> StaffWorld:
    async with db.sessionmaker().begin() as s:
        hr = Employee(role="hr", hired_at=T0, updated_at=T0, **card(9000))
        s.add(hr)
        s.add_all(
            [
                ClearanceKind(
                    code=CASH,
                    title="Работа с кассой",
                    valid_days=180,
                    briefing_topic=CASH_TOPIC,
                    recheck_fields=["full_name", "passport", "snils"],
                ),
                ClearanceKind(code=FIRE, title="Пожарный пост", valid_days=365, briefing_topic=FIRE_TOPIC),
                ClearanceKind(
                    code=RARE, title="Фонд редких книг", valid_days=20, recheck_fields=["passport"]
                ),
            ]
        )
    north = (await act(staff.create_site, hr.id, "Север")).id
    south = (await act(staff.create_site, hr.id, "Юг", 3)).id
    world = StaffWorld(hr=hr.id, north=north, south=south, boss_north=0, boss_south=0)
    world.boss_north = await hire(world, north, role="manager")
    world.boss_south = await hire(world, south, role="manager")
    await act(staff.appoint_responsible, north, world.boss_north, hr.id)
    await act(staff.appoint_responsible, south, world.boss_south, hr.id)
    return world


async def hire(w: StaffWorld, site: int | None, *, role: str = "librarian", **overrides) -> int:
    fields = card() | overrides
    employee = await act(staff.hire_employee, w.hr, role=role, **fields)
    if site is not None:
        await act(staff.transfer_employee, employee.id, site, w.hr)
    return employee.id


async def shift(
    w: StaffWorld,
    site: int,
    *,
    starts_at: datetime = TOMORROW + timedelta(hours=9),
    hours: int = 8,
    capacity: int | None = None,
    min_staff: int = 1,
    clearance: str | None = None,
) -> int:
    created = await act(
        staff.create_shift,
        site_id=site,
        responsible_id=w.boss(site),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=hours),
        capacity=capacity,
        min_staff=min_staff,
        required_clearance=clearance,
    )
    return created.id


async def put_on(w: StaffWorld, shift_id: int, employee_id: int, site: int | None = None) -> None:
    await act(staff.assign_to_shift, shift_id, employee_id, w.boss(site or w.north))


async def cleared(w: StaffWorld, employee_id: int, kind: str, site: int | None = None) -> int:
    site = site or w.north
    topic = {CASH: CASH_TOPIC, FIRE: FIRE_TOPIC}.get(kind)
    if topic:
        await act(
            staff.hold_briefing,
            site_id=site,
            employee_id=employee_id,
            topic=topic,
            instructor_id=w.boss(site),
        )
    return (await act(staff.grant_clearance, employee_id, kind, w.hr)).id


async def roster(shift_id: int) -> list[int]:
    return await read(staff.roster, shift_id)
