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

# USER 模式：由 UserPromptSubmit hook 呼叫，只記下「使用者剛送出訊息」的時刻。
# 用途：讓 B 類判定能排除「使用者讀訊息+打字」的時間，只在**真的是 Claude 慢**時才報警。
if [ "$LABEL" = "USER" ]; then
  _um="${TS_STAMP_USER_MARK:-.claude/gate/.ts_stamp_user}"
  mkdir -p "$(dirname "$_um")" 2>/dev/null || true
  python3 -c 'import time;print(int(time.time()*1000))' > "$_um" 2>/dev/null || true
  exit 0
fi
LOG="${TS_STAMP_LOG:-.claude/gate/ts_stamp.log}"
STATE="${TS_STAMP_STATE:-.claude/gate/.ts_stamp_in}"
LAST_OUT="${TS_STAMP_LAST_OUT:-.claude/gate/.ts_stamp_out}"
USER_MARK="${TS_STAMP_USER_MARK:-.claude/gate/.ts_stamp_user}"   # UserPromptSubmit hook 寫入
# A 類=call 內（正常 0.08s，分類器 2.3s）→ 門檻 10s
# B 類=call 之間（結果回到 Claude + Claude 生成；可能夾使用者輸入）→ 門檻 120s
#   2026-08-05 使用者放寬 60→120：60s 在「大輸出回灌 + 長回覆生成」時常態觸發
#   （實測 67.0s 一次即報警，但該次僅是正常的長段生成），訊噪比太低。
#   ⚠️ 誠實邊界：歷史上 git push 全輸出回灌實測 89.9s，**在新門檻下不再報警**。
#   換來的是不再被正常長生成洗版；要抓回那類請設 TS_STAMP_WARN_B_SEC=60。
WARN_A="${TS_STAMP_WARN_A_SEC:-10}"
WARN_B="${TS_STAMP_WARN_B_SEC:-120}"
ALERT=""   # 非空 → 同時注入 Claude context，讓 Claude 自己知道要查

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

now_ms="$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || echo 0)"
now_hms="$(python3 -c 'import datetime;print(datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3])' 2>/dev/null \
          || date '+%H:%M:%S' 2>/dev/null || echo '')"

payload="$(cat 2>/dev/null || true)"
full_cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null | tr '\n' ' ' || true)"
snippet="$(printf '%s' "$full_cmd" | head -c 60 || true)"

msg="⏱ T-${LABEL} ${now_hms}"

if [ "$LABEL" = "IN" ]; then
  # B 類偵測：距「上一個工具呼叫結束」多久 = 結果回到 Claude + Claude 生成（可能夾使用者輸入）
  last_out="$(cat "$LAST_OUT" 2>/dev/null || echo 0)"
  case "$last_out" in ''|*[!0-9]*) last_out=0 ;; esac
  if [ "$last_out" -gt 0 ] && [ "$now_ms" -gt 0 ]; then
    gap_ms=$(( now_ms - last_out ))
    gsec="$(python3 -c "print(f'{$gap_ms/1000:.1f}')" 2>/dev/null || echo "?")"
    # 若這段期間使用者送出過訊息 → 間隔含「使用者讀+打字」，不是 Claude 慢 → 不報警
    user_ms="$(cat "$USER_MARK" 2>/dev/null || echo 0)"
    case "$user_ms" in ''|*[!0-9]*) user_ms=0 ;; esac
    if [ "$user_ms" -gt "$last_out" ]; then
      msg="⏱ T-IN ${now_hms}｜距上次 ${gsec}s（含使用者輸入，不計）"
    elif [ "$gap_ms" -gt $(( WARN_B * 1000 )) ]; then
      msg="⏱ T-IN ${now_hms}｜🐌 **B 類卡頓** 距上次工具結束 ${gsec}s，且**期間使用者未輸入**＝Claude 端慢"
      ALERT="【B 類卡頓・已排除使用者輸入】距上一個工具呼叫結束 ${gsec} 秒才發出本次呼叫，且這段期間使用者**沒有**送出任何訊息——所以這是「結果回到 Claude + Claude 生成」這一段真的慢。請在本回合結尾主動告知使用者實際秒數，並查 ${LOG}.slow。"
      printf '%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "GAP-B" "${gsec}s" "${snippet}" >> "${LOG}.slow" 2>/dev/null || true
    else
      msg="⏱ T-IN ${now_hms}｜距上次 ${gsec}s"
    fi
  fi
  printf '%s' "$now_ms" > "$STATE" 2>/dev/null || true
else
  start_ms="$(cat "$STATE" 2>/dev/null || echo 0)"
  case "$start_ms" in ''|*[!0-9]*) start_ms=0 ;; esac
  if [ "$start_ms" -gt 0 ] && [ "$now_ms" -gt 0 ]; then
    delta_ms=$(( now_ms - start_ms ))
    secs="$(python3 -c "print(f'{$delta_ms/1000:.2f}')" 2>/dev/null || echo "?")"
    msg="⏱ T-OUT ${now_hms}｜call 內耗時 ${secs}s"
    # 超過門檻 → 大聲喊，並記下當時的指令，供事後判斷它是否走了分類器那條路
    # 已知本來就慢的指令（真的在做事，非分類器掛住）→ 不報 A 類，避免誤判淹沒真訊號。
    # git push 會觸發 pre-push 跑 287 個治理測試(~80s)；pytest/委員派工同理。
    # ⚠️ 必須比對**完整指令**，不可用截斷的 snippet：
    #    2026-07-26 實測 bug——`git add ... && git commit ... && git push` 的 push 落在
    #    60 字之後，用 snippet 比對就漏掉，導致正當的 80 秒被誤報成卡頓。
    known_slow=0
    printf '%s' "$full_cmd" | grep -Eq '(git (push|pull|fetch|clone))|pytest|cx_run|committee_run|gov_check|npm (run |install)|pip install' && known_slow=1
    if [ "$known_slow" = "0" ] && [ "$delta_ms" -gt $(( WARN_A * 1000 )) ]; then
      msg="🐌🐌 **A 類卡頓** call 內耗時 ${secs} 秒（門檻 ${WARN_A}s）｜指令: ${snippet}｜此為 T-IN→T-OUT 之間，非 Claude 生成時間"
      ALERT="【A 類卡頓】本次工具呼叫在 call 內耗時 ${secs} 秒（正常 0.08s，分類器 2.3s）。指令: ${snippet}。這是權限分類器路徑掛住的徵兆——請檢查該指令是否觸發三條件之一（未命中 allow／執行任意程式碼／路徑在專案外，見 CLAUDE.md Gotchas），並在本回合結尾主動告知使用者。"
      printf '%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "SLOW-A" "${secs}s" "${snippet}" >> "${LOG}.slow" 2>/dev/null || true
    fi
  fi
fi

[ "$LABEL" = "OUT" ] && { printf '%s' "$now_ms" > "$LAST_OUT" 2>/dev/null || true; }
printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%d')" "${LABEL} ${now_hms}" "${snippet}" >> "$LOG" 2>/dev/null || true

# jq 負責安全逸出（訊息含引號/中文也不會壞 JSON）；jq 不在就不輸出，同樣不阻擋。
# 慢事件才把 additionalContext 注入 Claude context——正常呼叫不注入，避免每次都佔 context。
if [ -n "$ALERT" ]; then
  ev="PostToolUse"; [ "$LABEL" = "IN" ] && ev="PreToolUse"
  jq -n --arg m "$msg" --arg a "$ALERT" --arg e "$ev" \
     '{systemMessage:$m, hookSpecificOutput:{hookEventName:$e, additionalContext:$a}}' 2>/dev/null || true
else
  printf '%s' "$msg" | jq -Rs '{systemMessage: .}' 2>/dev/null || true
fi

exit 0
