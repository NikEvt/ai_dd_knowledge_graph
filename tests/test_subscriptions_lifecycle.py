from datetime import UTC, date, datetime, timedelta

from services.subscriptions import jobs
from tests.factories import T0, act, travel
from tests.subscriptions_factories import (
    active,
    all_notices,
    invoices,
    notice_kinds,
    open_invoice,
    pay,
    plans,
    status,
    subscribe,
    subscription,
)


def at(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 3, 0, tzinfo=UTC)


async def run(job, now: datetime):
    travel(now)
    return await act(job, now=now)


async def test_unpaid_month_moves_to_grace() -> None:
    p = await plans()
    sub_id = await active(p["std"])

    result = await run(jobs.expire_overdue, at(date(2026, 4, 1)))
    assert result["grace"] == []
    assert await status(sub_id) == "active"

    result = await run(jobs.expire_overdue, at(date(2026, 4, 2)))
    assert result["grace"] == [sub_id]
    assert await status(sub_id) == "grace"
    grace = [n for n in await all_notices(sub_id) if n.kind == "grace"]
    assert "2026-05-01" in grace[0].body


async def test_grace_ends_after_thirty_days() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    await run(jobs.expire_overdue, at(date(2026, 4, 2)))

    await run(jobs.expire_overdue, at(date(2026, 5, 1)))
    assert await status(sub_id) == "grace"

    result = await run(jobs.expire_overdue, at(date(2026, 5, 2)))
    assert result["expired"] == [sub_id]
    sub = await subscription(sub_id)
    assert sub.status == "expired"
    assert sub.closed_at == at(date(2026, 5, 2))
    assert "expired" in await notice_kinds(sub_id)


async def test_forgotten_active_subscription_expires_directly() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    result = await run(jobs.expire_overdue, at(date(2026, 6, 1)))
    assert result == {"expired": [sub_id], "grace": []}
    assert await status(sub_id) == "expired"


async def test_renewal_invoice_issued_week_before_end() -> None:
    p = await plans()
    sub_id = await active(p["std"])

    assert await run(jobs.issue_renewal_invoices, at(date(2026, 3, 24))) == []
    issued = await run(jobs.issue_renewal_invoices, at(date(2026, 3, 25)))
    assert len(issued) == 1
    invoice = await open_invoice(sub_id)
    assert (invoice.period_start, invoice.period_end) == (date(2026, 4, 2), date(2026, 5, 1))

    assert await run(jobs.issue_renewal_invoices, at(date(2026, 3, 26))) == []


async def test_paying_renewal_extends_subscription() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    await run(jobs.issue_renewal_invoices, at(date(2026, 3, 28)))
    await pay(sub_id)

    sub = await subscription(sub_id)
    assert sub.status == "active"
    assert sub.paid_until == date(2026, 5, 1)
    assert "renewed" in await notice_kinds(sub_id)


async def test_grace_subscription_returns_to_active_after_payment() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    await run(jobs.issue_renewal_invoices, at(date(2026, 3, 28)))
    await run(jobs.expire_overdue, at(date(2026, 4, 10)))
    assert await status(sub_id) == "grace"

    await pay(sub_id)
    sub = await subscription(sub_id)
    assert sub.status == "active"
    assert sub.paid_until == date(2026, 5, 1)


async def test_expired_subscription_voids_open_invoice() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    await run(jobs.issue_renewal_invoices, at(date(2026, 3, 28)))
    await run(jobs.expire_overdue, at(date(2026, 5, 10)))

    assert await status(sub_id) == "expired"
    assert [i.status for i in await invoices(sub_id)] == ["paid", "void"]


async def test_unpaid_new_subscription_expires() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])

    assert await run(jobs.expire_stale_pending, T0 + timedelta(days=14)) == []
    assert await run(jobs.expire_stale_pending, T0 + timedelta(days=14, minutes=1)) == [sub_id]
    assert await status(sub_id) == "expired"
    assert [i.status for i in await invoices(sub_id)] == ["void"]
