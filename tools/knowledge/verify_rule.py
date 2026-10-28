"""Отметка «проверено человеком»: единственный способ поставить правилу статус verified.

Сохраняет кто и когда проверил и отпечаток проверенной версии (смысл правила + хэши кода, БД и требований).
Если правило потом поменяют, отпечаток не совпадёт и правило покажется как «правили после проверки».

  uv run python tools/knowledge/verify_rule.py R-APP-CREATE-01 --by "Иванов И."
  uv run python tools/knowledge/verify_rule.py --pin-existing   # разово: отпечаток verified-правил без него
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.knowledge import trust
from tools.knowledge.common import dump_rules_yaml, error, rule_files
from tools.knowledge.drift import read_rule_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Отметить правила проверенными человеком")
    parser.add_argument("ids", nargs="*", help="ID правил")
    parser.add_argument("--by", help="кто проверил (обязательно для отметки)")
    parser.add_argument(
        "--pin-existing",
        action="store_true",
        help="проставить отпечаток verified-правилам, у которых его нет (кто и когда не меняются)",
    )
    args = parser.parse_args()
    if args.ids and not args.by:
        error("укажи --by: кто проверил правило")
        return 1
    wanted = set(args.ids)
    done: set[str] = set()
    for path in rule_files():
        header, rules = read_rule_file(path)
        dirty = False
        for r in rules:
            if r.get("id") in wanted:
                for key in ("suspect_since", "suspect_reason"):
                    r.pop(key, None)
                r["status"] = "verified"
                r["verified_by"] = args.by
                r["verified_at"] = dt.date.today().isoformat()
                r["verified_fingerprint"] = trust.fingerprint(r)
                done.add(r["id"])
                dirty = True
            elif args.pin_existing and r.get("status") == "verified" and not r.get("verified_fingerprint"):
                r["verified_fingerprint"] = trust.fingerprint(r)
                done.add(r["id"])
                dirty = True
        if dirty:
            path.write_text(dump_rules_yaml(header, rules), encoding="utf-8")
    for rid in sorted(wanted - done):
        error(f"правило {rid} не найдено")
    print(f"отмечено: {len(done)}")
    return 1 if wanted - done else 0


if __name__ == "__main__":
    sys.exit(main())
