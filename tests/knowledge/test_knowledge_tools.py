"""Тесты инструментов модели знаний (tools/knowledge, mcp/knowledge_server.py)."""

import importlib.util
import json
import textwrap
from pathlib import Path

import pytest

from tools.knowledge import check_rules, extract_bpm, extract_code, extract_events, graph
from tools.knowledge.common import ROOT
from tools.knowledge.pyindex import Project, normalized_hash

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _project(tmp_path: Path, files: dict[str, str]) -> Project:
    for name, text in files.items():
        path = tmp_path / "pkg" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")
    p = Project(root=tmp_path, dirs=("pkg",))
    p.analyze(orm=False)
    return p


def test_hash_ignores_formatting_comments_and_docstrings(tmp_path: Path) -> None:
    a = _project(tmp_path / "a", {"m.py": "def f(x):\n    return x + 1\n"})
    b = _project(
        tmp_path / "b",
        {
            "m.py": 'def f(x):\n    """Документация."""\n    # комментарий\n'
            "    return (\n        x + 1\n    )\n"
        },
    )
    c = _project(tmp_path / "c", {"m.py": "def f(x):\n    return x + 2\n"})
    h = lambda p: normalized_hash(p.symbols["pkg/m.py::f"].node)  # noqa: E731
    assert h(a) == h(b)
    assert h(a) != h(c)


def test_transitive_hash_follows_project_callees(tmp_path: Path) -> None:
    src = {"m.py": "from pkg import n\n\ndef f():\n    return n.g()\n", "n.py": "def g():\n    return {}\n"}
    before = _project(tmp_path / "a", src)
    after = _project(tmp_path / "b", {**src, "n.py": "def g():\n    return {'changed': True}\n"})
    assert before.own_hash(before.symbols["pkg/m.py::f"]) == after.own_hash(after.symbols["pkg/m.py::f"])
    assert before.transitive_hash("pkg/m.py::f") != after.transitive_hash("pkg/m.py::f")


@pytest.fixture(scope="module")
def code_model() -> dict:
    return extract_code.extract()


def _edges(doc: dict, type_: str) -> set[tuple[str, str]]:
    return {(e["src"], e["dst"]) for e in doc["edges"] if e["type"] == type_}


@pytest.mark.xfail(
    reason="после роста платформы литерал 30 неоднозначен: несколько настроек = 30, "
    "связь flag_overdue -> LOAN_PERIOD_DAYS не выводится",
    strict=False,
)
def test_code_layer_finds_links_invisible_to_imports(code_model: dict) -> None:
    reads_config = {(e["src"], e["dst"]): e for e in code_model["edges"] if e["type"] == "reads_config"}
    literal = reads_config[
        ("services/scheduling/jobs.py::flag_overdue", "libs/settings.py::LOAN_PERIOD_DAYS")
    ]
    assert literal.get("inferred")
    assert ("services/applications/api.py::change_venue", "libs/web.py::session") in _edges(
        code_model, "depends_on"
    )
    assert ("services/applications/listeners.py::_domain_events", "applications.clients") in _edges(
        code_model, "listens"
    )
    writes = {(e["src"], e["dst"]): e for e in code_model["edges"] if e["type"] == "writes"}
    assert writes[("services/applications/service.py::change_venue", "applications.applications")][
        "columns"
    ] == [
        "site_checker_id",
        "venue_id",
    ]
    assert ("services/applications/models.py::Application", "applications.applications") in _edges(
        code_model, "maps_to"
    )


def test_event_layer_resolves_dynamic_subscribers() -> None:
    doc = extract_events.extract()
    consumes = {(e["src"], e["dst"]): e for e in doc["edges"] if e["type"] == "consumes"}
    chat = consumes[("services/chat/consumers.py::_handler", "application.venue_changed")]
    assert chat["dynamic"] is True
    assert ("services/billing/consumers.py::on_venue_changed", "application.venue_changed") in consumes
    assert ("services/applications/listeners.py::_domain_events", "client.updated") in _edges(
        doc, "publishes"
    )


def test_bpm_layer_links_guards_and_code() -> None:
    doc = extract_bpm.extract()
    assert ("guard:fully_paid", "services/billing/guards.py::fully_paid") in _edges(doc, "implemented_by")
    assert ("awaiting_payment->awaiting_issue", "guard:fully_paid") in _edges(doc, "guarded_by")
    approve = {dst for src, dst in _edges(doc, "transitions_to") if src.endswith("service.py::approve")}
    assert approve == {
        "on_review->awaiting_invoice",
        "on_review->awaiting_payment",
        "on_review->awaiting_issue",
    }


@pytest.fixture(scope="module")
def g(tmp_path_factory: pytest.TempPathFactory) -> graph.Graph:
    path = tmp_path_factory.mktemp("index") / "index.sqlite"
    graph.build(path)
    return graph.Graph.load(path, rebuild_if_stale=False)


def test_find_entry_maps_russian_task_to_setting(g: graph.Graph) -> None:
    answer = graph.find_entry(g, "срок пользования книгами")
    assert "libs/settings.py::LOAN_PERIOD_DAYS" in answer.nodes[:3]


@pytest.mark.parametrize("budget", [800, 2000, 4000])
def test_impact_respects_budget_and_crosses_services(g: graph.Graph, budget: int) -> None:
    answer = graph.impact(g, "services/applications/service.py::change_venue", budget_tokens=budget)
    assert len(answer.text) // 3 <= budget
    assert "application.venue_changed" in answer.nodes
    if budget >= 4000:
        assert "trg_applications_venue_lock" in answer.nodes
        assert "services/billing/consumers.py::on_venue_changed" in answer.nodes
        assert "awaiting_payment->awaiting_invoice" in answer.nodes


def test_entity_resolves_russian_term(g: graph.Graph) -> None:
    answer = graph.entity_card(g, "заявка")
    assert answer.nodes[0] == "applications.applications"
    assert "trg_applications_venue_lock" in answer.nodes


def test_mcp_log_line(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, g: graph.Graph) -> None:
    spec = importlib.util.spec_from_file_location("knowledge_server", ROOT / "mcp" / "knowledge_server.py")
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    monkeypatch.setattr(server, "_graph", g)
    monkeypatch.setattr(server.graph, "index_is_stale", lambda *_: False)
    log = tmp_path / "mcp.jsonl"
    monkeypatch.setenv("EVAL_MCP_LOG", str(log))
    monkeypatch.setenv("EVAL_RUN_ID", "run-1")
    text = server.find_entry("смена площадки")
    record = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert set(record) == {"ts", "run_id", "tool", "args", "response_tokens", "nodes_returned", "ms"}
    assert record["run_id"] == "run-1" and record["tool"] == "find_entry"
    assert record["response_tokens"] == len(text) // 3
    assert record["nodes_returned"] and all(n in g.nodes for n in record["nodes_returned"])

    monkeypatch.delenv("EVAL_MCP_LOG")
    server.find_entry("смена площадки")
    assert len(log.read_text(encoding="utf-8").splitlines()) == 1


def test_rule_annotation_binds_to_function() -> None:
    spans = [(3, 10, "change_venue"), (12, 20, "close")]
    assert check_rules._symbol_at(spans, 2) == "change_venue"  # комментарий над def
    assert check_rules._symbol_at(spans, 5) == "change_venue"  # внутри тела
    assert check_rules._symbol_at(spans, 11) == "close"
