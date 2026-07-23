#!/usr/bin/env bash
# governance_families.sh — 治理家族 SoT 的 bash getter(source 用)。
# 用法: source scripts/governance_families.sh; families_get <key> [sep]
#   key ∈ families|review_families|executor_clis|advisory_only
#   sep 預設 ','; 傳 '|' 可直接組 regex alternation
# fail-closed: SoT 檔缺/JSON 壞/key 缺或非非空 list → return≠0(caller 須處理,勿放行)。
# 雙語一致: python 端 governance_families_loader.py 讀同檔同 key。

_GF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_GF_JSON="${_GF_DIR}/governance_families.json"

families_get() {
  local key="${1:-}" sep="${2:-,}"
  [ -n "${key}" ] || { echo "families_get: 缺 key" >&2; return 2; }
  [ -f "${_GF_JSON}" ] || { echo "families_get: SoT 檔不存在(fail-closed): ${_GF_JSON}" >&2; return 1; }
  python3 - "${_GF_JSON}" "${key}" "${sep}" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    sys.stderr.write("families_get: JSON 讀取失敗: %s\n" % e); sys.exit(1)
key, sep = sys.argv[2], sys.argv[3]
v = d.get(key)
if not isinstance(v, list) or not v or not all(isinstance(x, str) and x for x in v):
    sys.stderr.write("families_get: key 缺/非非空字串list: %s\n" % key); sys.exit(1)
print(sep.join(v))
PY
}

# families_get_upper — 回大寫(給 ADV regex 用: CODEX|COMPOSER|GROK)
families_get_upper() {
  local key="${1:-}" sep="${2:-|}"
  local out
  out="$(families_get "${key}" "${sep}")" || return $?
  printf '%s' "${out}" | tr '[:lower:]' '[:upper:]'
}
