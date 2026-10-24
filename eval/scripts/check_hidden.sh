#!/usr/bin/env bash
# Прогон скрытых тестов против ревизии проекта во временном worktree.
#   check_hidden.sh --rev v0 [--out DIR]
# Печатает сводку: регрессия (ожидается зелёная) и тесты задач (на v0 ожидаются красные).
set -euo pipefail
source "$(dirname "$0")/lib.sh"

REV=HEAD OUT=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --rev) REV=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done

WT=$WT_ROOT/hidden-check-$$
git -C "$REPO" worktree add -q --detach "$WT" "$REV"
trap 'git -C "$REPO" worktree remove --force "$WT"' EXIT
cp -R "$EVAL/hidden_tests" "$WT/_hidden"
OUT=${OUT:-$WT/_reports}
mkdir -p "$OUT"

cd "$WT"
uv sync -q
docker compose up -d --wait >/dev/null 2>&1
uv run pytest _hidden/regression -q -p no:cacheprovider --junitxml="$OUT/regression.xml" >"$OUT/regression.txt" 2>&1 || true
uv run pytest _hidden/tasks -q -p no:cacheprovider --junitxml="$OUT/tasks.xml" >"$OUT/tasks.txt" 2>&1 || true

echo "== regression: $(tail -1 "$OUT/regression.txt")"
grep -E "^(FAILED|ERROR)" "$OUT/regression.txt" || true
echo "== tasks: $(tail -1 "$OUT/tasks.txt")"
python3 - "$OUT/tasks.xml" <<'EOF'
import sys, collections, xml.etree.ElementTree as ET
by = collections.defaultdict(lambda: [0, 0])
for tc in ET.parse(sys.argv[1]).iter("testcase"):
    task = tc.get("classname").split(".")[-1].removeprefix("test_").upper()
    failed = any(c.tag in ("failure", "error") for c in tc)
    by[task][failed] += 1
for task, (ok, bad) in sorted(by.items()):
    print(f"   {task}: passed={ok} failed={bad}")
EOF
