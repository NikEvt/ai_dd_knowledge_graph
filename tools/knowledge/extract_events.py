"""Слой событий: кто публикует и кто обрабатывает события outbox/Redis Streams, какие эффекты они дают.

Учитываются ``events.publish(...)`` (в т.ч. из слушателей ORM), ``@subscribe("topic")`` и динамическая
регистрация ``subscribe(topic)(handler)`` в цикле по константе. Эффекты: письма (сервис notifications)
и записи в ленте чата (сервис chat).

Запуск: uv run python tools/knowledge/extract_events.py  ->  knowledge/model/events.json
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge.common import edge, model_document, node, write_model
from tools.knowledge.extract_code import service_of
from tools.knowledge.pyindex import Project

GENERATOR = "tools/knowledge/extract_events.py"
EMAIL_SENDER = "services/notifications/service.py::send"
CHAT_LOGGER = "services/chat/service.py::log_event"


def extract(p: Project | None = None) -> dict[str, Any]:
    if p is None:
        p = Project()
        p.analyze()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    publishers: dict[str, list[str]] = defaultdict(list)
    consumers: dict[str, list[str]] = defaultdict(list)
    payload: dict[str, set[str]] = defaultdict(set)
    dynamic: list[dict[str, Any]] = []

    for sid, f in sorted(p.facts.items()):
        if sid.startswith("tests/"):
            continue
        for pub in f.publishes:
            topic = pub["topic"]
            if topic is None:
                dynamic.append({"symbol": sid, "line": pub["line"], "expr": pub["expr"]})
                continue
            publishers[topic].append(sid)
            payload[topic] |= set(pub["payload"])
            edges.append(edge(sid, topic, "publishes", line=pub["line"], condition=pub["condition"] or None))
        for sub in f.subscribes:  # динамическая регистрация
            if sub["handler"] is None:
                continue
            consumers[sub["topic"]].append(sub["handler"])
            edges.append(
                edge(
                    sub["handler"],
                    sub["topic"],
                    "consumes",
                    line=sub["line"],
                    registered_in=sid,
                    dynamic=True,
                )
            )
            if sub["handler"].startswith("services/chat/"):
                edges.append(
                    edge(sub["topic"], "effect:chat.event_log", "notifies", template=sub["template"])
                )

    for sid, d in sorted(p.decorations.items()):
        for topic in d.subscribe:
            consumers[topic].append(sid)
            edges.append(edge(sid, topic, "consumes", line=p.symbols[sid].line))

    # Эффекты обработчиков: письма по типу шаблона, лента чата.
    effects: dict[str, dict[str, Any]] = {
        "effect:chat.event_log": node(
            "effect:chat.event_log",
            "effect",
            name="Событие в ленте чата заявки",
            implemented_by=CHAT_LOGGER,
            channel="chat",
        )
    }
    for topic, handlers in consumers.items():
        for h in handlers:
            f = p.facts.get(h)
            if f is None:
                continue
            for callee, kw, value, line in f.kwargs_literals:
                if callee == EMAIL_SENDER and kw == "type_":
                    eid = f"effect:email.{value}"
                    effects.setdefault(
                        eid,
                        node(
                            eid,
                            "effect",
                            name=f"Письмо клиенту и представителю: {value}",
                            channel="email",
                            implemented_by=EMAIL_SENDER,
                        ),
                    )
                    edges.append(edge(h, eid, "notifies", line=line))
                    edges.append(edge(topic, eid, "notifies", via=h))

    for topic in sorted(set(publishers) | set(consumers)):
        pubs = sorted(set(publishers[topic]))
        subs = sorted(set(consumers[topic]))
        nodes.append(
            node(
                topic,
                "event",
                name=topic,
                payload=sorted(payload[topic]),
                publishers=pubs,
                consumers=subs,
                publisher_services=sorted({s for x in pubs if (s := service_of(x))}),
                consumer_services=sorted({s for x in subs if (s := service_of(x))}),
                orphan="нет подписчиков" if not subs else ("нет публикаторов" if not pubs else None),
            )
        )
        for svc in sorted({s for x in pubs if (s := service_of(x))}):
            edges.append(edge(f"service:{svc}", topic, "publishes"))
        for svc in sorted({s for x in subs if (s := service_of(x))}):
            edges.append(edge(f"service:{svc}", topic, "consumes"))
    nodes.extend(effects.values())
    return model_document(GENERATOR, nodes, edges, dynamic_topics=dynamic)


def main() -> None:
    doc = extract()
    write_model("events", doc)
    print(f"knowledge/model/events.json: {len(doc['nodes'])} nodes, {len(doc['edges'])} edges")


if __name__ == "__main__":
    main()
