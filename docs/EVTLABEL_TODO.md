# EVTLABEL — TODO

**SPEC**：`docs/EVTLABEL_SPEC.md`　**票**：`EVTLABEL`　**日期**：2026-09-10　**狀態**：DRAFT v2（R1 三家 27 條已收斂 C1–C14，`handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`；待 R2 閉合輪）
**實作端**：Claude 主委自任（`scripts/governance_roles.json` implementer=claude）；review＝codex＋composer＋grok。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **解耦**：`momentum/` 不 import `api/`（R1）。新統計模組 `momentum/Analysis/binary_discrimination.py` 只吃 DataFrame/ndarray；service 只組參數、不算統計。service 不互 import（R4）。
- **Logging**：`get_logger(__name__)`；Task 3.5 逐欄迴圈與 3.7 置換迴圈內**不得** log。
- **Error 分類**：label 錯位／缺值／單類（顯式 binary 模式下）＝non-retryable，`AlignmentViolationError`／`ValueError` 明確 raise；`auto` 模式條件不足＝**降級揭露**（`label_mode.reason`），不 raise。
- **不可違反原則**：不弱化 NaN/inf 閘（3.4 ②、3.5 ⑤）；不擅改輸出大小（summary_table 只**加**欄；全域與 `return_rule` 報告逐位元組不變＝G-1／G-4）；禁合成價格 fixture。
- **manifest ID**：`[A-1]`＝SPEC `ASSUME-1`（spec bytes＝實際套用 spec；B1 先跑）；`[A-2]`＝`ASSUME-2`（MW 向量化耗時；B4 先跑）；`[A-3]`＝`ASSUME-3`（`validate_event_given` 吃 0/1；B4 先跑）。
- **防假綠**：既有斷言只允許 Task 2.3 列出的 isolation 語意更新，diff 附本檔 B2 段；驗收讀 pytest 自己的 summary 行；`pytest tests/governance` 小時級**不跑**。
- **主目標守則**：SPEC §A 使用者原話；任何審查提議把 P3 延後 ⇒ 主委 AskUserQuestion 彈窗，不自行接受。
- **兩注入點同改**：`api/services/ic_analysis_service.py` `:1296-1302`（掃描格）與 `:1578-1585`（主路徑）。
- **每批收尾**：commit → 背景 push → 更新 `白話說明/現在做到哪.md` → `bash scripts/agent_postflight.sh`。

---

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B0** | 0.1 | 無 | Phase gate 腳本＋mutate 腳本＋placeholder 測試（skip≠綠） | 小 |
| **B1** | 1.1, 1.2, 1.3 | B0 | P1 整段（後端揭露＋前端兩處）；`[A-1]` 於 1.1 驗證①先跑 | 小 |
| **B2** | 2.1, 2.2, 2.3 | B1（`label_window_feature_bars` 計算式共用） | P2 整段；G-2 前後對照同批 | 中 |
| **B3** | 3.1, 3.2, 3.3 | B2 | 契約＋請求＋staging（資料進得來，尚無統計） | 中 |
| **B4** | 3.4, 3.5, 3.6, 3.7 | B3 | orchestrator 核心（mode 決策→綁定→統計→門檻→依賴感知自檢）；`[A-2]`、`[A-3]` 先跑；G-6 golden 於本批動工前凍結 | 大 |
| **B5** | 3.8, 3.9 | B4 | 倖存者輸出（含 suppressed）＋前端（依 B4 定案之欄名） | 中 |
| **B6** | 3.10, 3.11 | B5 | 真實 kline 端到端＋三方簽核 oracle＋ML consumer 契約 | 中 |

- **批次間 Gate**：`bash scripts/evtlabel_phase_gate.sh <0|1|2|3a|3b|3c>` rc=0（skip 不算通過；空 golden glob 不算通過；mutate UNCOVERED=0）。每批完成後三家 code review（`committee_run.sh`），quorum 由 `review_quorum_check.sh` 機檢，不足不派下一批。
- **派工 prompt（主委自任，以本檔該批 Task 為 brief）**：前置狀態＝上一批 gate rc=0＋review 收斂；Task 列表＝該批；驗證命令＝各 Task「驗證」欄。

---

## Phase 0 — 前置（完成後：gate 與 mutate 跑得起來、placeholder 為 skip）

### Task 0.1 — Phase gate＋mutate＋placeholder（`票 —`）
`票 —`：測試基礎設施，不對單一票。
- SPEC ref：§V　目標：消除「文件引用了不存在的腳本」缺口；rc 判讀沿 EVTALIGN 教訓（紅只認 rc=1；rc=5＝UNCOVERED）。
- 輸入 / 輸出：無 → `scripts/evtlabel_phase_gate.sh`、`handoffs/20260910-evtlabel-mutate.py`、placeholder 測試檔（`pytest.skip("Task N.x 尚未實作")`）。
- 實作要點：
  1. gate 腳本 phase 參數 → 對應 pytest 檔集合（見各 Phase 測試段）；`rc=$?` 直接取，禁經 pipe。
  2. mutate 腳本：`(mutation_id, file, old, new, test_cmd)` 表；套用→跑→還原（`git checkout -- <file>` 只對本腳本改的檔；工作區 dirty 之其他檔不動）；輸出 `COVERED/UNCOVERED` 計數。
  3. placeholder：`tests/api/test_evtlabel_disclosure.py`、`tests/momentum/event_samples/test_isolation_terms.py`、`tests/momentum/Analysis/test_evtlabel_isolation_channel.py`、`tests/api/test_evtlabel_staging.py`、`tests/momentum/Analysis/test_evtlabel_stage3.py`、`tests/momentum/Analysis/test_binary_discrimination.py`、`tests/momentum/Analysis/test_evtlabel_stage5.py`、`tests/momentum/Analysis/test_evtlabel_oracle.py`、`tests/momentum/Analysis/test_evtlabel_e2e_realkline.py`、`tests/momentum/Analysis/test_evtlabel_survivor_consumer.py`、`tests/momentum/Analysis/test_event_label_mode_contract.py`。
- 修改檔案：新建如上；既有 caller：無。
- 路徑：
  - scripts/evtlabel_phase_gate.sh
  - handoffs/20260910-evtlabel-mutate.py
  - tests/api/test_evtlabel_*.py
  - tests/momentum/event_samples/test_isolation_terms.py
  - tests/momentum/Analysis/test_evtlabel_*.py
  - tests/momentum/Analysis/test_binary_discrimination.py
  - tests/momentum/Analysis/test_event_label_mode_contract.py
- 不可做：不寫任何業務邏輯；不把 skip 當綠。
- 邊界：①phase 參數未知 ⇒ rc=2 並印用法；②mutate 套用失敗（old 不存在）⇒ 該 mutation 記 `APPLY_FAIL` 且整體 rc≠0。
- 風險緩解：⊘
- **驗證**：`bash scripts/evtlabel_phase_gate.sh 0` rc=0；`bash scripts/evtlabel_phase_gate.sh 1` rc=1（全 skip ⇒ 不通過）；`venv/bin/python handoffs/20260910-evtlabel-mutate.py --list` 印 10 條 mutation ID（M-P2-1..3、M-P3-1..7）。
- **存活至**：全票完工後保留（回歸用）。
- **覆蓋風險**：無。

### Phase 0 測試＋Gate
單元：無。邊界：gate 對 skip 之處置。效能：⋅跳過。Gate：`evtlabel_phase_gate.sh 0` rc=0。

---

## Phase 1 — 揭露實際 label 規則＋UI 單位（完成後：事件報告帶 `metadata.event_label_rule`；隔離區多一段；h/k 旁有單位）

### Task 1.1 — `metadata.event_label_rule`（`票 EVTLABEL-①`）
- SPEC ref：Task 1.1　目標：事件 run 報告寫入實際消費之 label 規則與單位換算。
- 輸入 / 輸出：`staged`（含 `prepared: PreparedAnalysisWindows`、`records`）＋`report: dict` → `report["metadata"]["event_label_rule"]: dict`（鍵集＝`event_label_mode.json["event_label_rule_keys"]`）。
- 實作要點：
  1. `spec = json.loads(staged["prepared"].normalized_spec_bytes)`；取 `horizon_bars, decision_offset_bars, entry_price_semantic, label_return_mode`。
  2. `window_ms = max(w.label_end_ms - w.label_start_ms for w in prepared.windows)`；`event_tfs = {w.timeframe}`；`feature_tf = report["metadata"]["timeframe"]`；`ratio = event_bar_s / feature_bar_s`（用 service 已注入之 `timeframe_seconds` map，禁直讀 module 常數）；`label_window_feature_bars = -(-window_ms // (feature_bar_s*1000))`。
  3. `return_formula`：`_return_formula(mode, entry) -> str`（查表；表在 `event_label_mode.json["return_formula_by_mode"]`）。
  4. `imported_binary_label = {"present": all("label" in r for r in records), "n_pos": sum(label==1), "n_neg": sum(label==0), "used": False}`；`n_events_consumed = len(staged["event_label_by_id"])`。
  5. 鍵集斷言：`set(out) == set(contract["event_label_rule_keys"])`，不等 ⇒ raise（fail-closed）。
  6. 掛點：`_inject_isolation_source` 之兩個呼叫處緊接呼叫 `_inject_label_rule_disclosure(staged, report)`。
- 修改檔案：`api/services/ic_analysis_service.py::_inject_label_rule_disclosure`（新）、呼叫處（與 `_inject_isolation_source` 同兩處）；`momentum/Analysis/contracts/event_label_mode.json`（新，本 Task 先建 `event_label_rule_keys`、`return_formula_by_mode` 兩鍵；其餘鍵 Task 3.1 補）。既有 caller：無新 caller。
- 路徑：
  - api/services/ic_analysis_service.py
  - momentum/Analysis/contracts/event_label_mode.json
  - handoffs/20260910-probe-label-rule.py
  - tests/api/test_evtlabel_disclosure.py
- 不可做：不在 orchestrator 寫；不讀 request spec；不重算 label。
- 邊界：①mixed tf ⇒ `event_timeframe="mixed"`、`feature_bars_per_event_bar=null`、`ratio_integral=false`；②legacy 無 `label` ⇒ `present=false, n_pos=n_neg=0`；③切分未套用仍寫。
- 風險緩解：`[A-1]`（驗證①）。
- **驗證**：①`venv/bin/python handoffs/20260910-probe-label-rule.py` rc=0（165 批逐事件 `window_ms == horizon_bars×event_bar_ms`；印 `label_window_feature_bars=12`）；②`pytest tests/api/test_evtlabel_disclosure.py -q` rc=0：鍵集相等、`imported_binary_label=={present:True,n_pos:136,n_neg:29,used:False}`（fixture 用測試自建之 165 筆 records，值取自 receipt）、非事件 run 無鍵；③G-1 `pytest tests/momentum/Analysis/test_gap2_golden.py -q` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：Task 3.4 更新 `used`／`statistic_kind` 值，鍵集不變；無刪除。

### Task 1.2 — 隔離區「label 規則」揭露（`票 EVTLABEL-①`）
- SPEC ref：Task 1.2　目標：`IsolationNote` 多一段四行。
- 輸入 / 輸出：`report.metadata.event_label_rule` → `string[]`（四行）。
- 實作要點：
  1. `frontend/src/lib/icLabelRule.ts`：`readLabelRule(metadata): ICEventLabelRule|null`、`labelRuleLines(rule): string[]|null`、`unitCaption(eventTf, featureTf, ratio): string`。
  2. 行 1：`h=${h} 根（單位＝事件週期 ${eventTf} 的根數＝${featureTf} 特徵的第 ${label_window_feature_bars} 根）`；ratio null ⇒ `h=${h} 根（單位＝事件週期根數）`。行 2：k 同單位。行 3：`進場價＝${entry}；報酬＝${return_formula ?? '報酬算法未揭露（後端缺欄）'}`。行 4：`你匯入的 0/1 標籤：${present ? `有（正 ${n_pos}／反 ${n_neg}）` : '無'}；本次${used ? '已用（IC 對的是你的 0/1 標籤）' : '未用（IC 對的是規則重算的報酬）'}`。
  3. `IsolationNote.tsx`：在既有 lines 後渲染 `<section data-testid="label-rule-note">`，無鍵不渲染。
  4. `types.ts`：`export interface ICEventLabelRule { … }`（欄位＝JSON 契約鍵）。
- 修改檔案：`frontend/src/lib/icLabelRule.ts`（新）、`frontend/src/components/ic-analysis/IsolationNote.tsx`、`frontend/src/lib/types.ts`。既有 caller：`page.tsx:709` 不改。
- 路徑：
  - frontend/src/lib/icLabelRule.ts
  - frontend/src/lib/icLabelRule.test.ts
  - frontend/src/components/ic-analysis/IsolationNote.tsx
  - frontend/src/components/ic-analysis/IsolationNote.test.tsx
  - frontend/src/lib/types.ts
- 不可做：不從批次 detail 推 h；不重算單位。
- 邊界：①`present=false` ⇒ 行 4「無」；②`return_formula` 缺 ⇒ 缺欄文案。
- 風險緩解：⊘
- **驗證**：`cd frontend && npx vitest run src/lib/icLabelRule.test.ts src/components/ic-analysis/IsolationNote.test.tsx` rc=0：有鍵四行且含 `第 12 根`；ratio null 退化；無鍵無 `label-rule-note`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：Task 3.9 改行 4 之 `used` 分支文案；行數不變。

### Task 1.3 — h/k 輸入旁單位（`票 EVTLABEL-③`）
- SPEC ref：Task 1.3　目標：兩輸入旁加單位說明。
- 輸入 / 輸出：`detail.summary.timeframes`（批）、`featureTimeframe`（prop，自 `config.timeframe`）→ 兩個 caption 元素。
- 實作要點：
  1. `EventBatchDisclosurePanel` 新 prop `featureTimeframe?: string`；`page.tsx:714-737` 傳 `config.timeframe`。
  2. `eventTf = summary.timeframes.length===1 ? summary.timeframes[0] : null`；`ratio = TIMEFRAME_SECONDS[eventTf]/TIMEFRAME_SECONDS[featureTf]`（前端既有 tf 秒表；若無則加到 `icLabelRule.ts`，與後端 `momentum/Analysis/event_samples/label_value_from_case.py::TIMEFRAME_SECONDS` 值一致並以 vitest 對證 JSON 匯出）。
  3. caption：`單位：事件週期（${eventTf}）的根數；1 根＝${featureTf} 特徵的 ${ratio} 根`；ratio 非整數或任一 tf 缺 ⇒ `單位：事件週期的根數`。掛 `data-testid="ic-param-h-unit"`／`"ic-param-k-unit"`。
- 修改檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`（`:320-354` h 輸入、`:469-495` k 輸入）、`frontend/src/app/ic-analysis/page.tsx:714-737`、`frontend/src/lib/icLabelRule.ts::unitCaption`。既有 caller：`icEventBatchDisclosure.test.tsx` 既有 render 不傳新 prop ⇒ 退化文案，不紅。
- 路徑：
  - frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx
  - frontend/src/components/ic-analysis/icEventBatchDisclosure.test.tsx
  - frontend/src/app/ic-analysis/page.tsx
  - frontend/src/lib/icLabelRule.ts
- 不可做：不動 `IC_ANALYSIS_INITIAL_HORIZON_BARS`、不動 seed 邏輯。
- 邊界：①mixed tf ⇒ 退化；②feature run 未選 ⇒ 退化。
- 風險緩解：⊘
- **驗證**：`cd frontend && npx vitest run src/components/ic-analysis/icEventBatchDisclosure.test.tsx -t unit` rc=0：12h×1h ⇒ `12 根`；4h×1h ⇒ `4 根`；1h×4h ⇒ 退化。`npm run build` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase 1 測試＋Gate
單元：`test_evtlabel_disclosure.py`、`icLabelRule.test.ts`。邊界：mixed tf／legacy。效能：⋅跳過。Golden：G-1。Gate：`bash scripts/evtlabel_phase_gate.sh 1` rc=0＋vitest 兩檔＋`npm run build`。

---

## Phase 2 — purge 依 label 視窗換算（完成後：`ic_train_test_split.purge_gap` 承載 label 視窗，embargo 只承載 config／look-ahead 深度；G-2 重凍結）

### Task 2.1 — `isolation_terms_rows`（`票 EVTLABEL-②`）
- SPEC ref：Task 2.1　目標：label 視窗列數與 look-ahead 深度列數分開。
- 輸入 / 輸出：`windows: Sequence[WindowRow]`、`lookahead_bars_declared: Mapping[str,int]`、`timeframe_seconds: Mapping[str,int]`、`feature_timeframe: str` → `IsolationTerms(label_window_rows:int, lookahead_depth_rows:int)`（frozen dataclass）。
- 實作要點：
  1. `fb_ms = timeframe_seconds[feature_timeframe]*1000`（缺 ⇒ `LabelProducerError`）。
  2. `label_window_rows = max(ceil((w.label_end_ms-w.label_start_ms)/fb_ms) for w in windows, default=0)`；`lookahead_depth_rows = max(ceil(lookahead_bars_declared[w.timeframe]*timeframe_seconds[w.timeframe]*1000/fb_ms) for w in windows, default=0)`。
  3. 不變式（測試）：`max(label_window_rows, lookahead_depth_rows) == ceil(max(purge_lower_bound_ms)/fb_ms)`（與既有 `purge_rows` 相等）。
  4. service `_stage_event_batch` 回傳新增 `label_window_rows`、`lookahead_depth_rows`；兩注入點改 `cell_override["embargo"]=max(config.embargo, lookahead_depth_rows)` 並 `analyzer.analyze(..., event_isolation=EventIsolationRows(label_window_rows=…, lookahead_depth_rows=…))`（顯式 kwarg；**禁**放進 `config_override`——R1 C8）。`EventIsolationRows` frozen dataclass 於 `momentum/core/contracts.py`（本 Task 建）。
- 修改檔案：`momentum/Analysis/event_samples/label_value_from_case.py::isolation_terms_rows`（新，緊接 `purge_lower_bound_rows`）；`api/services/ic_analysis_service.py::_stage_event_batch`（`:744-772`）、`_run_event_label_stages`（`:1296-1302`、`:1578-1585`）。既有 caller：`purge_lower_bound_rows`／`project_purge` 不動。
- 路徑：
  - momentum/Analysis/event_samples/label_value_from_case.py
  - api/services/ic_analysis_service.py
  - tests/momentum/event_samples/test_isolation_terms.py
- 不可做：不改 `purge_lower_bound_rows` 公式；不動事件切分 `split_events`。
- 邊界：①`lookahead=0` ⇒ depth 0；②windows 空 ⇒ (0,0) 不 raise；③feature 比事件粗 ⇒ ceil≥1。
- 風險緩解：⊘
- **驗證**：`pytest tests/momentum/event_samples/test_isolation_terms.py -q` rc=0：12h h=1 於 1h ⇒ 12；`{"12h":12}` ⇒ 144；`open_to_close` ⇒ 12；4h h=3 於 1h ⇒ 12；不變式對 G-2 九組成立。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.2 — split purge 吃 `event_isolation.label_window_rows`（`票 EVTLABEL-②`）
- SPEC ref：Task 2.2　目標：`purge_gap=max(effective_horizon, label_window_rows)`；metadata 三新鍵（`embargo_source` 由 service 寫，R1 C7）。
- 輸入 / 輸出：`analyze(..., event_isolation: Optional[EventIsolationRows] = None)`（**定案（R1 C8）：顯式 kwarg**；`ICConfig.model_validate` 對未知鍵靜默丟，三家實跑證實，故 `config_override` 通道**禁用**）→ `metadata["ic_train_test_split"]` 新增三鍵 `purge_gap_source`、`event_label_window_rows`、`lookahead_depth_rows`（`embargo_source` **不在此**——R1 C7，由 service 寫 `metadata.isolation.embargo.source`）。
- 實作要點：
  1. `analyze` 與 `_run_full_sample_fallback` 簽名加 `event_isolation=None`；入口 fail-closed：`config_override` 含 `{"event_purge_rows","lookahead_depth_rows","event_isolation"}` 任一鍵 ⇒ `raise ValueError("event isolation must be passed as kwarg, not config_override")`（M-P2-3 之守衛）。
  2. `_build_holdout_split_plan`（`:478-540`）之 `test_rows = np.arange(split_point + effective_purge + effective_embargo, n_rows)` 改為 `holdout_test_row_index(n_rows, oos_test_size=config.oos_test_size, purge_gap=effective_purge, embargo=effective_embargo)`（R3 單一實作；新檔 `momentum/core/split_preview.py`；`train_rows` 算式不動）。`:1102-1160`：`w = event_isolation.label_window_rows if event_isolation else 0`；`purge_gap = max(effective_horizon, w)`；`purge_gap_source = "event_label_window" if w > effective_horizon else "mainline_horizon"`；`event_label_window_rows = w`；`lookahead_depth_rows = event_isolation.lookahead_depth_rows if event_isolation else None`；非事件（`event_isolation=None`）時三鍵**不寫**（G-1 逐位元組）。
  3. `_run_full_sample_fallback` 收下 kwarg 但不用（無切分）。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::analyze`（簽名＋入口守衛）、`_run_full_sample_fallback`（簽名）、`:1102-1160` split 建立與 metadata 寫入；`momentum/core/contracts.py::EventIsolationRows`（Task 2.1 建）。既有 caller：`_build_holdout_split_plan` 簽名不變；`api/services/ic_analysis_service.py` 兩注入點（Task 2.1）。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - momentum/core/contracts.py
  - handoffs/20260907-probe-split-baseline.py
  - tests/golden/evtalign/split_baseline.json
  - tests/momentum/Analysis/test_ic_1a_cut1_split.py
  - tests/momentum/Analysis/test_evtlabel_isolation_channel.py
- 不可做：不改 `_resolve_effective_label_horizon`；不在 orchestrator 換算 ms；不動 embargo 語意；不經 `config_override` 傳列數。
- 邊界：①purge 過大 ⇒ `SkippedResult(INSUFFICIENT_DATA)` 既有路徑；②非事件 ⇒ 逐位元組同前；③`label_window_rows<effective_horizon` ⇒ `mainline_horizon`。
- 風險緩解：G-2／G-3；M-P2-1、M-P2-3。
- **驗證**：`venv/bin/python handoffs/20260907-probe-split-baseline.py --diff` 三條通過條件（SPEC G-2）；`--write` 後新 sha 記於本檔 B2 收尾；G-3 重現 `purge_gap=12`；`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/core/test_split_contract.py tests/golden/ic_phase1_contract tests/momentum/Analysis/test_evtlabel_isolation_channel.py -q` rc=0；`ASSERT venv/bin/python handoffs/20260907-probe-split-baseline.py --check WHEN group=global THEN rc=0`；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_isolation_channel.py -q WHEN config_override=event_purge_rows THEN rc=0`（測試斷言入口 raise）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.3 — 隔離區來源改讀新鍵（`票 EVTLABEL-②`）
- SPEC ref：Task 2.3　目標：`metadata.isolation` 與前端文案反映真實來源。
- 輸入 / 輸出：`ic_train_test_split`（新鍵）＋`staged` → `isolation.purge.source ∈ {mainline_horizon, event_label_window}`、`isolation.embargo.source ∈ {config_embargo, event_lookahead_depth}`。
- 實作要點：
  1. `_inject_isolation_source`：`purge.source = split.get("purge_gap_source") or "global_default_horizon"`；`purge.note` 改為 `f"purge {bars} 根＝max(主線 horizon {eff}, label 視窗 {win} 根)"`；`embargo.source = "event_lookahead_depth" if staged["lookahead_depth_rows"] > staged["embargo_before_event"] else "config_embargo"`（**唯一寫入點**，R1 C7）；`embargo` 物件新增 `lookahead_depth_rows` 鍵；既有 `event_purge_rows` 鍵保留舊值（＝max(depth,window) 列數）供對照。
  2. 前端 `SOURCE_TEXT` 新增：`mainline_horizon: '由主線 horizon 決定（label 視窗沒有比它長）'`、`event_label_window: '由你設的 label 視窗（h×事件週期）換算成特徵根數'`、`event_lookahead_depth: '由批次宣告的 look-ahead 深度換算成特徵根數'`；舊鍵保留。
  3. 既有測試更新（diff 明列）：`tests/api/test_isolation_disclosure.py` 之 `purge.source=="global_default_horizon"` 斷言 → 依情境改 `mainline_horizon`／`event_label_window`；`icIsolation.test.ts` 同步。
- 修改檔案：`api/services/ic_analysis_service.py::_inject_isolation_source`；`frontend/src/lib/icIsolation.ts::SOURCE_TEXT`。既有 caller：`IsolationNote.tsx` 不改。
- 路徑：
  - api/services/ic_analysis_service.py
  - frontend/src/lib/icIsolation.ts
  - frontend/src/lib/icIsolation.test.ts
  - tests/api/test_isolation_disclosure.py
- 不可做：不重算列數。
- 邊界：①舊報告無新鍵 ⇒ 舊 source 值；②切分未套用 ⇒ 不寫鍵。
- 風險緩解：⊘
- **驗證**：`pytest tests/api/test_isolation_disclosure.py -q` rc=0（G-3 情境 `purge.source=="event_label_window"`、`embargo.source=="event_lookahead_depth"`、`total_bars==156`）；`cd frontend && npx vitest run src/lib/icIsolation.test.ts` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase 2 測試＋Gate
單元：`test_isolation_terms.py`。整合：`test_isolation_disclosure.py`、split 三檔。Golden：G-1、G-2（`--diff`→`--write`）、G-3。Mutation：M-P2-1、M-P2-2、M-P2-3（mutate 腳本）。Gate：`bash scripts/evtlabel_phase_gate.sh 2` rc=0。

---

## Phase 3 — 匯入標籤模式（完成後：`imported_binary` 下 IC 直接對 0/1 算、報酬版第二欄、倖存者帶標籤來源；`return_rule`／全域逐位元組不變）

### Task 3.1 — 枚舉 SoT＋契約（`票 EVTLABEL-④`）
- SPEC ref：Task 3.1　目標：所有新枚舉一檔定義；`derive_label_kind`／survivor contract 接新值。
- 輸入 / 輸出：無 → `event_label_mode.json` 補齊鍵：`label_modes`、`label_sources`（含 `imported_binary_label`）、`statistic_kinds`（含 `binary_discrimination`、`binary_discrimination_unavailable`）、`label_mode_reasons`（`no_label_column`／`label_invalid_domain`／`one_class`／`class_below_min_selection`）、`summary_columns_binary`（含 `binary_status`）、`binary_status_values`、`threshold_skip_keys_binary`（ic_mean／icir／ic_hit_rate／monotonicity／coverage／long_short_spread）、`removed_keys_binary`（`rank_biserial`／`binary_unavailable`／`permutation_oracle_disagree`／`permutation_unavailable`）、`survivor_suppressed_reasons`（`negative_control_failed`）、`min_events_per_class_default`；`ic_survivor_contract.json` `sample_scope.event` 新增 `label_binary`（nullable 物件：`import_id`／`n_pos`／`n_neg`／`label_origin_values`）與 `statistic_kind`；`ic_config_schema.py`：`EventFilterConfig.min_events_per_class:int=10`、`.perm_budget_total:int=200000`、`.negative_control_n:int=50`、`.oracle_seed:int=20260910`；`ThresholdsConfig.rank_biserial_min:float=0.10`。
- 實作要點：
  1. `momentum/core/contracts.py:1030`：`LABEL_KIND_BY_SOURCE["imported_binary_label"] = LABEL_KIND_EVENT_GIVEN`；同檔新增 `@dataclass(frozen=True) class ValidatedBinaryLabel(series: pd.Series, digest: str, rows_frozenset: frozenset[tuple[str,int,int]], n_pos: int, n_neg: int)`（R2 D1：`rows_frozenset` 必填，契約測試斷言欄位存在）、`def is_event_label_consumed(event_info: Mapping) -> bool`（`label_source in {"event_label_value","imported_binary_label"}`）、`def binary_label_digest(rows: Iterable[tuple[str,int,int]]) -> str`（sha256 over sorted `(event_id, ts_ms, label)`）；測試以 JSON `label_sources` 對證 Python dict 鍵集。
  2. `survivor_contract.py::validate_survivor_output`：`label_source=="imported_binary_label"` ⇒ 六鍵非 null **且** `label_binary` 非 null 且四子鍵齊；其他 label_source ⇒ `label_binary` 必為 null；`_survivor_reason` 詞彙表加 `negative_control_failed`。
  3. `_load_contract()` 讀 JSON 缺鍵 ⇒ import 期 raise。
  4. orchestrator 內所有 `_is_event_conditional_consumed(...)` 呼叫改 `is_event_label_consumed(...)`（`:3262-3281`、`:3895-3902`）；舊函式保留為薄包裝或刪除（測試對證呼叫點數＝0）。
- 修改檔案：`momentum/Analysis/contracts/event_label_mode.json`、`momentum/Analysis/contracts/ic_survivor_contract.json`、`momentum/core/contracts.py::LABEL_KIND_BY_SOURCE`／`ValidatedBinaryLabel`／`is_event_label_consumed`／`binary_label_digest`、`momentum/Analysis/survivor_contract.py::validate_survivor_output`／`_survivor_reason`、`momentum/Analysis/ic_config_schema.py::EventFilterConfig`／`ThresholdsConfig`、`momentum/Analysis/ic_filter_orchestrator.py`（predicate 呼叫點）。既有 caller：`validate_survivor_output` 既有呼叫（return_rule payload `label_binary=null` ⇒ 通過）。
- 路徑：
  - momentum/Analysis/contracts/event_label_mode.json
  - momentum/Analysis/contracts/ic_survivor_contract.json
  - momentum/core/contracts.py
  - momentum/Analysis/survivor_contract.py
  - momentum/Analysis/ic_config_schema.py
  - tests/momentum/Analysis/test_event_label_mode_contract.py
- 不可做：不改 `sample_scope_kind_values`；不在散文重列枚舉。
- 邊界：①JSON 缺鍵 ⇒ raise；②未知 label_source ⇒ 既有 raise。
- 風險緩解：⊘
- **驗證**：`pytest tests/momentum/Analysis/test_event_label_mode_contract.py tests/momentum/Analysis/test_survivor_contract.py -q` rc=0：枚舉集合相等；`derive_label_kind("imported_binary_label")=="event_given"`；binary payload 六鍵非 null＋`label_binary` 齊 ⇒ 通過、缺 `import_id` ⇒ raise、`return_rule` payload 帶非 null `label_binary` ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.2 — `event_label_mode` 請求欄（`票 EVTLABEL-④`）
- SPEC ref：Task 3.2　目標：request→route→service 透傳；前端送欄。
- 輸入 / 輸出：`ICAnalyzeRequest.event_label_mode: Literal["auto","return_rule","imported_binary"]="auto"` → `event_batch["event_label_mode"]`。
- 實作要點：
  1. `ic_models.py:231-256` 不變式加：`event_label_mode!="auto" and not event_import_id ⇒ 400`；`event_label_scan and event_label_mode=="imported_binary" ⇒ 400 scan_not_applicable_in_imported_binary_mode`（`auto` 解析為 binary 且帶 scan 之情形於 Task 3.3 服務端擋）。
  2. `ic_analysis.py:278-289` 把值放進 `event_batch`。
  3. 前端 `types.ts::ICAnalysisConfig.event_label_mode?`；`useICAnalysis.ts:647-663` 只在 event＋import 分支送；store 預設 `'auto'`。
- 修改檔案：`api/models/ic_models.py::ICAnalyzeRequest`／`_gap3_event_transport_invariants`；`api/routes/ic_analysis.py`（event_batch 組裝）；`frontend/src/lib/types.ts`、`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`。既有 caller：`tests/api/test_ic_analysis_api.py`。
- 路徑：
  - api/models/ic_models.py
  - api/routes/ic_analysis.py
  - frontend/src/lib/types.ts
  - frontend/src/hooks/useICAnalysis.ts
  - frontend/src/hooks/icEventAnalysisRequest.test.ts
  - frontend/src/store/icAnalysisStore.ts
  - tests/api/test_ic_analysis_api.py
- 不可做：不在 route 解析 `auto`；不加第四模式。
- 邊界：①`event_timestamps` 路徑帶欄 ⇒ 400；②大小寫錯 ⇒ 422。
- 風險緩解：⊘
- **驗證**：`pytest tests/api/test_ic_analysis_api.py -q -k label_mode` rc=0；`cd frontend && npx vitest run src/hooks/icEventAnalysisRequest.test.ts` rc=0（legacy 分支不送欄）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.3 — staging：binary 向量＋`auto` 解析（`票 EVTLABEL-④`）
- SPEC ref：Task 3.3　目標：與 `ts_map` 同鍵之 0/1 向量；獨立快照之三元組來源；值域閘。**不決定 effective mode**（R1 C2，決策在 Task 3.4）。
- 輸入 / 輸出：`records`（含 `label`）、`prepared1.windows` → `staged["event_binary_labels"]: Dict[int,int]`（key＝feature_cutoff_ms，與 `ts_map` 同鍵）、`staged["event_binary_rows_by_id"]: Dict[str, tuple[int,int]]`（`event_id → (feature_cutoff_ms, label)`，由 records **獨立快照**建）、`staged["label_mode_requested"]`、`staged["label_mode_hint"]`（`no_label_column`／`label_invalid_domain`／None）。
- 實作要點：
  1. 值域閘（R1 C14c）：`_binary_label_domain(records) -> tuple[bool, str|None]`：每筆 `label` 須 `is not None`、`float(x).is_integer()`、`int(x) in {0,1}`、finite；任一違反 ⇒ `requested=="imported_binary"` raise `ValueError("label_invalid_domain: …")`（route 422）；`auto` ⇒ 不建 map、`hint="label_invalid_domain"`。`label` 欄全缺 ⇒ `hint="no_label_column"`。
  2. `:705-724` 迴圈內：`lab = int(rec_by_id[w.event_id]["label"])`；`bin_map[key]=lab`；`bin_rows_by_id[event_id]=(key, lab)`。
  3. `requested=="imported_binary"` 且 `event_label_scan` 非空 ⇒ raise `scan_not_applicable_in_imported_binary_mode`（`auto` 解析為 binary 且帶 scan ⇒ orchestrator 端拒，Task 3.4）。
  4. 兩注入點 `analyzer.analyze(..., event_binary_labels=bin_map or None, label_mode_requested=requested)`（kwargs 新增於 orchestrator `analyze`／`_run_full_sample_fallback`）。
  6. 顯式 fast-fail（R2 D4／R3 單一實作）：新建 `momentum/core/split_preview.py::holdout_test_row_index(n_rows:int, *, oos_test_size:float, purge_gap:int, embargo:int) -> np.ndarray`（純算術：`split_point=floor((1-oos_test_size)*n_rows)`；`arange(split_point+purge_gap+embargo, n_rows)`）；orchestrator `_build_holdout_split_plan` 之 `test_rows` 改呼叫它（Task 2.2 要點 2 同步；`tests/momentum/core/test_holdout_test_row_index.py` 對證受理 run test 段 31 列＝1940 rows 起點）。service `prevalidate_imported_binary_selection_classes(bin_map, feature_index, cfg, label_window_rows, embargo_rows) -> tuple[int,int]` 呼叫同一函式算 test 段 index，計 bin_map 於該段每類數；`requested=="imported_binary"` 且 `min < cfg.min_events_per_class` ⇒ raise（route 422 `class_below_min_selection_preview`）；`auto` 不呼叫。結果寫 `staged["selection_preview"]={n_pos,n_neg}` 並透傳 orchestrator；stage3 以同函式同輸入重算，不一致 ⇒ `raise AlignmentViolationError("selection preview mismatch")`（R3 codex P1-04：同函式同輸入不一致＝bug，不容忍）；`metadata.label_mode.selection_preview` 揭露。
  5. `_assert_event_triple_bound` 改依 `info["label_source"]` 分派（R1 C5）：`"event_label_value"` ⇒ 既有回比；`"imported_binary_label"` ⇒ (a) 報酬 `consumed_event_labels` vs `event_label_by_id` 逐筆（既有邏輯）**且** (b) `consumed_event_binary_rows[event_id] == (ms, value)` vs `event_binary_rows_by_id[event_id]` 三項逐筆、鍵集相等；其他 source（fallback）維持既有 early-return。
- 修改檔案：`api/services/ic_analysis_service.py::_stage_event_batch`、`_binary_label_domain`（新）、`_run_event_label_stages`（兩注入點）、`_assert_event_triple_bound`。既有 caller：`_stage_event_batch` 回傳 dict 只加鍵。
- 路徑：
  - api/services/ic_analysis_service.py
  - tests/api/test_evtlabel_staging.py
- 不可做：不改 `ts_map` 鍵；不在此算統計；不在此決定 effective mode。
- 邊界：①legacy 無 `label` ⇒ `hint=no_label_column`、不送 map；②值域違反見要點 1；③symbol 過濾後單類 ⇒ 仍送 map（由 Task 3.4 判）。
- 風險緩解：⊘
- **驗證**：`pytest tests/api/test_evtlabel_staging.py -q` rc=0：165 批（測試自建 records）⇒ `len(event_binary_labels)==len(event_label_values)` 且鍵集相等、`event_binary_rows_by_id[e][0] == owners 反查之 ms`；注入 `2,-1,0.5,NaN,None` ⇒ `auto` 得 `hint=label_invalid_domain`；`ASSERT venv/bin/python -m pytest tests/api/test_evtlabel_staging.py -q -k explicit_binary_invalid_domain WHEN label_mode=imported_binary THEN rc=0`（斷言 raise）；三元組：交換兩同值事件之 owner ⇒ `_assert_event_triple_bound` raise；mutate `consumed_event_labels` 一值（binary 不動）⇒ 亦 raise（雙鍵）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.4 — stage3 binary 綁定與驗證（`票 EVTLABEL-④`）
- SPEC ref：Task 3.4　目標：stage3 決定 `label_mode_effective`（R1 C2）；binary 向量對齊 filtered index、過 `validate_event_given`、以 immutable `ValidatedBinaryLabel` 交付（R1 C4）。
- 輸入 / 輸出：`event_binary_labels: Dict[int,int]|None`、`label_mode_requested` → `self._ic_cache["event_binary_label"]: ValidatedBinaryLabel|None`；`event_info` 新鍵 `consumed_event_binary_rows`、`binary_label_digest`、`label_source="imported_binary_label"`、`statistic_kind="binary_discrimination"`、`secondary_statistic="conditional_ic"`；`metadata["label_mode"]={requested, effective, reason, n_pos_batch, n_neg_batch, n_pos_selection, n_neg_selection, selection_scope}`（事件路徑限定）。
- 實作要點：
  1. selection scope：`sel_idx = filtered.index[test_mask]` 若 `split_context` 存在，否則 `filtered.index`（fallback＝全樣本）；`n_pos_sel, n_neg_sel` 自 `event_binary_labels` 於 `sel_idx`。
  2. mode 決策：`requested=="auto"`：`binary map is None` ⇒ `return_rule`＋`reason=hint`；`min(n_pos_sel,n_neg_sel)==0` ⇒ `one_class`；`< cfg.min_events_per_class` ⇒ `class_below_min_selection`；否則 `imported_binary`。`requested=="imported_binary"` 且任一不足 ⇒ `raise ValueError(...)`（non-retryable）；`requested=="return_rule"` ⇒ 不綁 binary。`auto` 得 binary 且 `event_label_scan` 非空 ⇒ raise `scan_not_applicable_in_imported_binary_mode`。
  3. `imported_binary` 下：`bvals=[float(event_binary_labels[int(t)]) ...]`（缺鍵／NaN ⇒ raise）；`res = validate_consumed_label(filtered_features, pd.Series(bvals, index=filtered.index), label_kind=derive_label_kind("imported_binary_label"), expected_values=event_binary_labels, event_owners=owners)` `[A-3]`（R1 C6）；`validate_event_given` 回傳新增 `consumed_event_rows={event_id:(ts_ms,value)}`（additive；報酬路徑回傳鍵不變）；`event_info["consumed_event_binary_rows"]=res["consumed_event_rows"]`。
  4. `rows = frozenset((eid, int(ts), int(v)) for eid,(ts,v) in consumed_event_rows.items())`；`digest = binary_label_digest(sorted(rows))`；`self._ic_cache["event_binary_label"] = ValidatedBinaryLabel(series=pd.Series(bvals, index=filtered.index).copy(), digest=digest, rows_frozenset=rows, n_pos=..., n_neg=...)`（R2 D1）；`series.to_numpy().flags.writeable=False`（grok／Claude 實跑：之後 `iloc[...]=` 會 `ValueError`）；`event_info["binary_label_digest"]=digest`。
  5. 報酬 label 既有驗證與 `consumed_event_labels` 鍵**不動**。fallback（`conditional_ic_abandoned`）⇒ `statistic_kind="binary_discrimination_unavailable"`、binary 不綁、`label_mode.effective="return_rule"`、`reason="conditional_ic_abandoned"`。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_stage3_event_filter`（`:3348-3480`）、`analyze`／`_run_full_sample_fallback` 簽名（`event_binary_labels=None, label_mode_requested="auto"`）；`momentum/core/contracts.py::validate_event_given`（回傳加 `consumed_event_rows`）。既有 caller：`api/services/ic_analysis_service.py`（Task 3.3）；`validate_event_given` 既有測試（回傳只加鍵，不紅）。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - momentum/core/contracts.py
  - tests/momentum/Analysis/test_evtlabel_stage3.py
- 不可做：不覆寫 `consumed_event_labels`；不在 service 決定 effective。
- 邊界：①fallback ⇒ unavailable；②NaN／缺鍵 ⇒ raise；③selection 單類 ⇒ `one_class`。
- 風險緩解：`[A-3]`；M-P3-3、M-P3-5。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q` rc=0：錯位一格 ⇒ `AlignmentViolationError`；`return_rule` 鍵集 == 改前；binary 值集 ⊆ {0.0,1.0}；fixture 全批 20/20、test 18/2 ⇒ `auto`→`return_rule/class_below_min_selection`；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q -k icir_gate_off_binary WHEN label_source=imported_binary_label THEN rc=0`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.5 — `mann_whitney_table`（`票 EVTLABEL-④`）
- SPEC ref：Task 3.5　目標：向量化 MW／AUC／rank-biserial。
- 輸入 / 輸出：`features: pd.DataFrame (n×p)`、`y: np.ndarray[int] (n,)`、`min_class_n:int` → `pd.DataFrame(index=feature, columns=[auc, rank_biserial, mw_u, p_value, n_pos, n_neg, n_used, status])`。
- 實作要點：
  1. `Xf = np.where(np.isfinite(X), X, np.nan)`（inf 亦視為缺值並計入 `n_used` 扣除；inf 在上游已被閘，此處只防禦）；**一次**呼叫 `mannwhitneyu(Xf[y==1], Xf[y==0], alternative="two-sided", method="auto", axis=0, nan_policy="omit")`（R3 codex P1-03：**禁**逐欄 python 迴圈；scipy 1.13.1）；`n_pos_c = isfinite(Xf[y==1]).sum(0)`、`n_neg_c` 同；`min(n_pos_c,n_neg_c) < min_class_n` 之欄 ⇒ `unavailable:class_below_min`（結果值仍算但 status 非 ok）；`n_used=n_pos_c+n_neg_c`；全 NaN 欄 ⇒ `unavailable:all_nan`。
  2. `auc = U/(n_pos*n_neg)`；`rank_biserial = 2*auc-1`；常數欄 ⇒ **定案：`status="unavailable:constant"`**（scipy 對全 ties 之 p 定義依版本而異，不冒充 0.5/1.0）。
  3. 任一類 `< min_class_n` ⇒ `unavailable:class_below_min`；`n_used==0` ⇒ `unavailable:all_nan`。
  4. 純函式、無 log、無 I/O。
- 修改檔案：`momentum/Analysis/binary_discrimination.py::mann_whitney_table`（新）。既有 caller：無（3.6 接）。
- 路徑：
  - momentum/Analysis/binary_discrimination.py
  - tests/momentum/Analysis/test_binary_discrimination.py
  - handoffs/20260910-probe-mw-bench.py
- 不可做：無組合特徵；無 bootstrap；hot loop 無 log。
- 邊界：①類 < min ⇒ unavailable；②`n_used==0`；③兩值欄極端 ties。
- 風險緩解：`[A-2]`（驗證④）；M-P3-1。
- **驗證**：`pytest tests/momentum/Analysis/test_binary_discrimination.py -q` rc=0：①`y=1[x>median]` ⇒ `auc==1.0`；②鏡像 ⇒ `rank_biserial` 取負 `abs≤1e-12`；③與逐欄標量 scipy `p` `rel≤1e-9`；⑤全 NaN ⇒ `all_nan`；⑥常數 ⇒ `constant`。④`venv/bin/python handoffs/20260910-probe-mw-bench.py`（39,373×165 隨機矩陣或真實 run）印秒數，`< 60` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.6 — stage5 binary 進 summary_table＋門檻（`票 EVTLABEL-④`）
- SPEC ref：Task 3.6　目標：主統計 `rank_biserial`（效應量閘取絕對值、獨立門檻，R1 C1）、p 走 MW→BH；stage5 消費前三守衛（index 對齊＋長度＋`rows_frozenset` 子集；R1 C4／R2 D1；**無** digest 比對）；stage6／6b 消費規則定死（R1 C9）；報酬版保留第二欄。
- 輸入 / 輸出：`self._ic_cache["event_binary_label"]: ValidatedBinaryLabel`、selection scope 事件列之 features → summary_table 每列新增 `auc, rank_biserial, mw_u, mw_p_value, mw_p_value_adj, n_pos, n_neg, n_used_binary, binary_status`（欄名＝JSON `summary_columns_binary`）；`metadata.event_label_rule.primary_statistic="rank_biserial"`、`secondary_statistic="ic_mean"`、`p_assumption="iid_events"`、`effect_gate={field:"abs(rank_biserial)", min: cfg.rank_biserial_min}`、`imported_binary_label.used=True`。
- 實作要點：
  1. stage5 事件分支（`:3766-3900`）：`vb = self._ic_cache["event_binary_label"]`；`X = features.loc[sel_idx, feature_cols]`；`y = vb.series.loc[sel_idx].to_numpy(int)`；**消費前唯一守衛**（R2 D1；**無** digest 相等比對）：`assert X.index.equals(pd.Index(sel_idx)) and len(y)==len(X)`、`all((owner[int(ts)], int(ts), int(y_i)) in vb.rows_frozenset for ts,y_i in zip(sel_idx_ms, y))`；任一不成立 ⇒ `raise AlignmentViolationError("binary label consumed != validated")`。之後**直接**以此 `X, y` 呼叫 `mann_whitney_table`（中間不得重排、不得 `.iloc[perm]`）。
  2. `tbl = mann_whitney_table(X, y, min_class_n=cfg.min_events_per_class)`；逐列合併到 `summary_table`；`apply_fdr({name: mw_p}, alpha, method)` → `mw_p_value_adj`（既有 `p_value_adj` 仍為報酬版 q）。
  3. `_apply_thresholds(..., binary_mode: bool = False)`：`binary_mode=True` ⇒ 效應量閘 `abs(row["rank_biserial"]) >= thresholds.rank_biserial_min`（`removed["rank_biserial"]`）；p 閘讀 `mw_p_value_adj`；`ic_mean`／`icir`／`ic_hit_rate`／`monotonicity`／`coverage`／`long_short_spread` 全部記錄 `removed[f"{gate}_skipped_binary_mode"]` 不剔除（鍵名＝JSON `threshold_skip_keys_binary`）；`binary_status!="ok"` ⇒ `removed["binary_unavailable"]`。既有呼叫不傳 kwarg ⇒ 行為一字不變。
  4. 排序：binary 模式 `(-abs(rank_biserial), feature_name)`（NaN 置底）。
  5. stage6 redundancy（`:3266-3281`）：`is_event_label_consumed` 且 binary ⇒ 分數＝`abs(rank_biserial)`、tiebreak `feature_name`；stage6b（`:4609-4649`）：入參 label 固定為報酬列（既有 `label_series`，`:1357-1359` 不改）；binary 模式其結果節 metadata 寫 `role="diagnostic"`、`label_source="return_rule_diagnostic"`（R2 D7），**不得**從倖存集移除任何特徵（現網無 `passed.remove`，grok 計數 0；測試：雙特徵 fixture 釘住）。
  6. `return_rule`／全域：不呼叫 3.5、欄集不變、`_apply_thresholds` 預設參數一字不改。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 事件分支、`_apply_thresholds`（`:4360-4400`，加 `binary_mode` kwarg）、stage6 redundancy、stage6b role 標記、`_inject_label_rule_disclosure` 更新 `used`／`primary_statistic`／`effect_gate`（service）。既有 caller：`_apply_thresholds` 既有呼叫不改參數。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - api/services/ic_analysis_service.py
  - tests/momentum/Analysis/test_evtlabel_stage5.py
- 不可做：不把 `rank_biserial` 寫進 `ic_mean`；不共用 `ic_mean_min`；不動全域路徑。
- 邊界：①selection 單類（顯式 binary 之防線）⇒ 全表 `unavailable:one_class_selection`、倖存者 0、`degraded` loud；②pooled fallback 與 binary 並存；③`n_tests=0` 不除零。
- 風險緩解：M-P3-2、M-P3-5、M-P3-7；G-4。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q` rc=0：植入特徵 `passed` 且 `mw_p_value_adj<0.05`；**負向植入（rb≈−0.8）亦 `passed`**；`rank_biserial_min=0.9` ⇒ 弱特徵 `removed["rank_biserial"]`；`p_value_max=0.001` ⇒ 弱特徵 `removed["p_value"]`；`return_rule` 欄集 == 改前；stage3 後替換 cache ⇒ stage5 raise 且無 report；雙特徵 fixture（A 只對 0/1、B 只對報酬）⇒ 倖存集含 A 不含 B；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q -k threshold_reads_abs_rank_biserial WHEN label_mode=imported_binary THEN rc=0`；G-1、G-4。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.7 — 置換自檢＋負對照（`票 EVTLABEL-④`）
- SPEC ref：Task 3.7　目標：倖存者逐一 **block permutation** 重驗（依賴感知，R1 C10）；整批置亂負對照 **fail-closed**（R1 C3）；置換預算有上界（R1 C14a）。
- 輸入 / 輸出：倖存者名單、`X`、`y`、`sel_idx`（時間序） → `removed["permutation_oracle_disagree"]`、`removed["permutation_unavailable"]`；`metadata.event_label_rule.permutation_receipt={seed, n_perm, block_len, n_blocks, first_permutation_digest, budget_floor_hit}`、`.negative_control={n_observed, shuffled_counts, q95, seed_base, block_len}`；`n_observed > 0` 且 `n_observed <= q95` ⇒ `self._survivor_suppressed_reason="negative_control_failed"`（Task 3.8 消費）＋report `degraded`；`n_observed == 0` ⇒ **不跑負對照**、`negative_control={status:"skipped:no_survivors"}`（R3：與邊界①同一路徑，紅 banner 不得出現）。
- 實作要點：
  1. `momentum/Analysis/binary_discrimination.py::block_ids_for_events(sel_idx_ms, label_window_feature_bars, feature_bar_ms) -> np.ndarray`：`gaps = diff(sorted(sel_idx_ms))/feature_bar_ms`；`L = max(1, ceil(W / max(1, min(gaps))), ceil(W / median(gaps)))`（R2 D3：取較大者吸收局部密集段；`len(gaps)==0` ⇒ L=1）；事件依時間序每 L 個一 block；回 `(block_ids, L, n_blocks)`。
  2. `block_permutation_oracle(values, y, block_ids, stat_fn, oracle_config)`：置換單位＝block（`_permute_blocks(rng, y, block_ids)` 獨立小函式供 M-P3-4 monkeypatch）；沿 `baseline.py::permutation_oracle` 三道硬檢與雙尾經驗 p；`n_blocks < 10` ⇒ 回 `{"status":"unavailable:insufficient_blocks"}`。
  3. 候選＝`passed` 依 `(-abs(rb), feature_name)` 排序；`K=len(passed)`；`n_perm = min(1000, max(200, cfg.perm_budget_total // max(K,1)))`；`budget_floor_hit = (cfg.perm_budget_total < 200*K)`。逐候選跑；`in_band` ⇒ `removed["permutation_oracle_disagree"]`；`unavailable` ⇒ `removed["permutation_unavailable"]`（不得成為 consumable 倖存者）。
  4. 負對照（R2 D2，B＋C）：`n_observed = len(passed_after_step3)`；`if n_observed == 0: negative_control={"status":"skipped:no_survivors"}; 不設 suppressed; return`（R3 短路，先於置亂）；`counts=[]`；`for i in range(cfg.negative_control_n)`（預設 **50**，R3 codex P1-02）`: y_sh=_permute_blocks(rng(cfg.oracle_seed+i), y, block_ids); tbl_sh=mann_whitney_table(X, y_sh, ...); q_sh=apply_fdr(...); counts.append(int(sum((q_sh<=alpha) & (abs(rb_sh)>=cfg.rank_biserial_min))))`；`q95 = int(np.quantile(counts, 0.95, method="higher"))`（整數 order statistic，禁插值）；`n_observed <= q95` ⇒ `self._survivor_suppressed_reason="negative_control_failed"`（Task 3.8）；一律寫 `metadata.event_label_rule.negative_control={n_observed, shuffled_counts: counts, q95, seed_base, block_len}`。consumable 放行仍以要點 3 之 per-survivor block permutation 為準（特徵級 fail-closed）。
- 修改檔案：`momentum/Analysis/binary_discrimination.py::block_ids_for_events`／`block_permutation_oracle`／`_permute_blocks`（新）；`momentum/Analysis/ic_filter_orchestrator.py` stage5 binary 分支末。既有 caller：`baseline.py::permutation_oracle` 不改。
- 路徑：
  - momentum/Analysis/binary_discrimination.py
  - momentum/Analysis/ic_filter_orchestrator.py
  - tests/momentum/Analysis/test_evtlabel_oracle.py
  - handoffs/20260910-probe-oracle-bench.py
- 不可做：置換 p 不取代 MW p；不對全表跑置換；不改 `baseline.py`。
- 邊界：①倖存者 0 ⇒ `skipped:no_survivors`；②`budget_floor_hit`；③`n_blocks<10`。
- 風險緩解：M-P3-4、M-P3-6。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_oracle.py -q` rc=0：植入特徵留下；植入 fixture（200 合成特徵×真實 kline 165 列，含 1 植入）⇒ `n_observed > q95(counts)`、survivor 可寫；全 null fixture ⇒ `n_observed <= q95` ⇒ `survivor_output.status=="suppressed"`、`reason=="negative_control_failed"`、無 consumable 檔；monkeypatch `_permute_blocks` 恆等 ⇒ raise；`L=3` fixture ⇒ 置換後同 block 標籤仍相鄰；密集段 fixture（前 10 事件 gap=1、後段 gap=20、W=12）⇒ `L>=12`（`test_dense_cluster_block_len`）；W=156／median_gap=1 ⇒ `n_blocks<10`、`unavailable:insufficient_blocks`、無 consumable；benchmark 兩道（R3 codex P1-03）：(a) `handoffs/20260910-probe-oracle-bench.py` K=2000、budget 200000、39,373×165 `< 120s`；(b) `handoffs/20260910-probe-mw-bench.py 31 39373 50` 之 clean 與 10% NaN 路徑各 `< 120s`；任一超時 **測試 FAIL**。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.8 — 倖存者輸出帶標籤來源（`票 EVTLABEL-④`）
- SPEC ref：Task 3.8　目標：`sample_scope.event.label_source="imported_binary_label"`＋`label_binary`＋`statistic_kind`。
- 輸入 / 輸出：`event_context`、`event_info`、`staged`（`import_id`、`n_pos`、`n_neg`、`label_origin_values`）→ survivor payload。
- 實作要點：
  1. `build_survivor_output`：`label_source = event_info["label_source"]`；`label_binary = {...}` iff binary else `None`；`statistic_kind = event_info["statistic_kind"]`。
  2. `label_origin_values = sorted({r.get("label_origin") for r in records})` 由 service 放進 `event_context`（經 `event_context_for_analysis` 出口，不在 service 自寫 hash）。
  3. `return_rule`／全域 payload 逐位元組不變（G-6 golden；定案：`label_binary` 與 `statistic_kind` 兩鍵**只在 binary 下寫**，非 binary payload 一鍵不加）。
  4. suppressed（R1 C3）：orchestrator 帶 `_survivor_suppressed_reason="negative_control_failed"` ⇒ `report_meta["survivor_output"]={status:"suppressed", reason:"negative_control_failed", path:None, sha256:None, case_id:...}`，`_write_survivor_output` 不落檔；`_survivor_reason` 詞彙表含此值（Task 3.1）。
- 修改檔案：`momentum/Analysis/survivor_contract.py::build_survivor_output`（`:411-700`）、`validate_survivor_output`；`momentum/Analysis/event_samples/pipeline.py::event_context_for_analysis`（加 `label_origin_values`）。既有 caller：`_write_survivor_output`。
- 路徑：
  - momentum/Analysis/survivor_contract.py
  - momentum/Analysis/event_samples/pipeline.py
  - tests/momentum/Analysis/test_survivor_contract.py
  - tests/momentum/Analysis/test_gap2_survivor_persist.py
- 不可做：不改 `sample_scope_kind_values`；不改檔路徑規則。
- 邊界：①倖存者 0 ⇒ stub 仍寫 `sample_scope`；②掃描格不寫。
- 風險緩解：⊘
- **驗證**：`pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_gap2_survivor_persist.py -q` rc=0；binary run 倖存者檔 `label_source=="imported_binary_label"`、`label_binary.n_pos==136`；缺 `import_id` ⇒ raise。
- **存活至**：全票完工後保留（ML 交接物）。
- **覆蓋風險**：無。

### Task 3.9 — 前端模式選擇＋表格欄＋揭露（`票 EVTLABEL-④`）
- SPEC ref：Task 3.9　目標：三選模式；binary 版面；行 4「已用」；banner 原因。
- 輸入 / 輸出：`config.event_label_mode`、`report.summary_table[0]` 鍵、`metadata.label_mode`、`metadata.event_label_rule` → UI。
- 實作要點：
  1. `EventBatchDisclosurePanel`：radio `ic-param-label-mode`（auto／return_rule／imported_binary），旁顯示 `正 ${n_pos}／反 ${n_neg}`（自 batch facts `label`）；`imported_binary` 選中時 scan 區停用並提示。
  2. `ICSummaryTable`：`isBinary = 'rank_biserial' in rows[0]`；binary 欄序 `feature_name, rank_biserial, auc, mw_p_value, mw_p_value_adj, n_pos, n_neg, | ic_mean(第二欄), t_stat, p_value_adj, …`；表頭文案由 `icLabelRule.ts::binaryColumnLabels()` 單點。
  3. `icLabelRule.ts` 行 4 `used=true` 文案（Task 1.2 已留分支）。
  4. `DegradedBanner`：`metadata.label_mode.effective==='return_rule' && requested==='auto' && reason` ⇒ 顯示 `已自動改用報酬規則：${reasonText[reason]}`（reason 文案表由 JSON `label_mode_reasons` 匯出至前端常數，vitest 對證）；`survivor_output.status==='suppressed' && reason==='negative_control_failed'` ⇒ 紅色 banner「負對照失敗：本次倖存者不可餵 ML」。
  5. 新 `LabelModeBanner`（`data-testid="label-mode-banner"`，R1 C14b）：`effective==='imported_binary'` ⇒ 非 degrade 之摘要「本次 IC 對象＝你匯入的 0/1 標籤（selection 段正 n_pos_selection／反 n_neg_selection）；報酬版 IC 在第二欄」；`permutation_receipt.status==='unavailable:insufficient_blocks'` ⇒ 琥珀 banner「label 視窗太長、可置換區塊不足：無法做依賴感知放行，倖存者不可餵 ML（預期限制）」（R2 D3）；掛 `page.tsx` `DegradedBanner` 之後。
- 修改檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`、`ICSummaryTable.tsx`、`DegradedBanner.tsx`、`IsolationNote.tsx`、`frontend/src/lib/icLabelRule.ts`、`frontend/src/lib/types.ts`、`frontend/src/store/icAnalysisStore.ts`。既有 caller：`ICSummaryTable.paging.test.tsx`（欄動態）。
- 路徑：
  - frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx
  - frontend/src/components/ic-analysis/ICSummaryTable.tsx
  - frontend/src/components/ic-analysis/ICSummaryTable.binary.test.tsx
  - frontend/src/components/ic-analysis/DegradedBanner.tsx
  - frontend/src/components/ic-analysis/DegradedBanner.test.tsx
  - frontend/src/components/ic-analysis/IsolationNote.tsx
  - frontend/src/lib/icLabelRule.ts
  - frontend/src/lib/types.ts
  - frontend/src/store/icAnalysisStore.ts
- 不可做：前端不算統計；不隱藏報酬版欄。
- 邊界：①舊報告 ⇒ 版面不變；②`reason=one_class` ⇒ banner。
- 風險緩解：⊘
- **驗證**：`cd frontend && npx vitest run src/components/ic-analysis` rc=0；binary 報告首數值欄 `rank-biserial` 且含 `第二欄`；return_rule 表頭 snapshot 同改前；`npm run build` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.10 — 真實 kline 端到端（`票 EVTLABEL-④`）
- SPEC ref：Task 3.10　目標：三方簽核之可證偽 oracle。
- 輸入 / 輸出：`data_cache/feature_klines/kline_cache.h5` ETHUSDT 12h／1h → 事件批（t₀＝12h 根、label＝`close[t0+1]/close[t0]-1 ≥ 2%`）＋小特徵集（或既有 1h feature run）→ 兩模式報告。
- 實作要點：
  1. 探針建 records（含 `label`、`label_value`、`lookahead_bars_declared={"12h":0}`）；跑 `return_rule` 與 `imported_binary`。
  2. 斷言（R1 C11，無 sign oracle）：(i) 兩模式事件身分 parity（`consumed_event_count`、event_id 集合、對應 ts 逐位元組）；(ii) 兩模式 `ic_mean`／`t_stat`／`p_value` 逐特徵相等；(iii) 植入單調特徵 `feat_planted(t0)=close_12h(t0+1)/close_12h(t0)`（與 label 規則同源）⇒ `auc==1.0`、`passed`；(iv) label 往前錯一事件 ⇒ `AlignmentViolationError`；(v) 三方各自實跑探針附 receipt。
  3. 印 receipt：事件數、n_pos/n_neg（全批／selection）、倖存者數、`negative_control`、`permutation_receipt.block_len／n_blocks`。
- 修改檔案：`tests/momentum/Analysis/test_evtlabel_e2e_realkline.py`、`handoffs/20260910-probe-evtlabel-e2e.py`。既有 caller：無。
- 路徑：
  - tests/momentum/Analysis/test_evtlabel_e2e_realkline.py
  - handoffs/20260910-probe-evtlabel-e2e.py
- 不可做：禁合成價格；禁用 `data_cache/events/*` 當 fixture。
- 邊界：①cache 缺 ETHUSDT ⇒ `pytest.skip` 印明；②事件不足 ⇒ 測試自建足量。
- 風險緩解：三方簽核鐵律（Claude＋Codex＋Composer＋Grok 各自實跑探針）。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_e2e_realkline.py -q` rc=0；探針 rc=0 並印 receipt。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.11 — 倖存者檔之 ML 消費契約測試（`票 EVTLABEL-④`）
- SPEC ref：Task 3.11（R1 C13）　目標：證明 binary survivor payload 是既有純函式 consumer 可接收的 ML 輸入。
- 輸入 / 輸出：Task 3.10 之 binary run survivor payload（＋`return_rule` payload、suppressed stub）→ `pattern_bridge` `survivor_v2` 入口之接收結果。
- 實作要點：
  1. 讀 `momentum/Analysis/event_samples/pattern_bridge.py:52-64,89-105` 之 `survivor_v2` 入口簽名；以 Task 3.10 探針落地之 payload 餵入。
  2. 斷言：接收成功；`sample_scope.event.label_source=="imported_binary_label"`；`label_binary` 四鍵保留；倖存特徵集合 == payload `survivors`。
  3. `return_rule` payload：接收成功、`label_binary is None`；suppressed stub（無 `survivors` 鍵）⇒ 既有 `_survivor_feature_names` raise（`pattern_bridge.py:20-21`）；倖存者 0 之空 `survivors[]` ⇒ 既有 raise（`:24`）；`schema_version=1` ⇒ 既有 raise（`:17-18`）。三者只釘住，不改。
- 修改檔案：`tests/momentum/Analysis/test_evtlabel_survivor_consumer.py`（新）。既有 caller：無；**不改** `pattern_bridge.py`。
- 路徑：
  - tests/momentum/Analysis/test_evtlabel_survivor_consumer.py
  - momentum/Analysis/event_samples/pattern_bridge.py
- 不可做：不接 ML 訓練殼、不加 API caller、不改 consumer 行為。
- 邊界：①倖存者 0 之空 `survivors[]` ⇒ 既有 loud raise；②`schema_version=1` ⇒ 既有 validator 拒收；③suppressed stub 無 `survivors` 鍵 ⇒ 既有 raise。
- 風險緩解：⊘
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_survivor_consumer.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_survivor_consumer.py -q -k suppressed_not_consumable WHEN survivor_status=suppressed THEN rc=0`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase 3 測試＋Gate
單元：3.5、3.1。整合：3.3、3.4、3.6、3.7、3.8、3.11。Golden：G-1、G-4、G-6（B4 動工前凍結）。端到端：3.10。前端：3.2、3.9＋`npm run build`。Mutation：M-P3-1..7。
Gate：`bash scripts/evtlabel_phase_gate.sh 3a`（B3）／`3b`（B4）／`3c`（B5＋B6）各 rc=0；每批三家 code review 收斂後才進下一批。

---

## 收尾（全票）
- `docs/IC_QUANT_GAP_REGISTRY.md` 登記 R-1..R-6（三值理由）；ROADMAP pointer；HANDOFF ≤30 行；`白話說明/現在做到哪.md` 更新；`bash scripts/restore_golden_inventory.sh`。
- 之後才排 B26–B34＋新增項目之使用者驗收（本票不叫使用者驗收）。
