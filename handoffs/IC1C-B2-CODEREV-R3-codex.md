# IC1C-B2 Code Review R3 — Codex (2026-07-14)

範圍：R2 四項 blocking 逐條重跑與 claimed rework delta 掃描；唯讀審查，僅新增本檔。SPEC/TODO reconcile stamp checker 皆 PASS。

## 終判
1. **B1 STILL-OPEN（BLOCKING）**：Frozen TODO:127 明定同號 gate 於 `max(|gi|)≥0.05` 強制；RESULT 無權改成「兩側皆達 0.05」。`0` 無正/負號，故 `(0.0,0.2)` 不同號，應 FAIL。實作 `check_gross_ic_pair` 使用雙側 `and`，實跑仍 PASS。`--self-test` 雖涵蓋案例，卻把此錯誤語意固定為 `expect_pass=True`，屬錯 oracle，不能閉合。
2. **B3 CLOSED**：`skipped?: false` 已刪；GROSS_ONLY/SKIPPED 的 `?: never` 排除混合鍵。於 `/tmp` 構造 gross core+僅 `cost_bps` 的混合物件，`tsc --strict` 如期 TS2322（缺其餘 cost profile 必填鍵）。
3. **B4 CLOSED**：T4 直接透過真 `useICAnalysis.startDeepAnalysis`，mock fetch 422 並驗 URL/body/error；page 掛載傳 `loading={isDeepRunning || deepAnalysisStatus === 'running'}`。Vitest 8/8 PASS，production build PASS。
4. **R2-NEW-1 CLOSED**：`NetICChart` 先以 finite guard 剔除缺失/非有限 `gross_ic`，不再 `?? 0`；全剔除落 `netic-empty`。具名缺欄測試隨 Vitest 通過，靜態掃描無 runtime fallback。
5. **Delta scan**：claimed R2 rework 五個 source/test 檔與 RESULT 敘述相符，`git diff --check` PASS，未見 `data_cache/` diff。工作樹另有大量既存/他案 dirty 檔，未歸因本輪，亦未納入本裁決。

ASSUMPTIONS_VERIFIED: Frozen TODO 是 RESULT 上位 oracle；zero 與 material 值不構成同號；TS exact-profile、真 hook 422、page loading、gross_ic empty path 均實跑。
TESTS_RUN: reconcile SPEC+TODO→2 PASS；六 predicate→PASS/FAIL/PASS/FAIL/FAIL/FAIL；`--self-test`→PASS（但錯 oracle）；type probe `tsc`→預期 TS2322；Vitest→8 passed；Next build→PASS（僅既有 hook warnings）；`git diff --check`→PASS。
FAILURES_SEEN: zero_vs_material 實跑仍 PASS，與 Frozen TODO oracle 衝突；此為未解 blocking。
SCOPE_CHANGES: reviewer 僅新增本檔；未改 source、root HANDOFF 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: reviewer 無；待修 B1 predicate/self-test，應在 max threshold 啟動時要求兩值確為同號，zero-vs-material FAIL。
CODE-REVIEW-R3: REJECT(1 BLOCKING)
