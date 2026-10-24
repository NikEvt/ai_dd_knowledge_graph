"""Прод-доставка событий: outbox -> Redis Streams -> обработчики сервисов."""

import asyncio
import json

from redis.asyncio import Redis
from sqlalchemy import select, update

from libs import clock, db, settings
from libs.events import registry
from libs.events.outbox import OutboxEvent

STREAM_PREFIX = "events:"


async def relay_forever(poll_seconds: float = 0.5) -> None:
    redis = Redis.from_url(settings.REDIS_URL)
    sm = db.sessionmaker()
    while True:
        async with sm.begin() as s:
            batch = (
                await s.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.processed_at.is_(None))
                    .order_by(OutboxEvent.id)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for ev in batch:
                await redis.xadd(STREAM_PREFIX + ev.topic, {"payload": json.dumps(ev.payload)})
                await s.execute(
                    update(OutboxEvent).where(OutboxEvent.id == ev.id).values(processed_at=clock.now())
                )
        if not batch:
            await asyncio.sleep(poll_seconds)


async def consume_forever(group: str, topics: list[str], consumer: str = "worker-1") -> None:
    redis = Redis.from_url(settings.REDIS_URL)
    streams = {STREAM_PREFIX + t: ">" for t in topics}
    for stream in streams:
        try:
            await redis.xgroup_create(stream, group, id="0", mkstream=True)
        except Exception:  # noqa: BLE001 - группа уже существует
            pass
    sm = db.sessionmaker()
    while True:
        for stream, messages in await redis.xreadgroup(group, consumer, streams, count=10, block=1000):
            topic = stream.decode().removeprefix(STREAM_PREFIX)
            for msg_id, fields in messages:
                payload = json.loads(fields[b"payload"])
                for handler in registry.handlers(topic):
                    async with sm.begin() as hs:
                        await handler(hs, payload)
                await redis.xack(stream, group, msg_id)
