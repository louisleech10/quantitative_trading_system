# GAP-3 事件型分析 TODO（DRAFT v0.2｜基於 `docs/GAP3_EVENT_SPEC.md` FROZEN 2026-08-20｜生成日 2026-08-20）

> 狀態：**DRAFT**（v0.2＝R7 對抗審 12 修訂群集寫回，synth `handoffs/reconcile/20260820-gap3-x-review-r7/synth.md`；Frozen 前只能標 Internal Frozen）。
> 生成依據：`templates/TODO_GENERATION_PROMPT.md` V13；階段 1 索引＝`handoffs/20260820-gap3-todo-stage1-index.md`（追溯基準：20 Task／26 驗證項／§G 6 項／M1–M12／殘留 8）。
> 層級宣告（W1）：**操作依據＝本檔**（執行端逐 Task 寫碼以本檔為準）；**語意權威＝`docs/GAP3_EVENT_SPEC.md`（FROZEN）**——本檔與 SPEC 衝突時以 SPEC 為準並回報，不得自行取捨；**欄位/枚舉/reason 字面 SoT＝`momentum/Analysis/contracts/event_import_contract.json`（Task B1.0 產出）**——B1.0／B2.4 內之欄位列舉為 **genesis 建檔規格**（建檔依據，僅此兩處），檔建立後以契約檔為準、該列不再維護；其餘章節與程式禁複列鍵表。
> 歸屬票：全部 Task＝`docs/IC_QUANT_GAP_REGISTRY.md` **#3（GAP-3）**；各 Task 標題之 `票 #3` 指此。

## §0 全域規則與約束（執行端讀完即可遵守）

1. **解耦**（SPEC §C-1）：R1 `momentum/` 不 import `api/`（新模組全在 `momentum/Analysis/event_samples/` 與 `momentum/FeatureEngineering/operators/`；範例：`from momentum.Analysis.event_samples.alignment import align_events` 合法，`from api.models import …` 在 momentum/ 內＝違規）；R5 config 單一來源（運行參數入 `momentum/core/config.py` 既有 schema 或函式參數 dataclass，禁散落模組級常數；**門檻/枚舉字面唯一住契約檔**）；R6 `pytest tests/momentum/` 獨立跑（不需 `run_api.py`）；R7 DTO 不跨界（事件契約 dataclass 住 `momentum/Analysis/event_samples/types.py`，`api/models/` 只做 request/response 殼）。
2. **資料真實**（SPEC §C-2／§G）：涉對齊/特徵取列/全 K 線驗證 ⇒ 必用真實 kline（`tests/golden/la0/inputs/` 既有 fixture 或 `data_cache/feature_klines/kline_cache.h5`）；統計 oracle 可用合成**因子/label/事件序列**（`docs/TEST_DESIGN_CHARTER.md` §F），**禁合成價格**。
3. **NaN/inf 不弱化**（SPEC §C-2）：對齊/物化失敗＝loud 枚舉（reason 字面見契約檔），**禁 fillna(0)、禁 silent `continue`**（舊雛形 `xgboost_batch_service.py:621,651` 之靜默跳過＝反例，不沿用 [FACT-RECEIPT]）。
4. **輸出大小**：IC 主線既有報告鍵集不變，只新增（§G-1 golden 機械看住）。
5. **JSON SoT**（SPEC §C 範本鐵律）：事件欄位名/枚舉值/reason/分類門檻字面**只**在 `event_import_contract.json` 出現一次（B1.0）；survivor 擴欄字面**只**在 `ic_survivor_contract.json` v2（B2.4）。本檔各 Task 僅寫「鍵住契約檔 §<區>」。
6. **允許改動之既有檔白名單**（唯此八項＝SPEC §C-3 原六項＋W2 寫回之 ⑦⑧）：① `ic_survivor_contract.json`＋`momentum/Analysis/survivor_contract.py` 只在 B2.4；② `momentum/Analysis/ic_filter_orchestrator.py` 只在 B2.3；③ `momentum/Analysis/event_filter.py` 只在 B3.2；④ `momentum/FeatureEngineering/operators/`＋registry 只在 B3.3；⑤ `api/models/`＋`api/routes/`＋`api/services/`（case/search/ic 路徑）與 `frontend/src/` 只在 B5；⑥ 既有測試檔只新增斷言禁放寬；⑦ `momentum/factories.py` **只在 B5.1** 新增 `create_event_sample_pipeline()` 一個出口（SPEC §RISK 末行明文授權；W2）；⑧ 收尾文件（`HANDOFF.md`／`docs/ROADMAP.md`／`docs/IC_QUANT_GAP_REGISTRY.md`／`白話說明/`）**只在 B5.3**（W2）。**不改**：`xgboost_batch_service` 訓練殼、`label_generator.py`、`SplitPlan`（`momentum/core/contracts.py`）、回測層、`pattern_extractor.py` 既有簽名。
7. **成熟度約束**（SPEC §C）：`api/services/xgboost_*`、`momentum/Optimization/`、回測層內部不得作為設計依據；事件契約只綁 `symbol/timeframe/bar 邊界/時區/snapshot digest`，**不綁 HDF5 佈局**。
8. **R5 A′ 語意原樣保留**（SPEC §C）：條件 IC fallback 時 `event_timestamps` 透傳＋one-shot guard 不動；fallback ⇒ `fallback_requested_scope`＋`degraded`，禁丟事件。
9. **防假綠**（SPEC §V）：不得放寬/刪除既有測試斷言換綠；每批 review brief 附既有測試 diff。
10. **時間**：一律 epoch ms UTC（[D2-3]）；量級像秒卻宣告 ms ⇒ 拒。
11. **預設 ON**（SPEC §R-3）：驗證 PASS 後預設啟用；flag 只作逃生口。
12. **程式規範**：全函式 type hints；docstrings 中文；`get_logger(__name__)`；hot loop 不 log；向量化優先。
13. **鐵三角語意錨**（SPEC §0，實作時逐條回查該節原文）：[D1] 標籤/價格語意（`close_to_close` 預設、label 錨 mode-scoped、entry 映射 D1-6）；[D2] PIT 三段鏈＋兩層收據＋失敗枚舉；[D3] 欄位角色隔離；[D4] 固定分母 manifest。白話閘裁決①門檻皆舉例可調②`label_return_mode` 三值③`decision_offset_bars`＝研究參數。

## §B 批次執行策略（依賴拓撲 → 5 批；實作＝主委自任，review＝三家全員／ORCH §1）

| Batch | 含 Task（批內順序） | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | B1.0→B1.1→B1.2→B1.3→B1.6→B1.4→B1.5 | 無 | 資料正確性底座一批可驗（C9）；B1.4 需 B1.6 產出 | 大 |
| B2 | B2.1→B2.2→〔§G 凍結〕→B2.3→B2.4→B2.5 | B1 | 三表＋estimand 並排；凍結須在 B2.3 動工前 | 大 |
| B3 | B3.1→B3.2→B3.3 | B1＋B2.5（G6 呼叫 all-bars evaluator） | 產生器共用 B1.0 validator＋B2.5 | 中 |
| B4 | B4.1→B4.2 | B2、B3 | pattern→ledger 單向鏈 | 中 |
| B5 | B5.1→B5.2→B5.3 | B1–B4 | 上線面（API/前端/UAT）一次接 | 中 |

**批間 Gate（每批全過＋三家 code review＋三家戳記才進下批＝U13）**：

- **B1 Gate**：`venv/bin/python -m pytest tests/momentum/event_samples/ -q` rc=0（含 `test_import_contract.py`／`test_alignment.py`／`test_dedupe.py`／`test_event_split.py`／`test_feature_materialization.py`／`test_baseline_oracle.py`／`test_counterexample_classifier.py`）＋mutation `test_mutation_guard.py -q -k "M1 or M2 or M3 or M5 or M8 or M9 or M10 or M12"`（B1 歸屬 8 條）逐條紅（mutation 注入時）／綠（baseline）。
- **B2 Gate**：`pytest tests/momentum/event_samples/ -q`＋`pytest tests/momentum/ -q -k "gap3 and conditional_ic"`＋`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_baseline_oracle.py -q -k conditional_ic` rc=0（W3：conditional-IC 置亂 oracle）；`venv/bin/python scripts/gap3_freeze_golden.py --check` rc=0（§G-1）；mutation M4/M7/M11。
- **B3 Gate**：`pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters"`＋`pytest tests/momentum/feature_engineering/ -q -k state_counters` rc=0；G1–G6 逐項斷言；mutation M6；§G-1 `--check` 複跑 rc=0（B3.2 接線後）。
- **B4 Gate**：`pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` rc=0（含 AUC→DSR 拒絕 ASSERT）。
- **B5 Gate**：`pytest tests/api/ -q -k gap3_import`＋`cd frontend && npm run build`＋`cd frontend && npx vitest run gap3`＋`pytest tests/momentum/event_samples/ -q`＋`bash scripts/plain_docs_sync_check.sh` 全 rc=0；`docs/GAP3_UAT_CHECKLIST.md` 逐項附 rc＋使用者簽字。

**每批派工 prompt 骨架（主委自任仍照走；review 派工另走 `gate.sh dispatch`＋brief）**：

> Batch B{n} 開工。前置狀態：B{n-1} 已過批間 Gate＋三家戳記（受 `review_quorum_check.sh` 機檢）。本批 Task：{列表}。逐 Task 照 `docs/GAP3_EVENT_TODO.md` 對應節實作；驗證命令見各 Task「驗證」欄；批完成跑上表 B{n} Gate 全部命令。禁動白名單（§0-6）外之既有檔。完成後派三家 code review（diff＋測試 diff＋摘要）。

---

## Phase B1 — 匯入契約＋PIT 對齊＋樣本 manifest＋切分＋特徵物化＋自檢 oracle
**目標**：外部標註事件可 fail-closed 匯入並完成 PIT 正確的樣本建構。完成後系統狀態：`momentum/Analysis/event_samples/` 具八個純函式模組＋契約 JSON SoT，`pytest tests/momentum/event_samples/ -q` 綠，8 條 mutation guard 生效。

### Task B1.0 — 事件匯入契約 JSON SoT＋validator（`票 #3`）
- SPEC ref：Task B1.0／D1-1／D2-2／[AR-1][AR-2]　目標：所有事件欄位名/枚舉值/reason 字面只在一個檔；匯入 fail-closed。
- 輸入/輸出：輸入＝使用者 CSV/JSON 記錄列表；輸出＝`event_import_contract.json`（SoT）＋驗證通過之 `pd.DataFrame`（dtype 正規化）或 `ContractValidationError`。
- 實作要點：
  1. 新建 `momentum/Analysis/contracts/event_import_contract.json`，區塊：`version`、`required_fields`（`event_id/symbol/timeframe/t0/decision_offset_bars/entry_price_semantic/direction/scenario/label/label_definition/control_kind/source_file_digest/data_snapshot_digest`——值集與型別全在檔內定義，含 `entry_price_semantic` 五值、`label_return_mode` 三值預設 `close_to_close`、`control_kind` 四值閉集與 accepted 三值＋`platform_random_bars` 恆拒 reason）、`optional_fields`（`label_value/counterexample_kind/kind_source/search_rule_summary/taxonomy 五欄/event_type_tag/meta`）、`conditional_required`（T8 `reference_symbols[]`／T9 `source_model`／T10 `event_interval`——觸發條件與全欄列舉）、`derived_fields`（六時間欄、`event_known_at_decision/dedupe_cluster_id/overlap_set_hash/uniqueness_weight/time_cluster_id/cluster_weight/counterexample_kind_effective` 四值集）、`failure_reasons`（D2-4 枚舉聯集＋`missing_control_group/not_implemented_platform_random_bars/missing_label_value/missing_prevalence_disclosure`）、`counterexample_classifier_config`（四門檻 `example_default` 值 0.05/0.0/0.01/0.05＋單位＋公式參數；白話閘①）、`receipt_schema`（事件級＋per-TF 兩層欄名——D2-4）、`_doc`（誠實邊界：hash 相同不證內容正確；v1 不重算 label）。〔本項全部列舉＝genesis 建檔規格；契約檔建立後以檔為準、本列不再維護——W1〕
  2. 新建 `momentum/Analysis/event_samples/import_contract.py`：
     ```python
     def load_event_import_contract() -> dict: ...  # 讀檔+版本檢
     class ContractValidationError(ValueError):     # .failures: list[dict]  {event_id|row, reason}
     def validate_event_import(records: list[dict] | pd.DataFrame,
                               *, contract: dict | None = None) -> pd.DataFrame: ...
     ```
     偽碼：載契約 → 頂層鍵集比對（缺必填/多未知鍵 ⇒ 收集 reason）→ 逐欄型別/枚舉閉集檢 → ms 量級閘（`t0 < 10**12` 宣告 ms ⇒ 拒）→ 條件必填（T8/T9/T10 觸發即全欄檢；T9 `available_at > decision_at` ⇒ reason `research_only` 拒）→ 二元任務單類別 ⇒ `missing_control_group` → **單批 `direction` 唯一值檢：同一匯入批同時出現 long 與 short ⇒ 拒（U1 一次只研究一向、匯入批內單值；規則住契約檔 validator/_doc——W12/GROK-R7-P1-02）** → `counterexample_kind` 出現 `unclassifiable` ⇒ 拒（匯入值集僅 a/b/c）→ 重複 `event_id` ⇒ 拒 → 任一 failure ⇒ raise（fail-closed，不回部分結果）。
  3. `momentum/Analysis/event_samples/types.py` 建 dataclass 殼（`AlignmentConfig/AlignmentReceipts/EventManifest/EventSplitPlan` 等，本批後續 Task 逐一填實；欄位名 pointer 契約檔）。
- 修改檔案：新增 `momentum/Analysis/contracts/event_import_contract.json`；新增 `momentum/Analysis/event_samples/{__init__,import_contract,types}.py`。既有 caller：無（`CaseRecord`／`/case/import` 不動，B5 才接 legacy adapter）。
- 不可做：不得在本檔/TODO/程式註解複列鍵表；不得沿用/擴充 `CaseRecord` 充當契約；不得實作 `platform_*` 抽樣。
- 邊界：①空 CSV/空列表 ⇒ loud 拒；②重複 `event_id` ⇒ 拒；③`label_value` 與 `label` 矛盾——值缺失容許、型別錯拒；④T9 `available_at > decision_at` ⇒ `research_only`/拒。
- 風險緩解：RISK-a（fail-closed 擋髒資料）；mutation M3/M12 歸屬本 Task 測試。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_import_contract.py -q` rc=0；斷言①頂層鍵集 `==` 契約列舉②枚舉值閉集③缺必填/多未知鍵/枚舉外值 ⇒ `ContractValidationError`④二元任務單類別 ⇒ `missing_control_group`⑤ms 量級閘（`t0<10^12` 宣告 ms ⇒ 拒）⑥**digest 篡改 negative fixture：`source_file_digest`／`data_snapshot_digest` 與實際內容不符 ⇒ 拒（§G-4 fail-closed——W4/CODEX-R7-P1-04）**⑦**單批 `direction` 混值（long＋short）⇒ 拒（W12）**。M3/M12 於 `test_mutation_guard.py -k "M3 or M12"` 可證偽。
- **存活至**：全票完工後保留；未來事件型所有匯入之唯一契約。
- **覆蓋風險**：無（B2.4 只動 survivor 契約，不動本檔）。

### Task B1.1 — PIT 對齊純函式＋兩層收據（`票 #3`）
- SPEC ref：Task B1.1／D2 全節／[AR-1]　目標：六時間欄推導、per-TF `feature_cutoff`、失敗枚舉 loud。
- 輸入/輸出：輸入＝B1.0 驗證後事件表＋`bars_by_tf: dict[str, pd.DataFrame]`（呼叫端已載入之 bar 表，欄含 `open_time_ms/close_time_ms/open/close`）＋`AlignmentConfig`；輸出＝`(AlignmentReceipts, failures: pd.DataFrame)`。
- 實作要點：
  1. `momentum/Analysis/event_samples/alignment.py`：
     ```python
     def align_events(events: pd.DataFrame, bars_by_tf: dict[str, pd.DataFrame],
                      config: AlignmentConfig) -> tuple[AlignmentReceipts, pd.DataFrame]: ...
     def n_dropped_by_reason(failures: pd.DataFrame) -> dict[str, int]: ...
     ```
     `AlignmentReceipts`（types.py）＝`event_level: pd.DataFrame`（每事件一列：`t0_ms/decision_offset_bars/decision_at_ms/entry_at_ms/entry_price_source{bar_open_ms,field}/label_start_ms/label_end_ms/entry_after_label_start`）＋`per_tf: pd.DataFrame`（每事件×每 TF：`feature_cutoff_ms/last_bar_open_ms/last_bar_close_ms/row_id`）——欄名字面 pointer 契約檔 `receipt_schema`。
  2. 推導偽碼（逐事件）：`decision_at`＝t₀ 往前第 k 根錨定 TF bar 之 open（k=`decision_offset_bars`；缺 bar ⇒ `missing_bar`）→ **validator 檢 `decision_at ≤ t0_open_ms`（t₀＝觸發根 open_time；AR-1／D2-2 獨立不變式，非三段鏈涵蓋；違反 ⇒ 該事件入 failures，reason=`no_boundary_match`——W11/GROK-R7-P1-01）** → entry bar/price 依 D1-6 映射（`trigger_open`＝t₀ open；`trigger_close`＝t₀ close；`next_open`＝t₀ 後下一根錨定 TF open；`decision_bar_open/close`＝decision bar）→ `label_start` 依 mode 機械定（`close_to_close` ⇒ t₀ close_time；`open_to_*` ⇒ entry 時點）→ 三段鏈檢：PIT 鏈 `observed_through ≤ feature_cutoff[tf] ≤ decision_at ≤ entry_at`；label 鏈 `decision_at ≤ label_start < label_end`；持有鏈 `entry_at < label_end`；`entry_at` 對 `label_start` 無強制順序、`entry_after_label_start` 入收據 → per-TF `feature_cutoff[tf] = max{bar.close_ms ≤ decision_at}`（as-of，非整點邊界不報錯）。
  3. 違反任一不變式 ⇒ 該事件入 `failures{event_id, reason}`（reason＝契約檔 `failure_reasons` 枚舉）；**函式內無任何 silent skip 分支**（每個 drop 必有 reason 列）。
- 修改檔案：新增 `alignment.py`（上列兩函式）；`types.py` 填 `AlignmentConfig/AlignmentReceipts`。既有 caller：無；B1.4/B1.6/B2 消費。
- 不可做：不得用「時間戳剛好相等」對齊（as-of 取列）；不得對失敗事件 `continue` 不記帳；不得在本函式內算特徵；不得讀 HDF5（kline 隔離，吃已載入 bar 表）。
- 邊界：①t₀ 在資料末端（答案窗未完）⇒ `label_window_incomplete`；②缺 bar/亂序/重複 bar ⇒ 各對應枚舉；③`decision_at` 早於資料起點 ⇒ `warmup_insufficient_<tf>`；④非整點 TF 邊界 ⇒ as-of 取列非報錯。
- 風險緩解：RISK-a（look-ahead 之源頭閘）；mutation M1/M2/M9 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q` rc=0（含 §G-2 真實 kline 手算對照：≥3 個 t₀〔12h UTC 整點/非整點邊界/資料末端〕×1h/4h/12h 手算 `feature_cutoff` 與六時間欄，整數 ms `==` 容差 0；`k=0`/`k>0`/`next_open` 三形 exact receipt oracle；各 mode `label_start_ms/label_end_ms` exact；`next_open`×`close_to_close` 斷言 `entry_after_label_start=true` 且三段鏈全過；末端案例預期 `label_window_incomplete`）；記帳守恆 `n_input == n_receipts + n_failures`；**`decision_at ≤ t0_open_ms` 負例（竄改推導使 `decision_at > t0` ⇒ 斷言紅，rc!=0——W11）**；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q WHEN mutation=cutoff_shift_one_bar THEN rc!=0`。
- **存活至**：全票完工後保留；B2 三表與全 K 線驗證之對齊底座。
- **覆蓋風險**：無。

### Task B1.2 — 去重/簇/唯一性權重 manifest（`票 #3`）
- SPEC ref：Task B1.2（K3/C5）　目標：連續觸發與重疊答案窗變成可重現的事件 manifest。
- 輸入/輸出：輸入＝B1.1 `AlignmentReceipts`＋`DedupePolicyConfig`；輸出＝`EventManifest`（table＋summary＋policy provenance）。
- 實作要點：
  1. `momentum/Analysis/event_samples/dedupe.py`：
     ```python
     def build_event_manifest(receipts: AlignmentReceipts,
                              policy_config: DedupePolicyConfig) -> EventManifest: ...
     ```
     `EventManifest.table` 每事件：`observation_interval/label_start/label_end/dedupe_cluster_id/overlap_set_hash/uniqueness_weight`；`EventManifest.summary`：`n_events_raw/n_events_effective/overlap_fraction/sensitivity_flip`。
  2. 簇偽碼：`cluster_gap` 以 **UTC duration**（預設＝答案窗 duration；config 可調）非 row count；區間相交（interval overlap）與跨 symbol 同時刻一併 union-find 成簇；primary policy 事前固定依情境：scenario C ⇒ `cluster_first`（簇首代表＝interval 最早）、A/B ⇒ `all_with_uniqueness`（`w_i = 1/overlap_count` 於 label 窗）。
  3. 另一 policy＝預先登記之敏感度重跑，輸出 `sensitivity_flip: bool`；A/B 全留之顯著性必配 cluster-robust/bootstrap 標記（無修正 raw-all 禁出——下游 B2 讀此標記強制）。
- 修改檔案：新增 `dedupe.py`；`types.py` 填 `DedupePolicyConfig/EventManifest`。既有 caller：無；B1.3/B2 消費。
- 不可做：權重不進 ML 訓練（`UNWIRED_MODULES` 含 `sample_weight`；§N-4）；不得以 row count 當 gap 單位；不得把兩種 policy 都當 confirmatory。
- 邊界：①單事件（無重疊）⇒ weight=1、自成簇；②全部同刻（極端簇）⇒ effective n=1 級；③缺 interval ⇒ fail-closed。
- 風險緩解：RISK-d（重疊樣本膨脹顯著性）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_dedupe.py -q WHEN scenario=C policy=primary THEN rc=0`（斷言簇首代表＝interval 最早——W9/CODEX-R7-P2-09 恢復 SPEC 全文命令）；權重和/簇計數對手算小例 exact。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無（B4 之 GBDT 權重消費列 §N 殘留，不回頭改本 manifest）。

### Task B1.3 — per-symbol 時間切分＋interval-aware purge＋跨標的 time-cluster（`票 #3`）
- SPEC ref：Task B1.3（K4/C6；U12）／[AR-3]　目標：多標的合併樣本的切分與統計單位正確。
- 輸入/輸出：輸入＝B1.2 `EventManifest`＋`EventSplitConfig`；輸出＝`EventSplitPlan`（事件→split 指派＋purge 清單＋cluster 欄＋summary）。
- 實作要點：
  1. `momentum/Analysis/event_samples/event_split.py`：
     ```python
     def split_events(manifest: EventManifest,
                      split_config: EventSplitConfig) -> EventSplitPlan: ...
     ```
     `EventSplitPlan`：`assignments: pd.DataFrame{event_id, symbol, split_label}`、`purged: pd.DataFrame{event_id, reason}`、`clusters: pd.DataFrame{event_id, time_cluster_id, cluster_weight}`、`summary{n_symbols, per_symbol_n, n_time_clusters, avg_cluster_size, degraded[], loso_status}`。
  2. 偽碼：每 symbol 各自按 `decision_at_ms` 時間切（依 ms，禁 positional index）＋train/test 間緩衝 ≥ 答案窗；事件 interval 跨界 ⇒ purge 帶 reason；`time_cluster_id = floor(decision_at_ms / bucket)`（bucket 預設＝觸發 TF 一根）＋`cluster_weight = 1/n_events_in_time_cluster`（primary；bootstrap over clusters＝敏感度）。
  3. 統計 primary＝macro（symbol 等權）、micro（event 等權）＝敏感度，兩者皆輸出且標示；`n_symbols==1` ⇒ `degraded:single_symbol`（exploratory 可跑）；未 cluster 調整 ⇒ `degraded`；跨 symbol 泛化宣稱須 LOSO/held-out-symbol receipt；test 段事件數 < tier 下限 ⇒ loud `insufficient_events_in_test`，**不**回退全樣本。
- 修改檔案：新增 `event_split.py`；`types.py` 填 `EventSplitConfig/EventSplitPlan`。既有 caller：無；**不改 `SplitPlan`**（`momentum/core/contracts.py` row identity 契約另軌）。
- 不可做：不重建 cross-sectional IC、不做 random-effects/GEE、不宣稱關閉 registry #4（§N-5）。
- 邊界：①單 symbol ⇒ 退化為單標的切、macro==micro；②某 symbol 事件全在 train ⇒ 該 symbol 不進 test 統計並報欄；③同刻全 symbol 觸發 ⇒ cluster n=1。
- 風險緩解：RISK-d（跨 symbol 洩漏／positional index 舊坑）；mutation M5/M11 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_event_split.py -q` rc=0；斷言①跨界事件被 purge（手造小例 exact）②禁 positional index（split 依 ms 非列號）③macro/micro 兩統計皆輸出且標示④同 time_cluster 權重和＝1（`atol=1e-12`）。
- **存活至**：全票完工後保留；registry #4 開票時之可複用原語。
- **覆蓋風險**：無。

### Task B1.6 — 特徵物化與決策列選取（`票 #3`；批內順序在 B1.3 後、B1.4 前）
- SPEC ref：Task B1.6（R1 X7）　目標：「全部 K 線連續算特徵、每案例取決策時點那一列」落成有契約的資料路徑，杜絕「每案例固定窗」誤實作。
- 輸入/輸出：輸入＝B1.1 `AlignmentReceipts`＋`bars_by_tf`＋`feature_config`；輸出＝`(features_at_decision: pd.DataFrame, feature_manifest_hash: str, failures: pd.DataFrame)`（W5：failures 通道顯式回傳，reason 枚舉同契約檔，禁 silent drop／NaN 混入）。
- 實作要點：
  1. `momentum/Analysis/event_samples/feature_materialization.py`：
     ```python
     def materialize_features_at_decision(receipts: AlignmentReceipts,
                                          bars_by_tf: dict[str, pd.DataFrame],
                                          feature_config: dict
                                          ) -> tuple[pd.DataFrame, str, pd.DataFrame]: ...
     # 第三元 failures{event_id, reason}；reason 字面＝契約檔 failure_reasons（W5/CODEX-R7-P1-05）
     ```
  2. 偽碼：per-TF **連續**物化（呼叫既有 Feature Factory 入口 `momentum.factories.create_feature_factory()`，不重實作特徵；段長＝全史或 ≥ 最長 lookback＋warmup——結果須與全史算一致）→ 每事件以 `decision_at` per-TF as-of 取列（規則同 D2-1 `max{close_ms ≤ decision_at}`）→ 輸出事件×特徵表。
  3. `feature_manifest_hash = sha256(sorted 特徵名集 + config canonical digest)`（決定性）；per-TF warmup 不足 ⇒ 該事件入失敗枚舉 `warmup_insufficient_<tf>`（非 NaN 混入）；NaN 語意不填 0。
- 修改檔案：新增 `feature_materialization.py`。既有 caller：無；B1.4/B2/B4 特徵輸入唯一來源；Feature Factory 本體不改。
- 不可做：不切「每案例固定 N 根」窗當訓練單位；不在本函式內做特徵選擇；不引入 `shift(-n)` 未來欄。
- 邊界：①事件 `decision_at` 早於 warmup 完成點 ⇒ 入失敗清單非 NaN 混入；②多 TF 特徵欄名衝突 ⇒ loud 拒。
- 風險緩解：RISK-a/d（訓練特徵 look-ahead 之最後一道）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_feature_materialization.py -q` rc=0；①真實 kline「足長段物化」vs「全史物化」同事件列逐值 `atol=1e-12` 一致②因果 invariant：截斷 `decision_at` 之後資料重算，事件列逐值不變（exact）③`feature_manifest_hash` 決定性（同 config 重跑 sha256 相等）④**記帳守恆 `n_input_receipts == n_feature_rows + n_failures`（W5）**。
- **存活至**：全票完工後保留；B2/B4 特徵路徑底座。
- **覆蓋風險**：無。

### Task B1.4 — 單特徵二元 baseline＋自檢 oracle 載體（`票 #3`）
- SPEC ref：Task B1.4（R1 C5-2）　目標：B1 有統計載體可掛 label 置亂與 PIT 後移 oracle。
- 輸入/輸出：輸入＝B1.6 `features_at_decision`（含 `feature_manifest_hash`）＋labels＋B1.3 `EventSplitPlan`；輸出＝report dict（`statistic_kind=binary_discrimination`）。
- 實作要點：
  1. `momentum/Analysis/event_samples/baseline.py`：
     ```python
     def single_feature_binary_baseline(features_at_decision: pd.DataFrame,
                                        labels: pd.Series,
                                        event_split_plan: EventSplitPlan,
                                        *, oracle_config: OracleConfig) -> dict: ...
     ```
  2. 每特徵單獨算 OOS AUC/PR-AUC（test 段 only）＋BH-FDR。
  3. chance-level oracle＝**permutation quantile**：固定 seed、`N_perm=1000`；per `statistic_kind` 以置亂分布 `[q_{0.025}, q_{0.975}]` 為帶（AUC null 中心 0.5、PR-AUC null 中心＝prevalence、IC null 中心 0，皆由置亂分布自然給出）；**三道硬檢**——(i) 分布非退化：`variance > 0` 且 `n_unique_perm_stats > 1`，否則 oracle 自身 FAIL；(ii) 至少一排列 ≠ identity（seed＋排列 digest 寫 receipt）；(iii) 帶判定用經驗分位。oracle 計算核心以 `statistic_kind` 參數化，供 B2.2/B2.3（`conditional_ic`，null 中心 0）直接重用（W3）。
- 修改檔案：新增 `baseline.py`；`types.py` 填 `OracleConfig`。既有 caller：無；B2.2 擴為正式表（共用計算核心）。
- 不可做：不做多特徵組合（B4）；不接 DSR/PBO（AUC 禁直接餵）。
- 邊界：①one-class（test 段單類）⇒ `capability_status=unavailable`；②特徵全 NaN ⇒ loud 拒。
- 風險緩解：RISK-d；mutation M8 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_baseline_oracle.py -q` rc=0；label 置亂（固定 seed）⇒ 全特徵落帶內；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_baseline_oracle.py -q WHEN mutation=pit_shift THEN rc!=0`。
- **存活至**：B2 三表落地後降級為自檢工具（保留不刪）。
- **覆蓋風險**：B2.2 之辨別表為其超集——不刪本 Task 產出（oracle 載體長期保留），故無覆蓋。

### Task B1.5 — 反例自動分類（`票 #3`）
- SPEC ref：Task B1.5（U4；[AR-2]；白話閘①）　目標：`counterexample_kind` 缺值時平台依 t₀ 走勢自動分類 a/b/c，門檻可調。
- 輸入/輸出：輸入＝B1.0 `import_contract.py` 過檢後事件表＋`AlignmentReceipts`＋`bars_by_tf`＋`classifier_config`（讀契約檔 `counterexample_classifier_config`，runtime 可覆寫）；輸出＝derived 欄 DataFrame `{event_id, counterexample_kind_effective, kind_source, platform_suggested_kind}`。
- 實作要點：
  1. `momentum/Analysis/event_samples/counterexample_classifier.py`：
     ```python
     def classify_counterexamples(events: pd.DataFrame, receipts: AlignmentReceipts,
                                  bars_by_tf: dict[str, pd.DataFrame],
                                  classifier_config: dict) -> pd.DataFrame: ...
     ```
  2. 公式（R2 Y2 寫死）：`dir∈{+1(long),−1(short)}`；`R0 = dir·(close_t0−open_t0)/open_t0`；`Rw = dir·(close_labelEnd−close_t0)/close_t0`（錨＝t₀ close 同 D1；aggregation＝label window 末 close）。分類（僅 `label=0` 且 `counterexample_kind` 缺值時執行）：**a**＝`R0 ≥ trigger_threshold ∧ Rw ≤ follow_threshold`；**b**＝`|R0| ≤ range_threshold`；**c**＝`R0 ≤ −drop_threshold`；同時滿足多條 ⇒ `unclassifiable`（不猜）。
  3. 門檻四值（0.05/0.0/0.01/0.05）皆 `example_default` 可調（白話閘①；字面唯一住契約檔）；c 類以舉例預設啟用。使用者已標 ⇒ 不重算不回寫（`kind_source=user`）；user/platform 衝突 ⇒ 保留 user＋`platform_suggested_kind` 留痕。
- 修改檔案：新增 `counterexample_classifier.py`。既有 caller：無；B2 分層報表消費 derived 欄。
- 不可做：不回寫使用者手標欄；不把自動分類當 label（只是報表分層鍵）。
- 邊界：①走勢同時滿足多類 ⇒ `unclassifiable`（不進分層分母）；②答案窗不完整 ⇒ `unclassifiable` 非亂填；③user 有標且 platform 建議不同 ⇒ 主鍵不變、留痕欄出現。
- 風險緩解：RISK-d；mutation M10 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_counterexample_classifier.py -q` rc=0（手造三類小例 exact；boundary fixtures：每門檻取 `=`、`+1e-9`、`−1e-9` 三點落位 exact；conflict case 斷言主鍵保留＋`platform_suggested_kind` 出現；多類邊界 ⇒ `unclassifiable`）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B1 測試（單元/邊界/效能三層）＋Phase Gate
- 單元：7 個 test 檔（見各 Task 驗證欄）手算小例 exact。
- 邊界：空DF/全NaN列/Inf（`nan_or_inf_feature`）/重複·亂序 timestamp/末端截斷/同刻極端簇（§V 邊界目錄歸屬 B1 各項）。
- 效能：B1 無效能斷言（萬級牆鐘屬 B5.1 實測記錄）。
- mutation：`test_mutation_guard.py` 建檔，本批落 M1/M2/M3/M5/M8/M9/M10/M12（fixture 身分與 seed 依 §V 表；sha256 首建記入 `handoffs/run_receipts/gap3_mutation_fixtures.json`）。
- **Gate**：§B B1 Gate 全命令 rc=0 → 三家 code review＋戳記 → 進 B2。

---

## Phase B2 — 三張表＋survivor 契約升版＋全部 K 線驗證
**目標**：統計層與 estimand 全部落地、IC 主線接事件模式而行為不變。完成後系統狀態：三表可跑、survivor v2、`gap3_golden_pre.json` 凍結且 `--check` 綠。

> **B2 全批共同約束（[AR-3] 落地）**：B2.1/B2.2/B2.3/B2.5（及 B4.1）之必需輸入＝B1.3 `event_split_plan`＋cluster manifest；每張表/報告必列 macro primary、micro sensitivity、raw/effective n、cluster CI、`degraded`（含 `degraded:single_symbol`）、LOSO/held-out status；未 cluster 調整 ⇒ **禁 formal pooled inference**。各 Task 驗證含此共同約束斷言（M11 看住）。
> **§G 凍結（B2.3 動工前，順序強制）**：新增 `scripts/gap3_freeze_golden.py`——`import` 復用 `scripts/gap2_freeze_golden.py::gap2_canonical_sha`（唯一序列化實作；scrub 清單＝該檔寫死之 ①`marginal_ic` ②`survivor_output` ③時戳/路徑鍵 ⑤`scope_id` 正規化，**不另立 scrub 清單**）；以 `tests/momentum/helpers/ichc_run.run_analyze()`＋`tests/golden/la0/inputs/` 真實 kline fixture 跑預設 config，`--write` 寫 `handoffs/run_receipts/gap3_golden_pre.json`（fixture sha256＋config_hash＋canonical_sha＋summary_table；獨立 commit）；`--check`＝canonical_sha exact＋`summary_table` 逐鍵 `abs≤1e-12`。B2.3/B2.4/B3.2 各接線後跑 `--check`（§G-1）。

### Task B2.1 — 事件後報酬表（`票 #3`）
- SPEC ref：Task B2.1（K5/C7-i；U1）　目標：事件後多 horizon 報酬分布表；不需反例。
- 輸入/輸出：輸入＝`EventManifest`＋`AlignmentReceipts`＋`bars_by_tf`＋`EventSplitPlan`＋`table_config`（horizon 列表 config 化）；輸出＝report dict（`statistic_kind=event_return`）。
- 實作要點：
  1. `momentum/Analysis/event_samples/tables.py`：
     ```python
     def event_forward_return_table(manifest: EventManifest, receipts: AlignmentReceipts,
                                    bars_by_tf: dict[str, pd.DataFrame],
                                    event_split_plan: EventSplitPlan,
                                    table_config: dict) -> dict: ...
     ```
  2. signed `(exit_h − entry)/entry`（entry＝D1-6 映射表唯一定義；與標籤基準兩數並排＝D1-4）；多 horizon config 化（不寫死 5/10/20/45）；平均/中位/勝率/樣本數。
  3. 分層：direction/scenario/symbol/time/cluster；CI 用 cluster bootstrap/HAC（固定 seed 決定性）；共同約束欄全列（macro/micro/degraded/LOSO）。
- 修改檔案：新增 `tables.py::event_forward_return_table`。既有 caller：無。
- 不可做：不合併三表為總分（禁單一數字混報）。
- 邊界：①horizon 超出資料 ⇒ 該格 `n` 反映排除、不灌 0；②單事件 ⇒ CI `unavailable`。
- 風險緩解：RISK-d。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_tables.py -q -k forward_return` rc=0（手造小例 exact；CI 固定 seed 決定性）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B2.2 — 正反例辨別表（`票 #3`）
- SPEC ref：Task B2.2（K5/C7-ii）　目標：0/1 分得開嗎——OOS only、按反例種類與兩段式腿分層。
- 輸入/輸出：輸入＝OOS scores＋labels＋`EventSplitPlan`＋B1.5 derived 欄＋`table_config`；輸出＝report dict（`statistic_kind=binary_discrimination`）。
- 實作要點：
  1. `tables.py::binary_discrimination_table(scores_oos, labels, event_split_plan, strata, table_config) -> dict`——擴 B1.4 baseline 為正式表，**共用其計算核心**（同一 AUC/permutation 函式，禁重寫）。
  2. 只用 OOS score；AUC/PR-AUC/rank-biserial/prevalence/threshold/confusion/lift。
  3. 按 `counterexample_kind_effective`（derived 欄）a/b/c 與兩段式腿分層；`unclassifiable` 不進分層分母、單獨列 `n_unclassifiable`；one-class ⇒ `unavailable`。
- 修改檔案：`tables.py` 新增函式；`baseline.py` 計算核心抽公用（不改其對外簽名）。既有 caller：B1.4（共用核心）。
- 不可做：AUC 不餵 DSR/PBO；不報 in-sample 分數。
- 邊界：①某 kind 層樣本 0 ⇒ 該層 `unavailable` 非空表；②分層後 one-class 同上。
- 風險緩解：RISK-d；M11 共同約束斷言涵蓋。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_tables.py -q -k discrimination` rc=0；label 置亂 oracle 沿 B1.4。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無（B1.4 不被刪）。

### Task B2.3 — 條件 IC 接線（`票 #3`；動工前先跑 §G 凍結 `--write`）
- SPEC ref：Task B2.3（K5/C7-iii；J7/S3.9；R5 A′）　目標：事件子樣本上跑既有 IC 全流程；label 用連續 `label_value`。
- 輸入/輸出：輸入＝`EventManifest`＋`EventSplitPlan`＋事件 `label_value`；輸出＝IC 報告（既有鍵集＋新增事件欄）。
- 實作要點：
  1. 新增餵入層 `momentum/Analysis/event_samples/ic_feed.py::build_event_ic_inputs(manifest, event_split_plan, events) -> dict`（產 `event_timestamps`＋label 序列＋`sample_scope.kind=event` 標記；純函式）。
  2. `momentum/Analysis/ic_filter_orchestrator.py`（白名單 §0-6-②）：沿**既有 `event_timestamps` 入口**接事件樣本；條件 IC 只吃連續 `label_value`（缺 ⇒ `unavailable:missing_label_value`，**不重算**；y=0/1 不當 return IC）；`statistic_kind=conditional_ic`；stage3/4/5＋A′ fallback 透傳＋one-shot guard **原樣**；既有 stage 語意與既有報告鍵不變。
  3. `label_return_mode ≠ close_to_close` 而沿用主線 label ⇒ 標 `label_price_mismatch=true`；禁以 `decision_at` 列 join 主線 `return_N`（D1-5）。
- 修改檔案：新增 `scripts/gap3_freeze_golden.py`（本 Task 動工前第一步，`--write` 獨立 commit；規格見 Phase B2 前言）；新增 `ic_feed.py`；改 `ic_filter_orchestrator.py`（僅事件入口接線處，函式級 diff 限最小）。既有 caller：IC 三入口（`analyze`/`refilter`/`analyze_full`）。
- 不可做：不改 stage3/4/5 內部；不把 mismatch 語意的主線 `return_N` 靜默當事件 label；v2 survivor 新欄 payload 在 B2.4 升版 commit 前不得寫（`additional_properties:false` 會拒）。
- 邊界：①事件數 < tier 下限 ⇒ 既有 tier 降級語意（U5）；②`label_value` 缺 ⇒ `unavailable:missing_label_value`；③t₀−k 手算案例：label 錨不隨 decision 移動（D1-5）。
- 風險緩解：RISK-b（共用路徑）；§G-1 golden 看住行為不變。
- 驗證：`venv/bin/python -m pytest tests/momentum/ -q -k "gap3 and conditional_ic"` rc=0；**conditional-IC 置亂 oracle（W3/CODEX-R7-P1-03＝§G-3(i) 落地）：label_value 置亂（固定 seed）⇒ 條件 IC 落 permutation quantile 帶內（共用 B1.4 oracle 計算核心，null 中心 0、`N_perm=1000`、經驗分位；`statistic_kind=conditional_ic`），`venv/bin/python -m pytest tests/momentum/event_samples/test_baseline_oracle.py -q -k conditional_ic` rc=0**；`venv/bin/python scripts/gap3_freeze_golden.py --check` rc=0（§G-1 行為不變 exact）；A′ fallback 案例斷言 `event_timestamps` 透傳＋`degraded` 標示。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B2.4 — `ic_survivor_contract` v2 升版（`票 #3`）
- SPEC ref：Task B2.4（R1 C4）　目標：事件型倖存者可被下游安全消費。
- 輸入/輸出：輸入＝v1 契約＋B2.3 事件欄需求；輸出＝`ic_survivor_contract.json` version 2＋同步 validator/consumer/golden。
- 實作要點：
  1. `momentum/Analysis/contracts/ic_survivor_contract.json` version 1→2：event object 擴 `event_manifest_hash/label_definition_hash/decision_time_rule/feature_cutoff_rule/label_window_rule/control_kind`（字面唯一住契約檔）。〔本列舉＝genesis 升版規格；v2 檔落地後以契約檔為準、本列不再維護——W1〕
  2. `momentum/Analysis/survivor_contract.py`（實際路徑，非 contracts/ 下）validator/consumer 同步：顯式版本判別——v1 舊檔讀舊版或拒，**禁 silent coerce**；v2 新欄缺 ⇒ 拒。
  3. golden 同步＋`fallback_requested_scope`/`degraded` 保留；升版獨立 commit，B2.3 餵入層自此 commit 後才寫新欄 payload。
- 修改檔案：`ic_survivor_contract.json`＋`momentum/Analysis/survivor_contract.py`（白名單 §0-6-①）。既有 caller：GAP-2b 契約消費側（現唯讀）。
- 不可做：不動 GAP-2 既有 v1 欄語意；不在文件/程式複列鍵表。
- 邊界：①v1 舊檔 ⇒ 顯式版本判別（讀舊版或拒）；②新欄缺 ⇒ 拒。
- 風險緩解：RISK-b（契約升版影響 validator/consumer/golden）。
- 驗證：`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0（v2 鍵集斷言；v1 檔案讀入之相容/拒絕行為斷言）；`gap3_freeze_golden.py --check` rc=0（升版不動序列型行為）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B2.5 — 全部 K 線驗證 evaluator（`票 #3`）
- SPEC ref：Task B2.5（K8/C4＝D4；U11）　目標：整票靈魂的機器形——固定分母＋基率並排＋lift。
- 輸入/輸出：輸入＝`model_scores_or_rule`（每 bar score 序列或規則 callable）＋`bars`＋`manifest_config`；輸出＝report dict＋落檔 evaluation manifest（可審計）。
- 實作要點：
  1. `momentum/Analysis/event_samples/all_bars_eval.py`：
     ```python
     def evaluate_all_bars(model_scores_or_rule, bars: dict[str, pd.DataFrame],
                          manifest_config: dict) -> dict: ...
     ```
  2. D4 全文為規格：manifest 以 `decision_at` 為索引、只納 `eligible`（答案窗完整/資料連續/價格有效/PIT 合法）；報 `n_total/n_eligible/n_labeled/n_unknown/n_tail_excluded/n_missing`＋reason；輸出 precision/recall/F1/PR 曲線＋AUC/PR-AUC/lift（top-q%＋固定閾值）/confusion/訊號頻率/signed 持有報酬（實際進場價→答案窗末 close，與 D1-4 並排）；按 symbol/direction/`counterexample_kind_effective`/時間段分層＋CI（列 `n_unclassifiable`）。
  3. `prevalence_learn` 與 `prevalence_full` 必並排＋`sample_design=case_control`＋lift；缺任一 ⇒ `unavailable:missing_prevalence_disclosure`；與序列型全 bar IC 並排（J7-4）；多組條件同時命中 ⇒ 保留多標籤（`event_id/label_id`）或契約明定 precedence，禁默默覆蓋。
- 修改檔案：新增 `all_bars_eval.py`。既有 caller：無；B3.2 G6 與 B4 消費。
- 不可做：D4-4 清單（倉位/手續費/滑價/複利/資金曲線/turnover/capacity/triple-barrier/long-short）一律不做。
- 邊界：①資料末端 bars ⇒ `n_tail_excluded` 記帳；②多組條件同時命中 ⇒ 多標籤保留或明定 precedence。
- 風險緩解：RISK-a/d（固定分母＝case-control 誤讀之解）；mutation M4/M7 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py -q` rc=0；真實 kline 小段手算分母 exact；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py -q WHEN mutation=ineligible_in_denominator THEN rc!=0`；缺基率欄 ⇒ `unavailable:missing_prevalence_disclosure`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B2 測試（單元/邊界/效能三層）＋Phase Gate
- 單元：三表手算小例 exact＋survivor v2 契約斷言；整合：真實 kline 端到端 B1→B2。
- 邊界：單類別（B2.2）/末端截斷（B2.5）/tier 降級（B2.3）。
- 效能：無新斷言（§G-1 `--check` 本身秒級）。
- mutation：本批落 M4/M7/M11。
- **Gate**：§B B2 Gate 全命令 rc=0 → 三家 code review＋戳記 → 進 B3。

---

## Phase B3 — 完整版事件產生器＋變化類特徵
**目標**：降低手工標註成本——條件引擎、`/search`/`event_filter` adapter、state-counter 算子。完成後系統狀態：G1–G6 逐項可驗，`platform_same_trigger_rule` 控制組可產出並過 B1.0 validator。

### Task B3.1 — 條件引擎純函式（`票 #3`）
- SPEC ref：Task B3.1（K9/C3＝D3）　目標：typed AST＋欄位角色＋digest 的事件產生核心。
- 輸入/輸出：輸入＝條件式字串＋欄位角色 registry；輸出＝`ConditionSpec`（AST＋canonical digest＋角色清單＋max lookback）＋布林遮罩。
- 實作要點：
  1. `momentum/Analysis/event_samples/condition_engine.py`：
     ```python
     ExpressionRole = Literal["feature", "selection_predicate", "label"]  # W6：role 為輸入之一
     @dataclass(frozen=True)
     class ConditionSpec:  # ast/canonical_digest/column_roles/max_lookback/label_ids/expression_role
     def parse_condition(expression: str, column_registry: dict[str, str],
                         expression_role: ExpressionRole) -> ConditionSpec: ...
     def evaluate_condition(spec: ConditionSpec, df: pd.DataFrame) -> pd.Series: ...
     # role-aware 檢查在 parse 期：expression_role='feature' 引用 future_*/trigger_outcome 欄 ⇒ 拒；
     # 'selection_predicate' 放行未來欄但 spec.column_roles 全記錄、只進抽樣 provenance（W6/CODEX-R7-P1-06）
     ```
  2. safe-subset AST：僅已註冊欄位＋比較/布林/區間/缺值運算（白名單 node 型別，其餘拒）；canonical digest＝AST 正規化後 sha256（同式異白/排序 ⇒ 同 digest）。
  3. 角色隔離（D3）：欄位角色 `∈ {pit_feature, trigger_outcome, future_outcome}`；`feature` 角色引用 `future_*`/`trigger_outcome` 欄 ⇒ 拒；`selection_predicate` 可含未來欄但只進抽樣 provenance；多組 label 用 `label_id` manifest（非布林覆寫）；去重在產生期（G4）；輸出事件過 B1.0 validator（G5）。
- 修改檔案：新增 `condition_engine.py`。既有 caller：無；B3.2 adapter 消費。
- 不可做：不得以 `df.eval` 任意字串為核心；不得讓 `selection_predicate` 欄流入特徵表（D3-4）。
- 邊界：①未註冊欄位 ⇒ 拒；②表達式空/恆真 ⇒ loud；③digest 決定性（同式異白排序 ⇒ 同 digest）。
- 風險緩解：RISK-a（選樣看答案、特徵不可）；mutation M6 歸屬本 Task。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_condition_engine.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_condition_engine.py -q WHEN expression_role=feature column=future_return THEN rc!=0`；**雙案例（W6）：①`parse_condition(expr含future_return, registry, expression_role='selection_predicate')` 成功且 `column_roles` 記錄該欄為 `future_outcome`②同式 `expression_role='feature'` ⇒ 拒（兩案例同一表達式，只差 role）**。
- **存活至**：全票完工後保留；IC 事件遮罩之長期底層（J10）。
- **覆蓋風險**：無。

### Task B3.2 — `/search` 與 `event_filter` adapter（`票 #3`）
- SPEC ref：Task B3.2（U6/G1–G6；U7）　目標：產生器能力全開；一鍵產合規事件檔；同引擎做全 K 線標籤重算。
- 輸入/輸出：輸入＝`ConditionSpec`＋bars＋label 設定；輸出＝合規事件 DataFrame（過 B1.0 validator）＋provenance。
- 實作要點：
  1. 新增 `momentum/Analysis/event_samples/generator.py::generate_events(spec, bars_by_tf, label_config, gen_config) -> tuple[pd.DataFrame, dict]`（G1 任意 FF 特徵＋t₀ 結果＋未來結果欄觸發；G2 多組 label 一次設定 `label_id` manifest；G3 方向/情境/答案窗/規則摘要自動存；G4 去重回報原始/去重後數；G5 輸出過 B1.0 validator）。
  2. `momentum/Analysis/event_filter.py`（白名單 §0-6-③）掛薄 adapter：既有遮罩語意不變；legacy `df.eval` 路徑保留為既有遮罩 adapter；未通過角色隔離 receipt 前不得宣稱「已共用完整引擎」；`allowed_filtering_params={'price_change'}` 改為契約化允許清單（D3-3）。
  3. G6＝**呼叫 B2.5 `evaluate_all_bars` 做全 K 線標籤重算，禁平行實作**；`control_kind=platform_same_trigger_rule` 控制組自本 Task 啟用——產出過**同一** B1.0 validator（無 profile 分裂）。
- 修改檔案：新增 `generator.py`；改 `event_filter.py`（adapter 掛載處）。既有 caller：IC 事件遮罩既有 caller（§G-1 看住）；`/search` 後端 API 接線在 B5。
- 不可做：未過角色隔離 receipt 前不宣稱共用完整引擎；不動 `/search` 前端（B5）。
- 邊界：①條件命中 0 事件 ⇒ loud 空結果非錯；②既有 `event_filter` query 路徑行為不變斷言。
- 風險緩解：RISK-b；§G-1 `--check` 於本 Task 後複跑。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_generator_adapters.py -q` rc=0，G1–G6 逐項斷言（G1 含十類中 ①②③⑩ 代表案例各一）；`platform_same_trigger_rule` 產出過 validator＋`control_kind` 正確標記；`gap3_freeze_golden.py --check` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B3.3 — 變化類特徵算子（`票 #3`）
- SPEC ref：Task B3.3（K7/C8）　目標：補 `bars_since_cross/consecutive_run/bars_since_threshold/window_max_ratio/cross_count`；已有算子不重做。
- 輸入/輸出：輸入＝價格/特徵序列＋lookback 參數；輸出＝五個算子欄＋`max_lookback/warmup/as-of` 中繼資料。
- 實作要點：
  1. 新增 `momentum/FeatureEngineering/operators/state_counters.py`（落點寫死，不擴 `derived_operators.py`）。五算子精確語意（W7/CODEX-R7-P1-07；TODO 階段細化——SPEC 只命名算子未定公式；全部只看閉區間 `[t−lookback+1, t]`、含當前根 t；「交叉」定義＝`d_i = a_i − b_i` 之嚴格變號：`sign(d_i) ≠ sign(d_{i−1})` 且兩者皆非 NaN 非 0；`d=0` 不計交叉）：
     - `def bars_since_cross(series_a: pd.Series, series_b: pd.Series, lookback: int) -> pd.Series`：t 減窗內最近一次交叉的 bar index；交叉發生在當前根 ⇒ 0；窗內無交叉 ⇒ NaN。
     - `def consecutive_run(series: pd.Series, lookback: int) -> pd.Series`：以 t 結尾、`sign(series)` 連續同號（嚴格 >0 或 <0）之 run 長度（含 t），上限 lookback；`series_t==0` 或 NaN ⇒ NaN。
     - `def bars_since_threshold(series: pd.Series, threshold: float, lookback: int) -> pd.Series`：t 減窗內最近一次「上穿」（`series_{i−1} < threshold ≤ series_i`）的 bar index；窗內無上穿 ⇒ NaN。
     - `def window_max_ratio(series: pd.Series, lookback: int) -> pd.Series`：`series_t / rolling_max(series, lookback)_t`（分母含當前根）；分母 ≤0 或 NaN ⇒ NaN。
     - `def cross_count(series_a: pd.Series, series_b: pd.Series, lookback: int) -> pd.Series`：窗內交叉（同上定義）次數；無 ⇒ 0（計數語意，非狀態語意，故 0 合法）。
  2. NaN 語意明定不填 0；除 `cross_count` 外「窗內無事件」一律 NaN（非哨兵 0）；warmup 不足 ⇒ NaN 前綴；每算子附 ≥1 個 exact expected case（手算序列寫死於測試）。
  3. `operator_registry` 註冊（既有 `ts_argmax/ts_argmin/slope` 等不動）；過 Feature Factory 因果/golden 紀律（三方數據正確性簽核鐵律適用——本 Task 之 review 須含 explicit adversarial 獵漏）。
- 修改檔案：新增 `state_counters.py`；改 `operator_registry`（僅註冊行）。既有 caller：Feature Factory pipeline。
- 不可做：不重做已存在算子；不引入跨列未來資訊（`shift(-n)` 禁）。
- 邊界：①窗內無交叉/事件 ⇒ NaN（`cross_count` 例外＝0，計數語意——W7 定義）；②warmup 不足 ⇒ NaN 前綴。
- 風險緩解：RISK-a（Feature Factory 因果紀律）。
- 驗證：`venv/bin/python -m pytest tests/momentum/feature_engineering/ -q -k state_counters` rc=0（手算小例 exact——每算子 ≥1 個寫死序列 expected；因果測試：截斷未來資料結果不變）。**測試落點＝新建目錄 `tests/momentum/feature_engineering/test_state_counters.py`（W14 裁決：該目錄現不存在、FF 既有測試在 `tests/feature_engineering/`；新建使 SPEC 命令字面可跑、不動既有，免 SPEC amendment）**。
- **存活至**：全票完工後保留（Feature Factory 永久算子）。
- **覆蓋風險**：無。

### Phase B3 測試＋Phase Gate
- 單元：AST/digest/角色/五算子手算 exact；整合：generator→validator→evaluate_all_bars 鏈。
- 邊界：0 事件/未註冊欄/恆真式/無交叉窗。
- mutation：本批落 M6。
- **Gate**：§B B3 Gate 全命令 rc=0 → 三家 code review＋戳記 → 進 B4。

---

## Phase B4 — pattern＋DSR/PBO 橋
**目標**：學習段找多特徵組合、訊號轉 return series 接 GAP-1 統計防線。完成後系統狀態：candidate ledger 可審計、AUC 誤餵 DSR 被機械拒絕。

### Task B4.1 — pattern 抽取（`票 #3`）
- SPEC ref：Task B4.1（J8）　目標：在學習段找多特徵組合 pattern；ML 殼不動。
- 輸入/輸出：輸入＝B1 manifest＋B1.6 特徵表＋B2.4 survivor v2＋`EventSplitPlan`；輸出＝pattern report（train 段擬合、test 段分數）。
- 實作要點：
  1. 新增 `momentum/Analysis/event_samples/pattern_bridge.py::extract_event_patterns(features_at_decision, labels, event_split_plan, survivor_v2, bridge_config) -> dict`——消費既有 `momentum/Analysis/pattern_extractor.py`／GBDT 分析器之**消費側**新函式；**禁改 `xgboost_batch_service` 訓練殼、禁改 `pattern_extractor.py` 既有簽名**。
  2. 訓練只在事件樣本 train 段；score 只在 test 段報；train fail-closed（split 缺 ⇒ 拒，不 fallback 全樣本）。
  3. 引擎 LightGBM/XGBoost 之選不影響契約（U8）；必需輸入含 `event_split_plan`＋cluster manifest；報告列 macro/micro/`degraded`/LOSO status（[AR-3] 共同約束）；特徵數 > 樣本可撐 ⇒ 依 IC 粗篩先行（J8）。
- 修改檔案：新增 `pattern_bridge.py`。既有 caller：無。
- 不可做：不動 ML 殼；`sample_weight` 不接訓練（§N-4）；不在全樣本 fit。
- 邊界：①特徵數 > 樣本可撐 ⇒ IC 粗篩先行；②test 段 one-class ⇒ `unavailable`。
- 風險緩解：RISK-d；置亂 oracle 沿用。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_pattern_bridge.py -q` rc=0（train/test 隔離斷言；置亂 oracle 沿用）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B4.2 — 規則 → return series → candidate ledger → DSR/PBO（`票 #3`）
- SPEC ref：Task B4.2（K6/C7；GAP-1 對接）　目標：規則/訊號以同 entry/exit 語意轉 OOS return series，接 GAP-1 DSR/PBO/MinBTL。
- 輸入/輸出：輸入＝pattern/規則＋bars＋entry 語意；輸出＝candidate ledger（provenance 完整）＋DSR/PBO 報告。
- 實作要點：
  1. 新增 `momentum/Analysis/event_samples/candidate_ledger.py`：
     ```python
     def record_candidate(ledger_path, candidate_meta) -> None        # provenance：規則 digest/seed/輸入 digest
     def to_return_series(rule_or_scores, bars, entry_semantic,
                          label_definition: dict,        # W8：window+label_return_mode ⇒ 退出時點唯一決定
                          receipts: AlignmentReceipts    # W8：entry_at/label_end 從對齊收據取，禁自行推導
                          ) -> pd.Series
     # entry＝D1-6 映射（entry_price_source）；exit＝答案窗末 close（label_end；D1-4 持有鏈），horizon 由
     # label_definition.window 唯一決定——禁把事件標籤報酬/實際進場報酬混用（W8/CODEX-R7-P1-08）
     def run_dsr_pbo(ledger_path, returns_by_candidate) -> dict
     ```
  2. 消費 `momentum/Analysis/strategy_validation/{pbo.py, min_btl.py}`（不改其簽名）；`n_trials` **從 ledger 讀**，禁 request 任意填。
  3. AUC/PR-AUC/rank-biserial **不**直接餵 return-based DSR/PBO（型別/metric 檢查機械拒）；每 oracle 記命令/seed/輸入 digest/預期 fail-pass。
- 修改檔案：新增 `candidate_ledger.py`。既有 caller：GAP-1 產物（唯讀消費）。
- 不可做：不為 AUC 自創 MinBTL 數字；不跳過 ledger 直餵。
- 邊界：①ledger 空 ⇒ DSR/PBO `unavailable`；②return series 長度不足 MinBTL 前提 ⇒ loud。
- 風險緩解：RISK-d（多重測試防線）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q WHEN input_metric=auc target=dsr THEN rc!=0`；**entry×exit 一致性（W8）：對 D1-6 五種 `entry_price_semantic` 各一手算案例，斷言 return series 之 entry 取 `entry_price_source`、exit 取 `label_end` close，逐值 exact**。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B4 測試＋Phase Gate
- 單元：ledger provenance/return series 手算 exact；隔離斷言。
- 邊界：空 ledger/長度不足/one-class。
- **Gate**：§B B4 Gate rc=0 → 三家 code review＋戳記 → 進 B5。

---

## Phase B5 — 持久化/API/前端/UAT
**目標**：新 schema 上線、三頁升級、整票 UAT。完成後系統狀態：epic 可收案。

### Task B5.1 — API 接線＋legacy adapter（`票 #3`）
- SPEC ref：Task B5.1　目標：匯入新 schema 上線；舊路徑顯式處置。
- 輸入/輸出：輸入＝HTTP 匯入請求（CSV/JSON）；輸出＝驗證結果/錯誤明細 response（拒絕走 4xx＋逐列 reason）。
- 實作要點：
  1. `api/models/`＋`api/routes/case*`＋`api/services/case_import_service.py`（白名單 §0-6-⑤）：request/response 殼只透傳，**驗證唯一實作在 `momentum/Analysis/event_samples/import_contract.py`**（R7；API 層不得重複實作檢查）。
  2. factories 出口（SPEC §RISK 末行「TODO 階段定簽名」）：`momentum/factories.py` 新增
     ```python
     def create_event_sample_pipeline() -> EventSamplePipeline: ...
     ```
     `EventSamplePipeline`＝`event_samples/pipeline.py` 之組合殼（validate→align→dedupe→split→materialize；服務端唯一消費入口）。
  3. `/case/import` 舊格式 ⇒ legacy adapter：顯式 migration 提示或拒絕，禁 silent coerce；舊 `cases.json` 不遷移；批次抓 K 線概念保留（lookback＋forward＋warmup；多 TF 已支援 [FACT-RECEIPT]）。
- 修改檔案：`api/models/`（新 request/response 殼）＋`api/routes/case*`＋`api/services/case_import_service.py`＋`momentum/factories.py`（一個出口）＋新增 `event_samples/pipeline.py`。既有 caller：`/case/import` 前端呼叫端。
- 不可做：不改 `xgboost_batch_service`；API 層不重複實作契約檢查。
- 邊界：①混合新舊欄 CSV ⇒ 拒＋指出缺欄；②大檔（萬級事件）⇒ 分頁/串流處理；**驗收形（W10/CODEX-R7-P2-11，不捏門檻）：本 Task 前置＝偵察待辦 T-3 完成定 workload；驗收＝實測 receipt `handoffs/run_receipts/gap3_import_scale.json` 存在且含 `{n_events≥10000, wall_clock_s, peak_rss_mb}` 三欄（記錄型可證偽）；效能門檻若需，偵察後另走 SPEC amendment，TODO 不私定數值**。
- 風險緩解：RISK-b。
- 驗證：`venv/bin/python -m pytest tests/api/ -q -k gap3_import` rc=0（新 schema 過、舊格式得顯式錯誤訊息、無靜默轉換）；規模 receipt 檔存在＋三欄齊（W10）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B5.2 — 前端三頁升級（`票 #3`）
- SPEC ref：Task B5.2（U10；U7）　目標：產/匯入在 `/search`＋`/data-preparation`；分析在 `/ic-analysis` 加事件模式；事件型獨有兩表只在事件模式顯示。
- 輸入/輸出：輸入＝後端事件 API；輸出＝三頁升級後 UI（功能殼＋兩張新表）。
- 實作要點：
  1. `frontend/src/` 三頁升級不翻掉（U7）：`/ic-analysis` 加事件模式切換＋「從已匯入案例選事件」入口（S3.9-5）；既有圖表全共用（九成可用——J7）。
  2. 兩張新表（事件後報酬表/辨別表）僅事件模式顯示；後端 `unavailable` reason ⇒ 前端顯示原因非空白；empty/loading/error 三態齊。
  3. 第一版＝功能殼＋兩表；vitest 對 registry 防漂移沿既有 `pendingFeatures` 機制；typed props/Zustand/`<ResponsiveContainer>`。
- 修改檔案：`frontend/src/`（`/search`、`/data-preparation`、`/ic-analysis` 三頁對應元件＋store＋`lib/types.ts`）。既有 caller：既有頁面路由。
- 不可做：不另開分析頁（兩份殼——U10）；前端不重算任何統計。
- 邊界：①未匯入任何事件 ⇒ 事件模式入口 empty state；②後端 `unavailable` ⇒ 顯示 reason。
- 風險緩解：RISK-b（全棧 wiring：後端/前端/接線三欄齊查）。
- 驗證：`cd frontend && npm run build` rc=0；**vitest（W9/CODEX-R7-P2-10）：測試檔命名規約 `frontend/src/**/gap3_*.test.{ts,tsx}`（≥3 檔：事件模式入口/兩表渲染/`unavailable`+empty state），命令 `cd frontend && npx vitest run gap3` rc=0（vitest 檔名子串過濾；`package.json` 既有 `"test": "vitest run"`）**。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task B5.3 — UAT＋收尾（`票 #3`）
- SPEC ref：Task B5.3　目標：整票 UAT＋白話看板更新、殘留登記 registry、HANDOFF/ROADMAP 同步。
- 輸入/輸出：輸入＝B1–B5 全部產出；輸出＝UAT checklist 檔（逐項實跑命令＋rc）＋文件同步 commit。
- 實作要點：
  1. UAT 腳本走真實流程：匯入 → 對齊 → 三表 → 全 K 線 → 報告（真實 kline）；**checklist 檔＝`docs/GAP3_UAT_CHECKLIST.md`（本 Task 產出；逐項＝步驟＋實跑命令＋rc＋預期畫面/輸出；使用者簽字欄——W9/CODEX-R7-P2-10）**。
  2. 殘留逐條入 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」（§N 8 條三值理由已登記，UAT 後補新增項）；白話看板更新（`白話說明/`）；HANDOFF/ROADMAP 同步。
  3. UAT 發現缺陷 ⇒ 回對應批修，不在 B5 打補丁繞過。
- 修改檔案：`白話說明/`＋`docs/IC_QUANT_GAP_REGISTRY.md`＋`HANDOFF.md`＋`docs/ROADMAP.md`；新增 `docs/GAP3_UAT_CHECKLIST.md`（W9）。既有 caller：無程式面。
- 不可做：不以 UAT 遮蔽 B1–B4 未驗收項（C9）。
- 邊界：①UAT 缺陷 ⇒ 回批修；②使用者未簽字 ⇒ epic 不收案。
- 風險緩解：⊘（流程項）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/ -q` rc=0＋`cd frontend && npm run build` rc=0＋`bash scripts/plain_docs_sync_check.sh` rc=0；UAT checklist 檔逐項附實跑命令與 rc，使用者驗收簽字。
- **存活至**：epic CLOSED。
- **覆蓋風險**：無。

### Phase B5 測試＋Phase Gate
- 整合：API 端到端＋前端 build＋vitest；效能：萬級事件匯入牆鐘實測記錄（B5.1 邊界②）。
- **Gate**：§B B5 Gate 全命令 rc=0＋使用者 UAT 簽字 ⇒ epic 收案。

---

## §V mutation 目錄（自 SPEC §V **逐字抄錄、不得增刪**；歸屬：B1＝M1/M2/M3/M5/M8/M9/M10/M12，B2＝M4/M7/M11，B3＝M6）

- **mutation 條件**：RISK-HIT 含 a,d ⇒ 附可證偽/mutation 設計（引 `docs/TEST_DESIGN_CHARTER.md`）。最小 mutation 集（R1 X8＋R2 Y4 逐條可執行化）：**統一命令**＝`venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M<n>`；**fixture 身分**＝M1/M2/M4/M9 用真實 kline `tests/golden/la0/inputs/` 既有 fixture＋固定事件表（seed 20260820）、M3/M5–M8/M10–M12 用合成事件表（seed 20260820＋M 序號；章程 §F 合法——合成的是事件/label 序列非價格）；fixture sha256 於首次建立記入 `handoffs/run_receipts/gap3_mutation_fixtures.json`（**誠實邊界**：SPEC 無法預寫尚不存在檔案之 digest——那是 receipt 非規格）；**TODO 逐字抄本表、不得增刪**。每條=「baseline 預期＋mutation diff＋預期 rc」：
  - M1 失敗記帳被吞：baseline＝`align_events` 對每個 dropped 事件寫 reason 入 `failures`；mutation＝drop 但不寫 reason（`n_dropped_by_reason` 總數 < 實際 drop 數）⇒ `test_alignment.py` 記帳守恆斷言（`n_input == n_receipts + n_failures`）紅，rc!=0。
  - M2 PIT 後移（跨 TF 可重現形）：mutation＝`feature_cutoff[tf]` 改選「`decision_at` 之後**下一實際 TF bar**」⇒ §G-3(ii) oracle（比對手算 receipt exact）紅，rc!=0。
  - M3 ms 單位閘移除：mutation＝刪量級檢查 ⇒ 秒級 `t0` 測資通過匯入 ⇒ `test_import_contract.py` 拒收斷言紅，rc!=0。
  - M4 分母竄改：mutation＝`evaluate_all_bars` 把 `label_window_incomplete` bars 計入 `n_eligible` ⇒ 真實 kline 小段手算分母 exact 斷言紅，rc!=0。
  - M5 權重歸一：mutation＝`cluster_weight` 全設 1（棄 `1/n_events_in_time_cluster`——X9 公式）⇒ B1.3 同簇權重和＝1（`atol=1e-12`）斷言紅，rc!=0。
  - M6 角色隔離移除：mutation＝condition_engine 允許 `future_*` 欄過 `feature` 角色 ⇒ B3.1 ASSERT（`WHEN expression_role=feature column=future_return THEN rc!=0`）反轉＝測試紅。
  - M7 基率欄移除 ⇒ B2.5 `unavailable:missing_prevalence_disclosure` 斷言紅，rc!=0。
  - M8 置亂 oracle 空心防護（R2 Y5／R3 Z4 定式）：baseline＝固定 seed 置亂 label 後，各 `statistic_kind` 觀測值落 **permutation quantile 帶**（B1.4 定式：`N_perm=1000`＋三道硬檢——非退化 `variance>0`／`n_unique>1`、非恆等斷言、經驗分位）；mutation＝把置亂改為恆等排列 ⇒ 非退化與非恆等硬檢**必觸發** ⇒ 紅，rc!=0（「觀測值∈觀測值」假綠路徑已封死）。
  - M9 offset 推導竄改：mutation＝`decision_at_ms` 推導 k 改 k−1 ⇒ §G-2 k>0 exact receipt oracle 紅，rc!=0（R1 X1）。
  - M10 分類猜測：mutation＝多類邊界從 `unclassifiable` 改取 precedence 猜一類 ⇒ B1.5 邊界案例斷言紅，rc!=0（R1 X4）。
  - M11 `degraded` 標記移除：mutation＝單 symbol 或未 cluster 調整時不標 `degraded` ⇒ B1.3/B2 共同約束斷言紅，rc!=0（R1 X6）。
  - M12 T9 availability 檢查移除：mutation＝`available_at > decision_at` 仍收 ⇒ B1.0 條件必填斷言紅，rc!=0（R1 X5）。

## §T 追溯與偵察待辦

- 追溯基準：`handoffs/20260820-gap3-todo-stage1-index.md`（20 Task ↔ 本檔 20 Task；26 驗證項全數入各 Task 驗證欄；§G 6 項入 B1.1/B2 前置/各 Gate；M1–M12 逐字抄於上節；殘留 8 條不屬 TODO scope——已登記 registry）。
- 偵察待辦（SPEC §V 末；TODO 執行中補、不阻凍結）：T-1 外部源現有程式面；T-2 Feature Factory 多 TF as-of 工具現況（B1.6 動工前查）；T-3 萬級事件 bootstrap 牆鐘；T-4 `two_stage_search` 欄位對照全表（B3.2 動工前查）。
- estimand 隔離（SPEC §V）：`statistic_kind ∈ {event_return, binary_discrimination, conditional_ic}` 三值分節、禁合併總分；capability 枚舉沿 `ic_report_contract.json`（ref，不重定義）。

## §N N/A 登記

本 TODO 無省略之範本必填段（§0/§B/20 Task 五欄/Phase 測試/Gate 全實填）。殘留 8 條屬 SPEC §N，已登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」，本 TODO 不重複列。
