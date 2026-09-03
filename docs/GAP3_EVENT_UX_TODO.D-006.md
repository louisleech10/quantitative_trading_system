# GAP3_EVENT_UX_TODO — D 延伸 006（`G3-D2` 灰色項目完成：五 phase 施工清單；基於 `docs/GAP3_EVENT_UX_SPEC.D-001.md`）

BASE: docs/GAP3_EVENT_UX_TODO.md @ 4dc7bac5
PREDECESSOR: none（D-001…D-005 已 SUPERSEDED-BY-R；編號不重用）

改什麼: 為 SPEC 延伸 D-001 之 15 個 Task（D1.1–D1.6、D2.1、D3.1、D4.1–D4.3、D5.1–D5.4；R1 更正計數）產生冷啟動可寫碼之施工清單，五 phase＝五批，每批三家 code review 至閉合。

為什麼: `docs/IC_QUANT_GAP_REGISTRY.md` `G3-D2`（user-ruling 2026-08-31／09-02）；SPEC 延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md` 對抗審 r1–r4 收斂（`handoffs/reconcile/20260903-gap3d2-x-review-r4/synth.md`；grok／codex APPROVED，composer 待補）。

## 觸及面宣告
新增: 無新增原檔 heading；本檔 Task 以 `D` 前綴編號。
覆寫: none（原檔 Task 7.0b／7.1／7.2／7.3／7.6 之產出為本檔輸入，不改其條文）。
依賴: **### Task 7.0b — 分析時 `label_value` producer 與其 wiring（`票 #3-全棧`）**；**### Task 7.1 — 五維度全部接出前端（依賴 7.0）（`票 #3-全棧`）**；**### Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（`票 #3-全棧`）**。

## 內容

## §0 全域規則與約束（執行端讀完即可遵守）
- 實作者＝Claude 主委自任（ORCH §1 現行分工行）；每批完成後三家 code review（codex＋composer＋grok）至閉合；實作者不自審。
- 解耦 7 條：`momentum/` 不 import `api/`；服務不互 import；契約單一真相源＝`momentum/Analysis/contracts/event_import_contract.json`；前端鏡像 `EVENT_DIM_CONTRACT_MIRROR` 由既有 `eventContractOptions.test.tsx` 防漂移。
- 資料鐵律：golden／測試一律真實 `data_cache/feature_klines/kline_cache.h5`（ETHUSDT 12h／1h），禁合成 fixture；跳空案例須先斷言 `open(t₀) != close(t₀−1)`。
- 防假綠：既有斷言不得放寬（`test_analysis_label_producer_03/05` 於 P1–P3 不動，P4 改時附 diff）；每個新測試須 mutation 自證（改壞→紅），提交前實跑貼 rc；rc 直接取禁經 pipe。
- 引用 SPEC D-001 §A 三題（甲／乙／丙）＝委員共識、使用者可否決；實作不得偏離。
- 不可違反：不弱化 NaN／inf gate、不改輸出大小、無 fallback 分支、單一映射只在 `align_events`。
- Logging：`get_logger(__name__)`，producer／對齊迴圈內不 log。

## §B 批次執行策略（依賴拓撲 → 五批；每批＝一次實作＋三家 review）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B-D1 | D1.1 D1.2 D1.3 D1.4 D1.5 D1.6 | 無 | B 之可選＋provenance＋golden 機制同一交付 | 大 |
| B-D2 | D2.1 | B-D1 | A 只差解灰＋未標籤路徑 | 小 |
| B-D3 | D3.1 | B-D1 | two_stage 同 D2 形態 | 小 |
| B-D4 | D4.1 D4.2 D4.3 | B-D1（golden loader）；**串行於 B-D3 之後**（R1 P2-03：B-D2／B-D3／B-D4 皆改 `frontend/src/lib/eventDimensions.ts` 與 `eventExport.ts`，平行寫檔必衝突；實際順序 B-D1→B-D2→B-D3→B-D4→B-D5） | producer 取價＋全矩陣＋k 參數化互相耦合 | 大 |
| B-D5 | D5.1 D5.2 D5.3 D5.4 | B-D4（producer）、B-D1（loader） | 隨機對照組全鏈 | 大 |
- 批次間 Gate：前批 `pytest` 指定選擇器全綠＋golden `--check` rc=0＋三家 review CLOSED＋commit 推送；後批才動工。
- 每批派工 prompt：「照 `docs/GAP3_EVENT_UX_TODO.D-006.md` B-D<n> 逐 Task 實作；驗證命令見各 Task；先不 push（review 後 push）」。

## Phase D1 — B（scenario 解灰＋provenance＋`trigger_open × close_to_close`＋golden 機制）

### Task D1.1 — 契約先行：`label_origin`／`scenario_depth_inconsistent`／`entry_price_semantic.default`／`scenario.doc`（`票 G3-D2`）
- SPEC ref：D-001 Task D1.1＋契約字面總表　目標：本票所有新字面唯一住契約檔，validator 與前端鏡像同步。
- 輸入／輸出：`event_import_contract.json`（現行 version 1）→ 同檔新增鍵；`import_contract.py` validator 新規則；前端鏡像同步。
- 實作要點：①`optional_fields.label_origin = {type:"str", enum:[search_positive_case,user_csv,platform_generator,platform_random,search_unlabeled], not_importable:[search_unlabeled], doc}`；②`import_failure_reasons` 增 `scenario_depth_inconsistent`、`label_origin_not_importable`；③`required_fields.entry_price_semantic.default = "trigger_close"`；④`required_fields.scenario.doc` 改誠實描述（D-001 D1.1 ③ 字面）；⑤validator（`validate_event_import`）新規則：`scenario in {A,B,two_stage} and label_origin is None ⇒ conditional_required_missing`；`label_origin in not_importable ⇒ label_origin_not_importable`；`scenario in {A,two_stage} and max(lookahead_bars_declared.values()) < 1 ⇒ scenario_depth_inconsistent`（缺 map 時沿用 D-7 L2 既有拒收，reason 不覆蓋）；⑥`frontend/src/lib/eventDimensions.ts::EVENT_DIM_CONTRACT_MIRROR` 逐鍵同步。
- 修改檔案：`momentum/Analysis/contracts/event_import_contract.json`；`momentum/Analysis/event_samples/import_contract.py::validate_event_import`（規則區）；`frontend/src/lib/eventDimensions.ts::EVENT_DIM_CONTRACT_MIRROR`、`eventContractDocs.ts`。　既有 caller：全部匯入路徑（`EventSamplePipeline.validate`、`generator.py`）——規則僅對 scenario≠C 或帶 `label_origin` 之列生效，既有 C 批不受影響。
- 不可做：不得為缺 `label_origin` 之舊批補值；不得在 validator 硬寫枚舉（讀契約）；不得改 `label`／`decision_offset_bars` 之必填性。
- 邊界：①`scenario=A` 且 `lookahead_bars_declared={}` ⇒ 先命中 D-7 缺宣告拒收；②批內 scenario 混值 ⇒ Task 1.8 拒收先於本規則；③`label_origin=""` ⇒ `enum_violation`。
- 風險緩解：契約 hash 變更 ⇒ `tests/momentum/event_samples/test_import_contract.py` 既有 receipt 相關斷言須重看（不得放寬）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_import_contract.py -q -k "label_origin or scenario_depth or entry_default"` ≥5 條：(i) A＋深度全 0 ⇒ reason `== "scenario_depth_inconsistent"`；(ii) B＋深度 0 ⇒ 通過；(iii) B 缺 `label_origin` ⇒ `conditional_required_missing`；(iv) `search_unlabeled` ⇒ `label_origin_not_importable`；(v) validator 不讀 `entry_price_semantic.default`（缺欄仍 `missing_required_field`）。mutation：刪 validator 規則 ③ ⇒ (i) 紅。前端 `npx vitest run src/lib/eventContractOptions.test.tsx` 鏡像逐鍵相等。
- **存活至**：全票完工後保留。　**覆蓋風險**：無（後續 phase 只擴同表）。

### Task D1.2 — 對齊層寫入 `event_known_at_decision`（`票 G3-D2`）
- SPEC ref：D-001 D1.2　目標：契約 derived 欄落地於 `event_level` receipt，D2-2 下照實 False。
- 輸入／輸出：`align_events` 既有 `ev_rows` → 增一欄 `event_known_at_decision: bool`；契約 `receipt_schema.event_level` 增鍵。
- 實作要點：①`alignment.py::align_events` 於 `ev_rows.append({...})` 增 `"event_known_at_decision": bool(decision_at >= int(ct[t0_idx]))`；②`_EVENT_COLS` 增該欄（末位）；③契約 `receipt_schema.event_level` 增 `event_known_at_decision: "bool"`；④`WindowRow`／`_receipt_hash` **不動**。
- 修改檔案：`momentum/Analysis/event_samples/alignment.py::align_events`、`_EVENT_COLS`；契約 `receipt_schema.event_level`。　既有 caller：`label_value_from_case._windows_from_receipts`（只讀七鍵）、`tables.py`（欄名讀）、`pipeline.py`（欄名讀）——無需改。
- 不可做：不得依 scenario 推導此欄；不得放進 `WindowRow`／hash payload。
- 邊界：①`t0` 在資料末端 ⇒ `label_window_incomplete` 先拒、本欄不寫；②k>0 ⇒ 仍 False。
- 風險緩解：`flatten_receipt_schema` 既有前綴相等斷言須含新欄（更新期望並附 diff）。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q -k event_known` ≥2 條：(i) 真實 kline k∈{0,2} 兩事件皆 `False`；(ii) `ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q -k event_known WHEN mutation=decision_at_close THEN rc!=0`（把 `decision_at` 改 `ct[t0_idx]` ⇒ 既有 `decision_at > t0` 守衛先拒）。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D1.3 — 支援矩陣 ①：`SUPPORTED_MATRIX` 常數＋`(trigger_open, close_to_close, 0)`（`票 G3-D2`）
- SPEC ref：D-001 D1.3　目標：B 預設三元組可算 `label_value`，取價不變。
- 輸入／輸出：`label_value_from_case.py` 三個 `SUPPORTED_*` 常數 → `SUPPORTED_MATRIX: frozenset[tuple[str,str,int]]`；`spec_is_supported` 查集合。
- 實作要點：①`SUPPORTED_MATRIX = frozenset({("trigger_close","close_to_close",0), ("trigger_open","close_to_close",0)})`；②`spec_is_supported(normalized) = (entry, mode, k) in SUPPORTED_MATRIX`；③`resolve_label_value_at_analyze` 取價路徑不動；④保留舊常數名為別名（deprecation 註解）避免既有 import 斷裂。
- 修改檔案：`momentum/Analysis/event_samples/label_value_from_case.py::spec_is_supported`、常數區。　既有 caller：`api/services/ic_analysis_service.py::_run_event_label_stages`（不變）。
- 不可做：不得開放 `open_to_*`；不得在前端另判支援。
- 邊界：①`(trigger_open, open_to_close, 0)` 仍 `supported=False`、reason `label_producer_unsupported_for_declared_semantics`；②`(trigger_open, close_to_close, 1)` 不支援。
- 風險緩解：既有 `test_analysis_label_producer_03/05` 不動。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "analysis_label_producer and trigger_open"` ≥3 條：(i) 同 records 同 h 兩 entry 之 `label_values` 逐 event `==`；(ii) `entry_at_ms` 不等且 hash 不等；(iii) D1.4 golden `--check` rc=0。mutation：`SUPPORTED_MATRIX` 移除 `trigger_open` 對 ⇒ (i) 紅。
- **存活至**：P4 擴充同一常數，保留。　**覆蓋風險**：P4 擴充非覆蓋。

### Task D1.4 — golden 機制：`tests/golden/gap3_label/` loader＋`scripts/gap3_label_golden.py --freeze|--check`（`票 G3-D2`）
- SPEC ref：D-001 D1.4／§G　目標：G-3 外部凍結檔落地，含既有組合。
- 輸入／輸出：真實 kline＋固定 t0 清單＋spec → JSON golden（§G 內容：`data_snapshot_digest`、t0 清單、spec、direction、逐 event `label_value`／窗四時間戳／`entry_at_ms`／`entry_price_ref{bar_open_ms, field}`／NaN mask／`analysis_alignment_receipt_hash`／逐 scope purge）。
- 實作要點：①`tests/golden/gap3_label/loader.py`：`@dataclass(frozen=True) GoldenCase`、`load_golden(path) -> GoldenCase`（typed；缺鍵／型別錯 ⇒ raise）、`run_case(case, bars) -> Observed`（跑 prepare → coverage(空) → purge → resolve）、`check_golden(case, bars) -> Report(diffs: list)`；②`entry_price_ref` P1 自 `align_events` 收據 `entry_price_source_bar_open_ms`／`entry_price_source_field` 取（P4 改自 `PreparedAnalysisWindows.entry_price_refs`，golden 鍵集不變）；③`scripts/gap3_label_golden.py --freeze <case.json>|--check <glob>`：freeze 寫 observed 進檔（含 `data_snapshot_digest`＝bar 表 S-9 sha256）、check 逐項 `==`（`atol=0`）並印 diff、rc=1；④手算路徑：`bars[field]@open_time==bar_open_ms`（open_to_*）／`close@close_time==label_start_ms`（close_to_close）與 `close@close_time==label_end_ms` 相除——**不另寫報酬公式**；⑤P1 凍結：`trigger_close__close_to_close__k0__{long,short}__12h__h{1,3}`、`trigger_open__close_to_close__k0__{long,short}__12h__h{1,3}`、一組 1h。
- 修改檔案：新增 `tests/golden/gap3_label/loader.py`、`tests/golden/gap3_label/*.json`、`scripts/gap3_label_golden.py`；`tests/momentum/event_samples/test_gap3_analysis_label_producer.py` 增 parametrize 跑全部 golden。　既有 caller：新建。
- 不可做：aggregate 代替逐 event；loader 內重算公式；合成 bar。
- 邊界：①golden 缺 `data_snapshot_digest` ⇒ loader raise；②bar 表缺 symbol/tf ⇒ `KeyError`；③digest 不符 ⇒ FAIL 不跳過。
- 風險緩解：`--freeze` 只允許寫入不存在之檔（防覆蓋既有 golden；覆蓋須 `--force` 並在 commit message 具名）。
- 驗證：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；`ASSERT venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json" WHEN mutation=direction_sign_dropped THEN rc!=0`；`ASSERT … WHEN mutation=label_end_shift_one_bar THEN rc!=0`。
- **存活至**：保留（P2–P5 golden 皆用）。　**覆蓋風險**：無。

### Task D1.5 — 前端：`/search` 解灰 `B` 與 `trigger_open`；匯出寫 provenance；揭露（`票 G3-D2`）
- SPEC ref：D-001 D1.5　目標：B 可選、選了會落檔、揭露隨實際設定。
- 輸入／輸出：`EVENT_DIM_PATH_EXCLUSIONS` → `/search|scenario` 值 `['A','two_stage']`；`/search|entry_price_semantic` 與 `/ic-analysis|entry_price_semantic` 移除 `trigger_open`；匯出 record 增 `label_origin: 'search_positive_case'`、`search_rule_summary`。
- 實作要點：①`eventDimensions.ts::EVENT_DIM_PATH_EXCLUSIONS` 三筆值更新、理由字串更新（引用 D-001）；②`eventExport.ts::buildEventContractRecords` 增 `label_origin`＝`'search_positive_case'`（scenario ∈ {B, C}）、`search_rule_summary`＝當時搜尋條件 canonical 字串（無條件 ⇒ canonical 空條件字串，非空白）；③`eventFieldFormatters.ts` 增 `label_origin` formatter（欄位級 registry）；④`EventBatchDisclosurePanel.tsx` 批次事實欄增 `label_origin` 顯示（值來自 detail，舊批 null ⇒ 「（未宣告）」）；⑤`EVENT_EXPORT_ENTRY_PRICE_SEMANTIC` 改讀契約 `default`：**新增** `eventDimensions.ts::contractDefault(dim: EnumEventDimension, contract = EVENT_DIM_CONTRACT_MIRROR): string`（＝`dimContractNode(contract, dim)?.default`，缺 ⇒ throw；`EventDimContractNode` 型別增 `default?: string`；鏡像 `entry_price_semantic.default` 同步）——R1 P2-02：現無此函式，須建於同檔並列入「修改檔案」；刪硬編碼字面。
- 修改檔案：`frontend/src/lib/eventDimensions.ts`、`eventExport.ts`、`eventFieldFormatters.ts`、`components/ic-analysis/EventBatchDisclosurePanel.tsx`、`lib/types.ts`。　既有 caller：`contractEnumWiring.test.tsx`、`eventContractOptions.test.tsx`、`eventExportOptions.test.ts`、`gap3_event_mode_entry.test.tsx`（更新期望並附 diff）。
- 不可做：元件內 `if (value === 'A')`；寫死 scenario 文案。
- 邊界：①`/data-preparation` 不受影響；②舊批 detail 無 `label_origin` ⇒ 顯示（未宣告）。
- 風險緩解：Task 7.2 三層閘沿用；mutation：把 `A` 改 enabled ⇒ ①紅（既有）。
- 驗證：`cd frontend && npx vitest run src/lib src/app/search src/components/ic-analysis`（rc 直接取）：(i) `selectable('/search','scenario')` 集合相等 `{'B','C'}`；(ii) `selectable('/search','entry_price_semantic')` 集合相等 `{'trigger_close','trigger_open'}`；(iii) 選 B＋trigger_open 匯出 record 四欄值；(iv) 預設 entry 由契約 default 導出（mutation：契約 default 改 `trigger_open` ⇒ 匯出預設跟著變）。
- **存活至**：保留。　**覆蓋風險**：P2／P3 縮小同一常數，非覆蓋。

### Task D1.6 — 後端揭露：`label_origin` 入 detail 批次事實六鍵；分析揭露 `event_known_at_decision`（`票 G3-D2`）
- SPEC ref：D-001 D1.6（覆寫 Task 7.6 批次事實欄）　目標：detail 回六鍵 scalar；分析 receipt 揭露 known 值集合。
- 輸入／輸出：`EventImportDetailResponse.batch_facts` 增 `label_origin: Optional[str]`；`EventBatchFactNotes` 不變；分析 `capability`／揭露 dict 增 `event_known_at_decision_values: list[bool]`。
- 實作要點：①`api/models/event_import_models.py:111-131` `class EventBatchFacts` 增 `label_origin: Optional[str]`（`EventImportDetailResponse.batch_facts: EventBatchFacts` 於 L159-165 引用，勿在該處加欄——R1 P2-01）（scalar；`_batch_facts` 以 `_single_value(recs,"label_origin")`，異質 ⇒ Task 1.8 既有拒）；②`api/routes/case.py:366` detail 端點 response_model 已含 → 自動回傳；③`api/services/ic_analysis_service.py::_run_event_label_stages` 揭露 dict 增 `event_known_at_decision_values = sorted({...})`（自 receipts.event_level）；④`frontend/src/lib/types.ts` 對應 TS 型別；⑤`tests/api/test_gap3_event_batch_detail_dims.py` 批次事實欄集合期望改六鍵（附 diff）。
- 修改檔案：`api/models/event_import_models.py`（`EventBatchFacts`）、`api/services/case_import_service.py::_batch_facts`、`api/services/ic_analysis_service.py::_run_event_label_stages`、`frontend/src/lib/types.ts`、`tests/api/test_gap3_event_batch_detail_dims.py`。
- 不可做：scalar 冒充 `t0`／`label`；`label_origin` 進 `event_label_spec`。
- 邊界：①舊批 ⇒ `label_origin: null`；②`supported=False` 仍列 known 值集合。
- 風險緩解：response_model 過濾——漏加欄即靜默丟，測試 (i) 擋。
- 驗證：`venv/bin/python -m pytest tests/api -q -k "event_batch_detail_dims or event_known"`：(i) 批次事實欄鍵集 `== {scenario, control_kind, direction, t0, label, label_origin}`；(ii) 舊批 fixture `label_origin is None`；(iii) 分析揭露 `event_known_at_decision_values == [False]`。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase D1 測試＋Gate
- 單元：D1.1–D1.4 選擇器全綠；golden `--check` rc=0；vitest 三檔綠；`tests/api -k event_batch_detail_dims` 綠。
- Gate：三家 code review CLOSED；`bash scripts/restore_golden_inventory.sh`；commit＋push。

## Phase D2 — A（依賴 B-D1）

### Task D2.1 — `/search` 解灰 `A`：未標籤匯出路徑＋深度≥1 阻擋（`票 G3-D2`）
- SPEC ref：D-001 D2.1　目標：A 可選但 label 不由 `positive_case` 產；補標後以 `user_csv` 匯入。
- 輸入／輸出：`EVENT_DIM_PATH_EXCLUSIONS['/search|scenario']` → `['two_stage']`；匯出 record（A）：無 `label` 鍵、`label_origin='search_unlabeled'`；匯入端 `batch_defaults.label_origin='user_csv'`。
- 實作要點：①`eventExport.ts`：`scenario==='A'` ⇒ 強制 `includeUnlabeled=true`、record 省略 `label` 鍵（`delete`，非 `null`／`""`）、`label_origin='search_unlabeled'`；②`/search` 匯出面板：`scenario==='A'` 且 `max(depthByTimeframe) < 1` ⇒ 按鈕 disabled＋理由含 `scenario_depth_inconsistent`（`fetch` 0 次）；③揭露固定字面由契約 `scenario.doc`／`label_origin.doc` 導出；④`/data-preparation` 批次預設區增 `label_origin` 選項（預設 `user_csv`）→ `batch_defaults`。
- 修改檔案：`frontend/src/lib/eventDimensions.ts`、`eventExport.ts`、`app/search/page.tsx`（匯出守衛）、`components/case/EventCsvMappingForm.tsx`（批次預設）。
- 不可做：`future_*` 接成 /search 選樣條件；寫 `label: ""`。
- 邊界：①`includeUnlabeled=false`＋A ⇒ 強制 true 並揭露；②`label: null` 與鍵缺席同視為缺。
- 風險緩解：三態 pytest 擋「解灰即算完成」。
- 驗證：vitest：(i) A 匯出每列無 `label` 鍵且 `label_origin==='search_unlabeled'`；(ii) 深度全 0 ⇒ disabled；(iii) 揭露 DOM 字面。pytest `tests/api -k label_origin_three_state`：(a) 直接匯入 ⇒ reasons 集合 `== {"missing_required_field","label_origin_not_importable"}`；(b) 補 label 仍 `search_unlabeled` ⇒ `label_origin_not_importable`；(c) 補 label＋`batch_defaults={"label_origin":"user_csv"}` ⇒ 通過且 record `label_origin=='user_csv'`。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase D2 Gate：vitest＋pytest 三態綠；三家 review CLOSED；commit＋push。

## Phase D3 — two_stage（依賴 B-D1）

### Task D3.1 — `/search` 解灰 `two_stage`：兩段必填、provenance、去重（`票 G3-D2`）
- SPEC ref：D-001 D3.1　目標：two_stage 可選；同 producer；`stage_count==2` 強制。
- 輸入／輸出：排除值 `[]`；匯出 record：`search_rule_summary` 含兩段 canonical digest 與 `stage_count=2`（單一字串，形狀由契約 `doc` 定）；label 路徑同 D2.1（未標籤）。
- 實作要點：①`eventExport.ts`：`scenario==='two_stage'` 且 `stageConditions.length !== 2` ⇒ 前端阻擋（理由 `two_stage_requires_two_stages`，`fetch` 0 次）；②`search_rule_summary` 序列化 `{stage_count:2, stages:[digest1,digest2]}` 之 canonical JSON；③深度≥1 阻擋同 D2.1；④`/two-stage` 既有 router 不動不接。
- 修改檔案：`frontend/src/lib/eventExport.ts`、`eventDimensions.ts`、`app/search/page.tsx`。
- 不可做：復活／改動 `api/routes/two_stage_search.py`；新設兩段答案窗欄；一段時靜默寫 `stage_count=1`。
- 邊界：①一段 ⇒ 阻擋；②`two_stage` 批 dedupe `policy_primary=='all_with_uniqueness'`（既有）。
- 風險緩解：揭露「兩段各自分數尚無」由契約 doc 導出。
- 驗證：vitest：`selectable('/search','scenario')` 集合相等 `{'A','B','C','two_stage'}`；一段 ⇒ disabled＋理由；pytest：two_stage 批 dedupe summary 政策斷言；深度 0 ⇒ `scenario_depth_inconsistent`。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase D3 Gate：同 D2。

## Phase D4 — (c) 其餘：producer 取價、全矩陣、k 參數化（依賴 B-D1；**串行於 B-D3 之後**，不得與 B-D2／B-D3 平行——R2 P2-01）

### Task D4.1 — producer：`entry_price_refs` 側載＋進 hash；open_to_* 取價（`票 G3-D2`）
- SPEC ref：D-001 D4.1（覆寫 (iii) hash payload）　目標：open 語意基準價取 entry bar 之 open，消除連續網格別名錯價。
- 輸入／輸出：`PreparedAnalysisWindows.entry_price_refs: Tuple[EntryPriceRef, ...]`（新欄，與 windows 同序）；`_receipt_hash` payload 增 `entry_price_refs`；`resolve_label_value_at_analyze` 依 mode 取價。
- 實作要點：①`@dataclass(frozen=True) EntryPriceRef(event_id: str, bar_open_ms: int, field: str)`；②`_refs_from_receipts(event_level) -> tuple`（逐字取 `entry_price_source_bar_open_ms`／`entry_price_source_field`，按 event_id UTF-8 升冪與 windows 同序）；③`_receipt_hash(..., entry_price_refs)` payload 六鍵（D-001 code fence 逐字）；④`resolve`：`mode == close_to_close ⇒ base = _close_at(bars, label_start_ms)`；`mode in open_to_* ⇒ ref = refs[event_id]; assert label_start_ms == entry_at_ms else LabelProducerError; base = _price_at(bars, ref.bar_open_ms, ref.field)`（新函式：`open_time_ms == bar_open_ms` 唯一列之 `field` 欄；找不到 ⇒ None）；`end = _close_at(bars, label_end_ms)`；⑤`apply_event_coverage` 以 `replace` 攜帶 refs；⑥重凍既有 golden 之 hash（`--force`，commit message 具名「hash 合法改變一次、label_value 逐位元組不變」）。
- 修改檔案：`momentum/Analysis/event_samples/label_value_from_case.py`（`EntryPriceRef`、`PreparedAnalysisWindows`、`_receipt_hash`、`prepare_analysis_windows`、`resolve_label_value_at_analyze`、新 `_price_at`）；`tests/golden/gap3_label/loader.py`（ref 改自 prepared 取）。　既有 caller：`ic_analysis_service` 三處讀 hash（不變式仍成立）。
- 不可做：producer 依 `entry_price_semantic` 自判欄位；改 `WindowRow` 鍵數；回落 `_close_at` 當 open 語意 fallback。
- 邊界：①`next_open × open_to_*` 之 `bar_open_ms = ot[t0_idx+1]`；②ref bar 不唯一 ⇒ `None`＋reason。
- 風險緩解：既有 `close_to_close` `label_values` 逐位元組不變之斷言。
- 驗證：`venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "open_to or entry_price_ref"` ≥6 條（D-001 D4.1 (i)–(vi)：跳空 bar 手算、k=2 decision_bar_open、ref.field 對調紅、刪 refs ⇒ None、改 ref 值 ⇒ hash 變、既有值不變）；`ASSERT venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*open_to*.json" WHEN mutation=entry_ref_field_swapped THEN rc!=0`。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D4.2 — 支援矩陣 ②：13 對＋成對可行域＋兩上界＋pair_rejected UI＋三層 oracle（`票 G3-D2`）
- SPEC ref：D-001 D4.2　目標：全矩陣（減兩幾何必拒對）可選可算；可行域誠實；差分／raw-bar oracle。
- 輸入／輸出：`SUPPORTED_MATRIX` 擴為 13 對 × 任意 k；`feasible(e,k,h)` 純函式；揭露 `k_max_feasible_at_h`／`h_max_feasible_at_k`；契約 `label_return_mode.rejected_pairs`；前端 `pair_rejected`。
- 實作要點：①`SUPPORTED_MATRIX` 改為對集合 `SUPPORTED_PAIRS: frozenset[(entry, mode)]`（13 對）＋`spec_is_supported = (entry,mode) in SUPPORTED_PAIRS and k >= 0`；`{trigger_close, decision_bar_close} × open_to_close` ⇒ `supported=False, reason="zero_length_label_window"`（reason 登記契約 `capability_unavailable_reasons`）；②`feasible(e, k, h, *, mode, entry, t0_idx, n_bars, coverage_ok) -> bool` 純函式（閉式依 D-001）；`bounds(records, bars, spec) -> (k_max_at_h, h_max_at_k)` 於階段 2 後、以 index 算，不重跑對齊；③契約 `label_definition.fields.label_return_mode.rejected_pairs = {"open_to_close": ["trigger_close","decision_bar_close"]}`＋鏡像；④`eventDimensions.ts`：`dimOptions(path, dim, contract, selection?)` 增 `kind:'pair_rejected'`（雙向）；`selectable(..., selection?)`；兩 caller（`EventDimensionFields.tsx:69`、`EventBatchDisclosurePanel.tsx:130`）傳 `selection`；既選非法 ⇒ 另一維重設契約 `default`＋揭露；送出守衛；⑤排除常數：`/search`／`/ic-analysis` 三元組排除值清空；`decisionOffsetRange('/ic-analysis')` ⇒ `{min, max:null, locked:false}`；⑥golden 新增（D-001 D4.2 清單）＋raw-bar 期望表測試 `test_gap3_label_rawbar_oracle.py`（五語意 `(offset, field)`、三 mode `(start,end)` 寫死於測試）＋`label_differential_grid`（固定網格＋seed 20260903 隨機 40 組）。
- 修改檔案：`label_value_from_case.py`（常數、`spec_is_supported`、新 `feasible`／`bounds`）；契約；`eventDimensions.ts`（`dimOptions`／`selectable`／`decisionOffsetRange`／常數）；`EventDimensionFields.tsx`、`EventBatchDisclosurePanel.tsx`；`api/services/ic_analysis_service.py`（揭露兩上界）；新測試三檔；golden 檔。
- 不可做：為任一組合寫特例公式；先凍全矩陣再刪；上界當輸入鎖。
- 邊界：①`decision_bar_close × open_to_horizon_close` 可算；②`(k_max_at_h + 1, h)` 該事件入 failures；③上界 ≤ 不保證零 failures（誠實邊界字面進揭露）。
- 風險緩解：Task 7.2 閘擴「pair 對稱性」一條。
- 驗證：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；`pytest … -k "rawbar_oracle or label_differential_grid or feasible_bounds"` 綠（三事件手算兩上界 `==`；`end_idx` 少算一根 ⇒ 兩上界皆變）；vitest：pair 雙向、重設讀契約 default、守衛 `fetch==0`、對稱性閘。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D4.3 — k 分析參數化：UI 移除、seeds 不帶 k、雙值揭露、scan_max（`票 G3-D2`）
- SPEC ref：D-001 D4.3　目標：裁定②落地；既有 (B,k=1) 批不靜默改變。
- 輸入／輸出：契約 `analysis_params.decision_offset_bars_scan_max{value, example_default:10, doc}`；`EventDeclarationSeeds` 去 `decision_offset_bars`；`EventBatchFactNotes` 增 `decision_offset_bars_record_values: list[int]`；分析揭露 `decision_offset_bars_analysis`、兩上界；`capability_unavailable_reasons` 增 `missing_decision_offset_disclosure`。
- 實作要點：①契約增鍵；②`api/models/event_import_models.py::EventDeclarationSeeds` 移除欄；`EventBatchFactNotes` 增 `decision_offset_bars_record_values`；`case_import_service.py:1390-1394` 改填；③`api/routes/ic_analysis.py:134-137` `spec.setdefault("decision_offset_bars", 0)`（常數）；④`EventDimensionFields.tsx` 於 `/search`／`/data-preparation` 隱藏 k 控制項（CSV 欄對映表保留 `decision_offset_bars`）；`eventExport.ts` 恆寫 0；⑤`EventBatchDisclosurePanel.tsx:172` 移除 seeds 回退、初始 0、`max=null`、超 `scan_max` 警示、並排「批次記錄 k（record 值集合）／本次分析 k」；⑥`ic_analysis_service`：缺任一揭露欄 ⇒ `unavailable:missing_decision_offset_disclosure`；⑦`tests/api/test_gap3_event_batch_detail_dims.py:28` `SEED_KEYS` 改兩鍵（附 diff）；`frontend/src/lib/types.ts` 同步。
- 修改檔案：契約；`event_import_models.py`（`EventDeclarationSeeds`／`EventBatchFactNotes`）；`case_import_service.py::get_import` 內聯區塊 L1390–1399（`declaration_seeds=EventDeclarationSeeds(...)`／`batch_fact_notes=EventBatchFactNotes(...)`；無同名私有方法——R1 P2-04；實作時**可**抽成私有方法）；`api/routes/ic_analysis.py`；`ic_analysis_service.py`；`EventDimensionFields.tsx`；`EventBatchDisclosurePanel.tsx`；`eventExport.ts`；`types.ts`；測試。
- 不可做：改契約 `decision_offset_bars` 必填／default；靜默重設 record k；拒收 CSV k>0（允許＋揭露）。
- 邊界：①既有 k=1 批 ⇒ 初始 0、揭露 `[1]`；②分析 k > `k_max_feasible_at_h` ⇒ 全批 failures ⇒ `unavailable`。
- 風險緩解：seeds 銜接清單五處逐一改（D-001 列）。
- 驗證：pytest：(i) k=1 fixture 初始 `== 0` 且 `decision_offset_bars_record_values == [1]`；(ii) 缺揭露欄 ⇒ `unavailable` reason；(iii) **經分析 API 揭露欄回傳**之 `k_max_feasible_at_h`／`h_max_feasible_at_k` 對真實 kline 三事件手算相等（含一 `decision_bar_open × open_to_horizon_close` 事件證明耦合；R1 COMPOSER/GROK-R1-P1-01：此條為 D-001 D4.3 (iii) 原句，與 D4.2 純函式測試並存、不得互相取代）；(iv) `SEED_KEYS == {entry_price_semantic, label_return_mode}`；vitest：`/search` DOM 無 `event-dim-decision_offset_bars`；`/data-preparation` 對映表仍含該欄；IC 頁雙值並排 DOM。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase D4 Gate：golden 全 `--check` rc=0（含 hash 重凍具名）；三檔新測試綠；vitest 綠；三家 review CLOSED；commit＋push。

## Phase D5 — (b) `platform_random_bars`（依賴 B-D4、B-D1）

### Task D5.1 — 契約：`random_control_spec` typed nested schema、estimand、三 reason、`control_kind` 解禁（`票 G3-D2`）
- SPEC ref：D-001 D5.1　目標：抽樣契約與 wire 唯一。
- 輸入／輸出：匯入 body `{records, random_control_spec}` → validator 通過之 records＋`receipt.batch.random_control_spec`（原樣落檔、detail 回傳）；契約新增鍵／reason 見實作要點。
- 實作要點：①契約 `receipt_schema.batch.random_control_spec` typed object（每葉 `{type, required}`；`universe`／`strata`／`exclusion`／**`label_rule{threshold: float, horizon_bars: int}`**（必填；R1 P1-02）nested；`per_stratum: list[object]`）；`import_failure_reasons` 增 `random_control_label_rule_missing`；`receipt_schema.batch.label_rule{threshold, horizon_bars}`（optional；觸發批規則身分，R2 P1-01）；`capability_unavailable_reasons` 增 `random_control_rule_identity_unverifiable`／`random_control_rule_mismatch`；`doc` 寫 estimand（僅當觸發批 `label_rule` typed 相等時比較成立）；②`control_kind.accepted` 增 `platform_random_bars`、刪其 `rejected_with_reason`；③reasons：`random_control_spec_missing`、`random_control_mixed_batch`（import）、`random_control_prevalence_missing`、`random_control_period_mismatch`（capability）；④`import_contract.py::receipt_type_ok` 遞迴（`object`／`list[object]`；既有 leaf 不變）；`validate_event_import(..., random_control_spec: Optional[Mapping]=None)`：`control_kind==platform_random_bars` ⇒ 必填、否則出現 ⇒ mixed；⑤`case_import_service` 落檔 `receipt.batch.random_control_spec`；detail 回傳；⑥鏡像同步。
- 修改檔案：契約；`import_contract.py`（`receipt_type_ok`、`validate_event_import`）；`case_import_service.py`；`event_import_models.py`（detail）；`eventDimensions.ts` 鏡像。
- 不可做：fallback；逐列欄承載 spec。
- 邊界：①`n_drawn < n_requested` 允許＋揭露；②跨 symbol universe ⇒ 拒。
- 風險緩解：既有 leaf receipt 測試不變（`pytest … -k receipt` 綠）。
- 驗證：D-001 D5.1 四段 wire 鏈 (a)–(d) 逐段命令；`pytest tests/momentum/event_samples/test_import_contract.py -q -k random_control` ≥4 條；`inspect.signature` 含 keyword；`tests/api -k random_control_roundtrip`。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D5.2 — 產生器 `random_control.py::sample_random_bars`（`票 G3-D2`）
- SPEC ref：D-001 D5.2　目標：確定性抽樣純函式，排除區間／配額／period 定死。
- 實作要點：①`sample_random_bars(bars, spec, trigger_receipts, label_rule) -> (records, receipt)`；②候選＝`all_bars_eval._is_eligible` 之 bar 減排除區間 `[t0_idx − neighborhood, label_end_idx + embargo]`（對每觸發事件取聯集）；③`strata.period` 與觸發期 `[min t0, max label_end]` 無交集 ⇒ raise `random_control_period_mismatch`；④配額：`n_target=min(n_requested, candidate_count)`；floor＋最大餘數（小數降冪、key 升冪）＋cap；不變式 `Σ==n_drawn==n_target`；⑤`rng = numpy.random.default_rng(seed)`，各 stratum 無放回；⑥label（R1 COMPOSER/GROK-R1-P1-02 定死；`canonical_digest` 不可逆、條件引擎無 digest→spec 路徑、`/search` 匯出批無 `filters`）：**唯一**標籤路徑＝`all_bars_eval._label_from_rule(direction_sign, close, i, horizon, threshold)`，其中 `horizon = random_control_spec.label_rule.horizon_bars`、`threshold = random_control_spec.label_rule.threshold`（**契約必填**，D5.1 typed schema 增 `label_rule{threshold: float, horizon_bars: int}`）、`direction_sign` 由觸發批 `direction` 導出；缺 `label_rule` ⇒ `random_control_label_rule_missing`（登記 `import_failure_reasons`）；**不**呼叫 `evaluate_condition`；pytest：同 `label_rule` 兩次評值逐 bar 相等、改 `horizon_bars` ⇒ label 集合改變；record：`control_kind=platform_random_bars`、`label_origin=platform_random`、scenario 同觸發批、`label_definition={rule_id:"random_control:label_rule", canonical_digest: S-9 sha256(label_rule), window:{horizon_bars}, label_return_mode:"close_to_close"}`（R2 codex P1-01 wire）；⑦receipt：`per_stratum`、`sample_ids_digest`（S-9 sha256 of sorted ids）、`data_snapshot_digest`、`candidate_count`。
- 修改檔案：新增 `momentum/Analysis/event_samples/random_control.py`；`momentum/factories.py` 不需新出口（服務端經 pipeline 消費）。
- 不可做：隨機 bar 補入觸發批；合成 bar；`round`。
- 邊界：①候選 0 ⇒ `unavailable`；②`neighborhood=0, embargo=6` 反例：觸發前一根不得被抽（若落其他觸發後鄰域）。
- 風險緩解：決定性測試（同 seed digest 相等）。
- 驗證：`pytest tests/momentum/event_samples/test_random_control.py -q` ≥7 條（D-001 D5.2 (i)–(vii)）。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D5.3 — API／分析／前端：`POST /case/import-events/random-control`、prevalence 並排、解灰（`票 G3-D2`）
- SPEC ref：D-001 D5.3　目標：隨機批可產、可匯入、可算條件 IC、與觸發批 prevalence 並排。
- 實作要點：①`api/routes/case.py` 新端點 `POST /case/import-events/random-control`（body `{event_import_id, random_control_spec}`；讀觸發批、跑 D5.2、經同一 validator 落檔；回 `EventImportResponse`）；②`ic_analysis_service`：隨機批分析揭露 `sample_design='unconditional_random'`；**規則身分閘**（R2 三家 P1-01；D-001 D5.3 ①–④）：`compare_random_control(trigger_detail, random_detail) -> CompareVerdict`——(a) 觸發批 `receipt.batch.label_rule` 缺 ⇒ `unavailable:random_control_rule_identity_unverifiable`；(b) 任一葉不等或 direction 不同 ⇒ `unavailable:random_control_rule_mismatch`；(c) 相等 ⇒ 以同一 `label_rule` 經 `_label_from_rule` 重評觸發批每列 label，一致率 `!= 1.0` ⇒ `random_control_rule_mismatch`；(d) 缺 prevalence ⇒ `random_control_prevalence_missing`；②b 觸發批規則身分來源：平台產生器批於 `generator.py` 落 `receipt.batch.label_rule`（自 `LabelRule` 之 threshold／horizon）；匯入 envelope 可選帶 `label_rule`（validator typed 驗）；③前端：`/search`（或 `/ic-analysis` 事件模式）「產生隨機對照批」入口（依附既有觸發批）；`control_kind` 選項 `platform_random_bars` 由契約 `accepted` 解灰；④鏡像。
- 修改檔案：`api/routes/case.py`；`api/services/case_import_service.py`；`api/services/ic_analysis_service.py`；`frontend/src/lib/api.ts`、`eventDimensions.ts`、相關元件。
- 不可做：隨機批當反例餵辨別表；新建 `api/routes/event_import.py`。
- 邊界：①隨機批單獨分析允許（IC＝無條件估計，揭露）；②`n_drawn<<n_requested` 於比較時必揭露。
- 風險緩解：端點走既有 validator（無 profile 分裂）。
- 驗證：pytest `tests/api -q -k random_control_compare` ≥5 條：(i) 觸發批無 `label_rule` ⇒ `random_control_rule_identity_unverifiable`；(ii) 葉不等 ⇒ `random_control_rule_mismatch`；(iii) 相等且重評一致率 1.0 ⇒ 比較成立並回兩 prevalence；(iv) mutation：翻轉觸發批一列 label ⇒ (iii) 轉 `random_control_rule_mismatch`；(v) 缺 prevalence ⇒ `random_control_prevalence_missing`；隨機批單獨分析 `supported=True`、`label_values` 非空；vitest：`selectable('/search','control_kind')` 含 `platform_random_bars`。
- **存活至**：保留。　**覆蓋風險**：無。

### Task D5.4 — golden：抽樣決定性（`票 G3-D2`）
- SPEC ref：D-001 D5.4　實作要點：①`tests/golden/gap3_random_control/<seed>__<tf>.json` 凍 `sample_ids_digest`、`n_drawn`、`per_stratum`、逐列 label；②`scripts/gap3_label_golden.py` 增 `--kind random_control`；③negative：改 `neighborhood`／`embargo` ⇒ digest 變；period 錯位 ⇒ raise。
- 修改檔案：golden 檔；`scripts/gap3_label_golden.py`。　不可做：合成 bar。　邊界：跨月分層；候選 0。　風險緩解：`--force` 規則同 D1.4。
- 驗證：`venv/bin/python scripts/gap3_label_golden.py --kind random_control --check "tests/golden/gap3_random_control/*.json"` rc=0；`ASSERT … WHEN mutation=neighborhood_changed THEN rc!=0`。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase D5 Gate：D5 全測試綠＋golden rc=0；三家 review CLOSED；registry `G3-D2` 改 CLOSED、`G3-R7` 收回；UAT B3 改「可選項全部通過」待使用者驗；commit＋push。

## 戳記
（三家 RECONCILE-STAMP 於 TODO 對抗審收斂後 append。）
