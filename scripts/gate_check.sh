#!/usr/bin/env bash
# gate_check.sh — PreToolUse hook backstop (fail-closed dispatch/artifact gate).
#
# 哲學（見 docs/MULTI_AGENT_ORCHESTRATION.md「Gate」節）：
#   守「通道」不守「實例」。委派只有兩個通道：Task 工具(全涵蓋) 與 Bash(executor pattern)。
#   治理文件創建走 Write。沒有對應 fresh token → exit 2 擋下（fail-closed），
#   讓 Claude 無法靜默跳過 committee/template/adversarial 檢查。
#
# 誠實邊界：本 gate 不驗證 token 內聲稱為真，只保證「沒跑 gate 就不能派工/創檔」+ 留審計痕跡。
#
# 退出碼：0=放行；2=擋下（stderr 回饋給 Claude）。parse 失敗 fail-open(0) 避免鎖死 session。

set -u
TTL_SECONDS=900   # token 有效 15 分鐘；過期需重跑 gate（防舊 token 綠燈無關的後續派工）
GATE_DIR=".claude/gate"

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
    if printf '%s' "$cmd" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|agy)[[:space:]]|claude[^|]*(-p|--print)'; then
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
if [ -f "$token" ]; then
  now="$(date +%s)"; mtime="$(stat -f %m "$token" 2>/dev/null || stat -c %Y "$token" 2>/dev/null || echo 0)"
  if [ $(( now - mtime )) -le "$TTL_SECONDS" ]; then
    exit 0   # fresh token → 放行
  fi
fi

# fail-closed：擋下，告訴 Claude 怎麼開門
cat >&2 <<EOF
[GATE BLOCKED] 偵測到 kind=${kind} 高風險動作 (tool=${tool_name})，但無 fresh gate token。
此動作把工作交給執行者 / 創建治理文件，必須先過 gate (不可靜默跳過)。
請先跑：  bash scripts/gate.sh ${kind}   (它會列出必填檢查清單並指出缺什麼)
gate 通過會寫 token + 審計到 ${GATE_DIR}/，使用者可稽核。token 有效 ${TTL_SECONDS}s。
EOF
exit 2
