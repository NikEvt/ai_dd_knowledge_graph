"""Документация для людей из модели знаний: docs/ (markdown + mermaid) и блок L0 в AGENTS.md.

Ничего в docs/ руками не правится: правится модель (knowledge/rules, glossary) или код, затем
  uv run python tools/knowledge/render_docs.py
CI проверяет, что docs/ совпадает с результатом рендера.
"""

import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge import graph, reconcile
from tools.knowledge.common import DOCS, INDEX, KNOWLEDGE, ROOT, load_glossary, load_rules

GENERATED = (
    "<!-- Сгенерировано tools/knowledge/render_docs.py. "
    "Не править руками: правьте модель и перегенерируйте. -->\n\n"
)
L0_BEGIN = "<!-- BEGIN L0: генерируется render_docs.py -->"
L0_END = "<!-- END L0 -->"


def link(n: dict[str, Any], depth: int, text: str | None = None) -> str:
    """Ссылка на файл и строку относительно страницы на глубине depth внутри docs/."""
    path, line = n.get("path"), n.get("line")
    label = text or n["id"]
    if not path:
        return f"`{label}`"
    up = "../" * (depth + 1)
    return f"[`{label}`]({up}{path}#L{line})" if line else f"[`{label}`]({up}{path})"


def esc(text: Any) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def mermaid_id(text: str) -> str:
    return re.sub(r"\W", "_", text)


class Docs:
    def __init__(self) -> None:
        graph.build(INDEX)
        self.g = graph.Graph.load(INDEX, rebuild_if_stale=False)
        self.glossary = load_glossary()
        self.rules = load_rules()
        self.files: dict[str, str] = {}

    def nodes(self, type_: str) -> list[dict[str, Any]]:
        return sorted((n for n in self.g.nodes.values() if n["type"] == type_), key=lambda n: n["id"])

    def page(self, rel: str, text: str) -> None:
        self.files[rel] = GENERATED + text.rstrip() + "\n"

    def stage(self, s: str) -> str:
        return self.glossary.get("stages", {}).get(s, s)

    def role(self, r: str) -> str:
        return self.glossary.get("roles", {}).get(r, {}).get("ru", r)

    # ----------------------------------------------------------------- страницы

    def readme(self) -> None:
        stats = defaultdict(int)
        for n in self.g.nodes.values():
            stats[n["type"]] += 1
        statuses = defaultdict(int)
        for r in self.rules:
            statuses[r.get("status", "draft")] += 1
        out = [
            "# Документация ERP библиотеки",
            "",
            "Сгенерирована из модели знаний (`knowledge/`). Источник истины — модель: правила",
            "`knowledge/rules/*.yaml`, слои `knowledge/model/*.json` (извлекаются из кода и БД).",
            "",
            "| Раздел | Что внутри |",
            "|---|---|",
            "| [Процесс заявки](process.md) | этапы, переходы, условия, пути по видам, диаграмма |",
            "| [События](events.md) | кто публикует и кто обрабатывает события, эффекты |",
            "| [Сущности](entities/README.md) | таблицы: поля, ограничения, триггеры, код, правила |",
            "| [Роли](roles.md) | кто что может: по правилам, коду и процессу |",
            "| [Настройки и фоновые задачи](config.md) | константы, сроки, таймеры и кто их читает |",
            "| [Правила](rules/README.md) | все правила по модулям, статусы |",
            "| [Покрытие](coverage.md) | правила без кода и тестов, suspect, непокрытые ограничения БД |",
            "| [Сверка источников](reconciliation.md) | расхождения схемы, кода и БД |",
            "",
            "## Модель в цифрах",
            "",
            "| Тип узла | Количество |",
            "|---|---|",
            *(f"| {t} | {c} |" for t, c in sorted(stats.items())),
            "",
            "Правила по статусу: " + ", ".join(f"{k} — {v}" for k, v in sorted(statuses.items())),
        ]
        self.page("README.md", "\n".join(out))

    def process(self) -> None:
        transitions = self.nodes("bpm_transition")
        procs = self.nodes("bpm_process")
        out = [
            "# Процесс заявки",
            "",
            f"Описание: {link(procs[0], 0, 'bpm/application_process.yaml')}" if procs else "",
        ]
        out += ["", "## Этапы", "", "| Этап | Название | Виды заявок |", "|---|---|---|"]
        for s in sorted(self.nodes("status"), key=lambda n: n.get("order", 0)):
            out.append(
                f"| `{s['name']}` | {self.stage(s['name'])} | {', '.join(s.get('kinds') or []) or '—'} |"
            )
        if procs:
            out += ["", "## Пути по видам", ""]
            for kind, path in procs[0].get("paths", {}).items():
                ru = self.glossary.get("kinds", {}).get(kind, kind)
                out.append(f"- **{kind}** ({ru}): " + " → ".join(self.stage(s) for s in path))
        out += ["", "## Диаграмма переходов", "", "```mermaid", "stateDiagram-v2"]
        for t in transitions:
            src, dst = t["id"].split("->")
            label = graph.variants_text(t).replace(":", " ")
            out.append(f"    {src} --> {dst}: {label}")
        out += ["```", "", "## Переходы и код, который их выполняет", ""]
        out += ["| Переход | Исполнитель (виды, условие) | Код |", "|---|---|---|"]
        for t in transitions:
            code = sorted({e.src for e in self.g.inc.get(t["id"], []) if e.type == "transitions_to"})
            code_links = ", ".join(link(self.g.nodes[c], 0, graph.short(c)) for c in code) or "—"
            out.append(f"| {link(t, 0, t['id'])} | {esc(graph.variants_text(t))} | {code_links} |")
        out += ["", "## Условия переходов (guard)", ""]
        for gd in self.nodes("bpm_guard"):
            impl = gd.get("implemented_by")
            impl_link = link(self.g.nodes[impl], 0, impl) if impl in self.g.nodes else "**не реализовано**"
            out.append(f"- `{gd['id']}` → {impl_link}" + (f" — {gd['doc']}" if gd.get("doc") else ""))
        self.page("process.md", "\n".join(out))

    def events(self) -> None:
        events = self.nodes("event")
        out = [
            "# События",
            "",
            "Транзакционный outbox (`events.outbox`) → Redis Streams → обработчики сервисов.",
            "",
        ]
        out += ["```mermaid", "flowchart LR"]
        for svc in self.nodes("service"):
            out.append(f"    {mermaid_id(svc['id'])}[{svc['name']}]")
        for ev in events:
            out.append(f"    {mermaid_id(ev['id'])}([{ev['id']}])")
            for s in ev.get("publisher_services", []):
                out.append(f"    {mermaid_id('service:' + s)} --> {mermaid_id(ev['id'])}")
            for s in ev.get("consumer_services", []):
                out.append(f"    {mermaid_id(ev['id'])} --> {mermaid_id('service:' + s)}")
        out += [
            "```",
            "",
            "| Событие | Публикует | Обрабатывает | Данные | Эффекты |",
            "|---|---|---|---|---|",
        ]
        for ev in events:
            pubs = "<br>".join(
                link(self.g.nodes[p], 0, graph.short(p))
                for p in ev.get("publishers", [])
                if p in self.g.nodes
            )
            subs = "<br>".join(
                link(self.g.nodes[c], 0, graph.short(c)) for c in ev.get("consumers", []) if c in self.g.nodes
            )
            effects = sorted({e.dst for e in self.g.out.get(ev["id"], []) if e.type == "notifies"})
            out.append(
                f"| `{ev['id']}` | {pubs or '—'} | {subs or '—'} | {', '.join(ev.get('payload', []))} | "
                f"{', '.join(effects) or '—'} |"
            )
        self.page("events.md", "\n".join(out))

    def entities(self) -> None:
        tables = self.nodes("table")
        index = [
            "# Сущности",
            "",
            "| Таблица | Колонок | Ограничений и триггеров | ORM |",
            "|---|---|---|---|",
        ]
        for t in tables:
            cons = [e for e in self.g.inc.get(t["id"], []) if e.type in ("constrains", "on_table")]
            orm = [e.src for e in self.g.inc.get(t["id"], []) if e.type == "maps_to"]
            index.append(
                f"| [{t['id']}]({t['id']}.md) | {len(t.get('columns', []))} | {len(cons)} | "
                f"{', '.join(graph.short(o) for o in orm) or '—'} |"
            )
            card = graph.entity_card(self.g, t["id"]).text
            card = card.replace(f"Миграция: {graph._loc(t)}", f"Миграция: {link(t, 1, graph._loc(t))}")
            self.page(f"entities/{t['id']}.md", card)
        self.page("entities/README.md", "\n".join(index))

    def roles(self) -> None:
        out = ["# Роли: кто что может", ""]
        out += ["## По правилам", ""]
        by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in self.rules:
            for role in r.get("roles") or []:
                by_role[role].append(r)
        for role in self.glossary.get("roles", {}):
            rs = by_role.get(role, [])
            out.append(f"### {self.role(role)} (`{role}`)\n")
            out += [f"- {r['id']} [{r.get('status')}] {esc(r.get('title', ''))}" for r in rs] or [
                "- правил нет"
            ]
            out.append("")
        out += ["## По процессу заявки (исполнители переходов)", "", "| Роль | Переходы |", "|---|---|"]
        trans_by_role: dict[str, list[str]] = defaultdict(list)
        for t in self.nodes("bpm_transition"):
            for v in t.get("variants", []):
                for a in v["actor"]:
                    trans_by_role[a].append(
                        t["id"] + (f" [{','.join(v['kinds'])}]" if v.get("kinds") else "")
                    )
        for role, ts in sorted(trans_by_role.items()):
            out.append(f"| {self.role(role)} | {', '.join(sorted(set(ts)))} |")
        out += ["", "## По коду (параметр-исполнитель и проверки доступа)", ""]
        out += ["| Функция | Роль | Проверки доступа |", "|---|---|---|"]
        for n in self.nodes("symbol"):
            if not n["id"].startswith("services/") or n.get("kind") in ("route", "class", "orm_model"):
                continue
            roles = graph._roles_of(self.g, n)
            denied = [c for c in n.get("checks", []) if c["error"] == "AccessDenied"]
            if not roles and not denied:
                continue
            checks = "<br>".join(esc(c["message"]) for c in denied) or "—"
            out.append(
                f"| {link(n, 0, graph.short(n['id']))} | "
                f"{', '.join(self.role(r) for r in roles) or '—'} | {checks} |"
            )
        self.page("roles.md", "\n".join(out))

    def config(self) -> None:
        out = ["# Настройки и фоновые задачи", "", "## Настройки и константы, влияющие на поведение", ""]
        out += ["| Настройка | Значение | Описание | Кто читает |", "|---|---|---|---|"]
        for c in self.nodes("config"):
            readers = []
            for e in self.g.inc.get(c["id"], []):
                if e.type == "reads_config" and self.g.nodes.get(e.src, {}).get("type") != "rule":
                    tag = f" ⚠ {e.data['inferred']}" if e.data.get("inferred") else ""
                    readers.append(link(self.g.nodes[e.src], 0, graph.short(e.src)) + tag)
            value = esc(graph._clip(str(c.get("value")), 80))
            out.append(
                f"| {link(c, 0, graph.short(c['id']))} | `{value}` | {esc(c.get('doc', ''))} | "
                f"{'<br>'.join(readers) or '—'} |"
            )
        out += ["", "## Фоновые задачи", ""]
        for j in self.nodes("job"):
            reads = [e.dst for e in self.g.out.get(j["id"], []) if e.type == "reads_config"]
            pubs = [e.dst for e in self.g.out.get(j["id"], []) if e.type == "publishes"]
            trans = sorted({e.dst for e in self.g.out.get(j["id"], []) if e.type == "transitions_to"})
            calls = [e.dst for e in self.g.out.get(j["id"], []) if e.type == "calls"]
            out.append(f"### {link(j, 0, j['id'])}\n")
            out.append(f"- {j.get('doc') or 'без описания'}")
            out.append(f"- настройки: {', '.join(f'`{r}`' for r in reads) or '—'}")
            out.append(
                f"- события: {', '.join(f'`{p}`' for p in pubs) or '—'}; "
                f"вызывает: {', '.join(graph.short(c) for c in calls) or '—'}"
            )
            if trans:
                out.append(f"- переходы: {', '.join(trans)}")
            out.append("")
        self.page("config.md", "\n".join(out))

    def rules_pages(self) -> None:
        by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in self.rules:
            by_file[Path(r["_file"]).stem].append(r)
        index = ["# Правила", "", "| Модуль | Правил | verified | draft | suspect |", "|---|---|---|---|---|"]
        for module, rs in sorted(by_file.items()):
            count = lambda s, rs=rs: sum(1 for r in rs if r.get("status") == s)  # noqa: E731
            index.append(
                f"| [{module}]({module}.md) | {len(rs)} | {count('verified')} | {count('draft')} | "
                f"{count('suspect')} |"
            )
            out = [
                f"# Правила: {module}",
                "",
                f"Источник: [`knowledge/rules/{module}.yaml`](../../knowledge/rules/{module}.yaml)",
                "",
            ]
            for r in rs:
                out.append(f"## {r['id']} — {esc(r.get('title', ''))}")
                out.append("")
                out.append(
                    f"`{r.get('status', 'draft')}`"
                    + (f" · {r['kind']}" if r.get("kind") else "")
                    + (f" · {esc(r['schema_ref'])}" if r.get("schema_ref") else "")
                )
                out.append("")
                out.append(esc(r.get("text", "")))
                out.append("")
                impl = []
                for e in r.get("implemented_by") or []:
                    target = e.get("symbol") or e.get("transition") or e.get("guard")
                    n = self.g.nodes.get(target)
                    if n is None:
                        impl.append(f"`{target}`")
                        continue
                    span = re.match(r"^\s*(\d+)", str(e.get("lines") or ""))
                    shown = {**n, "line": int(span.group(1))} if span else n
                    impl.append(link(shown, 1, f"{target}" + (f":{e['lines']}" if e.get("lines") else "")))
                if impl:
                    out.append("- Реализация: " + ", ".join(impl))
                if r.get("enforced_by_db"):
                    db = []
                    for e in r["enforced_by_db"]:
                        target = next(iter(e.values())) if isinstance(e, dict) else e
                        n = self.g.nodes.get(target)
                        db.append(link(n, 1, target) if n else f"`{target}`")
                    out.append("- БД: " + ", ".join(db))
                if r.get("config"):
                    out.append("- Настройки: " + ", ".join(f"`{c}`" for c in r["config"]))
                if r.get("tested_by"):
                    out.append("- Тесты: " + ", ".join(f"`{t}`" for t in r["tested_by"]))
                if r.get("roles"):
                    out.append("- Роли: " + ", ".join(self.role(x) for x in r["roles"]))
                if r.get("related"):
                    out.append("- Связанные: " + ", ".join(r["related"]))
                if r.get("discrepancy"):
                    out.append(f"- ⚠ Расхождение со схемой: {esc(r['discrepancy'])}")
                out.append("")
            self.page(f"rules/{module}.md", "\n".join(out))
        self.page("rules/README.md", "\n".join(index))

    def coverage(self) -> None:
        f = reconcile.findings()
        no_impl = [r for r in self.rules if not r.get("implemented_by") and not r.get("enforced_by_db")]
        no_tests = [r for r in self.rules if not r.get("tested_by")]
        suspect = [r for r in self.rules if r.get("status") == "suspect"]
        out = ["# Покрытие модели", ""]
        out.append(
            f"- Правил: {len(self.rules)}; verified: {sum(r.get('status') == 'verified' for r in self.rules)}"
        )
        out.append(f"- Без реализации (implemented_by / enforced_by_db): {len(no_impl)}")
        out.append(f"- Без тестов (tested_by): {len(no_tests)}")
        out.append(f"- suspect: {len(suspect)}")
        out.append(f"- Ограничения БД без правил: {len(f['db_uncovered'])}")
        out.append(f"- Проверки в коде без правил: {len(f['code_checks_uncovered'])}")
        sections = [
            (
                "suspect",
                [f"{r['id']} (с {r.get('suspect_since', '?')}) {esc(r.get('title', ''))}" for r in suspect],
            ),
            ("Правила без реализации", [f"{r['id']} {esc(r.get('title', ''))}" for r in no_impl]),
            ("Правила без тестов", [f"{r['id']} {esc(r.get('title', ''))}" for r in no_tests]),
            ("Ограничения БД без правил", f["db_uncovered"]),
            ("Проверки в коде без правил", f["code_checks_uncovered"]),
        ]
        for title, items in sections:
            out += ["", f"## {title} ({len(items)})", ""]
            out += [f"- {esc(x)}" for x in items] or ["- нет"]
        self.page("coverage.md", "\n".join(out))

    def reconciliation(self) -> None:
        f = reconcile.findings()
        out = ["# Сверка источников: схема, код, БД", ""]
        out.append(
            "Проект реализует подмножество общей схемы (`knowledge/sources/erp-library.md`) с упрощениями."
        )
        out.append("Расхождения фиксируются здесь и в `knowledge/reconciliation.yaml`; код не исправляется.")
        path = KNOWLEDGE / "reconciliation.yaml"
        items = (
            (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("discrepancies", [])
            if path.exists()
            else []
        )
        out += ["", f"## Расхождения ({len(items)})", ""]
        if items:
            out += [
                "| ID | Важность | Расхождение | Схема | Код / БД | Правила | Вопрос |",
                "|---|---|---|---|---|---|---|",
            ]
            for d in items:
                code_db = esc(d.get("code", "")) + (f"<br>БД: {esc(d['db'])}" if d.get("db") else "")
                out.append(
                    f"| {d.get('id')} | {d.get('severity', '')} | {esc(d.get('title', ''))} | "
                    f"{esc(d.get('schema', ''))} | "
                    f"{code_db} | {', '.join(d.get('rules') or [])} | {esc(d.get('question', ''))} |"
                )
        else:
            out.append("- пока нет")
        out += ["", "## Детерминированная сверка", "", reconcile.to_markdown(f).replace("### ", "### ")]
        self.page("reconciliation.md", "\n".join(out))

    # ----------------------------------------------------------------- L0 для AGENTS.md

    def l0(self) -> str:
        procs = self.nodes("bpm_process")
        lines = ["### Карта системы (L0)", ""]
        lines.append(
            "Сервисы: "
            + "; ".join(f"**{k}** — {v}" for k, v in self.glossary.get("services", {}).items())
            + "."
        )
        lines.append("")
        if procs:
            lines.append("Этапы заявки по видам:")
            for kind, path in procs[0].get("paths", {}).items():
                lines.append(f"- {kind}: {' → '.join(path)}")
            lines.append("- вне пути: archived (архив, попытки), closed_duplicate (дубль)")
        lines.append("")
        lines.append(
            "Роли: " + ", ".join(f"{self.role(r)} (`{r}`)" for r in self.glossary.get("roles", {})) + "."
        )
        lines.append("")
        lines.append("Сущности: " + ", ".join(f"`{t['id']}`" for t in self.nodes("table")) + ".")
        lines.append("")
        lines.append("События: " + ", ".join(f"`{e['id']}`" for e in self.nodes("event")) + ".")
        statuses = defaultdict(int)
        for r in self.rules:
            statuses[r.get("status", "draft")] += 1
        lines.append("")
        lines.append(
            f"Правил в модели: {len(self.rules)} ("
            + ", ".join(f"{k}: {v}" for k, v in sorted(statuses.items()))
            + ")."
        )
        return "\n".join(lines)

    def write(self) -> None:
        self.readme()
        self.process()
        self.events()
        self.entities()
        self.roles()
        self.config()
        self.rules_pages()
        self.coverage()
        self.reconciliation()
        if DOCS.exists():
            shutil.rmtree(DOCS)
        for rel, text in self.files.items():
            path = DOCS / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        agents = ROOT / "AGENTS.md"
        if agents.exists():
            text = agents.read_text(encoding="utf-8")
            if L0_BEGIN in text and L0_END in text:
                head, rest = text.split(L0_BEGIN, 1)
                _, tail = rest.split(L0_END, 1)
                agents.write_text(f"{head}{L0_BEGIN}\n{self.l0()}\n{L0_END}{tail}", encoding="utf-8")
        print(f"docs/: {len(self.files)} страниц")


def main() -> None:
    Docs().write()


if __name__ == "__main__":
    main()
