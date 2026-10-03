# RATIOUNSAFE：ratio-unsafe（pattern）欄之判定對帶週期欄名失效、主路徑 L6.5 未跳過 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 3 步；`handoffs/20261003-ticketorder-prework-steps2-4.md`　|　日期：2026-10-03　|　對應 TODO：`docs/manifests/RATIOUNSAFE.json`
> 版本：v5（審查 r4 `handoffs/reconcile/20261003-ratiounsafe-x-review-r4/synth.md`：三家 proceed；採納 native 強制臂與 mutant⑨）；v4（審查 r3 `handoffs/reconcile/20261003-ratiounsafe-x-review-r3/synth.md` 三家一致採納：failopen 單週期 oracle 為 registry、不經 L6.5 落盤路徑 ⇒ 撤回重凍；Task 2.2 改為落盤路徑改後基準永久化＋failopen 不變確認；§N 登記 failopen 未觀測落盤路徑之既有覆蓋缺口）；v3（審查 r2 `handoffs/reconcile/20261003-ratiounsafe-x-review-r2/synth.md` 全數採納：append 模式 ratio-unsafe 衍生欄不再產生之明示與驗收、新增 Task 2.2 failopen 單週期基準重凍與核可、切片位置釘在各呼叫點、校準順序以 spy 與 safe-only 子封包鑑別、mutant ⑥⑦⑧）；v2（審查 r1 `handoffs/reconcile/20261003-ratiounsafe-x-review-r1/synth.md` 全數採納：Task 2.1 改以生產落盤入口 `transform_registry_groups_to_sink` 與其 native／分片／分塊分支為主、混合群組逐欄處置、分類先於校準子封包；L7 dead-drop 預設開致落盤欄數增加之實測與核可；週期標記規則改以 storage 之群組週期身分為準、定義加剝互逆之定義域；mutant 改置共同核心並分接線鑑別；pattern 值域敘述更正；`transform_selected` 全 pattern 回空 dict；路徑更正）；v1（主委起草）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。`docs/TICKET_ORDER.md` 標「小」；依 CLAUDE.md 任務分派規則重判：命中 (a)(b)(d)，且觸「膨脹升級」訊號（碰 `momentum/factories.py`、測試面擴大）。預查另證主路徑資料品質缺陷（§A FACT-RECEIPT 2、3），範圍擴及特徵工廠 L6.5 registry 兩入口全分支。
- **命中高風險原則**：(a) 數值／資料品質——主路徑 L6.5 改寫 pattern 欄之值、13／62 欄訊號被抹為 0 並因此被 L7 dead-drop 剔除；(b) 跨模組共用路徑——判定與週期標記規則散在 `feature_preprocessor`、`operators/rolling_aggregator`、`factories`、`preprocessing/calibration`、`feature_storage`；(d) ML 正確性——落盤特徵為 IC 與 ML 之輸入。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（3 條 FACT-RECEIPT＋6 條宣告）：
  - FACT-RECEIPT: `env PYTHONPATH=. venv/bin/python handoffs/run_receipts/ratiounsafe_probes/tagged_names_probe.py`（收據 `handoffs/run_receipts/20261003-ratiounsafe-tagged-names.json`；以生產命名規則造 61 個 L1 pattern 名＋122 個 L2 衍生名＋74 個非 pattern 名，各週期鍵分別以 `feature_storage` CGSA 寫檔標記規則與 `FeatureFactory._timeframe_tagged_name` 加標記）→ 印出未標記 `pattern_flagged 183/183`、`others_false_positive 0`；兩套標記規則下 `1m／5m／15m／30m／1h／4h／12h／1d` 每週期 `pattern_flagged_preprocessor 0／183`、`pattern_flagged_rolling_aggregator 0／183`；storage 規則對 `1w` 不加標記（例 `ohlc_pattern_CDL2CROWS`）（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/ratiounsafe_probes/registry_l65_pattern_probe.py`（收據 `handoffs/run_receipts/20261003-ratiounsafe-registry-l65-pattern.json`；真實 BTCUSDT 12h、近 1000 天＝1695 根、只開 pattern、`l7_dead_feature_drop` 關；同設定 `preprocessing.enabled` 關／開各經 `generate_features(persist=True)` 生成一次並落盤至暫存目錄，讀回 `raw` 成品〔CGSA 之 L6.5 經 `transform_registry_groups_to_sink` 寫入該成品〕）→ 印出 `n_pattern 62／62`、`n_identical 0`、`nonzero_total 5137 → 4286`、`n_cols_signal_erased 13`（主委 實跑 2026-10-03；峰值 footprint 0.23 GB）。⇒ 主路徑 L6.5 對 pattern 欄照常轉換；raw 路徑預設只啟用 winsorization（rolling 分位數 [0.01, 0.99]、窗 252），稀疏訊號被裁為 0。
  - FACT-RECEIPT: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/ratiounsafe_probes/deaddrop_probe.py`（收據 `handoffs/run_receipts/20261003-ratiounsafe-deaddrop.json`；BTCUSDT 12h、近 1000 天、L1 開 pattern＋trend EMA8／SMA13、L2–L6 預設、**L7 dead-drop 預設開**；前處理關／開各生成一次落盤讀 `raw`）→ 印出欄數 `363（關）／350（開）`、pattern 欄 `51／38`、只存於「關」之 pattern 欄 13 個（`ohlc_12h_pattern_CDL3INSIDE` 等，與 FACT-RECEIPT 2 之抹 0 欄同名）、非 pattern 欄集合相等、parquet 總 bytes `1,372,641／1,170,890`（主委 實跑 2026-10-03）。⇒ 現行 13 欄被抹 0 後判為常數死欄而**不落盤**；修後原值通過，此 13 欄恢復落盤（bytes 差含非 pattern 欄之編碼差，非純 pattern 增量）。
  - 宣告——判定與呼叫點（碼證）：`feature_preprocessor._is_ratio_unsafe_column`（:107，`split("_", 2)[1]`）只用於 `FeaturePreprocessor.transform` 入口（:608）；`operators/rolling_aggregator._is_ratio_unsafe_column`（:30）為逐字重複實作，用於 L3 `_select_columns`（:1055）；`momentum.factories.ratio_unsafe_category`（:260）委由前者並回 `split("_",2)[1]`，用於 IC 頁 `ic_analysis_service`（:2897）。
  - 宣告——L6.5 registry 兩入口與分支：**生產落盤入口**＝`transform_registry_groups_to_sink`（feature_preprocessor.py:805；caller `feature_storage.py:1267` ← `write_raw_from_registry_stream` ← `feature_factory.py:3869–3875`〔CGSA，`feature_factory.py:508–521` 早退〕），其分支＝`_maybe_run_native_l65_to_sink`（:1147，內呼 `native_pp._transform_single`）、`_transform_single_group_to_arrays`（:2312）、`_stream_sharded_group_to_sink`（:2431）、`_stream_single_group_chunked_to_sink`（:2497）；**inplace 入口**＝`transform_registry_groups`（:747；caller `feature_factory.py:3148`），其分支＝`_maybe_run_native_l65_inplace`、`_registry_fast_transform`、`_transform_single_group_optimized`、`_transform_single_group`。兩入口皆於分派前呼叫 `_prepare_calibration_for_groups`（:289），且皆**不呼叫**任何 ratio-unsafe 判定。registry 存在混合群組（例 `12h_L4_lag` 含 pattern 類 `Consensus` 之 lag 欄與非 pattern 欄；審查 r1 codex 實跑）。
  - 宣告——週期標記規則：①`FeatureFactory._timeframe_tagged_name`／`_apply_timeframe_tag`（feature_factory.py:4559／4569）與 `MultiTFGenerator._apply_timeframe_tag`（`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1719`）：`parts[1:]` 任一為週期鍵即不標——僅 frame 路徑使用，FRAMEPATH（第 5 步）刪除；②`calibration.tagged_column_name`（`momentum/FeatureEngineering/preprocessing/calibration.py:190`）：`parts[1]` 為任一週期鍵即不標；③`feature_storage` CGSA L7 寫檔（feature_storage.py:1059–1071，生產落盤欄名之唯一來源）：週期取自 group_id 前綴（群組週期身分）、只認 `m／h／d` 結尾（`1w` 永不標）、只在「其後已以同一週期起頭」時不標（冪等）、labels 不經此段（審查 r1 grok 實查：labels 走獨立 `labels_df`）。週期鍵＝`TimeframeAligner._timeframe_seconds_keys()`＝{1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w}。②與③對「第二段為他週期鍵」或「第三段起含週期鍵」之名不一致（例自訂 `ret_1d_x`：③於 12h／4h 群組產 `ret_12h_1d_x`／`ret_4h_1d_x`，②查封包用 `ret_1d_x`）。
  - 宣告——結構化類別之可得性：落盤 manifest 之 `groups` 無逐欄類別；`FeatureInfo` 只供 L2 使用、不落盤；`ColumnGroup` 無類別欄位；L1 group_id `{tf}_L1_{category}_{indicator}` 由 `_parse_l1_column_identity`（feature_factory.py:1276）以位置解析產生。⇒ `docs/TICKET_ORDER.md` 所寫「改讀結構化類別」於 IC 頁與 L6.5 現無資料來源；本票改為**名稱解析之單一真相源**，結構化類別列 §N。
  - 宣告——生成期順序與 IC 兩路：生成期 L6.5 所見欄名未標記（標記於 storage `_write_group`）；帶標記欄名進入判定之路徑＝IC 頁「套用後處理」與 `run_ic_first` 之 `transform_selected`（皆讀落盤成品）。**全域序列型**：涵蓋（轉換排除、落盤特徵值與欄集合修正）；**事件型**：事件型 IC 不呼叫 L6.5 轉換，但讀同一落盤特徵 ⇒ Phase 2 之落盤修正同時涵蓋；本票不改事件型程式碼。
- **待使用者確認**：待確認：無（以下語意變更於 SPEC 白話逐條閘請使用者核可，未核可不得進 TODO）——①主路徑 L6.5 對 ratio-unsafe 欄之處置＝**原值通過、不做任何 L6.5 轉換**，而非自輸出刪除；涵蓋全部 pattern 類欄：L1 原始 K 線型態訊號（`CDL*`，值域如 {−100, 0, 100}，`CDLHIKKAKE` 為 [−200, 200]）、型態計數（例 `BullishCount_W21`，實測 [11, 61]）、`Consensus`（[−1, 1]）及其 L4 lag 衍生欄。理由：自 `docs/NAN_POISONING_INVESTIGATION.md` § 7B／Q11.2 起整類列為 ratio-unsafe 之既有分類契約（L2、L3 已據此跳過），L6.5 入口防線原設計意圖即「不轉換此類欄」；此類欄為離散事件訊號或計數，滾動縮尾會把稀有事件裁掉（FACT-RECEIPT 2）。②連帶之**落盤欄數增加**：L7 dead-drop 預設開時，現行被抹 0 而判死之 pattern 欄恢復落盤（FACT-RECEIPT 3：該設定下 +13 欄）；修後實際欄集合與 bytes 於實作後以同設定實測，列入完工收據。③`preprocessing.mode=append`（非預設，生產預設 `replace`）時，ratio-unsafe 來源欄**不再產生** L6.5 衍生欄（例 `ohlc_pattern_CDLDOJI_zscore_100`、`_zscore_252`、`_fracdiff`；審查 r2 codex 以真實 CDLDOJI＋EMA8、zscore 窗 [100, 252] 實跑：改前原始 2 欄＋衍生 4 欄、改後原始 2 欄＋safe 衍生 2 欄）⇒ append 設定下落盤欄數**減少**；實際縮減欄集合與 bytes 於實作後以 append 設定實測，列入完工收據。④落盤路徑之改後基準（§G S1 兩臂）由 Task 2.2 寫出並永久作回歸基準；failopen 單週期基準以 registry 為 oracle、不經 L6.5 落盤路徑，本票前後不變、不重凍。
- **已確認結果**：
  - `2026-10-03 使用者`：逐條聽取 SPEC v5 白話後核可 §A 待確認①–④（ratio-unsafe 欄原值通過、dead-drop 恢復欄落盤、append 模式不產 ratio-unsafe 衍生欄、落盤路徑改後基準永久化），答「全部核可，開工」。
  - `2026-10-02 使用者`：全票排序 17 步定案，第 3 步 RATIOUNSAFE（`docs/TICKET_ORDER.md`）；「照表做不另問」。
  - `2026-09-26 使用者`：不得侷限加密貨幣——週期鍵一律取自 `TimeframeAligner`，不寫死。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦：API 取判定一律經 `momentum.factories`（Rule 3）；`momentum/` 不 import `api/`；新命名模組為純函式、無狀態。
- 不弱化 NaN／inf 閘；L7 dead-drop 之閘與閾值不改。L6.5 不刪 ratio-unsafe 欄；L7 dead-drop 依修後之值重判 ⇒ 落盤欄集合之變動**只限**：「現行被 L6.5 改壞而判死、原值不死」之 ratio-unsafe 欄恢復（§A 待確認②），及 append 模式下 ratio-unsafe 來源之 L6.5 衍生欄不再產生（§A 待確認③）；ratio-unsafe 原始輸入欄之原值與欄序保留；非 ratio-unsafe 欄（含其 L6.5 衍生欄）之欄名、欄數、落盤值逐位元組不變；欄名變更只限 Task 1.3 之 `1w` 標記。
- `RATIO_UNSAFE_CATEGORIES` 仍為單一常數；各模組以 re-export 引用，`is` 同一物件。
- 不得侷限加密貨幣：週期鍵集合取自 `TimeframeAligner._timeframe_seconds_keys()`；不寫死週期清單或正則。
- 嚴禁慢閘：新增測試皆為單元或輕量真實資料（pattern＋精簡 L1 單週期，秒級）。

## §G Golden / Baseline
- **feature/kline 條件**：適用——真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **凍結時機**：動工前以 HEAD 產 `tests/_golden/ratiounsafe/baseline.json`。設定 S1＝BTCUSDT 12h、近 1000 天、L1 開 pattern＋trend（EMA8、SMA13）、L2–L6 預設、預設前處理；一律經 `generate_features(persist=True)` 落盤至暫存目錄後讀 `raw` 成品（生產落盤路徑）。兩臂：S1-off＝`l7_dead_feature_drop` 關；S1-on＝預設開。各臂記名稱集合 sha256、欄數、列數、逐欄 float64 值 sha256 與 NaN mask sha256、parquet 總 bytes；另以 S1 之 `preprocessing.enabled=False` 產 ratio-unsafe 欄之原值 sha256。
- **通過條件（可證偽）**：改後 S1-off ①名稱集合 sha256、欄數、列數＝改前；②非 ratio-unsafe 欄逐欄值與 NaN mask sha256＝改前（逐位元組）；③ratio-unsafe 欄逐欄值 sha256＝`preprocessing.enabled=False` 之原值 sha256。改後 S1-on ④非 ratio-unsafe 欄之名稱集合與逐欄值 sha256＝改前；⑤新增欄集合＝「改前被剔除且原值於 dead-drop 判準下不死」之 ratio-unsafe 欄集合（逐欄具名），刪減欄集合為空；⑥欄數與 bytes 之改前／改後實測寫入收據。任一不符列出欄名＝FAIL。

## §P Phase 與依賴

### Phase 1 — 命名單一真相源（依賴：無）
**Task 1.1 — 新增純函式命名模組**
- 目標：判定、週期標記之加與剝集中一處。　檔案：新建 `momentum/FeatureEngineering/feature_naming.py`。既有 caller：新建無 caller。
- 改法：`timeframe_keys() -> frozenset[str]`（取自 `TimeframeAligner._timeframe_seconds_keys()`）；`tag_timeframe(column, timeframe) -> str`（**群組週期身分規則**＝§A 之③推廣：`timeframe` 須屬 `timeframe_keys()`，否則 `ValueError`；`label_` 開頭、少於 2 段、或 `parts[1] == timeframe` ⇒ 原樣；否則插於第一段後）；`strip_timeframe_tag(column) -> str`（非 `label_`、至少 3 段且 `parts[1]` 屬 `timeframe_keys()` ⇒ 去除 `parts[1]`；否則原樣）；`ratio_unsafe_category(column) -> Optional[str]`（**共同核心**：對 `strip_timeframe_tag` 後取 `split("_", 2)[1]`，屬 `RATIO_UNSAFE_CATEGORIES` 回之，否則 None）；`is_ratio_unsafe_column(column) -> bool`（＝`ratio_unsafe_category(column) is not None`）。`RATIO_UNSAFE_CATEGORIES` 定義移至本模組，`derived_operators` 以 re-export 保留同名。
- **加剝互逆之定義域**：未標記名＝非 `label_`、至少 2 段、`parts[1]` 不屬 `timeframe_keys()`；對其全部、對每個週期鍵 `tf`：`strip_timeframe_tag(tag_timeframe(c, tf)) == c`。`parts[1]` 屬週期鍵之名一律視為已標記（自訂名若第二段為週期鍵，屬命名歧義，留 FF-NAME，§N）。
- **驗證**：單元測試對 §A FACT-RECEIPT 1 之 257 名 × 9 週期鍵：pattern 全判 True、非 pattern 全 False；互逆對定義域內全部名稱成立；具名案例：`tag_timeframe("ret_1d_x", "12h") == "ret_12h_1d_x"`、`tag_timeframe("ret_1d_x", "4h") == "ret_4h_1d_x"`（跨週期不同名）、`tag_timeframe("close_12h_trend_EMA_8", "12h")` 冪等、`tag_timeframe("ohlc_pattern_CDLDOJI", "1w") == "ohlc_1w_pattern_CDLDOJI"`；`RATIO_UNSAFE_CATEGORIES` 於 `derived_operators`、`rolling_aggregator`、`feature_preprocessor`、`feature_naming` 為同一物件。mutant「`strip_timeframe_tag` 恆回原值」⇒ 帶標記名測試紅；mutant「`tag_timeframe` 改為任一段含週期鍵即不標」⇒ `ret_1d_x` 跨週期案例紅。
- **邊界**：①`label_` 開頭不加不剝；②單段名回 False；③`timeframe` 不屬週期鍵 ⇒ `ValueError`。
- **存活至**：永久。**覆蓋風險**：FF-NAME（第 6 步）改名時須沿用本模組。　不可做：不得以正則 `\d+[mhdw]` 代替週期鍵集合。

**Task 1.2 — 判定改用單一模組**
- 目標：刪兩份重複實作。　檔案：`feature_preprocessor.py`（刪 `_is_ratio_unsafe_column`，:608 改用 `feature_naming.is_ratio_unsafe_column`）；`operators/rolling_aggregator.py`（刪 :30 重複定義，:1055 改用之）；`momentum/factories.py::ratio_unsafe_category` 改委由 `feature_naming.ratio_unsafe_category`。同步點：`tests/api/test_icpostleak_api.py:272` 之 mutant 改破壞 `feature_naming.ratio_unsafe_category`（IC 頁實際經之共同核心）；`tests/_golden/ffstat/nan_propagation_classes.json` 兩鍵改名；`scripts/verify_nan_poisoning_fix.py` 改引用新模組。
- **驗證**：`grep -rn "def _is_ratio_unsafe_column" momentum` 為 0；IC 頁對真實帶標記名（`ohlc_12h_pattern_CDLDOJI` 等）之 `excluded_features` 含之、reason `ratio_unsafe:pattern`；共同核心 mutant「`ratio_unsafe_category` 恆回 None」⇒ IC 頁 excluded 與 reason、L3 candidates、兩 registry 入口之 §G ③ 四處皆紅；接線 mutant（逐一把各 consumer 改回舊 `split("_", 2)[1]`）⇒ 該 consumer 之帶標記名測試紅。
- **邊界**：①L3 生成期未標記名之行為不變（`MTF_12H_L3_SURVIVOR_COUNT` 不變）；②非 pattern 欄零誤判。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得保留任何一份舊實作作相容層。

**Task 1.3 — 週期標記規則單一化（生產落盤與校準）**
- 目標：生產落盤欄名與校準封包鍵用同一規則。　檔案：`feature_storage.py` CGSA L7 寫檔標記段（:1059–1071）；`preprocessing/calibration.py::tagged_column_name`（:190）。
- 改法：兩處皆呼叫 `feature_naming.tag_timeframe`；storage 段週期仍取自 group_id 前綴，以 `timeframe_keys()` 判定合法週期（`1w` 起被標記；前綴非週期鍵之群組維持不標）。frame 路徑之 `_timeframe_tagged_name`／`_apply_timeframe_tag`（feature_factory 與 MultiTF）**不改**（FRAMEPATH 刪除）。
- **驗證**：S1 與「BTCUSDT 12h＋4h、近 200 天、精簡 L1」兩設定之落盤欄名集合改前改後相同（名稱集合 sha256）；`1w` 單元：storage 段對 `1w` group 之欄名加標記；calibration 與 storage 對全部 FACT-RECEIPT 1 名稱 × 週期、及具名案例（`ret_1d_x`、冪等、`1w`）之結果相同；mutant「calibration 改回 `parts[1]` 為任一週期鍵即不標」⇒ `ret_1d_x` 案例紅。
- **邊界**：①`1w` 欄名由未標記變為標記——現無任何 `1w` 落盤 run（使用者 2026-10-03 已刪舊 run），不需遷移；②labels 不經 storage 標記段（收據列呼叫鏈）。
- **存活至**：永久。**覆蓋風險**：無（frame 標記器不在本 Task 範圍）。　不可做：不得改 group_id 文法；不得改 frame 路徑標記器。

### Phase 2 — 主路徑 L6.5 跳過 ratio-unsafe 欄（依賴：Phase 1）
**Task 2.1 — registry 兩入口全分支跳過**
- 目標：L6.5 不改寫 ratio-unsafe 欄。　檔案：`feature_preprocessor.py`——生產入口 `transform_registry_groups_to_sink`（:805）與其分支 `_maybe_run_native_l65_to_sink`（:1147）、`_transform_single_group_to_arrays`（:2312）、`_stream_sharded_group_to_sink`（:2431）、`_stream_single_group_chunked_to_sink`（:2497）；inplace 入口 `transform_registry_groups`（:747）與其分支 `_maybe_run_native_l65_inplace`、`_registry_fast_transform`、`_transform_single_group_optimized`、`_transform_single_group`；`_prepare_calibration_for_groups`（:289）。第一步以收據盤點兩入口之分派與實際落點（以 `feature_storage.py:1267` 呼叫鏈為權威）。
- 改法：兩入口於 `_prepare_calibration_for_groups` **之前**逐群組逐欄分類；公開域欄集合（校準子封包、指紋）不含 ratio-unsafe 欄（`restrict_packet` 允許校準域多出欄）。群組處置：全為 ratio-unsafe ⇒ to_sink 入口以**原值陣列**送 sink（欄名、形狀、shard 命名、來源清理、compact 對齊展開與 `preprocessor=None` 之既有原值串流一致），inplace 入口不覆寫 registry；混合群組 ⇒ 只對非 ratio-unsafe 子矩陣轉換、ratio-unsafe 欄原值保留、欄序不變（native-tf 分支以原生子矩陣經既有 `apply_idx_map_to_array` 展開）；全為非 ratio-unsafe ⇒ 行為不變。**切片位置**：分類表於兩入口建立；`_registry_fast_transform` 維持無欄名介面、其內不加判定；凡呼叫 `_registry_fast_transform`、`native_pp._transform_single`、`_transform_single` 或寫入 sink 之點（含 sharded 每個 shard 依 `shard_cols`、chunked 每個 chunk、inplace 依 `group.columns`），先依該點之欄名清單切出非 ratio-unsafe 子矩陣再呼叫、ratio-unsafe 欄原值拼回。**append 模式**：輸出＝原始輸入欄（ratio-unsafe 原值、非 ratio-unsafe 依既有語意）＋非 ratio-unsafe 來源之衍生欄；ratio-unsafe 來源不產生任何衍生欄（§A 待確認③）。`transform`（DataFrame 路徑）維持既有「入口剔除」語意不變。
- **驗證**：`pytest tests/feature_engineering/test_ratiounsafe_registry.py` 綠：§G ①–⑥（經 `generate_features(persist=True)` 讀 `raw`）；逐分支單元（沿用 `tests/_golden/icpostleak/contract.json` 之 `registry_sink`／`registry_sink_sharded` 等強制分支設定，與 `tests/feature_engineering/test_icpostleak.py` 同 harness）：ratio-unsafe 原始欄 `np.array_equal(輸出, 輸入, equal_nan=True)`、非 ratio-unsafe 欄（含其衍生欄）之值與名稱與改前逐位元組相同、sink 收到之列數與原始欄名／shard 名與改前相同；append 臂（`registry_chunked_append` 等既有 contract 鍵）：ratio-unsafe 來源之衍生欄不存在、非 ratio-unsafe 衍生欄與改前相同；平穩化開＋pattern 群組 ⇒ 不拋 `CalibrationError`、pattern 輸出＝輸入，且以 spy 觀測 `_prepare_calibration` 收到之 `columns_by_timeframe` 不含任何 ratio-unsafe 欄；另以真實封包經生產 `restrict_packet` 取**只含非 ratio-unsafe 欄**之子封包作來源，生成須成功。mutant：①「只改 inplace 入口、to_sink 不改」⇒ §G ③紅；②「跳過判定恆 False」⇒ §G ③紅；③「跳過判定恆 True」⇒ §G ②紅；④「混合群組整群跳過」⇒ 混合群組內非 ratio-unsafe 欄之 §G ②紅；⑤「分類移至 `_prepare_calibration_for_groups` 之後」⇒ spy 斷言紅、safe-only 子封包來源拋 `CalibrationError`；⑥「全 ratio-unsafe 之 sharded 群組仍整 shard 進 `_registry_fast_transform`」⇒ sharded 強制分支之 ratio-unsafe 原值斷言紅；⑦「混合群組之 shard／chunk 未依欄名切片」⇒ 該群 ratio-unsafe 欄原值斷言紅；⑧「append 仍對 ratio-unsafe 來源產衍生欄」⇒ append 臂衍生欄不存在斷言紅；⑨「native 呼叫點未依欄名切片、整組進 `native_pp._transform_single`」⇒ native 強制臂之 ratio-unsafe 原值斷言紅。**native 強制臂**：S1 為單週期、`same_tf` 永不進 native（`_native_tf_helpers.py:269–270`），且 ICPOSTLEAK contract 無 native 強制鍵 ⇒ 另以真實 kline 之 compact-aligned 混合群組（`source_tf ≠ primary_tf`，含 pattern 欄與非 pattern 欄；設定沿用 `tests/feature_engineering/preprocessing/test_l65_native_tf.py` 之對齊方式）經 `transform_registry_groups_to_sink` 跑，斷言 `_maybe_run_native_l65_to_sink` 回非 `None`（確實走 native）、ratio-unsafe 欄展開後 `np.array_equal(輸出, 原值展開, equal_nan=True)`、非 ratio-unsafe 欄與改前逐位元組相同；秒級單元。
- **邊界**：①全群組皆 ratio-unsafe ⇒ L6.5 無轉換、run 正常完成且 sink 收齊；②compact-aligned 群組原值展開後列數＝主週期列數；③chunked／sharded 之 shard 數與命名不變。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得自落盤成品刪除 ratio-unsafe 欄；不得以關閉 winsorization 全域代替；不得改 L7 dead-drop 閘。

**Task 2.2 — 落盤路徑基準永久化與 failopen 不變確認（依賴：Task 2.1）**
- 目標：L6.5 落盤路徑（`generate_features(persist=True)` → `transform_registry_groups_to_sink` → L7 dead-drop → `raw` 成品）有永久回歸基準；既有 failopen 基準於本票前後不變。　檔案：`tests/_golden/ratiounsafe/baseline.json`（§G 之 S1-off／S1-on 兩臂，改後版本）；`tests/feature_engineering/test_ratiounsafe_registry.py`；`tests/_golden/failopen/baseline.json` 不改。
- 改法：§G 改前基準僅供改前改後對照；Task 2.1 驗收通過後，以改後實跑寫出 S1 兩臂之改後基準（逐欄 float64 值 sha256、NaN mask sha256、名稱集合 sha256、欄數、列數、parquet 總 bytes），作為落盤路徑之永久回歸基準，由 `test_ratiounsafe_registry.py` 每次比對。寫出改後基準為使用者核可事項（與 §A 待確認①②③ 同一白話閘）。failopen 單週期 Gate-A 以 registry 為 oracle（`scripts/freeze_failopen_baseline.py:497` 之 `persist=False`、`:523–524` 之 `final_L7` 為 `storage=registry_groups`），不經 L6.5 落盤路徑（審查 r3 codex 以「`transform_registry_groups_to_sink` 改為必拋」之 mutant 實跑：入口呼叫 0 次、`final_L7` 雜湊不變），故本票不重凍。
- **驗證**：`pytest tests/feature_engineering/test_ratiounsafe_registry.py` 綠且比對改後基準；`pytest tests/feature_engineering/test_failopen_contract.py tests/feature_engineering/test_failopen_layers.py` 綠；`test_failopen_correctness.py::test_v3_healthy_full_run_matches_frozen_baseline`、`::test_v3_ethusdt_1h_matches_frozen_baseline` 逐節點獨立行程綠且 `git diff --quiet tests/_golden/failopen/baseline.json`（rc=0）；mutant「改後基準之任一 ratio-unsafe 欄 sha256 改一位」⇒ `test_ratiounsafe_registry.py` 紅。
- **邊界**：①Phase 1、Phase 2 合併後 failopen 全部雜湊不變（任一變動＝越界，須歸因）；②改後基準不得於 Task 2.1 驗收前寫出。
- **存活至**：永久。**覆蓋風險**：FFSTORE（第 14 步）重定落盤格式時須同步重定本基準。　不可做：不得改 `scripts/freeze_failopen_baseline.py` 之 oracle 路徑；不得重凍 failopen 基準。

### Phase 3 — 讀落盤成品之消費端（依賴：Phase 1）
**Task 3.1 — IC 頁與 IC-first 之排除對帶標記欄名生效**
- 目標：ICPOSTLEAK 設計之「ratio-unsafe 欄明示排除」對真實落盤欄名生效。　檔案：無新改動（由 Task 1.2 帶入）；新增測試。
- **驗證**：以 S1 落盤成品（暫存目錄）分別跑：IC 頁 `_apply_transforms_sync`——帶標記 pattern 欄全數列於 `excluded_features`、reason `ratio_unsafe:pattern`、非 pattern 欄輸出與改前逐位元組相同；`transform_selected`——帶標記 pattern 欄不在任何輸出群組、非 pattern 欄輸出與改前逐位元組相同。
- **邊界**：①全選 pattern 欄：IC 頁 ⇒ 既有 `ValueError`（全為 ratio-unsafe）；`transform_selected` ⇒ 既有契約回空 dict（feature_preprocessor.py:678–690）；兩契約各自保持、逐 caller 斷言；②前端 `excluded_features` 顯示不變。
- **存活至**：永久。**覆蓋風險**：ICFIRSTALIGN 乙改 `run_ic_first` 時沿用。　不可做：不改 API schema；不改 `transform_selected` 之錯誤語意。

## §V 驗證策略與邊界測試目錄
- mutation：Task 1.1／1.2／1.3／2.1 各具名 mutant（見各 Task）；共同核心鑑別＝改壞 `ratio_unsafe_category` 使 IC 頁、L3、兩 registry 入口四處同時紅；接線鑑別＝逐 consumer 改回舊判定使該處紅。
- 測試層級：單元（命名模組）、真實資料輕量整合（S1 單週期，秒級）、分支強制（ICPOSTLEAK contract harness）、Golden 對照（§G）。可獨立 `pytest` 執行。
- 防假綠：既有測試斷言 diff 逐處說明；Phase 1 後 L3 存活欄數（Task 1.2 邊界①）與 failopen 全部雜湊不變；Phase 2 後 failopen 全部雜湊仍不變（其 oracle 不經 L6.5 落盤路徑）；落盤路徑由 §G 與 Task 2.2 之永久基準守。
- 邊界目錄：空 DF、全 NaN 欄、單段欄名、`label_`、`1w`、自訂名含週期鍵、混合群組、compact-aligned 群組、sharded／chunked、append 模式、平穩化開。

## §R 回退
- 每 Phase 獨立 commit；Phase 2（含 Task 2.2 寫出之改後基準）為落盤值與欄集合之語意變更，回退＝revert 該 commit（基準一併回復）。

## §N N/A 登記
- 結構化類別落盤（逐欄 category 寫入 manifest）— `為何現在不做: blocked-by:FFSTORE（第 14 步）快照契約定義 manifest 逐欄 metadata schema`；觸發：FFSTORE SPEC 定案時改由結構化類別判定並刪名稱解析；登記處：`docs/ROADMAP.md` RM-FFSTORE。
- 自訂指標名第二段恰為週期鍵（例 `ret_1d_x` 未標記時與已標記名不可區分）之命名歧義；L2 Cross／Ratio 以 FeatureInfo 原始 source 重組欄名（含底線來源、`None_` 前綴）與 L1 正規化不一致 — `為何現在不做: blocked-by:FF-NAME（第 6 步）統一命名文法`；觸發：FF-NAME 開工；登記處：`docs/ROADMAP.md` RM-FFNAME。
- failopen 單週期 Gate-A 以 registry 為 oracle（`persist=False`），不觀測 L6.5 落盤路徑與 L7 dead-drop（本票前即存在之覆蓋缺口；本票之落盤路徑由 Task 2.2 永久基準守，僅限 S1 設定）— `為何現在不做: blocked-by:FFSTORE（第 14 步）重定落盤格式與快照契約，基準形狀將隨之重定`；觸發：FFSTORE SPEC 定案時改以落盤成品為 failopen oracle；登記處：`docs/ROADMAP.md` RM-FFSTORE。
- 既有已落盤之 pattern 欄值受 L6.5 改寫 — `為何現在不做: user-ruling:2026-10-03 使用者已核可刪除全部舊算法特徵 run`；觸發：無（資料已不存在）。
