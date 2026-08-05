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

# 命令欄：全文 sha256 ＋ 前 512 位元組（stdout: <sha256>\t<head512>）。
# 僅在 deny 路徑呼叫；結果不得回饋進判定（D-12）。
_gate_deny_cmd_fields() {
  local cmd="${1-}"
  local sha head
  if command -v sha256sum >/dev/null 2>&1; then
    sha="$(printf '%s' "$cmd" | sha256sum | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    sha="$(printf '%s' "$cmd" | shasum -a 256 | awk '{print $1}')"
  else
    sha="$(printf '%s' "$cmd" | openssl dgst -sha256 2>/dev/null | awk '{print $NF}')"
  fi
  # head -c：取前 512 位元組（非字元）；空命令 → 空 head
  head="$(printf '%s' "$cmd" | head -c 512 2>/dev/null || true)"
  printf '%s\t%s\n' "${sha:-}" "${head}"
}

# 僅 deny 路徑：由已定案的 deny_reason + cmd 推 match_rule，並取命中片段。
# 🔴 grep -Eo 只在此發生，結果不得回饋判定。
# stdout: <match_rule>\t<frag>
_gate_deny_match_info() {
  local deny_reason="${1-}"
  local cmd="${2-}"
  local mr="unknown"
  local frag=""
  case "$deny_reason" in
    open_debt) mr="open_debt" ;;
    token_expired) mr="token_expired" ;;
    *)
      if [ -n "$cmd" ]; then
        if printf '%s' "$cmd" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]'; then
          mr="family_cli"
          frag="$(printf '%s' "$cmd" | LC_ALL=C grep -Eo '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]' 2>/dev/null | head -1)" || frag=""
        elif printf '%s' "$cmd" | grep -Eq 'claude[^|]*(-p|--print)'; then
          mr="claude_agent"
          frag="$(printf '%s' "$cmd" | LC_ALL=C grep -Eo 'claude[^|]*(-p|--print)' 2>/dev/null | head -1)" || frag=""
        fi
      fi
      ;;
  esac
  printf '%s\t%s\n' "$mr" "$frag"
}

# $1=reason $2=tool $3=kind $4=cmd(可空) $5=match_rule
# 既有 tool/kind 保留（test_gate_deny_audit 基線）；新增 match_rule/cmd_sha256/cmd_head。
_append_gate_deny_audit() {
  local reason="$1"
  local tool="$2"
  local kind="$3"
  local cmd="${4-}"
  local match_rule="${5:-unknown}"
  local ts fields cmd_sha cmd_head line
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
  mkdir -p "${GATE_DIR}" 2>/dev/null || true

  fields="$(_gate_deny_cmd_fields "$cmd")"
  cmd_sha="${fields%%	*}"
  cmd_head="${fields#*	}"

  # jq 組 JSON（換行／控制字元安全）；失敗時降級為無 cmd_head 的最小行
  line="$(jq -nc \
    --arg ts "$ts" \
    --arg tool "$tool" \
    --arg kind "$kind" \
    --arg reason "$reason" \
    --arg match_rule "$match_rule" \
    --arg cmd_sha256 "$cmd_sha" \
    --arg cmd_head "$cmd_head" \
    '{event:"gate_deny",ts:$ts,tool:$tool,kind:$kind,reason:$reason,match_rule:$match_rule,cmd_sha256:$cmd_sha256,cmd_head:$cmd_head}' 2>/dev/null)" || line=""

  if [ -z "$line" ]; then
    line="$(printf '{"event":"gate_deny","ts":"%s","tool":"%s","kind":"%s","reason":"%s","match_rule":"%s","cmd_sha256":"%s","cmd_head":""}' \
      "$ts" "$tool" "$kind" "$reason" "$match_rule" "$cmd_sha")"
  fi

  # 邊界③：單行 ≤1 KB；超長則縮 cmd_head 重組
  if [ "${#line}" -gt 1024 ]; then
    cmd_head=""
    line="$(jq -nc \
      --arg ts "$ts" \
      --arg tool "$tool" \
      --arg kind "$kind" \
      --arg reason "$reason" \
      --arg match_rule "$match_rule" \
      --arg cmd_sha256 "$cmd_sha" \
      --arg cmd_head "$cmd_head" \
      '{event:"gate_deny",ts:$ts,tool:$tool,kind:$kind,reason:$reason,match_rule:$match_rule,cmd_sha256:$cmd_sha256,cmd_head:$cmd_head}' 2>/dev/null)" \
      || line="$(printf '{"event":"gate_deny","ts":"%s","tool":"%s","kind":"%s","reason":"%s","match_rule":"%s","cmd_sha256":"%s","cmd_head":""}' \
        "$ts" "$tool" "$kind" "$reason" "$match_rule" "$cmd_sha")"
  fi

  { printf '%s\n' "$line"; } >> "${GATE_DIR}/audit.log" 2>/dev/null || true
}


# GOVB0 詞法契約實作見 scripts/_gate_lex.sh（僅 Bash 路徑 source，避免 Task 冷路徑解析 awk）

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
cmd=""   # Bash 才填；缺失時 audit 寫空字串（不得缺欄）
case "$tool_name" in
  Task)
    kind="dispatch"   # Agent 工具：全涵蓋，零列舉
    ;;
  Bash)
    cmd="$(jq -r '.tool_input.command // empty' <<<"$INPUT" 2>/dev/null)"
    # R1：剝除行首 env 前綴（VAR=value 可多個）再比對 executor，防 GATE_DIR_OVERRIDE=… codex exec 繞過。
    # 🔴 值限「簡單字面」（不含 $ ` ( ) 空白）——避免把 out=$(codex exec x) 誤剝成 exec x)（E-3 回歸）。
    while printf '%s' "$cmd" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_./:@%+=,-]+[[:space:]]'; do
      cmd="$(printf '%s' "$cmd" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_./:@%+=,-]+[[:space:]]+//')"
    done
    # executor 通道：只比對「命令位置」（行首 / 分隔符後）的 binary，避免誤擋 cat sp_codex.txt 這種檔名子字串。
    # executor 名單 = scripts/governance_families.json executor_clis(codex|cursor-agent|grok|agy)。
    # 熱路徑(每次工具呼叫)故此處寫死避免 subprocess 開銷;governance 測試釘死此清單 == SoT(防漂移)。
    # 事故:寫死漏 grok,主力實作 CLI 不被 PreToolUse 攔(2026-07-23)。
    # 🔴 判定段：只做 grep -Eq，禁止 grep -Eo（D-12：取片段不得入判定）。
    # 延遲載入詞法（熱路徑只在 Bash 通道付出）
    # shellcheck source=scripts/_gate_lex.sh
    # 突變測試常只複製 gate_check.sh：若 SCRIPT_DIR 無 lex，回退到本檔同目錄失敗後用 repo 相對 scripts/
    if [ -f "${SCRIPT_DIR}/_gate_lex.sh" ]; then
      # shellcheck source=scripts/_gate_lex.sh
      . "${SCRIPT_DIR}/_gate_lex.sh"
    elif [ -f "scripts/_gate_lex.sh" ]; then
      # cwd=repo root（pytest 慣例）
      # shellcheck source=scripts/_gate_lex.sh
      . "scripts/_gate_lex.sh"
    else
      echo "ERROR: _gate_lex.sh missing (fail-closed dispatch scan)" >&2
      exit 2
    fi
    # GOVB0 Task 2.1：詞法前處理後判定（契約 1／1b／2／3／…）；GATE_LEGACY_DECISION=1 回舊路徑。
    # 錨點字面（覆蓋斷言機械導出）：(codex|cursor-agent|grok|agy)[[:space:]] 與 claude[^|]*(-p|--print)
    # 分隔符前綴（舊＋擴充）：(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)
    if [ "${GATE_LEGACY_DECISION:-0}" = "1" ]; then
      if printf '%s' "$cmd" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'; then
        if printf '%s' "$cmd" | grep -Eq 'scripts/gate(_check)?\.sh'; then exit 0; fi
        kind="dispatch"
      fi
    elif _gate_cmd_is_dispatch "$cmd"; then
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
    # 先判定、後記錄：match_info 的 grep -Eo 只在 deny 路徑執行
    _mi="$(_gate_deny_match_info "$deny_reason" "$cmd")"
    _mr="${_mi%%	*}"
    _append_gate_deny_audit "$deny_reason" "$tool_name" "$kind" "$cmd" "$_mr"
    cat >&2 <<EOF
[GATE BLOCKED] kind=${kind} 有 fresh token，但債務帳本重查未通過（OPEN 債或帳本不可信）。
主擋門是 gate.sh 的 _check_open_debt；本重查為次要補強。
請先銷帳或 abandon 後重跑：  bash scripts/gate.sh ${kind}
EOF
    exit 2
  fi
  deny_reason="token_expired"
fi

# 先判定、後記錄：取片段／match_rule 不入判定主路徑
_mi="$(_gate_deny_match_info "$deny_reason" "$cmd")"
_mr="${_mi%%	*}"
_append_gate_deny_audit "$deny_reason" "$tool_name" "$kind" "$cmd" "$_mr"

# fail-closed：擋下，告訴 Claude 怎麼開門
cat >&2 <<EOF
[GATE BLOCKED] 偵測到 kind=${kind} 高風險動作 (tool=${tool_name})，但無 fresh gate token。
此動作把工作交給執行者 / 創建治理文件，必須先過 gate (不可靜默跳過)。
請先跑：  bash scripts/gate.sh ${kind}   (它會列出必填檢查清單並指出缺什麼)
gate 通過會寫 token + 審計到 ${GATE_DIR}/，使用者可稽核。token 有效 ${TTL_SECONDS}s。
EOF
exit 2
