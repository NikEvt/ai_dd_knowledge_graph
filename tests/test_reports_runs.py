from datetime import timedelta

import pytest

from libs.errors import AccessDenied, DomainError
from services.reports import service, settings
from tests.factories import T0, act, travel
from tests.reports_factories import (
    ANALYST,
    ANALYST_2,
    DIRECTOR,
    FINES,
    LOANS,
    definition,
    inbox,
    load_run,
    load_schedule,
    run,
    run_pending,
    schedule,
    series,
    snapshot,
)


async def test_summary_run_is_built_and_requester_notified() -> None:
    await series(LOANS, [10, 12, 8, 20])
    await snapshot(LOANS, 99, days_ago=10)  # за пределами недельного периода
    def_id = await definition(params={"metrics": [LOANS, FINES]})

    run_id = await run(def_id)

    r = await load_run(run_id)
    assert r.status == "completed"
    assert r.started_at == r.finished_at == T0
    assert r.body["period"] == {"from": "2026-02-24", "to": "2026-03-02"}
    assert r.body["metrics"][LOANS] == {
        "points": 4,
        "total": "50.00",
        "avg": "12.50",
        "min": "8.00",
        "max": "20.00",
    }
    assert r.body["metrics"][FINES] == {"points": 0}
    [note] = await inbox(ANALYST)
    assert note.kind == "completed"
    assert note.body == f"Отчёт «Отчёт loans-weekly» готов (запуск №{run_id})"


async def test_trend_respects_dimension_and_as_of() -> None:
    await series(LOANS, [5, 7, 4], dimension="msk")
    await series(LOANS, [100, 100, 100], dimension="kzn")
    def_id = await definition("loans-trend", kind="metric_trend", params={"metric": LOANS, "days": 2})

    run_id = await run(def_id, params={"dimension": "msk", "as_of": "2026-03-01"})

    body = (await load_run(run_id)).body
    assert body["period"] == {"from": "2026-02-28", "to": "2026-03-01"}
    assert body["series"] == [{"day": "2026-02-28", "value": "5.00"}, {"day": "2026-03-01", "value": "7.00"}]
    assert body["change"] == "2.00"


async def test_run_without_data_fails_and_owner_is_told() -> None:
    def_id = await definition("loans-trend", kind="metric_trend")

    run_id = await run(def_id, by=ANALYST_2)

    r = await load_run(run_id)
    assert r.status == "failed"
    assert r.body is None
    assert r.error == f"за период нет снимков метрики {LOANS}"
    for employee in (ANALYST, ANALYST_2):
        [note] = await inbox(employee)
        assert note.kind == "failed" and note.run_id == run_id


async def test_completed_runs_feed_audit_report() -> None:
    await series(LOANS, [1])
    weekly = await definition("loans-weekly")
    audit = await definition("runs-audit", kind="run_audit", params={"days": 1})
    trend = await definition("fines-trend", kind="metric_trend", params={"metric": FINES})
    await run(weekly)
    await run(trend)  # без данных — неуспешный

    # Служебная метрика копится подписчиком на reports.run_completed
    counter = await definition(
        "runs-counter", params={"metrics": [settings.RUNS_COMPLETED_METRIC], "dimension": "loans-weekly"}
    )
    travel(T0 + timedelta(hours=1))
    await run(weekly)
    counted = (await load_run(await run(counter))).body["metrics"][settings.RUNS_COMPLETED_METRIC]
    assert counted["total"] == "2.00"

    body = (await load_run(await run(audit))).body
    assert body["by_status"] == {"completed": 3, "failed": 1}
    assert body["by_report"] == {"fines-trend": 1, "loans-weekly": 2, "runs-counter": 1}
    assert body["total"] == 4


async def test_pending_run_cancelled_only_by_requester() -> None:
    def_id = await definition()
    run_id = await run_pending(def_id)

    with pytest.raises(AccessDenied):
        await act(service.cancel_run, run_id, ANALYST_2)
    await act(service.cancel_run, run_id, ANALYST)

    r = await load_run(run_id)
    assert r.status == "cancelled" and r.finished_at == T0
    assert await inbox(ANALYST) == []
    with pytest.raises(DomainError, match="ещё не начал строиться"):
        await act(service.cancel_run, run_id, ANALYST)


async def test_pending_runs_limited_per_employee() -> None:
    ids = [await definition(f"report-{n}") for n in range(settings.MAX_PENDING_RUNS_PER_USER + 1)]
    await run_pending(ids[0])
    with pytest.raises(DomainError, match="уже есть незавершённый запуск"):
        await run_pending(ids[0])
    for def_id in ids[1:-1]:
        await run_pending(def_id)
    with pytest.raises(DomainError, match="не больше 3 незавершённых"):
        await run_pending(ids[-1])
    # Другому сотруднику лимит не мешает
    await run_pending(ids[-1], by=ANALYST_2)


async def test_deactivation_cancels_pending_runs_and_schedules() -> None:
    await series(LOANS, [3])
    def_id = await definition()
    done = await run(def_id)
    pending = await run_pending(def_id, by=DIRECTOR)
    schedule_id = await schedule(def_id)

    await act(service.deactivate_definition, def_id, ANALYST)

    assert (await load_run(done)).status == "completed"
    assert (await load_run(pending)).status == "cancelled"
    [note] = await inbox(DIRECTOR)
    assert note.kind == "cancelled" and "отчёт отключён" in note.body
    assert not (await load_schedule(schedule_id)).is_active
    with pytest.raises(DomainError, match="отключён"):
        await run(def_id)


async def test_redelivered_request_does_not_rebuild() -> None:
    await series(LOANS, [3])
    def_id = await definition()
    run_id = await run(def_id)
    travel(T0 + timedelta(hours=2))

    again = await act(service.build_run, run_id)

    assert again.finished_at == T0
    assert len(await inbox(ANALYST)) == 1
