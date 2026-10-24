"""Сборка индекса knowledge/index.sqlite из модели (knowledge/model/*.json) и правил (knowledge/rules/*.yaml).

uv run python tools/knowledge/build_index.py                      # собрать индекс
uv run python tools/knowledge/build_index.py --all                # сначала все экстракторы, затем индекс
uv run python tools/knowledge/build_index.py --slice services/billing   # срез графа модуля (для LLM)
"""

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge import graph
from tools.knowledge.common import INDEX


def run_extractors(with_db: bool) -> None:
    from tools.knowledge import extract_bpm, extract_code, extract_events
    from tools.knowledge.common import write_model
    from tools.knowledge.pyindex import Project

    if with_db:
        import subprocess

        subprocess.run([sys.executable, str(Path(__file__).with_name("extract_db.py"))], check=True)
    p = Project()
    p.analyze()
    write_model("code", extract_code.extract())
    write_model("events", extract_events.extract(p))
    write_model("bpm", extract_bpm.extract(p))


def main() -> None:
    parser = argparse.ArgumentParser(description="Индекс модели знаний")
    parser.add_argument("--all", action="store_true", help="перед сборкой запустить экстракторы (с БД)")
    parser.add_argument("--no-db", action="store_true", help="с --all: не пересобирать слой БД")
    parser.add_argument("--slice", metavar="PREFIX", help="вывести срез графа по пути модуля и выйти")
    args = parser.parse_args()
    if args.slice:
        g = graph.Graph.load(INDEX)  # пересобирается, только если устарел
        sys.stdout.write(graph.module_slice(g, args.slice))
        return
    if args.all:
        run_extractors(with_db=not args.no_db)
    stats = graph.build(INDEX)
    print(f"knowledge/index.sqlite: {stats['nodes']} nodes, {stats['edges']} edges")


if __name__ == "__main__":
    main()
