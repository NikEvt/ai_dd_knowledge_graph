from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from libs import clock, events
from services.staff.models import Employee

TRACKED_FIELDS = ("full_name", "passport", "snils", "birth_date", "role")


@event.listens_for(Session, "before_flush")
def _employee_changes(session: Session, flush_context: Any, instances: Any) -> None:
    for obj in list(session.dirty):
        if not isinstance(obj, Employee):
            continue
        state = inspect(obj)
        changed = [f for f in TRACKED_FIELDS if state.attrs[f].history.has_changes()]
        if not changed:
            continue
        obj.updated_at = clock.now()
        events.publish(session, "staff.employee_updated", {"employee_id": obj.id, "fields": changed})
