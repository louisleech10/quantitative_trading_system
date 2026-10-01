# ICPOSTLEAK：IC 頁「套用後處理」之未來洩漏與 rank／zscore／gaussian 窗未滿即出值 — SPEC

> 來源 PLAN/診斷：`docs/ROADMAP.md` RM-ICFIRSTALIGN（「甲」部分）；`handoffs/reconcile/20260926-icfirstneed-x-consult-r1/synth.md`；`handoffs/20260927-ffstat-b4-redesign-rulings.md` R7　|　日期：2026-10-01　|　對應 TODO：`docs/manifests/ICPOSTLEAK.json`（SPEC 凍結後依 `templates/TODO_GENERATION_PROMPT.md` 生成；本版尚不存在）
> 版本：v4（審查 r3 `handoffs/reconcile/20261001-icpostleak-x-review-r3/synth.md`：通過條件改逐步驟 oracle〔該分支生產核心＋測試端獨立遮罩，逐位元組〕、改前 golden 降為對照收據、前端本地 state 型別）；v3（審查 r2 `handoffs/reconcile/20261001-icpostleak-x-review-r2/synth.md`：數值基準改逐分支自比＋跨分支既有差異凍結、順序文案全落點、保序去重、前端顯示被排除欄）；v2（審查 r1 `handoffs/reconcile/20261001-icpostleak-x-review-r1/synth.md` 全數採納：遮罩錨定步驟輸入、全分支盤點＋路徑一致性、IC 頁順序改正式順序、ratio-unsafe 欄明示排除、時間序 fail-closed、append 多窗、golden 存值、測試清單、gaussian 排名窗、zscore 主窗）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（CLAUDE.md 任務分派規則：命中 (b)(d)）。
- **命中高風險原則**：(b) 跨模組——`api/services/ic_analysis_service.py` 改呼叫 `momentum` 正式前處理；`feature_preprocessor.py` 之 rank／zscore／gaussian 被 `transform`（L6.5 與 post-IC）、`transform_selected`（`run_ic_first`）、registry 群組路徑共用。(d) ML 正確性——IC 頁輸出 `data_cache/reports/post_ic_transforms_<task>.h5` 為下游 ML 輸入，現含未來洩漏與錯誤之轉換順序。
- RISK-HIT: b,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（4 條 FACT-RECEIPT＋2 條宣告）：
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/icpostleak_probes/probe_icpage_leak.py`（收據 `handoffs/run_receipts/20261001-icpostleak-probe_icpage_leak.log`；真實 BTCUSDT 1h 前 3000 根 close、volume 為兩特徵欄；經 `ic_analysis_service._apply_transforms_sync` 真服務路徑；只把最後一列 ×50 後重跑，比前 2999 列）→ 印出 `gaussian … 值改變之格數=4039；各欄首個有限值列=[0, 0]`、`rank …=0；…=[125, 125]`、`zscore …=0；…=[49, 49]`、`rank_zscore_gaussian …=0；…=[174, 174]`（主委 實跑 2026-10-01）。⇒ 只勾 Gaussian 時為**未來洩漏**（`ic_analysis_service.py:2897-2898` 全樣本排名）；rank／zscore 窗未滿即出值（`min_periods=max(window//2, 1)`）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/icpostleak_probes/probe_formal_postic.py`（收據 `handoffs/run_receipts/20261001-icpostleak-probe_formal_postic.log`；同輸入與擾動；`FeaturePreprocessor.transform_selected`）→ 印出四組合 `值改變格數=0`；首個有限值列 rank／gaussian `62`、zscore `0`、三項 `124`（主委 實跑 2026-10-01）。⇒ 正式路徑因果；窗未滿即出值（rank／gaussian 以 min_periods 63、zscore `rolling(window, min_periods=1)`，`feature_preprocessor.py:2813`）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/icpostleak_probes/probe_order_clip.py`（收據 `handoffs/run_receipts/20261001-icpostleak-probe_order_clip.log`；重放手寫版 rank→zscore→gaussian 之公式）→ 印出 `gaussian 輸入（z 分數）有限值 5652 格，其中落在 [0.001, 0.999] 外而被裁切 4190 格（74.1%）；被裁切者 ppf 後只剩 ±3.09 兩值`（主委 實跑 2026-10-01）。⇒ 手寫版「gaussian 永遠最後」之順序把 z 分數當成 0–1 排名值做 ppf，屬**錯誤轉換**；正式順序 rank→gaussian→zscore（`_transform_single_legacy` :2962-2968）為正確者。
  - FACT-RECEIPT: `grep -rlE "<rank_transform／adaptive_zscore／gaussian_normalize 啟用或呼叫三項內部函式之樣式>" tests --include='*.py' | wc -l` → 印出 `18`（主委 實跑 2026-10-01；清單見 Task 1.3）。
  - 宣告——IC 兩路涵蓋：本票轉換作用於特徵矩陣之時間序列——**全域序列型**：涵蓋、為本票主體；**事件型**：IC 頁「套用後處理」只接 IC 任務之 `req_features_path`／`symbol+timeframe` 特徵矩陣（`ic_analysis_service.py:2853-2861`），不接事件批 ⇒ 不涉及。
  - 宣告——分支盤點（Task 1.1 第一步以收據確認並補漏）：三項轉換於前處理器之實作分支＝①legacy `_transform_single_legacy`（:2962 rank、:2965 gaussian、:2968 zscore）；②optimized `_transform_single_optimized_df`（:2863 rank、:2879 gaussian、:2901 zscore）；③Polars `_transform_single_polars`（:3020 rank、:3043 zscore；gaussian 另見其內）；④registry 群組 `_transform_single_group`（:2198，numba 轉換＋:2241 gaussian 後置）、`_transform_single_group_to_arrays`（:2293，:2325）、`_stream_sharded_group_to_sink`（:2436，:2490）；⑤共用核心 `_rolling_rank_2d_v2`（:3856）、`_gaussian_2d`（:3919）、`_rolling_zscore_2d`（:2791）。
- **待使用者確認**：待確認：無（使用者 2026-10-01 宣告離線並授權「有問題你跟委員討論共識」；IC 頁順序改正式順序、ratio-unsafe 欄明示排除兩項屬語意變更，以委員共識定並於完工回報逐條告知使用者）。
- **已確認結果**：
  - `2026-10-01 使用者「FF-STAT完成後，IC 頁洩漏要先修」`；同日「有問題你跟委員討論共識，之後再跟我說發生哪些事和如何處理」。
  - `2026-09-27 使用者 R7 裁定`：post-IC 之排名轉換與自適應 z 分數窗未滿即出值，一併處理（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）。
  - `2026-09-26 使用者裁定`：IC 頁第三步改用正式實作並淘汰手寫版與其洩漏（`docs/ROADMAP.md` RM-ICFIRSTALIGN）。
  - `2026-09-17 使用者`：未來洩漏必修、不得列殘留；修法與驗法由主委與委員決定。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦：API 服務取前處理器一律經 `momentum.factories`（Rule 3）；`momentum/` 不得 import `api/`。
- 不弱化 NaN／inf 閘；不改輸出列數；欄名／欄數之變更僅限 §P Task 2.2 明示排除者。
- **窗未滿之定義**：沿用 FF-STAT b4 第①類之語意（窗內未滿 `window` 個觀測之輸出不公開），**錨點＝該步驟之輸入**：逐欄 `cut = 步驟輸入首個有限值列 + window − 1`，`[0, cut)` 設 NaN。b4 縮尾之 `mask_incomplete_window_inplace` 以輸出首個有限值為錨點，僅因縮尾輸出之 NaN 位置＝輸入（`stable_mask.py:216-219`）而等價；rank／gaussian 之 min_periods > 1 使輸出首個有限值晚於輸入，故不得沿用輸出錨點。新增 `stable_mask` 純函式以輸入錨點實作，縮尾之既有呼叫不改。
- **各步驟之 window**：rank＝`rank_config.window`；gaussian＝其因果排名窗 `_rolling_window()`（`winsor_config.window`，未設則 `rank_config.window`，再未設 252；`feature_preprocessor.py:552-554`）；zscore＝每個實際輸出之窗（replace 模式＝`windows[0]`，append 模式＝每個窗各自）。
- **時間序**：三項皆為依列序之 rolling ⇒ 輸入 index 若為時間戳，須嚴格遞增；非嚴格遞增（倒序、重複、亂序）⇒ fail-closed（`ValueError` 列出違規位置），不靜默排序。
- 本任務特別注意：前端只動 Task 2.2 之型別與結果區；`transform_selected` 之 caller `feature_factory.py:2730`（`run_ic_first`）；API 回應 schema（`api/models/ic_models.py:413-440`）只得**新增**選填欄；h5 `analysis_status`／`oos_guarantees` attrs 寫入契約（B3-XFORM-01）不變。
- 不得侷限加密貨幣：窗口單位為「根」（`ic_models.py:420` 現寫「天」，改正）。

## §G Golden / Baseline
- **feature/kline 條件**：適用——真實 `data_cache/feature_klines/kline_cache.h5`（`ffstat_helpers.kline_frame()`）；禁合成 fixture。
- **輸入集**：「真實 BTCUSDT 1h 前 3000 根之 close、volume 與 3 個真實 L1 特徵欄（含 1 欄前段 NaN 之晚生欄）」：①`transform_selected` × 七種開關組合（rank、zscore、gaussian 之非空子集）；②`transform`（mode＝append）× zscore 窗 [100, 252] × 開 rank 與否；③各分支（§A 分支盤點①–④）× 同上組合。
- **逐步驟 oracle**（通過條件之參照；測試端實作）：對每分支、每組合，依正式順序 rank→gaussian→zscore 逐步：取上一步之 oracle 輸出（首步取原輸入）→ 呼叫**該分支之生產數值核心**（本票不改之函式：`_rolling_rank_2d_v2`／`_gaussian_2d`／`_rolling_zscore_2d`、numba `transform_array_fast` 之對應單步、Polars `polars_l65_rank_transform`／`polars_l65_adaptive_zscore` 等，Task 1.1 盤點收據列全）→ 以**測試端獨立實作**之輸入錨點遮罩（§C 定義；不呼叫生產 `stable_mask`）遮之。累積式核心（pandas／bottleneck 滾動 mean、std）之後段末位元依前段輸入而變，故參照必以「遮罩後之步驟輸入」實算，不得以改前全輸出代之。
- **通過條件（可證偽）**：改後每欄 ①首個有限值列＝oracle 之首個有限值列（等價於依 §C 錨點與窗逐步累加之期望，測試另以純整數公式獨立核對）；②全陣列與 oracle **逐位元組相同**（含 NaN 位置）；③列數、欄名、欄數同改前。任一不符即列出分支、欄名與差異＝FAIL。
- **改前對照收據**（資訊性，非通過條件）：動工前以 HEAD 存 `tests/_golden/icpostleak/baseline.npz`（逐組合、逐分支之 float64 陣列＋欄名＋index）與 `baseline.json`（名稱集合 sha256、列數、逐欄首個有限值列；③之欄名欄數比對以此 sha256 為準）；改後產 `handoffs/run_receipts/<日期>-icpostleak-change-report.json`：逐分支、逐欄之首個有限值列（改前→改後）、遮罩後區段與改前之差異格數與最大絕對差（窗內純函式核心預期 0，累積式核心與改序之 registry 分支預期非 0 並具名列出）。
- IC 頁：改後 `_apply_transforms_sync` 之輸出與同參數（§P Task 2.1 之映射）`transform_selected` 輸出**逐位元組相同**（同欄序）。

## §P Phase 與依賴

### Phase 1 — 三項轉換全分支之窗未滿遮罩（依賴：無）
**Task 1.1 — 輸入錨點遮罩與全分支套用**
- 目標：rank／zscore／gaussian 之輸出於各自窗未滿之列為 NaN，於 §A 分支盤點之每一分支。　檔案：`stable_mask.py` 新增輸入錨點遮罩純函式；`feature_preprocessor.py` 之分支①–⑤。既有 caller：`transform`、`transform_selected`、`transform_registry_groups`／`transform_registry_groups_to_sink`。
- 改法：第一步以 `grep` 盤點收據（`handoffs/run_receipts/<日期>-icpostleak-branch-inventory.txt`）確認 §A 分支清單、補漏；每分支於每個步驟產出後，以「該步驟輸入之首個有限值」與 §C 之窗呼叫新純函式；不改三項之數值公式與 min_periods。分支間之步驟順序若與 legacy（rank→gaussian→zscore）不同，改為同序。
- **數值基準**：各分支之數值核心本即不同（pandas float64〔`_rolling_zscore_2d`〕、numba／bottleneck float32〔`_numba_transforms.py`〕、Polars 表達式〔`polars_adapter.py`〕；本票不改公式）⇒ 每分支之通過條件為對**該分支之 §G 逐步驟 oracle** 逐位元組相同；跨分支數值不要求相等，其量級入收據 `handoffs/run_receipts/<日期>-icpostleak-branch-diff.json`（逐分支對 legacy 之最大絕對差、最大相對差、差異格數），作 §N 殘留之輸入。
- **驗證（可證偽）**：`pytest tests/feature_engineering/test_icpostleak.py -k "phase1"` 綠——①§G 通過條件於七組合、append 多窗、晚生欄、各分支全符；②**路徑一致性**：同一輸入於分支①②③④（以 `FFACT_USE_POLARS`、optimized 條件、registry 群組入口切換）之**遮罩位置（逐欄首個有限值列）、步驟順序、參數**逐分支完全相同；數值依上列「數值基準」比對（不加 atol、不刪格）；③擾動最後一列 ⇒ 前 2999 列逐位元組不變；mutant 各自使具名測試紅：遮罩 identity、遮罩錨點改用輸出首個有限值、遮罩窗 `window−2`、任一分支漏遮（逐分支各一）、append 只遮第一窗。
- **邊界（≥2）**：①全 NaN 欄 ⇒ 全 NaN、不拋錯；②晚生欄 ⇒ 錨點自該欄首個有限值；③列數 < window ⇒ 全 NaN、不拋錯；④三項鏈式 ⇒ 首個有限值逐步累加；⑤zscore 常數窗沿用現行 `where(std > 0, 0)`。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得改三項之數值公式；不得以放寬比較範圍換綠；不得另立與 §C 不同之窗未滿定義。

**Task 1.2 — 時間序 fail-closed**
- 目標：三項轉換之入口（`transform`、`transform_selected`、registry 群組入口）於 DatetimeIndex 非嚴格遞增時拋 `ValueError`。
- **驗證**：`pytest tests/feature_engineering/test_icpostleak.py -k "time_order"` 綠——倒序、重複時間戳、單點亂序三案例皆拋錯且訊息含首個違規位置；嚴格遞增與 RangeIndex 不拋；mutant「移除檢查」使三案例紅。
- **邊界**：①RangeIndex（L7 raw 讀回）⇒ 不檢；②長度 0／1 ⇒ 不拋。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得靜默排序。

**Task 1.3 — 既有測試 oracle 更新（18 檔）**
- 目標：依 §A 第 4 條收據之 18 檔，凡依賴三項轉換早段出值之斷言，改以測試端獨立遮罩之 oracle 比對（同 FF-STAT b5 `test_winsorize_partition_opt.py` 作法：遮罩後其餘值逐值比、加「遮罩後仍有可比有限值」前提斷言、fixture 列數 ≤ 窗則加大列數或局部設窗）；含 `tests/feature_engineering/preprocessing/test_ff_causal_golden.py` 之 gaussian 全陣列比對。清單由驗證命令產出並逐檔處置記於 brief。
- **驗證**：`pytest <18 檔逐檔明列>` 之全部節點綠（以 `--collect-only -qq` 取清單）；每項改寫附「遮罩 identity」mutant 下該節點紅之實跑；`git diff` 斷言行數不減、atol／rtol 不變。
- **邊界**：①斷言本身驗早段出值 ⇒ 逐條說明退役理由；②fixture 過短 ⇒ 加大列數，不刪測試。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得 skip／xfail 暫避。

### Phase 2 — IC 頁改用正式實作（依賴：Phase 1）
**Task 2.1 — `_apply_transforms_sync` 改呼叫正式 post-IC 轉換**
- 目標：刪除 `ic_analysis_service.py:2873-2905` 手寫三項；以 `momentum.factories` 取得前處理器，組 `PreprocessingConfig`（縮尾、fracdiff、ADF 關閉，mode＝replace；`rank_transform.window`＝`rank_window`；`adaptive_zscore.windows`＝`sorted(zscore_windows)`〔保留手寫版以最小窗為主窗之語意〕；`gaussian_normalize.enabled`＝`gaussian`），呼叫 `transform_selected(kept_cols, {"ic_page": df}, config=…)`。
- 改法：轉換順序改為正式順序 rank→gaussian→zscore（§A 第 3 條收據：手寫順序 74.1% 裁切）；`transforms_applied` 依實際順序填；所有宣稱舊順序之文案同步改為正式順序——`api/models/ic_models.py:419`（`gaussian` 欄說明）、`api/services/ic_analysis_service.py:2814`（`apply_transforms` docstring）、`api/routes/ic_analysis.py:750`（route docstring，即 OpenAPI 敘述）；`ic_models.py:420` `rank_window` 說明「（天）」改「（根）」；落盤、attrs 不變。`selected_features` 於入口**保序去重**（現行未去重：`ic_analysis_service.py:2865-2871` 與 `transform_selected` 皆保留重複），去重後之清單同時用於 kept_cols、excluded_features 與各計數。
- **驗證（可證偽）**：`pytest tests/api/test_icpostleak_api.py` 綠——①七組合下改最後一列 ⇒ 前段逐位元組不變（改前 gaussian 4039 格之反例轉綠）；②輸出與同映射之 `transform_selected` 逐位元組相同；③`zscore_windows=[252, 100]` 與 `[100, 252]` 輸出相同（主窗＝100）；④`grep -c "rank(pct=True, axis=0)" api/services/ic_analysis_service.py` == 0；⑤`tests/api/test_ic_la1_degraded_gate.py` 之 apply_transforms 節點綠；⑥`grep -c "rank → zscore → gaussian\|rank/zscore 之後" api/models/ic_models.py api/services/ic_analysis_service.py api/routes/ic_analysis.py` 各 == 0；⑦`selected_features` 含重複名 ⇒ 輸出欄不重複、`selected_feature_count`＝去重後數；mutant「恢復全樣本排名」使①紅、「改回 gaussian 最後」使②紅、「不排序 zscore 窗」使③紅、「移除去重」使⑦紅。
- **邊界（≥2）**：①selected_features 部分不存在 ⇒ 維持 warning＋只轉存在者；全不存在 ⇒ 維持 ValueError；②三開關全關 ⇒ 維持 ValueError；③請求窗 > 資料列數 ⇒ 全 NaN、不拋錯；④檔案輸入 index 倒序 ⇒ Task 1.2 之 ValueError 經 API 回 4xx／5xx 而非靜默輸出。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不改 API 路由路徑與既有回應欄位。

**Task 2.2 — ratio-unsafe 欄明示排除**
- 目標：`transform` 入口丟棄 `_is_ratio_unsafe_column` 欄（`feature_preprocessor.py:600-612`），IC 頁改接後不得**靜默**少欄（審查 r1 三家）。
- 改法：IC 頁於呼叫前以同一判定函式分出 ratio-unsafe 欄，不送轉換、不寫入輸出；回應新增選填欄 `excluded_features: List[{"name", "reason"}]`（reason＝`ratio_unsafe:<category>`），並 warning log；選中欄全為 ratio-unsafe ⇒ `ValueError`（訊息列欄名與原因）。`ApplyTransformsResponse` 只新增選填欄。前端顯示：`frontend/src/hooks/useICAnalysis.ts:751` 之回應型別加選填 `excluded_features`；`frontend/src/app/ic-analysis/page.tsx` 之本地 state 型別（:149 `applyTransformsResult`）加選填 `excluded_features`，結果區（:906-915）於非空時列出被排除之欄名與原因。
- **驗證**：`pytest tests/api/test_icpostleak_api.py -k "ratio_unsafe"` 綠——混入 1 個 pattern 欄 ⇒ 輸出欄數＝選中數−1、`excluded_features` 恰列該欄；全為 pattern 欄 ⇒ ValueError；mutant「不填 excluded_features」使前者紅；前端 `cd frontend && npm run build` rc=0，且 `vitest` 對結果區之元件測試：`excluded_features` 非空時渲染欄名與原因、為空時不渲染（mutant「不渲染」使之紅）。
- **邊界**：①無 ratio-unsafe 欄 ⇒ `excluded_features == []`、前端不顯示；②同名欄重複選取（numeric 與 ratio-unsafe 各一例）⇒ 依 Task 2.1 保序去重後只計一次。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得改 `_is_ratio_unsafe_column` 之判定；不得把 ratio-unsafe 欄未轉換即寫入輸出。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用（RISK-HIT 含 d）。mutant 清單見各 Task 驗證欄；共通：遮罩 identity、錨點改輸出、窗 `window−2`、逐分支漏遮、append 只遮第一窗、移除時間序檢查、恢復全樣本排名、gaussian 改回最後、zscore 窗不排序、不填 excluded_features。
- 測試層級：單元（純函式遮罩邊界、時間序）、整合（真實 kline 之各分支、IC 服務真路徑）、Golden 對照（§G 存值逐位元組）。皆可獨立 `pytest` 執行，不需 `run_api.py`。
- **防假綠**：oracle 遮罩由測試端獨立實作；「遮罩後仍有可比有限值」前提斷言；路徑一致性測試防單一分支漏改。
- **邊界目錄**：空DF／全NaN欄／晚生欄／列數 < 窗／std=0／倒序與重複時間戳／ratio-unsafe 欄／鏈式轉換。

## §R 回退
- Phase 1、Phase 2 各自獨立 commit 可單獨 revert；§G 不符 ⇒ 不 merge。不設 feature flag（洩漏修正不得保留可切回之洩漏路徑）。

## §N N/A 登記
- (a)、(c) 不命中：不改三項之數值公式（只遮窗未滿列、改 IC 頁順序為正式順序）；兩 Phase、可回退。
- 前端：只改 Task 2.2 之型別與結果區顯示被排除欄；不改流程與其他元件。
- 殘留：
  - 各分支 zscore 數值核心不一致（pandas float64／numba float32／Polars）——`為何現在不做: needs-research:差異量級是否超出 float32 精度與下游是否依賴分支一致（Task 1.1 量級收據為輸入）`；觸發：量級收據之最大相對差 > 1e-3（`FLOAT16_MAX_REL_ERROR` 同級）或任一下游以分支切換比對數值；登記處：`docs/ROADMAP.md` 本票列之 pointer 與本 SPEC。
  - ICFIRSTALIGN 乙部分（不可變 run context、L7 raw 讀回時間軸）——`為何現在不做: user-ruling:2026-10-01 使用者裁定 IC 頁洩漏修完後開全票細項排序諮詢定序`；觸發：該諮詢定案；登記處：`docs/ROADMAP.md` RM-ICFIRSTALIGN。
