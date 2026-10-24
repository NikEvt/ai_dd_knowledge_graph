from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from libs import clock, db
from libs.errors import DomainError
from libs.events import dispatch_pending
from services.subscriptions import service
from services.subscriptions.models import Payment, Subscription
from tests.factories import T0, act
from tests.subscriptions_factories import (
    CLIENT_1,
    CLIENT_2,
    STUDENT,
    active,
    history,
    invoices,
    notice_kinds,
    open_invoice,
    pay,
    plans,
    status,
    subscribe,
    subscription,
)


async def test_activation_only_after_full_payment() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    await pay(sub_id, Decimal(200))
    assert await status(sub_id) == "pending"
    invoice = await open_invoice(sub_id)
    assert invoice.paid_total == Decimal(200)

    await pay(sub_id)
    sub = await subscription(sub_id)
    assert sub.status == "active"
    assert sub.activated_at == T0
    assert sub.paid_until == date(2026, 4, 1)
    assert await open_invoice(sub_id) is None
    assert [i.status for i in await invoices(sub_id)] == ["paid"]
    assert "activated" in await notice_kinds(sub_id)


async def test_overpayment_rejected() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    with pytest.raises(DomainError, match="больше остатка"):
        await pay(sub_id, Decimal(601))
    assert await status(sub_id) == "pending"


async def test_paid_invoice_does_not_take_payments() -> None:
    p = await plans()
    sub_id = await active(p["std"])
    invoice = (await invoices(sub_id))[0]
    with pytest.raises(DomainError, match="уже оплачен"):
        await act(service.record_payment, invoice.id, Decimal(10))


async def test_same_external_payment_counted_once() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    await pay(sub_id, Decimal(100), external_ref="bank-77")
    with pytest.raises(DomainError, match="уже учтён"):
        await pay(sub_id, Decimal(100), external_ref="bank-77")
    assert (await open_invoice(sub_id)).paid_total == Decimal(100)


async def test_paid_subscription_closes_pending_duplicate() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    second = await subscribe(p["std"])
    await pay(second)

    assert await status(second) == "active"
    dup = await subscription(first)
    assert dup.status == "closed_duplicate"
    assert dup.closed_at == T0
    assert [i.status for i in await invoices(first)] == ["void"]
    assert "closed_duplicate" in await notice_kinds(first)


async def test_switching_paid_plan_closes_previous_one() -> None:
    p = await plans()
    old = await active(p["std"])
    new = await active(p["std-plus"])
    assert await status(new) == "active"
    assert await status(old) == "closed_duplicate"


async def test_corporate_and_regular_are_the_same_track() -> None:
    p = await plans()
    regular = await active(p["std"])
    corp = await active(p["corp"], employer_ref="org-15")
    assert await status(corp) == "active"
    assert await status(regular) == "closed_duplicate"


async def test_social_and_paid_plans_live_together() -> None:
    p = await plans()
    paid = await active(p["std"], birth_date=STUDENT)
    social = await active(p["soc"], birth_date=STUDENT)
    assert await status(paid) == "active"
    assert await status(social) == "active"


async def test_other_clients_are_not_duplicates() -> None:
    p = await plans()
    mine = await active(p["std"])
    theirs = await active(p["std"], client=CLIENT_2)
    assert await status(mine) == "active"
    assert await status(theirs) == "active"


async def test_partly_paid_duplicate_is_refunded() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    await pay(first, Decimal(250))
    second = await active(p["std"])

    assert await status(second) == "active"
    assert [i.status for i in await invoices(first)] == ["void"]
    assert "refund" in await notice_kinds(first)


async def test_payment_for_closed_duplicate_is_refunded() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    second = await subscribe(p["std"])
    first_invoice = await open_invoice(first)
    second_invoice = await open_invoice(second)

    # Оба счёта оплачены до того, как воркер обработал события.
    async with db.sessionmaker().begin() as s:
        await service.record_payment(s, first_invoice.id, first_invoice.amount)
        await service.record_payment(s, second_invoice.id, second_invoice.amount)
    await dispatch_pending()

    assert await status(first) == "active"
    assert await status(second) == "closed_duplicate"
    assert "refund" in await notice_kinds(second)


async def test_second_subscription_on_live_plan_rejected() -> None:
    p = await plans()
    await active(p["std"])
    with pytest.raises(DomainError, match="уже есть действующий"):
        await subscribe(p["std"])


async def test_database_keeps_one_live_subscription_per_plan() -> None:
    p = await plans()
    await active(p["std"])
    with pytest.raises(IntegrityError, match="uq_subscriptions_one_active"):
        async with db.sessionmaker().begin() as s:
            s.add(
                Subscription(
                    client_ref=CLIENT_1,
                    plan_id=p["std"],
                    status="grace",
                    holder_name="Анна Петрова",
                    paid_until=date(2026, 3, 31),
                    created_at=clock.now(),
                )
            )


async def test_status_changes_are_logged() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    second = await active(p["std"])
    assert await history(second) == [("pending", "active")]
    assert await history(first) == [("pending", "closed_duplicate")]


async def test_closed_subscription_cannot_be_reopened() -> None:
    p = await plans()
    first = await subscribe(p["std"])
    await active(p["std"])
    with pytest.raises(DBAPIError, match="is closed"):
        async with db.sessionmaker().begin() as s:
            sub = await s.get(Subscription, first)
            sub.status = "pending"
            sub.closed_at = None


async def test_database_rejects_payment_above_balance() -> None:
    p = await plans()
    sub_id = await subscribe(p["std"])
    invoice = await open_invoice(sub_id)
    with pytest.raises(DBAPIError, match="exceeds invoice"):
        async with db.sessionmaker().begin() as s:
            s.add(Payment(invoice_id=invoice.id, amount=Decimal(700), paid_at=clock.now()))
