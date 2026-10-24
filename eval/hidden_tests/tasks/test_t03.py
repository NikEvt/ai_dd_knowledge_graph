"""T03: выдача по платной заявке открывается после оплаты не менее 50% счёта."""

from decimal import Decimal

from support import REP_PLAIN, invoice, new_application, pass_review, pay, read, stage, token

from services.billing.public import active_books_invoice


async def test_t03_half_payment_opens_issue() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)  # 110.00
    await pay(inv, Decimal("55.00"))
    assert await stage(app_id) == "awaiting_issue"
    assert await token(app_id) is not None


async def test_t03_less_than_half_keeps_waiting() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv, Decimal("54.99"))
    assert await stage(app_id) == "awaiting_payment"
    assert await token(app_id) is None


async def test_t03_duplicate_closed_at_half_payment() -> None:
    winner = await new_application()
    loser = await new_application(rep=REP_PLAIN)
    await pass_review(winner)
    await pass_review(loser)
    inv = await invoice(winner)
    await invoice(loser)
    await pay(inv, Decimal("60.00"))
    assert await stage(winner) == "awaiting_issue"
    assert await stage(loser) == "closed_duplicate"
    assert await read(active_books_invoice, loser) is None


async def test_t03_second_payment_does_not_repeat_transition() -> None:
    app_id = await new_application()
    await pass_review(app_id)
    inv = await invoice(app_id)
    await pay(inv, Decimal("60.00"))
    await pay(inv, Decimal("50.00"))
    assert await stage(app_id) == "awaiting_issue"
