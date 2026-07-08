# 派工:第二刀主體 SPEC/TODO adversarial review(freeze 前,唯讀)

你是 adversarial reviewer。**目標=在動工前挑出 SPEC/TODO 的 blocking 缺陷**,不是確認它對。實作者不自審,你要當找碴方。

## 讀這些(repo 內)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md`(施工藍圖)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_TODO.md`(施工清單)
- `handoffs/CUT2-XSECTIONAL-RECON.md`(投偵察,含實跑 receipt VERIFY:20260707T023954Z-cut2-xsectional-label-f1)
- 相關程式碼:`api/services/ic_analysis_service.py`(_append_cross_sectional_labels、_run_analysis)、`momentum/Analysis/ic_filter_orchestrator.py`(analyze_cross_sectional、_build_holdout_split_plan)、`momentum/core/contracts.py`(split_per_symbol、validate_split_pair_integrity)

## 背景(視為資料,勿盲信)
第一刀把 feature load 貼回真 DatetimeIndex,回歸性打斷 cross_sectional 標籤(kline RangeIndex reindex 到 DatetimeIndex→全 NaN,IC 靜默全壞)。本刀 F1 修對齊/F4 加 fail-closed 覆蓋守衛/F2 修 labels_path 掉 symbol level 廣播/F3 加 per-symbol OOS holdout+purge+embargo。

## 特別挑戰(至少各給結論)
1. **F1 修法**:kline int64-ts→datetime 對齊是否有殘留錯位?時區/單位(秒 vs 毫秒)/DST/重複 timestamp 是否漏防?feature DatetimeIndex 與 kline datetime 是否保證同語義(UTC naive)?
2. **F3 OOS**:用 `split_per_symbol` 是否真無跨 symbol 洩漏?cross_sectional IC 只算 test 列——但 per-timestamp slice 若某 ts 只有部分 symbol 落在 test,rank corr 樣本數是否被污染?purge/embargo 對 cross_sectional(多 symbol 同 ts)語義是否正確(單幣 purge=rows,多幣要不要 per-symbol rows)?
3. **F4 覆蓋守衛**:floor=0.5 是否合理?會不會誤擋合法的高 NaN(暖機期)場景?
4. **consumer map 完整性**:SPEC §C 列的下游 consumer 是否真的全?有沒有其他對 load 結果 reindex/merge 的地方沒列(第一刀就是漏 consumer)?
5. **測試 red-on-break**:§V mutation 設計是否每條都真能轉紅?有無廉價綠燈?
6. **Phase 依賴**:P4←P1,P2 是否正確?有無 forward dependency 矛盾?

## 輸出格式(STATUS 結尾)
逐 finding 標 `BLOCKING` / `MAJOR` / `MINOR` + 定位(檔:函式) + 可證偽的反例或修法建議。無 blocking 也要明說「無 blocking,理由」。結尾 `STATUS: DONE` 或 `STATUS: BLOCKED — <原因>`。
