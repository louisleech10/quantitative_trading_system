# 1a cut1 — FIX3：default-ON 分因回退（委員會定案）

先讀 `handoffs/20260626-1a-cut1-DEFAULTON-RECONCILE.md`（三方定案）。default 已 ON（`ic_train_test_split=True`）。實作分因回退讓 default-ON 不打爆小/合成 caller，同時不削弱洩漏契約。

## 必做
1. **analyze() 分因回退**（`momentum/Analysis/ic_filter_orchestrator.py`）：
   - flag-on 時若 `_build_holdout_split_plan` 回 `SkippedResult`（insufficient_data），或 stage4 rolling warmup 不足 → **不要 skip 整條分析**；改走 **full-sample 路徑**（等同 flag-off：`fit_mask=None`、各 stage 不傳 split_context）。
   - 回退時寫 metadata：`ic_train_test_split={requested:true, applied:false, scope:"full_sample_legacy", oos_guarantees:false, reason:"insufficient_data"|"rolling_warmup_insufficient", details:{train_rows,test_rows,min_test_rows}}`。**不得**寫 train/test_time_bounds，**不得** `metadata.scope:"test"`（那是 OOS 專用）。
   - **TimestampDiscontinuityError 維持 raise，不接 fallback**（C-3 紅線：時間軸壞不可產 full-sample IC）。
2. **API plumbing 測試 opt-out**：`tests/api/test_ic_analysis_api.py`（及其他用 `np.arange` 假 timestamp 的合成 IC 測試）的 request 設 `config_override={"ic_train_test_split": False}`（它們測 API 管線非 OOS）。只改這類合成測試,**不得**改真實 kline 測試。
3. **新測試**（真實 kline 為主）：
   - `tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false`：小 n（test<min_test_rows）+ flag on → analyze() 回**完整 summary_table** 且 metadata `applied:false`/`scope:"full_sample_legacy"`/`reason:"insufficient_data"`。
   - `::test_irregular_timestamps_still_fail_closed`：假 arange timestamps + flag on → `pytest.raises(TimestampDiscontinuityError)`（不 fallback）。
   - `::test_oos_applied_true_when_sufficient`：真實 BTC/1h 足量 → `applied:true`/`scope:"test"`（守住成功路徑仍標對）。

## 必重驗
- `pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` 全綠。
- **3 個洩漏不變量仍 PASS**（fallback 不得重開洩漏；applied:true 路徑不變）。
- G-OLD flag-off deep-equal 仍 PASS；G-NEW（applied:true）不需重凍（OOS 成功路徑未改）—若你改動影響 applied:true 輸出則須重凍並說明。
- 既有 IC API 測試（opt-out 後）不再 timeout：`pytest tests/api/test_ic_analysis_api.py -q -k "not deep and not export"`（deep/export 是既有 flaky,可不論）。
- 解耦 `grep -rE "from api\." momentum/`==0。

## 鐵律
default 維持 ON；不放寬既有斷言；TimestampDiscontinuity 維持 raise；≤2 輪卡關即 `STATUS: BLOCKED`。進度寫 `handoffs/20260626-1a-cut1-FIX3-CODEX.md`，完成 STATUS: DONE/BLOCKED。
