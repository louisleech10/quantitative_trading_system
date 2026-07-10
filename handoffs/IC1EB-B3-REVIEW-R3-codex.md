# IC1EB B3 R3 裁定確認 — Codex

範圍：只讀靜態歸因 R2 唯一 BLOCK 事由；未執行測試、未修改實作或測試。

## 裁定

R2 的八項功能／正確性檢查維持全數 CLOSED/PASS。兩個 gitignored 衍生檔的覆寫不可歸因於 B3 diff，屬既有 cut1 回歸測試走真實 service 落盤路徑的 legacy 測試設計債；R2 唯一 BLOCK 依據撤銷。

## 理由與靜態證據

1. B3 基底 `9df75d3` 已存在 `test_fallback_insufficient_data_marks_applied_false`、`test_oos_applied_true_when_sufficient`：兩者用 `tmp_path` 建輸入後直接呼叫 `ICFilterOrchestrator.analyze(...)`，但未重導／隔離輸出。
2. 同一基底的既有 production 鏈 `_stage7_report → _persist_outputs` 已固定把 filtered features 寫到 `data_cache/features/{symbol}_{timeframe}_filtered.h5`，並把 report 寫到 `data_cache/reports`；metadata 本來即由 fixture 提供 `BTCUSDT`、`1h`，case id 無值時本來即回退 `ic_gatekeeper`。
3. B3 orchestrator diff 僅涉及 cross-sectional horizon、HAC t/p、FDR q 與 metadata；未新增、修改或搬動 `_stage7_report`、`_persist_outputs`、`_resolve_filtered_path`、report output directory 或 case-id 邏輯。
4. cut1 測試 diff 只在三個直接 `_stage5_statistical_validation(...)` 呼叫補 `metadata={"symbol": "BTCUSDT"}`；這些呼叫不經 `_stage7_report/_persist_outputs`，不是上述兩檔的落盤引入點。

## 債項建議（NON-BLOCKING，另案）

建立 cut1 測試輸出隔離債：由 fixture 將 `_persist_outputs` 重導至 `tmp_path`，或注入可配置 output root；覆蓋所有走真實 `analyze(...)` 的測試，並加驗證確保測試前後 `data_cache/` 指紋不變。此債不得在 B3 裁定中反向歸責，也不影響 B3 功能正確性。

TESTS_RUN: none（依派工要求只讀、不執行測試）。
ASSUMPTIONS_VERIFIED: 以 `git show 9df75d3:<path>` 與當前 B3 diff 靜態確認既有 caller、既有落盤鏈及 B3 無新增 persist 路徑。
SCOPE_CHANGES: none；僅新增本裁定檔。
NUMERIC_OR_SCHEMA_IMPACT: none。

VERDICT: PASS
