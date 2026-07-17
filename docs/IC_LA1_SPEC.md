# IC-ANALYSIS-LOOKAHEAD Phase LA-1(P1) — SPEC

> **版本 v0.4.3**(round3 codex 抓 migration 表幽靈第 6 列已修:「:23 基本 analyze」實屬 test_quantile_exceeds_samples,表改既有 5 nodeid+1 新增 test_long_short_fixed_q;round2 §A 基數 8→12 已修;round1 兩處舊文字殘留已修:B1.3 邊界「首段 unknown」→委派 B1.2、B4「三種」→≥5;R3 三家高度收斂:R2 四大家族 CLOSED;殘 R3-B1 name_map namespace/R3-B2 prefix 契約/R3-B3 出口 carrier/R3-B4 migration 表 + 3 MAJOR 全數落地;reconcile 見 `handoffs/LA1-SPEC-ADV-R{1,2,3}-RECONCILE.md`)
> 來源 PLAN/診斷：`handoffs/LA1-RECON-SYNTHESIS.md`(四方聯合偵察) | 日期：2026-07-16 | 對應 TODO：`docs/IC_LA1_TODO.md`(待生成)
> 前身：LA-0(P0)已合併 main;`momentum/Analysis/pit_stats.py` 七原語(`PIT_STATS_VERSION=la0_b1_v1`, `MIN_SAMPLES=100`, §MS)為本票基礎。權威盤點 `handoffs/ICLOOKAHEAD-MASTER.md` P1 節。

## §RISK 風險分級
- **大小**：**大**。
- **命中高風險原則**：(a) 數值/資料品質(regime/long_short 分位洩漏污染研究結論)、(b) 跨模組共用路徑(ic_engine/long_short/orchestrator/regime_detector + 前端)、(c) 多 phase(B0-B4)、(d) ML/回測正確性(look-ahead 直接偽造 IC/建議)。
- **RISK-HIT 宣告**：
RISK-HIT: a,b,c,d
- → §G Golden 必填、adversarial review 必跑(三家)。

## §A 假設與待使用者確認

**已驗證事實（12 條 FACT-RECEIPT,含真 kline 實跑 receipt）：**
- FACT-RECEIPT: `grep -n nanpercentile ic_engine.py` → `:1106-1107 np.nanpercentile(vol_values, high_pct/low_pct)`(全序列 vol 分位)（Claude 實跑 2026-07-16）
- FACT-RECEIPT: P1-1 leak — BTC/1h drop50 `early high_flip=152 low_flip=322`;Composer trunc@1500 `high_flip=100 low_flip=85, grouped IC absdiff=0.0099`;PIT `pit_expanding_bounds` early_flip=**0**（Grok+Composer 實跑真 kline 2026-07-16）
- FACT-RECEIPT: P1-2 leak — Grok drop20 `bin_flip=254/8132`;Composer `bin_flip=94/1500 + recommendation full=只做空→trunc=雙向`;PIT `pit_expanding_qcut_label` early_flip=**0**（Grok+Composer 實跑 2026-07-16）
- FACT-RECEIPT: P1-3 silent — `inspect.getsource(_run_full_sample_fallback)` 不含 `logger.`;frontend grep `oos_guarantees`=**0 hits**（三方 2026-07-16）
- FACT-RECEIPT: 原語簽名 — `pit_expanding_bounds(series, lo_q, hi_q, min_samples)` warmup 回 (-inf,+inf)(pit_stats.py:358);`pit_expanding_qcut_label(series, q, min_samples)` warmup/退化回 NaN(:311)（Claude 讀碼 2026-07-16）
- FACT-RECEIPT: 雙閘 — `by_regime: bool = True`(ic_config_schema.py:83) **且** `include_regime_analysis: bool = True`(:153, orch:2582 消費)（Claude 實跑 2026-07-16）
- FACT-RECEIPT: P1-1b — `regime_detector.py:306-307 high_thresh=np.nanpercentile(vol_values,80)`(hardcode,kmeans 樣本不足 fallback,同病)（Composer 抓+Claude 實跑 2026-07-16）
- FACT-RECEIPT: min_samples — first_valid(vol rolling55 疊 100 finite)=pos **154**;真實樣本足(1h 92-96% 可用,12h >1.5k)（Grok+Composer 實跑 2026-07-16）
- FACT-RECEIPT: P1-1c — `regime_detector.py:257 _align_labels` 用全期 raw_labels×volatility 排序命名;prefix mutation(seed=0,n=300,trunc=180)→`early_label_flips=88/180`（Codex 實跑+Claude 讀碼獨立證實 2026-07-16）
- FACT-RECEIPT: `oos_guarantees` 只寫不讀 — `_apply_thresholds` 原始碼不含 `oos_guarantees`(inspect.getsource);degraded 照常產 `passed_features`;persist(:2988,:3333)+task completed 先於紅標（Composer+Codex 實跑 2026-07-16）
- FACT-RECEIPT: reduced-bin 非 NaN — `pit_expanding_qcut_label` synthetic t=120,q=5,actual_bins=1→label=0.0(NON-NaN)（Composer 實跑 2026-07-16）
- FACT-RECEIPT: caller 圖 — `regime_detector` 消費者=IC kmeans(ic_engine:1137)+XGBoost Market_Phase fallback(xgboost_task_service:473-482);**LightGBM 0 hits**（Claude 實跑 grep 2026-07-16）
- 註:P1-1/P1-2 洩漏 flip 精確數各家實跑不同(方法未鎖;方向與規模一致)→ mutation 定義以 `tests/golden/la1/gen_baseline.py` 內嵌為 canonical,SPEC 不鎖口頭數字。

**待確認：無**（P1-1b/P1-1c scope 皆已裁;D1/D3/D4 已於 R1 reconcile 鎖死,不再 defer）。

**已確認結果**：
- 2026-07-16 使用者裁定 P1-1b(kmeans fallback 同族洩漏)**併入 LA-1**(AskUserQuestion)。
- 2026-07-16 使用者裁定 P1-1c(kmeans 主路徑 `_align_labels` 全期命名洩漏,R1 codex 抓+Claude 獨立證實 88/180 flip)**併入 LA-1 完整修**;XGBoost 尚未開始使用,行為變更可接受。LightGBM 實跑 caller 圖 0 hits 不受影響。

## §C 約束
- 解耦 7 條不變(`momentum/` 不 import `api/`;原語留 `momentum/Analysis/pit_stats.py`)。
- **RULING-3(LA-0)**：fallback 時鎖 `fit_mode=full_sample`+`oos_guarantees=False`;本票只加**可觀測性**,不改數學出口。
- **§MS(LA-0)**：min_samples=COUNT;valid⟺effective_count≥m;first_valid=computed。bin/regime 分配統一 min_samples=100。
- 下游消費者(不得破)：`GroupedICBarChart`/`RegimeRadarChart`(讀 `grouped_ic.by_regime`)、`LongShortComparisonChart`(讀聚合 recommendation/mean_return)、fallback 前端(目前**無**欄位,須新增)、**XGBoost Market_Phase fallback**(`xgboost_task_service.py:473-482` 經 `create_regime_detector`;P1-1c 改命名會變其 phase 特徵=**已裁可接受的行為變更**,B1.3 附對照 golden 記錄;LightGBM 0 hits 不受影響)。
- **known consumer debt(R1 composer-7)**：`GroupedICBarChart.tsx:51`/`RegimeRadarChart.tsx:21` 對缺失 IC `?? 0` 畫成 0 假訊號;PIT 後子桶更常缺失 → B3 一併修為 null/N/A(禁 `?? 0`),golden 不得含「NaN→0」假設。
- **禁**：weaken NaN/inf gate;per-t 降 q(依賴全樣本 nunique=洩漏);把 config percent 整數直灌原語 fraction 參數;「impl 前委員定」式 defer(R1 裁全部凍結前鎖死)。

## §G Golden / Baseline（RISK-HIT a,d → 必填）
- **feature/kline 條件**：命中(生成→計算→分位→grouped)→ 用真實 `data_cache/feature_klines/kline_cache.h5`;禁合成 fixture;B4 三方 DATA-CORRECT 簽核。
- **凍結時機/reference**：B0 動工前,legacy(改前)跑 baseline,symbol×TF = BTCUSDT/1h + ETHUSDT/12h(跨 symbol 隔離,承 LA-0 慣例),config = regime(by_regime+include_regime_analysis ON,rule)+ long_short(enabled ON,num_quantiles=5)+ 觸發 fallback 的短樣本 case。存 `tests/golden/la1/{gen_baseline.py, <sym>_<tf>_baseline.json, attribution_allowlist.json, inputs/*}`。
- **baseline 內容**：per-regime grouped IC(high/low/bull/bear) + long_short 聚合(long/short ic/mean_return/recommendation/num_quantiles_used) + regime mask 成員 hash + 分層 manifest(改前可測翻轉的 early bar 集合)。名稱集合 sha256 + 每量 value hash + NaN mask hash。
- **通過條件（可證偽，分尺度）**：
  - **control 路徑 deep-equal**：regime OFF / long_short OFF / 非觸發 fallback → 改前==改後 byte 級(值/NaN/數量)。**kmeans 不是 control**(R1 codex-1:`_align_labels` 全期命名=P1-1c 洩漏,本票修改路徑)。
  - **修改路徑 membership 漂移允許但須歸因**：PIT 後 regime high/low 率非對稱、long_short num_quantiles_used/recommendation 可變、P1-1c kmeans 命名變 → 進**機器可讀歸因表**。
  - **歸因表 schema(R1 composer-5 + R2 codex N5 反洗強化)**：`tests/golden/la1/attribution_allowlist.json` — `schema_version` + `class_enum ∈ {P1-1, P1-1b, P1-1c, P1-2, P1-3-obs}` + `rows[]` 每筆綁 **exact JSON path + index + old/new 值 discriminator**(禁只寫 class 名)+ **unlisted diff=unexpected=FAIL**;**wash mutations ≥5 必打紅**:①竄改 early mask 冒充 P1-1 ②control 路徑塞 diff ③刪紅標稱 P1-3 closed ④wrong-side swap(把 diff 歸錯 class)⑤擅擴 allowlist/unowned value(validator 拒非 predeclare 列)。
  - **B3 fallback**：頂層紅標欄位存在 + logger.warning 發出(caplog)+ **OOS-gate 斷言(consumer 級)**:`analysis_status!="ok_oos"` 時任一出口輸出 OOS 文案必 FAIL;既有 `oos_guarantees=False` 仍在。
  - **mutation 定義 canonical + 可重放(R1 composer-11 + R2 codex N6;R3 補實跑 receipt)**：
    - input dataset(FACT-RECEIPT,Claude h5py 實跑 2026-07-16):`data_cache/feature_klines/kline_cache.h5` — `BTCUSDT/1h` rows=**20352** 全欄位 bytes sha256₁₆=`1c93c37938a4917a`;`ETHUSDT/12h` rows=**1696** sha256₁₆=`00d1ee985ad3f09f`。
    - canonical mutation 常數(寫死):**M-trunc**=截尾保留前 75%(`n_keep=int(0.75*n)`);early window=保留段前 2/3(`[0, int(2/3*n_keep))`);mid-segment trunc=trunc 點落 refit 段中(`prev_end + REFIT_INTERVAL//2`)。
    - 全部內嵌 `gen_baseline.py`;單命令重放 `python tests/golden/la1/gen_baseline.py --check`(比對上列 sha),receipt 逐字可比對。

## §P Phase 與依賴

**DAG(R1 codex-6/composer-9 修)**：`B0 → {B1, B2, B3 可並行} → B4`。**所有修改 legacy 輸出(數值或可觀測欄位)的批次一律不得早於 B0**;B3 亦依賴 B0(loud 欄位屬可觀測變更,先做會污染「legacy 改前」baseline 定義)。

### Phase B0 — baseline 凍結（依賴：無）
**Task B0.1** — legacy P1 baseline
- 目標：改前凍結**五**洩漏點輸出 + 分層 manifest。檔案：`tests/golden/la1/gen_baseline.py`。caller：新建無 caller。
- 改法：可重現跑 regime(rule)/**kmeans(P1-1c legacy,含 `detect_phases_for_index` XGBoost 路徑;R2 codex C5)**/long_short/fallback,element 級逐值+regime 成員+early-flip manifest;allowlist predeclare。
- 驗證：baseline JSON 存在 + sha 抽驗 atol=1e-12;分層 manifest 兩側可測翻轉(early high/low mask、early bin)。
- 邊界：短樣本(觸發 fallback)、全 warmup 標的。
- 不可做：合成 fixture;aggregate-only baseline。

### Phase B1 — P1-1 + P1-1b + P1-1c regime PIT（依賴：B0）
**Task B1.1** — regime rule PIT 分位門檻
- 目標：`_compute_regime_groups_rule` 全域 nanpercentile → per-t expanding。檔案：`ic_engine.py:1096-1114`。caller：`_compute_regime_groups`(:1078 分派)。
- 改法：`vol` 因果不變;**必做**薄 wrapper `pit_expanding_quantile_thresholds(series, lo_q, hi_q, min_samples)`(pit_stats 內,內部呼 `pit_expanding_bounds` + **regime 契約測試鎖 warmup=(-inf,+inf) 語意**,防日後 bounds 改 NaN silent 破 regime;R1 裁死不 defer);`(lo_t,hi_t)=pit_expanding_quantile_thresholds(vol, lo_q=low_pct/100.0, hi_q=high_pct/100.0, min_samples=100)`;`high_vol=vol>=hi_t`、`low_vol=vol<=lo_t`;warmup 不進任一。**percent→fraction 鎖 + 驗 `0≤low_pct<high_pct≤100`(否則 raise)**。current-inclusive 明定(`values[:t+1]`)。bull/bear 不改。
- **空 vol 契約(R1 composer-4,Opt-A)**：`vol` 有效樣本=0(如 `len(close)<55`)→ 保留 legacy `return {}`(ic_engine:1103-1105 guard 不得移除);B1 測試 `test_regime_pit_empty_vol` assert `== {}`。
**Task B1.2** — P1-1b kmeans fallback PIT
- 目標：`_fallback_rule_based` 同一 nanpercentile → 同 PIT wrapper。檔案：`regime_detector.py:306-307`(hardcode 80/20)。caller：`detect()` 樣本不足分支 + **XGBoost `detect_phases_for_index`**(共用,見 B1.3)。
- 改法：同 B1.1 wrapper(hardcode 80/20 → lo_q=0.20/hi_q=0.80)。
- **邊界真值表(R1 codex-4,鎖 exact)**：①`len(vol_values)<2` → 全 `"unknown"`(legacy parity,不變)②warmup bar(`effective_count(vol)<100`)→ `high_vol=False`、`low_vol=False`,**bull/bear/mid 判定照舊**(即 warmup bar 得 `mid_vol_ranging`/bull/bear 家族,不得為 unknown)③非 warmup → PIT 門檻分類。B1.2 測試逐列 assert 此表。
**Task B1.3** — P1-1c kmeans 主路徑因果化（使用者 2026-07-16 裁併入完整修;演算法=R2 reconcile 裁 **Segment-causal**,偽碼鎖此不 defer）
- 目標：kmeans fit 窗 + `_align_labels` 命名雙重 look-ahead → 段起點因果決策。檔案：`regime_detector.py:224-290`(`_fit_expanding`+`_align_labels`)。caller：IC kmeans(ic_engine:1137)+ XGBoost Market_Phase fallback(xgboost_task_service:473-482)。LightGBM 0 hits。
- **演算法(Segment-causal,凍結版偽碼;R3-B1/B2/M3 修訂)**：
  ```
  REFIT_INTERVAL = REFIT_INTERVAL_CONST(=50, config 可調;禁依最終 n 推導)      # R2 codex N1
  warm_up      = min_samples_for_fit                                          # R3-M3 公式寫死
  refit_points = list(range(warm_up, n, REFIT_INTERVAL)); 末段補 n
  for 段 [prev_end, end_idx) in refit_points 切分:
      if prev_end < min_samples_for_fit:                                      # R3-B2:含首段
          labels[prev_end:end_idx] = B1.2_PIT_rule(該段)   # 委派 rule 真值表(len<2→unknown/warmup→mid·bull·bear/else PIT 門檻)
          continue
      scaler_t, model_t = kmeans.fit( valid_df[0:prev_end] )                  # fit 只用段前 prefix
      prefix_raw = model_t.predict( scaler_t.transform(valid_df[0:prev_end]) ) # R3-B1:same-model re-predict
      name_map   = align_by_vol( prefix_raw, vol[0:prev_end] )                 # 命名同 model namespace
      labels[prev_end:end_idx] = name_map( model_t.predict(scaler_t.transform(段)) )
  ```
  決策時點=`prev_end`,對段內任一 bar 零未來資訊(fit/命名/predict 全同一 model namespace;**禁**用前段模型的歷史 raw id 建 map——異質 cluster id 對不上,R3 codex+grok 雙家獨立抓)。段內 predict 出現 map 未涵蓋 raw id → `"unknown"`(map 不回頭擴充)。
- **XGBoost 對照 golden**：B1.3 附 `detect_phases_for_index` 改前/改後對照,legacy 於 **B0 凍結**(R2 codex C5)(**預期有 diff=P1-1c 歸因類**,記錄非阻擋;使用者已裁可接受)。
- **§N-級誠實排除**：`_fit_global`/`expanding=False` 全期 fit 仍 LA — 本票**禁 IC/XGBoost 路徑傳 `expanding=False`**(caller assert+文件),完整修 `_fit_global` 歸 P2(§N 登記)。
- 驗證(B1)：`pytest tests/momentum/test_la1_lookahead.py::test_regime_pit` — M-lookahead 截未來 → early high/low mask flip + **kmeans early label flip** 改前>0 改後=**0**;**mid-segment trunc mutation**(R2:trunc 落 refit 段中間 → early-in-segment name flip 改後=0,mutation 以固定 refit 段界為對照鍵,禁段界隨 n 漂移);bull/bear 零 diff(atol=1e-12);hand-calc 小序列 expanding p20/p80;truth-table 逐列;`test_regime_pit_empty_vol`。
- 邊界：vol 全 NaN(→`{}`)、len<2(→unknown)、warmup 全期(短樣本)、單 cluster、首段/prefix 不足(→委派 B1.2 rule 真值表,見偽碼)、段內新 raw id(→unknown)、refit 段跨界命名翻轉。
- 不可做：改 bull/bear;per-t 以外的全域門檻殘留;把 kmeans 當 control(它是修改路徑)。

### Phase B2 — P1-2 long_short PIT（依賴：B0）
**Task B2.1** — qcut PIT + 移除全域降 q
- 目標：`_assign_quantiles_with_fallback` 全序列 qcut → per-t。檔案：`long_short_analyzer.py:191-210`;`analyze()`:44-45;`batch_analyze` top_n 同病一併。caller：deep long_short 路徑。
- 改法：`pit_expanding_qcut_label(feature, q=固定, min_samples=100, require_full_q=True)` + **Policy-Strict(R1 三家 convergent;R2 grok 裁單軌=原語層參數,禁 analyzer 端另驗)**:原語現行 `duplicates="drop"` 後 `nunique<q` **仍出 label(非 NaN,實跑證實)** → 原語加 `require_full_q` 參數,不滿 q → **當根 NaN**;warmup/退化 NaN→`isin` 自動排除 long/short mask;**移除全域降 q**;禁 per-t 降 q。
- **PIT 定義域(R2 codex N3,BLOCKING)**：bins 在**原 feature 時序**上算(僅 feature 自身 NaN 排除),**禁**先 `concat(feature,future_returns).dropna()` 再分箱(現碼 :33-36→:44-45 順序=未來報酬 finite 與否篩選 expanding 窗歷史=洩漏);分箱後才對齊 finite future_returns 僅算 metrics。mutation:竄改 return-NaN mask → bins 必須不變(feature 不變時),變=FAIL。
- **schema 鎖(B4)**：`num_quantiles_used` 語意=固定 q==requested(禁再暗示全域實際 bin 數)。
- **雙 min_samples**：bin 分配 min_samples=100;模組進入門檻 `LongShortAnalyzer._min_samples=30` 保留;SPEC/impl 寫清兩層。
- **測試 migration 表(R3-B4;既有 5 nodeid 全列 + 1 新增,collect-only 實跑 2026-07-16=5 items)**：
  | nodeid(`tests/momentum/Analysis/test_long_short_analyzer.py`) | 遷移預期 |
  |---|---|
  | `::test_insufficient_ls_samples` | 不變:n<30 → SkippedResult(INSUFFICIENT_DATA) |
  | `::test_quantile_exceeds_samples`(q=10,n=60;其 `:23` `num_quantiles_used>=2` 斷言) | n<bin min_samples=100 → bins 全 NaN → **SkippedResult("cannot form quantiles")**(`>=2` 斷言整段取代) |
  | `::test_both_sides_negative_ic`(現 n=120) | fixture 擴 n≥200(過 bin min_samples);metrics 斷言不變 |
  | `::test_empty_side` | PIT NaN 排除下單側可空 → 該側 metrics NaN + `recommendation=="不建議"` |
  | `::test_asymmetric_quantile_def` | 固定 q 語意重寫(禁依賴全域降 q 行為) |
  | **新增** `tests/momentum/test_la1_lookahead.py::test_long_short_fixed_q`(n≥200) | 正常路徑斷言 `num_quantiles_used==5`(固定 q) |
- **recommendation 契約(R3-M1)**：enum 鎖 {雙向交易, 只做多, 只做空, 不建議}(對齊現碼 `_recommendation`:180-189);空側/IC 全 NaN → **"不建議"**;禁 agent 自創文案。
- §V 禁放寬換綠。
- 驗證：`pytest tests/momentum/test_la1_lookahead.py::test_long_short_pit` — M-lookahead early bin/long_mask 改前>0 改後=0(atol=1e-12);recommendation 翻轉歸因;**reduced-bin mutation**(2 unique 值×q=5 → 當根 `isna` + side 空,可證偽:原語裸用會 FAIL);migration 表逐 nodeid。
- 邊界：常數尾端(legacy 降 q 觸發點)、warmup 全 NaN label、單一 bin、2-unique×q=5。
- 不可做：改 `_compute_side_metrics` 描述統計(sharpe/mean/std 非 signal 級)。

### Phase B3 — P1-3 fallback loud + OOS gate（依賴：**B0**;可與 B1/B2 並行）
**Task B3.1** — 非 silent + 頂層紅標(單名鎖) + machine-checkable OOS gate + 前端
- 目標：fallback 觸發不再 silent,且 degraded 不可被當 OOS-passed 消費。檔案：`ic_filter_orchestrator.py:1033 _run_full_sample_fallback` + 呼叫點 :883/:982 + `_apply_thresholds`(:3150+) + persist/export 出口(:2988,:3333) + `api/services/ic_analysis_service.py`(:239,:421);`frontend/src/lib/types.ts`。
- **紅標欄位(R1 grok-3/composer-3,單名鎖死,刪全部「或」式)**：
  - `report.analysis_status: "ok_oos" | "degraded_full_sample"`(root,str enum)
  - `report.oos_guarantees: bool`(root 鏡像,權威優於巢狀 metadata)
  - types.ts `ICReport` 同步兩欄位。
- **D1 定案(R1 convergent + R2 RB-2 G-A2 家族,loud-not-fail-closed + machine-checkable guard)**：
  - `logger.warning`(結構化 reason/train_rows/test_rows/min_test_rows/fit_mode);
  - **G-A2(R2 裁,取代 R1 G-A 字面)**：`passed_features` **維持 `list[str]`**(不動 stage6/redundancy caller);`summary_table[]` 每列加 `pass_class`(degraded="full_sample_research_only");**OOS 宣稱 iff root `analysis_status=="ok_oos"`**。
  - **G-C persist 政策(R2 composer-5,鎖死)**：fallback 內層 `analyze()` **禁 persist**(以 context flag 跳過 `_persist_outputs`);唯一寫出點=wrapper 於 root 欄位加註**之後**。修「persist 先於紅標」時序洞(:2988,:3333 先寫、:1062-1068 patch 無 re-persist)。
  - **bypass oracle 全列(R2 codex N2/composer R2-3,≥5 出口;R3-B3 carrier 鎖死)**：①`summary_table` top-ICIR ②`filter_log.stage5_thresholds.output_features` ③filtered HDF5(`ic_reporter.py` writer 寫 `analysis_status` HDF5 attr;degraded=research-only 標記,仍可下載)④`generate_ai_json` top_features(degraded 時 OOS 文案 fail-closed)⑤API 直通出口 carrier:HDF5 FileResponse(:317)=檔內 attr;CSV(:393)=**HTTP header `X-Analysis-Status` + 檔首註解行**;transforms(:418)=**`ApplyTransformsResponse.analysis_status` 欄位 + 輸出 HDF5 attr**。task payload 必含 root 紅標。
  - **檔案 scope(R3-B3 補全)**：`ic_filter_orchestrator.py` + `ic_reporter.py`(HDF5 attr writer) + `api/models/ic_models.py`(response schema 加 `analysis_status`) + `api/routes/ic_analysis.py`(三出口) + `api/services/ic_analysis_service.py` + `frontend/src/lib/types.ts` + IC 報告 store/banner component + 對應前端測試。
  - 與 RULING-3 相容:fallback 仍出報表不 raise;只是報表被機器可讀地降級。
- **前端(R1 composer-7/R2 N4+R2-7 定 scope)**：本票=types.ts 欄位 + `GroupedICBarChart.tsx:51`/`RegimeRadarChart.tsx:21` 缺失 IC 改 null/N/A(禁 `?? 0`)+ **degraded banner**(載體=IC 報告頁 store 讀 `analysis_status!=="ok_oos"` 顯示,附前端測試);其餘 `?? 0` 圖(`LongShortComparisonChart.tsx:22`/`OOSDistributionChart.tsx:23` 等)列 §C known debt 清單,本票不修。
- 驗證：注入 fallback → `caplog` assert warning + `report["analysis_status"]=="degraded_full_sample"`(字面鍵名)+ **第三斷言(consumer 級,R2 重定義)**:export/consumer helper 在 `analysis_status!="ok_oos"` 時輸出 OOS 文案必 FAIL(≥5 oracle 逐一,非 fixture 自帶 pass_class 假綠)+ persisted JSON/HDF5 attr/task payload 均含 degraded 標;既有 `oos_guarantees=False` 仍在;非觸發路徑 deep-equal。
- 邊界：insufficient_data / rolling_warmup_insufficient 兩觸發源;export 三 format 保留紅標;cache-hit 路徑紅標不丟失。
- 不可做：改 fallback 數學出口(RULING-3);raise/fail-closed;欄位雙軌;改 `passed_features` 型別。

### Phase B4 — tests/golden/歸因/三方 DATA-CORRECT（依賴：B1,B2,B3）
**Task B4.1** — 完整測試套 + golden 重基準 + 三方簽核
- 目標：B6(LA-0)式歸因表 + membership 漂移歸因 + control deep-equal + 跨 symbol 隔離。
- 改法：golden 重基準(control byte-equal;修改路徑歸因表 0 unexpected,schema 見 §G:`attribution_allowlist.json` class_enum {P1-1,P1-1b,P1-1c,P1-2,P1-3-obs});validator 擋洗歸因(§G **≥5** 種 wash mutation 打紅);ETHUSDT/12h 隔離;XGBoost phase 對照(P1-1c 歸因)。
- 驗證：`pytest tests/momentum/test_la1_lookahead.py tests/golden/la1/` 全綠;三方 DATA-CORRECT(Claude+Codex+Composer 皆 PASS;Grok=實作者不簽);歸因表 0 unexpected、control deep-equal(atol=1e-12)、mutation 全紅。
- 不可做：sanitized fixture;廉價綠燈。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**(RISK-HIT a,d)：截未來 bar → early regime mask/bin flip 改前>0 改後=0(P1-1/1b/2);fallback caplog(P1-3)。引 `docs/TEST_DESIGN_CHARTER.md`。
- 測試層級：單元(原語映射)/整合(orchestrator 路徑)/Golden 對照(control deep-equal + 修改歸因)/邊界。獨立 `pytest tests/momentum/` 跑,不需 run_api.py。
- **防假綠**：diff 既有測試斷言;降 q 移除的測試逐 nodeid migration(禁放寬換綠);validator 擋洗歸因。
- **邊界目錄**（打勾）：☑空DF ☑全NaN列 ☑std=0/單值 ☑重複timestamp(qcut duplicates) ☑短樣本(觸發 fallback+全 warmup) ☑跨 symbol 隔離。

## §R 回退
- B0-B4 各獨立 commit 可單獨 revert。B1/B2 改動點集中(regime/long_short 分位),config flag(by_regime/long_short.enabled)即逃生口(預設 ON,驗後不關,合 feedback_no_default_off)。Golden control FAIL→不 merge。

## §N N/A 登記
- 無省略必填段。§RISK/§A/§C/§G/§P/§V/§R 全填。D1/D3/D4 已於 R1 reconcile 鎖死(不再 defer)。
- **scope exclude(R1 composer-10)**：`factor_return_analyzer.py:209` 全序列 qcut 非本票(orch :1877 不呼叫 FR;歸 1c-FR-FULL epic,非 active leak);LA-1 agent 不得擴 scope 碰 FR。
- **scope exclude(R2 grok/codex)**：`regime_detector._fit_global`/`expanding=False` 全期 fit 仍 look-ahead — 本票只**禁 IC/XGBoost 路徑傳 `expanding=False`**(B1.3 caller assert),`_fit_global` 完整因果化歸 P2 追蹤(known residual,非 silent:§C 已文件化)。
- **known consumer debt 清單(R2 composer-7)**：`LongShortComparisonChart.tsx:22-23`、`OOSDistributionChart.tsx:23` 等其餘 `?? 0` 圖本票不修,列 debt;本票只修 regime 兩圖+types.ts+banner。
