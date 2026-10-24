"""Данные книжного фонда для тестов inventory."""

from decimal import Decimal
from itertools import count

from libs import db
from services.inventory import service as inventory
from services.inventory.models import Copy, IllLoan, Transfer
from tests.factories import BOOK_H1, KZN, MSK, TVR, act, read

KEEPER = {MSK: 701, KZN: 702, TVR: 703}
OUTSIDER = 799

_numbers = count(1)


async def staff() -> None:
    async with db.sessionmaker().begin() as s:
        for venue_id, employee_id in KEEPER.items():
            await inventory.add_custodian(s, venue_id, employee_id)


async def copy(venue: int = MSK, book: int = BOOK_H1, inventory_no: str | None = None) -> int:
    created = await act(
        inventory.register_copy,
        custodian_id=KEEPER[venue],
        venue_id=venue,
        book_ref=book,
        inventory_no=inventory_no or f"ИН-{next(_numbers):05d}",
    )
    return created.id


async def copies(n: int, venue: int = MSK, book: int = BOOK_H1) -> list[int]:
    return [await copy(venue, book) for _ in range(n)]


async def partner(code: str = "SPB-01", daily_penalty: str = "20.00", max_active_loans: int = 5) -> int:
    created = await act(
        inventory.register_partner,
        code=code,
        name=f"Библиотека {code}",
        daily_penalty=Decimal(daily_penalty),
        max_active_loans=max_active_loans,
    )
    return created.id


async def lend(copy_id: int, partner_id: int, venue: int = MSK) -> int:
    loan = await act(inventory.issue_ill, copy_id, partner_id, KEEPER[venue])
    return loan.id


async def transfer(copy_id: int, to: int = KZN, frm: int = MSK) -> int:
    created = await act(inventory.request_transfer, copy_id, to, KEEPER[frm])
    return created.id


async def state(copy_id: int) -> str:
    return (await read(inventory.get_copy, copy_id)).state


async def get(model: type[Copy | IllLoan | Transfer], pk: int):
    async with db.sessionmaker()() as s:
        return await s.get(model, pk)


async def stock(venue: int = MSK, book: int = BOOK_H1) -> tuple[int, int]:
    return await read(inventory.stock, book, venue)
