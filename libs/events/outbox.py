"""Transactional outbox.

Событие пишется в events.outbox в той же транзакции, что и изменение данных.
В проде relay.py перекладывает события в Redis Streams, а воркеры сервисов читают их
consumer-группами. В тестах dispatch_pending() доставляет события синхронно.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from libs import clock, db
from libs.events import registry


class OutboxEvent(db.Base):
    __tablename__ = "outbox"
    __table_args__ = {"schema": "events"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    topic: Mapped[str]
    payload: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]
    processed_at: Mapped[datetime | None]


def publish(session: Session | Any, topic: str, payload: dict[str, Any]) -> None:
    session.add(OutboxEvent(topic=topic, payload=payload, created_at=clock.now()))


async def dispatch_pending(max_events: int = 5_000) -> int:
    sm = db.sessionmaker()
    handled = 0
    while True:
        async with sm() as s:
            batch = (
                await s.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.processed_at.is_(None))
                    .order_by(OutboxEvent.id)
                    .limit(50)
                )
            ).all()
        if not batch:
            return handled
        for ev in batch:
            for handler in registry.handlers(ev.topic):
                async with sm.begin() as hs:
                    await handler(hs, ev.payload)
            async with sm.begin() as s2:
                await s2.execute(
                    update(OutboxEvent).where(OutboxEvent.id == ev.id).values(processed_at=clock.now())
                )
            handled += 1
            if handled > max_events:
                raise RuntimeError("event dispatch does not converge")
