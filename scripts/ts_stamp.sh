#!/usr/bin/env bash
# ts_stamp.sh — 工具呼叫耗時哨兵（診斷用，不做任何判斷、永不阻擋）。
#
# 為何存在（2026-07-26 使用者要求）：
#   使用者觀察到多次 Bash 呼叫「5–12 分鐘才開始吐字」。Claude 從內部**無法觀測**
#   「送出呼叫 → 指令開始」與「指令結束 → 開始吐字」這兩段，只能靠猜（且猜錯三次）。
#   本 hook 在 PreToolUse/PostToolUse 各打一個毫秒戳，把時間軸切開：
#
#     ① 送出  ──?──  ② T-IN  ──call 內──  ③ T-OUT  ──?──  ④ 開始吐字
#
#   **使用者不必讀時間戳**：OUT 會自己算 ②→③ 的差，超過門檻就在 UI 跳警告。
#
# 已測得的事實（2026-07-26 受控實驗）：
#   · 命中 permissions.allow 的指令：9/9 全部 < 0.12 秒，零離群值
#   · 未命中的指令：0.056 / 0.069 / 0.084 / 2.37 / 2.63 / **603** 秒
#   · 同一個 awk 指令，加進 allow 前 2.37s+2.27s，加進後 0.054s（**42 倍，且無快取**）
#   → defaultMode="auto" 會把未命中 allow 的指令送 LLM 分類器（≈2.3s/次）。
#   ⚠️ **但 2.3 秒解釋不了 603 秒**。603 秒僅 1 個樣本、未重現、原因**未證明**。
#     本哨兵留著就是為了抓下一次，並記錄它是否落在「未命中 allow」那條路上。
#
# 用法（由 settings.json hooks 呼叫，非人工執行）：
#   bash scripts/ts_stamp.sh IN
#   bash scripts/ts_stamp.sh OUT
#
# 門檻（秒）：TS_STAMP_WARN_SEC，預設 10。
#
# 設計紅線：
#   · **永不阻擋**：全程容錯，結尾強制 exit 0。python3/jq 不在也不影響任何工具呼叫。
#   · **不解析、不判斷**：只讀 stdin 取指令前 60 字當標籤，不做任何 gate 邏輯。
#
# 移除方式：從 .claude/settings.json 的 hooks 拿掉這兩筆，並刪本檔與 log。

LABEL="${1:-?}"
LOG="${TS_STAMP_LOG:-.claude/gate/ts_stamp.log}"
STATE="${TS_STAMP_STATE:-.claude/gate/.ts_stamp_in}"
WARN="${TS_STAMP_WARN_SEC:-10}"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

now_ms="$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)"
now_hms="$(python3 -c 'import datetime;print(datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3])' 2>/dev/null \
          || date '+%H:%M:%S' 2>/dev/null || echo '')"

payload="$(cat 2>/dev/null || true)"
snippet="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null | head -c 60 | tr '\n' ' ' || true)"

msg="⏱ T-${LABEL} ${now_hms}"

if [ "$LABEL" = "IN" ]; then
  printf '%s' "$now_ms" > "$STATE" 2>/dev/null || true
else
  start_ms="$(cat "$STATE" 2>/dev/null || echo 0)"
  case "$start_ms" in ''|*[!0-9]*) start_ms=0 ;; esac
  if [ "$start_ms" -gt 0 ] && [ "$now_ms" -gt 0 ]; then
    delta_ms=$(( now_ms - start_ms ))
    secs="$(python3 -c "print(f'{$delta_ms/1000:.2f}')" 2>/dev/null || echo "?")"
    msg="⏱ T-OUT ${now_hms}｜call 內耗時 ${secs}s"
    # 超過門檻 → 大聲喊，並記下當時的指令，供事後判斷它是否走了分類器那條路
    if [ "$delta_ms" -gt $(( WARN * 1000 )) ]; then
      msg="🐌🐌 **卡頓偵測** call 內耗時 ${secs} 秒（門檻 ${WARN}s）｜指令: ${snippet}｜此為 T-IN→T-OUT 之間，非 Claude 生成時間。詳見 ${LOG}"
      printf '%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "SLOW" "${secs}s" "${snippet}" >> "${LOG}.slow" 2>/dev/null || true
    fi
  fi
fi

printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%d')" "${LABEL} ${now_hms}" "${snippet}" >> "$LOG" 2>/dev/null || true

# jq 負責安全逸出（訊息含引號/中文也不會壞 JSON）；jq 不在就不輸出，同樣不阻擋
printf '%s' "$msg" | jq -Rs '{systemMessage: .}' 2>/dev/null || true

exit 0
