# IC Phase 1 — 1-contract（契約層）SPEC（v2，已納雙家族 adversarial）

> 來源 PLAN/診斷：handoffs/20260624-ic-roadmap-phasing-CONVERGED.md（§Phase 1）+ handoffs/20260625-ic-PHASE1-{BRIEF,CONTRACT-MANIFEST}.md
> Adversarial reconcile：handoffs/20260626-ic-PHASE1-CONTRACT-ADVERSARIAL-RECONCILE.md（CODEX+CURSOR 雙家，R1-R9）
> 日期：2026-06-26　|　對應 TODO：docs/IC_PHASE1_CONTRACT_TODO.md（待 TODO_GENERATION 生成）

## §RISK 風險分級
- **大小**：大（契約是後面 1a-1f 全部正確性修法的地基，跨棧、難回退）。
- **命中高風險原則**：(a) 數值/資料品質（artifact 全表值守恆、not_evaluated 不混入 0）、(b) 跨模組共用路徑（`momentum/core/contracts.py`+`api/models/ic_models.py`+`ic_analysis_service.py`，多下游）、(c) 多 phase 難回退（契約定錯 → 1a-1f + Phase 3 返工）、(d) ML 正確性/防洩漏（per-symbol + 單 symbol 時間連續性、selection scope、前瞻對齊）。
- 命中 (a)+(d) → §G Golden 必填、adversarial review 必跑（已跑雙家）、三方數據正確性簽核必跑。

## §A 假設與待使用者確認
- **已驗證事實**（附驗證方式：pytest 實跑 / grep / 實讀 .py 原始碼）：
  - **只有 `CombinatorialPurgedCV` 有 `def split()`**（`combinatorial_purged_cv.py:41`，yield `(train_idx,test_idx)` int 陣列）。**`WalkForwardValidator` 無 `def split()`**（`grep "def split" walk_forward_validator.py`→0，實驗證），對外只有 `validate(model_factory,X,y,...)`，內部 `_generate_rolling_splits()` 回 index range tuples。【v1 §A 誤稱兩者皆有 split()，已更正——CURSOR adversarial 抓出】
  - CPCV/WF 切分用 **positional integer index**，purge/embargo 用連續切片 `mask[purge_start:purge_end]`（`combinatorial_purged_cv.py:181-197` 實讀）。**positional purge 假設樣本時間連續等距**。
  - **CPCV 在 train 清空時會自動降 embargo（silent relaxation）**：`combinatorial_purged_cv.py:75-79` 實見 `embargo_pct/2` 重算 + warning。複用時若不偵測會繼承此弱化。
  - ML 孤島既有 30 測試（15 CPCV+15 WF）**全 PASS 但全為 synthetic fixture（`synthetic_binary_data`，無 timestamp/無 gap/未碰 kline_cache.h5）**；**不足以證明 IC 真實時間軸 purge 正確**，不得引用代替 [C-3] 測試。
  - 既有 IC DTO：`ICResult`(contracts.py:283，無 horizon 維度)、`FilteredFeatureSet`(301)、`SkippedResult`(311)；API DTO `api/models/ic_models.py`。
  - 既有結果回傳：`IcAnalysisService.get_result()`(L275)→`result` dict→`_to_json_compatible()`(L469)，全 JSON 路徑；前端 `useICAnalysis`/`types.ts` 直接消費該 dict。
  - 既有特徵讀取已 **Parquet-only(V7)**：`momentum/FeatureEngineering/feature_reader.py` docstring；`api/core/config.py` **無** `ic_response_v2` key（實 grep）。
  - 真實 kline：`data_cache/feature_klines/kline_cache.h5`（10 symbols × {1h,4h,12h}，OHLCV+taker/quote/trades）。
- **已確認結果**（使用者，2026-06-25）：① 先全力 Phase 1 正確性。② API 版本化(top-N 摘要+artifact URI)，artifact 須全表可篩(FF-explorer 式)。③ 複用 ML 孤島切分索引邏輯(不重寫切分數學、不碰模型引擎)。④ not_evaluated=防漏非允許漏(P1 全評估)。⑤ XGBoost/LightGBM 空殼疑慮留 Phase 4。
- **委員會收斂裁決（技術決策，依雙家 adversarial，對使用者透明不另問）**：
  - **[Q-1]→Parquet**（非 HDF5）：composer 證據 feature_reader V7 已 Parquet-only + Phase 3 串流亦 parquet → HDF5 必二次遷移；codex 要求的權衡論證見 §P Task 3.1 表。**改寫先前給使用者的 HDF5 預設。**
  - **[Q-2]→同 endpoint + `?schema_version=2` negotiation + `ic_response_v2` flag**（預設 off）；flag-off 必 byte-for-byte 等於 baseline（見 §G）。
  - **[Q-3]→漸進遷移 + SSOT 規則**：v2 on 時 top-N 摘要必由 artifact 衍生（非另算）；artifact 路徑含 `task_id+config_hash+schema_version`。

## §C 約束
- 解耦 7 條：`grep "from api\." momentum/`→0；契約 DTO 引擎側 `momentum/core/contracts.py`、API 側 `api/models/ic_models.py`，兩側不互 import（Rule 7）；服務經 factory。
- 不可違反原則：跨 tier 可重複、多 symbol 不 OOM、資料品質（不假資料/不跨 symbol 污染/**不靜默接受 CPCV embargo 降級**）、不弱化 NaN/inf gate、不擅改輸出數值大小。
- 共用路徑：`momentum/core/contracts.py`、`api/models/ic_models.py`、`api/services/ic_analysis_service.py`（下游：IC service、前端 ic-analysis、decay/quantile/correlation/grouped/export route 皆讀 `get_result()`、Phase 3 串流）。
- **cross_sectional 模式**（`ic_filter_orchestrator.analyze_cross_sectional`）本刀 [C-3] 不涵蓋（見 §N）。

## §G Golden / Baseline（拆三 golden，R7；行為不變簽核點=改前==改後）
> 凍結時機：動工前。reference run 寫死：symbol=**BTC**, timeframe=**1h**, mode=longitudinal, `config_hash`=**取 feature_library 最新 BTC/1h run 之 hash 並在 TODO 凍結前寫死**（附生成命令；不得實作者自選）。
- **G1 — v1 JSON byte-stability（flag off）**：`ic_response_v2=false` 時 `/result/{task_id}` 與 `tests/golden/ic_phase1_contract/baseline_btc_1h.json` **deep equality（非僅「舊欄存在」）**；既有 `to_dict`/JSON 路徑無新鍵（含不序列化 `eval_status`）。通過：`==` 全等，任一鍵/值 diff=FAIL。
- **G2 — artifact 全表 roundtrip（非抽樣）**：寫入全部 feature×horizon → 讀回 **所有 row 的 value/NaN/inf/eval_status 之 sha256 全等**（非抽樣 hash）；含 NaN mask hash。通過：`abs<=1e-9 或 rel<=1e-7`(float64) 且 sha256 相等，否則列 feature+diff=FAIL。
- **G3 — 多 symbol split/leakage golden**：至少 BTC+ETH 真實 kline，含 **gap/未排序/重複 timestamp 反例**；assert 跨 symbol 與單 symbol-gap 兩類洩漏皆 fail-closed（raise）。通過：反例必 raise，正例 train/test symbol 純度==1.0 且 purge 距離==requested。
- 範圍限定：Golden 僅 flag-off + 單 symbol longitudinal（G1）+ 契約層（G2/G3）；**cross_sectional 不覆蓋**。

## §P Phase 與依賴

### Phase 1 — 切分/列遮罩契約（依賴：無）
**Task 1.1 — SplitPlan 契約 [C-1][R9]**
- 目標：定義 train/val/test 列歸屬的 **canonical timestamp-based** 表示。檔案：`momentum/core/contracts.py` 新增 `@dataclass(frozen=True) SplitPlan`。caller：無（新建）。
- 改法：欄位 `split_label: Literal["train","val","test"]`、`index_kind: Literal["timestamp","positional","row_id"]`（canonical=timestamp）、`row_index: np.ndarray`、`time_bounds: tuple[ts,ts]`、`purge_gap: int`、`embargo: int`、**`purge_semantic: Literal["rows","timedelta"]`（預設 "rows"，標 1a 改 timedelta）**、`expected_freq: Optional[str]`、`base_universe_hash: str`（來源 frame order/identity hash）、`symbol: Optional[str]`。frozen+型別註記。
- 驗證：`pytest tests/momentum/core/test_split_contract.py::test_splitplan_fields` `assert` 欄位+型別；`from momentum.core.contracts import SplitPlan` import 成功；`test_splitplan_requires_base_universe_hash`（缺 hash raise）。
- 邊界（≥2）：空 index→建構成功標 empty；`purge_gap>=`區段長→建構 raise ValueError；`index_kind` 非法→raise。
- 不可做：不實作切分執行（1a）。

**Task 1.2 — RowMaskPlan 契約 [C-2][R9]**
- 目標：以 canonical row identity 表達「哪些列入計算」遮罩。檔案：`momentum/core/contracts.py` 新增 `RowMaskPlan`。
- 改法：欄位 `row_index: np.ndarray`、`index_kind: Literal["timestamp","positional","row_id"]`、`source: Literal["split","event","feature_filter","full"]`、`base_universe_hash: str`、`length: int`、`symbol: Optional[str]`；`n_selected` property；提供 `to_mask(base_len)`/`from_mask(mask)` 但**禁無 discriminator 的 ambiguous union**。
- 驗證：`pytest tests/momentum/core/test_rowmask_contract.py::test_rowmask_roundtrip`（`assert (from_mask(to_mask(idx))==idx).all()`）；`test_rowmask_requires_index_kind`（缺 raise）。
- 邊界：全 False→n_selected==0 不報錯；length!=base→raise；base_universe_hash 不符→raise。
- 不可做：不接現有計算路徑（共存）。

**Task 1.3 — 單/多 symbol 時間連續性洩漏紅線 [C-3][R1]（(d) 紅線）**
- 目標：契約強制 (i) split per-symbol 套用不跨 symbol、(ii) **單 symbol 內 timestamp 單調遞增/無重複/符合 expected_freq（或明確允許 gap 並用 timestamp purge）**；違反 fail-closed。檔案：`momentum/core/contracts.py` 新增 `validate_split_integrity(plan, ts, symbols)` + `CrossSymbolLeakageError` + `TimestampDiscontinuityError`。
- 改法：校驗 ① 多 symbol 未 per-symbol grouped/未 sorted by (symbol,time)→raise `CrossSymbolLeakageError`；② 單 symbol 內 `ts` 非單調/有重複/與 `expected_freq` 不符且 `purge_semantic=="rows"`→raise `TimestampDiscontinuityError`（因 row purge≠time purge）；提供 `split_per_symbol(...)` helper（逐 symbol 包既有 split，purge 不跨界）。
- 驗證（可證偽）：`pytest tests/momentum/core/test_split_contract.py::test_cross_symbol_purge_blocked`（BTC 尾接 ETH 頭，未 per-symbol→`pytest.raises(CrossSymbolLeakageError)`）；`test_single_symbol_gap_blocked`（取 kline_cache.h5 BTC/1h **刪 3 根 bar 製造 gap**，rows-purge→`pytest.raises(TimestampDiscontinuityError)`）；`test_unsorted_dup_ts_blocked`。per-symbol 正例→`assert` symbol 純度==1.0。**用真實 kline。**
- 邊界：單 symbol 連續→正常切；symbol 欄缺→raise；允許 gap 模式（freq=None）→需 timedelta purge 否則 raise。
- 不可做：不重寫 purge/embargo 數學。

**Task 1.4 — ML 孤島 adapter + 弱化偵測 [C-4][R1][R3]**
- 目標：`SplitPlan` 由既有切分產出轉換；**偵測 CPCV silent relaxation 並 fail-closed**。檔案：`momentum/Analysis/ic_split_adapter.py`（新）+ `momentum/factories.py` 加 `create_ic_split_adapter()`。
- 改法：① **CPCV path**：逐 symbol 呼叫 `cpcv.split()`，包成 `SplitPlan`，套 [C-3] 校驗。② **WF path（修正:WF 無 split()）**：包裝 `_generate_rolling_splits(n_samples,...)` 為 `iter_split_indices()`（允許在 adapter 層讀取，不改 WF 檔內既有方法簽名）；**或** Phase 1 僅 adapter CPCV、WF 標 1a 依賴（TODO 二選一並寫死）。③ **strict mode**：adapter 呼叫後**重算 returned train/test 的 effective embargo 距離**，若 < requested（即 CPCV 降級發生）→ raise `EmbargoRelaxedError` 或回 `SkippedResult`，不靜默。
- 驗證：`pytest tests/momentum/Analysis/test_ic_split_adapter.py::test_adapter_wraps_cpcv`（真實 kline 多 symbol→SplitPlan list，`assert` 各 plan 過 [C-3]，索引與直接 split() per-symbol `np.array_equal`）；`test_adapter_detects_embargo_relaxation`（構造小樣本觸發 CPCV 降級→`pytest.raises(EmbargoRelaxedError)`）。
- 邊界：validator raise（樣本不足）→傳 `SkippedResult` 不吞；空 symbol list→raise。
- 不可做：不改 `walk_forward_validator.py`/`combinatorial_purged_cv.py` 既有方法內部邏輯（WF 只在 adapter 層讀 `_generate_rolling_splits`）。

### Phase 2 — 範圍/評估契約（依賴：Phase 1）
**Task 2.1 — SelectionScope 契約 [C-5]**
- 目標：記錄 FDR/顯著性在「universe×split×evaluated features」+ canonical scope id。檔案：`momentum/core/contracts.py` 新增 `SelectionScope`。
- 改法：欄位 `scope_id: str`、`universe_features: list[str]`、`split_label`、`evaluated_features: list[str]`、`n_tests: int`、`method: str`、`base_universe_hash: str`。
- 驗證：`pytest tests/momentum/core/test_scope_contract.py::test_selection_scope_fields`；`test_scope_n_tests_matches_evaluated`（`assert scope.n_tests==len(scope.evaluated_features)`）。
- 邊界：evaluated 空→n_tests==0；evaluated⊄universe→raise。
- 不可做：不實作 FDR（1b）。

**Task 2.2 — EvaluatedScope + not_evaluated 語義 [C-6][R-codex9]（(a)）**
- 目標：明訂 已評估/未評估/legacy 邊界；未評估不混入排序/FDR。檔案：`momentum/core/contracts.py` 新增 `EvaluationStatus`(Enum: EVALUATED/NOT_EVALUATED/SKIPPED/**UNKNOWN_LEGACY**) + `ICResult` 加 `eval_status: EvaluationStatus = UNKNOWN_LEGACY`。
- 改法：新契約物件建構時**要求明確 eval_status**；legacy/未遷移→`UNKNOWN_LEGACY`；`filter_evaluated(results)` 排序/FDR 前**只接受 explicit EVALUATED**（剔除 NOT_EVALUATED/SKIPPED/UNKNOWN_LEGACY）；**JSON 序列化（flag off）不輸出 eval_status**（保 G1 byte 不變）。
- 驗證（可證偽）：`pytest tests/momentum/core/test_eval_status.py::test_only_explicit_evaluated_ranked`（混 4 種狀態→`assert filter_evaluated` 只剩 EVALUATED）；`test_legacy_not_counted_as_zero`（`assert` UNKNOWN_LEGACY 不入 n_tests）；`test_flag_off_json_has_no_eval_status`（G1 連動）。
- 邊界：全非 EVALUATED→filter 回空+log warning（不 raise）；既有 ICResult 反序列化→UNKNOWN_LEGACY。
- 不可做：Phase 1 不產 NOT_EVALUATED（小尺度全評估）；只建 surface。

**Task 2.3 — 前瞻偏誤對齊契約 [C-7]（(d)）**
- 目標：定義 Feature_t vs Target_{t+lag} 對齊不變量契約欄位（給 1-align）。檔案：`momentum/core/contracts.py` 新增 `AlignmentSpec`(feature_ts_col, target_ts_col, lag, freq) + `validate_alignment(...)` **僅簽名**。
- 改法：純 dataclass + 函式簽名，body `raise NotImplementedError`（註記 1-align 落地）。
- 驗證：`pytest tests/momentum/core/test_alignment_contract.py::test_alignment_spec_fields`；`test_validate_alignment_signature`（`assert callable` 且 `pytest.raises(NotImplementedError)`）。
- 邊界：lag<0→建構 raise；freq 非法→raise。
- 不可做：不實作對齊偵測（1-align）。

### Phase 3 — 輸出/API 版本化契約（依賴：Phase 2）
**Task 3.1 — Artifact metric table schema（Parquet）[C-8][R4][R8]（(a)）**
- 目標：全因子完整指標表落 **Parquet** artifact，不載全表即可篩。檔案：`momentum/core/contracts.py` 新增 `ICArtifactSchema`（**明確欄位**：`feature_name:str, horizon:int, ic_mean:f64, ic_std:f64, icir:f64, p_value:f64, ic_hit_rate:f64, eval_status:str, selection_scope_id:str, schema_version:int`，long layout）+ `momentum/Analysis/ic_artifact_writer.py`（Parquet writer/reader，predicate pushdown 篩選、atomic write）。**本刀 writer 為純 schema/IO，不接進 task result path（保 R2/G1）。**
- **[Q-1] 權衡表（codex 要求）**：

  | 面向 | Parquet（採） | HDF5（棄） |
  |---|---|---|
  | 篩選 | predicate pushdown 不載全表 | 多需整 group 載入→8GB OOM |
  | 與 codebase | feature_reader V7 已 parquet | 舊路徑 |
  | Phase 3 串流 | 一致 | 二次遷移 |
  | 業界 | quant artifact 慣用 parquet/arrow | 少 |
- 改法：writer `write(results, path)` atomic（temp+rename）；`read(path, filters, columns, page)` 用 pyarrow predicate pushdown，**memory bound 不整表載入**；schema_version 寫 metadata。
- 驗證（可證偽）：`pytest tests/momentum/Analysis/test_ic_artifact.py::test_artifact_roundtrip`（寫 N feature→讀回 **全 row** value/NaN/inf/eval_status sha256 全等，G2）；`test_artifact_filter_no_full_load`（filter 子集 `len` 正確且 peak RSS < 門檻，用 `tracemalloc`）；`test_artifact_atomic`（中斷不留半檔）。**真實 IC 輸出。**
- 邊界：空結果→寫空表可讀；NaN/inf→保真；寫中斷→無孤兒（atomic）。
- 不可做：不刪舊 JSON 路徑；**不接 task result path**。

**Task 3.2 — API response 版本化 + negotiation [C-9][C-10][R2][R5][R6]（(b)）**
- 目標：v2 response=top-N 摘要+artifact_uri（由 artifact 衍生，SSOT）；flag-off byte 不變。檔案：`api/models/ic_models.py` 新增 `ICResultV2Response`(schema_version, top_n_summary, artifact_uri, total_features) + `api/core/config.py` 加 `ic_response_v2: bool=False` + `IcAnalysisService.get_result()` 加 `?schema_version` 分支。
- 改法：negotiation=`/result/{task_id}?schema_version=2`（無參或 flag off→v1 原樣）；**相容矩陣三態**：(off)→v1 deep-equal baseline；(on,有 artifact)→v2 envelope，top_n 由 artifact 篩 top-N 衍生（非另算，SSOT）；(on,無 artifact)→artifact_uri=None+明確狀態（不假連結）。artifact 路徑 `…/{task_id}_{config_hash}_v{schema_version}.parquet`。
- **[C-10] 讀端點**：本刀僅定 `ICArtifactQueryParams`（`sort_by: enum`, `filter` 白名單運算子, `page_size`(tier cap), `cursor`）+ Python reader API；**HTTP route 落 Phase 3**（降 scope，§N 登記），避免空殼。
- 驗證：`pytest tests/api/test_ic_response_v2.py::test_flag_off_deep_equal_baseline`（off→與 baseline_btc_1h.json `==` deep equal）；`test_v2_envelope_shape`（on→含 schema_version+artifact_uri+top_n_summary）；`test_v2_top_n_derived_from_artifact`（SSOT：top_n_summary==artifact 篩 top-N）；`test_no_artifact_uri_none`。
- 邊界：大 run→v2 response 不含全表（`assert` size 上限）；retry→artifact 路徑冪等不孤兒。
- 不可做：不改前端（前端接線另刀）；不刪 v1；不在此實作 HTTP 篩選端點。

### Phase 4 — 測試/落地（依賴：Phase 1-3）
**Task 4.1 — 可證偽契約測試集 + 三 Golden [C-11][C-12][R7]**
- 目標：解耦校驗 + 真實 kline falsifiable 測試 + G1/G2/G3。檔案：`tests/momentum/core/test_*_contract.py`、`tests/momentum/Analysis/test_ic_*.py`、`tests/api/test_ic_response_v2.py`、`tests/golden/ic_phase1_contract/`。
- 改法：集合上述測試；凍結 G1/G2/G3 baseline（§G，config_hash 動工前寫死）；解耦檢查。
- 驗證：`pytest tests/momentum/core/ tests/momentum/Analysis/ tests/api/` 全 PASS；`grep -rE "from api\." momentum/ | wc -l`==0；`./scripts/check_decoupling_phase4.sh` exit 0；G1 deep-equal、G2 sha256 全等、G3 反例必 raise。
- 邊界：見各 Task。
- 不可做：不用合成 fixture 代替真實 kline（.h5）（三方簽核鐵律 / 驗證保真度鐵律）。

## §V 驗證策略與邊界測試目錄
- 層級：單元（契約欄位/型別）、整合（adapter↔ML 孤島 + embargo 降級偵測）、Golden（G1 v1 byte / G2 artifact 全表 / G3 多symbol+gap）、邊界。全可 `pytest tests/momentum/core/ tests/momentum/Analysis/ tests/api/` 獨立跑，不需 run_api.py（Rule 6）。
- **防假綠**：`grep` diff 既有測試斷言，不得放寬/刪除換綠燈。**[C-3] 跨 symbol 與單 symbol-gap 反例必須真 raise（`pytest.raises`），不得降級 warning**（驗證保真度鐵律）；**不得引用既有 30 synthetic 測試代替 [C-3]**。
- **真實資料**：所有資料正確性測試用 `kline_cache.h5`，禁合成 fixture 代替（三方簽核鐵律 #2）。
- **跨 tier 表（R-cursor橫向）**：

  | tier | artifact 寫 peak RSS 上限 | filter read peak RSS | page_size cap |
  |---|---|---|---|
  | 8GB | 待 TODO 量測寫死 | 不整表載入 | 小 |
  | 16/32GB | 寬鬆 | 同 | 中/大 |
- **邊界目錄**（打勾對應 Task）：☑空DF ☑全NaN列 ☑Inf ☑std=0 ☑重複/亂序 timestamp(1.3) ☑**缺bar/非等距index(1.3)** ☑多symbol堆疊(1.3) ☑CPCV embargo 降級(1.4) ☑artifact 寫中斷 atomic(3.1) ☑大尺度浮點 reduction(G2)。

## §R 回退
- 每 Task 獨立 commit 可單獨 revert；新契約 surface 預設不接舊路徑（共存）；API 版本化用 `ic_response_v2` flag（預設 off，off=v1 原行為，G1 保證 byte 不變）；artifact writer 不接 task result path；Golden 任一 FAIL→不 merge。

## §N N/A 登記
- **cross_sectional 模式的 split/leakage 契約**：N/A — 本刀 [C-3] 只涵蓋 longitudinal 堆疊 per-symbol；cross_sectional（`analyze_cross_sectional` 按 timestamp 橫截面 rank）的洩漏語義留 1a 補（風險：本刀不保護該路徑，須在 1a 前不開放 cross_sectional 正確性宣稱）。
- **[C-10] artifact HTTP 篩選端點**：本刀只定 query 契約 + Python reader API；HTTP route 落 Phase 3（避免空殼）。
- **artifact GC / task 刪除清理**：N/A 本刀（風險記錄：retry/resume 可能留孤兒 artifact，Phase 3 補 GC）。
- 其餘必填段（§RISK/§A/§C/§G/§P/§V/§R）全填。
