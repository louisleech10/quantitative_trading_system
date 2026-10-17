# FF-NAME：特徵欄名單一文法、具型身分與單一 formatter／parser，並以命名世代防跨世代混用 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 6 步；研究輪 `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`；偵察設計諮詢 r1 `handoffs/reconcile/20260924-ffname-x-consult-r1/synth.md`（21 條全處置，D-1～D-9）；事實盤點 `handoffs/run_receipts/ffname_probes/recon_facts_20261018.md`　|　日期：2026-10-18　|　對應 TODO：`docs/manifests/FFNAME.json`（本 SPEC 定案後依 TODO_GENERATION_PROMPT 產出）
> 版本：v12（修訂審查 r10 處置 `handoffs/reconcile/20260924-ffname-x-review-r10/synth.md`：靜態封閉範圍擴及 `scripts/`、`scripts/analyze_problem_features.py` 改用 parser 與 reader）；v11（修訂審查 r9 處置 `handoffs/reconcile/20260924-ffname-x-review-r9/synth.md`：IC stage0 之 h5 載入納入 canonical run 規則、靜態白名單擴及 HDF5 讀取；前端「語意解析」範圍明定並以靜態掃描封閉）；v10（修訂審查 r8 處置 `handoffs/reconcile/20260924-ffname-x-review-r8/synth.md`：改規則式封閉——凡接受特徵檔路徑者先解析為 canonical run 經 reader、移除任意路徑退路；前端描述唯一供給點為瀏覽投影兩種 detail_level，所有元件經共享 map 查詢）；v9（修訂審查 r7 處置 `handoffs/reconcile/20260924-ffname-x-review-r7/synth.md`：世代閘改為 reader 內單一 manifest 解析邊界＋特徵 parquet 只准經 reader 開啟之靜態封閉檢查；前端描述資料流端到端列明、刪前端 parser 與 worker）；v8（修訂審查 r6 處置 `handoffs/reconcile/20260924-ffname-x-review-r6/synth.md`：source 依實際輸入逐欄決定、世代閘移至 FeatureReader V2 讀取共同邊界並列全 direct 呼叫者、前端只消費 API 描述不再解析語意）；v7（全面重寫：v6 之 `layer1_only` 已由 FF-STAT 刪、frame 世代閘因 FRAMEPATH 失去對象、名稱平穩化白名單已失效；改依諮詢 r1 D-1～D-9）。v1–v6 之審查沿革見 `handoffs/reconcile/20260924-ffname-x-review-r{1..5}/synth.md`。

## §RISK 風險分級
- **大小**：大（命中 a、b、c、d）。
- (a) 欄名為特徵索引鍵：L2 配對分組、L4 lag 選欄、欄序（`column_order_sha256`）、ratio-unsafe 判定、meta 找欄、cascade 黑名單皆讀欄名；改名若漏改消費端即靜默改變數值或選欄。
- (b) 跨模組：atomic 全部引擎、`operators/*`、`feature_factory.py`、`feature_storage.py`、`core/column_group_registry.py`、`preprocessing/*`、`feature_library.py`、`api/utils/feature_name_parser.py`、`api/services/*`、前端 `featureNameParser.ts` 與元件。
- (c) 多 phase：產生端與消費端須同批切換；全部含欄名之 golden 重凍一次。
- (d) IC／訓練以欄名跨標的對齊；混世代會靜默產生半 NaN 欄或丟欄。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認
- **已驗證事實**（6 條 FACT-RECEIPT）：
  - FACT-RECEIPT: 三家各自以秒級探針解析現存真實 run `data_cache/features/BTCUSDT/12h/0729db3a2de860b6c7d01be16ca22d22/feature_manifest.json`（204,094 欄）→ 單底線文法下不可解析 codex 2,095、composer 1,587；grok 對 `fd46c9c7…`（202,431 欄）→ 2,052；失敗類型＝底線來源被週期標記切開（`taker_12h_ratio_trend_EMA_5_20_Cross`，約 1,100）、自製 atomic 底線 indicator 或底線參數（`hlc_12h_volatility_Keltner_Width_20_2.0`、`ohlc_12h_pattern_BearishCount_W13`）、raw lag 無 category（`open_12h_Lag_1`）（諮詢 r1 收斂檔）。
  - FACT-RECEIPT: L2 配對欄名兩處以 `f"{fast.source}_{fast.category}_{fast.indicator}_{param_str}_{op}"` 組名（`momentum/FeatureEngineering/operators/derived_operators.py:304-306`、`:629-632`）；分支一用 metadata 原始值、分支二解析已正規化名（:889-931）；Distance 以 `info.source in raw_data.columns` 查（:253、:563）。同 manifest：Cross 欄 1,917，`BBANDS_Upper` 形 36、`BBANDS-Upper` 形 0（grok 探針）。
  - FACT-RECEIPT: 週期標記兩套條件不同：`momentum/FeatureEngineering/feature_naming.py:29-40`（`parts[1]==tf`）與 `momentum/FeatureEngineering/feature_factory.py:4219-4227`（`any(p in tf_keys for p in parts[1:])`）。
  - FACT-RECEIPT: `momentum/FeatureEngineering/operators/lag_processor.py:123-156` 以欄名子字串判 L1／raw ⇒ `volume_12h_volume_VolumeMA_Ratio_20`、`ohlc_12h_pattern_BullishCount_W5` 實測不被加 lag（grok worktree 探針：同 manifest VolumeMA／BullishCount 之 Lag 欄 0）。
  - FACT-RECEIPT: config hash 無命名版本鹽（`feature_factory.py:4096-4138`）；`momentum/FeatureEngineering/utils/adf_safe_skip.py` 生產碼零引用、`feature_config.py:324-325` 已拒收 `preprocessing.adf_safe_skip`。
  - FACT-RECEIPT: `api/services/ic_analysis_service.py:2972` 有不經 `FeatureLibrary` 之路徑載入（grok r1）；`feature_library.load_multi`（:236-265）逐標的載入後直接返回。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-21 使用者「那命名缺陷和timeframe缺陷，應該是要修吧 你跟委員先研究是真缺陷看是要怎麼修」；2026-08-05「面向未來不溯及既往」；2026-10-02「開發階段所有資料可重新產生」；2026-10-14「就用主流軟體業界和量化金融的模式和規則」。

## §C 約束
- 解耦：`momentum/` 不 import `api/`；formatter／parser 為 `momentum/FeatureEngineering/feature_naming.py` 之純函式，`api/` 經 `momentum/factories.py` 取用。
- **值不變**：特徵值、NaN mask、列數、欄數、dtype 不變；只准欄名、group 檔名、manifest 欄名與 `feature_naming_version` 鍵、config hash 改變。L2 配對之「同一對輸入 L1 欄」之值不變；配對集合差異只准為舊兩分支分裂之同家族合併，差集機械列出（§G）。
- 不改 raw kline 欄鍵（`taker_ratio` 等為 adapter 之資料鍵）；查 raw 一律用產生端記憶體內之 `raw_lookup_key`。
- 不落盤逐欄身分 sidecar；身分由欄名經 `parse_feature_name` 完整還原（輸出量不增加；欄名長度變化入 §G 收據）。
- 不寫死加密貨幣假設：來源詞彙取自 adapter 之資料鍵經 canonical，週期鍵取自 `TimeframeAligner._timeframe_seconds_keys()`。
- 不遷移、不別名：舊 run 由世代閘拒收（使用者 2026-10-02）。

## §G Golden / Baseline
- **feature/kline 條件**：適用。真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **reference 設定**：涵蓋全部產生端——TA-Lib 六引擎（含多輸出、多參數、`close-volume` 來源）、自製 volatility／volume／pattern、entropy、microstructure、tail-risk、L2（Cross、Ratio 與全部單欄算子含 TsCorr、Distance、BinarySignal）、L3、L4（`layer1_and_raw`，含 `taker_ratio`、`quote_volume`、`taker_buy_volume` raw 欄）、L6 meta、L6.5 append 模式（`fracdiff`、`diff-k`、`rank`、`gaussian`、`zscore-w` 後綴）；多週期 `["1h","12h"]`；CGSA 序列模式（`FFACT_MULTI_TF_PARALLEL=0`）。L5 cross-sectional 另以三標的小窗 run 涵蓋。
- **凍結（改前，現行 HEAD）**：存 `tests/_golden/ffname/baseline.json`：逐欄（舊名為鍵）dtype、shape、NaN mask sha256、值 sha256，與**組名零件**——凍結腳本於 recon A1–A12 所列每個組名點包裝，記 `(舊名, kind, source, raw_lookup_key, category, indicator, params, ops, tf)`；manifest 任一欄無對應零件紀錄 ⇒ 凍結失敗（封閉涵蓋）。另記 L2 配對簽名集合 `(fast L1 舊名, slow L1 舊名, op)`、L4 lag 輸入集合、欄序、group_id 集合、平穩化決策鍵集合。
- **舊名→新名映射**：由錄得零件以新 formatter 推導；禁字串清單與全欄 `replace`。
- **通過條件**：①映射後欄集合相等（L2 依下條例外）；②每欄四雜湊全等；③改名數 > 0；④新 run 全部欄名 `parse` 成功且 `format(parse(n)) == n`；⑤L2 配對簽名集合經映射後相等，差集只准為「同 canonical 身分之舊兩分支重複」且逐筆列入收據；⑥L4 lag 輸入集合＝新 run 之 L1 群組欄＋raw 欄（`volume-volume_*_VolumeMA-Ratio_*`、`ohlc_*_pattern_BullishCount_*` 由此新增 lag，屬缺陷修正，新增欄逐筆列入收據並驗其值＝輸入位移）；⑦manifest `feature_naming_version == CURRENT`。任一不等列欄名與 diff＝FAIL。
- **現存 run 解析基線**：§A 三家探針數字為改前基線；遷移後新 run 須 100%。

## §P Phase 與依賴

### Phase 0 — 凍結與基線（依賴：無）

**Task 0.1 — 改前凍結**
- 目標：依 §G 凍結 baseline 與組名零件。　檔案：`handoffs/run_receipts/ffname_probes/freeze_baseline.py`（隔離同 `fftfmeta_golden_helpers.prepare_env`）、`tests/_golden/ffname/baseline.json`。
- **驗證**：`venv/bin/python handoffs/run_receipts/ffname_probes/freeze_baseline.py --check` rc 0——manifest 全部欄皆有零件紀錄（無紀錄欄數 == 0）；L2 配對簽名、lag 輸入集合、欄序、group_id、平穩化決策鍵均已記；重跑凍結兩次之 baseline.json sha256 相同。
- **邊界**：①同名欄出自兩個組名點 ⇒ 凍結失敗並列出；②零件中 source 為 None（microstructure、tail-risk 現況）照實記錄。
- **存活至**：Task 4.3 完成後保留（golden）。　**覆蓋風險**：無。
- 不可做：不改生產碼；不寫正式 `data_cache`。

### Phase 1 — 身分與文法（依賴：無）

**Task 1.1 — `FeatureIdentity`、formatter、parser**
- 目標：單一真相源。　檔案：`momentum/FeatureEngineering/feature_naming.py`。
- 改法：
  - 文法 `<source>_<tf>_<category>_<indicator>[_<params>][_<op>]*`；段間 `_`、段內 `-`；任一段不得含 `_`。
  - `FeatureIdentity`（kind ∈ atomic、derived、raw-lag、rolling、cross-sectional、meta、preprocess、custom；source、tf、category、indicator、params、ops）。
  - `category` 封閉集合：trend、momentum、volatility、volume、cycle、statistics、pattern、price-transform、entropy、microstructure、tail-risk、raw、cross-sectional、meta、custom。
  - params 單段：token 以 `-` 串，token 字母表 `[A-Za-z0-9.]+`；L2 配對雙成員以 `~` 分隔（`12-26-0~5-30-0`）。
  - op 每步一段：名稱與參數以 `-` 串（`Cross`、`Ratio`、`Distance`、`Momentum-L5`、`Kurt-W13`、`Lag-1`、`TsCorr-<digest8>-W21`、`fracdiff`、`diff-1`、`rank`、`gaussian`、`zscore-21`）；op 名稱集合封閉（由產生端註冊）。
  - `canonical_segment(x)`（`_`→`-`、冪等）、`format_feature_name(identity)`、`parse_feature_name(name)`（不合文法或未知 category／op ⇒ `FeatureNameParseError`，不猜）、`tag_timeframe`（唯一實作：第 2 段）、`strip_timeframe_tag`、`CURRENT_FEATURE_NAMING_VERSION: int = 2`。
  - `label_*` 不屬特徵文法：`parse_feature_name` 對其拋具名例外，另以 `is_label_column` 判定。
- **驗證**：`pytest tests/feature_engineering/test_feature_naming_grammar.py`——往返（隨機身分 1,000 例＋§G 零件推導之全部新名）、拒收（底線入段、未知 category、未知 op、非法參數字元、空段、TsCorr 缺 digest）、冪等 `canonical_segment`、tf 鍵取自 aligner（新增鍵不需改碼）。
- **邊界**：①多輸出指標（`BBANDS-Lower`）；②參數含小數（`20-2.0`）；③配對成員參數數不同；④無參數指標（params 段省略）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得在其他模組另寫組名或解析邏輯。

**Task 1.2 — 描述向量**
- 目標：API 欄名描述（Task 3.3）之契約對證來源（前端不另解析語意）。　檔案：`scripts/export_feature_name_vectors.py`、`tests/_golden/ffname/name_vectors.json`。
- **驗證**：`venv/bin/python scripts/export_feature_name_vectors.py --check` rc 0——向量含 §G reference 全部新名之解析結果與拒收案例（未知 category、非法參數字元、custom slug 碰撞、TsCorr、label）；重產之 sha256 相同。
- **邊界**：向量檔由腳本產生，手改即 Task 3.3 測試紅。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得手寫向量。

### Phase 2 — 產生端遷移（依賴：Phase 1；Task 2.6 依賴 Task 0.1）

**Task 2.1 — TA-Lib 與六引擎 metadata**
- 目標：共用身分建構。　檔案：`atomic/talib_wrapper.py`、`atomic/{trend,momentum,volatility,volume,cycle,statistics,pattern}_indicators.py`。
- 改法：抽 `build_l1_identity(spec, source)`；欄名與 metadata 鍵皆 `format_feature_name`；metadata 另存 `raw_lookup_key`（原始 kline 鍵）；`normalize_source_label`／`normalize_indicator_name` 委派 `canonical_segment`。
- **驗證**：`pytest tests/feature_engineering/test_ffname_atomic_identity.py`——metadata 之 source／indicator 為 canonical、`raw_lookup_key` 為原始鍵；§G 通過條件 ②④（Task 2.6）。
- **邊界**：①`close_volume`→`close-volume`；②多輸出；③pattern CDL。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改 `info.source` 之查欄用途（改用 `raw_lookup_key`）。

**Task 2.2 — 自製 atomic、entropy、microstructure、tail-risk**
- 目標：一處定義身分。　檔案：`atomic/volatility_indicators.py`、`atomic/volume_indicators.py`、`atomic/pattern_indicators.py`、`atomic/entropy_indicators.py`、`atomic/microstructure_indicators.py`、`atomic/tail_risk_indicators.py`、`atomic/custom_indicators.py`。
- 改法：每指標一個身分常數，compute、輸出點（`l1op` 鍵）、`get_feature_metadata` 三處共用；indicator 詞與欄名一致（`Keltner-Width`、`Donchian-Width`、`VolumeMA-Ratio`、`ForceIndex`〔補參數〕、`BullishCount`〔`W5`→params `5`〕、`shannon`、`apen`、`sampen`、`hurst`、`fractal-dim`、`perm`、`amihud-illiq`、`kyle-lambda`、`roll-spread`、`cs-spread`、`ofi-raw`、`ofi-zscore`、`large-trade-ratio`、`vpin`、`vpin-zscore`、`cvar`〔params `1pct-21`〕、`rv-up`、`rv-down`、`rsj`、`ud-vol-ratio`、`gpr`、`jb`、`mdd`）；source＝該輸出**實際使用之輸入資料鍵**依輸出點契約之順序經 canonical 後以 `-` 串接（取自 `l1op.point` 之輸入元組，例 microstructure Amihud 有 `quote_volume` 時 `close-quote-volume`、退回分支時 `close-volume`；OFI 有 `taker_ratio` 時 `taker-ratio`、否則 `taker-buy-volume-volume`；tail-risk MDD＝`close`、報酬類＝`close-return`；entropy＝實際輸入），分支改變輸入即改變欄名，同一欄名不得代表不同輸入；custom＝category `custom`、indicator＝slug（`[a-z0-9-]+`，不合或兩定義同 slug 即 run 級拒收）。
- **驗證**：`pytest tests/feature_engineering/test_ffname_atomic_identity.py`——每指標 compute、輸出點、metadata 三處欄名 == 同一身分 format；以真實 kline 之「含 `quote_volume`／`taker_ratio`」與「不含」兩份資料各生成 microstructure，同一指標之欄名不同且各自 source == 輸出點輸入元組之 canonical 串接；custom 同 slug 兩定義 ⇒ 拒收；§G ②④。
- **邊界**：①vpin 輸出點契約參數 `n_buckets` 與 metadata 一致；②無參數指標。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改指標計算。

**Task 2.3 — L2 衍生層**
- 目標：兩分支同一身分、配對保真。　檔案：`operators/derived_operators.py`。
- 改法：`_build_feature_info` 兩分支皆產 canonical `FeatureIdentity`（分支二改用 `parse_feature_name`）；配對分組鍵＝`(source, category, indicator)` canonical；同家族同參數或 canonical 鍵撞兩個不同 `raw_lookup_key` ⇒ ValueError（列兩員）；配對欄名＝基底身分＋params `fast~slow`＋op；Distance 以 `raw_lookup_key` 查 raw；BinarySignal 比對 canonical indicator；TsCorr op 嵌目標身分 `format` 之 sha256 前 8 碼。
- **驗證**：`pytest tests/feature_engineering/test_ffname_derived.py`——兩分支同家族合併、重複參數 ValueError、Distance 對 `taker-ratio` 來源產欄數 > 0（今日 0）、TsCorr 名 `parse` 成功；§G ⑤。
- **邊界**：①同家族不同參數兩分支合併後配對＝單分支給全部參數；②`close-volume` 來源配對。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改 `_PAIR_MULTIPLIERS` 與配對規則本身。

**Task 2.4 — L3、L4、L5、L6、L6.5**
- 目標：後綴改 op 段、L4 raw 入文法。　檔案：`operators/rolling_aggregator.py`、`operators/lag_processor.py`、`feature_factory.py`（L5、L4 輸入組裝）、`meta_features/*.py`、`preprocessing/feature_preprocessor.py`（append 後綴、`_DERIVED_SUFFIX_RE`）。
- 改法：L3 `<Agg>-W<w>`；L4 `Lag-<k>`，raw 欄身分 `<canonical raw>_<tf>_raw_value`；L5 `xsec_<tf>_cross-sectional_<indicator>`（`relative-price`、`beta`、`idiosyncratic-momentum`）；L6 `meta_<tf>_meta_<indicator>`（`trend-consensus`、`time-day-of-week` 等）；L6.5 `fracdiff`、`diff-<k>`、`rank`、`gaussian`、`zscore-<w>`。
- **驗證**：`pytest tests/feature_engineering/test_ffname_suffix_ops.py`——L3、L4（含 raw）、L5、L6、L6.5 每類至少一例 `format(parse(n)) == n`；§G ②④⑥。
- **邊界**：①L4 對 L2 欄之 lag（`apply_to=all`）；②L6.5 replace 模式名不變（只 append 加 op）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改運算本身。

**Task 2.5 — 週期標記與 group_id**
- 目標：單一實作。　檔案：`feature_factory.py`（刪 `_timeframe_tagged_name`，:3640、:4163 改呼叫 `tag_timeframe`；`_parse_l1_column_identity` 改 parse）、`feature_storage.py:863-876`、`preprocessing/calibration.py:190-197`、`scripts/freeze_batch2d_baseline.py:162`。
- **驗證**：`grep -rn "_timeframe_tagged_name" momentum api scripts tests` → 0；§G 之欄序、group_id、平穩化決策鍵經映射一致。
- **邊界**：①欄名後段含週期 token（只看第 2 段）；②label 不標記。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得保留第二套標記條件。

**Task 2.6 — 值不變驗收**
- 目標：§G 全部通過條件。　檔案：`tests/feature_engineering/test_ffname_value_invariance.py`、收據 `handoffs/run_receipts/ffname-value-invariance.json`（含改名差集、L2 合併差集、L4 新增 lag 欄、欄名長度變化）。
- **驗證**：`pytest tests/feature_engineering/test_ffname_value_invariance.py`（真實 kline）——§G 通過條件 ①–⑦ 全成立；收據 `handoffs/run_receipts/ffname-value-invariance.json` 之值雜湊不符數 == 0。
- **邊界**：任一通過條件不等 ⇒ 回本 Phase，不得改 golden 遷就。
- **存活至**：Task 4.3。　**覆蓋風險**：無。
- 不可做：不以欄數相等代替逐欄雜湊。

### Phase 3 — 消費端與世代閘（依賴：Phase 2）

**Task 3.1 — 後端解析點**
- 目標：一律 `parse_feature_name`（`momentum`、`api`、`scripts` 內凡由欄名推 source／category／indicator／params／ops 或 layer 者）。　檔案：`api/utils/feature_name_parser.py`、`scripts/analyze_problem_features.py`（:80-114 之自製 parser 改呼叫 `parse_feature_name`，讀特徵 parquet 改經 reader）、`core/column_group_registry.py`（`_column_sort_key`、`_extract_*`、`_CATEGORY_ORDER` 補齊封閉集合）、`feature_naming.ratio_unsafe_category`、`atomic/pattern_indicators.py:65`、`api/services/feature_export_service.py`、`api/services/feature_factory_service.py`。
- **驗證**：`pytest tests/api/test_feature_name_parser.py tests/feature_engineering/test_ffname_consumers.py`——`infer_category`／`infer_layer`／`_extract_category` 對 §G 全部新名與身分一致（不一致數 == 0；今日誤判之 `*_volume_statistics_*`、`ms_ofi_zscore_*` 為反例）。
- **邊界**：非特徵名（label、raw kline 欄）具名回傳，不落入 other。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得保留子字串判 category／layer。

**Task 3.2 — 結構化選欄**
- 目標：數值路徑不讀欄名子字串。　檔案：`operators/lag_processor.py`（`_is_layer1_or_raw` 改讀 group layer）、`meta_features/consensus_features.py`、`meta_features/interaction_features.py`（`_find_column` 改身分精確比對）、`utils/cascade_blacklist.py`（比對 parse 後 indicator）。
- **驗證**：`pytest tests/feature_engineering/test_ffname_structural_selection.py`——lag 輸入集合 == L1 群組欄＋raw 欄；`ATR-14` 不命中 `NATR-14`；cascade 黑名單對連字號名精確命中；§G ⑥。
- **邊界**：使用者 `exclude_patterns` 仍為 fnmatch（使用者輸入）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得以新名之子字串補丁維持舊啟發式。

**Task 3.3 — API 描述與前端**
- 目標：欄名語意只由 Python parser 決定，前端只消費描述。　檔案：凡回傳特徵欄名清單之 API 一併回傳版本化欄名描述（kind、source、tf、category、indicator、params、ops、display；由 Python parser 於請求時算出、不落盤）之 `api/models/*` 與對應 route；**描述之唯一供給點＝瀏覽投影**：`api/services/feature_factory_service.py` `_project_browse_rows`（:1621-1626）之 `names` 與 `table` 兩種 `detail_level` 共用同一投影並一律帶描述；前端以單一共享描述 map（store，以欄名為鍵）保存，**凡顯示或篩選特徵欄名之元件一律經同一 hook 查 map**（含表格檢視 `FeatureTable.tsx` 之命名段篩選、選取與 `onOpenCorrelation`，相關矩陣與 VIF 之標籤——`BrowseFeatureItem`、`BrowseCorrelationMatrix`、`VifRow` 等回應之欄名皆經 map 取描述），map 查無即 unsupported。**「語意解析」之範圍**＝由欄名字串拆段推導 source／category／indicator／params／ops 或 layer；僅原樣顯示欄名或以子字串搜尋欄名（例 `DataQualityDashboard.tsx:662-705`）不屬之，不需描述；前端端到端資料流改為 `FeatureDescriptor`：型別定義（`frontend/src/lib/types.ts`）、Zustand 快取（`frontend/src/store/featureFactoryStore.ts` 之 `explorerFeatureNamesByTask` 等由 `string[]` 改 `FeatureDescriptor[]`）、`FeatureExplorer.tsx` 之請求與回傳、`FeatureNameSegmentFilter.tsx`（props 改描述、選取回傳 name）、`FeatureCorrelationHeatmap.tsx`（shortLabel、`startsWith('ms_')`）、`FeatureTimeSeriesChart.tsx`、`FeatureDistributionChart.tsx`、`ExportButtons.tsx:257`；`frontend/src/lib/featureNameParser.ts` 與 `workers/featureNameParser.worker.ts` 刪除；缺描述即顯示 unsupported（fail-closed），不得退回字串解析。
- **驗證**：`pytest tests/api/test_feature_name_descriptor.py`——各回傳欄名之 API 之描述 == Task 1.2 向量（含拒收時之錯誤描述）；前端語意解析之靜態封閉檢查：`frontend/src`（測試檔除外）內 `featureNameParser`、`parseFeatureNameSegments`、對欄名之 `split('_')`／`split("_")`／`split(/_/)`、`startsWith('ms_'|'ent_'|'tr_'|'cs_'|'meta_')`、`parts[3]` 命中 == 0（`frontend/src/lib/featureDescriptor.static.test.ts` 掃描，新增即紅）；`frontend/src/lib/featureDescriptor.test.ts`（vitest）以 API `detail_level=names` 與 `table` 兩種回應樣本（含不在 Task 1.2 向量內之合法 `cross-sectional`、`tail-risk`、連字號 source 名）經共享 map 送入 Table、Filter、Heatmap（含相關矩陣與 VIF 標籤）、TimeSeries、Distribution，各元件只經 hook 讀描述、map 查無或未知版本顯示 unsupported；`pytest tests/api/test_feature_name_descriptor.py` 另驗兩種 detail_level 之描述逐欄相等；`cd frontend && npm run build` rc 0。
- **邊界**：描述版本不符或未知 kind ⇒ 前端顯示 unsupported，不 fallback other。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得手寫第二套語意啟發式。

**Task 3.4 — 命名世代閘**
- 目標：全部特徵矩陣讀取拒舊世代、多標的合併拒混世代。　檔案：`feature_naming.py`（`assert_feature_naming_version`、`assert_single_feature_naming_version`）；**共同邊界**＝`momentum/FeatureEngineering/feature_reader.py` 內單一私有 manifest 解析函式（`load_manifest_v2`、`load_columns_v2`、`load_row_index_v2`、`stream_groups_v2` 等全部 V2 讀取方法皆經它；缺鍵、舊版、無法解析即拒）；**特徵 run 之 parquet 只准經 `FeatureReader` 開啟**——`api/services/feature_factory_service.py` 之直接 `pq.read_table`（`_load_cgsa_features_df`、`_load_cgsa_selected_df` 等，:4669-4776、:4984、:5194-5248）改走 reader；涵蓋 direct 呼叫者 `momentum/Analysis/ic_engine.py:255,283,769`、`momentum/Analysis/coverage_analyzer.py:112,157,422`、`momentum/Analysis/event_samples/feature_materialization.py:80-81`、`feature_factory.py:2951`（post-IC 讀取自身新 run）與 `feature_library.py`；**凡接受特徵檔路徑之入口一律先解析為 canonical run（symbol、timeframe、config_hash 與 manifest）再經 reader，移除任意 `.parquet`／`.h5` 路徑退路**——含 `api/services/ic_analysis_service.py` 之 `_load_features_for_transforms`（:2842、:2966-2973，task 之 `req_features_path`）、`momentum/Analysis/ic_filter_orchestrator.py` 之 `_stage0_ingestion`→`_load_features_hdf5`（:3375-3389、:5818-5842）與其他以 `features_path` 載入特徵矩陣處；無法解析為 canonical run 即在產生任何 DataFrame 前拒收；多標的合併點 `feature_library.load_multi`、`api/services/cross_symbol_training_service.py`、`api/services/xgboost_batch_service.py`（交集前）再驗版本一致。
- **驗證**：`pytest tests/feature_engineering/test_ffname_generation_gate.py`——reader 三方法與上列每個 direct 呼叫者（ICEngine、CoverageAnalyzer、event materialization、feature_library、ic_analysis_service 路徑載入）各一例：缺鍵、舊版、無法解析 ⇒ 拒（訊息含重生指引）、同版通過且回傳 == 改前；三個多標的合併點各一例兩標的版本不一 ⇒ 拒；reader 每個 V2 讀取方法（含 `stream_groups_v2`）、`feature_factory_service` 之瀏覽、選欄、相關矩陣路徑、`ic_analysis_service` 之 apply-transforms 路徑各一例缺鍵／舊版／無法解析或非 canonical run 路徑 ⇒ 拒且不先回傳 DataFrame；`ic_filter_orchestrator` 之 stage0 以非 canonical run 之 `.h5` 路徑 ⇒ 拒；靜態封閉檢查：`momentum`、`api`、`scripts` 內讀取特徵矩陣之 `pq.read_table`／`pd.read_parquet`／`pq.ParquetFile`／`h5py.File`／`pd.read_hdf`／`pd.HDFStore` 呼叫只准出現於 `feature_reader.py` 與測試內之具名白名單（K 線、標籤、統計快取等非特徵矩陣之讀取逐一具名列入白名單並註明用途；白名單外新增即紅）。
- **邊界**：①單標的缺鍵亦拒；②非特徵矩陣之快取（統計 parquet）具名排除。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得自動改名或別名救回。

### Phase 4 — 鹽、死碼、重凍（依賴：Phase 3）

**Task 4.1 — config hash 鹽與 manifest**
- 檔案：`feature_factory.py` `_compute_config_hash`（`_feature_naming_version`）、`feature_storage.py`（manifest 根 `feature_naming_version`）。
- **驗證**：`pytest tests/feature_engineering/test_ffname_config_hash.py`——同設定 hash 改前 != 改後、改後重跑 ==；舊 run 在場時新 run 不命中續跑（spy 斷言 0 次）。
- **邊界**：`force_regenerate` 寫新 hash 目錄。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不刪舊 run 目錄。

**Task 4.2 — 死碼刪除**
- 檔案：刪 `utils/adf_safe_skip.py`、`tests/feature_engineering/test_adf_safe_skip.py`、`test_ffstat_all_tested.py` 對其之 mutant 引用；`feature_storage.py`、`feature_factory.py` 過時註解。
- **驗證**：`grep -rn "adf_safe_skip" momentum api` 只剩 `feature_config.py` 拒收；設定拒收測試仍綠；平穩化決策雜湊（§G）不變——與改名之值驗收分開歸因。
- **邊界**：`handoffs/` 探針引用不受版控、不處理。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改平穩化判定。

**Task 4.3 — golden 重凍與全量 reference**
- 目標：一次重凍。　檔案：事實盤點 §E 所列 `tests/_golden/{failopen,framepath,batch2d,ffstat,probewinsor,ratiounsafe,icfirstalign,icpostleak,fftfmeta,v2_ts}/*`。
- **驗證**：每檔重凍收據附「值雜湊不變、只欄名與名雜湊變」之對照；全量 reference（ETHUSDT 1h＋12h，設定沿用既有 reference）100% `parse` 往返；failopen 系列測試綠。
- **邊界**：重凍前之值雜湊若有任一不同 ⇒ 停、回 Phase 2。
- **存活至**：永久。　**覆蓋風險**：重凍等於換基準——收據逐檔逐欄比對值雜湊防止夾帶數值變更。
- 不可做：不得以重凍掩蓋數值差異。

## §V 驗證策略與邊界測試目錄
- **mutation**（各須使具名測試紅）：①某產生端繞過 formatter；②L2 只 canonical 一臂；③移除重複參數 ValueError；④Distance 改回以顯示 source 查 raw；⑤parser 接受底線入段；⑥TsCorr 改回內嵌全名；⑦移除版本鹽；⑧移除 reader 共同邊界或任一合併點之世代閘；⑨lag 改回欄名啟發式；⑩保留第二套週期標記；⑪前端恢復自行解析欄名語意（`split('_')` 或 `ms_` 特判）；⑬microstructure 退回分支沿用主分支 source（Task 2.2 雙資料測試必紅）；⑫§G 映射改為字串 replace（⑤通過條件必紅）。
- 測試層級：單元（Task 1.1、2.x 單元、3.x）、真實 kline 輕量 run（§G、Task 2.6、4.3）、vitest（Task 3.3）。
- 防假綠：既有 `test_feature_naming.py`、`test_ratiounsafe_*` 之斷言只可經本票改寫（測試刪改清單交審碼）。

## §R 回退
- Phase 1–4 各自獨立提交；版本鹽使新舊 run 互不命中；任一 Phase revert 後舊 run 仍可讀（世代閘一併 revert）。

## §N N/A 登記與殘留
- 殘留：舊產生器 `FeatureNamingConfig.make_feature_name`（`feature_config.py:593-619`，型態分析／XGBoost 批次用，不在 FF 管線）— `為何現在不做: blocked-by:已登記之舊產生器修正票（白話說明/還沒做的事.md「舊版特徵產生器」列：欄名不帶參數與看測試名字兩缺陷），命名統一併入該票`；登記處：`白話說明/還沒做的事.md`。
- 殘留：使用者已存之 IC `include_pattern`／lag `exclude_patterns` 含舊名者改名後不再命中 — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`；登記處：白話說明。
- N/A：EVENTSCAN 欄名 allowlist — 生產碼未實作（事實盤點 B11），隨第 15 步 EVENTSCAN 以新文法實作。
