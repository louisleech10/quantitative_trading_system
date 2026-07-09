# IC 1e HAC + 1b FDR 合刀 — Claude 獨立全量版(偵察+判斷)

**Task-id**: ic1eb-recon-claude(自產,非派工)
**日期**: 2026-07-09 | **HEAD**: 8e9601e
**方法**: 親讀源碼+實測 receipt;未參照本輪 codex/composer 偵察產出(其尚在跑)下結論。

---

## A. 現況事實(每項親驗 receipt)

### A1. p-value 生產鏈(核心病灶)
1. **rolling IC 結構**:`ic_engine.compute_rolling_ic`(ic_engine.py:269-303)——windows 預設 `[21,63,126]`、stride 預設 `1`(ic_config_schema.py:66-67);rolling Spearman,每窗產生步長 1 的 IC 序列,相鄰兩值共享 `w-1` 個資料點 → **機械性高自相關(近似 MA(w-1)),遠非 i.i.d.**。
2. **pool 再 t-test**:`StatisticalValidator.compute_ic_statistics`(statistical_validator.py:24-32)經 `_collect_values`(:75-83)把**同一 feature 的三個窗全部 pool 成一列**,`_compute_stats`(:95-128)對 pooled 值跑 `ttest_1samp` i.i.d. + 普通 t 分布 CI(:130-138)。**雙重錯誤**:①重疊窗自相關使有效樣本遠小於 n_obs;②三窗是同一資訊的三次重複計數(n_obs≈3N)。p-value 系統性反保守(過度顯著)。
3. **split 下的餵入**:`_stage4_ic_calculation`(ic_filter_orchestrator.py:2152-2181)rolling 在 train|test 聯集上算,`_slice_rolling_ic_to_test` 依 end-timestamp∈test 切段 → stage5 的 p-value 算在 test 段 rolling IC 上(scope 正確,分佈假設錯)。
4. **診斷不修正**:`compute_ic_autocorrelation`(ic_engine.py:443-464)算 lag-1 自相關、`>0.3` 只 log info,輸出 `ic_autocorr` 不參與任何 se 修正(:2183,:2228)。

### A2. 消費鏈
5. `_build_summary_table`(:2521-2560)把 `stats_item["p_value"]` 塞 row;`_apply_thresholds`(:2562-2627)序列閘 ic_mean→icir→**裸 p_value≤p_value_max**→hit_rate→monotonicity→coverage→spread;`p_value_max` 預設 0.05(schema:104),可被 `event_info["adjusted_p_threshold"]` 覆蓋(:2257-2260;產地 event_filter.py:94-99 `check_sample_size`)。
6. **幽靈 ×3**(全部生產 0 caller,grep 親驗):
   - `adjust_multiple_comparisons`+`_fdr_bh`(statistical_validator.py:58-73,150-166)——手刻 BH(由大到小 cummin,step-up)形式正確,僅測試呼叫。
   - `apply_significance_filter`+`sample_tier=low_confidence` 放寬 0.10(:34-56)——0 caller。
   - `SelectionScope`(contracts.py:724-742,n_tests==len(evaluated) 驗證)——契約+測試在,生產 0 使用。
7. **前端幽靈開關**:store `fdr_correction` 預設 false/advanced preset true(icAnalysisStore.ts:78/104/130),`getEffectiveConfig` 不送;`FeatureTierPanel.tsx:38` 有 UI;後端 `ic_config_schema.py` 無對應欄(grep fdr→0)。
8. **deep 路徑**:`factor_return_analyzer.py:103` `"newey_west_adjusted": False` 硬編(前輪雙委員 receipt,本輪未重驗行號)。

### A3. 工具與交付面
9. **statsmodels 0.14.6 在 venv**(實測 `venv/bin/python -c "import statsmodels"`)→ NW/HAC 與 `multipletests` 可用,亦可作手刻 BH 的對照 oracle。
10. **bootstrap_estimator.py** 存在,generic bootstrap,IC 路徑 0 使用(前輪 receipt)。
11. **1-align 交付複用點**:`_resolve_effective_label_horizon`(:188-231)/`_resolve_label_horizon_from_column`(:234-244)=horizon 單一真相源;label 為 h-bar forward return → **重疊 label 本身即 MA(h-1)**,顯著性修正的 lag 結構須與此同源(SPEC §N 交付義務)。
12. **cross_sectional 路徑**(ic_filter_orchestrator.py:1050-1118):per-timestamp 橫斷面 Spearman IC 序列(真 Fama-MacBeth 型逐期 IC)→ 算 `t_stat = mean/(std/√n)`(i.i.d. 假設,同病:h>1 label 重疊→逐期 IC 自相關)但 **`p_value` 硬填 None**(:1088),summary 僅按 ICIR 排序(:1099-1107),**不過 `_apply_thresholds`**(無門檻淘汰)。
13. `_passes_threshold`(:2629 附近):`None`/NaN → False(fail-closed;若 cross_sectional 表誤入 p 閘會全滅,現況不入)。

---

## B. 我的獨立設計判斷

**目標**:selection 消費的顯著性推斷統計可信(修 i.i.d. 假設)+以 FDR 控多重比較(修裸 p 門檻)+SelectionScope 接線(scope 可稽核)。**不動** IC 點估計/ICIR/rolling IC 診斷值(那些是描述統計,數值不變)。

### 裁決點(供 SPEC 起草+雙家族 adversarial 攻擊)
- **D-A p-value 生產修法(本刀心臟)**:廢「多窗 pool + i.i.d. t-test」。候選:
  - **A1(我的主推)**:對**單一檢定序列**(icir_window=63 該窗的 test 段 rolling IC,或更乾淨=per-bar 打分序列)做 **Newey-West HAC t-test**:`t = mean/se_NW`,maxlags 有下限約束 `≥ (w-1)+(h-1)` 由機械重疊決定——但 w=63 時 lag 63 對短 test 段不穩 → rolling IC 做檢定對象天生病態。
  - **A2(統計上更乾淨,我傾向為主 kernel)**:檢定對象改「**逐 bar 貢獻序列**」:`z_t = rank(x_t)·rank(y_t)` 中心化積(Spearman 的 per-bar 貢獻),對 z 序列做 NW(maxlags 下限=h-1,由 horizon resolver 同源)→ IC 顯著性;無 rolling 平滑製造的人工自相關,只剩 label 重疊的真 MA(h-1)。
  - **A3**:stationary/circular block bootstrap(block 長度≥h,對 test 段特徵-label 對重抽算 IC 分布)→ p/CI;非參數,對 Spearman 合身;成本高但作 cross-check 或 fallback。
  - 建議 SPEC:主 kernel=A2,A3 為驗證腿(Golden 對照);A1 明文否決理由(rolling 平滑序列不是合法檢定對象)。此為技術裁決,由 adversarial 兩家族攻擊收斂,不問使用者。
- **D-B FDR 消費點與 n_tests**:對 **stage5 進場的全部 evaluated features**(summary_table 全列)先算 BH q-value,再進 `_apply_thresholds` 以 `q ≤ α` 取代裸 p 閘;**禁**只對通過前置閘(ic_mean/icir)的子集算 FDR(selection-conditioning 會使 n_tests 縮水、FDR 失控)。n_tests=len(evaluated),與 SelectionScope.__post_init__ 驗證同源。
- **D-C SelectionScope 接線**:stage5 產 `SelectionScope(scope_id, universe_features, split_label="test", evaluated_features, n_tests, method="fdr_bh", base_universe_hash=_base_universe_hash(...))` 入 report metadata;golden/測試可稽核「在哪個集合上做了幾次檢定」。
- **D-D config+前後端接通**:`ic_config_schema` 新增 significance 節(hac 參數/fdr method+alpha);**fdr 預設 ON**(驗過就別預設關閉,鐵律);前端 `getEffectiveConfig` 真送 `fdr_correction`,report 加 `p_value_raw/p_value_adj/n_tests/scope_id`,types.ts+表格對齊(q-value 顯示)。幽靈開關轉真開關(關=對照/逃生口,report 明標 raw)。
- **D-E event tier 互動**:`adjusted_p_threshold`(樣本不足調門檻)語意改為作用在 **FDR α**(low_confidence→α=0.10),非 per-feature p;`apply_significance_filter` 幽靈函式合併進新路徑或刪除(禁留兩套並行)。
- **D-F 欄位相容**:summary_table `p_value` 欄語意變更(HAC p)→ 同步 `p_value_raw` 保留舊值一版?我的傾向:`p_value`=HAC raw、新增 `p_value_adj`(q);前端 threshold 顯示消費 adj。舊值不保留(舊值=統計錯誤,保留=誤導)。
- **D-G deep 路徑**(factor_return_analyzer NW=False):**§N 登記另立**,本刀 scope=selection 主鏈(stage5→thresholds→report→前端),不暗示全平台覆蓋。
- **D-H cross_sectional 路徑**(A12):逐期橫斷面 IC 序列是 NW 的教科書適用對象(重疊 h→MA(h-1));其 `t_stat` i.i.d. 假設同病、`p_value=None`。我的傾向:**入本刀**但最小面——同一 kernel 對其 IC 序列產誠實 `t_stat/p_value/p_value_adj`(填掉 None),**不新增門檻行為**(該路徑現無淘汰,維持排序);理由=同一統計 kernel 順手接、避免半修狀態,行為風險≈0。可被 adversarial 挑戰改判 §N。

### 行為變更聲明(Golden 型態)
本刀是**行為變更型**(p-value 數值與 passed_features 會變),非 byte-equal 重構:
- Golden=真 3sym 資料舊 vs 新 **selection diff 快照**(哪些 feature 從 pass→fail,附 raw p vs HAC p vs q 三欄對照)+ 新路徑自身的凍結 baseline。
- 可證偽 mutation(草案):M-A 合成高自相關 null 序列(AR(1) φ=0.9,零均值)×1000 seeds → 舊法假陽率實測遠超 5%(receipt 數字),新法≈名目 α(統計檢定,允收帶);M-B 合成 m=100 null+5 true → BH 後實測 FDR≤α;M-C n_tests 故意只數通過前置閘子集 → 對應斷言必紅;M-D FDR 在 train 段算/test 段消費(scope 錯配)→ 紅;M-E 手刻 _fdr_bh vs statsmodels multipletests 數值一致(atol 1e-12);M-F 前端 fdr_correction=false 真關(report 標 raw,threshold 走 raw p)+ =true 走 q,e2e 兩態皆驗。

### 大小/流程
- **大**(命中 a/d;跨 momentum↔api schema↔frontend 三欄接線=全棧連通稽核適用)。完整管線:SPEC+TODO→雙家族 adversarial→雙戳記 freeze→**Codex 實作+Composer review**(依 HANDOFF 本 epic 分工)→三方數據正確性簽核。
- 依賴:1-align 已凍結交付(horizon resolver 同源)✅;statsmodels 已在 ✅。

---

ASSUMPTIONS_VERIFIED: 上述 A1-A11 全部親讀/親測(file:line 如文);A8 沿用前輪雙委員 receipt 未重驗行號。
TESTS_RUN: venv statsmodels import 實測;其餘=靜態讀碼。
FAILURES_SEEN: none。
SCOPE_CHANGES: none(僅本檔)。
STATUS: DONE
