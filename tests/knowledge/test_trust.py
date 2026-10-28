"""Тесты профиля достоверности правил (tools/knowledge/trust.py)."""

import pytest

from tools.knowledge import graph, trust

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

NODES = {"svc.py::f": {"id": "svc.py::f", "type": "symbol", "hash": "c1"}}


def _rule(**extra) -> dict:
    return {
        "id": "R-X-01",
        "title": "t",
        "text": "x",
        "status": "draft",
        "implemented_by": [{"symbol": "svc.py::f", "hash": "c1"}],
        "tested_by": ["tests/t.py::test"],
        "schema_ref": "§9 Виды заявок",
        **extra,
    }


def _profile(rule: dict, discrepancies: list | None = None) -> dict:
    return trust.profile(rule, NODES, discrepancies or [])


def test_levels() -> None:
    assert _profile(_rule())["level"] == "supported"
    assert _profile(_rule(tested_by=[]))["level"] == "weak"
    assert _profile(_rule(implemented_by=[]))["level"] == "unanchored"
    changed = _profile(_rule(implemented_by=[{"symbol": "svc.py::f", "hash": "old"}]))
    assert changed["level"] == "stale" and changed["freshness"] == "code_changed"
    assert _profile(_rule(discrepancy="код делает иначе"))["level"] == "contested"
    opened = [{"id": "D-01", "status": "open", "rules": ["R-X-01"]}]
    assert _profile(_rule(), opened)["level"] == "contested"
    resolved = [{"id": "D-01", "status": "resolved", "rules": ["R-X-01"]}]
    assert _profile(_rule(), resolved)["level"] == "supported"


def test_schema_axis() -> None:
    assert _profile(_rule())["schema"] == "described"
    assert _profile(_rule())["schema_sections"] == ["§9"]
    assert _profile(_rule(schema_ref=None))["schema"] == "undescribed"
    deviates = _profile(_rule(discrepancy="иначе"))
    assert deviates["schema"] == "deviates" and deviates["ambiguity"]["deviation"] == "иначе"
    # discrepancy без ссылки на схему — оговорка о коде, уровень не понижает
    caveat = _profile(_rule(schema_ref=None, discrepancy="литерал вместо настройки"))
    assert caveat["level"] == "supported" and caveat["ambiguity"]["caveats"] == ["литерал вместо настройки"]


def test_verification_is_bound_to_the_checked_version() -> None:
    rule = _rule(status="verified", verified_by="Иванов", verified_at="2026-10-28")
    rule["verified_fingerprint"] = trust.fingerprint(rule)
    assert _profile(rule)["level"] == "confirmed"
    edited = _profile({**rule, "text": "агент переписал правило"})
    assert edited["level"] == "stale" and edited["freshness"] == "verified_outdated"
    # хэши ссылок входят в отпечаток: drift --write обновил хэш кода — проверка тоже устарела
    rehashed = {**rule, "implemented_by": [{"symbol": "svc.py::f", "hash": "c2"}]}
    assert trust.fingerprint(rehashed) != rule["verified_fingerprint"]


def test_phrases_have_no_codes_and_say_what_to_do() -> None:
    weak = _rule(tested_by=[])
    full = trust.describe({**weak, "trust": _profile(weak)})
    assert "описано в бизнес-схеме §9" in full and "сверь с кодом" in full
    assert "weak" not in full and "draft" not in full
    deviating = _rule(discrepancy="иначе")
    assert "уточни у пользователя" in trust.describe({**deviating, "trust": _profile(deviating)}, "compact")


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


def test_rule_card_has_why_how_trust_where(g: graph.Graph) -> None:
    card = graph.rule_card(g, "R-APP-CREATE-01").text
    for section in ("## Почему (бизнес-схема)", "## Как (правило)", "## Достоверность", "## Где"):
        assert section in card
    assert "§9" in card


def test_impact_marks_rules_without_status_codes(g: graph.Graph) -> None:
    answer = graph.impact(g, "services/applications/service.py::change_venue")
    assert "[draft]" not in answer.text and "## Пометки" in answer.text


def test_who_can_marks_role_guess(g: graph.Graph) -> None:
    text = graph.who_can(g, "сменить площадку заявки").text
    assert "предположение по имени параметра" in text
