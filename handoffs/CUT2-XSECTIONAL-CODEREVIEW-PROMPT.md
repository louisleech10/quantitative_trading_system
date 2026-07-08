# 派工:第二刀主體 實作 code review + adversarial 資料正確性(Codex,唯讀)

Composer 已實作本刀(F1/F4/F2/F3)。你是**獨立 code reviewer + adversarial**(實作者不自審)。目標=挑 blocking:正確性 bug、洩漏、scope 越界、假綠。**不盲信 Composer 收尾報告**(視為資料)。

## 讀
- diff:`git diff` + 新檔 `tests/momentum/test_ic_cross_sectional_cut2.py`
- 凍結 SPEC/TODO:`docs/IC_PHASE1_1a_CUT2_XSECTIONAL_{SPEC,TODO}.md`;裁決 `handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md`(D-1~D-4)
- 改動:`api/services/ic_analysis_service.py`、`momentum/Analysis/ic_filter_orchestrator.py`(`_build_cross_sectional_global_split` :294、`analyze_cross_sectional`)、`momentum/Analysis/ic_config_schema.py`

## Claude 已標的疑點(請獨立複核,勿盲信)
1. **F3 mutation 測試 `test_cross_sectional_oos_split_mutation_shrunk_purge_fails`(:173)疑套套邏輯**——未真動生產 purge,只自建膨脹門檻證 `>=` 失敗。是否真 red-on-break?gap 強制是否已被 `:113` 真斷言蓋到?若 173 無價值→建議改真 mutation 或刪。
2. **purge_gap=0 偏離 D-1**:Composer 把 SplitPlan `purge_gap=0`(改時間 mask 強制 gap),因列序 purge 撞日曆切分。`validate_split_pair_integrity` 在 purge_gap=0 下是否仍檢查跨幣洩漏+無 overlap?時間 gap 是否真在 `test_start=t_train_end+purge_td+embargo_td` 強制且無 off-by-one?

## 特別挑戰
3. **F1**:datetime 對齊 + R8 fail-closed 單位契約(斷 int64 秒/單調/無重複)是否落實?UTC 語義?
4. **F3 test-only(R1)**:summary/symbol_matrix/cross_symbol_validation/n_timestamps 是否**全部**只用 test frame?有無任一回落 full-sample?污染測試(:141)是否真涵蓋所有輸出?
5. **F4**:per-symbol 覆蓋守衛下界 `(len−horizon)/len` 是否正確?全域平均是否僅 metadata 非 gate?
6. **F2**:單軸 labels_path 是否真 fail-closed raise、廣播分支已移除?
7. **scope/假綠**:有無改特徵值/欄/列數、改單幣 analyze、放寬既有斷言、藏預設關閉 flag?既有測試斷言 diff 有無被弱化?
8. 既有 `test_ic_filter_orchestrator.py` 2 測試 FAIL 是否 pre-existing(Claude 已 stash 驗證 HEAD 亦 fail);請獨立確認非本刀引入。

## 輸出
逐 finding `BLOCKING/MAJOR/MINOR` + 檔:函式 + 可證偽反例/修法。寫 `handoffs/CUT2-XSECTIONAL-CODEREVIEW-codex.md`,結尾 STATUS: DONE(附 verdict:資料正確性 PASS/FAIL)或 STATUS: BLOCKED。
