# IC Phase1 1e+1b — 顯著性正確化(HAC + FDR 合刀) — SPEC v2.2【Frozen 2026-07-09】

> **Frozen**:R1-R3 雙家族 adversarial 全閉合+嚴謹度委員會三腿 FREEZE-OK;雙 RECONCILE-STAMP 機檢 PASS(handoffs/IC1EB-RECONCILE.md sha256:b77932d8…)。實作期間改本檔須重開 reconcile。

> 來源:三方偵察 `handoffs/IC1EB-RECON-claude.md`+`IC1EB-RECON-codex.md`+`IC1EB-RECON-composer.md`(task-id ic1eb-recon-*)|日期:2026-07-09|對應 TODO:docs/IC_PHASE1_1E1B_SIGNIF_TODO.md
> v2 2026-07-09:修 R1 雙家族 adversarial 全部 BLOCKING+MAJOR(`handoffs/IC1EB-SPECADV-{codex,composer}.md`,雙 REJECT→本版逐項回應,見 §ADV-RESOLUTION)。
> v2.1 2026-07-09:修 R2——Codex STILL-OPEN(NEW-CODEX-R2-1:`fdr:disabled` 第四命名)→D-G OFF 態統一 canonical;Composer NEW-ISSUE-1/2/3 文案精度(Task 1.1 摘要補 cap/M-I 差值改 seed sweep 區間/樣本下限 8 標註工程慣例)。Composer R2 已 APPROVE(13/13 CLOSED);v2.1 增量送 Codex R3 確認。
> v2.2 2026-07-09:**嚴謹度委員會**(使用者質疑觸發,task ic1eb-rigor-*,三腿=handoffs/IC1EB-RIGOR-{claude,codex,composer}.md,三方 verdict=FREEZE-OK/AMEND-最小)聯集收編:①M-B 增**相關 null 場景**(Claude AMEND:PRDS 從假設變被測性質);②report metadata 增 `fdr_assumption_note` 一行披露(Composer);③§N 登記 `fdr_by`/`romano_wolf` 未來選項、描述性指標正名、策略層 data-snooping epic、monotonicity `ttest_ind` P2(Codex Q4)。三方一致:HAC+BH=本層正確且足夠的標準工具,default 不變。
> 裁定順序出處:handoffs/IC1A-ALIGN-RECONCILE.md(①1-align ✅→**②1e+1b**);1-align 交付凍結 `effective_horizon` resolver=本刀單一真相源。

## §ADV-RESOLUTION(R1 findings → v2 裁決對照)
| Finding | 裁決 | 落點 |
|---|---|---|
| CODEX-1/COMPOSER-2/4/5 auto_bw+p 分布不確定 | ACCEPT:寫死 `auto_bw=int(4*(n_valid/100)**(2/9))`;p=2·sf(|t|,df=n_valid-1);oracle=statsmodels `use_t=True` 同 maxlags;新增 M-I 守衛(default Normal p≠oracle p 斷言);maxlags cap+override 規則入 D-A | D-A/Task1.1/§G/§V |
| CODEX-2 mean(z)=(n-1)/n·ρ 非恰等 | ACCEPT:z 僅供 HAC 截距檢定,**禁**作 IC 點估計替代/禁入 golden 值 hash;ties 重場景測試 | D-A/Task1.1 |
| CODEX-3 xsec `_label` 改名丟 horizon | ACCEPT:Task 3.1 於改名**前**解析 horizon(labels_df 選定欄→resolver;in-frame `return_N`→同);不可解析→p 欄 NaN+metadata 標記(現況等價,不反保守);回歸=labels_path `return_5`→maxlags≥4 | D-H/Task3.1 |
| CODEX-4/COMPOSER-10 α 政策 | ACCEPT:沿用既有產品語意(low_confidence 放寬)但**顯性標記**:threshold_log/report 記 `alpha_source`+`selection_mode="exploratory_low_confidence"`;marginal tier 明定=p_value_max;六格測試 | D-E/Task2.2 |
| CODEX-5 fdr 四名並存 | ACCEPT:canonical 路徑=`significance.fdr.{enabled,method,alpha_effective}`(config schema+report metadata 同形);前端 `fdr_correction` 僅 UI 邊界映射;每跳接點測試 | D-F/D-G/Task4.1/4.2 |
| CODEX-6 nullability 遷移不完整 | ACCEPT:types.ts `p_value?: number\|null`+`p_value_adj?: number\|null`;共用 finite formatter '--';舊 report 相容測試 | D-F/Task4.2 |
| CODEX-7 G-1 hash 蓋不住 identity | ACCEPT:結構化五 hash(index/columns/dtypes/nanmask/values 各 sha256);`.to_numpy().tobytes()` 僅附加 | §G |
| CODEX-8/COMPOSER-13 git stash 陷阱 | ACCEPT:baseline=實作**前**由編排端跑 snapshot 落 `handoffs/ic1eb_baseline/`(不可變產物),實作端唯讀;刪 git stash 字樣 | §G/Task5.1 |
| CODEX-9 統計測試預算 | ACCEPT:固定 seed、允收帶寫進碼、`slow_stat` marker+預算上限 | §V/Task1.3 |
| COMPOSER-1 統計前提當事實 | ACCEPT:§A 增「統計假設」子節(H0/全樣本 rank 相依/NW 漸近/適用邊界=assumption 非 fact);§V 短樣本/大 h receipt | §A/§V |
| COMPOSER-3 0.984 寫死 | ACCEPT:改「≈0.98 量級」 | §A |
| COMPOSER-6 檢定量 vs 展示 ic_mean 雙軌 | ACCEPT:D-F 明文披露(ic_mean=rolling 描述性;檢定=bar-level);metadata 記 tested estimator;UI tooltip 更新;不新增欄(防 scope creep) | D-F/Task4.2 |
| COMPOSER-7 CI 前端推導漏列 | ACCEPT:`resolveConfidenceInterval`(1.96·SE)一併刪,無後端 CI→'--';consumer map 9 補列 | §C/Task4.2 |
| COMPOSER-8 樣本下限 8 無出處 | ACCEPT:保留 `max(8, 2·effective_maxlags)`(8=rank corr 最小意義樣本,對齊 1-align oracle 下限);G-2 增 `fraction_nan_p` receipt(12h 短窗預期管理) | D-A/§G |
| COMPOSER-9 evaluated 嚴格性 | ACCEPT:Task 2.3 明寫 evaluated=finite p 子集,NaN 僅在 universe | D-D/Task2.3 |
| COMPOSER-11 preset 現況 vs 目標 | ACCEPT:§A 標「現況 2/3 false→Task 4.2 改 true」 | §A |
| COMPOSER-12 method 參數幽靈 | ACCEPT:刪 kernel `method` 參數(spearman only;pearson §N) | Task1.1/§N |

## §RISK 風險分級(gate 讀此決定要求強度)
- **大小**:大。跨模組(statistical_validator ↔ orchestrator ↔ contracts ↔ config schema ↔ api ↔ frontend 三欄全棧)、selection 主鏈行為變更。
- **命中**:(a) 數值品質——p-value 系統性反保守,選特徵=選噪音;(b) 跨模組共用路徑;(d) ML/回測正確性——顯著性是 IC Gatekeeper 的核心閘。
- **RISK-HIT 宣告**(機檢行):
RISK-HIT: a,b,d
- (a)(d) → §G Golden 必填、雙家族 adversarial 必跑、三方數據正確性簽核。實作 Codex、review Composer(依 HANDOFF 本 epic 分工)。

## §A 假設與待使用者確認
- **FACT-RECEIPT**(三方偵察,HEAD 57e9ac8;詳細 receipt 見三份 RECON 檔,此處摘關鍵):
  - **病灶①(pool+i.i.d.)**:`compute_ic_statistics`(statistical_validator.py:24-32)經 `_collect_values`(:75-83)把每 feature **三個重疊窗 [21,63,126] 的 rolling IC 串接成一列**,`_compute_stats`(:95-128)跑 `ttest_1samp` i.i.d.+普通 t CI。Composer 實跑:500 列→串接 n_obs=1293;**window_63 序列 lag-1 自相關 ≈0.98 量級**(stride=1,相鄰窗共享 w-1 點;R1 兩家族獨立複測 0.984/0.978,seed 相依)。p-value 反保守數量級。
  - **病灶②(裸 p 無 FDR)**:`_apply_thresholds`(ic_filter_orchestrator.py:2590-2593)裸 `p≤p_value_max`(0.05,schema:104);n_tests=stage5 進場全欄卻零多重比較校正。
  - **幽靈 ×4**(生產 0 caller,三方 grep 一致):`adjust_multiple_comparisons`+`_fdr_bh`(statistical_validator.py:58-73,150-166;**手刻 BH 與 statsmodels multipletests allclose=True,雙委員實測**);`apply_significance_filter`(:34-56);`SelectionScope`(contracts.py:724-742,n_tests==len(evaluated) 驗證);stage5 `tier` 死變數(:2255)。
  - **前端斷鏈**:store `fdr_correction` toggle `getEffectiveConfig` 不送(icAnalysisStore.ts:290-325);後端 schema 無 fdr 欄;`ICSummaryTable.resolveTStat`(:75-95)+`resolveConfidenceInterval`(1.96·SE,:116-137)**前端自己用 i.i.d. 公式推 t-stat/CI**(cross_sectional fallback);`_apply_tier_config`(:2882-2931)不讀 fdr_correction。preset 現況 `fdr_correction`:foundation/intermediate=false、advanced=true(**現況陳述**;目標=Task 4.2 三者改 true)。
  - **xsec horizon 丟失(R1 CODEX-3,Claude 親驗)**:labels_path 分支把選定 label 欄改名 `_label`(:966-968)後才 `_resolve_cross_sectional_label_horizon(label_col)`(:359-364,非 `return_N` fallback **回 1**)→ `return_5` 外部 labels 的真 horizon 在 xsec 路徑丟失(:986);in-frame 候選欄 `label/future_return/target/y` 同樣 fallback 1。
  - **cross_sectional 路徑**(orchestrator:1050-1096):逐期橫斷面 IC(真 Fama-MacBeth 型)算 `t_stat=mean/(std/√n)` i.i.d.,`p_value` 硬填 None(:1088),僅 ICIR 排序、不過 `_apply_thresholds`;h>1 重疊 label→逐期 IC 亦自相關。
  - **event tier**:`check_sample_size`→`adjusted_p_threshold=0.10`(event_filter.py:93-99,128-144)覆蓋 `p_value_max`(:2257-2260)——放寬的是**閾值**,與 FDR 校正 p 值是兩套語意。
  - **工具面**:venv statsmodels **0.14.6**(import+cov_hac 實測 OK);`bootstrap_estimator.py`=i.i.d. 重抽 ML 指標,無 block,不可直接複用。
  - **horizon 同源**:`_resolve_effective_label_horizon`(:188-231)/`_resolve_label_horizon_from_column`(:234-243)=1-align 交付單一真相源;h-bar forward return→label 本身 MA(h-1)。
  - **n_tests 量級註記**:Codex 引 manifest `total_features=437066`=FF raw artifact 總量(Claude 抽驗:BTCUSDT/1h manifest row_count=20352/total_features=437066/group_count=1009),**非 stage5 輸入**;stage5 n_tests=materialize 後 `features_df.columns`(>5000 僅 warn,:2025-2029)。n_tests 定義採**結構性**(=len(evaluated)),不依賴量級假設。
  - stage5 已有 test 段資料:`_slice_by_mask`(:2248-2252)產 `features_for_stats/label_for_stats`→per-bar 序列可就地計算,無新資料通道。
  - `ic_autocorr`(ic_engine.py:442-464)只診斷,report 不輸出(stage7 無此 key)。
- **統計假設(v2,COMPOSER-1;assumption 非 fact,由 §V 統計性質測試+G-2 真資料 diff 把關)**:
  - H0=bar-level Spearman ρ=0(檢定對象=逐 bar 秩相關,非 rolling 窗均值)。
  - 全樣本 rank 使 z_t 存在弱全域相依(rank 是 n 點函數);視為漸近可忽略(n≥下限),**這是假設**——短樣本行為由 §V 邊界 receipt(n≈下限、h∈{1,5,63})實證,帶外=修法重議。
  - NW/HAC 依賴平穩混合條件與 Bartlett 核漸近;h>1 之 label 重疊給出已知 MA(h-1) 結構=maxlags 硬下限的依據。
  - `mean(z)`(ddof=1 標準化)=`(n-1)/n·ρ_spearman`,**非恰等 ρ**(CODEX-2 實測 0.98@n=50):z 僅供 HAC 截距 t 檢定(標度在 t 中消去);**禁**以 mean(z) 替代/覆蓋任何 IC 點估計欄、禁入 golden 值 hash。
- **設計裁決(D-A~D-H,技術裁決,由雙家族 adversarial 收斂,不問使用者;出處=三方 RECON 判斷節)**:
  - **D-A 檢定 kernel=逐 bar 貢獻序列 + Newey-West(主),參數全寫死(v2)**:對 test 段(stage5 既有 `features_for_stats/label_for_stats`)算 `u_t=zscore(rank(x_t), ddof=1)`,`v_t=zscore(rank(y_t), ddof=1)`,`z_t=u_t·v_t`;`se=NW_Bartlett(z, L)`,`t=mean(z)/se`,**p=2·t.sf(|t|, df=n_valid-1)**(單一定義,禁 Normal)。
    - **`auto_bw = int(4*(n_valid/100)**(2/9))`**(=statsmodels `maxlags=None` 慣例,R1 雙家族 VERIFY 一致);**`L = max(auto_bw, h-1)`**,h 由 horizon resolver 同源。
    - **cap/fail-closed**:`L ≥ n_valid-1` 或 `n_valid < max(8, 2*L)` → 全 NaN(8=**工程下限**,對齊 1-align Tier-2 有效樣本<8→raise 的既有慣例,非文獻常數;v2.1 COMPOSER NEW-ISSUE-3 註記);顯式 maxlags override 仍受 `≥h-1` 下限(低於→raise ValueError)與同一 cap。
    - **oracle 單一路徑**:statsmodels `OLS(z, ones).fit(cov_type="HAC", cov_kwds={"maxlags": L}, use_t=True)` 之 se/t/p 與 kernel `allclose(rtol=1e-8)`;**M-I 守衛**:同資料 `use_t` 預設(Normal)之 p ≠ oracle p 斷言(n=32 相對差 0.2%–2.4% 量級 seed 相依,R2 sweep 皆足以 not-allclose,防靜默走錯分布)。
    - **明文否決**「對 rolling 平滑序列做檢定」:rolling IC(單窗或串接)的自相關主體是視窗平滑人工製品(w−1 階,w=63 時 NW lag 需≥62,短 test 段不可行),不是合法檢定對象;rolling IC 保留為描述性診斷,數值不動。
  - **D-B 驗證腿=circular block bootstrap**(block≥h,對 (x,y) 對重抽算 IC 分布)——**測試側**對照 kernel(合成資料上顯著性同判+p 差≤0.05,pytest T-1.3),不進生產路徑。
  - **D-C FDR 消費**:對 stage5 進場**全 evaluated 集合**(summary_table 全列,含之後被 ic_mean/icir 閘掉者)先算 BH q(復用既有 `adjust_multiple_comparisons`,fdr_bh),`_apply_thresholds` p 閘改消費 `p_value_adj≤α`;**禁**對通過前置閘的子集算 FDR(selection-conditioning 使 n_tests 縮水、FDR 失控)。NaN p(樣本不足)不入 BH、該 feature p 閘 fail-closed(現行 `_passes_threshold` None/NaN→False 語意保留)。
  - **D-D SelectionScope 接線**:stage5 產 `SelectionScope(scope_id, universe_features=stage5 進場全欄, split_label(test/full→契約僅 train/val/test:full run 映射裁決見 Task 2.3), evaluated_features=有 finite p 者, n_tests=len(evaluated), method="fdr_bh", base_universe_hash=_base_universe_hash 復用)`入 report metadata;違反契約=raise(fail-closed)。
  - **D-E event tier×FDR(v2 六格)**:`adjusted_p_threshold` 語意改為作用在 **FDR α**:sufficient→α=p_value_max;**marginal→α=p_value_max**(明定,COMPOSER-10);low_confidence→α=max(p_value_max,0.10)。low_confidence 放寬=**沿用既有產品語意**(CODEX-4 裁決:非數學必然,顯性標記)——threshold_log/report metadata 記 `alpha_source`(threshold_default|event_tier_low_confidence),後者同時標 `selection_mode="exploratory_low_confidence"`,前端可見。`apply_significance_filter` 幽靈函式**刪除**(其 low_confidence 語意併入 α 政策;禁兩套並行)。
  - **D-F 欄位語意(v2)**:summary_table `p_value`=HAC raw p(舊 i.i.d. 值**不保留**——統計錯誤值保留=誤導),新增 `p_value_adj`(q)、`t_stat`(HAC);**canonical 命名(CODEX-5)**:config schema 與 report metadata 同形=`significance.fdr.{enabled,method,alpha_effective}`+`significance.{maxlags,n_tests,scope_id,tested_estimator,fdr_assumption_note}`(note 固定一行披露 BH 之 PRDS 假設與高相關特徵下輕微樂觀風險,v2.2 Composer);前端 `fdr_correction` 僅在 UI 邊界映射到 `significance.fdr.enabled`,禁第四種名字。**nullability(CODEX-6)**:types.ts `p_value?: number|null`、`p_value_adj?: number|null`、`t_stat?: number|null`,共用 finite formatter(非有限→'--'),舊 report(無新欄)相容測試。**估計量披露(COMPOSER-6)**:UI `ic_mean`=rolling 窗描述性均值,檢定量=bar-level(metadata `tested_estimator="bar_level_spearman"`),tooltip 明示兩者非同一估計量;threshold p 閘只綁檢定欄位;不新增展示欄(防 scope creep)。前端 **刪 resolveTStat(:75-95)+resolveConfidenceInterval(:116-137)** 全部 i.i.d. 推導,一律消費後端欄位。
  - **D-G FDR 預設 ON**(驗過就別預設關閉鐵律):後端 schema `significance.fdr.enabled=true` 預設;前端三 preset `fdr_correction` 統一 true,toggle 留作對照/逃生口。**OFF 態表述(v2.1,R2 NEW-CODEX-R2-1)**:唯一真相=canonical `significance.fdr.enabled=false`(config+report metadata 同 key),p 閘走 HAC raw p;**禁**任何其他 off 標記字串;threshold_log 內部欄 `fdr_enabled` 僅為 metadata 鏡像(值必與 canonical 相等,T-4.1 斷言)。**HAC 無 production 開關**(正確性修復;off 對照僅測試 monkeypatch,同 1-align M5 雙腿模式)。
  - **D-H cross_sectional 最小面入刀(v2 修 horizon 丟失)**:同一 kernel 對逐期 IC 序列(其 z 序列=逐期 IC 本身)產誠實 `t_stat/p_value/p_value_adj`(NW maxlags 同 D-A 下限 h-1)填掉 None;**不新增門檻行為**(維持 ICIR 排序)。**horizon 於 `_label` 改名前解析**(CODEX-3):labels_path→對 `_select_label_series` 選定的**原始欄名**跑 resolver;in-frame→對命中的候選欄名跑;皆不可解析→**p 族欄位=NaN+metadata 記 `horizon_unresolved`**(與現況 p=None 等價,不產反保守 p);回歸測試=labels_path `return_5`→斷言 maxlags≥4。
- **待確認:無**(D-A~D-H 屬技術裁決,由 R1/R2 adversarial 閉合複驗把關;前端 preset 預設改 true 依「驗過就別預設關閉」鐵律,不另問)。

## §C 約束
- 解耦 7 條保持(`grep "from api\." momentum/`→0);statistical kernel 落 `momentum/Analysis/statistical_validator.py`(或同層新模組),契約落 `momentum/core/contracts.py`。
- **consumer map(每項標處置)**:
  1. `_stage5_statistical_validation`(:2236-2294)— 接新 kernel+FDR+SelectionScope(Task 2.1-2.3)
  2. `_apply_thresholds`(:2562-2627)— p 閘消費 `p_value_adj`(Task 2.2)
  3. `_build_summary_table`(:2521-2560)— 增 `t_stat/p_value_adj` 欄(Task 2.2)
  4. `ic_reporter.py`(CSV/JSON 導出 p_value)— 同步新欄(Task 2.4)
  5. cross_sectional summary(:1050-1096)— D-H 填 None(Task 3.1)
  6. `event_filter.adjusted_p_threshold` 消費點(:2257-2260)— α 語意遷移(Task 2.2)
  7. `apply_significance_filter`(statistical_validator.py:34-56)— 刪除+測試遷移(Task 2.5)
  8. `SelectionScope` 契約+`tests/momentum/core/test_scope_contract.py` — 接線+補生產路徑測試(Task 2.3)
  9. 前端:`ic_config_schema.py`→`_apply_tier_config`(:2882-2931)→`icAnalysisStore.getEffectiveConfig`(:290-325)→`useICAnalysis.ts`→`FeatureTierPanel.tsx:38`→`types.ts ICFeatureInfo`→`ICSummaryTable.tsx`(刪 resolveTStat :75-95 **與 resolveConfidenceInterval :116-137** 全部推導)(Task 4.x;全棧三欄連通,禁半接;canonical 命名見 D-F)
  10. `compute_ic_statistics` 既有測試(`tests/momentum/test_statistical_validator.py`)— 語意變更遷移,不得刪斷言充當修法(diff 驗)
- **不改**:IC 點估計/ICIR/rolling IC/ic_decay/grouped_ic 數值(描述統計,byte 不動);label 生成;cut1/cut2/1-align 已簽核行為;deep 模組(§N);`bootstrap_estimator.py` 生產介面。
- 膨脹升級信號:若須動 `factories.py`/`protocols.py` 或新 caller 超出 map → 停,回報。

## §G Golden / Baseline((a)(d) 必填)
- **型態聲明**:本刀=**行為變更型**(p-value/passed_features 會變),非 byte-equal;Golden 雙腿:
  - **G-1 不變腿(v2 結構化五 hash,CODEX-7)**:IC 點估計/ICIR/rolling IC/monotonicity/coverage/turnover 等**非顯著性欄位**改前後相等,hash 對象=結構化 payload:`index_sha256+columns_sha256(含順序)+dtypes_sha256+nanmask_sha256(isna bytes)+values_sha256`;`.to_numpy().tobytes()` 僅作附加值 hash。證明只動了顯著性推斷且 feature identity/對齊未漂。
  - **G-2 變更腿(selection-diff 快照)**:真資料舊 vs 新 per-feature 對照表(`p_iid_old / p_hac / q / pass_old / pass_new / 淘汰原因`)落檔 `handoffs/IC1EB-GOLDEN-DIFF.md`+新路徑 baseline 凍結(名稱集合 sha256+每 feature p/q 值 hash)+**`fraction_nan_p` 統計**(COMPOSER-8:12h 短窗 fail-closed 比例=預期管理 receipt);變化方向可解釋性由三方簽核審(預期:高自相關假顯著 feature 轉紅)。
  - **baseline 取得程序(v2,CODEX-8/COMPOSER-13;禁 git stash/checkout)**:實作動工**前**由編排端(Claude)在當前 HEAD 跑 baseline snapshot(舊路徑 report+五 hash)落 `handoffs/ic1eb_baseline/`(含產生時 HEAD sha 記錄),視為不可變產物;實作端與 Golden 測試**唯讀**消費之。
  - **G-3 fail-closed**:樣本不足(n_valid<max(8,2·maxlags))/全 NaN/std=0→p=NaN→p 閘 fail;SelectionScope 違約→raise。
- **資料**:真實 `data_cache/features/` 3sym(1h 4a8a0b37+12h e53e2290/f754aad4)+`kline_cache.h5`;禁合成 fixture 充 Golden(hermetic 單元另計)。**data_cache 唯讀紅線**:輸出一律重導測試 tmp;postflight 快照零變化。
- **統計 oracle**:kernel 對照 statsmodels(OLS z_t~1, cov_type=HAC)同 maxlags 下 se/t/p `allclose(rtol=1e-8)`;BH 對照 `multipletests` 恆等(既有雙委員 receipt 轉為回歸測試)。

## §P Phase 與依賴

### Phase 1 — 統計 kernel(依賴:無)
**Task 1.1 — HAC 顯著性 kernel**:`statistical_validator.py` 新 `compute_hac_ic_statistics(features_df, label, horizon, ...)`(D-A 逐 bar 貢獻序列+NW;回 per-feature `{t_stat, p_value, se, n_obs, maxlags}`);NaN 對齊=pairwise dropna;`L≥n_valid-1` 或 `n_valid<max(8,2·L)`→NaN(fail-closed,同 D-A cap)。oracle=statsmodels HAC use_t=True allclose(rtol=1e-8)。
**Task 1.2 — FDR 應用層**:`apply_fdr(p_values: dict, alpha) -> (q_values, n_tests)` 包裝既有 `adjust_multiple_comparisons`;NaN p 排除於 BH、q=NaN;n_tests=finite p 數,與 SelectionScope 驗證同源。
**Task 1.3 — 測試側 block bootstrap 驗證腿**(D-B):circular block(block≥h)對照 Task 1.1 p 值容差帶;僅 tests/。

### Phase 2 — 縱向主路徑接線(依賴:P1)
**Task 2.1** stage5 改呼叫新 kernel(輸入=既有 `features_for_stats/label_for_stats`+resolver horizon;**廢棄 rolling_ic 餵 p-value 路徑**);`compute_ic_statistics` 舊 pooled 函式刪除或降級為 deprecated 純診斷(裁決入 TODO,禁靜默雙軌)。
**Task 2.2** `_build_summary_table` 增欄;`_apply_thresholds` p 閘消費 `p_value_adj`(FDR off 時=HAC raw p);event tier→α 政策(D-E);threshold_log 記 `alpha_effective/n_tests`。
**Task 2.3** SelectionScope 建構+入 report metadata;full run(無 split)之 `split_label` 映射裁決:契約 Literal 擴 `"full"` 或 metadata 另欄(TODO 定案,禁塞假值)。
**Task 2.4** `ic_reporter` 導出新欄。
**Task 2.5** 刪 `apply_significance_filter`+遷移其測試至 α 政策測試。

### Phase 3 — cross_sectional 最小面(依賴:P1)
**Task 3.1** 逐期 IC 序列接 kernel 產 `t_stat/p_value/p_value_adj` 填 None(D-H);不動排序/無門檻;n_tests=該路徑 evaluated 欄數。

### Phase 4 — config+API+前端全棧接通(依賴:P2)
**Task 4.1** `ic_config_schema.py` 增 `significance`節(fdr enabled 預設 true/method/maxlags 策略);`_apply_tier_config` 讀 `fdr_correction` override。
**Task 4.2** 前端:store `getEffectiveConfig` 送 fdr_correction(三 preset 統一 true);`useICAnalysis` 傳遞;types.ts `ICFeatureInfo` 增 `p_value_adj/t_stat` 等;`ICSummaryTable` 刪 resolveTStat/SE 推導改消費後端欄位(含排序/空值 '--');`FeatureTierPanel` tip 更新。
**Task 4.3** e2e 兩態驗證(fdr on/off 真後端行為差異+report 標記)。

### Phase 5 — Golden+選型 diff(依賴:P2-P4)
**Task 5.1** G-1/G-2/G-3 落地+`IC1EB-GOLDEN-DIFF.md` 產出;全套 momentum 綠。

## §V 驗證策略與邊界測試目錄
- **mutation(對照 TEST_DESIGN_CHARTER,全部附轉紅 receipt)**:
  - M-A 反保守性可證偽:合成 AR(1) φ=0.9 null(真 IC=0)×200 seeds→舊 i.i.d. 法假陽率 receipt(預期≫α);新 kernel 假陽率∈α 的 binomial 95% 允收帶;帶外=FAIL。
  - M-B FDR 控制(v2.2 雙場景):①獨立 null:m=100 null+5 true(植入相關)×100 seeds→實測 FDR≤α(允收帶);②**相關 null(PRDS 實測,嚴謹度委員會 Claude AMEND)**:50 個由同一 latent factor 生成、pairwise ρ≈0.7 的 null features+5 true→實測 FDR 仍≤α 允收帶;帶外=BH 於本資料型不可用,升級 `fdr_by` 並重審。n_tests 改成「只數通過前置閘子集」的 mutation→FDR 估計超帶轉紅。
  - M-C maxlags 下限 mutation:h=5 資料把 maxlags 鎖 0→se 縮水→與 statsmodels oracle 偏離斷言轉紅(horizon 同源接線可證偽)。
  - M-D scope 錯配 mutation:FDR 在 train 段算、test 段消費→SelectionScope/斷言轉紅。
  - M-E BH 恆等回歸:手刻 vs statsmodels multipletests allclose(含 ties/全 NaN/單元素邊界)。
  - M-F 雙腿程序(同 1-align M5):腿A=新 kernel ON+M-A 資料→PASS;腿B=monkeypatch 回舊 pooled 路徑→同一測試必 FAIL;雙 receipt。
  - M-G 前端接通:fdr toggle OFF→後端真走 raw HAC p(report 標記)+ON→走 q;兩態 e2e 斷言(防幽靈開關復發)。
  - M-H 結構斷言:新路徑不存在多窗串接(`_collect_values` 不在 p-value 鏈上);grep/呼叫圖測試。
  - M-I(v2)分布守衛:同資料 statsmodels HAC 預設(Normal)p ≠ oracle(use_t=True)p 斷言(n=32 相對差~1.6%,防靜默走錯分布)。
  - M-J(v2)xsec horizon 回歸:labels_path `return_5`→maxlags≥4 斷言;mutation 改回 `_label` 後解析→轉紅。
- **層級**:單元(kernel hermetic+statsmodels oracle)+統計性質測試(M-A/M-B,固定 seed、允收帶寫進碼、`slow_stat` marker+單測預算上限 CODEX-9)+Golden(真 3sym 雙腿)+e2e(前後端兩態)+短樣本/大 h 邊界 receipt(n≈下限、h∈{1,5,63},COMPOSER-1)。
- **防假綠**:diff 既有測試斷言;`test_statistical_validator.py` 語意遷移逐條列帳,不得放寬。
- **邊界目錄**:☑ 空DF ☑ 全NaN ☑ std=0(z 常數→se=0→NaN fail-closed)☑ n<2·maxlags ☑ h=1(maxlags 下限 0+自動頻寬)☑ ties(rank 並列)☑ NaN 孔 pairwise ☑ 單 feature(n_tests=1,BH=raw)☑ 全 p=NaN ☐ Inf(上游 gate 已擋,§N)。

## §R 回退
- 每 Task 獨立 commit 可 revert;HAC 無 production 開關(off 對照=測試 monkeypatch);FDR config flag=文檔化逃生口(預設 ON);Golden G-2 diff 無法解釋→不 merge;passed_features 變化屬正確性修復,metadata 標記,不做相容 shim。

## §N N/A 登記
- **deep 路徑顯著性**(factor_return_analyzer `newey_west_adjusted:False` 硬編:103、trend/quality `significance_level`):另立刀;本刀=selection 主鏈+cross_sectional 最小面,不暗示全平台。
- **bootstrap_estimator 泛化為生產 block bootstrap**:D-B 驗證腿僅測試側(tests/momentum/helpers/block_bootstrap.py);泛化=另立。
- **ic_autocorr report/UI 接線**(診斷欄):非本刀阻塞;偵察已錄 preset toggle 無映射,歸前端 wiring 清單。
- **IC-first raw/ML 孤島路徑**:沿 1-align §N 另立 epic。
- **Inf 邊界**:上游 NaN/inf gate 職責(FF pipeline),本刀不重複。
- **1f report schema flatten/空圖**:依裁定順序後續刀。
- **pearson IC 顯著性**(COMPOSER-12):kernel 僅 spearman(與 selection 主鏈 default_method 一致);pearson 需求另立。
- **FDR 方法升級選項**(v2.2 嚴謹度委員會):`significance.fdr.method` 未來允許 `fdr_by`(任意相依保證)/`romano_wolf`(resampling stepdown,需聯合 null bootstrap);本刀 default=`fdr_bh`+M-B 相關 null 實測把關;M-B 帶外時 BY 升級為既定路徑。
- **描述性指標正名**(v2.2):`ic_mean/icir/ic_hit_rate/monotonicity_score/ic_decay/grouped_ic`=描述性門檻/診斷,非統計檢定,本刀不升級;`monotonicity_tester ttest_ind`(i.i.d. long-short p,現未入閘)若未來接線須先 HAC/block 化(ROADMAP P2,Codex Q4)。
- **策略層 data-snooping**(v2.2):White RC/Hansen SPA/Deflated Sharpe/PBO=回測/策略選擇層,另立 epic(入 ROADMAP);本刀 FDR 不替代之。
