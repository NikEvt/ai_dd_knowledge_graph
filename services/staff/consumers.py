from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.staff import listeners as _listeners  # noqa: F401 - регистрирует before_flush
from services.staff import service


@subscribe("staff.employee_updated")
async def on_employee_updated(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.revoke_for_recheck(session, payload["employee_id"], payload["fields"])


@subscribe("staff.employee_dismissed")
async def on_employee_dismissed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.drop_from_future_shifts(session, payload["employee_id"], reason="dismissed")
    await service.revoke_all_clearances(session, payload["employee_id"], reason="dismissed")


@subscribe("staff.clearance_revoked")
@subscribe("staff.clearance_expired")
async def on_clearance_lost(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.drop_from_future_shifts(
        session, payload["employee_id"], reason="clearance_lost", clearance_kind=payload["kind"]
    )


@subscribe("staff.employee_transferred")
async def on_employee_transferred(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.drop_from_future_shifts(
        session, payload["employee_id"], reason="transferred", site_id=payload["from_site_id"]
    )
    if payload["was_responsible"]:
        await service.raise_alert(
            session,
            site_id=payload["from_site_id"],
            kind="no_responsible",
            body="Ответственный за площадку переведён, назначьте нового",
        )


@subscribe("staff.shift_member_removed")
async def on_shift_member_removed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.check_staffing(session, payload["shift_id"])


@subscribe("staff.shift_understaffed")
async def on_shift_understaffed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.raise_alert(
        session,
        site_id=payload["site_id"],
        shift_id=payload["shift_id"],
        kind="understaffed",
        body=f"На смене {payload['staffed']} из минимум {payload['min_staff']} сотрудников",
    )
