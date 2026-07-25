#!/usr/bin/env bash
# ci_check_after_push.sh — PostToolUse hook(Bash):偵測 git push 後自動查 GitHub CI 結果。
# 為何存在(2026-07-02 使用者要求):三關卡中 PreToolUse/git hooks 天生自動,唯 CI 靠
# 「Claude 記得去查」=會漏。本 hook 讓 push 後 CI 結果自動餵回 Claude context,紅燈藏不住。
#
# 2026-07-25 擴充:原只查 verify_claim.yml → 改**查 WATCHED_WORKFLOWS 清單**。
#   事故:governance.yml(287 守衛測試)紅了 hook 卻不報,我得手動 gh run list 才發現
#   跨平台(BSD/GNU realpath)bug——最該自動回饋的 workflow 反而沒被監看。
#   **新增 workflow 只需在 WATCHED_WORKFLOWS 加一行**(格式 <file>|<顯示名>)。
#   刻意不含 l65_benchmark.yml(既有長期紅、與治理無關,加了只會製造雜訊)。
# 誠實邊界:gh/token 不可用時輸出明確警告(非靜默跳過);逾時只提示不阻塞。
set -u

# --- 監看清單(擴充點) -------------------------------------------------------
WATCHED_WORKFLOWS="verify_claim.yml|Verify Claim
governance.yml|Governance"
DEADLINE_SECS=200   # governance 實測 ~60-75s;留餘裕
# ---------------------------------------------------------------------------

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

# 尚未出結果的 workflow(bash 3.2:用換行分隔字串,不用關聯陣列)
pending="${WATCHED_WORKFLOWS}"
any_fail=0

deadline=$((SECONDS + DEADLINE_SECS))
while [ -n "${pending}" ] && [ ${SECONDS} -lt ${deadline} ]; do
  still_pending=""
  while IFS= read -r entry; do
    [ -n "${entry}" ] || continue
    wf="${entry%%|*}"; label="${entry#*|}"
    line="$(gh run list -R "${repo}" --workflow="${wf}" --limit 5 \
      --json headSha,status,conclusion \
      --jq ".[] | select(.headSha==\"${head_sha}\") | .status+\"|\"+(.conclusion//\"\")" 2>/dev/null | head -1)"
    if [ -n "${line}" ]; then
      status="${line%%|*}"; conclusion="${line#*|}"
      if [ "${status}" = "completed" ]; then
        if [ "${conclusion}" = "success" ]; then
          echo "[CI-CHECK] ✅ ${label} PASS (${head_sha:0:7})"
        else
          any_fail=1
          run_id="$(gh run list -R "${repo}" --workflow="${wf}" --limit 5 \
            --json headSha,databaseId --jq ".[] | select(.headSha==\"${head_sha}\") | .databaseId" 2>/dev/null | head -1)"
          echo "[CI-CHECK] ❌ ${label} ${conclusion} (${head_sha:0:7}) — 診斷:gh run view -R ${repo} ${run_id} --log-failed"
        fi
        continue   # 這個 workflow 已結案,不再 pending
      fi
    fi
    still_pending="${still_pending}${entry}
"
  done <<EOF
${pending}
EOF
  pending="$(printf '%s' "${still_pending}" | sed '/^$/d')"
  [ -n "${pending}" ] || break
  sleep 10
done

if [ -n "${pending}" ]; then
  while IFS= read -r entry; do
    [ -n "${entry}" ] || continue
    echo "[CI-CHECK] ⏳ ${DEADLINE_SECS}s 內未取得 ${entry#*|} (${head_sha:0:7}) 結果 — 請稍後 gh run list 確認"
  done <<EOF
${pending}
EOF
fi

[ "${any_fail}" -eq 0 ] || echo "[CI-CHECK] ⚠️ 有 workflow 未通過 — 修好再繼續(勿當作已完成)"
exit 0
