# 派工:第二刀主體 fix-round(Composer)— Codex code review 4 findings

Codex 獨立審查 verdict=資料正確性 FAIL(見 `handoffs/CUT2-XSECTIONAL-CODEREVIEW-codex.md`)。修下列 4 項,**不擴散改動**、不動已通過的其他行為。debug ≤2 輪未過→STATUS: BLOCKED。

## FIX-1【BLOCKING・F4 守衛邊界漏洞】
- **問題**:`_enforce_cross_sectional_label_coverage` 下界 `floor_s=(len_s−horizon)/len_s`,當 `len_s ≤ horizon` → 門檻 ≤0 → 全 NaN 標籤靜默通過(Codex 實測 NO_RAISE)。違反 F4 fail-closed。
- **修法**:守衛開頭無條件先擋:**任一 symbol `notna(label_s).sum()==0` → `raise InvalidInputError`(全 NaN 標籤,不論列數)**;且 `len_s ≤ effective_horizon` → `raise InvalidInputError`(無法形成有效 forward 標籤)。再套既有 `coverage_s < floor_s×(1−tol)` 下界檢查。
- **測試**:加邊界 `test_cross_sectional_coverage_guard_short_series_all_nan`(`len_s==horizon` 全 NaN → `pytest.raises(InvalidInputError)`)。

## FIX-2【MAJOR・F3 mutation 套套邏輯】
- **問題**:`test_cross_sectional_oos_split_mutation_shrunk_purge_fails` 未動生產 purge,只自證 `>=` 不等式(Codex+Claude 一致)。非 red-on-break。
- **修法**:改真 mutation——monkeypatch/變體**實際縮短生產 `test_start`(或令 `purge_td=0`)**注入生產切分路徑,斷言真 gap 保護(鏡像 :113 的 `(test_min−train_max) ≥ purge_td+embargo_td`)在 mutation 下**FAIL/洩漏現形**。若無法乾淨 monkeypatch,改為:直接對 `_build_cross_sectional_global_split` 傳入被削小的 horizon/embargo,驗證輸出 gap 隨之縮小(證 gap 真由生產計算而非常數),再證原設定下 gap 足夠。刪掉套套那條。

## FIX-3【MAJOR・F1 容孔語義矛盾——Claude 裁決】
- **矛盾**:凍結 SPEC Task 1.1 邊界② 說「feature ts 有 kline 缺孔→該列 NaN 交 F4」;但 R8 我加的「feature.index ⊆ kline datetime,否則 raise」把任何缺孔變硬失敗。二者衝突,Composer 選了 raise。
- **Claude 裁決=採 Option B(容孔→NaN→F4 gate)**:研究型 IC 應容忍少量 kline 缺孔,由(已修穩的)F4 覆蓋守衛決定是否過低而擋;不因單一缺孔硬斷整個分析。
- **修法**:把 `_append_cross_sectional_labels` 的「⊆ 否則 raise」**放寬**為:對 feature ts **有**對應 kline ts 的列,斷言值正確對齊(不得錯位/misalignment);feature ts **無**對應 kline(缺孔)→該列 label NaN(允許,交 F4)。即 R8 的職責從「禁缺孔」改為「禁錯位」:仍須斷言對齊正確性(例:抽樣比對 aligned 值 == kline forward return),但缺孔不 raise。
- **測試**:調整/新增——人為在某幣 kline 挖一個孔(移除一根)→ 該列 label NaN、其餘正確、不 raise;覆蓋率若仍 ≥ 下界則分析續行。

## FIX-4【MINOR・F1 int64 契約】
- `_append_cross_sectional_labels` timestamp 單位契約:加 `assert np.issubdtype(ts_raw.dtype, np.integer)`(且視為 epoch 秒);非整數 → raise。

## Batch Gate(修後全綠)
- `grep -r "from api\." momentum/ | wc -l` → 0
- `pytest tests/api/test_ic_analysis_service.py tests/momentum/test_ic_cross_sectional_cut2.py -q`(含新邊界測試)
- 既有 `tests/momentum/test_ic_filter_orchestrator.py` 的 2 個 pre-existing fail 維持原狀(非本刀,勿動)

## 禁止
不擴散改動;不動單幣 analyze/特徵值/欄/列;不放寬既有斷言;不藏 flag。收尾更新 `handoffs/CUT2-XSECTIONAL-IMPL-RESULT.md`(append fix-round 段)+ STATUS。
