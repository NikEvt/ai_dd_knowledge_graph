import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.inventory import service as inventory
from services.inventory.models import Copy, WriteOff
from tests import inventory_factories as inv
from tests.factories import BOOK_H2, KZN, MSK, act


@pytest.fixture(autouse=True)
async def custodians(world: None) -> None:
    await inv.staff()


async def _write_off(copy_id: int) -> WriteOff | None:
    async with db.sessionmaker()() as s:
        return await s.scalar(select(WriteOff).where(WriteOff.copy_id == copy_id))


async def test_registered_copies_counted_in_stock() -> None:
    await inv.copies(3)
    await inv.copy(KZN)
    assert await inv.stock(MSK) == (3, 3)
    assert await inv.stock(KZN) == (1, 1)
    assert await inv.stock(MSK, BOOK_H2) == (0, 0)


async def test_inventory_number_is_normalized_and_unique() -> None:
    copy_id = await inv.copy(inventory_no=" ab-00017 ")
    assert (await inv.get(Copy, copy_id)).inventory_no == "AB-00017"
    with pytest.raises(DomainError, match="уже занят"):
        await inv.copy(KZN, inventory_no="AB-00017")
    with pytest.raises(DomainError, match="ШИФР"):
        await inv.copy(inventory_no="17")


async def test_lost_copy_is_written_off_and_leaves_stock() -> None:
    lost, _ = await inv.copies(2)
    await act(inventory.mark_lost, lost, inv.KEEPER[MSK], "не найден при инвентаризации")
    assert await inv.state(lost) == "written_off"
    act_ = await _write_off(lost)
    assert act_.reason == "lost"
    assert act_.created_by == inv.KEEPER[MSK]
    assert act_.act_no == f"СП-2026-{lost:06d}"
    assert await inv.stock() == (1, 1)


async def test_damaged_copy_is_written_off() -> None:
    copy_id = await inv.copy()
    await act(inventory.mark_damaged, copy_id, inv.KEEPER[MSK], "залит водой")
    assert (await _write_off(copy_id)).reason == "damaged"
    assert await inv.stock() == (0, 0)


async def test_worn_out_write_off_by_custodian_only() -> None:
    copy_id = await inv.copy()
    with pytest.raises(AccessDenied):
        await act(inventory.write_off_worn, copy_id, inv.OUTSIDER)
    await act(inventory.write_off_worn, copy_id, inv.KEEPER[MSK], "ветхость")
    assert (await _write_off(copy_id)).reason == "worn_out"
    with pytest.raises(DomainError, match="выбыл"):
        await act(inventory.mark_lost, copy_id, inv.KEEPER[MSK])


async def test_written_off_copy_cannot_be_changed() -> None:
    copy_id = await inv.copy()
    await act(inventory.write_off_worn, copy_id, inv.KEEPER[MSK])
    async with db.sessionmaker().begin() as s:
        with pytest.raises(DBAPIError, match="written off"):
            await s.execute(update(Copy).where(Copy.id == copy_id).values(state="available"))


async def test_state_is_constrained() -> None:
    copy_id = await inv.copy()
    async with db.sessionmaker().begin() as s:
        with pytest.raises(DBAPIError, match="copies_state_check"):
            await s.execute(update(Copy).where(Copy.id == copy_id).values(state="stolen"))
