# IC Phase1 1-align — SPEC/TODO Reconcile(R1→R3)

**Task 鏈**:ic1a-align-specadv(R1 雙 REJECT)→ ic1a-align-specadv-r2(Codex APPROVE/Composer REJECT)→ ic1a-align-specadv-r3(雙 APPROVE)
**凍結對象**:docs/IC_PHASE1_1A_ALIGN_SPEC.md v3 + docs/IC_PHASE1_1A_ALIGN_TODO.md v3
**日期**:2026-07-09

## 裁決總表(全文見 SPEC §ADV-RESOLUTION)
- R1 Codex 7 BLOCKING+2 NON-BLOCKING:v2 全 ACCEPT(consumer-map 補全至 10 項/D-2 bar-ordinal/D-3 兩段 freq/D-1 int64 相容/Golden 唯讀/M5 雙腿/Task 1.2 horizon resolver/Phase 3 defer/檔名更正)→ R2 Codex 覆核 9 條全 CLOSED。
- R1 Composer 6 BLOCKING+4 MAJOR+2 NON-BLOCKING:v2 修 12/13 → R2 Composer 抓 v2 新洞(Task 2.4 跨 dtype 交集恆空+index 同型化未定)→ v3 新增 **D-4 同型化寫回**+Task 2.4/2.3 修法 → R3 雙方覆核全 CLOSED,無 STILL-OPEN/NEW-ISSUE BLOCKING。
- 閉合方法:原提出方重跑同一反例(kline gap 腳本/int64∩datetime snippet/TypeError snippet/roundtrip index 型別/D-4 值守恆 sha256),非憑條文信任。
- 實作註記(NON-BLOCKING,入實作派工):Task 1.1 尾端 NaN==lag 檢查須對完整 target/close 軸,非截斷 feature 子集(Codex R2)。

## 過程檔(全部已 gate register-output)
- R1:handoffs/IC1A-ALIGN-SPECADV-{codex,composer}.md
- R2:handoffs/IC1A-ALIGN-SPECADV-R2-{codex,composer}.md
- R3:handoffs/IC1A-ALIGN-SPECADV-R3-{codex,composer}.md

## 戳記
(委員 append:`RECONCILE-STAMP: <codex|composer> APPROVED YYYY-MM-DD sha256:<body_hash> task:<task-id>`;body_hash 用 `bash scripts/reconcile_body_hash.sh handoffs/IC1A-ALIGN-RECONCILE.md` 取得)
RECONCILE-STAMP: codex APPROVED 2026-07-09 sha256:d68783b685bd4bb86437f12684425fa6b932ba21432adddc12ad0239771201f8 task:ic1a-align-stamp
RECONCILE-STAMP: composer APPROVED 2026-07-09 sha256:d68783b685bd4bb86437f12684425fa6b932ba21432adddc12ad0239771201f8 task:ic1a-align-stamp
