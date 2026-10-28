"""Тесты требований и профиля достоверности (tools/knowledge/requirements.py, trust.py)."""

import textwrap
from pathlib import Path

import pytest

from tools.knowledge import graph, requirements, trust

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

CODE = {"svc.py::f": {"id": "svc.py::f", "type": "symbol", "hash": "c1"}}
REQ = {"REQ-X-01": {"id": "REQ-X-01", "type": "requirement", "hash": "r1", "status": "approved"}}


def _rule(**extra) -> dict:
    return {
        "id": "R-X-01",
        "title": "t",
        "text": "x",
        "status": "draft",
        "implemented_by": [{"symbol": "svc.py::f", "hash": "c1"}],
        "tested_by": ["tests/t.py::test"],
        "satisfies": [{"requirement": "REQ-X-01", "hash": "r1"}],
        **extra,
    }


def _level(rule: dict, discrepancies: list | None = None) -> str:
    return trust.profile(rule, {**CODE, **REQ}, discrepancies or [])["level"]


def test_requirements_parse_meta_text_and_errors(tmp_path: Path) -> None:
    path = tmp_path / "x.md"
    path.write_text(
        textwrap.dedent(
            """\
            # Требования

            ## REQ-X-01 Заголовок
            владелец: продукт · статус: утверждено · схема: §9

            Первая строка
            вторая строка.

            ## REQ-bad Плохой
            владелец: продукт · статус: черновик
            """
        ),
        encoding="utf-8",
    )
    reqs, errors = requirements.parse(path)
    assert reqs[0]["status"] == "approved" and reqs[0]["schema"] == "§9"
    assert reqs[0]["text"] == "Первая строка вторая строка."
    assert any("неверный ID" in e for e in errors)
    assert any("статус 'черновик'" in e for e in errors)
    assert any("пустой текст" in e for e in errors)


def test_requirement_hash_ignores_formatting_only() -> None:
    a = requirements.requirement_hash("T", "один  два\nтри")
    assert a == requirements.requirement_hash("T", "один два три")
    assert a != requirements.requirement_hash("T", "один два четыре")


def test_levels() -> None:
    assert _level(_rule()) == "supported"
    assert _level(_rule(tested_by=[])) == "weak"
    assert _level(_rule(implemented_by=[])) == "unanchored"
    changed_code = _rule(implemented_by=[{"symbol": "svc.py::f", "hash": "old"}])
    assert _level(changed_code) == "stale"
    changed_req = _rule(satisfies=[{"requirement": "REQ-X-01", "hash": "old"}])
    profile = trust.profile(changed_req, {**CODE, **REQ}, [])
    assert profile["level"] == "stale" and profile["freshness"] == "requirement_changed"
    deviating = _rule(satisfies=[], deviates_from=[{"requirement": "REQ-X-01", "note": "иначе"}])
    assert _level(deviating) == "contested"
    assert _level(_rule(), [{"id": "D-01", "status": "open", "rules": ["R-X-01"]}]) == "contested"
    assert _level(_rule(), [{"id": "D-01", "status": "resolved", "rules": ["R-X-01"]}]) == "supported"


def test_verification_is_bound_to_the_checked_version() -> None:
    rule = _rule(status="verified", verified_by="Иванов", verified_at="2026-10-28")
    rule["verified_fingerprint"] = trust.fingerprint(rule)
    assert _level(rule) == "confirmed"
    edited = {**rule, "text": "агент переписал правило"}
    profile = trust.profile(edited, {**CODE, **REQ}, [])
    assert profile["level"] == "stale" and profile["freshness"] == "verified_outdated"
    # хэши ссылок входят в отпечаток: drift --write обновил хэш кода — проверка тоже устарела
    rehashed = {**rule, "implemented_by": [{"symbol": "svc.py::f", "hash": "c2"}]}
    assert trust.fingerprint(rehashed) != rule["verified_fingerprint"]


def test_phrases_have_no_codes_and_say_what_to_do() -> None:
    node = {**_rule(tested_by=[]), "trust": trust.profile(_rule(tested_by=[]), {**CODE, **REQ}, [])}
    full = trust.describe(node)
    assert "реализует требование REQ-X-01" in full and "сверь с кодом" in full
    assert "weak" not in full and "draft" not in full
    deviating = _rule(satisfies=[], deviates_from=[{"requirement": "REQ-X-01", "note": "иначе"}])
    node = {**deviating, "trust": trust.profile(deviating, {**CODE, **REQ}, [])}
    assert "уточни у пользователя" in trust.describe(node, "compact")


def test_edge_notes() -> None:
    assert trust.edge_note({"method": "ast"}) == ""
    assert trust.edge_note({"method": "llm"}) == ""
    assert trust.edge_note({"method": "human"}) == "проверено человеком"
    assert trust.edge_note({"method": "heuristic", "inferred": "литерал 30"}) == "предположение: литерал 30"


@pytest.fixture(scope="module")
def g(tmp_path_factory: pytest.TempPathFactory) -> graph.Graph:
    path = tmp_path_factory.mktemp("index") / "index.sqlite"
    graph.build(path)
    return graph.Graph.load(path, rebuild_if_stale=False)


def test_graph_has_requirements_and_trust(g: graph.Graph) -> None:
    rule = g.nodes["R-APP-CREATE-01"]
    assert rule["trust"]["requirements"] == ["REQ-KIND-01"]
    card = graph.rule_card(g, "R-APP-CREATE-01").text
    assert "## Почему (бизнес-требования)" in card and "REQ-KIND-01" in card
    assert "## Достоверность" in card
    req = graph.requirement_card(g, "REQ-KIND-01")
    assert "R-APP-CREATE-01" in req.nodes
    assert "не реализовано" in graph.requirement_card(g, "REQ-PROC-06").text


def test_impact_from_requirement_reaches_code(g: graph.Graph) -> None:
    answer = graph.impact(g, "REQ-VENUE-03")
    assert "R-APP-VENUE-CHANGE-01" in answer.nodes
    assert "services/applications/service.py::change_venue" in answer.nodes
    assert "[draft]" not in answer.text


def test_who_can_marks_role_guess(g: graph.Graph) -> None:
    text = graph.who_can(g, "сменить площадку заявки").text
    assert "предположение по имени параметра" in text
