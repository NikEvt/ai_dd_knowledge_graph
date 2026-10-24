from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from libs import clock, events
from services.applications.models import Application, Client

TRACKED_FIELDS = ("full_name", "passport", "birth_date")


@event.listens_for(Session, "before_flush")
def _domain_events(session: Session, flush_context: Any, instances: Any) -> None:
    for obj in list(session.dirty):
        if isinstance(obj, Application):
            history = inspect(obj).attrs.stage.history
            if history.deleted and history.added:
                events.publish(
                    session,
                    "application.stage_changed",
                    {"application_id": obj.id, "from": history.deleted[0], "to": obj.stage},
                )
        elif isinstance(obj, Client):
            state = inspect(obj)
            changed = [f for f in TRACKED_FIELDS if state.attrs[f].history.has_changes()]
            if changed:
                obj.updated_at = clock.now()
                events.publish(
                    session,
                    "client.updated",
                    {
                        "client_id": obj.id,
                        "fields": changed,
                        "source_application_id": session.info.pop("source_application_id", None),
                    },
                )
