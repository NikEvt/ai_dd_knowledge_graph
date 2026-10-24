import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from services.reports import service
from tests.factories import T0, read
from tests.reports_factories import (
    LOANS,
    definition,
    load_run,
    run,
    run_pending,
    schedule,
    series,
    snapshot,
    sql,
)


async def test_finished_run_cannot_be_rewritten() -> None:
    await series(LOANS, [2])
    run_id = await run(await definition())

    with pytest.raises(DBAPIError, match="уже завершён"):
        await sql(f"UPDATE reports.report_runs SET body = '{{}}'::jsonb WHERE id = {run_id}")
    assert (await load_run(run_id)).body["metrics"][LOANS]["total"] == "2.00"


async def test_run_status_rules_enforced_in_db() -> None:
    run_id = await run_pending(await definition())

    with pytest.raises(DBAPIError, match="недопустимый переход запуска"):
        await sql(
            f"UPDATE reports.report_runs SET status = 'completed', body = '{{}}', finished_at = now() "
            f"WHERE id = {run_id}"
        )
    with pytest.raises(IntegrityError, match="report_runs_status"):
        await sql(
            "INSERT INTO reports.report_runs (definition_id, status, requested_by, requested_at) "
            "SELECT definition_id, 'done', requested_by, requested_at FROM reports.report_runs "
            f"WHERE id = {run_id}"
        )
    with pytest.raises(IntegrityError, match="report_runs_body_on_completion"):
        await sql(f"UPDATE reports.report_runs SET status = 'running', body = '{{}}' WHERE id = {run_id}")


async def test_snapshot_rewrite_and_single_active_schedule() -> None:
    await snapshot(LOANS, 5)
    await snapshot(LOANS, 7)
    def_id = await definition(params={"metrics": [LOANS], "days": 1})
    body = (await load_run(await run(def_id))).body
    assert body["metrics"][LOANS] == {
        "points": 1,
        "total": "7.00",
        "avg": "7.00",
        "min": "7.00",
        "max": "7.00",
    }
    assert body["period"] == {"from": T0.date().isoformat(), "to": T0.date().isoformat()}

    await schedule(def_id)
    with pytest.raises(IntegrityError, match="export_schedules_one_active"):
        await sql(
            "INSERT INTO reports.export_schedules "
            "(definition_id, every_hours, next_run_at, created_by, created_at) "
            f"VALUES ({def_id}, 1, now(), 1, now())"
        )
    assert (await read(service.get_definition, def_id)).is_active
