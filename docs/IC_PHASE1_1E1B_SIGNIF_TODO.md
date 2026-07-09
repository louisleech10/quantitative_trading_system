# IC Phase1 1e+1b 顯著性正確化 TODO(v2 DRAFT,基於 docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md v2,2026-07-09;R1 修訂對照見 SPEC §ADV-RESOLUTION)

## §0 全域規則與約束(執行端讀完即可遵守)
- 解耦:統計 kernel 落 `momentum/Analysis/statistical_validator.py`,契約落 `momentum/core/contracts.py`;`grep "from api\." momentum/`→0 保持。
- **不改數值**:IC 點估計/ICIR/rolling IC/ic_decay/grouped_ic/monotonicity/coverage/turnover 的值 byte 不動(SPEC §G G-1 驗);只動顯著性推斷(p/t/q)與其消費。
- horizon 一律取自 `_resolve_effective_label_horizon`/`_resolve_label_horizon_from_column`(SPEC [A:horizon 同源]);禁另建解析。
- fail-closed:樣本不足/std=0/全 NaN→p=NaN→p 閘 fail(`_passes_threshold` None/NaN→False 語意保留);SelectionScope 違約→raise;禁靜默 fallback 回 i.i.d.。
- HAC 無 production 開關;FDR flag 預設 ON(SPEC D-G)。
- 防假綠:不得放寬/刪除既有測試斷言換綠;`tests/momentum/test_statistical_validator.py` 語意遷移逐條列帳;diff 斷言驗收。
- data_cache 唯讀;測試輸出重導 tmp;禁 git checkout/stash/restore tracked 檔(Golden baseline=唯讀消費 `handoffs/ic1eb_baseline/` 預產快照,禁自行操作 git 取舊版);測試污染用 `GATE_DIR_OVERRIDE`/tmp。
- 統計性質測試:固定 seed、允收帶(binomial 95% CI)寫進測試碼、長測掛 `slow_stat` marker 並給預算上限。
- Logging:`get_logger(__name__)`;kernel 熱迴圈不 log。

## §B 批次執行策略(依賴拓撲→最少批次)
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1, 1.2, 1.3 | 無 | 同檔 kernel+FDR 層+驗證腿,hermetic 可獨立綠 | 中 |
| B2 | 2.1, 2.2, 2.3, 2.4, 2.5 | B1 | stage5 同一鏈,拆開會出現半接線狀態 | 大 |
| B3 | 3.1 | B1 | cross_sectional 獨立路徑,只依賴 kernel | 小 |
| B4 | 4.1, 4.2, 4.3 | B2 | config→API→前端全棧一氣接通,防幽靈開關復發 | 中 |
| B5 | 5.1 | B2-B4 | Golden 三腿+diff 快照收尾 | 中 |
- 批次 Gate:B1→`pytest tests/momentum/test_statistical_validator.py tests/momentum/core/ -q` 全綠+T-1.1/T-1.2/T-1.3 轉紅 receipt;B2→`pytest tests/momentum/ -q` 全綠+M-C/M-D/M-F/M-H receipt;B3→T-3.1;B4→`npm run build`+M-G 兩態 e2e;B5→G-1/G-2/G-3+全套 momentum 綠。
- 每 Batch 派工 prompt 由編排端(Claude)於派工時依本表+Task 細目組裝,附 SPEC/TODO 路徑+驗證命令(pytest/npm 具體命令見各 Phase Gate)。

## Phase 1 — 統計 kernel(完成後:新顯著性函式 hermetic 可用,生產未接)

### Task 1.1 — HAC 顯著性 kernel
- SPEC ref:§P Task 1.1 / D-A(v2 參數全寫死)　目標:逐 bar 貢獻序列+Newey-West 的 per-feature 顯著性。
- 輸入/輸出:`compute_hac_ic_statistics(features_df: pd.DataFrame, label: pd.Series, horizon: int, *, maxlags: Optional[int]=None) -> dict[str, dict]`(spearman only,COMPOSER-12;無 method 參數);每 feature 回 `{"t_stat": float, "p_value": float, "se": float, "n_obs": int, "maxlags": int}`。
- 實作要點:
  1. per-feature pairwise dropna 對齊 (x,y);fail-closed 條件(先算 L 再判):`L ≥ n_valid-1` 或 `n_valid < max(8, 2*L)` → 全 NaN dict。
  2. `u=zscore(rank(x), ddof=1)`,`v=zscore(rank(y), ddof=1)`,`z=u*v`;`mean(z)` 僅供 t 檢定內部(=(n-1)/n·ρ,**禁**回傳/覆蓋任何 ic_mean 類欄位、禁入 golden 值 hash,CODEX-2)。
  3. **`auto_bw = int(4*(n_valid/100)**(2/9))`(寫死,禁其他頻寬規則);`L = max(auto_bw, horizon-1)`**;顯式 maxlags override:`< horizon-1`→raise ValueError,否則取 override 再過同一 cap。
  4. `se = NW_Bartlett(z, L)`(手刻 Bartlett 核或 statsmodels 皆可,但輸出須與 oracle 恆等);`t=mean(z)/se`;**`p=2*scipy.stats.t.sf(abs(t), df=n_valid-1)`(單一定義,禁 Normal)**。
  5. oracle=statsmodels `OLS(z, ones).fit(cov_type="HAC", cov_kwds={"maxlags": L}, use_t=True)`。
- 修改檔案:`momentum/Analysis/statistical_validator.py`(新函式;不動 `_fdr_bh`/`adjust_multiple_comparisons`)。既有 caller:新建無。
- 不可做:不得在 kernel 內做 FDR/門檻;不得消費 rolling_ic;不得改 `compute_ic_statistics` 簽名(其處置在 Task 2.1);不得引入 method/pearson 分支。
- 邊界:①全 NaN feature→NaN dict;②std=0(常數 rank)→se=0 或 rank 退化→NaN dict;③h=1→L=max(auto_bw,0);④ties 大量並列(>50% 重複值)→rank average 正常出值且 oracle 仍恆等;⑤n 剛好=下限→出值,n=下限-1→NaN;⑥h=63 短序列→fail-closed NaN。
- 風險緩解:D-A 否決 rolling 檢定;M-F 雙腿;M-I 分布守衛。
- 驗證:T-1.1a statsmodels oracle se/t/p allclose(rtol=1e-8,含 h∈{1,5,63},n∈{64,512},ties 重場景);T-1.1b M-A 反保守性(AR(1) φ=0.9 null×200 seeds 固定:舊法假陽率 receipt≫α,新法∈binomial 95% 允收帶,帶寫進碼,`slow_stat` marker);T-1.1c 邊界表全過;T-1.1d M-I:同資料 statsmodels 預設(Normal)p≠oracle p(n=32,assert not allclose);皆 `pytest tests/momentum/test_statistical_validator.py -q`。

### Task 1.2 — FDR 應用層
- SPEC ref:§P Task 1.2 / D-C　目標:BH q 值+n_tests 單一出口。
- 輸入/輸出:`apply_fdr(p_values: dict[str, float], alpha: float) -> tuple[dict[str, float], int]`(q_values 含 NaN 保位,n_tests=finite p 數)。
- 實作要點:①finite p 子集餵既有 `adjust_multiple_comparisons(method="fdr_bh")`;②NaN p 不入 BH,q=NaN;③n_tests=len(finite);④空 dict→({},0)。
- 修改檔案:`momentum/Analysis/statistical_validator.py`。既有 caller:新建無。
- 不可做:不得在此做 α 比較(消費在 _apply_thresholds);不得重寫 BH。
- 邊界:①全 NaN→({feature:NaN...},0);②單 feature→q=p;③ties p 相同→BH 單調性保持。
- 驗證:T-1.2a 手刻 vs statsmodels `multipletests` allclose(M-E,含 ties/單元素);T-1.2b NaN 保位+n_tests 正確。

### Task 1.3 — 測試側 block bootstrap 驗證腿
- SPEC ref:§P Task 1.3 / D-B　目標:kernel p 值的獨立統計對照。
- 輸入/輸出:`tests/momentum/helpers/block_bootstrap.py`(circular block,block=max(h, ceil(n**(1/3)))),回 IC 分布與雙尾 p。
- 實作要點:①對 (x,y) 對同步重抽;②B=2000 固定 seed;③與 Task 1.1 p 在合成資料上同判(顯著/不顯著一致,p 差≤0.05 容差帶)。
- 修改檔案:tests/ 新檔。既有 caller:無。
- 不可做:不進 `momentum/` 生產樹;不改 `bootstrap_estimator.py`。
- 邊界:①n<2*block→skip 註明;②全相同值→退化處理不炸。
- 驗證:T-1.3 對照測試綠+同判斷言可證偽(把 kernel t 人為 ×2 → 轉紅 receipt)。

### Phase 1 測試+Gate
單元(T-1.1a/c,T-1.2a/b)+統計性質(T-1.1b,T-1.3)+邊界表;Gate=B1 命令全綠+轉紅 receipt 齊。

## Phase 2 — 縱向主路徑接線(完成後:stage5 消費 HAC q,舊 pooled 路徑不存在於 p-value 鏈)

### Task 2.1 — stage5 接新 kernel
- SPEC ref:§P Task 2.1　目標:p-value 生產改 HAC,廢 rolling_ic 餵入。
- 輸入/輸出:`_stage5_statistical_validation` 內 `ic_stats = compute_hac_ic_statistics(features_for_stats, label_for_stats, horizon=split_context 的 effective_horizon(無 split 時 _resolve_effective_label_horizon(config, None)))`。
- 實作要點:①horizon 從 split_context["effective_horizon"] 或 resolver 取,禁 default 硬編;②舊 `compute_ic_statistics` **保留但改名 `compute_pooled_ic_statistics_deprecated`,唯一 caller=舊語意遷移測試**,任何生產 import→M-H 結構測試紅;③`ic_stats` 下游 key 相容(t_stat/p_value 語意換新)。
- 修改檔案:`ic_filter_orchestrator.py:_stage5_statistical_validation`;`statistical_validator.py` 舊函式改名。既有 caller:orchestrator:2254 唯一(偵察 receipt)。
- 不可做:不動 `rolling_ic`/`icir` 計算與其 report 輸出;不得留任何生產路徑呼叫 pooled 版。
- 邊界:①split 模式 test 段過短→kernel fail-closed NaN→該 feature p 閘 fail(非 raise 整 run);②labels 無法解析 horizon→resolver 既有 raise 行為傳遞。
- 風險緩解:M-F 雙腿;M-H 結構斷言。
- 驗證:T-2.1a stage5 單元(真小樣本):p 值=直接呼叫 kernel 相等;T-2.1b M-F 腿A/腿B 雙 receipt;T-2.1c M-H(grep+import 圖)。

### Task 2.2 — summary_table/門檻/α 政策
- SPEC ref:§P Task 2.2 / D-C/D-E/D-F　目標:q 進閘、α 政策單一化。
- 實作要點:①`_build_summary_table` 增 `t_stat`/`p_value_adj`(q);`p_value`=HAC raw;②`_stage5_statistical_validation` 在 build 表前:`q_values, n_tests = apply_fdr({f: ic_stats[f]["p_value"]}, alpha_effective)`,對**全 evaluated 集合**(features_df.columns 有 stats 者),先於任何門檻;③`alpha_effective` 三檔(D-E 六格):sufficient→p_value_max;**marginal→p_value_max**;low_confidence→max(p_value_max,0.10)(event_filter 產出欄位保留,消費端只作 α);④threshold_log/report metadata 記 **`alpha_source`**(threshold_default|event_tier_low_confidence),low_confidence 時另標 `selection_mode="exploratory_low_confidence"`;⑤`_apply_thresholds` p 閘:fdr enabled→`row["p_value_adj"]≤alpha_effective`;disabled→`row["p_value"]≤alpha_effective`;⑥threshold_log 增 `alpha_effective/n_tests/fdr_enabled`。
- 修改檔案:`ic_filter_orchestrator.py:_build_summary_table/_apply_thresholds/_stage5_statistical_validation`。既有 caller:stage5 內部+cross_sectional 不走此表。
- 不可做:禁對通過 ic_mean/icir 閘後的子集重算 FDR;禁保留舊 i.i.d. p 欄;禁沿用 adjusted_p_threshold 直接覆蓋 p_value_max 的舊語意。
- 邊界:①全 p=NaN→passed p 閘全 fail、n_tests=0 不炸;②單 feature→q=p;③fdr disabled→行為=HAC raw p 閘(M-G)。
- 驗證:T-2.2a M-B FDR 控制**雙場景**(①獨立 null ②相關 null:50 features 同 latent factor pairwise ρ≈0.7,v2.2;皆含 n_tests 縮水 mutation 轉紅;固定 seed+允收帶入碼);T-2.2b M-D scope 錯配轉紅;T-2.2c α 政策**六格**斷言(sufficient/marginal/low_confidence × fdr on/off,含 alpha_source/selection_mode 欄位值);T-2.2d threshold_log 欄位。

### Task 2.3 — SelectionScope 接線
- SPEC ref:§P Task 2.3 / D-D　目標:檢定範圍可稽核。
- 實作要點:①契約 `split_label` Literal 擴 `"full"`(contracts.py:729,同步 __post_init__ 與 test_scope_contract 斷言——**擴契約屬本刀明示變更,非放寬**);②stage5 建 `SelectionScope(scope_id=f"{run_id/config_hash}:{split_label}", universe_features=list(features_df.columns), split_label="test" if split_context else "full", evaluated_features=[finite p], n_tests, method="fdr_bh" if enabled else "none", base_universe_hash=_base_universe_hash(features_df.index, symbol))`;③入 report metadata `selection_scope`(dict 化)。
- 修改檔案:`momentum/core/contracts.py:SelectionScope`;`ic_filter_orchestrator.py:_stage5_statistical_validation/_build_report_metadata`;`tests/momentum/core/test_scope_contract.py`。
- 不可做:不塞假值(如 full 硬標 test);n_tests 不得≠len(evaluated);**evaluated 嚴格=finite p 子集,NaN-p feature 僅得在 universe**(COMPOSER-9)。
- 邊界:①evaluated 空→n_tests=0 合法建構;②symbol 缺→hash 用既有 fallback 或 raise(依 _base_universe_hash 現行為,不新造)。
- 驗證:T-2.3a 契約單元(擴 full 後全綠+舊三 label 不變);T-2.3b e2e report 含 selection_scope 且 n_tests==len(evaluated)(mutation:n_tests+1→契約 raise 轉紅)。

### Task 2.4 — reporter 導出
- SPEC ref:§P Task 2.4　目標:CSV/JSON 帶新欄。
- 實作要點:`ic_reporter.py` summary 導出列增 `t_stat/p_value_adj`;JSON metadata 增 canonical `significance` 節=`significance.fdr.{enabled,method,alpha_effective}`+`significance.{maxlags,n_tests,scope_id,tested_estimator,fdr_assumption_note}`(D-F,與 config schema 同形,禁別名;note=固定一行 PRDS 披露,v2.2);NaN 序列化=null。
- 修改檔案:`momentum/Analysis/ic_reporter.py`。既有 caller:stage7。
- 不可做:不改既有欄名/順序(向後相容,只增列)。
- 邊界:①舊 report 無新欄讀取端容錯(前端 optional);②NaN 序列化=null。
- 驗證:T-2.4 reporter 單元:新欄在+舊欄 byte 不變(golden 小樣本)。

### Task 2.5 — 刪 apply_significance_filter
- SPEC ref:§P Task 2.5 / D-E　目標:消滅並行幽靈。
- 實作要點:刪函式+其測試遷移為 α 政策測試(T-2.2c 覆蓋其 low_confidence 語意);grep 確認 0 殘留。
- 修改檔案:`statistical_validator.py`;`tests/momentum/test_statistical_validator.py`。
- 不可做:不留 deprecated stub。
- 邊界:⋅(刪除型)。
- 驗證:T-2.5 grep `apply_significance_filter`→僅 git 歷史;全套綠。

### Phase 2 測試+Gate
`pytest tests/momentum/ -q` 全綠+T-2.x/M receipt 齊;Gate=B2。

## Phase 3 — cross_sectional 最小面(完成後:xsec p_value 誠實非 None,無門檻行為變化)

### Task 3.1 — 逐期 IC 顯著性
- SPEC ref:§P Task 3.1 / D-H(v2 修 horizon 丟失)　目標:填掉 p_value=None,horizon 不得丟失。
- 實作要點:①**horizon 於 `_label` 改名前解析**(CODEX-3):labels_path 分支→對 `_select_label_series` 選定的**原始欄名**跑 `_resolve_label_horizon_from_column`;in-frame 分支→對命中的候選欄名跑;皆不可解析→h=None;②h 可解析:xsec 逐期 IC 序列直接作 z 序列餵 NW(mean/se_NW,L=max(auto_bw,h-1));h=None:**p 族欄位全 NaN+metadata 記 `horizon_unresolved`**(與現況 p=None 等價,禁產反保守 p);③`t_stat` 改 HAC(取代 :1077 i.i.d.),`p_value`=HAC p,增 `p_value_adj`(apply_fdr 對該路徑全 feature);④排序仍按 ICIR,不加門檻;⑤`_resolve_cross_sectional_label_horizon`(:359-364)的 fallback-1 行為由上述取代或收斂(禁留兩套)。
- 修改檔案:`ic_filter_orchestrator.py:analyze_cross_sectional`(:958-1096 段)+`_resolve_cross_sectional_label_horizon` 處置。既有 caller:API cross_sectional 端點。
- 不可做:不動 ic_mean/icir/排序;不引入淘汰;禁 fallback h=1 假 horizon。
- 邊界:①n_timestamps<下限→NaN(前端 '--');②單 symbol 退化(橫斷面=1 檔)→上游既有行為不變;③labels_path 欄名 `return_5`→h=5。
- 驗證:T-3.1a xsec 單元:p 非 None+與 kernel 直算一致;i.i.d. t 與 HAC t 在自相關合成資料上分離(mutation:換回 i.i.d.→斷言紅);T-3.1b M-J:labels_path `return_5`→斷言 maxlags≥4(mutation:對 `_label` 解析→轉紅);T-3.1c horizon 不可解析→p 全 NaN+metadata 標記。

### Phase 3 測試+Gate:T-3.1;Gate=B3。

## Phase 4 — config+API+前端全棧接通(完成後:fdr toggle 真有效,前端消費後端統計)

### Task 4.1 — 後端 config plumbing
- SPEC ref:§P Task 4.1 / D-G　目標:fdr 開關真實存在。
- 實作要點:①`ic_config_schema.py` 增 canonical `SignificanceSchema`:`significance.fdr.{enabled: bool=True, method: str="fdr_bh"}`+`significance.maxlags: Optional[int]=None`(嵌套形與 report metadata 同形,CODEX-5,禁 fdr_enabled 平鋪別名);②`_apply_tier_config`(:2882-2931)/`STAGE_OVERRIDE_PATHS` 增 `fdr_correction→significance.fdr.enabled` 映射(UI 邊界唯一轉名點);③stage5/xsec 消費 schema。
- 修改檔案:`ic_config_schema.py`;`ic_filter_orchestrator.py:_apply_tier_config`。既有 caller:API config override 路徑。
- 不可做:不動其他 schema 欄預設;maxlags 顯式給定仍受 horizon-1 下限(Task 1.1 raise);禁引入第四種 fdr 命名。
- 邊界:①未知 key 傳入→既有 schema 行為(拒/忽略)不變;②舊 config JSON 無 significance 節→預設 ON。
- 驗證:T-4.1 schema 單元+**每跳接點斷言**(store JSON→API model→_apply_tier_config→stage5 消費→report metadata,同一 key 鏈 `significance.fdr.enabled`;fdr_correction false→schema false)。

### Task 4.2 — 前端接通+誠實顯示
- SPEC ref:§P Task 4.2 / D-F/D-G　目標:斷鏈接通+刪前端 i.i.d. 推導。
- 實作要點:①`icAnalysisStore.ts`:三 preset `fdr_correction: true`(現況 foundation/intermediate=false);`getEffectiveConfig` 增 `fdr_correction` 送出;②`useICAnalysis.ts` 傳遞不動(走 feature_tiers);③`types.ts ICFeatureInfo`:`p_value` 改 `p_value?: number|null`,增 `p_value_adj?: number|null; t_stat?: number|null`(CODEX-6);④`ICSummaryTable.tsx` **刪 `resolveTStat`(:75-95)與 `resolveConfidenceInterval`(:116-137)全部 i.i.d. 推導**(COMPOSER-7),t-stat/p/q 欄直接讀 item,經共用 finite formatter(非有限→'--');排序用後端值;表頭增 q 欄;CI 無後端值→'--';⑤`FeatureTierPanel.tsx:38` tip 更新為真行為描述;⑥ic_mean tooltip 註明「描述性 rolling 均值,非檢定量」(COMPOSER-6)。
- 修改檔案:上列 5 檔至函式/常數名。既有 caller:IC 分析頁。
- 不可做:不在前端做任何統計推導(含 1.96·SE);不動其他 toggle 語意。
- 邊界:①舊 report(無新欄/p_value null)載入→'--' 不炸(相容測試);②loading/empty 態既有元件行為保持。
- 驗證:T-4.2 `npm run build` 綠+型別檢查;grep `resolveTStat|resolveConfidenceInterval|1.96` 於 ICSummaryTable.tsx→0;元件測試或 e2e 快照:q 欄顯示。

### Task 4.3 — e2e 兩態
- SPEC ref:§P Task 4.3 / M-G　目標:防幽靈開關復發。
- 實作要點:pytest e2e(真小樣本):fdr_correction=false→threshold_log.fdr_enabled=false 且 p 閘用 raw;true→用 q;兩態 passed_features 可分離的構造資料。
- 修改檔案:`tests/momentum/test_ic_filter_orchestrator.py` 增測試。
- 不可做:不 mock 掉 config 映射鏈(須走 _apply_tier_config 真路徑)。
- 邊界:兩態同資料同 seed,唯一差=開關。
- 驗證:T-4.3=M-G 兩態斷言+receipt(off 態唯一判據=report metadata `significance.fdr.enabled=false`;threshold_log.fdr_enabled 僅鏡像,斷言兩者恆等,v2.1)。

### Phase 4 測試+Gate:T-4.1/2/3+`npm run build`;Gate=B4。

## Phase 5 — Golden+選型 diff(完成後:三腿 Golden 綠,diff 快照可審)

### Task 5.1 — Golden 三腿
- SPEC ref:§G G-1/G-2/G-3(v2)　目標:行為變更可審計。
- 實作要點:①G-1 腿:真 3sym **`handoffs/ic1eb_baseline/` 預產快照(編排端於實作前產出,含 HEAD sha;實作端唯讀,禁 git stash/checkout 取舊版)** vs 改後非顯著性欄位**結構化五 hash 相等**(index/columns/dtypes/nanmask/values 各 sha256,CODEX-7);②G-2 腿:per-feature 對照表(p_iid_old/p_hac/q/pass_old/pass_new/reason)寫 `handoffs/IC1EB-GOLDEN-DIFF.md`+新 baseline 凍結(集合 sha256+值 hash)+**`fraction_nan_p`**(12h 短窗 fail-closed 比例,COMPOSER-8 預期管理);③G-3 腿:樣本不足/全 NaN/契約違反場景斷言。
- 修改檔案:tests golden 檔+handoffs 產物。既有 caller:無。
- 不可做:data_cache 只讀;禁合成資料充 Golden;禁任何 git 狀態操作取 baseline。
- 邊界:12h 資料窗較短→fail-closed 觸發即為預期行為,比例入 fraction_nan_p 記錄。
- 驗證:T-5.1 三腿命令+`pytest tests/momentum/ -q` 全綠;五 hash 各自斷言;G-2 diff 由三方簽核審可解釋性。

### Phase 5 測試+Gate:B5;之後進三方數據正確性簽核。

## 追溯表(SPEC ID→TODO)
- Task 1.1→T-1.1a/b/c/d;1.2→T-1.2a/b;1.3→T-1.3;2.1→T-2.1a/b/c;2.2→T-2.2a-d;2.3→T-2.3a/b;2.4→T-2.4;2.5→T-2.5;3.1→T-3.1a/b/c;4.1→T-4.1;4.2→T-4.2;4.3→T-4.3;5.1→T-5.1。
- M-A→T-1.1b;M-B→T-2.2a;M-C→T-1.1a(maxlags 鎖 0 變體)+Task 1.1 raise 斷言;M-D→T-2.2b;M-E→T-1.2a;M-F→T-2.1b;M-G→T-4.3;M-H→T-2.1c;M-I→T-1.1d;M-J→T-3.1b。
- G-1/G-2/G-3→T-5.1。RISK a,b,d→M-A/M-B(a,d)、consumer map+全棧(b)。
- 環境/flag:significance schema canonical(4.1)、fdr_correction 前端(4.2)。
- R1 findings 落點:CODEX-1/COMPOSER-2/4/5→Task1.1+T-1.1a/d;CODEX-2→Task1.1 要點2;CODEX-3→Task3.1+T-3.1b;CODEX-4/COMPOSER-10→Task2.2 要點3/4+T-2.2c;CODEX-5→Task2.4/4.1;CODEX-6→Task4.2 要點3;CODEX-7→Task5.1 五hash;CODEX-8/COMPOSER-13→Task5.1+§0;CODEX-9→§0 統計測試預算;COMPOSER-1/3→SPEC §A;COMPOSER-6/7→Task4.2;COMPOSER-8→Task5.1 fraction_nan_p;COMPOSER-9→Task2.3;COMPOSER-11→Task4.2 要點1;COMPOSER-12→Task1.1 簽名。
