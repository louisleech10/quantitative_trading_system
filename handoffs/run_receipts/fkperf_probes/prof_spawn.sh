#!/usr/bin/env bash
# 偵察：gen_fact_key_blocks.sh 各模式之外部程式呼叫次數（PATH shim 計數，不計時以免失真）。
# 用法：bash prof_spawn.sh [--check|--write-dry|emit]
set -u
REPO=/Users/louis/Desktop/quantitative_trading_system
SHIM="$(dirname "$0")/spawn_shim"
LOG="$(dirname "$0")/spawn.log"
mkdir -p "${SHIM}"
: > "${LOG}"
for t in jq awk sort grep sed git tr cut wc head tail shasum python3 cat mktemp printf comm uniq basename dirname realpath stat find; do
  real="$(command -v "${t}" 2>/dev/null)" || continue
  case "${real}" in "${SHIM}"/*) continue ;; esac
  printf '#!/bin/bash\necho %s >> "%s"\nexec "%s" "$@"\n' "${t}" "${LOG}" "${real}" > "${SHIM}/${t}"
  chmod +x "${SHIM}/${t}"
done
mode="${1:-emit}"
cd "${REPO}" || exit 1
case "${mode}" in
  emit)    PATH="${SHIM}:${PATH}" bash scripts/gen_fact_key_blocks.sh > /dev/null 2>&1 ;;
  --check) PATH="${SHIM}:${PATH}" bash scripts/gen_fact_key_blocks.sh --check > /dev/null 2>&1 ;;
  guard)   PATH="${SHIM}:${PATH}" bash scripts/factkey_write_guard.sh HANDOFF.md > /dev/null 2>&1 ;;
esac
echo "mode=${mode} rc=$?"
echo "total external calls: $(wc -l < "${LOG}")"
sort "${LOG}" | uniq -c | sort -rn | head -12
echo "fact keys: $(jq '[keys[] | select(. != "_schema")] | length' scripts/fact_keys.json)"
