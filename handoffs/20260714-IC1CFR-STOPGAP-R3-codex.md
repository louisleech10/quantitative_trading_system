# IC1C-FR-STOPGAP SPEC r3 adversarial review — codex (2026-07-14)
範圍：唯讀複核 R2-CX-1 選項 B、實碼 runner/tier/summary 控制流與 r3 golden；裁決 REJECT。

| 項目 | 判定 | 證據 |
|---|---|---|
| R2-CX-1 default-off 主契約 | STILL-OPEN | §C:24、Task 1.1:41-44 與驗收 oracle 尚未一致，見 R3-CX-1。 |
| 顯式開啟佔位 union | CLOSED（形狀） | §C:25 已唯一指定 `{status:"unavailable",value:null,reason}`，legacy/cache 由 sanitizer fail-close。 |
| §G 雙版本 | CLOSED（分版）/新 FACT 錯 | §G:34 已拆 default-off 與 force golden，但 before summary 值錯，見 R3-CX-4。 |

- **R3-CX-1｜BLOCKING｜tier 仍使選項 B 自相矛盾。** Task 1.1:41 要 `_apply_tier_config` 排除 `factor_return` 的 preset 強制 true，:42 的 default request 要 `not_run`+無節；但 :43 又要求 intermediate/advanced tier→佔位。現預設 active preset 即 intermediate（orchestrator:3338），兩個 oracle 可指同一 request。應定案 named preset 保持 default-off，或明確哪個 tier 是顯式 enable；M1b 必驗精確 summary/節缺席，不能只驗「無有限葉」。
- **R3-CX-2｜BLOCKING｜`unavailable` summary 無可行寫入者。** §C:25/Task 1.1:41 指定 runner 寫 summary，但 `_run_factor_return` 只回 dict；父迴圈在 orchestrator:1665-1667 接回後無條件寫 `completed`。須指定父迴圈 special-case（並定義 completed_count/progress），或改 runner result protocol；否則 explicit golden 必得 `completed`。
- **R3-CX-3｜BLOCKING｜force 契約漏掉 global deep-off 早退。** §C:25/Task 1.1:43 宣告 `force_modules=["factor_returns"]`→佔位，但 orchestrator:1601-1615 在建立 `force_set`(:1627)前即因 deep disabled 返回。須裁定 force 是否跨過 global deep-off；若是，列控制流改點與 basic/deep-off 測試，若否，收窄契約。
- **R3-CX-4｜BLOCKING｜default-off golden 的 before 狀態不存在。** §G:34 寫 `module_summary.factor_returns: enabled→not_run`；現 runner 成功/失敗/未跑只會寫 `completed`/`skipped`/`not_run`（orchestrator:1667,1681,1696），沒有 `enabled`。應以凍結 before.json 的實值（預期成功 fixture 為 `completed`）作 oracle，不可預寫不存在狀態。

新洞掃描其餘結果：sanitizer 缺鍵不注入、legacy finite 整節替換、前端兩圖 fail-close 與 config/output 單複數鍵警示未見新增 blocking；REJECT 故未追加 RECONCILE-STAMP。
ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF.md/CLAUDE.md/SPEC r3/RECONCILE/r2 codex；以 `nl/sed/rg` 核對 default active tier、runner selection、deep-off 早退、summary 寫入與 golden 狀態集合。
TESTS_RUN: `wc -l`+`sed -n` 讀治理文件；`rg -n -C4 factor_return...` 掃 consumer/control-flow；`nl -ba ... | sed -n` 核對 SPEC:23-76、orchestrator:1638-1707/3335-3385；review-only，未跑 pytest/vitest。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本審查檔，未改 SPEC/程式/根 HANDOFF，未追加戳記。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改數值/schema；要求釘死 not_run/missing、unavailable union、completed_count 的狀態契約。
SPEC-REVIEW-R3: REJECT(4 BLOCKING)
