"""T07: при изменении максимума мест площадки будущие окна со старым максимумом получают новый."""

from datetime import timedelta

from support import CHECKER, HISTORY, MSK, T0, act, slot, travel

from libs import db
from services.applications import admin
from services.scheduling import service as scheduling
from services.scheduling.models import Slot


async def _capacity(slot_id: int) -> int:
    async with db.sessionmaker()() as s:
        return (await s.get(Slot, slot_id)).capacity


async def test_t07_raise_max_updates_default_future_slots() -> None:
    past = await slot(MSK, HISTORY, T0 + timedelta(days=1))
    default = await slot(MSK, HISTORY, T0 + timedelta(days=5))
    reduced = await slot(MSK, HISTORY, T0 + timedelta(days=6))
    await act(scheduling.reduce_capacity, reduced, CHECKER[MSK], 1)
    travel(T0 + timedelta(days=2))

    await act(admin.set_venue_max_capacity, MSK, 5)

    assert await _capacity(default) == 5
    assert await _capacity(reduced) == 1
    assert await _capacity(past) == 3


async def test_t07_new_slots_get_new_max() -> None:
    await act(admin.set_venue_max_capacity, MSK, 4)
    assert await _capacity(await slot(MSK, HISTORY, T0 + timedelta(days=5))) == 4
