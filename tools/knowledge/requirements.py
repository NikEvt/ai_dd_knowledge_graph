"""Бизнес-требования: knowledge/requirements/*.md -> список требований.

Формат (правят люди):

    ## REQ-KIND-01 Вид заявки определяется при создании
    владелец: продукт · статус: утверждено · схема: §9

    Свободный текст до следующего заголовка.

Хэш требования — от заголовка и текста без форматирования: правка текста делает связанные правила suspect.
"""

import hashlib
import re
from pathlib import Path
from typing import Any

from tools.knowledge.common import REQUIREMENTS, rel

REQ_ID = re.compile(r"^REQ-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{2,}$")
HEADING = re.compile(r"^##\s+(\S+)\s+(.+?)\s*$")
STATUSES = {"предложено": "proposed", "утверждено": "approved", "отменено": "cancelled"}
STATUS_RU = {v: k for k, v in STATUSES.items()}
META_KEYS = {"владелец": "owner", "статус": "status", "схема": "schema"}


def requirement_files() -> list[Path]:
    return sorted(p for p in REQUIREMENTS.glob("*.md") if p.name != "README.md")


def requirement_hash(title: str, text: str) -> str:
    norm = " ".join(f"{title}\n{text}".split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def _where(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:  # файл вне репозитория (тесты)
        return str(path)


def parse(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Требования файла и ошибки формата (для check_rules)."""
    name = _where(path)
    reqs: list[dict[str, Any]] = []
    errors: list[str] = []
    cur: dict[str, Any] | None = None
    body: list[str] = []

    def flush() -> None:
        if cur is not None:
            cur["text"] = " ".join(" ".join(body).split())
            cur["hash"] = requirement_hash(cur["title"], cur["text"])
            reqs.append(cur)

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if m := HEADING.match(line):
            flush()
            rid, title = m.groups()
            where = f"{name}:{lineno}"
            if not REQ_ID.match(rid):
                errors.append(f"{where}: неверный ID требования {rid!r} (ожидается REQ-ОБЛАСТЬ-NN)")
            cur = {"id": rid, "title": title, "path": name, "line": lineno, "status": "proposed"}
            body = []
            continue
        if cur is None or (not body and not line.strip()):
            continue
        if not body and line.startswith("владелец:"):
            for part in line.split("·"):
                key, _, value = part.partition(":")
                key, value = key.strip(), value.strip()
                if key not in META_KEYS:
                    errors.append(f"{name}:{lineno}: {cur['id']}: неизвестное поле {key!r}")
                elif key == "статус":
                    if value not in STATUSES:
                        errors.append(
                            f"{name}:{lineno}: {cur['id']}: статус {value!r} не из {list(STATUSES)}"
                        )
                    cur["status"] = STATUSES.get(value, "proposed")
                else:
                    cur[META_KEYS[key]] = value
            continue
        body.append(line.strip())
    flush()
    for r in reqs:
        if not r["text"]:
            errors.append(f"{r['path']}:{r['line']}: {r['id']}: пустой текст требования")
    return reqs, errors


def load_requirements() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in requirement_files():
        out += parse(path)[0]
    return out


def requirement_nodes() -> list[dict[str, Any]]:
    return [
        {"type": "requirement", "name": r["title"], **{k: v for k, v in r.items() if v not in (None, "")}}
        for r in load_requirements()
    ]
