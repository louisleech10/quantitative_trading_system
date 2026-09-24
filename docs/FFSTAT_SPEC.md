# FF-STAT：平穩化處理之判定不得依欄名（免檢判定結構化、d\* 例外 fail-closed、刪 layer1_only）— SPEC

> 來源 PLAN/診斷：研究輪 `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`（兩家＋主委獨立版五題一致、零駁回）　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFSTAT.json`（本 SPEC 定案後產出）
> 版本：v1（主委起草）

## §RISK 風險分級
- **大小**：大（命中 a、b、d）。
- **命中高風險原則**：(a) 決定哪些特徵做 fracdiff／ADF 差分，直接改特徵數值；(b) 跨模組——`utils/adf_safe_skip.py`、`preprocessing/feature_preprocessor.py`、`operators/derived_operators.py`（衍生欄身分）、`feature_factory.py`（身分傳遞）、`core/column_group_registry.py`；(d) 特徵平穩性影響 IC 與模型。
- 不命中 (c)：只對新 run 生效；使用者 2026-09-24 裁定舊資料可刪除重生。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認
- **已驗證事實**（6 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `sed -n 95,150p momentum/FeatureEngineering/utils/adf_safe_skip.py` → `is_safe_skip` 以欄名子字串比對封閉 pattern 集，無層／運算子判別（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `grep -n '_apply_adf_safe_skip' momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 呼叫於 fracdiff 目標篩選（`:2855`、`:2859`、`:2884`、`:2910`）與 ADF 差分（`:3314`）（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: 主委 ADF 探針（`handoffs/20260924-ffnamestat-x-consult-r1-claude.md` 題二 3b）→ reference run 12h L2 Ratio：今日白名單免檢之單組件類 60 欄中 1 欄 ADF p>0.05；多組件類最大絕對值 12h 2021、1h 210288（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: codex 研究輪碼證 `derived_operators.py:397-399,545-549` → Cross＝`fast - slow`（差值，非離散訊號）、Ratio＝`a / safe_denominator(b)`；`AROON-aroondown_55` 分母為 0 者 1824／20352 列（codex 實跑 2026-09-24，研究輪收斂檔逐字附錄）。
  - FACT-RECEIPT: `sed -n 3035,3060p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `cache.get`／`_find_min_d` 拋例外時 `d_star=1.0` 套用並只記 warning（主委 讀檔 2026-09-24；研究輪兩家同判）。
  - FACT-RECEIPT: `grep -rn layer1_only momentum api frontend/src config` → 只命中 `feature_preprocessor.py:3564` 定義處；fracdiff 層範圍由 `momentum/core/config.py:18` 之 `_OPTIMIZED_FRACDIFF_LAYERS={"L1","L2"}` 寫死（主委 實跑 2026-09-24）。
- **已知結構化身分來源**：CGSA 路徑之 `ColumnGroup`（`core/column_group.py:76-81`）帶 `layer`、`indicator`；L2 以運算子分組（`L2_Ratio`、`L2_Cross`、`L2_Distance`、`L2_BinarySignal`、`L2_Momentum`、`L2_WorldQuant`），其中 `L2_WorldQuant` 一組混多種運算子 ⇒ **須逐欄身分**；frame 路徑只有 `_column_layer_map`（欄→層）。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-24 使用者「看名稱決定是否要平穩化，在量化數據好像是很嚴重的問題，需要盡早研究處理」「fracdiff layer1 only……是寫死的也沒有要給使用者動」「舊名稱或數據都可以刪掉舊的重新生成」。

## §C 約束
- 名稱不得參與任何數值處理之判定（免檢、fracdiff 目標層、ADF 差分候選）；欄名只作顯示與索引。
- 免檢判定之單一真相源＝新 JSON 封閉表 `config/stationarity_exempt.json`（逐項：層、運算子或指標身分、數學理由類別〔有界／差分構造／離散〕、出處）；SPEC 不列舉其內容。
- **比值（Ratio）與差值（Cross、Distance）類一律須檢定**，不論輸入指標是否有界（§A 實測與 codex 碼證）。
- d\* 搜尋或快取讀取例外：該欄**不套用** fracdiff、記入 run 之品質欄（沿用 FF-TFMETA 之 `apply_quality_degradation` 同一機制，不另加層），run 標 `partial`；不得以任何預設 `d` 替代。parallel 路徑與快取寫入同規則（例外之欄不得寫入 d\* 快取）。
- 刪除 `apply_to="layer1_only"` 分支與其寫死前綴；設定驗證對該字面明確拒收（不得落入 regex／其他路徑）。
- 不改 fracdiff 層範圍（L1、L2 寫死，使用者確認）。
- 特徵欄數、列數不變；允許變動之數值限於「免檢判定改變之欄」與「d\* 例外之欄」，兩者之欄集合由收據列舉。

## §G Golden / Baseline
- **feature/kline 條件**：適用。真實 `data_cache/feature_klines/kline_cache.h5`；沿用 `tests/feature_engineering/fftfmeta_golden_helpers.py` 之 run 隔離，輕量真實設定開 fracdiff（L1、L2）、L2 Ratio／Cross／WorldQuant、多組件有界指標；序列 CGSA；禁合成 fixture。
- **凍結**：動工前以當下 HEAD 跑一次，存 `tests/_golden/ffstat/baseline.json`：逐欄四 hash（dtype、shape、NaN mask sha256、值 sha256）＋每欄之「今日免檢判定」與「今日是否 fracdiff」。
- **通過條件（可證偽）**：改後同參數重跑——①欄名集合全等；②定義差集 Δ＝判定改變之欄（依新封閉表與新規則逐欄推導，由測試 helper 以結構化身分計算，不得以欄名推導），Δ 以外每欄四 hash 全等；③Δ 內每欄記改前改後之 fracdiff 與否、`d`、NaN mask 與值 hash 於收據；④注入 d\* 搜尋例外之欄於改後不 fracdiff、run 之品質欄含 `fracdiff_search_failed` 且 `quality_status == "partial"`。

## §P Phase 與依賴

### Phase 1 — 逐欄結構化身分（依賴：無）
**Task 1.1 — 身分定義與產出**
- 目標：每個進入 L6.5 之 L1／L2 欄有結構化身分 `(layer, kind, name)`：L1 之 kind＝`indicator`、name＝指標輸出身分（TA-Lib 多輸出含輸出名）；L2 之 kind＝`operator`、name＝運算子名。　檔案：`operators/derived_operators.py`（衍生欄產出時同步產出身分）、atomic 模組之 metadata（L1）、`feature_factory.py`（身分隨 layer 傳遞）、`core/column_group_registry.py`（CGSA 群組逐欄身分往返）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_identity.py` 綠——真實輕量 run 中每個 L1／L2 欄皆有身分、無缺漏（欄集合相等）；`L2_WorldQuant` 群組內各欄之運算子逐欄正確（抽樣與產出函式對照）。
- **邊界**：①欄無身分 ⇒ fail-closed（不得退回欄名判定）；②resume 讀回之群組身分與首跑相同。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得由欄名解析身分。

### Phase 2 — 免檢判定改依身分（依賴：Phase 1）
**Task 2.1 — 封閉表與判定函式**
- 目標：`config/stationarity_exempt.json` 為單一真相源；`adf_safe_skip` 改為以身分查表。　檔案：新 JSON、`utils/adf_safe_skip.py`、`feature_preprocessor.py` 之 `_apply_adf_safe_skip` 及其呼叫點、`_FRACDIFF_LAYER_RE` 名稱解析退路（改為身分之 layer，缺即 fail-closed）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_exempt.py` 綠——同一身分不論欄名如何皆得同一判定（改欄名 mutation 不改判定）；Ratio、Cross、Distance 身分一律不免檢；封閉表每項附數學理由類別。
- **邊界**：①封閉表缺檔或格式錯 ⇒ fail-closed；②使用者 `additional_patterns`／`exclusion_patterns` 設定（今以子字串）改為以身分表達或移除——由委員研判是否有使用者依賴。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留子字串比對作後備。

### Phase 3 — d\* 例外 fail-closed 與刪 layer1_only（依賴：無）
**Task 3.1 — d\* 例外**
- 檔案：`feature_preprocessor.py:3035-3060` 與 parallel 路徑。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_dstar_failure.py` 綠——注入 `_find_min_d` 拋例外 ⇒ 該欄值未 fracdiff、快取未寫該欄、品質欄含 `fracdiff_search_failed:1`、run `partial`；循序與 parallel 各一。
- **邊界**：①快取讀取例外（`cache.get`）同規則；②全部欄皆例外 ⇒ run `partial` 而非 `complete`。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得以任何預設 `d` 替代。

**Task 3.2 — 刪 `layer1_only`**
- **驗證**：`pytest tests/feature_engineering/test_ffstat_apply_to.py` 綠——設定 `apply_to="layer1_only"` ⇒ 設定驗證拋錯（訊息指名該值已移除）；`non_stationary` 行為不變。
- **邊界**：①list 形 `apply_to` 不受影響。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留該分支為相容。

### Phase 4 — 收尾（依賴：Phase 1–3）
**Task 4.1 — §G 對照與收據**
- **驗證**：`pytest tests/feature_engineering/test_ffstat_golden.py` 綠；收據 `handoffs/run_receipts/<日期>-ffstat-golden.json` 列 Δ 欄數、各類分佈、每欄改前改後 hash。
- **邊界**：①fracdiff 關閉之設定 ⇒ Δ 為空。
- **存活至**：收據永久。**覆蓋風險**：無。
- 不可做：不得放寬 §G 通過條件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用。至少五個 mutant 必使具名測試紅：①判定退回欄名子字串；②Ratio 身分加入免檢表；③d\* 例外改回 `d=1.0`；④身分缺漏時退回欄名；⑤`layer1_only` 分支恢復。
- **防假綠**：`tests/feature_engineering/test_adf_safe_skip.py` 既有斷言中「依欄名」者改為依身分，須逐條於對照表說明，不得刪除。
- **邊界目錄**：無身分之欄、封閉表缺檔、d\* 例外（循序／parallel／快取）、fracdiff 關閉、`layer1_only` 設定。

## §R 回退
- 各 Phase 獨立 commit；只對新 run 生效；§G 不等 ⇒ 不 merge。不設 feature flag。

## §N N/A 登記
- (c) 不命中：見 §RISK。
- 殘留：各類免檢之數學理由以真實資料之系統性檢定（≥3 個標的、多週期之 ADF／KPSS 分佈）— `為何現在不做: needs-research:本票以「比值與差值一律檢定」之保守規則消除已知反例，其餘有界類之免檢是否仍應保留，須跨標的實測後裁定`；觸發：本票收案後；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
