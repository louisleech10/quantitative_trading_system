# IC Phase 0 TODO（狀態 DRAFT｜基於 `docs/IC_PHASE0_SPEC.md` v2｜2026-06-25）

> 冷啟動執行端不需讀其他檔即可逐 Task 寫碼。SPEC 索引覆蓋 manifest `handoffs/20260625-ic-PHASE0-MANIFEST.md` 全 30 ID。
> reconcile 來源：`handoffs/20260625-ic-PHASE0-ADVERSARIAL-RECONCILE.md`（雙家族收斂）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **解耦 7 條**：`grep -r "from api\." momentum/`→0；`momentum/` 不 import `api/`；服務不互 import；engine 經 factories/protocols。`[M-4]`
- **不可違反原則**：`[M-1]` 命中 (b)跨模組共用路徑 +(d)ML/回測正確性 → 高風險。**不靜默截斷特徵**（feature_filter 預設不截斷、僅顯式套用、metadata 可審計）、不弱化 NaN·inf gate、不改 IC 數值語義（僅修錯的 T 時間軸、B 契約）。
- **Logging**：`from api.core.logging import get_logger`；熱迴圈零 log（D 即修此）。
- **防假綠**：不得放寬/刪除既有測試斷言換綠燈；驗收 diff 斷言。C-3/T-3 走 TDD 兩 commit（先紅後綠）。`[M-2]`
- **§A 事實標籤**：fact-verified（實跑）/code-verified（讀碼）/assumed。IC-BYVOL 已委員會收斂（fail-closed），不問使用者。`[M-3]`
- **§A 六項事實摘要**（執行端不必回讀 SPEC）`[M-2]`：① CRASH=orchestrator:1139 傳 pydantic GroupedConfig 給 dict-API compute_grouped_ic:371/377〔code〕；② TIMEAXIS=read_klines 回 RangeIndex+秒級 timestamp，_get_time_index:1025 對 Series 用 unit=ms → 回 Series → _iter_time_groups:1011 `.to_series()` AttributeError〔fact〕；③ BYVOL=schema:80 預設 True，engine:383-400 無 by_volatility 分支〔code〕；④ FEATURE-GUARD=filter 進 config_override 被 ICConfig.model_validate 丟棄（無 extra=forbid），前端預設 max_features:30〔fact〕；⑤ DECAY=_fit_exponential_decay 熱迴圈 4 處 warning（:904/:918/:944/:958）〔code〕；⑥ UX=service longitudinal:209-216 + cross-sectional:154-159 同步阻塞，WS failed payload 用 `message` 欄〔assumed/code〕。
- **回退**：每 epic 獨立 commit 可單獨 revert；Golden FAIL 不 merge。`[M-6]`
- **不可做（全域）**：`[M-7]` 串流重寫/train-test/case-control/decay R2 early-skip/decay·grouped 向量化/resume-retry/by_volatility 分組實作——皆留後 Phase。

## §B 批次執行策略（依賴拓撲 → 最少批次）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1 崩潰止血** | 1.1, 1.2 | 無 | 最優先；grouped 路徑可達前置 | 小 |
| **B2 正確性硬閘** | 2.1, 2.2, 2.3 | B1（grouped 路徑修通才能測時間軸/byvol） | 同檔 `ic_engine.py` grouped 區，一次改 | 中 |
| **B3 feature_filter 落地** | 3.1, 3.2, 3.3, 3.4, 3.5 | **B2（同改 `ic_config_schema.py`：B2 Task 2.3 改 :80、B3 Task 3.1 加 feature_filter 欄）→ B3 須 B2 合併後再動，避免 merge conflict** | 同一 feature_filter 端到端鏈 | 中 |
| **B4 效能/體感** | 4.1, 4.2, 4.3, 4.4 | 無（可平行） | decay log + 前後端 UX 一束 | 中 |

- **批次間 Gate**：每 Batch 完成跑 `pytest tests/momentum/ tests/api/ -q` 全綠 + 對應 golden 不 FAIL 才進下一批。
- **派工 prompt（每批可直接複製）**：見各 Phase 末「派工 prompt」框。

---

## Phase 1 — 止血崩潰（完成後：grouped 路徑不再 AttributeError，真 config 可跑）

### Task 1.1 — IC-CRASH 修契約 `[C-1]` `[C-2]`
- SPEC ref：Task 1.1。目標：caller 傳 dict 給 dict-API `compute_grouped_ic`。
- 輸入 / 輸出：orchestrator `config.ic_calculation.grouped_analysis`（pydantic GroupedConfig）/ 傳 dict。
- 實作要點：
  1. `ic_filter_orchestrator.py:1139`：`config.ic_calculation.grouped_analysis` → `config.ic_calculation.grouped_analysis.model_dump()`。
  2. grep 確認 `compute_grouped_ic` 僅此 caller（已驗，勿改 engine 簽名 `[C-2]`）。
  3. 不加 isinstance band-aid（A3）、不改 engine `config: dict` 簽名（A2）。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（`_compute_ic_results` 內 :1134-1140 呼叫）。既有 caller：僅此一處。
- 不可做：不改 `ic_engine.compute_grouped_ic` 簽名、不防禦式 isinstance。
- 邊界：grouped_analysis 全 False → 回空 dict 不崩；`include_regime_analysis=False` → grouped_ic=None 不進分支。
- 風險緩解：(d) 正確性——A1 最小改面。
- 驗證：對應 Test 1.2；`pytest` 真 config + `include_regime_analysis=True` 不拋 `AttributeError`、回傳 dict 含 `grouped_ic`。

### Task 1.2 — IC-CRASH 真路徑回歸測試 `[C-3]`
- SPEC ref：Task 1.2。目標：取代 SimpleNamespace+dict 假綠。
- 輸入 / 輸出：真 `ICConfig`(regime on) + 小真實 features/label/raw_data / 測試 pass。
- 實作要點：
  1. 新增 `tests/momentum/test_ic_crash_real_config.py`：建真 `ICConfig`（pydantic）打 orchestrator grouped 路徑。
  2. **點名取代/平行** 函式 `test_stage4_ic_calculation_with_kline_reader`（`tests/momentum/test_ic_filter_orchestrator.py`，~:524 起，關鍵 :541-548 用裸 dict `grouped_analysis={...}`）：須改為傳 **pydantic `GroupedConfig` 或 `.model_dump()` 後 dict，禁裸 dict 繞過 pydantic**。
  3. TDD：僅加測試 commit 時 fail（重現 `'GroupedConfig' object has no attribute 'get'`）。
- 修改檔案：新增 `test_ic_crash_real_config.py`；改 `test_ic_filter_orchestrator.py`。既有 caller：N/A 測試。
- 不可做：不用 dict/SimpleNamespace 繞過 pydantic。
- 邊界：raw_data=None → 不進 grouped 分支不崩；regime off → grouped_ic None。
- 風險緩解：防假綠。
- 驗證：`pytest tests/momentum/test_ic_crash_real_config.py` 僅加測試 commit 紅 → 修 1.1 後綠。

> **派工 prompt B1**：「修 IC-CRASH。讀 `docs/IC_PHASE0_SPEC.md` Task 1.1/1.2 + 本 TODO。改 orchestrator:1139 傳 model_dump()；新增真 config 回歸測試取代 :535-549 假綠。TDD 先紅後綠。跑 `pytest tests/momentum/ -q` 全綠。完成輸出 STATUS: DONE / BLOCKED — 原因。」

---

## Phase 2 — 正確性硬閘（完成後：grouped 時間軸正確、by_volatility 不靜默忽略）

### Task 2.1 — IC-TIMEAXIS 回 DatetimeIndex + 單位實測 + fail-closed `[T-1]` `[T-2]`
- SPEC ref：Task 2.1。目標：修「回 Series → `_iter_time_groups` 崩潰」**且**自判秒/毫秒、異常 fail-closed。
- 輸入 / 輸出：`raw_data`(RangeIndex+timestamp int64 秒) / `_get_time_index` 回 `pd.DatetimeIndex`。
- 實作要點：
  1. `_get_time_index`（ic_engine.py:1018-1027）numeric 分支：`unit = "ms" if v>=1e12 else "s"`；`>=1e15` → `raise ValueError`；回 `pd.DatetimeIndex(pd.to_datetime(values.to_numpy(), unit=unit))`（**非對 Series 呼叫**）。
  2. sanity：解出年份 `<1990` 或 `>今年+1` → `raise ValueError`（訊息含實際年份）。
  3. 確認回傳 index 與 `raw_data` 對齊（`_iter_time_groups` 的 `.loc[idx]` 用 raw_data labels）。
- 修改檔案：`momentum/Analysis/ic_engine.py:_get_time_index`（+ 必要時 `_iter_time_groups` group label 對齊）。既有 caller：`_iter_time_groups`(by_year/quarter)。
- 不可做：不寫死單位、不回傳 Series、不靜默吞錯軸。
- 邊界：已是 DatetimeIndex → 原樣回；無時間欄 → None 不崩；NaN timestamp → 明確處理；1e16 → raise。
- 風險緩解：(d) 正確性——Golden grouped。
- 驗證：Test 2.2；`pytest` fixture `timestamp=1704067200` → DatetimeIndex 且 `_iter_time_groups('year')` 不拋錯、year==2024；1970/2100/1e16 → raise。

### Task 2.2 — IC-TIMEAXIS kline-shape byte-faithful 回歸 `[T-3]`
- SPEC ref：Task 2.2。目標：fixture 重現真實 kline 形狀防 s/ms 假綠。
- 輸入 / 輸出：RangeIndex + 秒級 timestamp 欄 fixture / 測試 pass。
- 實作要點：
  1. fixture `reset_index()` + `timestamp=[1704067200, ...]`（秒，**禁 ms 構造、禁 DatetimeIndex index**）放 `tests/fixtures/ic_phase0/`。
  2. TDD：僅加測試 commit 重現 `AttributeError: 'Series' object has no attribute 'to_series'`。
  3. 修 2.1 後斷言 by_year 鍵==2024。
- 修改檔案：`tests/fixtures/ic_phase0/` + `tests/momentum/test_ic_timeaxis.py`。既有 caller：N/A。
- 不可做：不用 DatetimeIndex/ms fixture。
- 邊界：跨年資料 → 多正確年份鍵；空 raw_data → None 不崩。
- 風險緩解：防假綠（保真度鐵律：fixture 須 byte-faithful）。
- **Golden owner（grouped）`[M-5]`**：修 C+T 後凍結 `tests/fixtures/ic_phase0/baseline_grouped_post_timeaxis.json`（per-group IC mean + 每 group row index mask hash + group sizes）；於 `tests/momentum/test_ic_phase0_golden.py` 用參考實作 `pd.to_datetime(timestamp, unit='s').year` 獨立 groupby + `np.isclose(atol=1e-6,rtol=1e-4)` 比對。
- 驗證：`pytest tests/momentum/test_ic_timeaxis.py` 僅加測試紅 → 修 2.1 綠，by_year==2024；`pytest tests/momentum/test_ic_phase0_golden.py::test_grouped_baseline` 比對 mask hash + IC mean 不 FAIL。

### Task 2.3 — IC-BYVOL fail-closed（收斂：(b) + 預設 False）`[B-1]` `[B-2]`
- SPEC ref：Task 2.3。目標：by_volatility 不靜默忽略；fail-closed + 預設不再觸發。
- 輸入 / 輸出：`GroupedConfig.by_volatility` / 預設 False、顯式 True 則 raise。
- 實作要點：
  1. `ic_config_schema.py:80`：`by_volatility: bool = True` → `False`（+ 註解 migration：既有預設 grouped 不再因此 raise）。
  2. `compute_grouped_ic`（ic_engine.py:383-400 後）：`if config.get("by_volatility"): raise NotImplementedError("by_volatility grouped 於 Phase 0 不支援，留待後 Phase")`。
  3. 確認 by_year/by_quarter/by_regime 仍正常。
- 修改檔案：`momentum/Analysis/ic_config_schema.py`、`ic_engine.py:compute_grouped_ic`。既有 caller：orchestrator（經 model_dump）。
- 不可做：不靜默 pass、不假裝實作分組、不保留預設 True。
- 邊界：by_volatility=False（新預設）→ 不觸發、grouped 正常；顯式 True → raise 訊息含「not supported」。
- 風險緩解：契約正確性。
- 驗證：`pytest` (i) 預設 config grouped 不 raise 且有 by_year/by_regime；(ii) 顯式 True → `pytest.raises(NotImplementedError)` 訊息含 "not supported"。

> **派工 prompt B2**：「修 IC-TIMEAXIS + IC-BYVOL。讀 SPEC Task 2.1-2.3。`_get_time_index` 回 DatetimeIndex+單位實測+fail-closed；by_volatility 預設改 False + 顯式 True raise NotImplementedError；TDD fixture 用 RangeIndex+秒級 timestamp。跑 `pytest tests/momentum/ -q`。STATUS: DONE/BLOCKED。」

---

## Phase 3 — feature_filter 落地（完成後：篩選顯式真生效、預設全量、metadata 可審計）

### Task 3.1 — ICConfig 加 feature_filter 欄（修靜默丟棄）`[F-1]`
- SPEC ref：Task 3.1。目標：momentum 承接欄位 + config_override 不丟棄。
- 輸入 / 輸出：API `FeatureFilterConfig` → `ICConfig.feature_filter`。
- 實作要點：
  1. `ic_config_schema.py` 加 `feature_filter: Optional[FeatureFilterSchema] = None`，**FeatureFilterSchema 7 欄 1:1 對應 API `FeatureFilterConfig`（ic_models.py:8-15）**：`include_features: Optional[List[str]]`、`exclude_features: Optional[List[str]]`、`include_pattern: Optional[str]`、`include_categories: Optional[List[str]]`、`include_data_sources: Optional[List[str]]`、`include_families: Optional[List[str]]`、`max_features: Optional[int]`（禁用簡寫欄名）。
  2. 確認 override 套用路徑 `_apply_config_override`→`ICConfig.model_validate`（orchestrator:~1717）後 `feature_filter` 不被丟棄（現況親驗 ICConfig 無此頂層欄 → `has feature_filter False`）。
- 修改檔案：`momentum/Analysis/ic_config_schema.py`（ICConfig + 新 schema）；`load_ic_config` override 套用處。既有 caller：service `_build_config_override`。
- 不可做：不改其他既有 config 欄語義。
- 邊界：None → feature_filter is None 向後相容；部分欄位 → 其餘 None。
- 風險緩解：(b) 跨模組——確保端到端不丟。
- 驗證：`pytest` `load_ic_config({'feature_filter':{'max_features':30}})` 後 `config.feature_filter is not None` 且值相等（**現況紅 → 轉綠**）。

### Task 3.2 — orchestrator 真消費 + 穩定排序（預設不截斷）`[F-2]` `[F-3]`
- SPEC ref：Task 3.2。目標：篩選僅顯式生效、預設全量、排序穩定。
- 輸入 / 輸出：features_df + feature_filter / 篩後 features_df + 排序確定。
- 實作要點：
  1. orchestrator features_df 載入後、IC 計算前 `_apply_feature_filter`：用**精確欄名**——`include_features`/`exclude_features` 直接對 column name；`include_pattern` regex 對 column name；`include_categories`/`include_data_sources`/`include_families` 對 metadata 的 category/data_source/family 映射篩 columns。
  2. max_features 截斷：`selected = sorted(remaining_columns)[:max_features]`（穩定可移植；**禁** HDF5 欄序、**禁** label 衍生 IC 排序 look-ahead）。
  3. 前端 `icAnalysisStore.ts:187` 預設 `max_features` 改 `undefined`；後端僅在顯式套用才截斷。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（features 載入後新 helper `_apply_feature_filter`）；`frontend/src/store/icAnalysisStore.ts`。既有 caller：orchestrator 主流程。
- 不可做：不靜默截斷、不用不穩定/look-ahead 排序、不預設截斷。
- 邊界：無顯式 filter → 全量；篩後=0 → 明確 error 不靜默；max_features>總數 → 全留不報錯。
- 風險緩解：(d) feature universe 語義——穩定+可審計+非預設。
- 驗證：`pytest` (i) 無 filter → 全量（不截斷）；(ii) pytest factory 造 `n=45000` 具名欄 DataFrame，max_features=30 → 算 30 個 `sorted` 子集，兩次跑欄名集合 sha256 相同。

### Task 3.3 — metadata 審計（truncation_mode）+ 大 run 警示 `[F-4]` `[F-5]`
- SPEC ref：Task 3.3。目標：可審計、不靜默。
- 輸入 / 輸出：篩選結果 / metadata 計數欄。
- 實作要點：
  1. metadata 記 `feature_count_original`/`feature_count_filtered`/`feature_filter_applied`/`truncation_mode`/`truncation_order("sorted_column_name")`。
  2. **truncation_mode 判定（寫死）**：`"preview"` 僅當 `max_features` 顯式設定且實際生效（filtered<original 因 max_features）；其餘篩選（include/exclude/pattern/categories…無 max_features 截斷）→ `"none"` 且 `feature_filter_applied=True`；完全無 filter → `"none"`、applied=False。
  3. 總特徵 > `5000`（寫死）→ `logger.warning` 一行（僅警示不阻擋）。
- 修改檔案：`ic_filter_orchestrator.py`（metadata 組裝處 + `_apply_feature_filter` 回傳計數）。既有 caller：主流程。
- 不可做：不靜默截斷不記錄、不阻擋大 run（只警示）。
- 邊界：無篩選 → original==filtered、applied=False、truncation_mode=none；篩後 0 → 記錄後 error。
- 風險緩解：可審計性。
- 驗證：`pytest` (i) 顯式 max_features 生效 → `truncation_mode=="preview"`；(ii) 只 include_categories 篩 → `truncation_mode=="none"` 且 `feature_filter_applied==True`；(iii) 無 filter → applied==False；各斷言四欄存在且 `filtered<=original`。

### Task 3.4 — preview_limit（確認幽靈欄→併入 F-3）`[F-6]`
- SPEC ref：Task 3.4。目標：澄清範圍，移出實作。
- 輸入 / 輸出：N/A（無欄位）。
- 實作要點：
  1. `grep -rn preview_limit api/ momentum/ frontend/src` → 確認 0（Claude 親驗不存在）。
  2. 預覽 vs 正式語義改由 F-3 `metadata.truncation_mode` 表達，**不新建 alias/schema**。
- 修改檔案：無。既有 caller：N/A。
- 不可做：不為幽靈欄新建 alias/版本化/TS 型別。
- 邊界：N/A。
- 風險緩解：防過度工程（避免亂改 unrelated API）。
- 驗證：`grep -rn preview_limit api/ momentum/ frontend/src` 結果 0 行。

### Task 3.5 — feature_filter 回歸測試 `[F-7]`
- SPEC ref：Task 3.5。目標：端到端篩選真生效驗證。
- 輸入 / 輸出：真 features + filter / 測試 pass。
- 實作要點：
  1. 測試：送 max_features=N → 斷言實際算的 feature 數==N（非全量）。
  2. metadata 計數前後正確。
- 修改檔案：`tests/momentum/test_ic_feature_filter.py`（新增）。既有 caller：N/A。
- 不可做：不放寬 assert 換綠。
- 邊界：filter=None → 全量；filter 篩後 0 → error 測試。
- 風險緩解：防假綠。
- **Golden owner（feature_filter）`[M-5]`**：凍結 `tests/fixtures/ic_phase0/baseline_feature_filter.json`（篩後欄名集合 sha256 + 計數）；`tests/momentum/test_ic_phase0_golden.py::test_feature_filter_baseline` 比對確定性。
- 驗證：`pytest tests/momentum/test_ic_feature_filter.py` 斷言篩後數==N、metadata 正確；`test_ic_phase0_golden.py::test_feature_filter_baseline` sha256 不變。

> **派工 prompt B3**：「落地 feature_filter。讀 SPEC Task 3.1-3.5。ICConfig 加欄修丟棄；orchestrator `_apply_feature_filter` 預設不截斷+`sorted()` 排序；前端預設 max_features undefined；metadata truncation_mode；preview_limit 確認幽靈不做。跑 `pytest tests/momentum/ tests/api/ -q` + `npm run build`。STATUS: DONE/BLOCKED。」

---

## Phase 4 — 效能/體感（完成後：熱迴圈零 log、event loop 不阻塞、前端真錯誤）

### Task 4.1 — IC-DECAY-LOG 聚合 `[D-1]` `[D-2]`
- SPEC ref：Task 4.1。目標：熱迴圈零 log，結尾一行，數值不變。
- 輸入 / 輸出：decay 逐特徵 fit / 聚合摘要 log。
- 實作要點：
  1. `_fit_exponential_decay` 移除**熱迴圈內全部 4 處** `logger.warning`：:904 insufficient_points、:918 low_variance、:944 low_r2、:958 fit_exception（**保留回傳 dict 的 r2/fit_warning_reason 不變**，僅移 log）。
  2. `compute_ic_decay`（:331）迴圈收集各 feature 的 fit_warning_reason，結尾 `logger.info("Decay: %d/%d 特徵 fit 異常 (insufficient/low_var/low_r2/exception 計數) ...", n_warn, total)` 一行（唯一允許的 log）。
  3. 不改 decay 數值/不做 R2 early-skip。
- 修改檔案：`ic_engine.py:_fit_exponential_decay`、`compute_ic_decay`。既有 caller：orchestrator decay 分支。
- 不可做：不改 decay 回傳數值、不 early-skip。
- 邊界：全 fit 成功 → 摘要顯示 0 低品質；features=0 → 不崩。
- 風險緩解：(d) Golden D 防數值漂移。
- **Golden owner（decay）`[M-5]`**：凍結 `tests/fixtures/ic_phase0/baseline_decay.json`；`tests/momentum/test_ic_phase0_golden.py::test_decay_baseline` 結構化 float 比對。
- 驗證：Test 4.2 + Golden D；`pytest test_ic_phase0_golden.py::test_decay_baseline` 回傳 dict 逐 feature 結構化 float 比對不變（鍵集合 exact + `np.isclose(atol=1e-6,rtol=1e-4)` + NaN-mask exact；**禁 json byte compare**）。

### Task 4.2 — IC-DECAY-LOG 回歸測試 `[D-3]`
- SPEC ref：Task 4.2。目標：證熱迴圈零 warning + 一行摘要。
- 輸入 / 輸出：多特徵 decay / caplog 斷言。
- 實作要點：
  1. `pytest` caplog 跑多特徵 decay，`assert` per-feature warning 數==0。
  2. `assert` 結尾摘要恰一行。
- 修改檔案：`tests/momentum/test_ic_decay_log.py`（新增）。既有 caller：N/A。
- 不可做：不放寬斷言。
- 邊界：features=0 → 無摘要不崩；全低品質 → 摘要計數正確。
- 風險緩解：防假綠。
- 驗證：`pytest tests/momentum/test_ic_decay_log.py` caplog per-feature warning==0 + 一行摘要。

### Task 4.3 — IC-UX-ERR 後端 to_thread（兩條主路徑）`[U-1]`
- SPEC ref：Task 4.3。目標：解 event loop 阻塞。
- 輸入 / 輸出：同步 analyze / `await asyncio.to_thread` 包裹。
- 實作要點：
  1. `ic_analysis_service.py` longitudinal `analyze`（:209-216）改 `await asyncio.to_thread(analyzer.analyze, ...)`。
  2. cross-sectional `analyze_cross_sectional`（:154-159）同改（codex 揪兩條都同步）。
  3. 先讀碼確認對應點與參數簽名。
- 修改檔案：`api/services/ic_analysis_service.py`（兩處）。既有 caller：WS handler。
- 不可做：不改 analyze 內部邏輯、不吞錯誤。
- 邊界：analyze 拋錯 → 錯誤經 WS 傳遞非吞掉；空結果 → 正常回。
- 風險緩解：體感/錯誤傳遞。
- 驗證：`pytest tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop`（longitudinal + cross_sectional 各一）：patch `analyzer.analyze` sleep 2s，`asyncio.wait_for(gather(sleep×N, start_task), timeout<2)` 須 pass；改動前同測試確認紅。

### Task 4.4 — IC-UX-ERR 前端錯誤處理 + poll 狀態機 `[U-2]` `[U-3]` `[U-4]` `[U-5]`
- SPEC ref：Task 4.4。目標：真錯誤 + 有限重連 + poll fallback。
- 輸入 / 輸出：WS 事件 / 正確錯誤態 + poll。
- 實作要點：
  1. **WS failed 讀對欄位**：onmessage 補 `data.status==='failed'` 分支 → `setError(data.message ?? data.error)`（WS payload 用 **`message`** 欄，service:246-251，非 `error`）。
  2. **poll failed**：`fetchTaskStatus` 回 `status==='failed'` → `setError(response.error)`（poll endpoint 的 ICTaskStatusResponse 才有 `error` 欄）；`fetchTaskStatus` response TS type 補 `error?: string | null`。
  3. **poll 狀態機偽碼**：`retryCountRef`（onclose retry≤3）；超過 → `pollIntervalMs=2000` setInterval poll `/task/{id}`；terminal（completed/failed）→ `clearInterval` + close ws + `fetchResult`/`setError`；不與 WS 雙寫。
  4. **區分 transport vs backend failed**：onerror（:106-108）僅在無 terminal status 時顯示泛用訊息，不蓋掉後端真錯誤；onclose（:110-118）停無限重連。
- 修改檔案：`frontend/src/hooks/useICAnalysis.ts`（onmessage/onerror/onclose + fetchTaskStatus type）、`frontend/src/store/icAnalysisStore.ts`。既有 caller：ic-analysis page。
- 不可做：不無限重連、不雙寫狀態、不吞真錯誤。
- 邊界：後端送 error payload → 顯示真訊息；連續斷線 → retry 3 次後 poll，非無限轉圈；poll 到 terminal → 停。
- 風險緩解：體感正確性。
- 驗證：`vitest` + `npm run build` PASS；`expect` setError 帶 `data.message`（WS failed）/`response.error`（poll failed）各一斷言；模擬 WS 斷 → poll 接管到 terminal。

> **派工 prompt B4**：「修 decay log + UX。讀 SPEC Task 4.1-4.4。decay 移熱迴圈 warning + 結尾聚合(數值不變,Golden D 結構化比對)；後端兩條 analyze 改 to_thread；前端 failed setError 真訊息 + retry≤3 + poll fallback 狀態機。跑 `pytest tests/momentum/ tests/api/ -q` + `vitest` + `npm run build`。STATUS: DONE/BLOCKED。」

---

## Phase 測試 + Gate
- **單元**：_get_time_index 單位/型別、decay 聚合、feature_filter 排序、by_volatility raise。
- **邊界**：空 DF / 全 NaN / std=0 / 異常 timestamp(1970/2100/1e16) / 45k 篩選 / WS 斷線。
- **Golden** `[M-5]`：集中於 `tests/momentum/test_ic_phase0_golden.py`，三 owner Task 各凍 baseline——`test_grouped_baseline`(Task 2.2：per-group IC mean + row mask hash + group sizes，參考實作 `pd.to_datetime(ts,unit='s').year` 獨立 groupby + np.isclose)、`test_decay_baseline`(Task 4.2：結構化 float)、`test_feature_filter_baseline`(Task 3.5：sha256 確定性)。baseline 存 `tests/fixtures/ic_phase0/baseline_{grouped_post_timeaxis,decay,feature_filter}.json`。
- **Phase Gate**：每 Batch 跑 `pytest tests/momentum/ tests/api/ -q` 全綠 + `pytest tests/momentum/test_ic_phase0_golden.py` 不 FAIL + 前端 `npm run build`/`vitest`（B3/B4）。

## Frozen handoff
`SPEC=docs/IC_PHASE0_SPEC.md TODO=docs/IC_PHASE0_TODO.md FOCUS=完整審查`
（SPEC + TODO 皆已過雙家族 adversarial：SPEC reconcile=`...ADVERSARIAL-RECONCILE.md`、TODO reconcile-2=`...TODO-ADVERSARIAL-RECONCILE.md`，BLOCKING 全修補。Frozen。）
