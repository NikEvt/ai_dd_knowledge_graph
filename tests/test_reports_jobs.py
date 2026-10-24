from datetime import timedelta

import pytest

from libs.errors import DomainError
from services.reports import jobs, settings
from tests.factories import T0, travel
from tests.reports_factories import (
    ANALYST,
    DIRECTOR,
    LOANS,
    MANAGER,
    definition,
    inbox,
    job,
    load_run,
    load_schedule,
    run,
    run_pending,
    schedule,
    series,
    sql,
)


async def test_due_schedule_runs_and_notifies_recipients() -> None:
    await series(LOANS, [4, 6])
    def_id = await definition()
    schedule_id = await schedule(def_id, recipients=(MANAGER, DIRECTOR, MANAGER))

    [run_id] = await job(jobs.run_scheduled, T0)

    r = await load_run(run_id)
    assert r.status == "completed"
    assert r.schedule_id == schedule_id and r.scheduled_for == T0
    assert r.body["metrics"][LOANS]["total"] == "10.00"
    for employee in (ANALYST, MANAGER, DIRECTOR):
        assert [n.run_id for n in await inbox(employee)] == [run_id]
    s = await load_schedule(schedule_id)
    assert s.next_run_at == T0 + timedelta(hours=24)
    assert s.last_enqueued_at == T0


async def test_schedule_not_due_and_not_repeated() -> None:
    await series(LOANS, [1])
    def_id = await definition()
    await schedule(def_id, every_hours=6, first_run_at=T0 + timedelta(hours=1))

    assert await job(jobs.run_scheduled, T0) == []
    assert len(await job(jobs.run_scheduled, T0 + timedelta(hours=1))) == 1
    assert await job(jobs.run_scheduled, T0 + timedelta(hours=2)) == []


async def test_missed_intervals_are_not_caught_up() -> None:
    await series(LOANS, [1])
    def_id = await definition()
    schedule_id = await schedule(def_id, every_hours=24)
    # Плановый запуск не мешает ручному и не упирается в лимит
    await run_pending(def_id)

    later = T0 + timedelta(days=3, hours=5)
    travel(later)
    run_ids = await job(jobs.run_scheduled, later)

    assert len(run_ids) == 1
    assert (await load_run(run_ids[0])).scheduled_for == T0
    assert (await load_schedule(schedule_id)).next_run_at == T0 + timedelta(days=4)


async def test_schedule_validation() -> None:
    def_id = await definition()
    with pytest.raises(DomainError, match="от 1 до 744 часов"):
        await schedule(def_id, every_hours=0)
    with pytest.raises(DomainError, match="хотя бы один получатель"):
        await schedule(def_id, recipients=())
    with pytest.raises(DomainError, match="в прошлом"):
        await schedule(def_id, first_run_at=T0 - timedelta(minutes=1))
    await schedule(def_id)
    with pytest.raises(DomainError, match="уже есть действующее расписание"):
        await schedule(def_id)


async def test_purge_removes_only_finished_runs_past_retention() -> None:
    await series(LOANS, [1])
    def_id = await definition(params={"metrics": [LOANS], "days": settings.MAX_PERIOD_DAYS})
    old = await run(def_id)
    stale_pending = await run_pending(await definition("other"))
    travel(T0 + timedelta(days=settings.RETENTION_DAYS - 1))
    fresh = await run(def_id)

    removed = await job(jobs.purge_old_runs, T0 + timedelta(days=settings.RETENTION_DAYS, minutes=1))

    assert removed == 1
    assert [n.run_id for n in await inbox(ANALYST)] == [fresh]
    assert (await load_run(stale_pending)).status == "requested"
    assert (await load_run(fresh)).status == "completed"
    with pytest.raises(Exception, match=f"запуск {old}"):
        await load_run(old)


async def test_stuck_run_marked_failed_and_owner_told() -> None:
    def_id = await definition()
    run_id = await run_pending(def_id)
    await sql(f"UPDATE reports.report_runs SET status = 'running', started_at = now() WHERE id = {run_id}")
    started = (await load_run(run_id)).started_at

    timeout = timedelta(minutes=settings.RUN_TIMEOUT_MINUTES)
    assert await job(jobs.fail_stuck_runs, started + timeout - timedelta(seconds=1)) == []
    assert await job(jobs.fail_stuck_runs, started + timeout + timedelta(seconds=1)) == [run_id]

    r = await load_run(run_id)
    assert r.status == "failed" and "время построения" in r.error
    [note] = await inbox(ANALYST)
    assert note.kind == "failed"
