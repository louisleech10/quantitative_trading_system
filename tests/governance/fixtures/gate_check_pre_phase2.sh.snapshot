#!/usr/bin/env bash
# gate_check.sh — PreToolUse hook backstop (fail-closed dispatch/artifact gate).
#
# 哲學（見 docs/MULTI_AGENT_ORCHESTRATION.md「Gate」節）：
#   守「通道」不守「實例」。委派只有兩個通道：Task 工具(全涵蓋) 與 Bash(executor pattern)。
#   治理文件創建走 Write。沒有對應 fresh token → exit 2 擋下（fail-closed），
#   讓 Claude 無法靜默跳過 committee/template/adversarial 檢查。
#
# 誠實邊界：本 gate 不驗證 token 內聲稱為真，只保證「沒跑 gate 就不能派工/創檔」+ 留審計痕跡。
# P1-6 Task 3.1：fresh token 時重查債務帳本（次要補強）。**主擋門是 gate.sh 的
#   _check_open_debt**——本腳本 executor 正則不命中 cx_run/committee_run（SPEC §A 誠實邊界 1）。
#
# 退出碼：0=放行；2=擋下（stderr 回饋給 Claude）。parse 失敗 fail-open(0) 避免鎖死 session。

set -u
TTL_SECONDS=900   # token 有效 15 分鐘；過期需重跑 gate（防舊 token 綠燈無關的後續派工）
GATE_DIR=".claude/gate"
[ -n "${GATE_DIR_OVERRIDE:-}" ] && GATE_DIR="${GATE_DIR_OVERRIDE}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

_append_gate_deny_audit() {
  local reason="$1"
  local tool="$2"
  local kind="$3"
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
  mkdir -p "${GATE_DIR}" 2>/dev/null || true
  { printf '{"event":"gate_deny","ts":"%s","tool":"%s","kind":"%s","reason":"%s"}\n' \
      "$ts" "$tool" "$kind" "$reason"; } >> "${GATE_DIR}/audit.log" 2>/dev/null || true
}

# fresh token 重查帳本（次要補強）。**不使用 sidecar 快取**：
#   - (mtime,size) 鍵不含 cutoff/ledger/registry 語意輸入 → stale allow fail-open（B）
#   - 無完整性保護的 .has_open_idx 可預置毒化 → false-green（C）
#   - 生產路徑 deny 追加寫同一 audit.log → 快取在「有債要擋」時立刻失效（D）
# 效能：直接呼叫 _debt_ledger_core.py（與 debt_ledger --has-open 同語意，省一層 bash）；
#       cold 須 <100ms（SPEC）。
# 回傳 0=無債可放行；非 0=應擋（含 fail-closed）。
_gate_check_recheck_debt() {
  local core_py debt_bin ledger_rc repo
  core_py="${SCRIPT_DIR}/_debt_ledger_core.py"
  debt_bin="${SCRIPT_DIR}/debt_ledger.sh"
  # 優先直呼核心（冷路徑）；缺失時回退 debt_ledger.sh；兩者皆無 → fail-closed
  if [ -f "${core_py}" ]; then
    repo="$(cd "${SCRIPT_DIR}/.." && pwd)"
    DEBT_LEDGER_MODE=has_open \
    DEBT_LEDGER_ROUND_ID= \
    DEBT_LEDGER_REGISTRY="${SCRIPT_DIR}/audit_events.json" \
    DEBT_LEDGER_REPO="${repo}" \
    python3 -S "${core_py}"
    ledger_rc=$?
  elif [ -f "${debt_bin}" ]; then
    bash "${debt_bin}" --has-open
    ledger_rc=$?
  else
    echo "ERROR: debt_ledger 缺失（fail-closed）" >&2
    return 1
  fi
  case "${ledger_rc}" in
    0) return 0 ;;
    *) return 1 ;;
  esac
}

INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0   # 無 jq → fail-open，不鎖死

tool_name="$(jq -r '.tool_name // empty' <<<"$INPUT" 2>/dev/null)" || exit 0
[ -z "$tool_name" ] && exit 0

kind=""
case "$tool_name" in
  Task)
    kind="dispatch"   # Agent 工具：全涵蓋，零列舉
    ;;
  Bash)
    cmd="$(jq -r '.tool_input.command // empty' <<<"$INPUT" 2>/dev/null)"
    # R1：剝除行首 env 前綴（VAR=value 可多個）再比對 executor，防 GATE_DIR_OVERRIDE=… codex exec 繞過。
    while printf '%s' "$cmd" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*='; do
      cmd="$(printf '%s' "$cmd" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+//')"
    done
    # executor 通道：只比對「命令位置」（行首 / 分隔符後）的 binary，避免誤擋 cat sp_codex.txt 這種檔名子字串。
    # executor 名單 = scripts/governance_families.json executor_clis(codex|cursor-agent|grok|agy)。
    # 熱路徑(每次工具呼叫)故此處寫死避免 subprocess 開銷;governance 測試釘死此清單 == SoT(防漂移)。
    # 事故:寫死漏 grok,主力實作 CLI 不被 PreToolUse 攔(2026-07-23)。
    if printf '%s' "$cmd" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'; then
      # 排除 gate 自身與唯讀勘查
      if printf '%s' "$cmd" | grep -Eq 'scripts/gate(_check)?\.sh'; then exit 0; fi
      kind="dispatch"
    fi
    ;;
  Write)
    fp="$(jq -r '.tool_input.file_path // empty' <<<"$INPUT" 2>/dev/null)"
    # 治理文件創建（僅新檔；既有檔用 Edit 迭代不 gate）
    if printf '%s' "$fp" | grep -Eiq '(SPEC|TODO|PLAN).*\.md$' && printf '%s' "$fp" | grep -Eq 'docs/'; then
      [ -f "$fp" ] || kind="artifact"
    fi
    ;;
esac

[ -z "$kind" ] && exit 0   # 非 gated 動作 → 放行

token="$GATE_DIR/${kind}.token"
deny_reason="no_fresh_token"
if [ -f "$token" ]; then
  # mtime 跨平台:linux `stat -c %Y` 前置(linux 上 `stat -f %m` 會失敗且把檔案系統資訊印到 stdout,
  #   混進 mtime 致算術 exit 1;此為本機 macOS 抓不到、僅 CI/linux 現形的事故,2026-07-24)。
  #   各平台第一個 stat 即乾淨成功,第二個不執行。再加數字守衛防非數字。
  now="$(date +%s)"; mtime="$(stat -c %Y "$token" 2>/dev/null || stat -f %m "$token" 2>/dev/null || echo 0)"
  case "$mtime" in ''|*[!0-9]*) mtime=0 ;; esac
  if [ $(( now - mtime )) -le "$TTL_SECONDS" ]; then
    # Task 3.1：fresh token 不再直接放行；重查債務帳本（次要補強，主擋門=gate.sh）
    if _gate_check_recheck_debt; then
      exit 0
    fi
    deny_reason="open_debt"
    _append_gate_deny_audit "$deny_reason" "$tool_name" "$kind"
    cat >&2 <<EOF
[GATE BLOCKED] kind=${kind} 有 fresh token，但債務帳本重查未通過（OPEN 債或帳本不可信）。
主擋門是 gate.sh 的 _check_open_debt；本重查為次要補強。
請先銷帳或 abandon 後重跑：  bash scripts/gate.sh ${kind}
EOF
    exit 2
  fi
  deny_reason="token_expired"
fi

_append_gate_deny_audit "$deny_reason" "$tool_name" "$kind"

# fail-closed：擋下，告訴 Claude 怎麼開門
cat >&2 <<EOF
[GATE BLOCKED] 偵測到 kind=${kind} 高風險動作 (tool=${tool_name})，但無 fresh gate token。
此動作把工作交給執行者 / 創建治理文件，必須先過 gate (不可靜默跳過)。
請先跑：  bash scripts/gate.sh ${kind}   (它會列出必填檢查清單並指出缺什麼)
gate 通過會寫 token + 審計到 ${GATE_DIR}/，使用者可稽核。token 有效 ${TTL_SECONDS}s。
EOF
exit 2
