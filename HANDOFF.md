# Handoff
**Agent**: Claude | **Time**: 2026-07-07 | **Branch**: main

## ✅ 剛完成:IC 第二刀首項 row_index attach(commit 6a991c2,已 push)
- `feature_library._attach_row_index` 在 V2 load 路徑貼回真時間軸(鏡像 `_attach_cgsa_row_index`);只改 index,值/欄/列不變。修全 tf config_hash 載入掉時間軸→切分校驗誤判 raise 的 bug。
- 回歸 `tests/momentum/test_feature_library_row_index.py tests/momentum/test_feature_library_config_hash.py tests/api/test_ic_analysis_service.py` 13 passed VERIFY:20260706T165905Z-cut2-rowindex-regression exit0;三方數據正確性簽核 PASS 零 BLOCKING(RECONCILE-STAMP codex+composer APPROVED)。docs/IC_PHASE1_1a_CUT2_ROWINDEX_{SPEC,TODO}。
- Follow-up(登記未做):ingest cache 版本化、1d 頻率地圖、conftest scoped-collect clobber L6.5 golden、full-analyze 效能(歸「79 測試換真資料」epic)。

## ★下一站 = IC 第二刀主體:cross_sectional `analyze_cross_sectional` 防洩漏(大任務 a/b/d)
**目標**:把 `momentum/Analysis/ic_filter_orchestrator.py:528 analyze_cross_sectional` 提升到第一刀(單幣 `analyze`)的防洩漏標準。**須走完整管線 SPEC+TODO+雙家族 adversarial + 全三方數據正確性簽核**(多 symbol 跨界洩漏=數據正確性 scope)。

**已偵察到的洩漏面(新 session 須自行驗證勿盡信)**:
1. **label 只按 timestamp 對齊**(:558-561 `label_series.reindex(timestamp_index)` 掉 symbol level)→ per-(timestamp,symbol) label 可能貼到別 symbol 的列。**最可疑的跨界洩漏點**。對照 memory「IC Phase1 決策」:ML孤島 positional-index 切片→多 symbol 跨界洩漏,SplitPlan 須 per-symbol。
2. **無 OOS / 無 purge·embargo**:full-sample IC,無 holdout split(單幣 `analyze` 有 `_build_holdout_split_plan`);look-ahead 未圍。
3. cross_sectional labels 來自 `api/services/ic_analysis_service.py:_append_cross_sectional_labels`(_run_analysis :159)——per-symbol 正確性未驗。
4. 呼叫鏈:`_run_analysis`(:125-171)load_multi→concat→set_index("_symbol")→append labels→analyze_cross_sectional。

**前置就緒**:真實 FF 測試資料(3 sym×1h + 兩套 12h,`data_cache/features/`);第一刀 CUT1 的 per-symbol SplitPlan/purge 契約(`momentum/core/contracts.py` validate_split_*)可複用。
**建議**:新 session 先跑投偵察(讀 analyze_cross_sectional 全文 + _append_cross_sectional_labels + 用真實多 symbol 資料實跑觀察 label 對齊),再寫 SPEC。

## 續(cross_sectional 之後)
- 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;grouped_ic 止血。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員審查派工用 `gate.sh dispatch --task-id --risk low --template "n/a:"`(勿 --risk high --adversarial waived);codex exec 必接 `< /dev/null`。委員產出 register-output 才過 pre-commit claim checker。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout tracked 共用檔。
