# 1a 第一刀 — LEAK 修補派工（三方簽核 R1 抓到 2 真 LEAK）

你是嚴謹實作者。**先讀** `handoffs/20260626-1a-cut1-SIGNOFF-RECONCILE.md`（2 LEAK + 修法）+ `docs/IC_PHASE1_1a_CUT1_SPEC.md`。
B1-B5 已實作於 working tree；本次只修下列缺陷，不重做。

## 必修
- **[LEAK-1] rolling OOS 排除 purge rows**：`momentum/Analysis/ic_filter_orchestrator.py::_stage4_ic_calculation`。flag-on 時 rolling 輸入須只用 `train_mask | test_mask` 的 allowed rows（排除 purge hole `~train & ~test`），再切 test 端點；保留的 test rolling 視窗成員不得含 purge rows。
- **[LEAK-2] winsorize type-feature 分支改用 fit slice**：`momentum/Analysis/data_preprocessor.py::winsorize`。`_is_type_feature` 的判斷對象改 `_select_fit_series(series, fit_mask)`（train slice），不得由 test 分布決定 skip/winsorize 分支。逐一審 winsorize/standardize/handle_missing/remove_constant 內所有「分類/分支」決策是否也用了全段（非只統計量）。
- **[FIX-embargo] embargo 接線**：`_build_holdout_split_plan` test 起點 `= split_point + effective_purge + int(config.embargo)`；補 embargo>0 測試。

## 必補測試（可證偽，真實 kline，會抓上述 LEAK）
`tests/momentum/Analysis/test_ic_1a_cut1_oos.py`：
- 改用真實 `_build_holdout_split_plan()` 產生含 purge gap 的 train/test mask（非 `test_mask=~train_mask`）。
- **不變量1**：擾動 purge rows 的 label → test rolling IC / ICIR **不變**（LEAK-1 修好則 PASS；未修則 FAIL）。
- **不變量2**：只改 test 段某 type-like 特徵值 → winsorize 分支(skipped/winsorized 集合)與 train 輸出 **不變**（LEAK-2）。
- **不變量3**：embargo>0 → test 起點推遲 embargo 列（FIX-embargo）。
真實 kline `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture。

## 鐵律
- flag 仍預設 OFF；不得放寬既有斷言；反例必真 `pytest.raises`/數值不變斷言。
- 不碰次路徑(reanalyze/deep analysis)——cut1 範圍外。
- ≤2 輪卡關即 `STATUS: BLOCKED — <原因>` 停手，不 solo 硬幹。
- 驗收：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` 全綠 + `grep -rE "from api\." momentum/`==0。
- 進度寫 `handoffs/20260626-1a-cut1-FIX-CODEX.md`；完成 `STATUS: DONE` 或 `BLOCKED`。
