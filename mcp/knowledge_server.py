"""MCP-сервер модели знаний ERP библиотеки (stdio).

  uv run python mcp/knowledge_server.py

Инструменты: find_entry, impact, rule, requirement, entity, who_can. Индекс knowledge/index.sqlite
пересобирается автоматически, если модель, правила, требования или сверка новее индекса.

Если задана переменная окружения EVAL_MCP_LOG, каждый вызов инструмента дописывается в этот файл
строкой JSON: {"ts", "run_id", "tool", "args", "response_tokens", "nodes_returned", "ms"}.
"""
    
import datetime as dt
import json
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Корень репозитория — в конец sys.path, чтобы пакет mcp из зависимостей не перекрывался каталогом mcp/.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from mcp.server.mcpserver import MCPServer

from tools.knowledge import graph
from tools.knowledge.common import INDEX, estimate_tokens

INSTRUCTIONS = """\
Модель знаний ERP библиотеки: бизнес-требования (REQ-…, как должно быть, правят люди), правила (R-…, как
устроено сейчас, извлечены из кода), код, БД (таблицы, CHECK, триггеры, функции), события outbox, процесс
заявки (BPM), настройки, фоновые задачи, тесты. У каждого правила — пометка словами: какое требование оно
реализует, насколько ему верить и что делать (опереться, сверить с кодом, уточнить у пользователя).
Порядок работы: find_entry(текст задачи) -> impact(ID найденного узла) -> rule/requirement/entity по
необходимости. impact возвращает context pack: связи через события, триггеры, условия процесса и настройки,
которых не видно по импортам. Код читай точечно по указанным символам."""

server = MCPServer("knowledge", instructions=INSTRUCTIONS)
_lock = threading.Lock()
_graph: graph.Graph | None = None


def _g() -> graph.Graph:
    global _graph
    with _lock:
        if _graph is None or graph.index_is_stale(INDEX):
            _graph = graph.Graph.load(INDEX)
        return _graph


def _log(tool: str, args: dict[str, Any], answer: graph.Answer, ms: float) -> None:
    path = os.environ.get("EVAL_MCP_LOG")
    if not path:
        return
    record = {
        "ts": dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds"),
        "run_id": os.environ.get("EVAL_RUN_ID"),
        "tool": tool,
        "args": args,
        "response_tokens": estimate_tokens(answer.text),
        "nodes_returned": answer.nodes,
        "ms": round(ms, 1),
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _lock, open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _call(tool: str, args: dict[str, Any], fn: Callable[[graph.Graph], graph.Answer]) -> str:
    started = time.perf_counter()
    try:
        answer = fn(_g())
    except Exception as exc:  # noqa: BLE001 - ошибка инструмента должна дойти до агента текстом
        answer = graph.Answer(f"Ошибка {tool}: {exc}", [])
    _log(tool, args, answer, (time.perf_counter() - started) * 1000)
    return answer.text


@server.tool(structured_output=False)
def find_entry(task_text: str, limit: int = 8) -> str:
    """Превращает формулировку задачи в узлы графа знаний (бизнес-требования, правила, настройки, код,
    таблицы, события, переходы процесса). Вызывай первым; ID из ответа передай в impact."""
    return _call(
        "find_entry",
        {"task_text": task_text, "limit": limit},
        lambda g: graph.find_entry(g, task_text, limit),
    )


@server.tool(structured_output=False)
def impact(node: str, budget_tokens: int = 4000, max_depth: int = 4) -> str:
    """Context pack от узла: затронутые правила, переходы и условия процесса, события и их подписчики
    в других сервисах, ограничения и триггеры БД, точки входа в код, настройки, эффекты (письма, чат),
    тесты. Обход по приоритету типов связей, ответ ограничен budget_tokens; max_depth — верхний предел.
    node — ID из find_entry (требование REQ-…, правило R-…, path::symbol, schema.table, имя триггера,
    топик, from->to)."""
    args = {"node": node, "budget_tokens": budget_tokens, "max_depth": max_depth}
    return _call("impact", args, lambda g: graph.impact(g, node, budget_tokens, max_depth))


@server.tool(structured_output=False)
def rule(id: str) -> str:  # noqa: A002 - имя параметра — часть контракта инструмента
    """Полная карточка правила по ID (R-…): почему (бизнес-требования и расхождения с ними), как (текст),
    достоверность (происхождение, проверка человеком, актуальность, опоры, открытые вопросы, оговорки),
    где (символы и строки, ограничения БД, настройки, тесты, связанные правила)."""
    return _call("rule", {"id": id}, lambda g: graph.rule_card(g, id))


@server.tool(structured_output=False)
def requirement(id: str) -> str:  # noqa: A002 - имя параметра — часть контракта инструмента
    """Карточка бизнес-требования (REQ-…): текст, статус и владелец, правила, которые его реализуют или
    расходятся с ним, открытые расхождения D-xx. Если правил нет — требование в коде не реализовано."""
    return _call("requirement", {"id": id}, lambda g: graph.requirement_card(g, id))


@server.tool(structured_output=False)
def entity(name: str) -> str:
    """Карточка сущности (таблицы): поля, FK, CHECK/UNIQUE, триггеры с функциями, ORM-модель, этапы,
    код, который пишет в таблицу, связанные правила. name — schema.table, имя класса или термин («заявка»)."""
    return _call("entity", {"name": name}, lambda g: graph.entity_card(g, name))


@server.tool(structured_output=False)
def who_can(action: str) -> str:
    """Кто и при каких условиях может выполнить действие: роли (по правилам, параметрам и переходам
    процесса), проверки доступа и бизнес-условия в коде, условия переходов."""
    return _call("who_can", {"action": action}, lambda g: graph.who_can(g, action))


if __name__ == "__main__":
    server.run("stdio")
