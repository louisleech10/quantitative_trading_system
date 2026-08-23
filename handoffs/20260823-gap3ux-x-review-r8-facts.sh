#!/usr/bin/env bash
# GAP-3 SPEC R8 — fact receipt 產生器（可重跑）
#
# 為何存在（2026-08-22，CODEX consult finding）：R1–R3 的 brief 用「查證＝主委實讀」宣稱事實，
# 委員無法獨立重現、也無法偵測主委讀錯或讀到 stale 版本。本腳本把每條 fact 變成
# 「一條命令 + 其 stdout」，委員可自行重跑並與 brief 內貼的輸出逐字比對。
#
# 用法：bash handoffs/20260822-gap3ux-x-review-r4-facts.sh
# 退出碼：0＝全部 fact 命令成功；非 0＝有 fact 無法重現（此時 brief 之該條不可信）
set -u
# 🔴 CODEX-R5-P1-07：首版未開 pipefail ⇒ `grep <不存在路徑> | sed` 取到的是 sed 的 rc（0），
#    使「14 條 fact 皆可重跑 rc=0」之宣稱不成立。此即 CLAUDE.md 已載之
#    「`cmd | head` 讀到的是 head 的 rc」同一坑，主委在自己的 receipt 工具上再犯。
set -o pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

rc_all=0
n=0

emit() {  # emit <FACT-ID> <說明> <命令>
  n=$((n + 1))
  printf '\n=== %s | %s ===\n$ %s\n' "$1" "$2" "$3"
  # shellcheck disable=SC2086
  eval "$3"
  local rc=$?
  printf '[rc=%d]\n' "$rc"
  [ "$rc" -eq 0 ] || rc_all=1
}

echo "GAP-3 SPEC R8 FACT RECEIPTS"
echo "repo HEAD: $(git rev-parse --short HEAD)  branch: $(git rev-parse --abbrev-ref HEAD)"

emit F-01 "審查標的之 SPEC 指紋（審查期間不得變動）" \
  "shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l < docs/GAP3_EVENT_UX_SPEC.md"

emit F-02 "Phase 7 批次維度在契約中之**完整路徑**、型別與 enum（遞迴搜尋，不預設巢狀層級）" \
  "python3 handoffs/20260823-gap3ux-x-review-r8-dims.py"

emit F-03 "各批次維度之 enum 元素數與 accepted 子集（Task 7.2 之比對基準）" \
  "python3 handoffs/20260823-gap3ux-x-review-r8-dims.py --counts"

emit F-04 "契約之六份 reason／flag 清單長度（Task 1.1 與 1.12 之常數依據）" \
  "python3 -c \"import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));[print(k,len(c[k]),c[k]) for k in ('import_failure_reasons','alignment_failure_reasons','capability_unavailable_reasons','split_purge_reasons','split_loud_flags','degraded_flags')]\""

emit F-05 "dedupe 依 scenario 分流（證明系統本就非單一 scenario）" \
  "grep -n '_POLICY_BY_SCENARIO' -A 8 momentum/Analysis/event_samples/dedupe.py"

emit F-06 "eventExport.ts 各維度寫死位置（Phase 7 之接線缺口）" \
  "grep -n 'decision_offset_bars\|entry_price_semantic\|scenario\|label_return_mode\|control_kind\|counterexample_kind' frontend/src/lib/eventExport.ts"

emit F-07 "/search 呼叫端未傳任何 opts（介面留了、UI 沒做）" \
  "grep -n 'buildEventContractRecords' -A 8 frontend/src/app/search/page.tsx"

emit F-08 "event_forward_return_table 簽章（無 labels 參數 ⇒ Task 7.5 三組為新增行為）" \
  "grep -rn 'def event_forward_return_table' -A 12 momentum/Analysis/event_samples/"

emit F-09 "ic_feed 之 PIT 規則（特徵最晚取至 t0−1 收盤）" \
  "grep -n 'decision_time_rule\|feature_cutoff_rule' momentum/Analysis/event_samples/ic_feed.py"

emit F-10 "analyze_tables 之 horizons 預設（Task 4.2 之改動基準）" \
  "grep -rn 'horizons' momentum/Analysis/event_samples/pipeline.py | head -20"

emit F-11 "future 欄之兩套命名與其小時→根數換算（Task 1.10 之 registry 依據）" \
  "grep -n 'periods_\|future' momentum/DataExtraction/case_search_engine.py | sed -n '1,40p'"

emit F-12 "使用者既有事件批次之實際內容（D-7 洩漏情境是否適用之依據）" \
  "ls -1 data_cache/events/*.json 2>/dev/null | tail -3"

emit F-13 "IC 分析頁與 Feature Library 之 time_range（R3 群集 E 之盤點起點）" \
  "grep -rn 'time_range' frontend/src/app api/routes --include=*.tsx --include=*.ts --include=*.py | head -20"

# 🔴 本條之閘清單在 R6 與 R7 各漏同步一次（新增閘後未更新此處）。
#    根因＝計數稽核閘之掃描面當時未涵蓋本檔；已於 2026-08-23 放寬至所有檔所有語境。
#    ⚠️ 新增任何機械閘時，**必須同時**更新本條之標題與命令。
# 🔴 R8 群集 G（GROK-R8-P1-02／CODEX-R8-P1-05）：本條原以
#    `cmd; echo count_audit=$?` 結尾 ⇒ `emit` 之 `rc=$?` 取到的是 **echo 的 rc（0）**，
#    使 `spec_count_audit` 回 2 時整條仍報 rc=0、`rc_all=0` ⇒「五閘皆 rc=0」之 fact **假綠**。
#    與 CLAUDE.md 已載之「`cmd | head` 讀到的是 head 的 rc；**rc 一律直接取**」同型，主委再犯。
# 🔴 R8 群集 I（COMPOSER-R8-P1-02／GROK-R8-P2-01）：本條原寫死閘數（「五支」），
#    與角色卡／brief／HANDOFF 之字面互斥。
#    ⇒ **閘之權威清單唯一在 `scripts/gap3ux_pre_review.sh`**；本條只呼叫它、不列數字。
emit F-14 "機械閘現況（權威清單見 scripts/gap3ux_pre_review.sh；此處不重述閘數）" \
  "bash scripts/gap3ux_pre_review.sh"

printf '\n=== 總計 %d 條 fact；rc_all=%d ===\n' "$n" "$rc_all"
exit "$rc_all"
