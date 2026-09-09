# EVTLABEL — TODO

**SPEC**：`docs/EVTLABEL_SPEC.md`　**票**：`EVTLABEL`　**日期**：2026-09-10　**狀態**：DRAFT（待三家 adversarial R1）
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
| **B4** | 3.4, 3.5, 3.6, 3.7 | B3 | orchestrator 核心（綁定→統計→門檻→自檢）；`[A-2]`、`[A-3]` 先跑 | 大 |
| **B5** | 3.8, 3.9 | B4 | 倖存者輸出＋前端（依 B4 定案之欄名） | 中 |
| **B6** | 3.10 | B5 | 真實 kline 端到端＋三方簽核 oracle | 中 |

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
  3. placeholder：`tests/api/test_evtlabel_disclosure.py`、`tests/momentum/event_samples/test_isolation_terms.py`、`tests/api/test_evtlabel_staging.py`、`tests/momentum/Analysis/test_evtlabel_stage3.py`、`tests/momentum/Analysis/test_binary_discrimination.py`、`tests/momentum/Analysis/test_evtlabel_stage5.py`、`tests/momentum/Analysis/test_evtlabel_oracle.py`、`tests/momentum/Analysis/test_evtlabel_e2e_realkline.py`、`tests/momentum/Analysis/test_event_label_mode_contract.py`。
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
- **驗證**：`bash scripts/evtlabel_phase_gate.sh 0` rc=0；`bash scripts/evtlabel_phase_gate.sh 1` rc=1（全 skip ⇒ 不通過）；`venv/bin/python handoffs/20260910-evtlabel-mutate.py --list` 印 6 條 mutation ID（M-P2-1..2、M-P3-1..4）。
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
  4. service `_stage_event_batch` 回傳新增 `label_window_rows`、`lookahead_depth_rows`；兩注入點改 `embargo=max(config.embargo, lookahead_depth_rows)`、`event_purge_rows=label_window_rows`。
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

### Task 2.2 — split purge 吃 `event_purge_rows`（`票 EVTLABEL-②`）
- SPEC ref：Task 2.2　目標：`purge_gap=max(effective_horizon, event_purge_rows)`；metadata 四新鍵。
- 輸入 / 輸出：`config_override["event_purge_rows"]: Optional[int]`（**定案：走 config_override**，不新增 analyze kwarg——兩路徑已用 `config_override` 傳 embargo，同通道）→ `metadata["ic_train_test_split"]` 新增 `purge_gap_source`、`event_label_window_rows`、`embargo_source`、`lookahead_depth_rows`。
- 實作要點：
  1. orchestrator 讀 `config_override.pop("event_purge_rows", None)`／`pop("lookahead_depth_rows", None)`（pop 後再建 ICConfig，避免 schema `extra=forbid` 紅；若 ICConfig 允許 extra 則改為顯式欄位——TODO 執行時以實跑定）。
  2. `:1102-1160`：`purge_gap = max(effective_horizon, int(event_purge_rows or 0))`；`purge_gap_source = "event_label_window" if event_purge_rows and event_purge_rows > effective_horizon else "mainline_horizon"`；`embargo_source = "event_lookahead_depth" if (lookahead_depth_rows or 0) > config_embargo_before_override else "config_embargo"`（`config_embargo_before_override` 由 service 以 `config_override["embargo_before_event"]`… **不**——orchestrator 不知原值；改由 service 在 `_inject_isolation_source` 寫 `embargo_source`，orchestrator 只寫 `purge_gap_source`、`event_label_window_rows`、`lookahead_depth_rows`）。
  3. `_run_full_sample_fallback` 路徑亦 pop 兩鍵（不用，但不得殘留進 ICConfig）。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::analyze`（config_override 處理處）、`:1102-1160` split 建立與 metadata 寫入。既有 caller：`_build_holdout_split_plan` 簽名不變。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - handoffs/20260907-probe-split-baseline.py
  - tests/golden/evtalign/split_baseline.json
  - tests/momentum/Analysis/test_ic_1a_cut1_split.py
- 不可做：不改 `_resolve_effective_label_horizon`；不在 orchestrator 換算 ms；不動 embargo 語意。
- 邊界：①purge 過大 ⇒ `SkippedResult(INSUFFICIENT_DATA)` 既有路徑；②非事件 ⇒ 逐位元組同前；③`event_purge_rows<effective_horizon` ⇒ `mainline_horizon`。
- 風險緩解：G-2／G-3；M-P2-1。
- **驗證**：`venv/bin/python handoffs/20260907-probe-split-baseline.py --diff` 三條通過條件（SPEC G-2）；`--write` 後新 sha 記於本檔 B2 收尾；G-3 重現 `purge_gap=12`；`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/core/test_split_contract.py tests/golden/ic_phase1_contract -q` rc=0；`ASSERT venv/bin/python handoffs/20260907-probe-split-baseline.py --check WHEN group=global THEN rc=0`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.3 — 隔離區來源改讀新鍵（`票 EVTLABEL-②`）
- SPEC ref：Task 2.3　目標：`metadata.isolation` 與前端文案反映真實來源。
- 輸入 / 輸出：`ic_train_test_split`（新鍵）＋`staged` → `isolation.purge.source ∈ {mainline_horizon, event_label_window}`、`isolation.embargo.source ∈ {config_embargo, event_lookahead_depth}`。
- 實作要點：
  1. `_inject_isolation_source`：`purge.source = split.get("purge_gap_source") or "global_default_horizon"`；`purge.note` 改為 `f"purge {bars} 根＝max(主線 horizon {eff}, label 視窗 {win} 根)"`；`embargo.source = "event_lookahead_depth" if staged["lookahead_depth_rows"] > staged["embargo_before_event"] else "config_embargo"`；保留 `event_purge_rows`（改名不做，值＝`lookahead_depth_rows`？**不**——新增 `lookahead_depth_rows` 鍵，`event_purge_rows` 保留舊值供對照）。
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
單元：`test_isolation_terms.py`。整合：`test_isolation_disclosure.py`、split 三檔。Golden：G-1、G-2（`--diff`→`--write`）、G-3。Mutation：M-P2-1、M-P2-2（mutate 腳本）。Gate：`bash scripts/evtlabel_phase_gate.sh 2` rc=0。

---

## Phase 3 — 匯入標籤模式（完成後：`imported_binary` 下 IC 直接對 0/1 算、報酬版第二欄、倖存者帶標籤來源；`return_rule`／全域逐位元組不變）

### Task 3.1 — 枚舉 SoT＋契約（`票 EVTLABEL-④`）
- SPEC ref：Task 3.1　目標：所有新枚舉一檔定義；`derive_label_kind`／survivor contract 接新值。
- 輸入 / 輸出：無 → `event_label_mode.json` 補齊鍵：`label_modes`、`label_sources`（含 `imported_binary_label`）、`statistic_kinds`（含 `binary_discrimination`、`binary_discrimination_unavailable`）、`label_mode_reasons`、`summary_columns_binary`、`binary_status_values`、`threshold_skip_keys_binary`、`min_events_per_class_default`；`ic_survivor_contract.json` `sample_scope.event` 新增 `label_binary`（nullable 物件：`import_id`／`n_pos`／`n_neg`／`label_origin_values`）與 `statistic_kind`；`ic_config_schema.py::EventFilterConfig.min_events_per_class: int = 10`。
- 實作要點：
  1. `momentum/core/contracts.py:1030`：`LABEL_KIND_BY_SOURCE["imported_binary_label"] = LABEL_KIND_EVENT_GIVEN`；測試以 JSON `label_sources` 對證 Python dict 鍵集。
  2. `survivor_contract.py::validate_survivor_output`：`label_source=="imported_binary_label"` ⇒ 六鍵非 null **且** `label_binary` 非 null 且四子鍵齊；其他 label_source ⇒ `label_binary` 必為 null。
  3. `_load_contract()` 讀 JSON 缺鍵 ⇒ import 期 raise。
- 修改檔案：`momentum/Analysis/contracts/event_label_mode.json`、`momentum/Analysis/contracts/ic_survivor_contract.json`、`momentum/core/contracts.py::LABEL_KIND_BY_SOURCE`、`momentum/Analysis/survivor_contract.py::validate_survivor_output`、`momentum/Analysis/ic_config_schema.py::EventFilterConfig`。既有 caller：`validate_survivor_output` 既有呼叫（return_rule payload `label_binary=null` ⇒ 通過）。
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
- SPEC ref：Task 3.3　目標：與 `ts_map` 同鍵之 0/1 向量；`label_mode_effective`。
- 輸入 / 輸出：`records`（含 `label`）、`prepared1.windows` → `staged["event_binary_labels"]: Dict[int,int]`、`staged["event_binary_label_by_id"]: Dict[str,int]`、`staged["label_mode_effective"]`、`staged["label_mode_reason"]`；`metadata["label_mode"] = {requested, effective, reason, n_pos, n_neg}`（由 `_inject_label_mode(staged, report)` 寫，事件路徑限定）。
- 實作要點：
  1. `:705-724` 迴圈內：`lab = rec_by_id[w.event_id].get("label")`；`imported_binary` 顯式且 `lab is None` ⇒ raise；否則 `lab is not None` 時 `bin_map[key]=int(lab)`、`bin_by_id[event_id]=int(lab)`。
  2. 解析：`n_pos, n_neg` 自 `bin_by_id`；`auto` ⇒ `imported_binary` iff `present and min(n_pos,n_neg) >= cfg.min_events_per_class` else `return_rule` + reason（`no_label_column`／`one_class`／`class_below_min`）；顯式 `imported_binary` 條件不足 ⇒ raise（route 轉 422）。
  3. `imported_binary` 下 `event_label_scan` 非空 ⇒ raise `scan_not_applicable_in_imported_binary_mode`。
  4. 兩注入點 `config_override["event_label_mode"]=effective`、`analyzer.analyze(..., event_binary_labels=bin_map if effective=="imported_binary" else None)`（kwarg 新增於 orchestrator `analyze`／`_run_full_sample_fallback`）。
  5. `_assert_event_triple_bound` 新增分支：`effective=="imported_binary"` ⇒ 回比 `event_filter.consumed_event_binary_labels` vs `bin_by_id`。
- 修改檔案：`api/services/ic_analysis_service.py::_stage_event_batch`、`_run_event_label_stages`（兩注入點）、`_assert_event_triple_bound`、`_inject_label_mode`（新）。既有 caller：`_stage_event_batch` 回傳 dict 只加鍵。
- 路徑：
  - api/services/ic_analysis_service.py
  - tests/api/test_evtlabel_staging.py
- 不可做：不改 `ts_map` 鍵；不在此算統計。
- 邊界：①legacy 無 `label` ⇒ `return_rule/no_label_column`；②`label` 缺值混雜且顯式 binary ⇒ raise；③symbol 過濾後單類 ⇒ `one_class`。
- 風險緩解：⊘
- **驗證**：`pytest tests/api/test_evtlabel_staging.py -q` rc=0：165 批（測試自建 records）⇒ `effective=="imported_binary"`、`n_pos==136`、`n_neg==29`、鍵集相等；全 1 ⇒ `return_rule/one_class`；`ASSERT venv/bin/python -m pytest tests/api/test_evtlabel_staging.py -q -k explicit_binary_one_class WHEN label_mode=imported_binary THEN rc=0`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.4 — stage3 binary 綁定與驗證（`票 EVTLABEL-④`）
- SPEC ref：Task 3.4　目標：binary 向量對齊 filtered index 並過 `validate_event_given`。
- 輸入 / 輸出：`event_binary_labels: Dict[int,int]` → `self._ic_cache["event_binary_label"]: pd.Series(float, index=filtered.index)`；`event_info` 新鍵 `consumed_event_binary_labels`、`label_source="imported_binary_label"`、`statistic_kind="binary_discrimination"`、`secondary_statistic="conditional_ic"`。
- 實作要點：
  1. `_stage3_event_filter` `:3450-3462` 之後：`if event_binary_labels is not None: bvals=[float(event_binary_labels[int(t)]) if int(t) in event_binary_labels else nan ...]`；NaN 任一 ⇒ raise。
  2. `validate_consumed_label(filtered_features, pd.Series(bvals, index=...), label_source="imported_binary_label", expected_values=event_binary_labels, event_owners=owners)` `[A-3]`；回傳之 `consumed_event_labels` 存為 `event_info["consumed_event_binary_labels"]`。
  3. 報酬 label 既有驗證與 `consumed_event_labels` 鍵**不動**。
  4. fallback（`conditional_ic_abandoned`）⇒ `statistic_kind="binary_discrimination_unavailable"`、binary 不綁。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_stage3_event_filter`（`:3348-3480`）、`analyze`／`_run_full_sample_fallback` 簽名（`event_binary_labels=None`）。既有 caller：`api/services/ic_analysis_service.py`（Task 3.3）。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - tests/momentum/Analysis/test_evtlabel_stage3.py
- 不可做：不覆寫 `consumed_event_labels`。
- 邊界：①fallback ⇒ unavailable；②NaN ⇒ raise。
- 風險緩解：`[A-3]`；M-P3-3。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q` rc=0：錯位一格 ⇒ `AlignmentViolationError`；`return_rule` 鍵集 == 改前；binary 值集 ⊆ {0.0,1.0}。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.5 — `mann_whitney_table`（`票 EVTLABEL-④`）
- SPEC ref：Task 3.5　目標：向量化 MW／AUC／rank-biserial。
- 輸入 / 輸出：`features: pd.DataFrame (n×p)`、`y: np.ndarray[int] (n,)`、`min_class_n:int` → `pd.DataFrame(index=feature, columns=[auc, rank_biserial, mw_u, p_value, n_pos, n_neg, n_used, status])`。
- 實作要點：
  1. `mask_finite = np.isfinite(X)`（p 欄）；`clean = mask_finite.all(axis=0)`；對 `clean` 欄一次 `mannwhitneyu(X[y==1][:,clean], X[y==0][:,clean], alternative="two-sided", method="auto", axis=0)`；對非 clean 欄逐欄以自身 finite 列子集呼叫。
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
- SPEC ref：Task 3.6　目標：主統計 `rank_biserial`、p 走 MW→BH；報酬版保留第二欄。
- 輸入 / 輸出：`self._ic_cache["event_binary_label"]`、test split 事件列之 features → summary_table 每列新增 `auc, rank_biserial, mw_u, mw_p_value, mw_p_value_adj, n_pos, n_neg, n_used_binary`（欄名＝JSON `summary_columns_binary`）；`metadata.event_label_rule.primary_statistic="rank_biserial"`、`secondary_statistic="ic_mean"`、`imported_binary_label.used=True`。
- 實作要點：
  1. stage5 事件分支（`:3766-3900`）在既有 HAC 迴圈後：`tbl = mann_whitney_table(features_test[feature_cols], y_test, min_class_n=cfg.min_events_per_class)`；逐列合併到 `summary_table`。
  2. `apply_fdr({name: mw_p}, alpha, method)` → `mw_p_value_adj`（既有 `p_value_adj` 仍為報酬版 q）。
  3. `_apply_thresholds(..., primary_field="rank_biserial", p_field_override="mw_p_value_adj")`：`ic_mean_min` 閘讀 `primary_field`；`removed["ic_mean_skipped_binary_mode"]`／`["ic_hit_rate_skipped_binary_mode"]`／`["monotonicity_skipped_binary_mode"]` 記錄不剔除（鍵名＝JSON `threshold_skip_keys_binary`）；`status!="ok"` 之列 ⇒ `removed["binary_unavailable"]`。
  4. 排序：binary 模式 `|rank_biserial|` desc（NaN 置底）。
  5. `return_rule`／全域：不呼叫 3.5、欄集不變、`_apply_thresholds` 預設參數一字不改。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 事件分支、`_apply_thresholds`（`:4360-4400`，加兩個帶預設值的 kwarg）、`_inject_label_rule_disclosure` 更新 `used`／`primary_statistic`（service）。既有 caller：`_apply_thresholds` 既有呼叫不改參數。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - api/services/ic_analysis_service.py
  - tests/momentum/Analysis/test_evtlabel_stage5.py
- 不可做：不把 `rank_biserial` 寫進 `ic_mean`；不動全域路徑。
- 邊界：①test 單類 ⇒ 全表 unavailable、倖存者 0、`degraded` loud；②pooled fallback 與 binary 並存；③`n_tests=0` 不除零。
- 風險緩解：M-P3-2；G-4。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q` rc=0：植入特徵 `passed` 且 `mw_p_value_adj<0.05`；`p_value_max=0.001` ⇒ 弱特徵 `removed["p_value"]`；`return_rule` 欄集 == 改前；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q -k threshold_reads_rank_biserial WHEN label_mode=imported_binary THEN rc=0`；G-1、G-4。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.7 — 置換自檢＋負對照（`票 EVTLABEL-④`）
- SPEC ref：Task 3.7　目標：倖存者逐一置換重驗（fail-closed）；整批置亂負對照（揭露）。
- 輸入 / 輸出：倖存者名單、`features_test`、`y_test` → `removed["permutation_oracle_disagree"]`；`metadata.event_label_rule.permutation_receipt`、`.negative_control={n_survivors_shuffled, seed}`；`warnings += ["negative_control_nonzero"]` if >0。
- 實作要點：
  1. `for name in passed: o = permutation_oracle(X[name], y, auc_fn, OracleConfig(n_perm=cfg.n_perm, seed=cfg.seed))`；`o["in_band"]` ⇒ 移出。
  2. 負對照：`y_sh = rng(seed).permutation(y)`；`tbl_sh = mann_whitney_table(...)`；`q_sh = apply_fdr(...)`；`n_survivors_shuffled = sum(q_sh<=alpha and |rb|>=ic_mean_min)`。
  3. `OracleConfig`／`n_perm` 自 `EventFilterConfig`（新欄 `n_perm:int=1000`、`oracle_seed:int=20260910`，加入 3.1 JSON/schema）；`n_perm<200` ⇒ raise。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 binary 分支末；`momentum/Analysis/ic_config_schema.py::EventFilterConfig`。既有 caller：`baseline.py::permutation_oracle` 不改。
- 路徑：
  - momentum/Analysis/ic_filter_orchestrator.py
  - momentum/Analysis/ic_config_schema.py
  - tests/momentum/Analysis/test_evtlabel_oracle.py
- 不可做：置換 p 不取代 MW p；不對全表跑置換。
- 邊界：①倖存者 0 ⇒ `skipped:no_survivors`；②`n_perm<200` ⇒ raise。
- 風險緩解：M-P3-4。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_oracle.py -q` rc=0：植入特徵留下；固定 seed 置亂 fixture（200 合成特徵×真實 kline 165 列）⇒ `n_survivors_shuffled==0`；monkeypatch `_permute` 恆等 ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.8 — 倖存者輸出帶標籤來源（`票 EVTLABEL-④`）
- SPEC ref：Task 3.8　目標：`sample_scope.event.label_source="imported_binary_label"`＋`label_binary`＋`statistic_kind`。
- 輸入 / 輸出：`event_context`、`event_info`、`staged`（`import_id`、`n_pos`、`n_neg`、`label_origin_values`）→ survivor payload。
- 實作要點：
  1. `build_survivor_output`：`label_source = event_info["label_source"]`；`label_binary = {...}` iff binary else `None`；`statistic_kind = event_info["statistic_kind"]`。
  2. `label_origin_values = sorted({r.get("label_origin") for r in records})` 由 service 放進 `event_context`（經 `event_context_for_analysis` 出口，不在 service 自寫 hash）。
  3. `return_rule`／全域 payload 逐位元組不變（新鍵 `label_binary=null`、`statistic_kind` 抄既有值——若既有 payload 無 `statistic_kind` 則此鍵**只在 binary 下寫**以保 golden；在 TODO 執行時以 `test_gap2_survivor_persist` 實跑定）。
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
  4. `DegradedBanner`：`metadata.label_mode.effective==='return_rule' && requested==='auto' && reason` ⇒ 顯示 `已自動改用報酬規則：${reasonText[reason]}`（reason 文案表由 JSON `label_mode_reasons` 匯出至前端常數，vitest 對證）。
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
  2. 斷言 (i) `|ic_mean|` 前 20 名 `sign(rank_biserial)==sign(ic_mean)`；(ii) 兩模式 `ic_mean` 逐特徵相等；(iii) label 往前錯一事件 ⇒ `AlignmentViolationError`。
  3. 印 receipt：事件數、n_pos/n_neg、倖存者數、`negative_control`。
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

### Phase 3 測試＋Gate
單元：3.5、3.1。整合：3.3、3.4、3.6、3.7、3.8。Golden：G-1、G-4。端到端：3.10。前端：3.2、3.9＋`npm run build`。Mutation：M-P3-1..4。
Gate：`bash scripts/evtlabel_phase_gate.sh 3a`（B3）／`3b`（B4）／`3c`（B5＋B6）各 rc=0；每批三家 code review 收斂後才進下一批。

---

## 收尾（全票）
- `docs/IC_QUANT_GAP_REGISTRY.md` 登記 R-1..R-6（三值理由）；ROADMAP pointer；HANDOFF ≤30 行；`白話說明/現在做到哪.md` 更新；`bash scripts/restore_golden_inventory.sh`。
- 之後才排 B26–B34＋新增項目之使用者驗收（本票不叫使用者驗收）。
