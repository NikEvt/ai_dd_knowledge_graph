"""T04: правило «одна заявка клиента на сферу» действует и между социальной и платной заявками."""

from support import LAW, BOOK_L1, REP_PLAIN, invoice, new_application, paid_application, pass_review, read, stage, submit

from services.billing.public import active_books_invoice


async def test_t04_social_approval_closes_paid_duplicate() -> None:
    paid = await new_application()
    await pass_review(paid)
    await invoice(paid)
    social = await new_application(social=True, rep=REP_PLAIN)
    await pass_review(social)
    assert await stage(social) == "awaiting_issue"
    assert await stage(paid) == "closed_duplicate"
    assert await read(active_books_invoice, paid) is None


async def test_t04_paid_payment_closes_social_duplicate() -> None:
    social = await new_application(social=True, rep=REP_PLAIN)
    await submit(social)
    paid, _ = await paid_application()
    assert await stage(paid) == "awaiting_issue"
    assert await stage(social) == "closed_duplicate"


async def test_t04_other_sphere_not_affected() -> None:
    paid = await new_application()
    await pass_review(paid)
    social = await new_application(social=True, sphere=LAW, books=(BOOK_L1,))
    await pass_review(social)
    assert await stage(paid) == "awaiting_invoice"
