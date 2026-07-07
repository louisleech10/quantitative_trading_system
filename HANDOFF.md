# Handoff
**Agent**: Claude | **Time**: 2026-07-07 | **Branch**: main

## ✅ 剛完成:IC 第二刀主體 cross_sectional 防洩漏(2026-07-07,待 commit) SIGNOFF:claude:DATA-CORRECT SIGNOFF:codex:DATA-CORRECT SIGNOFF:composer:DATA-CORRECT
- **F1** `_append_cross_sectional_labels` kline int64-ts→datetime 對齊(修第一刀回歸的橫截面標籤全 NaN);**F4** per-symbol 覆蓋守衛 fail-closed(all-NaN/短序列無條件擋);**F2** 單軸 labels_path fail-closed;**F3** 全域同步時間邊界 OOS holdout+purge+embargo,test-only 覆蓋全部 report 輸出。VERIFY:20260707T023954Z-cut2-xsectional-label-f1
- **驗收**:Claude 自跑 18 passed,解耦 grep=0,postflight OK;三方簽核全 PASS(Codex adversarial 抓 F4 邊界 BLOCKING→fix-round→原提出方複驗閉合);SPEC 雙 RECONCILE-STAMP APPROVED provenance。SIGNOFF:codex:DATA-CORRECT
- **殘留(正交非本刀)**:`test_ic_filter_orchestrator.py` 2 pre-existing fail(單幣 analyze 合成 fixture 撞 rows-purge 校驗,HEAD 亦 fail,git stash 已驗)。REF:handoffs/CUT2-XSECTIONAL-SIGNOFF-claude.md
- **前刀**:row_index attach(commit 6a991c2 已 push)V2 load 貼回真時間軸=本刀 F1 修的回歸來源。REF:handoffs/CUT2-XSECTIONAL-SIGNOFF-claude.md

## ★下一站 = IC 1a 剩餘刀:1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;grouped_ic 止血
- 治理修補(SCAR 已入):SPEC consumer-map 須含所有對 load 結果 reindex/merge 的 consumer + 真路徑 red-on-break 測試(第一刀漏 `_append_cross_sectional_labels` 教訓)。REF:docs/SCAR_LEDGER.md

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
