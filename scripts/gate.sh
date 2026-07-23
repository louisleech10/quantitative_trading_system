#!/usr/bin/env bash
# gate.sh — mint a fail-closed gate token after recording a mandatory checklist.
# bash 3.2 相容（macOS 預設）：不使用 declare -A。
#
# 用法：
#   bash scripts/gate.sh dispatch --intent "..." --risk low|high \
#        --facts-asked "..." --review-role "..." --template "..." [--adversarial PATH|waived:reason]
#   bash scripts/gate.sh dispatch ... [--reconcile PATH]  # 高風險 adversarial 含 BLOCKING/ID: 時必填
#   bash scripts/gate.sh artifact --file docs/X_SPEC.md \
#        --template-opened templates/SPEC_TEMPLATE.md --sections "§G Golden 狀態=filled; §0.A=N/A:..."
#   bash scripts/gate.sh register-output <task-id> <handoffs/path.md>
#
# 誠實邊界：不驗證填入內容為真，只強制「必填有內容」+ 對可機檢項做真實檢查
#   （高風險派工的 --adversarial 檔須存在；artifact 的 --template-opened 檔須存在），其餘記入審計供稽核。
# 缺任一必填 → 拒發 token(exit 1)。無聲跳過此 gate 會被 gate_check.sh 擋死。

set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${REPO_ROOT}/venv/bin/python"
[ -x "${VENV_PY}" ] || VENV_PY="python"
# GATE_DIR_OVERRIDE:governance 測試隔離用(token/audit 寫進 tmp,不汙染真實信任工件)
GATE_DIR="${GATE_DIR_OVERRIDE:-.claude/gate}"; AUDIT="${GATE_DIR}/audit.log"; mkdir -p "${GATE_DIR}"

# ---------------------------------------------------------------------------
# BC1 反 bypass：腳本覆寫 env 僅 GOVERNANCE_TEST_HARNESS=1 才認；否則 fail-closed
# （正式/生產路徑不得靜默替換 reconcile_stamps / completeness）
# ---------------------------------------------------------------------------
if [ -n "${RECONCILE_STAMPS_CHECK_OVERRIDE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: RECONCILE_STAMPS_CHECK_OVERRIDE 僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed 拒覆寫）" >&2
  exit 1
fi
if [ -n "${COMPLETENESS_CHECK_OVERRIDE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: COMPLETENESS_CHECK_OVERRIDE 僅允許 GOVERNANCE_TEST_HARNESS=1（正式路徑 fail-closed 拒覆寫）" >&2
  exit 1
fi

_print_usage() {
  cat <<'EOF'
用法範例：
  bash scripts/gate.sh dispatch --intent "..." --risk low|high \
       --facts-asked "..." --review-role "..." --template "..." [--adversarial PATH|waived:reason]
  bash scripts/gate.sh dispatch ... [--reconcile PATH]  # 高風險 adversarial 含 BLOCKING/ID: 時必填
  bash scripts/gate.sh artifact --file docs/X_SPEC.md \
       --template-opened templates/SPEC_TEMPLATE.md --sections "§G Golden 狀態=filled; §0.A=N/A:..."
  bash scripts/gate.sh register-output <task-id> <handoffs/path.md>
  bash scripts/dispatch.sh --intent "..." --risk low|high ...  # 自動補 --task-id / --output
EOF
}

kind="${1:-}"; shift || true
[ "${kind}" = "dispatch" ] || [ "${kind}" = "artifact" ] || [ "${kind}" = "register-output" ] || {
  echo "ERROR: kind 必須是 dispatch|artifact|register-output"
  _print_usage
  exit 1
}

intent=""; risk=""; facts_asked=""; review_role=""; template=""; adversarial=""
reconcile=""
task_id=""; output_path=""
file=""; template_opened=""; sections=""; spec=""; todo=""; manifest=""

_norm_output_path() {
  "${VENV_PY}" - "$1" <<'PY'
import os
import sys
from pathlib import Path

raw = sys.argv[1]
norm = raw.replace("\\", "/")
if norm.startswith("/"):
    root = Path.cwd().resolve()
    try:
        rel = Path(raw).resolve().relative_to(root).as_posix()
        norm = rel
    except ValueError:
        marker = "handoffs/"
        idx = norm.find(marker)
        if idx >= 0:
            norm = norm[idx:]
print(os.path.normpath(norm).replace("\\", "/"))
PY
}

_sha256_file() {
  "${VENV_PY}" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
}

_append_committee_json_event() {
  local event="$1"
  local tid="$2"
  local family="$3"
  local out_rel="$4"
  local output_sha256="$5"
  local dispatch_ts
  dispatch_ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
  "${VENV_PY}" - "$event" "$tid" "$family" "$out_rel" "$output_sha256" "$dispatch_ts" <<'PY' >> "${AUDIT}"
import json
import sys

event, task_id, family, output_path, output_sha256, ts = sys.argv[1:7]
print(json.dumps(
    {
        "event": event,
        "task_id": task_id,
        "family": family,
        "output_path": output_path,
        "output_sha256": output_sha256,
        "ts": ts,
    },
    ensure_ascii=False,
    sort_keys=True,
))
PY
}

_task_has_dispatch() {
  local tid="$1"
  "${VENV_PY}" - "${AUDIT}" "${tid}" <<'PY'
import json
import sys
from pathlib import Path

audit = Path(sys.argv[1])
task_id = sys.argv[2]
if not audit.is_file():
    sys.exit(1)
for raw in audit.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line.startswith("{"):
        continue
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        continue
    if event.get("event") == "committee_dispatch" and event.get("task_id") == task_id:
        sys.exit(0)
sys.exit(1)
PY
}

if [ "${kind}" = "register-output" ]; then
  task_id="${1:-}"
  output_path="${2:-}"
  [ -n "${task_id}" ] || { echo "ERROR: register-output 缺 task-id"; exit 1; }
  [ -n "${output_path}" ] || { echo "ERROR: register-output 缺 path"; exit 1; }
  case "${task_id}" in
    legacy-*) echo "ERROR: register-output 拒絕 legacy-* task-id（請用 legacy 白名單腳本）"; exit 1 ;;
  esac
  [ -f "${output_path}" ] || { echo "ERROR: register-output 檔不存在:${output_path}"; exit 1; }
  out_rel="$(_norm_output_path "${output_path}")"
  case "${out_rel}" in
    handoffs/*) : ;;
    *) echo "ERROR: register-output 只接受 handoffs/ 內檔案:${output_path}"; exit 1 ;;
  esac
  case "${out_rel}" in
    *"/../"*|"../"*|*".."*) echo "ERROR: register-output 路徑不可含 ..:${output_path}"; exit 1 ;;
  esac
  _task_has_dispatch "${task_id}" || { echo "ERROR: register-output 找不到先行 committee_dispatch task:${task_id}"; exit 1; }
  output_sha256="$(_sha256_file "${output_path}")"
  _append_committee_json_event "committee_output" "${task_id}" "unknown" "${out_rel}" "${output_sha256}"
  echo "GATE PASS：已註冊 committee output task:${task_id} path:${out_rel} sha256:${output_sha256}。審計 → ${AUDIT}"
  exit 0
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --intent)          intent="${2:-}"; shift 2 ;;
    --risk)            risk="${2:-}"; shift 2 ;;
    --facts-asked)     facts_asked="${2:-}"; shift 2 ;;
    --review-role)     review_role="${2:-}"; shift 2 ;;
    --template)        template="${2:-}"; shift 2 ;;
    --adversarial)     adversarial="${2:-}"; shift 2 ;;
    --reconcile)       reconcile="${2:-}"; shift 2 ;;
    --task-id)         task_id="${2:-}"; shift 2 ;;
    --output)          output_path="${2:-}"; shift 2 ;;
    --file)            file="${2:-}"; shift 2 ;;
    --template-opened) template_opened="${2:-}"; shift 2 ;;
    --sections)        sections="${2:-}"; shift 2 ;;
    --spec)            spec="${2:-}"; shift 2 ;;
    --todo)            todo="${2:-}"; shift 2 ;;
    --manifest)        manifest="${2:-}"; shift 2 ;;
    *) echo "ERROR: 未預期參數 $1"; exit 1 ;;
  esac
done

missing=""
miss() { missing="${missing}  · --$1: $2\n"; }

# R7：委員派工 provenance emitter（只記錄派工+輸出指紋，不聲稱內容為真）
_append_committee_dispatch_any() {
  local adv_path="$1"
  local tid="$2"
  [ -n "${tid}" ] || return 0
  local out_rel family output_sha256
  out_rel=""
  [ -n "${adv_path}" ] && out_rel="$(_norm_output_path "${adv_path}")"
  family="composer"
  case "${out_rel}" in
    *-ADV-CODEX*|*-adv-codex*) family="codex" ;;
    *-ADV-COMPOSER*|*-adv-composer*) family="composer" ;;
    *)
      case "${review_role}" in
        *codex*|*CODEX*) family="codex" ;;
        *composer*|*COMPOSER*) family="composer" ;;
      esac
      ;;
  esac
  if [ -n "${adv_path}" ] && [ -f "${adv_path}" ]; then
    output_sha256="$(_sha256_file "${adv_path}")"
  else
    output_sha256="pending"
  fi
  _append_committee_json_event "committee_dispatch" "${tid}" "${family}" "${out_rel}" "${output_sha256}"
}

# D-1/D-2：adversarial 品質輕檢（字串級；語義真偽交人工＋二期 scope-out）
_check_adversarial_quality() {
  local adv_file="$1"
  if ! grep -qE 'Verdict[[:space:]]*[:：]' "${adv_file}"; then
    echo "ERROR: --adversarial 檔缺 Verdict 行:${adv_file}（D-1 拒發）"
    return 1
  fi
  local ids has_blocking=0 has_id_finding=0
  ids="$(grep -oE 'ADV-(CODEX|COMPOSER)-[0-9]+' "${adv_file}" 2>/dev/null | sort -u || true)"
  grep -q '\[BLOCKING\]' "${adv_file}" && has_blocking=1
  grep -qE 'ID:[[:space:]]*ADV-(CODEX|COMPOSER)-[0-9]+' "${adv_file}" && has_id_finding=1
  # 舊格式（無 BLOCKING 且無 ID: finding）→ grandfather，走現行行為
  if [ "${has_blocking}" -eq 0 ] && [ "${has_id_finding}" -eq 0 ]; then
    return 0
  fi
  if [ -z "${reconcile}" ]; then
    echo "ERROR: adversarial 含 [BLOCKING] 或 ID: finding，--reconcile 必填（D-2 拒發）:${adv_file}"
    return 1
  fi
  if [ ! -f "${reconcile}" ]; then
    echo "ERROR: --reconcile 檔不存在:${reconcile}（真實檢查失敗）"
    return 1
  fi
  local missing="" id
  while IFS= read -r id; do
    [ -z "${id}" ] && continue
    if ! grep -qE "${id}.*→" "${reconcile}"; then
      missing="${missing}  · ${id}\n"
    fi
  done <<EOF
${ids}
EOF
  if [ -n "${missing}" ]; then
    echo "ERROR: reconcile 缺以下 finding 處置行(須含 →):${reconcile}"
    printf "%b" "${missing}"
    return 1
  fi
  return 0
}

# 逗號分隔多 adversarial 檔逐檔處理（trim 空白）
_foreach_adversarial() {
  local adv_list="$1"
  local adv_path trimmed
  IFS=',' read -ra _adv_arr <<< "${adv_list}"
  for adv_path in "${_adv_arr[@]}"; do
    trimmed="$(echo "${adv_path}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -n "${trimmed}" ] || continue
    if ! "$2" "${trimmed}"; then
      return 1
    fi
  done
  return 0
}

# --reconcile 已給但所有 adversarial 皆無 BLOCKING/ID: → 僅 WARN（不拒發）
_warn_reconcile_without_structured_findings() {
  local adv_list="$1"
  [ -n "${reconcile}" ] || return 0
  local adv_path trimmed any=0
  IFS=',' read -ra _adv_arr <<< "${adv_list}"
  for adv_path in "${_adv_arr[@]}"; do
    trimmed="$(echo "${adv_path}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -n "${trimmed}" ] && [ -f "${trimmed}" ] || continue
    if grep -q '\[BLOCKING\]' "${trimmed}" || grep -qE 'ID:[[:space:]]*ADV-(CODEX|COMPOSER)-[0-9]+' "${trimmed}"; then
      any=1
      break
    fi
  done
  if [ "${any}" -eq 0 ]; then
    echo "WARN: --reconcile 已提供但 adversarial 無 [BLOCKING]/ID: finding（字串級，語義真偽交人工＋二期）"
  fi
}

_process_one_adversarial_file() {
  local adv_file="$1"
  [ -f "${adv_file}" ] || { echo "ERROR: --adversarial 檔不存在:${adv_file}（真實檢查失敗）"; return 1; }
  _check_adversarial_quality "${adv_file}" || return 1
  case "${adv_file}" in
    handoffs/*-ADV-CODEX.md|handoffs/*-ADV-COMPOSER.md|handoffs/*-adv-codex.md|handoffs/*-adv-composer.md)
      "${VENV_PY}" "${SCRIPT_DIR}/verify_task_provenance.py" check-adversarial "${adv_file}" \
        || { echo "ERROR: adversarial provenance 檢查失敗（見上），拒發 token。"; return 1; }
      ;;
    *)
      # 與 _run_reconcile_stamp_check_adv 一致：測試 harness 可覆寫 stamps bin
      local _adv_stamp_bin="${RECONCILE_STAMPS_CHECK_OVERRIDE:-${SCRIPT_DIR}/reconcile_stamps_check.sh}"
      bash "${_adv_stamp_bin}" "${adv_file}" \
        || { echo "ERROR: --adversarial 既非 ADV 命名亦未獲 reconcile 戳記核可（見上），拒發 token。"; return 1; }
      ;;
  esac
  return 0
}

_run_reconcile_stamp_check_adv() {
  # 測試隔離可覆寫（非正式逃生口）
  local stamps_bin="${RECONCILE_STAMPS_CHECK_OVERRIDE:-${SCRIPT_DIR}/reconcile_stamps_check.sh}"
  bash "${stamps_bin}" "$1"
}

# ---------------------------------------------------------------------------
# _run_completeness_gate — Task 3.2：reconcile 核可後、發 token 前掛 completeness
# 解析 session sources.lock；rc==1 → 拒發；rc==3(DEGRADED_PENDING) → 拒 final；腳本缺 → 拒發
# ---------------------------------------------------------------------------
_run_completeness_gate() {
  local reconcile_file="$1"
  local completeness_bin="${COMPLETENESS_CHECK_OVERRIDE:-${SCRIPT_DIR}/completeness_check.sh}"
  local sessdir lock_path rc

  # 結構性 engagement(BC2 primary)：completeness 閘為 convergence 內容合併專用,
  #   僅對 handoffs/reconcile/<session>/ 下的 reconcile 生效。epic 自身的 meta-reconcile
  #   (handoffs/*-RECONCILE.md,非 content-merge)→ 略過(非「lock 缺→略過」,是結構判定,不可靠刪 lock 繞)。
  case "${reconcile_file}" in
    */handoffs/reconcile/*|handoffs/reconcile/*) : ;;
    *) return 0 ;;
  esac

  if [ ! -f "${completeness_bin}" ]; then
    echo "ERROR: completeness_check 腳本不存在(fail-closed): ${completeness_bin}" >&2
    return 1
  fi

  # session 推導：handoffs/reconcile/<session>/…
  case "${reconcile_file}" in
    */handoffs/reconcile/*|handoffs/reconcile/*)
      # handoffs/reconcile/<session>/...
      sessdir="$(python3 -c '
import os,sys
p=os.path.abspath(sys.argv[1])
parts=p.replace("\\\\","/").split("/")
try:
    i=parts.index("reconcile")
    # handoffs/reconcile/<session>
    if i+1 < len(parts):
        print("/".join(parts[:i+2]))
    else:
        print(os.path.dirname(p))
except ValueError:
    print(os.path.dirname(p))
' "${reconcile_file}")"
      ;;
    *)
      sessdir="$(cd "$(dirname "${reconcile_file}")" && pwd)"
      ;;
  esac

  lock_path="${sessdir}/sources.lock"
  if [ ! -f "${lock_path}" ]; then
    echo "ERROR: sources.lock 不存在(fail-closed completeness): ${lock_path}（session=${sessdir}）" >&2
    return 1
  fi

  # 正式路徑：僅 --lock，禁 argv 覆寫來源
  bash "${completeness_bin}" --lock "${lock_path}"
  rc=$?
  if [ "${rc}" -eq 0 ]; then
    return 0
  fi
  if [ "${rc}" -eq 3 ]; then
    echo "ERROR: completeness DEGRADED_PENDING(rc=3) — 合法降級不可發 final/實作 token。" >&2
    return 1
  fi
  echo "ERROR: completeness 未過(rc=${rc})，拒發實作 token。" >&2
  return 1
}

if [ "${kind}" = "dispatch" ]; then
  [ -n "${intent}" ]      || miss intent      "派什麼給誰（一句）"
  [ -n "${risk}" ]        || miss risk        "low|high（命中 a/b/c/d 任一即 high）"
  [ -n "${facts_asked}" ] || miss facts-asked "code/log 推不出、已向使用者確認的事實（或 none-needed:理由）"
  [ -n "${review_role}" ] || miss review-role "委員會角色指派：誰挑戰前提/adversary（單一執行者填 single-executor:n/a）"
  [ -n "${template}" ]    || miss template    "對 SPEC/TODO 派工:template 跟過/N-A 說明（非 spec 派工填 n/a:理由）"
  if [ "${risk}" = "high" ]; then
    [ -n "${adversarial}" ] || miss adversarial "高風險必填 adversarial review 輸出路徑（或 waived:理由）"
    case "${adversarial}" in
      ""|waived:*) : ;;
      *)
        # R7：先記錄 committee_dispatch，供後續 reconcile/adversarial provenance 機檢
        case "${adversarial}" in
          waived:*|n/a:*|N/A:*|stamped-waived:*) : ;;
          *)
            if [ -n "${task_id}" ]; then
              _append_committee_dispatch_any "${adversarial}" "${task_id}"
              export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"
            fi
            ;;
        esac
        _warn_reconcile_without_structured_findings "${adversarial}"
        _foreach_adversarial "${adversarial}" _process_one_adversarial_file \
          || { echo "ERROR: adversarial 檢查失敗（見上），拒發 token。"; exit 1; }
        ;;
    esac
    # reconcile 核可閘:對 SPEC 派「實作」(--spec 存在)時,reconcile 須獲委員戳記
    #   防「Claude 自產 reconcile 無人複核就派實作」。adversarial-review 派工本身(--template n/a:)不受此限。
    #   新語義:--reconcile 提供時檢 reconcile 單檔;未提供時對 --adversarial foreach(舊式 reconcile 內嵌戳記)。
    #   戳記檢查：H1-H7 通用 waived 語義不變（waived 略過 stamp）。
    #   Completeness（BC2）：convergence session 不受 waived 跳過——呼叫在 case 外；
    #     _run_completeness_gate 內部以 handoffs/reconcile/<session>/ 結構判定，非 convergence → 略過。
    if [ -n "${spec}" ]; then
      case "${adversarial}" in
        ""|waived:*|stamped-waived:*) : ;;
        *)
          if [ -n "${reconcile}" ]; then
            case "${reconcile}" in
              waived:*|stamped-waived:*) : ;;
              *)
                _stamp_bin="${RECONCILE_STAMPS_CHECK_OVERRIDE:-${SCRIPT_DIR}/reconcile_stamps_check.sh}"
                bash "${_stamp_bin}" "${reconcile}" \
                  || { echo "ERROR: reconcile 未獲委員核可（見上），拒發實作 token。委員須在 reconcile append RECONCILE-STAMP APPROVED。"; exit 1; }
                ;;
            esac
          else
            _foreach_adversarial "${adversarial}" _run_reconcile_stamp_check_adv \
              || { echo "ERROR: reconcile 未獲委員核可（見上），拒發實作 token。委員須在 reconcile append RECONCILE-STAMP APPROVED。"; exit 1; }
          fi
          ;;
      esac
      # Task 3.2 / BC2：spec dispatch 一律嘗試 completeness（路徑/結構閘在函式內）
      # 即使 --adversarial waived: 也須對 convergence session 跑完整性
      _comp_src=""
      if [ -n "${reconcile}" ]; then
        case "${reconcile}" in
          waived:*|stamped-waived:*) : ;;
          *) _comp_src="${reconcile}" ;;
        esac
      fi
      if [ -z "${_comp_src}" ] && [ -n "${adversarial}" ]; then
        case "${adversarial}" in
          waived:*|stamped-waived:*|"") : ;;
          *) _comp_src="${adversarial%%,*}" ;;
        esac
      fi
      if [ -n "${_comp_src}" ]; then
        _run_completeness_gate "${_comp_src}" \
          || { echo "ERROR: completeness gate 未過（見上），拒發實作 token。"; exit 1; }
      fi
    fi
    # 高風險「對 SPEC 派工」必須附 --spec 且機檢合規（template 漏結構=擋）
    case "${template}" in
      n/a:*|N/A:*) : ;;  # 明確非 spec 派工（如 adversarial review 本身）才可豁免
      *) [ -n "${spec}" ] || miss spec "高風險對 SPEC 派工必填 --spec <SPEC路徑>（非 spec 派工 --template 填 n/a:理由）" ;;
    esac
  fi
  # Review-quorum 閘(2026-07-15 使用者定,scar:單家 review 連錯三批):中/大實作 batch N≥1 派工前,
  #   前一批須 ≥2 個「非實作者」家族 code review(ORCH §1「code review=Codex+Composer 雙家」)。
  #   從 impl task_id 自動推導(<root>-impl-b<N>-<impl_family>),無 flag 可繞、憑印象也擋得住。
  case "${task_id}" in
    *-impl-b[0-9]*-*)
      _rq_fam="${task_id##*-}"
      _rq_rest="${task_id%-*}"
      _rq_bN="${_rq_rest##*-}"
      _rq_root="${_rq_rest%-impl-*}"
      _rq_n="${_rq_bN#b}"
      if printf '%s' "${_rq_n}" | grep -qE '^[0-9]+$' && [ "${_rq_n}" -ge 1 ]; then
        # 往下找真正的前一批:descoped 批次(audit 無該 batch review 派工)跳過,避免誤擋(如 FR/B5 descope→B6 的前批實為 B4)
        _rq_p=$(( _rq_n - 1 )); _rq_prev=""
        while [ "${_rq_p}" -ge 0 ]; do
          _rq_cand="${_rq_root}-b${_rq_p}"
          if grep -q "\"task_id\": \"${_rq_cand}-review" "${AUDIT}" 2>/dev/null; then _rq_prev="${_rq_cand}"; break; fi
          _rq_p=$(( _rq_p - 1 ))
        done
        if [ -n "${_rq_prev}" ]; then
          bash "${SCRIPT_DIR}/review_quorum_check.sh" "${_rq_prev}" "${_rq_fam}" \
            || { echo "GATE 拒發 token — 前一批 ${_rq_prev} 未達雙家 review quorum(ORCH §1 code review=Codex+Composer);見上,補派第二家後再派本批。"; exit 1; }
        fi
      fi
      ;;
  esac
  # 範本錨點機檢（提供即驗，不合規拒發 token）—— 把「有沒有照範本」變機器可驗
  if [ -n "${spec}" ]; then
    bash scripts/template_check.sh spec "${spec}" || { echo "ERROR: SPEC 未過範本機檢（見上），拒發 token。"; exit 1; }
    [ -n "${manifest}" ] && { bash scripts/coverage_check.sh "${manifest}" "${spec}" || { echo "ERROR: SPEC 漏 manifest 項（見上），拒發 token。"; exit 1; }; }
  fi
  if [ -n "${todo}" ]; then
    bash scripts/template_check.sh todo "${todo}" || { echo "ERROR: TODO 未過範本機檢（見上），拒發 token。"; exit 1; }
    [ -n "${manifest}" ] && { bash scripts/coverage_check.sh "${manifest}" "${todo}" || { echo "ERROR: TODO 漏 manifest 項（見上），拒發 token。"; exit 1; }; }
  fi
  if [ -z "${missing}" ] && [ -n "${task_id}" ]; then
    if [ "${risk}" != "high" ] || [ -z "${adversarial}" ] || [ ! -f "${adversarial}" ]; then
      _append_committee_dispatch_any "${output_path}" "${task_id}"
      export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"
    elif [ -n "${output_path}" ] && [ "${output_path}" != "${adversarial}" ]; then
      _append_committee_dispatch_any "${output_path}" "${task_id}"
      export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"
    fi
  fi
elif [ "${kind}" = "artifact" ]; then
  [ -n "${file}" ]            || miss file            "目標治理文件路徑"
  [ -n "${template_opened}" ] || miss template-opened "已打開的 canonical template 路徑"
  [ -n "${sections}" ]        || miss sections        "必填章節覆蓋陳述（含 §G Golden 狀態 + 各 N/A 理由）"
  if [ -n "${template_opened}" ] && [ ! -f "${template_opened}" ]; then
    echo "ERROR: --template-opened 檔不存在:${template_opened}（真實檢查失敗）"; exit 1
  fi
fi

if [ -n "${missing}" ]; then
  echo "GATE 拒發 token — 缺以下必填："; printf "%b" "${missing}"
  _print_usage
  exit 1
fi

token="${GATE_DIR}/${kind}.token"; ts="$(date '+%Y-%m-%d %H:%M:%S')"
{
  echo "ts=${ts}"; echo "kind=${kind}"
  echo "intent=${intent}"; echo "risk=${risk}"; echo "facts_asked=${facts_asked}"
  echo "review_role=${review_role}"; echo "template=${template}"; echo "adversarial=${adversarial}"
  echo "reconcile=${reconcile}"
  echo "file=${file}"; echo "template_opened=${template_opened}"; echo "sections=${sections}"
  echo "spec=${spec}"; echo "todo=${todo}"; echo "manifest=${manifest}"
} > "${token}"
cat "${token}" | sed 's/^/  /' | { echo "=== ${ts} | ${kind} ==="; cat; } >> "${AUDIT}"

echo "GATE PASS：已發 ${kind} token（有效 900s）。審計 → ${AUDIT}"
echo "使用者可稽核：cat ${AUDIT}"
