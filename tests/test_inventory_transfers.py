from datetime import timedelta

import pytest
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.inventory import jobs
from services.inventory import service as inventory
from services.inventory.models import Copy, Transfer
from tests import inventory_factories as inv
from tests.factories import KZN, MSK, T0, TVR, act, travel


@pytest.fixture(autouse=True)
async def custodians(world: None) -> None:
    await inv.staff()


async def test_transfer_moves_copy_and_stock() -> None:
    moving, _ = await inv.copies(2)
    transfer_id = await inv.transfer(moving)
    await act(inventory.ship_transfer, transfer_id, inv.KEEPER[MSK])
    assert await inv.state(moving) == "in_transit"
    assert await inv.stock(MSK) == (2, 1)

    with pytest.raises(AccessDenied):
        await act(inventory.receive_transfer, transfer_id, inv.KEEPER[MSK])
    await act(inventory.receive_transfer, transfer_id, inv.KEEPER[KZN])
    copy = await inv.get(Copy, moving)
    assert (copy.venue_id, copy.state) == (KZN, "available")
    assert await inv.stock(MSK) == (1, 1)
    assert await inv.stock(KZN) == (1, 1)


async def test_last_copy_stays_on_venue() -> None:
    only = await inv.copy()
    with pytest.raises(DomainError, match="хотя бы один"):
        await inv.transfer(only)


async def test_one_open_transfer_per_copy() -> None:
    moving, _ = await inv.copies(2)
    await inv.transfer(moving)
    with pytest.raises(DomainError, match="незавершённое"):
        await inv.transfer(moving, to=TVR)
    async with db.sessionmaker().begin() as s:
        s.add(
            Transfer(
                copy_id=moving,
                from_venue_id=MSK,
                to_venue_id=TVR,
                status="requested",
                requested_by=inv.KEEPER[MSK],
                requested_at=T0,
            )
        )
        with pytest.raises(DBAPIError, match="uq_transfers_one_open"):
            await s.flush()


async def test_transfer_must_start_where_copy_is() -> None:
    copy_id = await inv.copy()
    async with db.sessionmaker().begin() as s:
        s.add(
            Transfer(
                copy_id=copy_id,
                from_venue_id=KZN,
                to_venue_id=TVR,
                status="requested",
                requested_by=inv.KEEPER[KZN],
                requested_at=T0,
            )
        )
        with pytest.raises(DBAPIError, match="is not at venue"):
            await s.flush()


async def test_loaned_copy_cannot_be_transferred() -> None:
    loaned, _ = await inv.copies(2)
    partner_id = await inv.partner()
    await inv.lend(loaned, partner_id)
    with pytest.raises(DomainError, match="выдан"):
        await inv.transfer(loaned)


async def test_loaned_copy_cannot_change_venue_even_on_reconciliation() -> None:
    loaned = await inv.copy()
    await inv.lend(loaned, await inv.partner())
    with pytest.raises(DBAPIError, match="on loan"):
        await act(inventory.reconcile_venue, loaned, KZN, inv.KEEPER[KZN])
    assert (await inv.get(Copy, loaned)).venue_id == MSK


async def test_cancel_in_transit_returns_copy_to_shelf() -> None:
    moving, _ = await inv.copies(2)
    transfer_id = await inv.transfer(moving)
    await act(inventory.ship_transfer, transfer_id, inv.KEEPER[MSK])
    with pytest.raises(AccessDenied):
        await act(inventory.cancel_transfer, transfer_id, inv.KEEPER[TVR], reason="ошибка")
    await act(inventory.cancel_transfer, transfer_id, inv.KEEPER[KZN], reason="не дошло")
    assert await inv.state(moving) == "available"
    assert await inv.stock(MSK) == (2, 2)
    # после отмены можно оформить новое перемещение
    await inv.transfer(moving, to=TVR)


async def test_stale_requests_expire() -> None:
    first, second, _ = await inv.copies(3)
    stale = await inv.transfer(first)
    travel(T0 + timedelta(days=10))
    fresh = await inv.transfer(second)
    expired = await act(jobs.expire_stale_transfers, now=T0 + timedelta(days=15))
    assert expired == [stale]
    assert (await inv.get(Transfer, stale)).cancel_reason == "expired"
    assert (await inv.get(Transfer, fresh)).status == "requested"
