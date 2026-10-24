from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.web import session
from services.staff import service
from services.staff.models import Employee, Shift

router = APIRouter(tags=["staff"])
Session = Annotated[AsyncSession, Depends(session)]


class EmployeeIn(BaseModel):
    role: str
    full_name: str | None = None
    passport: str | None = None
    snils: str | None = None
    birth_date: date | None = None


class EmployeePatch(BaseModel):
    role: str | None = None
    full_name: str | None = None
    passport: str | None = None
    snils: str | None = None
    birth_date: date | None = None


class EmployeeOut(BaseModel):
    id: int
    full_name: str | None
    role: str
    active: bool
    missing_fields: list[str]


class TransferIn(BaseModel):
    site_id: int


class ShiftIn(BaseModel):
    site_id: int
    starts_at: datetime
    ends_at: datetime
    capacity: int | None = None
    min_staff: int = 1
    required_clearance: str | None = None


class ShiftOut(BaseModel):
    id: int
    site_id: int
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: str
    understaffed: bool
    staff: list[int]


class MemberIn(BaseModel):
    employee_id: int


class ClearanceIn(BaseModel):
    employee_id: int
    kind: str


def _employee_out(e: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=e.id, full_name=e.full_name, role=e.role, active=e.active, missing_fields=service.missing_fields(e)
    )


async def _shift_out(s: AsyncSession, shift: Shift) -> ShiftOut:
    return ShiftOut(
        id=shift.id,
        site_id=shift.site_id,
        starts_at=shift.starts_at,
        ends_at=shift.ends_at,
        capacity=shift.capacity,
        status=shift.status,
        understaffed=shift.understaffed,
        staff=await service.roster(s, shift.id),
    )


@router.post("/employees", status_code=201)
async def hire(body: EmployeeIn, actor_id: int, s: Session) -> EmployeeOut:
    return _employee_out(await service.hire_employee(s, actor_id, **body.model_dump()))


@router.patch("/employees/{employee_id}")
async def update(employee_id: int, body: EmployeePatch, actor_id: int, s: Session) -> EmployeeOut:
    changes = body.model_dump(exclude_unset=True)
    return _employee_out(await service.update_employee(s, employee_id, actor_id, **changes))


@router.post("/employees/{employee_id}/transfer")
async def transfer(employee_id: int, body: TransferIn, actor_id: int, s: Session) -> dict[str, int]:
    assignment = await service.transfer_employee(s, employee_id, body.site_id, actor_id)
    return {"assignment_id": assignment.id, "site_id": assignment.site_id}


@router.delete("/employees/{employee_id}")
async def dismiss(employee_id: int, actor_id: int, s: Session) -> EmployeeOut:
    return _employee_out(await service.dismiss_employee(s, employee_id, actor_id))


@router.post("/shifts", status_code=201)
async def create_shift(body: ShiftIn, actor_id: int, s: Session) -> ShiftOut:
    shift = await service.create_shift(s, responsible_id=actor_id, **body.model_dump())
    return await _shift_out(s, shift)


@router.get("/sites/{site_id}/shifts")
async def shifts(site_id: int, since: datetime, until: datetime, s: Session) -> list[ShiftOut]:
    return [await _shift_out(s, x) for x in await service.site_shifts(s, site_id, since, until)]


@router.post("/shifts/{shift_id}/members", status_code=201)
async def add_member(shift_id: int, body: MemberIn, actor_id: int, s: Session) -> dict[str, int]:
    member = await service.assign_to_shift(s, shift_id, body.employee_id, actor_id)
    return {"member_id": member.id}


@router.delete("/shifts/{shift_id}/members/{employee_id}", status_code=204)
async def remove_member(shift_id: int, employee_id: int, actor_id: int, s: Session) -> None:
    await service.remove_from_shift(s, shift_id, employee_id, actor_id)


@router.post("/clearances", status_code=201)
async def grant(body: ClearanceIn, actor_id: int, s: Session) -> dict[str, int | str]:
    clearance = await service.grant_clearance(s, body.employee_id, body.kind, actor_id)
    return {"clearance_id": clearance.id, "expires_at": clearance.expires_at.isoformat()}


@router.get("/sites/{site_id}/alerts")
async def alerts(site_id: int, s: Session) -> list[dict[str, int | str | None]]:
    return [
        {"id": a.id, "kind": a.kind, "shift_id": a.shift_id, "body": a.body}
        for a in await service.alerts_for_site(s, site_id)
    ]
