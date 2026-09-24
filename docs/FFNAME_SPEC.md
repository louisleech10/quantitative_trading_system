# FF-NAME：衍生層與 L4 raw lag 欄名經來源／指標正規化，並以命名世代防跨世代混用 — SPEC

> 來源 PLAN/診斷：`docs/FFDEFECT_DECISION.md` 第一節（缺陷 A；定性輪 `handoffs/reconcile/20260921-ffdefect-x-consult-r1/synth.md`）　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFNAME.json`（五類落點 manifest；本 SPEC 定案後依 TODO_GENERATION_PROMPT 產出）
> 版本：v3（r2 收斂 `handoffs/reconcile/20260924-ffname-x-review-r2/synth.md`：Task 1.5 之來源集合寫死並加 `layer1_only` 逐欄數值對照；§G 映射清單改為 wrapper 實際輸出之指標名（含多輸出）與三段式來源、涵蓋 `_Lag_k` 後綴；Task 4.1 改為沿用 reference 原設定；HDF5 metadata 無法解析 ⇒ 世代未知、混世代閘拒絕；§C 釐清 frame 固定檔名覆寫）；v2（r1 收斂 `handoffs/reconcile/20260924-ffname-x-review-r1/synth.md`：新增 Task 1.5 名稱前綴型選欄器改由 formatter 導出；命名世代寫入 `result.metadata` 使 frame 路徑 HDF5 可判世代；L4 raw 改名驗收涵蓋 `quote_volume`／`taker_buy_volume`；132 欄 safe-skip 改述為白名單語意之一致化並加分母收據；§G 映射算法定死）；v1（主委起草）

## §RISK 風險分級
- **大小**：大（CLAUDE.md 任務分派規則：命中 a、b、d）。
- **命中高風險原則**：(a) 欄名為特徵之索引鍵，改名後 ADF safe-skip 白名單（名稱子字串比對）對 132 欄之判定改變，影響 fracdiff 是否施作；(b) 跨模組共用路徑——`operators/derived_operators.py`、`feature_factory.py`（L4 輸入、config hash）、`feature_storage.py`（manifest）、`feature_library.py`、`consumer_gate.py`、`api/services/xgboost_batch_service.py`；(d) 下游 IC／訓練以欄名對齊跨 symbol，混用兩世代會靜默產生半 NaN 欄或靜默丟欄。
- 不命中 (c)：只對新 run 生效（config hash 加鹽，舊 run 目錄與 cache 不動），每 Phase 可單獨 revert。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認
- **已驗證事實**（11 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `sed -n 300,306p momentum/FeatureEngineering/operators/derived_operators.py` 與 `sed -n 546,552p` → 兩處皆以 `f"{fast.source}_{fast.category}_{fast.indicator}_{param_str}_{operator_name}"` 組名；`:276`／`:517` 以 `(info.source, info.category, info.indicator)` 分組（主委 實跑 2026-09-24）——metadata-hit 分支之 `source`／`indicator` 為 raw（含 `_`），fallback 分支 `_parse_feature_name`（`:836-851`）自已正規化之 L1 欄名解析（含 `-`）⇒ 同一 canonical 家族在兩分支得不同分組鍵與不同欄名。
  - FACT-RECEIPT: `sed -n 35,47p momentum/FeatureEngineering/atomic/talib_wrapper.py` → 規則註解「`'_' separates major segments, while '-' separates values inside Params.`」；`normalize_source_label`／`normalize_indicator_name` 皆為 `str(x).replace("_", "-")`；六個 atomic 模組與 `talib_wrapper.py:490` 為其唯一呼叫者（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `jq -r '.groups|to_entries[]|select(.key|test("_L2_(Cross|Ratio)$"))|.value.columns[]' data_cache/features/ETHUSDT/1h/d9935491cea49e8cada481a8bf9487d6/feature_manifest.json | wc -l` → 印出 `4214`（Cross 2107、Ratio 2107；主委 實跑 2026-09-24）。
  - FACT-RECEIPT: 同上清單之 `_Ratio$` 欄以 `grep -Eo` 抽底線形多組件指標 → 印出 AROON_aroondown 14、AROON_aroonup 14、LINEARREG_ANGLE 54、MACDFIX_Hist 9、MACDFIX_Signal 9、MINUS_DI 16、PLUS_DI 16，共 **132**；同清單以 `_(RSI|CMO|ADX|MFI|WILLR|ROC|MOM)_` 比對之 Ratio 欄 349（主委 實跑 2026-09-24）——`momentum/FeatureEngineering/utils/adf_safe_skip.py` 白名單之多組件指標只列連字號形（`PLUS-DI` 等），單組件指標（`_RSI_` 等）之 Ratio 欄**今日已**被 safe-skip；多組件者因欄名為底線形而漏網 ⇒ 改名後 132 欄與 349 欄同待遇。
  - FACT-RECEIPT: `sed -n 895,907p momentum/FeatureEngineering/feature_storage.py` → CGSA 週期標記器 `_c.split("_", 1)` 後於第一段後插入週期（主委 實跑 2026-09-24）——底線來源 `taker_ratio_…` 被標成 `taker_12h_ratio_…`；正規化後得 `taker-ratio_12h_…`。
  - FACT-RECEIPT: `sed -n 55,80p momentum/FeatureEngineering/operators/lag_processor.py` → lag 欄名＝輸入欄名 `add_suffix(f"_Lag_{lag}")`；`sed -n 1752,1756p momentum/FeatureEngineering/feature_factory.py` → L4 輸入＝`_combine_layers([data, layer1])`，`data` 為 raw kline（主委 實跑 2026-09-24）⇒ raw 欄 `taker_ratio` 之 lag 名為 `taker_ratio_Lag_<k>`，**不經** derived_operators，修 L2 不會修到它。
  - FACT-RECEIPT: `sed -n 3688,3726p momentum/FeatureEngineering/feature_factory.py` → `_compute_config_hash` 已以 `config_payload["_mtf_align_version"] = CURRENT_MTF_ALIGN_VERSION` 為程式版本鹽，無命名世代（主委 實跑 2026-09-24）；`run_paths.cgsa_work_dir`（`:34-38`）以 config hash 前 8 碼為 CGSA 工作目錄葉名；resume 閘（`feature_factory.py:1066-1102`）須 `feature_run_dir(config_hash)` 下 L7 manifest 存在且可快取。
  - FACT-RECEIPT: `grep -rn 'load_multi(' api momentum` → 呼叫者只有 `api/services/ic_analysis_service.py:1712`（cross-sectional IC，後接 `pd.concat(frames, axis=0)`）與 `api/services/cross_symbol_training_service.py:38`；`api/services/xgboost_batch_service.py:~470-498` 逐 symbol 載入後以 `intersect_columns_without_masking` 取欄名交集（主委 實跑 2026-09-24）⇒ 兩世代混用時前者得聯集半 NaN 欄、後者靜默丟欄。
  - FACT-RECEIPT: `sed -n 3564,3566p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → fracdiff `apply_to="layer1_only"` 以寫死前綴 `("close_", "open_", "high_", "low_", "volume_", "quote_volume_", "taker_", "ms_", "ent_", "tr_")` 選欄；`grep -rn layer1_only momentum api frontend/src config` 只命中該處（無預設、無前端選項，須使用者明設）（主委 實跑 2026-09-24；r1 codex P1-01）——L1 欄名早已為 `taker-ratio_…`／`quote-volume_…`，故此設定**今日即漏選 L1**，只選到底線形之 L2 Cross／Ratio。
  - FACT-RECEIPT: `sed -n 2330,2334p momentum/FeatureEngineering/feature_storage.py` → frame 路徑 `save_factory_output` 寫固定檔名 `{symbol}_{timeframe}_factory.h5` 並以 `save_metadata_json` 寫 `result.metadata`；`load_factory_output` 自 HDF5 群組 attrs `metadata_json` 讀回 metadata（`:3254-3255`）（主委 實跑 2026-09-24；r1 codex P1-02）——同 symbol／週期之新 run 覆寫舊檔，其世代只能由 metadata 判定。
  - FACT-RECEIPT: `sed -n 385,433p tests/feature_engineering/test_batch2d_dstar_align.py` → 兩條 batch2d 測試斷言 live `canonical_sha256` **不等於** 凍結值；T3（`:338-372`）比的是同一程式碼下 frame 對 CGSA 兩次 live run（主委 實跑 2026-09-24）。
- **對決策檔之更正**（以實測為準）：
  1. 決策檔 A-5「須重簽 golden `tests/_golden/batch2d/*`」**不成立**：該三檔為 legacy 時期凍結之「不得相等」oracle（`docs/FF_FAILOPEN_FROZEN_TESTS.md` 之 batch2d 列），重簽會使 `!=` 斷言轉紅；T3 為 live 對 live。⇒ 本票**不重簽**，改以 Task 4.2 實跑確認該檔測試仍綠。
  2. 決策檔 A-3 之「Lag 16 欄」落點只列 `12h_L4_lag_{1,2,3}`；實為 `taker_ratio` 之 raw lag，1h 與 12h 各 8 欄，且需另修（Task 1.3）。
  3. 決策檔「ADF 白名單」未提；改名之數值副作用見本節第 4 條 receipt 與 Task 1.4。**此為依既有白名單語意之一致化，不是 132 欄比值為 I(0) 之證明**（r1 codex P2-04：比值分母可近零）——同一問題早已存在於 349 欄單組件 Ratio，列 §N 殘留。
  4. 進入 L4 之底線 raw 欄不只 `taker_ratio`：標準 preset（`config_manager.py:923-934`）另啟用 `quote_volume`、`taker_buy_volume`（r1 codex P2-03）；Task 1.3 對 `data` 全欄套 formatter 已涵蓋，驗收逐一斷言。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-21 使用者「那命名缺陷和timeframe缺陷，應該是要修吧 你跟委員先研究是真缺陷看是要怎麼修」；2026-08-05 使用者「面向未來不溯及既往」（只對新 run，採決策檔選項 A）；2026-09-23 使用者離線前「有問題你跟委員討論共識決定」。

## §C 約束
- 解耦 7 條：`momentum/` 不 import `api/`；canonical formatter 置於 `momentum/FeatureEngineering/` 之新純函式模組，`derived_operators` **不得** import `atomic/talib_wrapper`（決策檔四-1，codex 保留意見）。
- 決策檔 A-4 禁令：**不得改 `FeatureInfo.source`／atomic metadata／kline 欄名本身**（`info.source` 為查 kline 欄之鍵；entropy 之 `close_return` 字面；`ic_analysis_service.py:2472` 將 raw source 回給前端）。正規化只發生在「組輸出欄名」與「分組鍵」處。
- 特徵**值**、列數不變；欄數不變（僅改名）。允許變動：3,596 欄之欄名、132 欄 Ratio 之 ADF／fracdiff 路徑（fracdiff 覆蓋 L2 時）、fracdiff `apply_to=layer1_only` 之選欄集合（Task 1.5：改為與命名規則一致之來源前綴）、LINEARREG_SLOPE 等 Cross／Ratio 欄於 `column_group_registry._column_sort_key` 之排序位置、`feature_schema_hash`、config hash。**manifest 與 `result.metadata` 各新增一鍵 `feature_naming_version`**（決策檔 A-5 之機械防護，唯一新增鍵；frame 路徑經 `result.metadata` 落入 meta.json 與 HDF5 `metadata_json`）。
- 命名世代之單一真相源＝新模組中之常數 `CURRENT_FEATURE_NAMING_VERSION`（本票起為 `2`；manifest 無此鍵者視為 `1`）；不得在其他檔寫死數字。
- 不處理：atomic 層硬寫之底線指標字面（`Keltner_Width`、`Donchian_Width`、`VolumeMA_Ratio`、`BullishCount_W…`）與 `ms_`／`tr_`／`ent_` 前綴族——列 §N 殘留。
- 不回填、不遷移舊 run、舊 cache、舊 golden（使用者 2026-08-05 裁定）。「不動」指以 config hash 為鍵之 run 目錄、CGSA 工作目錄與 registry 條目；frame 路徑之 `{symbol}_{timeframe}_factory.h5` 為固定檔名，任何重生（不論世代）本就覆寫之——此為既有行為、本票不改，世代由 Task 2.1 寫入之 metadata 判定（r2 codex P2-05）。

## §G Golden / Baseline
- **feature/kline 條件**：適用。真實 `data_cache/feature_klines/kline_cache.h5`；沿用 `tests/feature_engineering/fftfmeta_golden_helpers.py` 之 run 隔離與輕量真實設定，但設定須開啟 L2 Cross／Ratio、L4 lag（含 raw）、`taker_ratio`／`quote_volume`／`taker_buy_volume` 三個資料源、至少一個多組件指標（`PLUS_DI` 或 `LINEARREG_SLOPE`）；多週期 `["1h","12h"]`；禁合成 fixture。
- **凍結時機 / reference**：動工前以當下 HEAD 跑一次，存 `tests/_golden/ffname/baseline.json`：逐欄（欄名序）`dtype`、`shape`、NaN mask sha256、值 sha256，以**舊欄名**為鍵。
- **舊名→新名映射算法（封閉，r1 composer P2-01；r2 codex P1-02 補全）**：作用於 L2 Cross／Ratio、L4 lag（含其 `_Lag_<k>` 後綴，涵蓋 frame 路徑 `lag_features.apply_to="all"` 把 L2 欄送入 L4 之產物）；①raw 來源段：清單＝資料 adapter 宣告之 kline 欄名中含 `_` 者（實跑列舉，含三段式 `taker_buy_volume`）；來源 `{p1}_{p2}_…_{pn}` 經 CGSA 標記器（`split("_",1)` 於首段後插週期）之舊形為 `{p1}_{tf}_{p2}_…_{pn}`，改寫為 `{p1}-{p2}-…-{pn}_{tf}`；②指標段：清單＝TA-Lib wrapper **實際產出之指標段名**中含 `_` 者——單輸出取 `spec.name`，多輸出取 `spec.name + "_" + output_name`（`talib_wrapper.py:483-495` 之組名法，如 `BBANDS_Upper`、`MACDFIX_Hist`、`AROON_aroondown`），以程式自 wrapper 列舉，禁手寫；把整段 `_{X}_{Y}_` 改寫為 `_{X}-{Y}_`；其餘字元一律不動。**禁**以全欄 `replace("_","-")` 作映射。映射 helper 須有單元測試：`close_12h_trend_BBANDS_Upper_13_55_Cross`→`close_12h_trend_BBANDS-Upper_13_55_Cross`、`taker_12h_buy_volume_Lag_1`→`taker-buy-volume_12h_Lag_1`。
- **通過條件（可證偽）**：改後同參數重跑，以上述映射（僅供測試，放 `tests/` helper，生產碼不得持有對照表）將 baseline 鍵轉為新名後——①新舊欄名集合經映射後**全等**（無多無少）；②每欄四個 hash **全等**（fracdiff 關閉之 reference，故 ADF 白名單變化不影響值）；③改名欄數等於映射中「新名≠舊名」之數，且 >0；④新 run 所有欄名不含子字串 `taker_ratio`、`taker_buy_volume`、`quote_volume`、`number_of_trades`；⑤新 run 之 manifest `feature_naming_version == 2`。任一不等即列出欄名與 diff＝FAIL。
- **fracdiff 開啟之對照（Task 1.4）**：另以同設定開 fracdiff（覆蓋 L1、L2）跑改前、改後各一次；除 132 類欄（多組件有界指標之 Ratio）外，所有欄經映射後四 hash 全等；132 類欄改後之值等於其 L2 raw 值（未 fracdiff）；實測欄數與位元組大小差寫入收據。

## §P Phase 與依賴

### Phase 1 — 產出端正規化（依賴：無）

**Task 1.1 — canonical formatter 單一真相源**
- 目標：命名規則之正規化與命名世代集中於一個純函式模組。　檔案：新建 `momentum/FeatureEngineering/feature_naming.py`（`canonical_segment(label: str) -> str`、`CURRENT_FEATURE_NAMING_VERSION: int = 2`）；`atomic/talib_wrapper.py` 之 `normalize_source_label`／`normalize_indicator_name` 改為委派 `canonical_segment`（簽名與行為不變）。　既有 caller：六個 atomic 模組、`talib_wrapper.py:490`（經委派，無改動）。
- 改法：`canonical_segment(x) = str(x).replace("_", "-")`；測試用之舊名→新名映射放 `tests/` helper，生產碼不持有。
- **驗證**：`pytest tests/feature_engineering/test_feature_naming.py` 綠；`grep -c 'replace("_", "-")' momentum/FeatureEngineering/atomic/talib_wrapper.py` → 0（已委派）；既有 atomic 產出欄名經 §G 驗收不變（L1 本就正規化）。
- **邊界**：①輸入已含 `-`（冪等：`canonical_segment(canonical_segment(x)) == canonical_segment(x)`）；②輸入含多個 `_`（`MACDFIX_Signal` → `MACDFIX-Signal`）；③空字串回空字串。
- **存活至**：票收案後永久保留（其他產出端之單一 formatter）。
- **覆蓋風險**：無。
- 不可做：不得正規化 category（category 無底線，且為 `_parse_feature_name` 之第二段）；不得改 `FeatureInfo`。

**Task 1.2 — 衍生層分組鍵與欄名正規化**
- 目標：metadata-hit 與 fallback 兩分支得同一分組鍵與同一欄名。　檔案：`operators/derived_operators.py` 之 pair 規格收集（`:265-308`）與 pandas 路徑（`:510-555`）。　既有 caller：L2 Cross／Ratio（CGSA 與 frame 兩路徑）。
- 改法：分組鍵改為 `(canonical_segment(info.source), info.category, canonical_segment(info.indicator))`；欄名由分組鍵組成；同一 canonical 家族內若出現重複 `params[0]`（兩分支各帶一員且參數相同）⇒ `raise ValueError`（列出兩員之 `name`），取代今日 `param_to_info` dict 之靜默覆寫。
- **驗證**：`pytest tests/feature_engineering/test_ffname_derived.py` 綠——以 indicator_specs 餵底線 source／indicator（metadata-hit）與同家族之已正規化 L1 名（fallback）之單元測試：兩分支產出欄名相等、合併為一族；重複參數 ⇒ ValueError。§G 驗收 ①–③。
- **邊界**：①source 為底線、indicator 為單組件（`taker_ratio`＋`RSI`）；②source 單字、indicator 多組件（`close`＋`LINEARREG_SLOPE`）；③兩分支同家族不同參數（應合併成一族，配對結果等於單分支給全部參數時之配對）；④同家族同參數（ValueError）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得改 `info.source`／`info.indicator` 本身（仍用於查欄與 metadata）；不得改 `_PAIR_MULTIPLIERS` 或配對規則。

**Task 1.3 — L4 raw kline 欄之 lag 名正規化**
- 目標：raw kline 欄 lag 名之來源段合規（`taker-ratio_Lag_<k>`）。　檔案：`feature_factory.py` `_layer4_lag_features`（`:1730-1760`）。　既有 caller：L4（CGSA 強制 `layer1_and_raw`；frame 路徑 `all`）。
- 改法：組 L4 輸入前，對 `data` 之欄以 `canonical_segment` 改名（`data.rename(columns=…)` 產生新 frame，不改原 `data`）；兩個 `apply_to` 分支皆經同一改名。
- **驗證**：真實 kline 輕量 run（三個底線來源皆啟用）之 L4 lag 群組含 `taker-ratio_<tf>_Lag_1`、`quote-volume_<tf>_Lag_1`、`taker-buy-volume_<tf>_Lag_1`，且無任何以底線形來源開頭之 lag 欄；原 `data` 物件欄名仍含 `taker_ratio`（identity 斷言）；§G ①–④。
- **邊界**：①raw 欄名無底線（`close`，改名為恆等）；②raw 欄改名後與 L1 欄撞名（斷言：改名後 `base` 欄名唯一，否則 ValueError）；③`lag_features.exclude_patterns` 使用者設定含 `taker_ratio*`——改名後不再命中（屬行為變更，記於白話說明；不做別名）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得改 kline dataset、`data` 本身或 L3／L5／L6 之 raw 欄使用。

**Task 1.4 — ADF safe-skip 白名單之副作用驗收**
- 目標：證明改名後唯一數值差異為 132 類 Ratio 欄改走 safe-skip，且與單組件同類欄（`_RSI_` 等 Ratio）待遇一致。　檔案：不改 `utils/adf_safe_skip.py`；新增測試。
- 改法：無生產碼改動；測試以真實 run（§G fracdiff 對照）與 `is_safe_skip` 單元斷言。
- **驗證**：`is_safe_skip("close_12h_momentum_PLUS-DI_14_28_Ratio") is True`、`is_safe_skip("close_12h_momentum_PLUS_DI_14_28_Ratio") is False`（記錄改前行為）；§G fracdiff 對照之收據欄數與類別分佈；收據另記 132 類欄每欄之分母（slow 腿）最小絕對值與比值之 1%／50%／99% 分位數（r1 codex P2-04，描述性，不作門檻）。
- **邊界**：①fracdiff 關閉（無差異）；②fracdiff 只覆蓋 L1（無差異）；③fracdiff 覆蓋 L2（132 類欄差異，其餘全等）。
- **存活至**：永久（測試）。
- **覆蓋風險**：無。
- 不可做：不得為保留舊行為而把底線形加入白名單或把連字號形排除（兩者皆製造第二套命名事實）。

**Task 1.5 — 名稱前綴型選欄器改由 formatter 導出（r1 codex P1-01）**
- 目標：依欄名前綴判來源之選欄器與命名規則一致。　檔案：`preprocessing/feature_preprocessor.py` `_select_columns` 之 `layer1_only` 分支（`:3564-3566`）。　既有 caller：fracdiff（`apply_to="layer1_only"`，須使用者明設）。
- 改法：前綴集合＝`{canonical_segment(c) + "_" for c in ("close", "open", "high", "low", "volume", "quote_volume", "taker_ratio", "taker_buy_volume")}` ∪ `{"ms_", "ent_", "tr_"}`——來源集合寫死為今日前綴所涵蓋之來源（舊 `taker_` 前綴同時涵蓋 `taker_ratio` 與 `taker_buy_volume`），**不得**改取 `enabled_sources` 或 adapter 全欄（前者縮小、後者擴大選欄；r2 composer P2-01），不得再寫死底線形；實作前以 `grep -rnE '"(taker|quote_volume|taker_buy|number_of)_' momentum api` 列舉其他同型字面，命中者同法處理並列入本 Task。
- **驗證**：`pytest tests/feature_engineering/test_ffname_selectors.py` 綠——新前綴下 `taker-ratio_12h_trend_EMA_5`（L1）與 `taker-ratio_12h_statistics_LINEARREG-SLOPE_5_21_Ratio`（L2）皆被選中；`close_`／`open_`／`high_`／`low_`／`ms_` 等既有前綴之選中集合不變；**`layer1_only` 逐欄數值對照（r2 codex P1-01）**：真實 kline 輕量 run 固定 `fractional_differencing.apply_to="layer1_only"` 跑改前、改後各一次；定義差集 Δ＝（新前綴於新名所選）△（舊前綴於舊名所選，經 §G 映射轉新名），Δ 以外之全部欄經映射後四 hash 全等；Δ 內每欄記改前改後之 NaN mask sha256 與值 sha256 於收據，且 Δ 恰等於「今日因 L1 已正規化而漏選之 `taker-ratio`／`quote-volume`／`taker-buy-volume` 欄」（reference 實測 L1 新增 872 欄，r2 codex 探針）——Δ 出現其他欄即 FAIL。
- **邊界**：①來源名無底線（`close`，前綴不變）；②`apply_to` 為 list 或 `all`（不受影響）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得同時保留底線形前綴（製造第二套命名事實）；不得改 `non_stationary` 分支。

### Phase 2 — 命名世代與跨世代 fail-closed（依賴：Phase 1）

**Task 2.1 — config hash 加鹽與 manifest 標記**
- 目標：新世代 run 不得命中舊世代 cache／resume；manifest 宣告世代。　檔案：`feature_factory.py` `_compute_config_hash`；`feature_storage.py` 之 L7 v2 manifest 寫入（`version: "l7_v2"` 同層）。
- 改法：`config_payload["_feature_naming_version"] = CURRENT_FEATURE_NAMING_VERSION`；manifest 根寫 `feature_naming_version`（IC-first 二次寫入同值保留）；三個 L7 persist 入口一律把 `feature_naming_version` 寫入 `result.metadata`（frame 路徑因而落入 meta.json 與 HDF5 `metadata_json`；r1 codex P1-02）。
- **驗證**：同 config、同 kline 之 hash 改前改後不等；改後重跑兩次相等；新 run manifest 根 `feature_naming_version == 2`；以改前產生之 run 目錄在場時，改後 run 不走 `_try_load_cache` 命中、不走 CGSA resume（spy 斷言兩路徑皆未返回舊 run）。
- **邊界**：①`FFACT_CGSA_WORK_DIR` 指定固定工作目錄且內有舊世代 manifest（resume 閘因新 hash 下無 L7 manifest 而拒絕——斷言之）；②`force_regenerate`（寫入新 hash 目錄，不覆寫舊 hash 目錄）；③frame 路徑同 symbol／週期先舊後新寫固定檔名 HDF5 ⇒ 讀回之 metadata `feature_naming_version == 2`（覆寫屬 frame 路徑既有行為，本票不改）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得修改或刪除舊 run 目錄、舊 cgsa_work、registry 舊條目。

**Task 2.2 — 跨世代合併 fail-closed**
- 目標：多 run 合併點遇到兩世代即拒絕。　檔案：`feature_library.py` `_load_internal`（讀 manifest 處設 `features_df.attrs["feature_naming_version"]`，manifest 無鍵 ⇒ `1`；HDF5 fallback 以 storage 新增之 `read_factory_output_naming_version(symbol, timeframe) -> Optional[int]` 讀：`metadata_json` 可解析且有鍵 ⇒ 其值、可解析而缺鍵 ⇒ `1`、**無法解析或非物件 ⇒ `None`（未知）**；r2 codex P1-04——既有 `load_factory_output` 會把解析失敗吞成空 dict，不得據以判世代）、`load_multi`；`consumer_gate.py` 新增 `assert_single_feature_naming_version(versions: Dict[str, Optional[int]], *, error_type)`（任一為 `None` 且 symbol 數 ≥2 ⇒ 拒絕；錯誤訊息標「世代未知」）；`api/services/xgboost_batch_service.py` 逐 symbol 載入迴圈（載入後立即讀 attrs，再做欄篩選）。　既有 caller：`ic_analysis_service.py:1712`、`cross_symbol_training_service.py:38`（經 `load_multi`，不改）。
- 改法：`load_multi` 收齊各 symbol 之世代後呼叫 assert；xgboost batch 於迴圈結束、交集前呼叫同一 assert；錯誤訊息列出每 symbol 之世代與「以新版重新生成」。
- **驗證**：`pytest tests/feature_engineering/test_ffname_generation_gate.py` 綠——2 個 symbol 一舊（manifest 無鍵，世代 1）一新（世代 2）⇒ `load_multi` 拋 `error_type`（IC 路徑經 `ValueError` 包裝回報）；同世代 ⇒ 通過且回傳值不變；xgboost batch 同斷言。
- **邊界**：①單 symbol（不檢）；②全部舊世代（通過：同世代內自洽）；③HDF5 fallback 與 v2 混用（fallback 依其 metadata 判世代；舊 HDF5 缺鍵為 1）；④新世代 HDF5 之 `metadata_json` 被改成 `{bad`、配一個合法缺鍵之舊 HDF5，走 `load_multi(..., for_training=False)` ⇒ 拒絕（r2 codex P1-04 反例）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得自動改名或別名對映以「救回」混用；不得放寬既有 `assert_required_columns_present`／交集檢查。

### Phase 3 — 消費端一致性（依賴：Phase 1）

**Task 3.1 — 名稱解析消費端對新名之行為測試**
- 目標：以新名證明既有解析器正確、無回歸。　檔案：新增測試；`api/utils/feature_name_parser.py`、`column_group_registry._extract_category`／`_column_sort_key`、`rolling_aggregator`／`feature_preprocessor` 之 `_is_ratio_unsafe_column`、`lag_processor._is_layer1_or_raw` 不改碼。
- **驗證**：對 `taker-ratio_12h_statistics_LINEARREG-SLOPE_10_144_Cross` 等代表名：`infer_category == "statistics"`、`infer_layer` 為 L2；`_is_ratio_unsafe_column` 為 False；`_is_layer1_or_raw` 為 False（Cross）／True（`taker-ratio`）；`_column_sort_key` 對新名穩定且與同家族 L1 名之 aggregator 判定一致。
- **邊界**：①Cross；②Ratio；③raw lag。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得為新名修改解析器（偵察判定皆為正確或不受影響；若測試紅則回 SPEC）。

### Phase 4 — 收尾驗收（依賴：Phase 1–3）

**Task 4.1 — 全量 reference 之名稱不變式**
- 目標：以全開設定真實 run 證明產出端無底線來源段。　檔案：探針 `handoffs/run_receipts/ffname_probes/`（隔離同 FF-TFMETA `_isolate.py`）。
- **驗證**：ETHUSDT 1h＋12h，**設定逐字沿用 reference `d9935491…` 之 task record `config_used`**（不另啟用來源；r2 codex P1-03）一次 run：欄數等於 reference 之 418,719；§G ④ 成立；改名欄數與決策檔 A-3 之 3,596 比對，差異逐類列入收據。
- **邊界**：①fracdiff 關（同 reference）；②欄數不等 ⇒ FAIL 並列差集。
- **存活至**：收據永久。
- **覆蓋風險**：無。
- 不可做：不得把 run 產物寫入 `data_cache/features` 正式目錄或 registry。

**Task 4.2 — 既有 batch2d 與 L6.5 測試實跑**
- 目標：證明不重簽 golden 之判斷成立。　檔案：無改動。
- **驗證**：`pytest tests/feature_engineering/test_batch2d_dstar_align.py` 含 slow／requires_kline 標記者全綠（T3 交集 ≥3000 仍成立；若因 132 類欄 safe-skip 使交集降至 <3000 ⇒ 回 SPEC 由委員會裁定，不得改門檻）。
- **邊界**：①T3 交集數改前改後寫入收據。
- **存活至**：收據永久。
- **覆蓋風險**：無。
- 不可做：不得重簽 `tests/_golden/batch2d/*`。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用（RISK-HIT 含 a、d）。至少五個 mutant 必使具名測試紅：①Task 1.2 只改欄名不改分組鍵（兩分支不合併）；②Task 1.2 移除重複參數 ValueError；③Task 1.3 只改 CGSA 分支之 raw 改名；④Task 2.1 移除 hash 鹽；⑤Task 2.2 `load_multi` 不呼叫 assert；⑥Task 1.5 前綴改回寫死底線形；⑦§G 映射改為全欄 `replace("_","-")`（§G ①或②必紅）；⑧Task 2.2 HDF5 fallback 一律回 1；⑨映射指標清單只取 `spec.name`（`BBANDS_Upper` 映射失敗，§G ①必紅）；⑩`read_factory_output_naming_version` 解析失敗回 1（邊界④必紅）。
- 測試層級：單元（1.1、1.2、1.4、3.1）、真實 kline 輕量 run（§G、1.3、2.1）、打樁整合（2.2）。可獨立 `pytest tests/feature_engineering/…` 跑，不需 run_api.py。
- **防假綠**：既有 `tests/test_feature_factory_operators.py:62-63`、`tests/feature_engineering/test_adf_safe_skip.py`（含 `:326-338` 禁底線多組件 pattern 之斷言）不得放寬；`tests/feature_engineering/test_batch2d_dstar_align.py` 須實跑仍綠（Task 4.2）。
- **邊界目錄**：冪等正規化（1.1①）、兩分支同家族（1.2③④）、raw 撞名（1.3②）、固定工作目錄 resume（2.1①）、混世代（2.2）。

## §R 回退
- Phase 1、2、3 各自獨立 commit；只對新 run 生效（hash 加鹽），revert 後新舊世代 run 各自可讀；§G 不等 ⇒ 不 merge。不設 feature flag（行為修正非實驗）。

## §N N/A 登記
- (c) 不命中：見 §RISK。
- 殘留：atomic 層硬寫底線指標字面（`hlc_volatility_Keltner_Width_{w}_{mult}`、`Donchian_Width`、`volume_volume_VolumeMA_Ratio_{w}`、`ohlc_pattern_{Bullish,Bearish}Count_W{w}`）— `為何現在不做: blocked-by:這些字面為 L1 欄名本身，改之即改 L1 identity 與 IC 歷史比對面，需另一張只改 atomic 產出之票並另跑本票之 §G 映射流程`；觸發：本票收案後；登記處：`docs/FFDEFECT_DECISION.md`（收案時補列）。
- 殘留：`ms_`／`tr_`／`ent_` 前綴族之命名方案 — `為何現在不做: needs-research:三族為獨立前綴方案且前端已特判（featureNameParser.ts:263-301），是否納入 source/category/indicator 三段式須先定義其 canonical 段`；觸發：研究結論；登記處：同上。
- 殘留：前端 `FeatureCorrelationHeatmap.tsx` `shortLabel` 以 `parts[3]` 取指標（對所有多組件名皆截斷）— `為何現在不做: blocked-by:前端顯示層獨立缺陷，本票新名下其結果為正確（LINEARREG-SLOPE），舊名之錯誤屬舊 run`；觸發：前端 UAT；登記處：同上。
- 殘留：ADF safe-skip 白名單以名稱子字串命中 L2 Ratio（今日 349 欄單組件、改名後另 132 欄多組件）而未證比值為 I(0) — `為何現在不做: needs-research:有界指標之兩期比值（分母可近零）於真實資料之平穩性與 fracdiff 必要性，須以分母分佈與 ADF 實測決定白名單是否應排除 _Ratio`；觸發：Task 1.4 收據出爐後；登記處：`docs/FFDEFECT_DECISION.md`（收案時補列）。
- 殘留：已存之使用者 IC `feature_filter.include_pattern` 或 lag `exclude_patterns` 含底線舊名者改名後不再命中 — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`；觸發：無；登記處：白話說明。
