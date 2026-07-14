# IC1C SPEC r4 閉合重驗 — codex
標的:`docs/IC1C_NETIC_SPEC.md` v0.4；日期:2026-07-14；reconcile 現值 sha256:`3c50083c2bf693400f7ddf106bf940f6001c5d24294abf6c2ed97ca96af80879`。

## r3 四條 BLOCKING 原反例重跑
- **CODEX-7 CLOSED** — §V M4:129 現要求 T4 同檔 `test_mutation_m4_frontend_drop_cost`；:137 另列 `npm run test -- NetICChart` 驗收且明示 Python checker 不覆蓋 T4。破壞前端 request builder、保留後端 passthrough 時，T4 probe 必紅。
- **CODEX-R3-1 CLOSED** — §U:34 明定 union 僅約束 profile 中存在的鍵，:35-39 精確集合唯一決定 presence；同一 GROSS_ONLY 結果不再同時被要求含/不含 breakeven、profitable。
- **CODEX-R3-2 CLOSED** — 階梯 `{c/2,c,2c,5c}` 已移至 §T:30 並由 Phase 1 :84 實作/:113 驗；Phase 3 :111-113 僅 UI 註記且要求 feature 輸出 byte 等值，原無 oracle/偷跨 phase 反例不成立。
- **CODEX-R3-3 CLOSED** — §U:36/:41 凍 cost_bps finite/range 三層拒絕與非有限 turnover→SKIPPED；M10:130 納入反例。NaN/inf 不再有合法路徑落入裸數值欄。

## r4 delta 新洞
- **CODEX-R4-1（BLOCKING）— `cost_bps=0` 契約自相矛盾。** §U:41 規定合法域 `0 < cost_bps ≤ 1000` 且 config/API/analyzer 全拒絕 0；但 Task 1.1:89 又要求 `cost=0(drag=0)`，§V:141 也把 `cost=0` 勾為已覆蓋邊界。同一 direct-analyzer 輸入依 :41 應 raise、依 :89 應回 0，無唯一實作/測試 oracle。須裁定 0 合法或非法並同步三處。
- **CODEX-R4-2（BLOCKING）— 新三層 validator claim 無三層可證偽覆蓋。** §U:41 聲稱 config schema/API/analyzer 三層一致；M10:130 只有 T1 analyzer 與 T2 API 測試、沒有 config schema direct test，且 probe 只有 T1 `test_mutation_m10_drop_finite_guard`。移除 config validator 無指定測試會紅；移除 API validator 時 T2 雖應紅，卻無 T2 同檔 probe，重現 CODEX-7 的「一個路徑 probe 代證另一個路徑」缺口，亦不符 §V:120/B1.1。須為三層各列具名 test，並為 T2/config correctness 路徑配置同檔自證 probe（或有據降級/N/A）。

ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF/CLAUDE/SPEC v0.4/r3 codex/reconcile；逐條重跑 4 個原反例；以 TEST_DESIGN_CHARTER B1.1/B8 與現有 mutation checker 範圍核 r4 delta。
TESTS_RUN: `nl -ba docs/IC1C_NETIC_SPEC.md`→151 行逐行核對；`rg -n 'cost_sensitivity|SCHEMA_|finite|test_mutation_m4_frontend|G-NEW2' ...`→確認四條閉合落點及兩個新衝突；`shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md`→`3c50083c...af80879`。review-only，未跑實作 pytest/vitest。
FAILURES_SEEN: 4 個 r3 blocking CLOSED；r4 delta 新增 2 個 blocking。
SCOPE_CHANGES: none；唯一產出 `handoffs/20260714-IC1C-SPECREV-R4-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未改數值/schema/輸出大小。
SPEC-REVIEW-R4: REJECT(2 BLOCKING)
