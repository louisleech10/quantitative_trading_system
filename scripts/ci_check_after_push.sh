#!/usr/bin/env bash
# ci_check_after_push.sh — PostToolUse hook(Bash):偵測 git push 後自動查 GitHub CI 結果。
# 為何存在(2026-07-02 使用者要求):三關卡中 PreToolUse/git hooks 天生自動,唯 CI 靠
# 「Claude 記得去查」=會漏。本 hook 讓 push 後 CI 結果自動餵回 Claude context,紅燈藏不住。
# 誠實邊界:只查 Verify Claim workflow;gh/token 不可用時輸出明確警告(非靜默跳過)。
set -u

input="$(cat)"
# 只攔 git push(其他 Bash 命令直接放行)
cmd="$(printf '%s' "${input}" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null || echo "")"
case "${cmd}" in
  *git\ push*) : ;;
  *) exit 0 ;;
esac

command -v gh >/dev/null 2>&1 || { echo "[CI-CHECK] gh CLI 不存在,無法自動驗 CI — 請手動查 Actions"; exit 0; }

GH_TOKEN="$(printf 'protocol=https\nhost=github.com\n' | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2)"
[ -n "${GH_TOKEN}" ] || { echo "[CI-CHECK] keychain 無 GitHub 憑證,無法自動驗 CI — 請手動查 Actions"; exit 0; }
export GH_TOKEN

head_sha="$(git rev-parse HEAD 2>/dev/null)"
repo="louisleech10/quantitative_trading_system"

# 輪詢至多 120s 等 Verify Claim 對 HEAD 的 run 出結果(CI 實測 ~15s)
deadline=$((SECONDS + 120))
while [ ${SECONDS} -lt ${deadline} ]; do
  line="$(gh run list -R "${repo}" --workflow=verify_claim.yml --limit 5 \
    --json headSha,status,conclusion,displayTitle \
    --jq ".[] | select(.headSha==\"${head_sha}\") | .status+\"|\"+(.conclusion//\"\")+\"|\"+.displayTitle" 2>/dev/null | head -1)"
  if [ -n "${line}" ]; then
    status="${line%%|*}"; rest="${line#*|}"; conclusion="${rest%%|*}"
    if [ "${status}" = "completed" ]; then
      if [ "${conclusion}" = "success" ]; then
        echo "[CI-CHECK] ✅ Verify Claim PASS (${head_sha:0:7})"
      else
        echo "[CI-CHECK] ❌ Verify Claim ${conclusion} (${head_sha:0:7}) — 立即診斷:gh run view -R ${repo} <run-id> --log-failed"
        gh run list -R "${repo}" --workflow=verify_claim.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null | sed 's/^/[CI-CHECK] run-id: /'
      fi
      exit 0
    fi
  fi
  sleep 10
done
echo "[CI-CHECK] ⏳ 120s 內未取得 Verify Claim (${head_sha:0:7}) 結果 — 請稍後 gh run list 確認"
exit 0
