#!/usr/bin/env bash
# gate.sh — mint a fail-closed gate token after recording a mandatory checklist.
# bash 3.2 相容（macOS 預設）：不使用 declare -A。
#
# 用法：
#   bash scripts/gate.sh dispatch --intent "..." --risk low|high \
#        --facts-asked "..." --review-role "..." --template "..." [--adversarial PATH|waived:reason]
#   bash scripts/gate.sh artifact --file docs/X_SPEC.md \
#        --template-opened templates/SPEC_TEMPLATE.md --sections "§1.4 Golden=filled; §0.A=N/A:..."
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

kind="${1:-}"; shift || true
[ "${kind}" = "dispatch" ] || [ "${kind}" = "artifact" ] || { echo "ERROR: kind 必須是 dispatch|artifact"; exit 1; }

intent=""; risk=""; facts_asked=""; review_role=""; template=""; adversarial=""
task_id=""
file=""; template_opened=""; sections=""; spec=""; todo=""; manifest=""
while [ $# -gt 0 ]; do
  case "$1" in
    --intent)          intent="${2:-}"; shift 2 ;;
    --risk)            risk="${2:-}"; shift 2 ;;
    --facts-asked)     facts_asked="${2:-}"; shift 2 ;;
    --review-role)     review_role="${2:-}"; shift 2 ;;
    --template)        template="${2:-}"; shift 2 ;;
    --adversarial)     adversarial="${2:-}"; shift 2 ;;
    --task-id)         task_id="${2:-}"; shift 2 ;;
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
_append_committee_dispatch() {
  local adv_path="$1"
  local tid="$2"
  [ -n "${tid}" ] || return 0
  [ -f "${adv_path}" ] || return 0
  local dispatch_ts out_rel family output_sha256
  dispatch_ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
  out_rel="${adv_path}"
  case "${out_rel}" in
    /*)
      case "${out_rel}" in
        *handoffs/*) out_rel="handoffs/${out_rel#*handoffs/}" ;;
        *docs/*) out_rel="docs/${out_rel#*docs/}" ;;
      esac
      ;;
  esac
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
  output_sha256="$(
    "${VENV_PY}" -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' \
      "${adv_path}"
  )"
  printf '%s\n' \
    "{\"event\":\"committee_dispatch\",\"task_id\":\"${tid}\",\"family\":\"${family}\",\"output_path\":\"${out_rel}\",\"output_sha256\":\"${output_sha256}\",\"ts\":\"${dispatch_ts}\"}" \
    >> "${AUDIT}"
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
        [ -f "${adversarial}" ] || { echo "ERROR: --adversarial 檔不存在:${adversarial}（真實檢查失敗）"; exit 1; }
        # R7：先記錄 committee_dispatch，供後續 reconcile/adversarial provenance 機檢
        case "${adversarial}" in
          waived:*|n/a:*|N/A:*|stamped-waived:*) : ;;
          *)
            if [ -n "${task_id}" ]; then
              _append_committee_dispatch "${adversarial}" "${task_id}"
              export VERIFY_GATE_COMMITTEE_AUDIT_LOG="${AUDIT}"
            fi
            ;;
        esac
        # W3 fail-closed：須為 ADV 命名+provenance，或 reconcile 戳記核可；其他路徑一律拒發 token
        case "${adversarial}" in
          handoffs/*-ADV-CODEX.md|handoffs/*-ADV-COMPOSER.md|handoffs/*-adv-codex.md|handoffs/*-adv-composer.md)
            "${VENV_PY}" "${SCRIPT_DIR}/verify_task_provenance.py" check-adversarial "${adversarial}" \
              || { echo "ERROR: adversarial provenance 檢查失敗（見上），拒發 token。"; exit 1; }
            ;;
          *)
            bash "${SCRIPT_DIR}/reconcile_stamps_check.sh" "${adversarial}" \
              || { echo "ERROR: --adversarial 既非 ADV 命名亦未獲 reconcile 戳記核可（見上），拒發 token。"; exit 1; }
            ;;
        esac
        ;;
    esac
    # reconcile 核可閘:對 SPEC 派「實作」(--spec 存在)時,--adversarial 指向的 reconcile 須獲委員戳記
    #   防「Claude 自產 reconcile 無人複核就派實作」。adversarial-review 派工本身(--template n/a:)不受此限。
    if [ -n "${spec}" ]; then
      case "${adversarial}" in
        ""|waived:*|stamped-waived:*) : ;;
        *) bash scripts/reconcile_stamps_check.sh "${adversarial}" || { echo "ERROR: reconcile 未獲委員核可（見上），拒發實作 token。委員須在 reconcile append RECONCILE-STAMP APPROVED。"; exit 1; } ;;
      esac
    fi
    # 高風險「對 SPEC 派工」必須附 --spec 且機檢合規（template 漏結構=擋）
    case "${template}" in
      n/a:*|N/A:*) : ;;  # 明確非 spec 派工（如 adversarial review 本身）才可豁免
      *) [ -n "${spec}" ] || miss spec "高風險對 SPEC 派工必填 --spec <SPEC路徑>（非 spec 派工 --template 填 n/a:理由）" ;;
    esac
  fi
  # 範本錨點機檢（提供即驗，不合規拒發 token）—— 把「有沒有照範本」變機器可驗
  if [ -n "${spec}" ]; then
    bash scripts/template_check.sh spec "${spec}" || { echo "ERROR: SPEC 未過範本機檢（見上），拒發 token。"; exit 1; }
    [ -n "${manifest}" ] && { bash scripts/coverage_check.sh "${manifest}" "${spec}" || { echo "ERROR: SPEC 漏 manifest 項（見上），拒發 token。"; exit 1; }; }
  fi
  if [ -n "${todo}" ]; then
    bash scripts/template_check.sh todo "${todo}" || { echo "ERROR: TODO 未過範本機檢（見上），拒發 token。"; exit 1; }
    [ -n "${manifest}" ] && { bash scripts/coverage_check.sh "${manifest}" "${todo}" || { echo "ERROR: TODO 漏 manifest 項（見上），拒發 token。"; exit 1; }; }
  fi
elif [ "${kind}" = "artifact" ]; then
  [ -n "${file}" ]            || miss file            "目標治理文件路徑"
  [ -n "${template_opened}" ] || miss template-opened "已打開的 canonical template 路徑"
  [ -n "${sections}" ]        || miss sections        "必填章節覆蓋陳述（含 §1.4 Golden 狀態 + 各 N/A 理由）"
  if [ -n "${template_opened}" ] && [ ! -f "${template_opened}" ]; then
    echo "ERROR: --template-opened 檔不存在:${template_opened}（真實檢查失敗）"; exit 1
  fi
fi

if [ -n "${missing}" ]; then
  echo "GATE 拒發 token — 缺以下必填："; printf "%b" "${missing}"; exit 1
fi

token="${GATE_DIR}/${kind}.token"; ts="$(date '+%Y-%m-%d %H:%M:%S')"
{
  echo "ts=${ts}"; echo "kind=${kind}"
  echo "intent=${intent}"; echo "risk=${risk}"; echo "facts_asked=${facts_asked}"
  echo "review_role=${review_role}"; echo "template=${template}"; echo "adversarial=${adversarial}"
  echo "file=${file}"; echo "template_opened=${template_opened}"; echo "sections=${sections}"
  echo "spec=${spec}"; echo "todo=${todo}"; echo "manifest=${manifest}"
} > "${token}"
cat "${token}" | sed 's/^/  /' | { echo "=== ${ts} | ${kind} ==="; cat; } >> "${AUDIT}"

echo "GATE PASS：已發 ${kind} token（有效 900s）。審計 → ${AUDIT}"
echo "使用者可稽核：cat ${AUDIT}"
