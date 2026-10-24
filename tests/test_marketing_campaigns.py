from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError

from libs import db
from libs.errors import DomainError
from libs.events import OutboxEvent
from services.marketing import consumers, jobs, service
from tests import marketing_factories as mf
from tests.factories import T0, act, read, travel


@pytest.fixture(autouse=True)
async def staff() -> None:
    await mf.staff()


async def _topics(s) -> list[str]:
    return list((await s.scalars(select(OutboxEvent.topic).order_by(OutboxEvent.id))).all())


async def test_launch_prepares_sends_and_summarizes() -> None:
    await mf.templates()
    audience_id = await mf.audience()
    campaign_id = await mf.launched(audience_id, subject="Новинки марта")

    campaign = await mf.campaign_row(campaign_id)
    assert campaign.status == "sent"
    assert (campaign.launched_at, campaign.finished_at) == (T0, T0)
    assert (campaign.recipients_count, campaign.sent_count, campaign.skipped_count) == (3, 3, 0)

    sent = await mf.messages(campaign_id)
    assert sent["anna@example.org"].body == "[1/paid] Новинки марта. Здравствуйте, Анна Петрова!"
    assert sent["boris@example.org"].body.startswith("[1/social]")
    assert sent["vika@example.org"].body.startswith("[1/vip]")
    assert {m.status for m in sent.values()} == {"sent"}
    assert all(m.sent_at == T0 for m in sent.values())

    assert (await mf.audience_row(audience_id)).last_campaign_at == T0
    assert await read(_topics) == [
        "marketing.campaign_launched",
        "marketing.campaign_prepared",
        "marketing.campaign_finished",
    ]


async def test_reader_without_template_is_skipped() -> None:
    await mf.template("social")
    await mf.template("vip", venue=None)
    audience_id = await mf.audience()
    campaign_id = await mf.launched(audience_id)

    sent = await mf.messages(campaign_id)
    assert sent["boris@example.org"].body.startswith("[1/social]")
    assert sent["vika@example.org"].body.startswith("[сеть/vip]")
    # для платной группы нет шаблона ни у площадки, ни у сети
    assert sent["anna@example.org"].status == "skipped"
    assert sent["anna@example.org"].skip_reason == "no_template"
    assert sent["anna@example.org"].sent_at is None
    campaign = await mf.campaign_row(campaign_id)
    assert (campaign.sent_count, campaign.skipped_count) == (2, 1)


async def test_unsubscribed_reader_excluded_from_future_campaigns() -> None:
    await mf.templates()
    audience_id = await mf.audience()
    await mf.launched(audience_id)

    first = await act(service.unsubscribe, email="Anna@example.org")
    again = await act(service.unsubscribe, email="anna@example.org", venue_id=mf.VENUE)
    assert again.id == first.id
    assert [m.opted_out for m in await mf.members("anna@example.org")] == [True]

    travel(T0 + timedelta(days=3))
    campaign_id = await mf.launched(audience_id)
    assert set(await mf.messages(campaign_id)) == {"boris@example.org", "vika@example.org"}
    assert (await mf.campaign_row(campaign_id)).recipients_count == 2


async def test_unsubscribe_skips_messages_not_yet_sent() -> None:
    await mf.templates()
    audience_id = await mf.audience()
    campaign_id = await mf.campaign(audience_id)
    await mf.run(service.launch_campaign, campaign_id, mf.MANAGER)
    await mf.run(service.prepare_messages, campaign_id)
    assert {m.status for m in (await mf.messages(campaign_id)).values()} == {"queued"}

    await act(consumers.on_unsubscribed, {"email": "boris@example.org", "venue_id": None})

    sent = await mf.messages(campaign_id)
    assert (sent["boris@example.org"].status, sent["boris@example.org"].skip_reason) == (
        "skipped",
        "unsubscribed",
    )
    assert sent["anna@example.org"].status == "sent"
    assert (await mf.campaign_row(campaign_id)).skipped_count == 1


async def test_venue_unsubscribe_keeps_other_venues() -> None:
    await mf.templates()
    await mf.templates(venue=mf.VENUE_2)
    here = await mf.audience()
    there = await mf.audience(venue=mf.VENUE_2)

    await act(service.unsubscribe, email="anna@example.org", venue_id=mf.VENUE)

    assert "anna@example.org" not in await mf.messages(await mf.launched(here))
    assert "anna@example.org" in await mf.messages(await mf.launched(there, venue=mf.VENUE_2))


async def test_audience_rests_between_campaigns() -> None:
    await mf.templates()
    audience_id = await mf.audience()
    await mf.launched(audience_id)

    travel(T0 + timedelta(days=1))
    second = await mf.campaign(audience_id)
    with pytest.raises(DomainError, match="меньше 3 дней назад"):
        await act(service.launch_campaign, second, mf.MANAGER)

    travel(T0 + timedelta(days=3))
    await act(service.launch_campaign, second, mf.MANAGER)
    assert (await mf.campaign_row(second)).status == "sent"
    with pytest.raises(DomainError, match="уже запущена или закрыта"):
        await act(service.launch_campaign, second, mf.MANAGER)


async def test_one_running_campaign_per_audience() -> None:
    audience_id = await mf.audience()
    first, second = await mf.campaign(audience_id), await mf.campaign(audience_id)
    await mf.run(service.launch_campaign, first, mf.MANAGER)
    with pytest.raises(DomainError, match="уже идёт другая кампания"):
        await mf.run(service.launch_campaign, second, mf.MANAGER)
    sql = f"UPDATE marketing.campaigns SET status = 'sending' WHERE id = {second}"
    with pytest.raises(IntegrityError, match="campaigns_audience_active_uq"):
        async with db.engine().begin() as conn:
            await conn.exec_driver_sql(sql)


async def test_finished_campaign_and_sent_letters_are_frozen() -> None:
    await mf.templates()
    campaign_id = await mf.launched(await mf.audience())
    with pytest.raises(DomainError, match="ещё не запущена"):
        await act(service.cancel_campaign, campaign_id, mf.MANAGER)

    async with db.engine().connect() as conn:
        with pytest.raises(DBAPIError, match=f"кампания {campaign_id} уже в статусе sent"):
            await conn.exec_driver_sql(
                f"UPDATE marketing.campaigns SET status = 'draft' WHERE id = {campaign_id}"
            )
        await conn.rollback()
        with pytest.raises(DBAPIError, match="текст менять нельзя"):
            await conn.exec_driver_sql(
                f"UPDATE marketing.sent_messages SET body = 'другое' WHERE campaign_id = {campaign_id}"
            )


async def test_repeated_bounces_unsubscribe_address() -> None:
    await mf.templates()
    reader = (("anna@example.org", "Анна Петрова", "paid"),)
    campaign_ids = [await mf.launched(await mf.audience(f"Аудитория {n}", readers=reader)) for n in range(3)]
    message_ids = [(await mf.messages(c))["anna@example.org"].id for c in campaign_ids]

    for message_id in message_ids[:2]:
        await act(service.register_bounce, message_id)
    assert await mf.unsubscriptions("anna@example.org") == []
    with pytest.raises(DomainError, match="только по отправленному письму"):
        await act(service.register_bounce, message_ids[0])

    await act(service.register_bounce, message_ids[2])
    [unsub] = await mf.unsubscriptions("anna@example.org")
    assert (unsub.reason, unsub.venue_id) == ("bounce", None)
    assert all(m.opted_out for m in await mf.members("anna@example.org"))
    assert (await mf.campaign_row(campaign_ids[0])).sent_count == 1


async def test_job_launches_due_campaigns() -> None:
    await mf.templates()
    fresh = await mf.audience("Новые читатели")
    tired = await mf.audience("Все читатели")
    await mf.launched(tired)
    due = await mf.campaign(fresh, scheduled_at=T0 + timedelta(hours=2))
    blocked = await mf.campaign(tired, scheduled_at=T0 + timedelta(hours=1))
    later = await mf.campaign(fresh, scheduled_at=T0 + timedelta(days=5))

    assert await act(jobs.launch_due, T0 + timedelta(hours=1)) == []

    travel(T0 + timedelta(hours=2))
    assert await act(jobs.launch_due, T0 + timedelta(hours=2)) == [due]
    assert (await mf.campaign_row(due)).status == "sent"
    assert (await mf.campaign_row(blocked)).status == "scheduled"
    assert (await mf.campaign_row(later)).status == "scheduled"

    travel(T0 + timedelta(days=3))
    assert await act(jobs.launch_due, T0 + timedelta(days=3)) == [blocked]
