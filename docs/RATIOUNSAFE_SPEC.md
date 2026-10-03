# RATIOUNSAFE：ratio-unsafe（pattern）欄之判定對帶週期欄名失效、主路徑 L6.5 未跳過 — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 3 步；`handoffs/20261003-ticketorder-prework-steps2-4.md`　|　日期：2026-10-03　|　對應 TODO：`docs/manifests/RATIOUNSAFE.json`
> 版本：v1（主委起草）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。`docs/TICKET_ORDER.md` 標「小」；依 CLAUDE.md 任務分派規則重判：命中 (a)(b)(d)，且觸「膨脹升級」訊號（碰 `momentum/factories.py`、測試面擴大）。預查另證主路徑資料品質缺陷（§A FACT-RECEIPT 2），範圍擴及特徵工廠 L6.5 registry 全分支。
- **命中高風險原則**：(a) 數值／資料品質——主路徑 L6.5 改寫 pattern 欄之值、13／62 欄訊號被抹為 0；(b) 跨模組共用路徑——判定與週期標記規則散在 `feature_preprocessor`、`rolling_aggregator`、`factories`、`feature_factory`、`multi_tf_generator`、`calibration`、`feature_storage` 七處；(d) ML 正確性——落盤特徵為 IC 與 ML 之輸入。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（2 條 FACT-RECEIPT＋5 條宣告）：
  - FACT-RECEIPT: `env PYTHONPATH=. venv/bin/python handoffs/run_receipts/ratiounsafe_probes/tagged_names_probe.py`（收據 `handoffs/run_receipts/20261003-ratiounsafe-tagged-names.json`；以生產命名規則造 61 個 L1 pattern 名＋122 個 L2 衍生名＋74 個非 pattern 名，各週期鍵分別以 `feature_storage` CGSA 寫檔標記規則與 `FeatureFactory._timeframe_tagged_name` 加標記）→ 印出未標記 `pattern_flagged 183/183`、`others_false_positive 0`；兩套標記規則下 `1m／5m／15m／30m／1h／4h／12h／1d` 每週期 `pattern_flagged_preprocessor 0／183`、`pattern_flagged_rolling_aggregator 0／183`；storage 規則對 `1w` 不加標記（例 `ohlc_pattern_CDL2CROWS`）（主委 實跑 2026-10-03）。
  - FACT-RECEIPT: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/ratiounsafe_probes/registry_l65_pattern_probe.py`（收據 `handoffs/run_receipts/20261003-ratiounsafe-registry-l65-pattern.json`；真實 BTCUSDT 12h、近 1000 天＝1695 根、只開 pattern、`l7_dead_feature_drop` 關；同設定 `preprocessing.enabled` 關／開各生成一次並落盤至暫存目錄，讀回 `raw` 成品〔CGSA 之 L6.5 經 raw-sink 寫入該成品〕）→ 印出 `n_pattern 62／62`、`n_identical 0`、`nonzero_total 5137 → 4286`、`n_cols_signal_erased 13`（主委 實跑 2026-10-03；峰值 footprint 0.23 GB）。⇒ 主路徑 L6.5 對 pattern 欄照常轉換（預設 `winsorization` 開、rolling 分位數 [0.01, 0.99]、窗 252），稀疏之 ±100 訊號被裁為 0。
  - 宣告——判定與呼叫點（碼證）：`feature_preprocessor._is_ratio_unsafe_column`（:107，`split("_", 2)[1]`）只用於 `FeaturePreprocessor.transform` 入口（:608）；`operators/rolling_aggregator._is_ratio_unsafe_column`（:30）為逐字重複實作，用於 L3 `_select_columns`（:1055）；`momentum.factories.ratio_unsafe_category`（:260）委由前者並回 `split("_",2)[1]`，用於 IC 頁 `ic_analysis_service`（:2897）。registry 路徑 `transform_registry_groups`（:747）→ `_transform_single_group`（:2244）等分支**不呼叫**任何 ratio-unsafe 判定。
  - 宣告——週期標記規則有三種：①`FeatureFactory._timeframe_tagged_name`／`_apply_timeframe_tag`（feature_factory.py:4559／4569）與 `MultiTFGenerator._apply_timeframe_tag`（multi_tf_generator.py:1719）：`label_` 不標、少於 2 段不標、`parts[1:]` 任一為週期鍵不標，否則插於第一段後；②`calibration.tagged_column_name`（calibration.py:190）：只看 `parts[1]`；③`feature_storage` CGSA L7 寫檔（feature_storage.py:1059–1071）：週期取自 group_id 前綴且只認 `m／h／d` 結尾（`1w` 永不標）、只在「其後已以同一週期起頭」時不標、不排除 `label_`。週期鍵＝`TimeframeAligner._timeframe_seconds_keys()`＝{1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w}。
  - 宣告——結構化類別之可得性：落盤 manifest 之 `groups` 無逐欄類別；`FeatureInfo` 只供 L2 使用、不落盤；`ColumnGroup` 無類別欄位；L1 group_id `{tf}_L1_{category}_{indicator}` 由 `_parse_l1_column_identity`（feature_factory.py:1276）以位置解析產生。⇒ `docs/TICKET_ORDER.md` 所寫「改讀結構化類別」於 IC 頁與 L6.5 現無資料來源；本票改為**名稱解析之單一真相源**，結構化類別列 §N。
  - 宣告——生成期順序：單週期與 CGSA 多週期之 L6.5 於落盤標記前執行（feature_factory.py:3148／3164 先於 storage 寫檔）⇒ 生成期 L6.5 所見欄名未標記；帶標記欄名進入判定之路徑＝IC 頁「套用後處理」與 `run_ic_first` 之 `transform_selected`（皆讀落盤成品）。
  - 宣告——IC 兩路涵蓋：**全域序列型**：涵蓋（IC 頁與 `run_ic_first` 之轉換排除、落盤特徵值修正）；**事件型**：事件型 IC 不呼叫 L6.5 轉換，但讀同一落盤特徵 ⇒ Phase 2 之落盤值修正同時涵蓋；本票不改事件型程式碼。
- **待使用者確認**：待確認：無（以下語意變更於 SPEC 白話逐條閘請使用者核可，未核可不得進 TODO）——主路徑 L6.5 對 ratio-unsafe 欄之處置＝**原值通過、不做任何 L6.5 轉換**（欄數不變、值回到未轉換之原值），而非自輸出刪除。理由：①L6.5 入口防線之原設計意圖即「不轉換此類欄」（`docs/NAN_POISONING_INVESTIGATION.md` § 7B／Q11.2）；②pattern 值域本即有界 {−100, 0, 100}，縮尾、平穩化無對象；③刪欄會改變落盤欄數（CLAUDE.md「不得擅改輸出大小」）。此為落盤值之語意變更，於 SPEC 白話閘逐條請使用者核可。
- **已確認結果**：
  - `2026-10-02 使用者`：全票排序 17 步定案，第 3 步 RATIOUNSAFE（`docs/TICKET_ORDER.md`）；「照表做不另問」。
  - `2026-09-26 使用者`：不得侷限加密貨幣——週期鍵一律取自 `TimeframeAligner`，不寫死。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦：API 取判定一律經 `momentum.factories`（Rule 3）；`momentum/` 不 import `api/`；新命名模組為純函式、無狀態。
- 不弱化 NaN／inf 閘；不改落盤欄數與欄名（Task 1.3 之 `1w` 標記為唯一欄名變更，見該 Task）；非 ratio-unsafe 欄之落盤值逐位元組不變。
- `RATIO_UNSAFE_CATEGORIES` 仍為單一常數；各模組以 re-export 引用，`is` 同一物件。
- 不得侷限加密貨幣：週期鍵集合取自 `TimeframeAligner._timeframe_seconds_keys()`；不寫死週期清單或正則。
- 嚴禁慢閘：新增測試皆為單元或輕量真實資料（pattern-only 單週期，秒級）。

## §G Golden / Baseline
- **feature/kline 條件**：適用——真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **凍結時機**：動工前以 HEAD 產 `tests/_golden/ratiounsafe/baseline.json`：設定 S1＝BTCUSDT 12h、近 1000 天、L1 開 pattern＋trend（EMA8、SMA13）、預設前處理、`l7_dead_feature_drop` 關；記逐欄名稱集合 sha256、欄數、列數、逐欄 float64 值 sha256 與 NaN mask sha256。另以同設定 `preprocessing.enabled=False` 產 pattern 欄之原值 sha256。
- **通過條件（可證偽）**：改後 S1 ①名稱集合 sha256、欄數、列數＝改前；②非 pattern 欄逐欄值與 NaN mask sha256＝改前（逐位元組）；③pattern 欄逐欄值 sha256＝`preprocessing.enabled=False` 之原值 sha256。任一不符列出欄名＝FAIL。

## §P Phase 與依賴

### Phase 1 — 命名單一真相源（依賴：無）
**Task 1.1 — 新增純函式命名模組**
- 目標：判定、週期標記之加與剝集中一處。　檔案：新建 `momentum/FeatureEngineering/feature_naming.py`。既有 caller：新建無 caller。
- 改法：`timeframe_keys() -> frozenset[str]`（取自 `TimeframeAligner._timeframe_seconds_keys()`）；`tag_timeframe(column, timeframe) -> str`（規則＝§A 之①）；`strip_timeframe_tag(column) -> str`（非 `label_`、至少 3 段且 `parts[1]` 為週期鍵 ⇒ 去除 `parts[1]`；否則原樣）；`ratio_unsafe_category(column) -> Optional[str]`（對 `strip_timeframe_tag` 後取 `split("_", 2)[1]`，屬 `RATIO_UNSAFE_CATEGORIES` 回之，否則 None）；`is_ratio_unsafe_column(column) -> bool`。`RATIO_UNSAFE_CATEGORIES` 定義移至本模組，`derived_operators` 以 re-export 保留同名。
- **驗證**：單元測試對 §A FACT-RECEIPT 1 之 257 名 × 9 週期鍵 × 兩套標記規則：pattern 全判 True、非 pattern 全 False；`strip_timeframe_tag(tag_timeframe(c, tf)) == c` 對全部非 `label_` 名成立；`RATIO_UNSAFE_CATEGORIES` 於 `derived_operators`、`rolling_aggregator`、`feature_preprocessor`、`feature_naming` 為同一物件。mutant「`strip_timeframe_tag` 恆回原值」⇒ 帶標記名測試紅。
- **邊界**：①自訂指標名第二段恰為週期鍵（例 `ret_1d_x`）⇒ 被剝除，不影響判定（剝後第二段非 pattern）；②`label_` 開頭不剝；③單段名回 False。
- **存活至**：永久。**覆蓋風險**：FF-NAME（第 6 步）改名時須沿用本模組。　不可做：不得以正則 `\d+[mhdw]` 代替週期鍵集合。

**Task 1.2 — 判定改用單一模組**
- 目標：刪兩份重複實作。　檔案：`feature_preprocessor.py`（刪 `_is_ratio_unsafe_column`，:608 改用 `feature_naming.is_ratio_unsafe_column`）；`operators/rolling_aggregator.py`（刪 :30 重複定義，:1055 改用之）；`momentum/factories.py::ratio_unsafe_category` 改委由 `feature_naming.ratio_unsafe_category`。同步點：`tests/api/test_icpostleak_api.py:272` 之 mutant monkeypatch 目標改為 `feature_naming`；`tests/_golden/ffstat/nan_propagation_classes.json` 兩鍵改名；`scripts/verify_nan_poisoning_fix.py` 改引用新模組。
- **驗證**：`grep -rn "def _is_ratio_unsafe_column" momentum` 為 0；IC 頁對真實帶標記名（`ohlc_12h_pattern_CDLDOJI` 等）之 `excluded_features` 含之，reason `ratio_unsafe:pattern`；`transform_selected` 對帶標記 pattern 欄排除；mutant「`feature_naming.is_ratio_unsafe_column` 恆 False」⇒ IC 頁與 L3 兩處測試皆紅（同源鑑別）。
- **邊界**：①L3 生成期未標記名之行為不變（L3 存活欄數測試 `MTF_12H_L3_SURVIVOR_COUNT` 不變）；②非 pattern 欄零誤判。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得保留任何一份舊實作作相容層。

**Task 1.3 — 週期標記規則單一化**
- 目標：三種標記規則收斂為 `feature_naming.tag_timeframe`。　檔案：`feature_factory.py` 之 `_timeframe_tagged_name`、`_apply_timeframe_tag`；`multi_tf_generator.py::_apply_timeframe_tag`；`calibration.py::tagged_column_name`；`feature_storage.py` CGSA L7 寫檔標記段。
- 改法：五處皆呼叫 `tag_timeframe`；storage 段週期仍取自 group_id 前綴，但改以 `timeframe_keys()` 判定合法週期（`1w` 起被標記）。第一步先以收據確認 storage 寫檔段是否會收到 `label_` 欄與「已含他週期段」之欄（`grep` 呼叫鏈＋S1 與 12h＋4h 多週期小設定實跑欄名集合）；若會，列出受影響欄名並於本 Task 處置。
- **驗證**：S1 與「BTCUSDT 12h＋4h、近 200 天、精簡 L1」兩設定之落盤欄名集合改前改後相同（golden 名稱集合 sha256）；`1w` 單元：storage 段對 `1w` group 之欄名加標記；calibration 與 factory 對全部 FACT-RECEIPT 1 名稱 × 週期之標記結果相同；mutant「calibration 改回只看 `parts[1]`」⇒ 對「第三段起含週期鍵」之名測試紅。
- **邊界**：①`1w` 欄名由未標記變為標記——現無任何 `1w` 落盤 run（使用者 2026-10-03 已刪舊 run），不需遷移；②`label_` 欄名不變。
- **存活至**：永久（CGSA 寫檔段與 calibration）。**覆蓋風險**：FRAMEPATH（第 5 步）將刪 frame 路徑之 `_apply_timeframe_tag`（feature_factory 與 MultiTF legacy）——本 Task 對其改動僅為改呼叫單一函式、無獨立邏輯，被刪不構成白工；FF-NAME 改名時沿用。　不可做：不得改 group_id 文法。

### Phase 2 — 主路徑 L6.5 跳過 ratio-unsafe 欄（依賴：Phase 1）
**Task 2.1 — registry 全分支跳過**
- 目標：主路徑 L6.5 不改寫 ratio-unsafe 欄。　檔案：`feature_preprocessor.py` 之 `transform_registry_groups`（:747）與其下全部分支：`_maybe_run_native_l65_inplace`、`_registry_fast_transform`、`_transform_single_group_optimized`、`_transform_single_group`（legacy）、`_transform_single_group_to_arrays`、`_stream_sharded_group_to_sink`。第一步以收據盤點分支並確認群組內欄是否同質（L1 pattern 群組只含 pattern 欄；混合群組之存在與否）。
- 改法：於群組分派前判定——群組欄全為 ratio-unsafe ⇒ 整群跳過（registry 資料不覆寫）；混合群組 ⇒ 只對非 ratio-unsafe 欄轉換、ratio-unsafe 欄原值保留（若盤點證實不存在混合群組，改為斷言「群組同質」fail-closed）。`transform`（DataFrame 路徑）維持既有「入口剔除」語意不變。
- **驗證**：`pytest tests/feature_engineering/test_ratiounsafe_registry.py` 綠：§G 通過條件①②③（名稱集合 sha256、非 pattern 欄值 sha256、pattern 欄值 sha256＝前處理關之原值 sha256）；逐分支單元（強制走各分支之設定）pattern 欄值 `np.array_equal(輸出, 輸入, equal_nan=True)`；mutant「跳過判定恆 False」⇒ §G ③紅；mutant「跳過判定恆 True」⇒ §G ②紅。
- **邊界**：①全群組皆 ratio-unsafe ⇒ L6.5 無轉換、run 正常完成；②平穩化校準：ratio-unsafe 欄不進子封包（`restrict_packet` 允許校準域多出欄），不得因缺欄 fail-closed。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得自落盤成品刪除 ratio-unsafe 欄；不得以關閉 winsorization 全域代替。

### Phase 3 — 讀落盤成品之消費端（依賴：Phase 1）
**Task 3.1 — IC 頁與 IC-first 之排除對帶標記欄名生效**
- 目標：ICPOSTLEAK 設計之「ratio-unsafe 欄明示排除」對真實落盤欄名生效。　檔案：無新改動（由 Task 1.2 帶入）；新增測試。
- **驗證**：以 S1 落盤成品（暫存目錄）跑 IC 頁 `_apply_transforms_sync` 與 `transform_selected`：帶標記 pattern 欄全數列於 `excluded_features`／不在輸出；非 pattern 欄輸出與改前逐位元組相同。
- **邊界**：①全選 pattern 欄 ⇒ 既有 ValueError（全為 ratio-unsafe）；②前端 `excluded_features` 顯示不變。
- **存活至**：永久。**覆蓋風險**：ICFIRSTALIGN 乙改 `run_ic_first` 時沿用。　不可做：不改 API schema。

## §V 驗證策略與邊界測試目錄
- mutation：Task 1.1／1.2／1.3／2.1 各具名 mutant（見各 Task）；同源鑑別＝改壞單一模組使 IC 頁、L3、L6.5 三處測試同時紅。
- 測試層級：單元（命名模組）、真實資料輕量整合（S1 pattern-only 單週期，秒級）、Golden 對照（§G）。可獨立 `pytest` 執行。
- 防假綠：既有測試斷言 diff 逐處說明；L3 存活欄數、failopen 單週期基準不得變（Task 1.2 邊界①）。
- 邊界目錄：空 DF、全 NaN 欄、單段欄名、`label_`、`1w`、自訂名含週期鍵、混合群組。

## §R 回退
- 每 Phase 獨立 commit；Phase 2 為落盤值語意變更，回退＝revert 該 commit。

## §N N/A 登記
- 結構化類別落盤（逐欄 category 寫入 manifest）— `為何現在不做: blocked-by:FFSTORE（第 14 步）快照契約定義 manifest 逐欄 metadata schema`；觸發：FFSTORE SPEC 定案時改由結構化類別判定並刪名稱解析；登記處：`docs/ROADMAP.md` RM-FFSTORE。
- L2 Cross／Ratio 以 FeatureInfo 原始 source 重組欄名（含底線來源、`None_` 前綴）與 L1 正規化不一致 — `為何現在不做: blocked-by:FF-NAME（第 6 步）統一命名`；觸發：FF-NAME 開工；登記處：`docs/ROADMAP.md` RM-FFNAME。
- 既有已落盤之 pattern 欄值受 L6.5 改寫 — `為何現在不做: user-ruling:2026-10-03 使用者已核可刪除全部舊算法特徵 run`；觸發：無（資料已不存在）。
