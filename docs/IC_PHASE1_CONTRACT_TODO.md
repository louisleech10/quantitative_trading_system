# IC Phase 1 1-contract TODO （v2｜納 TODO 雙家族 adversarial｜2026-06-26）

> 冷啟動可執行：執行端不需回讀 SPEC 即可逐 Task 開寫。覆蓋 [C-1..C-12] + R1-R9 + TODO-adversarial T1-T7+單家項。
> 來源：docs/IC_PHASE1_CONTRACT_SPEC.md v2；reconcile：handoffs/20260626-ic-PHASE1-CONTRACT-TODO-ADVERSARIAL-RECONCILE.md。
> 狀態：Frozen（SPEC+TODO 皆過雙家族 adversarial 並 reconcile）。

## §0 全域規則與約束（讀完即可遵守）
- **解耦 7 條**：`momentum/` 不得 `from api.`（`grep -rE "from api\." momentum/`→0；含 `from api.models`/`api.core` 皆禁）；引擎 DTO 放 `momentum/core/contracts.py`、API DTO 放 `api/models/ic_models.py`，兩側不互 import。服務經 `momentum/factories.py`。
- **Logging（修 codex MINOR：勿誘導反向 import）**：**momentum 層一律用 `from momentum.core.logging import get_logger`**（**禁** `from api.core.logging`，那會違反 Rule 1）；`contracts.py` 契約層優先不 log；API 層才用 `api.core.logging`。
- **命名/型別**：函式 type hints；docstring 繁中；不可變契約用 `@dataclass(frozen=True)`。
- **不可違反原則**：跨 tier(8-32GB) 可重複穩定、多 symbol 不 OOM、資料品質（不假資料/不跨 symbol 污染/**不靜默接受 CPCV embargo 降級**）、不弱化 NaN/inf gate、**不擅改既有輸出數值/JSON 形狀**（flag off 必 byte 不變）。
- **防假綠**：不得放寬/刪除既有斷言換綠燈；[C-3] 反例必 `pytest.raises` 不得降 warning；**禁引用既有 30 synthetic ML 測試代替 [C-3] 真實 kline 測試**。
- **真實資料**：資料正確性測試一律用 `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture。
- **artifact 格式 = Parquet**（pyarrow；非 HDF5）。
- **已知技術債（執行端須知，非 bug）**：`SplitPlan.purge_semantic` 預設 `"rows"`，**1a 才改 timedelta**；Phase 1 不改 purge 數學，靠 **Task 1.3 的 `expected_freq` gap 偵測 fail-closed** 擋住「rows-purge 遇 gap 的時間洩漏」。執行端不得自行把 purge 改成 timedelta（超範圍）。
- **G1 deep-equal 正規化（B0 實測：v1 payload 含動態欄）**：baseline `baseline_btc_1h.json` 含 `generated_at`（每次跑都變）。所有 G1 deep-equal 比對（Task 2.2/3.2）**必須先剔除動態欄 `generated_at`**（白名單比對：除 `generated_at` 外全鍵 deep-equal）；**不得**為了過測把整個 deep-equal 放寬成只比 top keys（防假綠）。動態欄清單寫死在測試 helper `_strip_dynamic(payload)={k:v for k,v in p.items() if k!="generated_at"}`。

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0 baseline freeze** | 0.1 凍結 v1 Golden baseline（**任何改碼前**） | 無 | T1：baseline 必須在改碼前凍結,否則「改後==改後」假綠 | 小 |
| **B1 契約 DTO** | 1.1 SplitPlan, 1.2 RowMaskPlan, 2.1 SelectionScope, 2.3 AlignmentSpec | B0 | 純新增 dataclass（**不含 2.2,2.2 改既有 ICResult+序列化故獨立**） | 中 |
| **B2 eval_status（含序列化）** | 2.2 EvaluationStatus + ICResult.eval_status + filter_evaluated + **_to_json_compatible 排除** | B1 | T2：加欄+v1 序列化排除+真實 get_result regression 必同批,否則 asdict 洩漏 | 中 |
| **B3 洩漏紅線+adapter** | 1.3 validate_split_integrity, 1.4 ic_split_adapter+strict embargo | B1 | (d) 紅線核心 | 大 |
| **B4 artifact(Parquet)** | 3.1 ICArtifactSchema + build_ic_artifact_rows + ic_artifact_writer | B1(scope) | writer 依 schema；獨立 IO | 中 |
| **B5 API 版本化** | 3.2 ICResultV2Response + config flag + **route Query** + get_result 分支 + subroute regression | B2,B4 | T3/T6：route+子端點回歸必同批 | 中 |
| **B6 Golden+測試集** | 4.1 G2/G3 + 解耦校驗 + [C-11] 雙向 grep | B1-B5 | G1 已在 B0；此處補 G2/G3 | 中 |

- **批次間 Gate**：每批跑該批 Test ID 全 PASS + `grep -rE "from api\." momentum/`==0 才進下批。B2/B5 Gate **必含 G1 deep-equal（引用 B0 baseline）**。
- 派工 prompt 見各 Phase 末。

---

## Phase 0 — baseline freeze（B0；完成後：v1 Golden 凍結，後續改碼有對照）

### Task 0.1 — 凍結 v1 Golden baseline [T1][R7-G1]
- SPEC ref：§G G1　目標：改任何碼前，凍結 v1 IC 輸出當 byte-stability 對照。
- 輸入：無　輸出：`tests/golden/ic_phase1_contract/baseline_btc_1h.json` + `baseline_meta.json`（含 config_hash/命令/sha256）。
- 實作要點：
  1. **寫死 reference run**：symbol=`BTCUSDT`, timeframe=`1h`, mode=`longitudinal`, **config_hash=`a384e6d22ca15fc639757cb3162e7cb3`**（registry 實查：90857 features/20352 rows；非 pytest 暫存）。
  2. 跑現有 IC longitudinal 主流程（`IcAnalysisService` 現行路徑）取 `get_result(task_id)` 之 v1 dict，存 `baseline_btc_1h.json`。
  3. 記錄生成命令 + 輸出 sha256 到 `baseline_meta.json`（可重現）。
- 修改檔案：新增 `tests/golden/ic_phase1_contract/`（資料+meta）；可加 `tests/golden/ic_phase1_contract/freeze_baseline.py` 腳本。既有 caller：無。
- 不可做：不得改任何 momentum/api 程式碼（純凍結）；不得用合成資料。
- 邊界：該 run 不存在→`STATUS: BLOCKED`（不可換 run 假裝）；run 已被改動污染→BLOCKED。
- 風險緩解：T1。
- 驗證：`baseline_btc_1h.json` 存在且非空；`baseline_meta.json` 含 config_hash==`a384e6d2...` 與 sha256；`pytest tests/golden/ic_phase1_contract/test_baseline_frozen.py::test_baseline_exists`（`assert` 檔存在 + sha256 match meta）。

### Phase 0 Gate
- baseline 檔 + meta 存在，sha256 記錄。無此 baseline 不得進 B1。

---

## Phase 1 — 契約 DTO（B1）

### Task 1.1 — SplitPlan [C-1][R9]
- SPEC ref：§P Task 1.1　目標：train/val/test 列歸屬 canonical timestamp-based 表示。
- 輸入：無　輸出：`momentum/core/contracts.py::SplitPlan`（frozen）。
- 實作要點：
  1. 欄位 `split_label: Literal["train","val","test"]`、`index_kind: Literal["timestamp","positional","row_id"]`、`row_index: np.ndarray`、`time_bounds: tuple`、`purge_gap: int`、`embargo: int`、`purge_semantic: Literal["rows","timedelta"]="rows"`、`expected_freq: Optional[str]`、`base_universe_hash: str`、`symbol: Optional[str]=None`。
  2. `__post_init__`：`base_universe_hash` 空→raise ValueError；`index_kind` 非法→raise；`purge_gap>=len(row_index)` 且 row_index 非空→raise。
- 修改檔案：`momentum/core/contracts.py`（檔尾新增）。既有 caller：無。
- 不可做：不實作切分執行（1a）；不接既有路徑；不改 purge 語義為 timedelta（債，留 1a）。
- 邊界：空 row_index→建構成功標 empty；purge_gap>=區段長→raise。
- 風險緩解：R9。
- 驗證：`pytest tests/momentum/core/test_split_contract.py::test_splitplan_fields`；`test_splitplan_requires_base_universe_hash`（`pytest.raises(ValueError)`）。

### Task 1.2 — RowMaskPlan [C-2][R9]
- SPEC ref：§P Task 1.2　目標：canonical row identity 列遮罩。
- 輸入：無　輸出：`contracts.py::RowMaskPlan`。
- 實作要點：欄位 `row_index/index_kind/source: Literal["split","event","feature_filter","full"]/base_universe_hash/length/symbol`；`@property n_selected`；`to_mask(base_len)`/classmethod `from_mask(mask,**meta)`；禁無 discriminator union。
- 修改檔案：`momentum/core/contracts.py`。既有 caller：無。
- 不可做：不接現有計算路徑。
- 邊界：全 False→n_selected==0；length!=base_len→to_mask raise；缺 index_kind→raise。
- 風險緩解：R9。
- 驗證：`pytest tests/momentum/core/test_rowmask_contract.py::test_rowmask_roundtrip`（`assert (RowMaskPlan.from_mask(p.to_mask(n)).row_index==idx).all()`）；`test_rowmask_requires_index_kind`（`pytest.raises`）。

### Task 2.1 — SelectionScope [C-5]
- SPEC ref：§P Task 2.1　目標：FDR/顯著性 universe×split×evaluated + scope id。
- 輸入：無　輸出：`contracts.py::SelectionScope`。
- 實作要點：欄位 `scope_id/universe_features/split_label/evaluated_features/n_tests/method/base_universe_hash`；`__post_init__` evaluated⊄universe→raise。
- 修改檔案：`momentum/core/contracts.py`。既有 caller：無。
- 不可做：不實作 FDR（1b）。
- 邊界：evaluated 空→n_tests==0；evaluated 含 universe 外→raise。
- 風險緩解：R-codex8。
- 驗證：`pytest tests/momentum/core/test_scope_contract.py::test_selection_scope_fields`；`test_scope_n_tests_matches_evaluated`（`assert scope.n_tests==len(scope.evaluated_features)`）。

### Task 2.3 — AlignmentSpec [C-7]
- SPEC ref：§P Task 2.3　目標：前瞻偏誤對齊契約欄位（給 1-align），僅簽名。
- 輸入：無　輸出：`contracts.py::AlignmentSpec` + `validate_alignment()` 簽名。
- 實作要點：`@dataclass AlignmentSpec(feature_ts_col,target_ts_col,lag:int,freq:str)`；`__post_init__` lag<0/freq 非法 raise；`validate_alignment(...): raise NotImplementedError("1-align 落地")`。
- 修改檔案：`momentum/core/contracts.py`。既有 caller：無。
- 不可做：不實作對齊偵測（1-align）。
- 邊界：lag<0→raise；freq 非法→raise。
- 風險緩解：⊘。
- 驗證：`pytest tests/momentum/core/test_alignment_contract.py::test_alignment_spec_fields`；`test_validate_alignment_signature`（`assert callable` + `pytest.raises(NotImplementedError)`）。

### Phase 1 Gate
- `pytest tests/momentum/core/test_split_contract.py tests/momentum/core/test_rowmask_contract.py tests/momentum/core/test_scope_contract.py tests/momentum/core/test_alignment_contract.py` 全 PASS + `grep -rE "from api\." momentum/`==0。

---

## Phase 2 — eval_status（含序列化排除）（B2）

### Task 2.2 — eval_status 語義 + v1 序列化排除 [C-6][T2][R-codex9]（(a)）
- SPEC ref：§P Task 2.2　目標：已評估/未評估/legacy 邊界；未評估不混入排序/FDR；**且 flag-off v1 JSON 不洩漏新欄**。
- 輸入：無　輸出：`contracts.py::EvaluationStatus`(Enum) + `ICResult.eval_status` + `filter_evaluated()` + `ic_analysis_service.py::_to_json_compatible` 排除邏輯。
- 實作要點：
  1. `class EvaluationStatus(str,Enum): EVALUATED/NOT_EVALUATED/SKIPPED/UNKNOWN_LEGACY`。
  2. `ICResult` 加 `eval_status: EvaluationStatus = EvaluationStatus.UNKNOWN_LEGACY`（預設 legacy 防掩蓋）。
  3. `filter_evaluated(results)`：`return [r for r in results if r.eval_status==EVALUATED]`。
  4. **T2 關鍵**：`_to_json_compatible`（`ic_analysis_service.py:1098 asdict`）對 `ICResult` dataclass 會自動帶出 `eval_status`。改法：在 v1 序列化路徑**剔除 `eval_status` 鍵**（`ic_response_v2=False` 時），確保 v1 payload 鍵集合不變。
- 修改檔案：`momentum/core/contracts.py`（ICResult L283+Enum+helper）；`api/services/ic_analysis_service.py::_to_json_compatible`（L1098 附近，flag-off 剔 eval_status）。既有 caller：`_to_json_compatible` 全 result 序列化路徑。
- 不可做：Phase 1 不產 NOT_EVALUATED（全評估）；不改 v2 以外行為。
- 邊界：全非 EVALUATED→filter 回空+warning（不 raise）；既有 ICResult 反序列化→UNKNOWN_LEGACY；flag off→JSON 無 eval_status 鍵。
- 風險緩解：T2。
- 驗證：`pytest tests/momentum/core/test_eval_status.py::test_only_explicit_evaluated_ranked`（混 4 狀態→`assert len(filter_evaluated)`==只 EVALUATED 數）；`test_legacy_not_counted`；**`tests/api/test_ic_response_v2.py::test_flag_off_get_result_no_eval_status_key`（真實 get_result v1 payload 鍵集合 == B0 baseline 鍵集合，非只測 helper）**。

### Phase 2 Gate
- 上述測試 PASS + **G1 deep-equal（flag off `/result` == B0 baseline）** + `grep -rE "from api\." momentum/`==0。

---

## Phase 3 — 洩漏紅線 + adapter（B3）

### Task 1.3 — 時間連續性洩漏紅線 [C-3][R1][T-cursorF8]（(d)）
- SPEC ref：§P Task 1.3　目標：強制 split per-symbol + 單 symbol 內時間連續，違反 fail-closed。
- 輸入：SplitPlan、ts、symbols　輸出：`contracts.py::validate_split_integrity` + `CrossSymbolLeakageError` + `TimestampDiscontinuityError` + `split_per_symbol` helper。
- 實作要點：
  1. 兩 Exception class。
  2. `validate_split_integrity(plan, ts, symbols)`：
     - **強化多 symbol 條件（codex B5）**：`plan.symbol is not None` 且 `np.unique(symbols[plan.row_index])` 必 =={plan.symbol}；否則（含「已 sorted/grouped 但整 frame 多 symbol」）→`raise CrossSymbolLeakageError`。
     - 單 symbol 內 `np.diff(ts_sorted)<=0` 任一（非單調/重複）→`raise TimestampDiscontinuityError`。
     - **gap 偵測（cursor F8 寫死）**：`if plan.purge_semantic=="rows" and expected_freq is not None: gap = np.max(np.diff(ts)) > pd.Timedelta(expected_freq)*(1+ATOL)`（`ATOL=0.05`）→ `raise TimestampDiscontinuityError`（rows-purge 遇 gap）。
  3. `split_per_symbol(data, splitter, symbol_col, ts_col)`：逐 symbol group 呼叫 splitter，每組產 `SplitPlan(symbol=sym,...)`；purge 不跨界。
- 修改檔案：`momentum/core/contracts.py`。既有 caller：無（adapter 1.4 呼叫）。
- 不可做：不重寫 purge/embargo 數學。
- 邊界：單 symbol 連續→正常；symbol 欄缺→raise；expected_freq=None（允許 gap）→須 purge_semantic=="timedelta" 否則 raise；多 symbol 整 frame→raise（強化條件）。
- 風險緩解：R1+T-cursorF8。
- 驗證：`pytest tests/momentum/core/test_split_contract.py::test_cross_symbol_purge_blocked`（BTC 尾接 ETH 頭未 per-symbol→`pytest.raises(CrossSymbolLeakageError)`）；`test_sorted_grouped_but_multi_symbol_blocked`（已排序但整 frame 多 symbol→`pytest.raises(CrossSymbolLeakageError)`，codex B5）；`test_single_symbol_gap_blocked`（kline BTC/1h 刪 3 bar→`pytest.raises(TimestampDiscontinuityError)`）；`test_unsorted_dup_ts_blocked`。**真實 kline。**

### Task 1.4 — ML 孤島 adapter + embargo 弱化偵測 [C-4][R1][R3][T4][T-cursorF0-1]
- SPEC ref：§P Task 1.4　目標：SplitPlan 由既有切分轉換 + 偵測 CPCV silent relaxation。
- 輸入：cpcv/wf 實例 + 含 symbol+ts 真實資料　輸出：`momentum/Analysis/ic_split_adapter.py::ICSplitAdapter` + `factories.py::create_ic_split_adapter` + `EmbargoRelaxedError`。
- 實作要點：
  1. **CPCV path**：逐 symbol `cpcv.split(X_sym,y_sym)`→`(train_idx,test_idx)` int 陣列→`SplitPlan`（轉 timestamp、`base_universe_hash=hash(frame)`）；套 `validate_split_integrity`。
  2. **WF path（cursor F0-1：WF 回區間 tuple 非 idx 陣列）**：`WalkForwardValidator._generate_rolling_splits(n_samples,train_size,test_size,step)` 回 `List[((train_s,train_e),(test_s,test_e))]`（`walk_forward_validator.py:256-273` 實查）。adapter 內 `_iter_wf_splits()`：對每 fold `train_idx=np.arange(train_s,train_e); test_idx=np.arange(test_s,test_e)` 展開→ SplitPlan。**embargo 來源**：`WalkForwardConfig.embargo_pct`（轉 rows）。**只讀 `_generate_rolling_splits`，不改 wf 檔。**
  3. **strict embargo 偵測（T4 寫死演算法）**：對每 test range，用**原始 requested config** 重算 expected excluded interval `[start-purge_gap, end+purge_gap+requested_embargo_len)`（`requested_embargo_len=int(n_samples*embargo_pct)`）；`assert returned train_indices == expected_train_set`（完全一致）。若 CPCV 觸發 `combinatorial_purged_cv.py:75-79` 的 `/2` 降級導致 returned train ⊋ expected → `raise EmbargoRelaxedError(f"embargo {requested}->{effective}")`。**分別檢查 pre-test purge 與 post-test embargo,不用單一 nearest-boundary。**
- 修改檔案：新 `momentum/Analysis/ic_split_adapter.py`；`momentum/factories.py` 加 `create_ic_split_adapter()`。既有 caller：無。
- 不可做：不改 `walk_forward_validator.py`/`combinatorial_purged_cv.py` 內部。
- 邊界：validator raise（樣本不足）→回 `SkippedResult(reason=INSUFFICIENT_DATA)` 不吞；空 symbol list→raise。
- 風險緩解：R1+R3+T4+T-cursorF0-1。
- 驗證：`pytest tests/momentum/Analysis/test_ic_split_adapter.py::test_adapter_wraps_cpcv`（真實 kline 多 symbol→SplitPlan list，各過 [C-3]，與直接 split() per-symbol `np.array_equal`）；**`test_adapter_wraps_wf`（WF 區間正確展開,與 `_generate_rolling_splits` `np.array_equal`，獨立於 CPCV）**；`test_adapter_detects_embargo_relaxation`（小樣本觸 CPCV /2 降級→`pytest.raises(EmbargoRelaxedError)`）。

### Phase 3 Gate
- `pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py` 全 PASS + `grep -rE "from api\." momentum/`==0。

---

## Phase 4 — artifact（Parquet）（B4）

### Task 3.1 — Artifact schema+mapping+writer [C-8][R4][R8][T5][T7]（(a)）
- SPEC ref：§P Task 3.1　目標：全因子完整指標表落 Parquet，不載全表即可篩。
- 輸入：IC results　輸出：`contracts.py::ICArtifactSchema` + `momentum/Analysis/ic_artifact_writer.py::{build_ic_artifact_rows,write,read}`。
- 實作要點：
  1. `ICArtifactSchema`（long layout，明確欄位）：`feature_name:str, horizon:int, ic_mean:f64, ic_std:f64, icir:f64, p_value:f64, ic_hit_rate:f64, eval_status:str, selection_scope_id:str, schema_version:int`。
  2. **horizon 映射（T7）**：`build_ic_artifact_rows(results, default_horizon:int, selection_scope_id:str)`。**Phase 1 單 horizon**：現有 `ICResult` 無 horizon，寫死 `horizon=default_horizon`（來源=該 run 的 IC horizon 設定，由呼叫端傳入，非猜）；multi-horizon artifact §N 登記留後。
  3. `write(rows, path)`：pyarrow 寫 parquet，**atomic（temp + `os.replace`）**；schema_version 寫 file metadata。
  4. `read(path, filters=None, columns=None, page=None)`：pyarrow dataset + `filters`(predicate pushdown)，**不整表載入**（`iter_batches`/dataset filter）。
- **tier 表（T5 可證偽相對門檻，不靠硬數字 + psutil 非 tracemalloc）**：

  | tier | filter read peak RSS（`psutil.Process().memory_info().rss`） | page_size cap | 不變量 |
  |---|---|---|---|
  | 8GB | < 2GB（tier×0.25） | 5000 | **peak 不隨總 feature 數成長**（O(page) 非 O(total)）|
  | 16GB | < 4GB | 20000 | 同 |
  | 32GB | < 8GB | 50000 | 同 |
- 修改檔案：新 `momentum/Analysis/ic_artifact_writer.py`；`contracts.py` 加 ICArtifactSchema；`factories.py` 加 `create_ic_artifact_writer()`。既有 caller：無。**不接 task result path（保 R2/G1）。**
- 不可做：不刪舊 JSON；不接 task result path；不用 HDF5；不猜 horizon。
- 邊界：空結果→寫空表可讀；NaN/inf→保真；寫中斷→atomic 無孤兒。
- 風險緩解：R4+R8+T5+T7。
- 驗證：`pytest tests/momentum/Analysis/test_ic_artifact.py::test_artifact_roundtrip`（寫 N→讀回全 row value/NaN/inf/eval_status sha256 全等=G2）；`test_artifact_filter_no_full_load`（filter `len` 正確 + **`psutil` peak RSS < tier×0.25 + 用 2× feature 數重跑 peak 不變**，O(page) 不變量）；`test_artifact_atomic`（中斷無半檔）；`test_build_rows_single_horizon`（horizon==default 非猜）。**真實 IC 輸出。**

### Phase 4 Gate
- 上述 PASS + `grep -rE "from api\." momentum/`==0。

---

## Phase 5 — API 版本化（B5）

### Task 3.2 — API 版本化 + route negotiation + 子端點回歸 [C-9][C-10][R2][R5][R6][T3][T6]（(b)）
- SPEC ref：§P Task 3.2　目標：v2 response=top-N+artifact_uri（SSOT）；flag-off byte 不變；route 可達；子端點不破。
- 輸入：artifact(3.1)　輸出：`api/models/ic_models.py::ICResultV2Response` + `api/core/config.py::ic_response_v2` + `api/routes/ic_analysis.py::get_result` Query + `ic_analysis_service.py::get_result` 分支 + `ICArtifactQueryParams`。
- 實作要點：
  1. `ic_response_v2: bool=False`（`api/core/config.py` Settings）。
  2. **route（T3）**：`api/routes/ic_analysis.py::get_result` 改 `async def get_result(task_id:str, schema_version: Optional[int]=Query(None))`→傳入 `service.get_result(task_id, schema_version)`。
  3. service `get_result(task_id, schema_version=None)`：`if not settings.ic_response_v2 or schema_version!=2: return <v1 原樣,鍵集合不變>`；`else:` `ICResultV2Response(schema_version=2, top_n_summary=<artifact read 篩 top-N 衍生,SSOT>, artifact_uri=<path 或 None>, total_features=N)`。`top_n` 的 N=現有 `DeepAnalysisRequest.top_n` 預設 30。
  4. artifact 路徑 `…/{task_id}_{config_hash}_v2.parquet`（冪等）。
  5. `ICArtifactQueryParams`(sort_by:enum=icir|ic_mean|p_value, filter:白名單運算子, page_size:int(tier cap), cursor:Optional[str])——**僅 model，HTTP route 落 Phase 3 epic**（§N）。
- 修改檔案：`api/models/ic_models.py`、`api/core/config.py`、`api/routes/ic_analysis.py::get_result`、`api/services/ic_analysis_service.py::get_result`(L275)。既有 caller：route `/result` + decay/quantile/correlation/grouped/export（皆讀 get_result 子鍵）。
- 不可做：不改前端；不刪 v1；不實作 HTTP 篩選端點。
- 邊界：大 run→v2 不含全表（`assert` size）；無 artifact→artifact_uri=None+明確狀態；retry→路徑冪等。
- 風險緩解：R2+R5+R6+T3+T6。
- 驗證（route-level TestClient + 子端點 matrix，T6）：`pytest tests/api/test_ic_response_v2.py::test_flag_off_deep_equal_baseline`（off→`/result` == B0 baseline deep equal）；`test_route_v2_negotiation`（flag on+`?schema_version=2`→v2；flag on 無參→v1；flag off+`?schema_version=2`→v1 deep-equal）；`test_v2_top_n_derived_from_artifact`（SSOT）；**`test_flag_off_subroutes_unchanged`（decay/quantile/correlation/grouped/export 對 B0 task 回應 hash 不變）**；`test_no_artifact_uri_none`。

### Phase 5 Gate
- 上述 PASS + G1 deep-equal + 子端點 hash 不變 + `grep -rE "from api\." momentum/`==0。

---

## Phase 6 — Golden G2/G3 + 解耦（B6）

### Task 4.1 — G2/G3 + 解耦校驗 [C-11][C-12][R7]
- SPEC ref：§P Task 4.1 + §G　目標：G2(artifact 全表)/G3(多 symbol+gap) + 解耦。
- 輸入：B1-B5 全 surface　輸出：`tests/golden/ic_phase1_contract/`、各 test。
- 實作要點：
  1. **G2**：`test_artifact_roundtrip` 全表 sha256 全等（非抽樣，已在 3.1）。
  2. **G3**：`test_split_leakage_golden`（BTC+ETH 真實 kline + gap/unsorted/dup/**sorted-but-multi-symbol** 反例必 raise；正例 symbol 純度==1.0 且 train set==expected）。
  3. **[C-11] 解耦（cursor F7）**：`grep -r "from api" momentum/core momentum/Analysis/ic_split_adapter.py`==0 **雙向**（含 `from api.models`）。
- 修改檔案：`tests/golden/ic_phase1_contract/`、`tests/momentum/`、`tests/api/`。既有 caller：無。
- 不可做：不用合成 fixture 代替真實 kline。
- 邊界：見各 Task。
- 風險緩解：R7+C-11。
- 驗證：`pytest tests/momentum/core/ tests/momentum/Analysis/ tests/api/` 全 PASS；`grep -rE "from api\." momentum/ | wc -l`==0；`./scripts/check_decoupling_phase4.sh` exit 0；G1 deep-equal、G2 sha256、G3 反例 raise。

---

## §自檢結果（階段 3）
- **覆蓋追溯**：[C-1]→1.1、[C-2]→1.2、[C-3]→1.3、[C-4]→1.4、[C-5]→2.1、[C-6]→2.2、[C-7]→2.3、[C-8]→3.1、[C-9]→3.2、[C-10]→3.2(+§N HTTP)、[C-11]→4.1、[C-12]→4.1+B0；R1→1.3/1.4、R2→2.2/3.2/G1、R3→1.4、R4→3.1、R5→3.2、R6→3.2、R7→B0/G2/G3、R8→3.1、R9→1.1/1.2。**TODO-adversarial**：T1→B0、T2→2.2(序列化)、T3→3.2(route)、T4→1.4(embargo 演算法)、T5→3.1(tier 相對門檻+psutil)、T6→3.2(子端點)、T7→3.1(horizon 映射)、codex-B5→1.3(多symbol 強化)、cursor-F0-1→1.4(WF 展開)、cursor-F8→1.3(gap 公式)、codex-logging→§0、cursor-F7→4.1。**全落地。**
- **深度**：每 Task 實作要點≥3 含偽碼/簽名、修改檔到函式、邊界≥2、驗證可證偽。
- **批次拓撲**：B0→B1→{B2,B3,B4}→B5(依 B2,B4)→B6；**baseline 在 B0(改碼前)**,無 forward dependency。
- **錨點**：§0 ✓ §B ✓ 每 Task 驗證/邊界/不可做 ✓。

## §階段 4 handoff
`SPEC=docs/IC_PHASE1_CONTRACT_SPEC.md TODO=docs/IC_PHASE1_CONTRACT_TODO.md FOCUS=洩漏紅線(1.3/1.4)+byte不變(B0/G1)+embargo演算法(T4)+route(T3)`
