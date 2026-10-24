#!/usr/bin/env bash
# Фаза 7: PR с мутацией кода (модель знаний не обновлена) → шаги CI решения на ветке variant/S.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
OUT=$EVAL/logs/mutations; mkdir -p "$OUT"
for M in ${@:-M1 M2 M3 M4 M5 M6}; do
  WT=$WT_ROOT/mut-$M; D=$OUT/$M; rm -rf "$WT" "$D"; mkdir -p "$D"
  git clone -q --no-local --single-branch --no-tags --branch variant/S "$REPO" "$WT"
  cd "$WT"; uv sync -q
  BASE=$(git rev-parse HEAD)
  python3 "$EVAL/mutations/mutations.py" "$M" || { echo "$M: мутация не применилась"; continue; }
  git add -A && git -c user.name=mut -c user.email=mut@local commit -qm "mutation $M"
  git diff --stat "$BASE" > "$D/mutation.stat"
  step() { local name=$1; shift; "$@" > "$D/$name.txt" 2>&1; echo $? > "$D/$name.exit"; }
  step build_index uv run python tools/knowledge/build_index.py --all
  step model_fresh git diff --exit-code -- knowledge/model
  git diff --stat -- knowledge/model > "$D/model_diff.stat"
  step drift uv run python tools/knowledge/drift.py --skip-model-check --base "$BASE"
  step check_rules uv run python tools/knowledge/check_rules.py --base "$BASE"
  uv run python tools/knowledge/render_docs.py > /dev/null 2>&1
  step docs_fresh git diff --exit-code -- docs AGENTS.md
  printf "%s: build=%s model_fresh=%s drift=%s check_rules=%s docs_fresh=%s\n" "$M" \
    "$(cat $D/build_index.exit)" "$(cat $D/model_fresh.exit)" "$(cat $D/drift.exit)" "$(cat $D/check_rules.exit)" "$(cat $D/docs_fresh.exit)"
  cd "$EVAL"; rm -rf "$WT"
done
uv run -q --with pyyaml python "$EVAL/scripts/score_mutations.py"
