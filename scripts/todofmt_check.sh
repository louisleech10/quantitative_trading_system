#!/usr/bin/env bash
# todofmt_check.sh — TODOFMT Task 0.1／0.2：新格式 manifest 之機械判定。
#   規格：docs/TODOFMT_SPEC.md（Task 0.1 契約表、Task 0.2）。契約：同目錄 todofmt_contract.json。
#
# 用法：
#   bash scripts/todofmt_check.sh <manifest.json>   # 判定；rc 0＝合規／1＝不合規／2＝用法或環境錯誤
#   bash scripts/todofmt_check.sh --digest          # 印現行 contract_digest（128 hex）
#   bash scripts/todofmt_check.sh --keys            # 印契約鍵集（頂層鍵與 batch_card.<子鍵>，排序，一行一鍵）
#   `bash scripts/template_check.sh todofmt <manifest>` 以 exec 轉呼叫本檔，rc 與輸出即本檔所出。
#
# 契約 JSON 只承載鍵集、型別名、required、exists_check；型別之值域與跨欄規則在本檔（SPEC Task 0.1）。
# contract_digest＝sha256(契約 JSON 之 `jq -S -c .` 輸出) ∥ sha256(本檔)——改規則不論改在哪一邊，樣本皆失效。
# 契約與 repo 根一律由本檔所在位置推導；不讀任何環境變數。純 jq＋路徑檢查，不執行 pytest（SPEC C-5）。
#
# 空類之宣告：stub_modules／contract_jsons 為空，或 test_files 與 script_acceptance 皆空時，
#   batch_card.not_executable 須有 item 恰為該鍵名（`stub_modules`／`contract_jsons`／`test_files`）之一項。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTRACT="${SCRIPT_DIR}/todofmt_contract.json"
SELF="${SCRIPT_DIR}/$(basename "${BASH_SOURCE[0]}")"

_usage() {
  echo "用法: todofmt_check.sh <manifest.json> | --digest | --keys" >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || { echo "todofmt_check: 找不到 jq ⇒ fail-closed" >&2; exit 2; }
[ -f "${CONTRACT}" ] || { echo "todofmt_check: 契約檔不存在：${CONTRACT}" >&2; exit 2; }

_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum | awk '{print $1}'
  else shasum -a 256 | awk '{print $1}'; fi
}

_digest() {
  _dc="$(jq -S -c . "${CONTRACT}" | _sha256)" || return 1
  _ds="$(_sha256 < "${SELF}")" || return 1
  [ ${#_dc} -eq 64 ] && [ ${#_ds} -eq 64 ] || return 1
  printf '%s%s\n' "${_dc}" "${_ds}"
}

case "${1:-}" in
  --digest) [ $# -eq 1 ] || _usage; _digest || { echo "todofmt_check: digest 計算失敗" >&2; exit 2; }; exit 0 ;;
  --keys) [ $# -eq 1 ] || _usage; jq -r '(.top|keys[]), (.batch_card|keys[]|"batch_card."+.)' "${CONTRACT}" | LC_ALL=C sort; exit 0 ;;
  ""|-*) _usage ;;
esac
[ $# -eq 1 ] || _usage
manifest="$1"

errs=""
_err() { errs="${errs}  · $1
"; }
_fail_now() {
  printf 'TODOFMT FAIL: %s\n%s' "${manifest}" "${errs}"
  exit 1
}

[ -f "${manifest}" ] || { _err "manifest 不存在"; _fail_now; }
jq -e 'type=="object"' "${manifest}" >/dev/null 2>&1 || { _err "JSON 不合法或頂層非物件"; _fail_now; }

# ── 1. 結構：封閉鍵集、必填、型別 ─────────────────────────────────────────────
_STRUCT='
def typeok($t; $v):
  if $t == "path_array" or $t == "string_array" then ($v|type)=="array" and all($v[]; type=="string")
  elif $t == "path" or $t == "string" then ($v|type)=="string"
  elif $t == "nonempty_string" then ($v|type)=="string" and ($v|test("\\S"))
  elif $t == "hex128" then ($v|type)=="string" and ($v|test("^[0-9a-f]{128}$"))
  elif $t == "bool" then ($v|type)=="boolean"
  elif $t == "lifecycle" then ($v|type)=="string" and ($v|IN("keep","drop_after_ticket","supersede"))
  elif $t == "receipt_array" then ($v|type)=="array" and all($v[]; type=="object"
      and (keys|sort)==["cmd","honest_bounds","path","rc"]
      and (.path|type)=="string" and (.cmd|type)=="string" and (.rc|type)=="number" and (.honest_bounds|type)=="string")
  elif $t == "forbidden_array" then ($v|type)=="array" and all($v[]; type=="object"
      and (keys|sort)==["observable","rule"] and (.rule|type)=="string" and (.observable|type)=="boolean")
  elif $t == "not_executable_array" then ($v|type)=="array" and all($v[]; type=="object"
      and (keys|sort)==["expiry","item","owner","reason"]
      and (.item|type)=="string" and (.reason|type)=="string" and (.owner|type)=="string" and (.expiry|type)=="string")
  elif $t == "batch_card" then ($v|type)=="object"
  else false end;
$c[0] as $C | . as $m
| ( (($m|keys) - ($C.top|keys))[] | "頂層未知鍵：\(.)（契約為封閉集合，不得新增第六類落點）" ),
  ( $C.top | to_entries[] | . as $e
    | if ($m|has($e.key)|not) then (if $e.value.required then "缺必填鍵：\($e.key)" else empty end)
      elif typeok($e.value.type; $m[$e.key]) then empty
      else "型別不符：\($e.key) 須為 \($e.value.type)" end ),
  ( if ($m.batch_card|type)=="object" then
      ( (($m.batch_card|keys) - ($C.batch_card|keys))[] | "batch_card 未知鍵：\(.)" ),
      ( $C.batch_card | to_entries[] | . as $e
        | if ($m.batch_card|has($e.key)|not) then (if $e.value.required then "batch_card 缺必填鍵：\($e.key)" else empty end)
          elif typeok($e.value.type; $m.batch_card[$e.key]) then empty
          else "batch_card 型別不符：\($e.key) 須為 \($e.value.type)" end )
    else empty end )
'
struct_out="$(jq -r --slurpfile c "${CONTRACT}" "${_STRUCT}" "${manifest}" 2>&1)" || { _err "結構判定執行失敗：${struct_out}"; _fail_now; }
if [ -n "${struct_out}" ]; then
  while IFS= read -r _l; do _err "${_l}"; done <<EOF
${struct_out}
EOF
  _fail_now
fi

# ── 2. 值域與跨欄規則 ─────────────────────────────────────────────────────────
_today="$(date +%Y-%m-%d)"
_SEM='
. as $m | $m.batch_card.not_executable as $ne | ($ne|map(.item)) as $items
| ( $ne[] | select(.item|test("\\S")|not) | "not_executable.item 為空" ),
  ( $ne[] | select(.reason|IN("blocked-by","user-ruling","needs-research")|not)
    | "not_executable.reason 非封閉值（blocked-by／user-ruling／needs-research）：\(.item)：\(.reason)" ),
  ( $ne[] | select(.owner|test("\\S")|not) | "not_executable 缺 owner：\(.item)" ),
  ( $ne[] | select(.expiry|test("^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")|not)
    | "not_executable.expiry 格式非 YYYY-MM-DD：\(.item)：\(.expiry)" ),
  ( $ne[] | select(.expiry|test("^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")) | select(.expiry < $today)
    | "not_executable.expiry 已過期（\(.expiry) < \($today)）：\(.item)" ),
  ( $m.batch_card.forbidden[] | select(.rule|test("\\S")|not) | "forbidden.rule 為空" ),
  ( $m.batch_card.forbidden[] | select(.observable==false) | select(.rule as $r | $items | index($r) | not)
    | "forbidden 之不可觀測項須於 not_executable 有同字面之 item：\(.rule)" ),
  ( if ($m.stub_modules|length)==0 and ($items|index("stub_modules")|not)
    then "stub_modules 為空而 not_executable 未宣告（item＝stub_modules）" else empty end ),
  ( if (($m.test_files|length)+($m.script_acceptance|length))==0 and ($items|index("test_files")|not)
    then "test_files 與 script_acceptance 皆空而 not_executable 未宣告（item＝test_files）" else empty end ),
  ( if ($m.contract_jsons|length)==0 and ($items|index("contract_jsons")|not)
    then "contract_jsons 為空而 not_executable 未宣告（item＝contract_jsons）" else empty end ),
  ( if ($m.spec_path|test("\\S")|not) then "spec_path 為空" else empty end )
'
sem_out="$(jq -r --arg today "${_today}" "${_SEM}" "${manifest}" 2>&1)" || { _err "值域判定執行失敗：${sem_out}"; _fail_now; }
if [ -n "${sem_out}" ]; then
  while IFS= read -r _l; do _err "${_l}"; done <<EOF
${sem_out}
EOF
fi

# ── 3. 路徑：repo 相對、無 `..`、exists_check=true 者須存在且解析後位於 repo 根下 ─────
# 路徑值含控制字元（換行、tab 等）者不輸出原值、改以 CTRL 標記＋JSON 編碼，
#   使下方逐行＋tab 分隔之讀取不會被路徑值本身拆開（b1 審碼 codex：換行可偽造一筆 exists_check=false 紀錄）。
_PATHS='
def row($ex; $key): if test("[[:cntrl:]]") then "CTRL\t\($key)\t\(tojson)" else "\($ex)\t\($key)\t\(.)" end;
$c[0] as $C | . as $m
| ( $C.top | to_entries[] | select(.value.type=="path_array" or .value.type=="path") | . as $e
    | ($m[$e.key] | if type=="array" then .[] else . end) | row($e.value.exists_check; $e.key) ),
  ( $C.batch_card | to_entries[] | select(.value.type=="path_array" or .value.type=="path") | . as $e
    | select($m.batch_card|has($e.key))
    | ($m.batch_card[$e.key] | if type=="array" then .[] else . end) | row($e.value.exists_check; "batch_card.\($e.key)") ),
  ( $m.run_receipts[] | .path | row($C.top.run_receipts.exists_check; "run_receipts[].path") )
'
_root_real="$(realpath "${REPO_ROOT}" 2>/dev/null)" || { _err "repo 根無法解析"; _fail_now; }
paths_out="$(jq -r --slurpfile c "${CONTRACT}" "${_PATHS}" "${manifest}" 2>&1)" || { _err "路徑擷取執行失敗：${paths_out}"; _fail_now; }
_tab="$(printf '\t')"
while IFS="${_tab}" read -r _ex _key _p; do
  [ -n "${_key}" ] || continue
  if [ "${_ex}" = "CTRL" ]; then
    _err "路徑含控制字元（換行、tab 等）：${_key}：${_p}"; continue
  fi
  case "${_p}" in
    "") _err "路徑為空：${_key}"; continue ;;
    /*) _err "路徑須為 repo 相對（不得以 / 開頭）：${_key}：${_p}"; continue ;;
  esac
  case "/${_p}/" in
    */../*) _err "路徑不得含 .. 段：${_key}：${_p}"; continue ;;
  esac
  [ "${_ex}" = "true" ] || continue
  if [ ! -e "${REPO_ROOT}/${_p}" ]; then
    _err "路徑不存在（exists_check）：${_key}：${_p}"; continue
  fi
  _rp="$(realpath "${REPO_ROOT}/${_p}" 2>/dev/null)" || { _err "路徑無法解析：${_key}：${_p}"; continue; }
  case "${_rp}" in
    "${_root_real}"/*) : ;;
    *) _err "路徑解析後位於 repo 根之外：${_key}：${_p} → ${_rp}"; continue ;;
  esac
done <<EOF
${paths_out}
EOF

# ── 4. run_receipts：資訊性，只驗位置與三鍵（SPEC Task 0.1 契約表）────────────────
# 含控制字元之路徑已於路徑段報錯，此處略過，免被換行拆成數列
_receipts="$(jq -r '.run_receipts[].path | select(test("[[:cntrl:]]")|not)' "${manifest}")"
while IFS= read -r _rp_path; do
  [ -n "${_rp_path}" ] || continue
  case "${_rp_path}" in
    handoffs/run_receipts/*) : ;;
    *) _err "run_receipts 之 path 須位於 handoffs/run_receipts/ 之下：${_rp_path}"; continue ;;
  esac
  [ -e "${REPO_ROOT}/${_rp_path}" ] || continue   # 不存在已於路徑段報
  # b1 審碼 grok：路徑為目錄時原本跳過三鍵檢查而放行
  [ -f "${REPO_ROOT}/${_rp_path}" ] || { _err "receipt 須為一般檔（非目錄等）：${_rp_path}"; continue; }
  jq -e 'type=="object" and has("schema_version") and has("command") and has("exit_code")' \
     "${REPO_ROOT}/${_rp_path}" >/dev/null 2>&1 \
    || _err "receipt 缺 schema_version／command／exit_code 三鍵之一（或非 JSON 物件）：${_rp_path}"
done <<EOF
${_receipts}
EOF

# ── 5. contract_digest：與現行計算值相等 ─────────────────────────────────────
_want="$(_digest)" || { _err "contract_digest 計算失敗"; _fail_now; }
_have="$(jq -r '.contract_digest' "${manifest}")"
[ "${_have}" = "${_want}" ] \
  || _err "contract_digest 與現行計算值不等（契約或檢查器已變；樣本須重產，只替換此欄）"

if [ -n "${errs}" ]; then
  _fail_now
fi
echo "TODOFMT PASS: ${manifest}"
exit 0
