import pytest
from sqlalchemy.exc import DBAPIError

from libs.errors import AccessDenied, DomainError
from services.reports import service
from tests.factories import act, read
from tests.reports_factories import ANALYST, ANALYST_2, FINES, LOANS, definition, run


async def test_summary_definition_keeps_metrics_unique_and_ordered() -> None:
    def_id = await definition(params={"metrics": [LOANS, FINES, LOANS], "days": 14})
    d = await read(service.get_definition, def_id)
    assert d.params == {"metrics": [LOANS, FINES], "days": 14}
    assert d.is_active


@pytest.mark.parametrize(
    ("kind", "params", "message"),
    [
        ("pivot", {}, "неизвестный тип"),
        ("metric_summary", {"metrics": ["Loans Issued"]}, "некорректное имя метрики"),
        ("metric_trend", {"metric": LOANS, "days": 365}, "от 1 до 90 дней"),
    ],
)
async def test_definition_params_are_validated(kind: str, params: dict, message: str) -> None:
    with pytest.raises(DomainError, match=message):
        await definition(kind=kind, params=params)


async def test_code_unique_and_title_unique_per_owner() -> None:
    await definition("loans-weekly", title="Выдачи за неделю")
    with pytest.raises(DomainError, match="уже занят"):
        await definition("loans-weekly", title="Другое название")
    with pytest.raises(DomainError, match="уже есть действующий отчёт"):
        await definition("loans-weekly-2", title="выдачи за неделю")
    # У другого сотрудника такое же название допустимо
    await definition("loans-weekly-3", title="Выдачи за неделю", owner=ANALYST_2)


async def test_title_released_after_deactivation() -> None:
    def_id = await definition("loans-weekly", title="Выдачи")
    await act(service.deactivate_definition, def_id, ANALYST)
    await definition("loans-weekly-v2", title="Выдачи")


async def test_only_owner_changes_definition() -> None:
    def_id = await definition()
    with pytest.raises(AccessDenied, match="владелец"):
        await act(service.update_definition, def_id, ANALYST_2, title="Чужой")
    with pytest.raises(AccessDenied):
        await act(service.deactivate_definition, def_id, ANALYST_2)
    updated = await act(service.update_definition, def_id, ANALYST, params={"metrics": [FINES]})
    assert updated.params == {"metrics": [FINES]}


async def test_kind_locked_once_report_was_run() -> None:
    def_id = await definition()
    changed = await act(
        service.update_definition, def_id, ANALYST, kind="metric_trend", params={"metric": LOANS}
    )
    assert changed.kind == "metric_trend"

    await run(def_id)
    with pytest.raises(DBAPIError, match="тип менять нельзя"):
        await act(service.update_definition, def_id, ANALYST, kind="run_audit", params={})
    assert (await read(service.get_definition, def_id)).kind == "metric_trend"


async def test_run_may_override_only_period_and_dimension() -> None:
    def_id = await definition()
    with pytest.raises(DomainError, match="нельзя менять параметры: metrics"):
        await run(def_id, params={"metrics": [FINES]})
    with pytest.raises(DomainError, match="ГГГГ-ММ-ДД"):
        await run(def_id, params={"as_of": "02.03.2026"})
