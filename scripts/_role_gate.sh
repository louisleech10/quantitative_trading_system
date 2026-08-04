#!/usr/bin/env bash
# _role_gate.sh — 角色閘 + task_id 白名單的**唯一實作**（GOVFLOW Task 3.1 / A-3）。
#
# 為何存在：角色相容性原先只在 cx_run 派工當下才驗 → 開債後才發現不相容
#   ⇒ 半失敗輪（R1 整輪 abandon）。前移到 committee_run 的 gate.sh dispatch **之前**，
#   且 cx_run 仍呼叫同一份（前移是早退，不是搬走）。
#
# 用法（subprocess 呼叫，勿 source——內部自管 mktemp＋EXIT trap，避免覆寫呼叫端 trap）:
#   bash scripts/_role_gate.sh check-family  <brief_path> <family> [--kind KIND]
#   bash scripts/_role_gate.sh check-families <brief_path> <fam1,fam2,...>
#   bash scripts/_role_gate.sh check-task-id  <task_id>
#   bash scripts/_role_gate.sh task-id-regex          # stdout 印白名單 ERE（錨定 fullmatch 形）
#
# rc: 0=通過；2=不相容／用法錯／fail-closed。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
ROLES_JSON="${SCRIPT_DIR}/governance_roles.json"
FAMILIES_SH="${SCRIPT_DIR}/governance_families.sh"

# 暫存檔契約：本腳本以 subprocess 執行，自管 mktemp + 單一 EXIT trap
# （不 source 進 cx_run——避免覆寫 cx_run 檔頭那一個 trap）。
_RG_TMP_FILES=""
_rg_mktemp() {
  local f
  f="$(mktemp)"
  _RG_TMP_FILES="${_RG_TMP_FILES} ${f}"
  printf '%s\n' "${f}"
}
_rg_cleanup() {
  # shellcheck disable=SC2086
  [ -n "${_RG_TMP_FILES}" ] && rm -f ${_RG_TMP_FILES}
  _RG_TMP_FILES=""
}
trap '_rg_cleanup' EXIT

# ── 單一來源：task_id 白名單（D-001 §D2／第⑦道；禁他處再寫一份）──────────────
# ERE full-match 形（含 ^$）；python re.fullmatch 用去錨後的本體亦可。
ROLE_GATE_TASK_ID_REGEX='^[A-Za-z0-9._-]+$'

# ── family → CLI 正規化映射（禁 raw set intersection；composer→cursor-agent）──
# 寫死於此：review_families 與 executor_clis 是異質命名空間。
_family_to_cli() {
  case "$1" in
    codex)    printf '%s' "codex" ;;
    grok)     printf '%s' "grok" ;;
    composer) printf '%s' "cursor-agent" ;;
    *)        return 1 ;;
  esac
}

_usage() {
  echo "用法: bash scripts/_role_gate.sh check-family <brief> <family> [--kind KIND]" >&2
  echo "      bash scripts/_role_gate.sh check-families <brief> <fam1,fam2,...>" >&2
  echo "      bash scripts/_role_gate.sh check-task-id <task_id>" >&2
  echo "      bash scripts/_role_gate.sh task-id-regex" >&2
}

# ── task_id 白名單 ──────────────────────────────────────────────────────────
cmd_check_task_id() {
  local tid="${1:-}"
  if [ -z "${tid}" ]; then
    echo "ERROR: task_id 為空（白名單檢查，fail-closed）" >&2
    return 2
  fi
  # bash [[ =~ ]]：右側未加引號時為 ERE；ROLE_GATE_TASK_ID_REGEX 已含 ^$
  if [[ ! "${tid}" =~ ${ROLE_GATE_TASK_ID_REGEX} ]]; then
    echo "ERROR: task_id 不符合白名單 ${ROLE_GATE_TASK_ID_REGEX}（第⑦道／committee 前移）: ${tid}" >&2
    return 2
  fi
  return 0
}

cmd_task_id_regex() {
  printf '%s\n' "${ROLE_GATE_TASK_ID_REGEX}"
}

# ── 讀 brief-kind（reuse brief_conformance_check --emit；禁本檔新增 parser）──
# 內部自管 mktemp；以子行程身份執行，清理用顯式 rm（避免巢狀 trap 覆寫）。
# 呼叫端（committee_run／cx_run）只 bash 呼叫、不 source——符合「單一 EXIT trap」契約。
_resolve_brief_kind() {
  # $1=brief  $2=optional pre-known kind → stdout 印 kind
  local brief="$1"
  local known="${2:-}"
  if [ -n "${known}" ]; then
    printf '%s\n' "${known}"
    return 0
  fi
  local _kv kind
  _kv="$(_rg_mktemp)"
  if ! bash "${SCRIPT_DIR}/brief_conformance_check.sh" "${brief}" --emit "${_kv}"; then
    return 2
  fi
  kind="$(sed -n '1p' "${_kv}")"
  if [ -z "${kind}" ]; then
    echo "ERROR: brief-kind 解析為空（fail-closed）" >&2
    return 2
  fi
  printf '%s\n' "${kind}"
}

# ── 讀 roles SoT ────────────────────────────────────────────────────────────
_load_implementer() {
  [ -f "${ROLES_JSON}" ] || {
    echo "ERROR: 角色 SoT 缺檔: ${ROLES_JSON}(fail-closed)" >&2
    return 2
  }
  local impl
  impl="$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['implementer'])" "${ROLES_JSON}" 2>/dev/null)" || {
    echo "ERROR: 角色 SoT 解析失敗或缺鍵(fail-closed): ${ROLES_JSON}" >&2
    return 2
  }
  [ -n "${impl}" ] || {
    echo "ERROR: 角色 SoT implementer 為空(fail-closed): ${ROLES_JSON}" >&2
    return 2
  }
  printf '%s\n' "${impl}"
}

_load_review_families_and_clis() {
  # stdout 兩行：review_families(空白分隔) / executor_clis(空白分隔)
  # shellcheck source=/dev/null
  . "${FAMILIES_SH}" || {
    echo "ERROR: 無法載入 family SoT(fail-closed)" >&2
    return 2
  }
  local rf ec
  rf="$(families_get review_families ' ')" || {
    echo "ERROR: 讀 review_families 失敗(fail-closed)" >&2
    return 2
  }
  ec="$(families_get executor_clis ' ')" || {
    echo "ERROR: 讀 executor_clis 失敗(fail-closed)" >&2
    return 2
  }
  printf '%s\n%s\n' "${rf}" "${ec}"
}

# ── 可執行判定表（由 governance_roles.json _rules 散文導出；禁直接比對散文）──
# brief-kind=impl     → 家族必須 == implementer
# brief-kind=review   → 家族必須 != implementer
# brief-kind=consult  → 不限制（仍須 mapping）
# brief-kind=closure  → 不限制（仍須 mapping）
# brief-kind=stamp    → 不限制（仍須 mapping；SoT _rules 與 closure 同組）
# 未知 brief-kind     → fail-closed
_role_rule_for_family() {
  # $1=kind $2=family $3=implementer → stdout 空=ok；非空=錯誤訊息
  local kind="$1" fam="$2" impl="$3"
  case "${kind}" in
    impl)
      if [ "${fam}" != "${impl}" ]; then
        printf '角色不符 — brief-kind=impl 的實作端須為 %s,但收到 %s' "${impl}" "${fam}"
      fi
      ;;
    review)
      if [ "${fam}" = "${impl}" ]; then
        printf '角色不符 — %s 是現行 implementer,不得擔任 code review(實作者不自審)' "${fam}"
      fi
      ;;
    consult|closure|stamp)
      : # 不限制 implementer
      ;;
    *)
      printf '未知 brief-kind=%s（角色閘 fail-closed）' "${kind}"
      ;;
  esac
}

_mapping_ok() {
  # $1=family $2=review_families_ws $3=executor_clis_ws
  # rc 0 ok；stdout 錯誤訊息時 rc 1
  local fam="$1" rf="$2" ec="$3"
  local cli
  if ! cli="$(_family_to_cli "${fam}")"; then
    printf '家族 %s 不在 family→CLI 映射（claude/agy/未知 ⇒ fail-closed）' "${fam}"
    return 1
  fi
  case " ${rf} " in
    *" ${fam} "*) : ;;
    *)
      printf '家族 %s 不在 review_families' "${fam}"
      return 1
      ;;
  esac
  case " ${ec} " in
    *" ${cli} "*) : ;;
    *)
      printf '家族 %s 映射 CLI=%s 不在 executor_clis' "${fam}" "${cli}"
      return 1
      ;;
  esac
  return 0
}

# ── 核心：對一組家族套用 mapping + 角色判定；累積完整清單 ──────────────────
_check_families_core() {
  # $1=kind  $2=fams_ws（空白分隔）  $3=mode
  # mode=strict_mapping → 未映射即拒（committee_run 路徑）
  # mode=known_only     → 僅對 review_families 內家族套用規則（cx_run 相容：未知家族交給 dispatch）
  local kind="$1"
  local fams_ws="$2"
  local mode="$3"

  local impl
  impl="$(_load_implementer)" || return 2

  local pair rf ec
  pair="$(_load_review_families_and_clis)" || return 2
  rf="$(printf '%s\n' "${pair}" | sed -n '1p')"
  ec="$(printf '%s\n' "${pair}" | sed -n '2p')"

  # 用暫存檔累積錯誤（bash 3.2 可攜）；歸 _rg_mktemp 由 EXIT trap 清理
  local err_file fam msg map_msg map_rc
  local n=0 n_err=0
  err_file="$(_rg_mktemp)"

  for fam in ${fams_ws}; do
    n=$((n + 1))
    case " ${rf} " in
      *" ${fam} "*)
        map_msg="$(_mapping_ok "${fam}" "${rf}" "${ec}" 2>/dev/null)" && map_rc=0 || map_rc=$?
        if [ "${map_rc}" -ne 0 ]; then
          printf '  · %s: %s\n' "${fam}" "${map_msg}" >> "${err_file}"
          n_err=$((n_err + 1))
          continue
        fi
        msg="$(_role_rule_for_family "${kind}" "${fam}" "${impl}")"
        if [ -n "${msg}" ]; then
          printf '  · %s: %s\n' "${fam}" "${msg}" >> "${err_file}"
          n_err=$((n_err + 1))
        fi
        ;;
      *)
        if [ "${mode}" = "strict_mapping" ]; then
          map_msg="$(_mapping_ok "${fam}" "${rf}" "${ec}" 2>/dev/null)" && map_rc=0 || map_rc=$?
          if [ "${map_rc}" -ne 0 ] && [ -n "${map_msg}" ]; then
            printf '  · %s: %s\n' "${fam}" "${map_msg}" >> "${err_file}"
          else
            printf '  · %s: 家族不在 review_families（committee 角色閘 fail-closed）\n' "${fam}" >> "${err_file}"
          fi
          n_err=$((n_err + 1))
        fi
        # known_only：跳過（交給 cx_run dispatch case）
        ;;
    esac
  done

  if [ "${n}" -lt 1 ]; then
    echo "ERROR: 角色閘：家族清單為空" >&2
    return 2
  fi

  if [ "${n_err}" -gt 0 ]; then
    echo "ERROR: 角色閘不相容（完整清單；整批拒絕）:" >&2
    cat "${err_file}" >&2
    echo "  角色 SoT: ${ROLES_JSON}  implementer=${impl}  brief-kind=${kind}" >&2
    return 2
  fi
  return 0
}

cmd_check_family() {
  local brief="${1:-}" fam="${2:-}"
  shift 2 2>/dev/null || true
  local kind_arg=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --kind)
        [ "$#" -ge 2 ] || { echo "ERROR: --kind 需要參數" >&2; return 2; }
        kind_arg="$2"; shift 2 ;;
      *) echo "ERROR: 未知旗標: $1" >&2; return 2 ;;
    esac
  done
  [ -n "${brief}" ] && [ -n "${fam}" ] || { _usage; return 2; }
  [ -f "${brief}" ] || { echo "ERROR: brief 不存在: ${brief}" >&2; return 2; }

  local kind
  kind="$(_resolve_brief_kind "${brief}" "${kind_arg}")" || return 2
  _check_families_core "${kind}" "${fam}" "known_only"
}

cmd_check_families() {
  local brief="${1:-}" csv="${2:-}"
  [ -n "${brief}" ] && [ -n "${csv}" ] || { _usage; return 2; }
  [ -f "${brief}" ] || { echo "ERROR: brief 不存在: ${brief}" >&2; return 2; }

  local kind
  kind="$(_resolve_brief_kind "${brief}" "")" || return 2
  local fams_ws
  fams_ws="$(printf '%s' "${csv}" | tr ',' ' ')"
  _check_families_core "${kind}" "${fams_ws}" "strict_mapping"
}

# ── dispatch ────────────────────────────────────────────────────────────────
cmd="${1:-}"
shift 2>/dev/null || true
case "${cmd}" in
  check-task-id)   cmd_check_task_id "$@" ;;
  task-id-regex)   cmd_task_id_regex "$@" ;;
  check-family)    cmd_check_family "$@" ;;
  check-families)  cmd_check_families "$@" ;;
  ""|-h|--help)    _usage; exit 2 ;;
  *) echo "ERROR: 未知子命令: ${cmd}" >&2; _usage; exit 2 ;;
esac
exit $?
