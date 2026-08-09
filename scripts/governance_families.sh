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

# families_active_stampers — 本期**實際要求蓋章**之家族(SoT key: active_stampers)。
#
# 出生理由(2026-08-09,R-19 / CODEX-R1-P1-03):`families_get` 對「key 不存在」與
#   「key 存在但為空 list」**一律回非零** ⇒ 呼叫端分辨不出,把使用者手改成
#   `active_stampers: []` 當成「缺席」而**靜默回退全員**——使用者以為自己停了全部,
#   實際被要求全員,屬靜默不服從;而 `["codexx"]`(打錯字)更會被接受為 required,
#   ⇒ 永遠等不到該家戳記而卡死。**這一行是使用者手改的,打錯是預期失敗模式,非邊緣案例。**
#
# 三態(呼叫端須分辨,勿用單一 `||` 併掉):
#   rc=0 → stdout = 分隔清單(已驗:非空、元素皆非空字串、無重複、⊆ review_families)
#   rc=3 → key **不存在** ⇒ 呼叫端應回退 review_families
#          (乾淨 clone／CI／本機制上線前之行為逐字相同)
#   rc=1 → key **存在但不合法** ⇒ 呼叫端須 **fail-closed 拒,不得回退**
families_active_stampers() {
  local sep="${1:-,}"
  [ -f "${_GF_JSON}" ] || { echo "families_active_stampers: SoT 檔不存在(fail-closed): ${_GF_JSON}" >&2; return 1; }
  python3 - "${_GF_JSON}" "${sep}" <<'PY'
import json, sys

def die(msg):
    sys.stderr.write("families_active_stampers: %s\n" % msg)
    sys.exit(1)

try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as e:
    die("JSON 讀取失敗: %s" % e)
sep = sys.argv[2]

if "active_stampers" not in d:
    sys.exit(3)                      # 缺 key(非錯誤) → 呼叫端回退 review_families

rf = d.get("review_families")
if not isinstance(rf, list) or not rf or not all(isinstance(x, str) and x.strip() for x in rf):
    die("review_families 缺/壞,無從驗證子集關係(fail-closed)")

v = d.get("active_stampers")
if not isinstance(v, list):
    die("active_stampers 非 list(fail-closed): %r" % (v,))
if not v:
    die("active_stampers 為空 list ⇒ 等於「沒人須蓋章」,拒(fail-closed)。\n"
        "  暫停全員不是合法狀態;要停用本機制請**刪掉這個 key**(缺 key 才回退 review_families)。")
if not all(isinstance(x, str) and x.strip() for x in v):
    die("active_stampers 含非字串或空字串(fail-closed): %r" % (v,))
vs = [x.strip() for x in v]
if len(set(vs)) != len(vs):
    die("active_stampers 有重複家族(fail-closed): %r" % (vs,))
unknown = [x for x in vs if x not in rf]
if unknown:
    die("active_stampers 含不在 review_families 之家族(fail-closed): %s\n"
        "  正式名冊 review_families=%s。打錯字請改正;要擴編正式委員須**先**改 review_families。"
        % (unknown, rf))
print(sep.join(vs))
PY
}

# families_get_upper — 回大寫(給 ADV regex 用: CODEX|COMPOSER|GROK)
families_get_upper() {
  local key="${1:-}" sep="${2:-|}"
  local out
  out="$(families_get "${key}" "${sep}")" || return $?
  printf '%s' "${out}" | tr '[:lower:]' '[:upper:]'
}
