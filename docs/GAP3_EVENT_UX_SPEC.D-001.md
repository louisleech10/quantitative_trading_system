# GAP3_EVENT_UX_SPEC — D 延伸 001（`G3-D2` 灰色項目完成：scenario A／B／two_stage、三元組其餘值與 k、`platform_random_bars`）

BASE: docs/GAP3_EVENT_UX_SPEC.md @ 55c0a9d50b92
PREDECESSOR: none

改什麼: 把 §F-1′／Task 7.1／Task 7.6／§N-7 以「本批」限定之三類 disabled 值改為**可選且分析層算得出 `label_value`**，依使用者裁定順序 (a)→(c)→(b) 分五個 phase 交付，每個 phase 有逐組合 exact golden、provenance 與誠實揭露。

為什麼: 票 `docs/IC_QUANT_GAP_REGISTRY.md` `G3-D2`（user-ruling 2026-08-31／2026-09-02：灰項不接受永久灰著、順序 (a)→(c)→(b)）；consult 收斂 `handoffs/reconcile/20260903-gap3d2-x-consult-r1/synth.md`（本機；四來源九群集，Verdict＝需修補後合併、形式＝D 延伸）。原檔 F-5′（L2458）與原 SPEC §N-7 本就把開放寫成有前置之路徑，本檔不推翻既有設計。

## 觸及面宣告
新增: 無新增原檔 heading；本檔內新增 Task D1.1–D5.4（編號以 `D` 前綴與原檔 Task 區隔）。
覆寫: **F-1′ 分析層支援矩陣（封閉集合；R8 由匯出層改掛分析層）**；**F-5′ 開放更多組合之前置**；**Task 7.1 — 五維度全部接出前端（依賴 Task 7.0）**（僅 `EVENT_DIM_PATH_EXCLUSIONS` 之封閉內容與 `scenario` 路徑級限制段）；**Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（R4 群集 C／遺留 E；R8 依 §D-3′ 改寫；R10 定死事實欄形狀）**（僅 ③ 分析參數區之可操作集合與 `decision_offset_bars` 初始值來源）；**G-3 analysis-label golden（R8 新建；R9 擴逐列 purge；R10 加 receipt hash 與混 TF 覆蓋面）**（固定輸入集合擴充＋凍結對象 ⑥ 之 hash payload 增 `entry_price_refs`）。
依賴: **Task 7.0b — 分析時 `label_value` producer 與其 wiring（R6 群集 E；F-4′ 之承載 Task；R10 拆兩階段函式）**；**Task 1.1 — 契約先行：新增 reason 與 label_definition.filters**；**Task 1.8 — 異質列顯式拒收（A-5'）**；**Task 7.3 — 動態揭露本批設定（取代原擬之固定文案）**；**Task 7.2 — 機械閘：可操作選項集合 ＝ `selectable(path,dim)`，且選值真的傳到落檔（依賴 Task 7.0／7.1）**；**F-2′ 偏離即 fail-closed（分析層）**。

## 內容

> 工作文件規約：本檔為主委與委員之契約，技術描述、無散文；白話另寫 `白話說明/`。
> 原檔（BASE）之一切未在「覆寫」列出的條文**原樣有效**。本檔所有 Task 皆須通過 `scripts/template_check.sh dext`；派工前 `gate.sh dispatch --spec docs/GAP3_EVENT_UX_SPEC.D-001.md`。

## §RISK 風險分級
- **大小**：大（CLAUDE.md 分派表：命中 (a)(b)(d)）。
- **命中高風險原則**：(a) 數值／資料品質——`label_value` 基準價取價、golden；(b) 跨模組共用路徑——`momentum/Analysis/event_samples/{alignment,label_value_from_case,import_contract,dedupe}.py`、`api/routes/ic_analysis.py`、`frontend/src/lib/eventDimensions.ts`、契約 JSON；(d) ML／回測正確性——事件樣本＝條件 IC 與 ML 訓練集入口。
- RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑（三家全員；`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行）。

## §A 假設與待使用者確認
- FACT-RECEIPT: `venv/bin/python handoffs/20260903-gap3d2-probe-triplets.py` → 印出 `trigger_open open_to_close k=0 supported=False … label_start_is_open_time=True is_close_time=True … _close_at(start)=2944.800048828125`（t₀−1 close）與 `trigger_close close_to_close … _close_at(start)=2935.31005859375`（t₀ close）（主委 實跑 2026-09-03；receipt `handoffs/20260903-gap3d2-probe-triplets.receipt.txt`）
- FACT-RECEIPT: `sed -n 43p momentum/Analysis/event_samples/bars_source.py` → 印出 `"close_time_ms": open_ms + TIMEFRAME_SECONDS[tf] * 1000,`（主委 實跑 2026-09-03）⇒ 連續網格 `open_time(t₀) == close_time(t₀−1)`
- FACT-RECEIPT: `grep -n "SUPPORTED_" momentum/Analysis/event_samples/label_value_from_case.py` → 印出 `75:SUPPORTED_ENTRY_PRICE_SEMANTIC = "trigger_close"`、`76:SUPPORTED_LABEL_RETURN_MODE = "close_to_close"`、`77:SUPPORTED_DECISION_OFFSET_BARS = 0`（主委 實跑 2026-09-03）
- FACT-RECEIPT: `grep -rn "event_known_at_decision" momentum api --include='*.py'` → 印出（無輸出）；`jq -c .derived_fields.names momentum/Analysis/contracts/event_import_contract.json` → 印出含 `"event_known_at_decision"` 之陣列（主委 實跑 2026-09-03）
- FACT-RECEIPT: `for f in data_cache/events/*.json; do jq -c '[.records[0].decision_offset_bars,.records[0].scenario]' "$f"; done | sort | uniq -c` → 印出 `5 [0,"C"]`、`4 [1,"B"]`（主委 實跑 2026-09-03；四家一致；codex 之 903 列計數未重現，採 723 列）
- FACT-RECEIPT: `grep -n "ret_entry\|ret_label_anchor" momentum/Analysis/event_samples/tables.py` → 印出 `232:… "ret_entry": …`、`233:… "ret_label_anchor": …`（主委 實跑 2026-09-03）⇒ 開盤進場實際報酬與標籤基準報酬之並排已在事件後報酬表
- FACT-RECEIPT: `grep -rn "sha256\|golden" tests/momentum/event_samples/test_gap3_analysis_label_producer.py tests/api/test_gap3_event_analysis_horizon_purge.py` → 印出（無輸出）（主委 實跑 2026-09-03）⇒ G-3 現況為 pytest 內手算、無外部凍結檔
- FACT-RECEIPT: `jq -r '.optional_fields|keys[]' momentum/Analysis/contracts/event_import_contract.json | grep -c label_origin` → 印出 `0`；`grep -n "label_source" momentum/Analysis/survivor_contract.py | head -2` → 印出 survivor v2 之 `label_source ∈ {event_label_value, mainline_return_N}`（codex 實跑 2026-09-03；主委抽驗）⇒ provenance 欄命名須為 `label_origin`，不得撞名
- **已確認結果**：`2026-09-03 使用者<docs/GAP3D2_KICKOFF_HANDOFF.md §5 五裁定：①(a) 不含全部 K 線驗證 ②k 不由使用者填、只作分析時掃描參數、預設 0 ③反例種類不必標、第二期 ④標籤基準維持 t₀ close／close_to_close、開盤進場實際報酬並排 ⑤(a) 內部順序 B→A→two_stage>`
- **待使用者確認**（使用者離線，依離線規則由委員共識決並具名，醒後可否決；**未否決即視為確認，不阻塞本檔對抗審**）：(甲) C 之「收盤後決策」不可表示 ⇒ 本檔採誠實揭露＋殘留 `G3-R13`，不改 D2-2；(乙) 契約 `decision_offset_bars` 保留必填 default 0（codex 異議＝改 optional）；(丙) k 掃描軟上限 `example_default=10`（判斷值）。

## §C 約束（引用，不重抄）
- 原檔 §C0（只能更嚴）、§C（解耦 7 條、不可違反原則）、§D-3′-a（i）–（iii）、D-7／D-8 三層防線原樣有效。
- 原 SPEC `docs/GAP3_EVENT_SPEC.md` D1-5（label 錨由 `label_return_mode` 唯一決定、與 entry／k 無關）、D1-6（entry 唯一映射，**只在 `align_events`**）、D2-2（決策時點單一表示法 `t0 + decision_offset_bars ≥ 0`）**不動**。
- 新資料結構一律進契約 JSON（單一真相源）：`event_import_contract.json`（`label_origin`、`scenario_depth_inconsistent`、`analysis_params`、`random_control_spec`）；本檔只 pointer，不在散文列舉欄位表。
- 特別注意：`WindowRow` 恰七鍵（R13 (β)）**不動**；survivor v2 `event_context` 恰六鍵**不動**；`_receipt_hash` payload 之擴充只在 Task D4.1 一處。

## §G Golden / Baseline
- **feature/kline 條件**：涉 label 計算與 PIT 對齊 ⇒ 真實 `data_cache/feature_klines/kline_cache.h5`（ETHUSDT；12h 與 1h），禁合成 fixture；三方簽核（三家 review 各自實跑 golden `--check`）。
- **凍結時機**：每 phase 動工前，先以該 phase 新增之組合對真實 kline 手算並寫入 `tests/golden/gap3_label/<entry>__<mode>__k<k>__<direction>__<tf>__h<h>.json`（Task D1.4 之 typed loader；`--check` rc=0 為驗收）。既有支援組合 `(trigger_close, close_to_close, k=0)` 於 P1 一併凍結（補實原檔 G-3 ⑥ 之 hash 凍結）。
- **golden 內容（逐項 exact，`atol=0`）**：`data_snapshot_digest`（bar 表 S-9 位元組 sha256）、t0 清單、`event_label_spec`、`direction`、逐 event `label_value`／`label_start_ms`／`label_end_ms`／`decision_at_ms`／`entry_at_ms`／`entry_price_ref{bar_open_ms, field}`、NaN mask（`label_value is None` 之 event_id 集合）、`analysis_alignment_receipt_hash`、逐 scope `purge_lower_bound_ms`。
- **手算法（唯一）**：直接自同一 bar 表取 `bars[field]@open_time==entry_price_ref.bar_open_ms`（open_to_* 基準）或 `close@close_time==label_start_ms`（close_to_close 基準）與 `close@close_time==label_end_ms`，相除；**不另寫報酬公式**。
- **通過條件**：值集合逐 event `==`；NaN mask 集合相等；hash 字串相等；任一不等 ⇒ 列出 event_id 與 diff ⇒ FAIL。改前==改後：P1 對既有組合之 `label_value` 逐位元組不變（`analysis_alignment_receipt_hash` 於 P4 因 payload 擴充**合法改變一次**，於 P4 golden 重凍並在 commit message 具名）。
- **必含案例**：①有跳空 bar（`open(t₀) != close(t₀−1)`，測試須先斷言此不等式成立再用）；②資料末端 `label_window_incomplete`；③k>0 之 `warmup_insufficient_<tf>`；④`next_open × close_to_close` 之 `entry_after_label_start=true`；⑤long／short 同價格序列（short 為 long 之相反數，`== -x`）。

## §P Phase 與依賴

### Phase D1 — B（scenario 解灰＋provenance＋`trigger_open × close_to_close`＋golden 機制）（依賴：無；原檔 Task 7.0b／7.1／7.3／7.6 已落地）

**Task D1.1 — 契約先行：`label_origin`、`scenario_depth_inconsistent`、`scenario.doc` 誠實化**
- 目標：provenance 與機檢之字面唯一住契約檔。　檔案：`momentum/Analysis/contracts/event_import_contract.json`；`momentum/Analysis/event_samples/import_contract.py`（validator）；`frontend/src/lib/eventDimensions.ts` 之 `EVENT_DIM_CONTRACT_MIRROR`（同步鏡像；漂移由 `eventContractOptions.test.tsx` 擋）。　既有 caller／影響面：validator 全部匯入路徑；Task 7.3／7.6 formatter 讀 `doc`。
- 改法：①`optional_fields.label_origin`：`enum ∈ {search_positive_case, user_csv, platform_generator, platform_random}`，`doc` 說明各值來源；缺值時 validator **不補值**、但 record 級 `scenario ∈ {A, B, two_stage}` 且缺 `label_origin` ⇒ 拒 `conditional_required_missing`（既有 reason）。②`import_failure_reasons` 增 `scenario_depth_inconsistent`；validator 規則：`scenario ∈ {A, two_stage}` ⇒ `max(lookahead_bars_declared.values()) ≥ 1`；`scenario == B` ⇒ 允許 0；`lookahead_bars_declared` 缺 ⇒ 沿用 D-7 L2 既有拒收。③`required_fields.scenario.doc` 改為誠實描述（決策時點恆為 `t₀−k` open；C＝t₀ 條件為深度 0 之事件、收盤後決策不可表示、見 `G3-R13`；A／B＝事件相對決策為未來、`event_known_at_decision=false`；two_stage＝深度取兩段較大者，兩段各自 `label_value` 未交付）。
- **驗證**：`pytest tests/momentum/event_samples/test_import_contract.py -q -k "label_origin or scenario_depth"` ≥4 條：(i) `scenario=A` 且深度 map 全 0 ⇒ `ContractValidationError` 且 reason `== "scenario_depth_inconsistent"`；(ii) `scenario=B` 深度 0 ⇒ 通過；(iii) `scenario=B` 缺 `label_origin` ⇒ `conditional_required_missing`；(iv) `label_origin` 枚舉外值 ⇒ `enum_violation`。前端 `npx vitest run src/lib/eventContractOptions.test.tsx` 鏡像逐鍵相等。
- **邊界**：①`lookahead_bars_declared` 為空 map 且 `scenario=A` ⇒ 先命中 D-7 L2 之缺宣告拒收（reason 不得被本規則覆蓋）；②批內 `scenario` 混值 ⇒ Task 1.8 既有拒收先於本規則。
- **存活至**：全票完工後保留（契約為所有事件匯入之唯一契約）。
- **覆蓋風險**：無（P2–P5 只擴 enum／新增鍵，不改本 Task 之鍵）。
- 不可做：不得在 validator 或前端硬寫枚舉清單；不得為缺 `label_origin` 之舊批補預設值（舊批 `scenario=C` 不受條件必填約束）。

**Task D1.2 — 對齊層寫入 `event_known_at_decision`（契約 derived 欄之落地）**
- 目標：把「事件於決策時是否已知」由對齊函式機械導出寫入 `event_level` receipt。　檔案：`momentum/Analysis/event_samples/alignment.py::align_events`（`_EVENT_COLS` 增一欄）；`momentum/Analysis/event_samples/types.py`（receipt schema）；契約 `receipt_schema.event_level`。　既有 caller／影響面：`label_value_from_case._windows_from_receipts`（**只讀七鍵，不受影響**）、`tables.py`、`pipeline.py` merge 清單。
- 改法：`event_known_at_decision = bool(decision_at_ms >= t0_close_ms)`，其中 `t0_close_ms = ct[t0_idx]`；D2-2 下恆 `False`，**照實寫**、不依 scenario 推導、不猜。
- **驗證**：`pytest tests/momentum/event_samples/test_alignment.py -q -k event_known` ≥2 條：(i) 真實 kline k=0／k=2 兩事件 `event_known_at_decision is False`；(ii) mutation：把 `decision_at` 改為 `ct[t0_idx]`（違反 D2-2）⇒ 原有 `decision_at > t0` 守衛先拒（`no_boundary_match`），本欄不得出現 `True`——`ASSERT venv/bin/python -m pytest tests/momentum/event_samples/test_alignment.py -q -k event_known WHEN mutation=decision_at_close THEN rc!=0`。
- **邊界**：①`t0` 在資料末端 ⇒ 既有 `label_window_incomplete` 先拒，本欄不寫；②多 TF per_tf 列不含本欄（僅 event_level）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得把本欄放進 `WindowRow`（七鍵不動）或 `_receipt_hash` payload（本欄為 D2-2 之恆等式，非身分）。

**Task D1.3 — 支援矩陣擴充 ①：`(trigger_open, close_to_close, k=0)`**
- 目標：B 之預設三元組（裁定④）可算 `label_value`。　檔案：`momentum/Analysis/event_samples/label_value_from_case.py`：`SUPPORTED_ENTRY_PRICE_SEMANTIC` 改為封閉集合常數 `SUPPORTED_MATRIX: frozenset[tuple[str, str, int]]`，P1 內容＝`{("trigger_close","close_to_close",0), ("trigger_open","close_to_close",0)}`；`spec_is_supported` 改查集合。　既有 caller／影響面：`api/services/ic_analysis_service.py::_run_event_label_stages`（呼叫不變）；`tests/momentum/event_samples/test_gap3_analysis_label_producer.py` 既有 03／05 條斷言（`next_open`／`open_to_close` 仍不支援，**斷言不得放寬**）。
- 改法：取價路徑**不變**（`close_to_close` 之基準＝`close@close_time==label_start_ms`，錨與 entry 無關＝D1-5）；只擴矩陣。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k "analysis_label_producer and trigger_open"` ≥3 條：(i) 同一 records、同 h，`trigger_open` 與 `trigger_close` 之 `label_values` 逐 event `==`（`atol=0`）；(ii) 兩者之 `WindowRow.entry_at_ms` 不等（open 為 `ot[t0_idx]`、close 為 `ct[t0_idx]`）且 `analysis_alignment_receipt_hash` 不等（spec bytes 不同）；(iii) golden `tests/golden/gap3_label/trigger_open__close_to_close__k0__{long,short}__12h__h{1,3}.json` `--check` rc=0。
- **邊界**：①`trigger_open × open_to_close` 仍 `supported=False`、reason `label_producer_unsupported_for_declared_semantics`（留給 P4）；②k=1 × `trigger_open` 仍不支援。
- **存活至**：P4 擴矩陣時本集合為其子集，保留。
- **覆蓋風險**：P4 會**擴充**同一常數（非覆蓋）；`SUPPORTED_MATRIX` 之單一常數設計即為此。
- 不可做：不得同時開放 `open_to_*`（P0 取價缺陷未修）；不得在前端另判支援。

**Task D1.4 — golden 機制：`tests/golden/gap3_label/` typed loader ＋ `--check`**
- 目標：G-3 之外部凍結檔落地（含既有組合）。　檔案：新增 `tests/golden/gap3_label/loader.py`（`load_golden(path) -> GoldenCase`、`check_golden(case, bars) -> Report`）；`scripts/gap3_label_golden.py --freeze|--check <glob>`；golden JSON 依 §G 內容。　既有 caller／影響面：新建；`test_gap3_analysis_label_producer.py` 加一條 parametrize 跑全部 golden。
- 改法：freeze＝以真實 kline 跑五階段（prepare → coverage(空) → purge → resolve）取值，手算法依 §G；check＝重跑後逐項 `==`。`data_snapshot_digest` 不符 ⇒ 直接 FAIL（不得靜默跳過）。
- **驗證**：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；mutation：`ASSERT venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json" WHEN mutation=direction_sign_dropped THEN rc!=0`（short 不取負 ⇒ 紅）；`ASSERT … WHEN mutation=label_end_shift_one_bar THEN rc!=0`。
- **邊界**：①golden 檔缺 `data_snapshot_digest` 鍵 ⇒ loader 拒（型別）；②bar 表缺 symbol/tf ⇒ `KeyError` loud。
- **存活至**：全票完工後保留（P2–P5 之 golden 皆用本 loader）。
- **覆蓋風險**：無。
- 不可做：不得以 aggregate（mean/std）代替逐 event 值；不得在 loader 內重算報酬公式。

**Task D1.5 — 前端：`/search` 解灰 `B` 與 `trigger_open`；匯出寫 provenance；揭露誠實化**
- 目標：B 可選、選了會落檔、揭露隨實際設定。　檔案：`frontend/src/lib/eventDimensions.ts`（`EVENT_DIM_PATH_EXCLUSIONS`：`/search|scenario` 值改 `['A','two_stage']`、理由更新；`/search|entry_price_semantic` 與 `/ic-analysis|entry_price_semantic` 值移除 `trigger_open`）；`frontend/src/lib/eventExport.ts`（record 增 `label_origin: 'search_positive_case'`、`search_rule_summary`＝當時搜尋條件之 canonical 字串）；`frontend/src/lib/eventFieldFormatters.ts`（scenario 文案由契約 `doc` 導出，已如此；新增 `label_origin` formatter）；`components/ic-analysis/EventBatchDisclosurePanel.tsx`（批次事實欄增 `label_origin` 顯示）。　既有 caller／影響面：`contractEnumWiring.test.tsx`、`eventContractOptions.test.tsx`、`eventExportOptions.test.ts`、`gap3_event_mode_entry.test.tsx`。
- 改法：只改單一常數與匯出對映；Task 7.2 三層機械閘沿用。
- **驗證**：`npx vitest run src/lib src/app/search src/components` 中：(i) `selectable('/search','scenario')` 集合相等 `{'B','C'}`；(ii) `selectable('/search','entry_price_semantic')` 集合相等 `{'trigger_close','trigger_open'}`；(iii) 選 `B`＋`trigger_open` 匯出之 record `scenario=='B'`、`entry_price_semantic=='trigger_open'`、`label_origin=='search_positive_case'`、`search_rule_summary` 非空；(iv) Task 7.2 mutation：把 `A` 改 enabled ⇒ ①紅（既有）。
- **邊界**：①`/data-preparation` 不受本常數影響（四種全開，既有）；②`search_rule_summary` 於無條件搜尋時為 canonical 空條件字串（非空白）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：P2／P3 會再縮小 `/search|scenario` 之排除值（同一常數），非覆蓋。
- 不可做：不得在元件內另寫 `if (value === 'A') disabled`；不得寫死任何 scenario 專屬文案。

**Task D1.6 — 後端揭露：`label_origin`／`event_known_at_decision` 入 detail 端點與批次事實欄**
- 目標：Task 7.6 批次事實欄擴為 `{scenario, control_kind, direction, t0, label, label_origin}`；分析 receipt 揭露 `event_known_at_decision` 之批內值集合（恆 `{False}`）。　檔案：`api/routes/ic_analysis.py`（detail 回應）；`api/services/ic_analysis_service.py`（揭露欄）；`api/models/ic_models.py`。　既有 caller／影響面：`tests/api -k event_batch_detail_dims`（驗收①之集合相等對象**擴一鍵**，測試須同步改期望集合並附 diff）。
- **驗證**：`pytest tests/api -q -k event_batch_detail_dims` 集合相等於六鍵；`label_origin` 為 scalar（批內常數，異質 ⇒ Task 1.8 拒）。
- **邊界**：①舊批（無 `label_origin`）⇒ detail 回 `null` 且前端顯示「（未宣告）」；②分析揭露於 `supported=False` 時仍列 `event_known_at_decision`。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得以 scalar 冒充 `t0`／`label`（R11）。

### Phase D2 — A（依賴：D1）

**Task D2.1 — `/search` 解灰 `A`：未標籤匯出路徑＋深度≥1**
- 目標：A 於 `/search` 可選，但 label **不得**由 `positive_case` 產生。　檔案：`eventDimensions.ts`（排除值改 `['two_stage']`）；`eventExport.ts`（`scenario ∈ {A}` ⇒ 強制走既有 `includeUnlabeled` 路徑：`label` 留空、`label_origin='user_csv'`；`positive_case` 不轉 label）；`/search` 匯出面板之 D-8 宣告框在 `scenario=A` 時 `max(depth) ≥ 1` 前端阻擋（`fetch` call count `== 0`）。
- **驗證**：vitest：(i) 選 A 匯出之每列 `label` 為空且 `label_origin=='user_csv'`；(ii) 深度 map 全 0 ⇒ 匯出按鈕 disabled 且理由字串含 `scenario_depth_inconsistent`；pytest：該匯出檔直接匯入 ⇒ `missing_required_field`（label 缺）——證明「A 不能靠解灰就算完成」被機器擋。
- **邊界**：①`includeUnlabeled=false` 且 `scenario=A` ⇒ 前端強制切為 true 並揭露；②CSV 路徑 A 之既有行為不變。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得把 `future_*` 附帶欄接成 /search 選樣條件（殘留，見 §N）。

### Phase D3 — two_stage（依賴：D1；與 D2 同構）

**Task D3.1 — `/search` 解灰 `two_stage`；provenance 與揭露**
- 目標：`two_stage` 可選；同 producer；去重 `all_with_uniqueness`（既有）；深度＝宣告較大者（D-8 既有）。　檔案：同 D2.1（排除值改 `[]`）；揭露文案由契約 `doc`（D1.1 ③）導出；`search_rule_summary` 記兩段條件之 canonical 字串（若 /search 僅一段，記一段並標 `stage_count=1`）。
- **驗證**：vitest `selectable('/search','scenario')` 集合相等 `{'A','B','C','two_stage'}`；pytest：`two_stage` 批之 `dedupe` summary `policy_primary=='all_with_uniqueness'`；深度 0 ⇒ `scenario_depth_inconsistent`。
- **邊界**：①既有 `api/routes/two_stage_search.py`（router 已註解）**不復活**；②兩段各自 `label_value` 不產（殘留）。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得新設兩段答案窗欄（D-8 逐 tf 宣告已涵蓋「取較大者」）。

### Phase D4 — (c) 其餘：producer 取價修法、open_to_*／next_open／decision_bar_*、k>0 與 k 之分析參數化（依賴：D1.3／D1.4）

**Task D4.1 — producer 取價：`entry_price_refs` 側載＋進 hash payload（群 1 採較嚴）**
- 目標：open 語意之基準價取 entry bar 之 `open`，消除連續網格別名之靜默錯價。　檔案：`label_value_from_case.py`：新 frozen dataclass `EntryPriceRef(event_id, bar_open_ms, field)`；`PreparedAnalysisWindows.entry_price_refs: tuple[EntryPriceRef, ...]`（與 `windows` 同序同長；`WindowRow` **維持七鍵**）；值逐字取自 `align_events` 收據 `entry_price_source_bar_open_ms`／`entry_price_source_field`；`_receipt_hash` payload 增 `"entry_price_refs": [[event_id, bar_open_ms, field], …]`；`resolve_label_value_at_analyze`：`close_to_close` ⇒ 基準 `close@close_time==label_start_ms`（不變）；`open_to_*` ⇒ 基準 `bars[field]@open_time==bar_open_ms` 且斷言 `label_start_ms == entry_at_ms`（不等 ⇒ `LabelProducerError`）；終點恆 `close@close_time==label_end_ms`。原檔 §D-3′-a（iii）hash 輸入清單增此一項（本檔覆寫 G-3 ⑥）。　既有 caller／影響面：`apply_event_coverage`（`replace` 攜帶）；`ic_analysis_service` 三處讀 hash（同 token 同 hash 不變式仍成立）；G-3 golden 之 hash 於本 Task 重凍一次（具名）。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k "analysis_label_producer and (open_to or entry_price_ref)"` ≥4 條：(i) 跳空 bar 案例：`trigger_open × open_to_close` 之 `label_value == (close[t0]-open[t0])/open[t0]`（手算自同一 bar 表），且 `!= (close[t0]-close[t0-1])/close[t0-1]`；(ii) `decision_bar_open × open_to_horizon_close, k=2` 基準＝`open[t0−2]`；(iii) mutation：ref.field open↔close 對調 ⇒ golden 紅（`ASSERT venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*open_to*.json" WHEN mutation=entry_ref_field_swapped THEN rc!=0`）；(iv) mutation：刪 refs ⇒ open 語意 `label_value is None` 且 reason 非空（fail-closed，不得回落 t₀−1 close）；(v) 改任一 ref 值 ⇒ `analysis_alignment_receipt_hash` 必變；(vi) 既有 `close_to_close` 組合之 `label_values` 逐位元組不變（hash 合法改變、值不變）。
- **邊界**：①`next_open × open_to_*` 之 `bar_open_ms = ot[t0_idx+1]`；②ref 之 bar 在 bar 表找不到唯一列 ⇒ `None`＋reason。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得依 `normalized_spec.entry_price_semantic` 在 producer 自判 open/close（第二份 D1-6 映射）；不得改 `WindowRow` 鍵數。

**Task D4.2 — 支援矩陣擴充 ②：全矩陣 ＋ k>0；golden 覆蓋**
- 目標：`SUPPORTED_MATRIX` ＝ 5 entry × 3 mode × k∈ℕ（k 只受對齊可行性限制）。　檔案：`label_value_from_case.py`；`eventDimensions.ts`（`/search`／`/ic-analysis` 三元組排除值清空；`decisionOffsetRange('/ic-analysis')` 改 `{min: 契約 min, max: null, locked: false}`；`/search` 之 k 控制項移除，見 D4.3）；golden 新增至少：`{trigger_open, next_open, decision_bar_open, decision_bar_close} × {open_to_close, open_to_horizon_close}` × k∈{0,2} × {long, short} × 12h（h∈{1,3}）＋ 1h 一組混 TF；含 `next_open × close_to_close` 之 `entry_after_label_start=true` 案例。
- **驗證**：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；`spec_is_supported` 對五×三×k∈{0,2} 全部 `True`；k=3 且資料起點不足 ⇒ 該 event 入 failures `warmup_insufficient_12h`（非 None 混入）。
- **邊界**：①`next_open` 且 `horizon_bars=0` 不存在（h≥1 既有）；②`decision_bar_close × open_to_close`：`label_start = ct[t0−k]`、`label_end = ct[t0−k]` ⇒ 窗長 0 ⇒ `no_boundary_match`（既有三段鏈 `label_start < label_end` 拒）——golden 須含此拒收案例。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得為任一組合寫特例公式。

**Task D4.3 — k 之分析參數化（裁定②）：UI 移除、種子不帶 k、雙值揭露、掃描上限**
- 目標：k 不由使用者於匯出／匯入時填；分析頁可掃。　檔案：契約 `analysis_params.decision_offset_bars_scan_max{value, example_default: 10, doc}`（新鍵；判斷值具名）；`EventDimensionFields.tsx`（`/search`、`/data-preparation` 之 k 控制項移除；CSV 欄對映仍可對映 k 欄——契約欄不變）；`eventExport.ts` 恆寫 `decision_offset_bars: 0`；`api/routes/ic_analysis.py:134-137`（`declaration_seeds` 不再帶 k；分析初始 k＝常數 0）；`EventBatchDisclosurePanel.tsx`（k 輸入 `max=null`，超過 `scan_max` 顯示警示不擋；必並排「批次記錄 k（record 值集合）／本次分析 k」）；`ic_analysis_service`（揭露 `decision_offset_bars_record_values: sorted set`、`decision_offset_bars_analysis: int`、`k_max_feasible: int`＝逐批由對齊可行性導出 `min_e max{k ≥ 0 : align_events(e,k) 有窗且 label 窗完整}`）。
- **驗證**：pytest：(i) 既有 k=1 批（`data_cache/events/20260901T132233Z-363ecc4f.json` 形態之 fixture）分析初始 k `== 0` 且揭露 `decision_offset_bars_record_values == [1]`；(ii) 缺任一揭露欄 ⇒ `capability_status=="unavailable"`（reason 新登記 `missing_decision_offset_disclosure`）；(iii) `k_max_feasible` 對真實 kline 三事件手算相等。vitest：`/search` DOM 無 `event-dim-decision_offset_bars`；`/data-preparation` 無 k 控制項但 CSV 對映表仍含 `decision_offset_bars` 欄。
- **邊界**：①分析 k > `k_max_feasible` ⇒ 全批 failures ⇒ `unavailable`（loud）；②分析 k 超 `scan_max` 但 ≤ feasible ⇒ 允許＋警示。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得改契約 `decision_offset_bars` 之必填／default（(乙) 裁定）；不得靜默重設既有批 record k。

### Phase D5 — (b) `platform_random_bars`（依賴：D1.4 golden、D4.1 producer）

**Task D5.1 — 契約：`random_control_spec` 與 estimand 字面**
- 目標：抽樣契約與 estimand 唯一住契約。　檔案：`event_import_contract.json`：`receipt_schema.batch.random_control_spec{universe{symbol,timeframe,start_ms,end_ms}, strata{symbol,timeframe,period,direction}, exclusion{trigger_ids_digest, neighborhood_bars, embargo_bars}, seed, n_requested, n_drawn, replacement(false), candidate_count, sample_ids_digest, data_snapshot_digest, generator_version}`；`control_kind.accepted` 增 `platform_random_bars`、移除其 `rejected_with_reason`；`capability_unavailable_reasons` 增 `random_control_prevalence_missing`；`import_failure_reasons` 增 `random_control_spec_missing`、`random_control_mixed_batch`；`doc` 寫 estimand：「同 universe 之非觸發 eligible bars 以同一 `label_definition` 規則自動標 label、同一 producer 算 `label_value`；回答觸發樣本相對無條件基準之 prevalence／IC lift；不回答反例品質、不補足缺失反例」。
- **驗證**：`pytest tests/momentum/event_samples/test_import_contract.py -q -k random_control` ≥3 條：缺 spec ⇒ `random_control_spec_missing`；觸發批內 `label_origin=platform_random` ⇒ `random_control_mixed_batch`；`control_kind=platform_random_bars` 批通過。
- **邊界**：①`n_drawn < n_requested` 允許但揭露；②跨 symbol universe ⇒ 拒。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得保留任何 fallback 分支。

**Task D5.2 — 產生器：確定性抽樣（純函式）**
- 目標：`momentum/Analysis/event_samples/random_control.py::sample_random_bars(bars, spec, trigger_receipts, label_rule) -> (records, receipt)`。　改法：universe＝`all_bars_eval._is_eligible` 判 eligible 之 bar；排除觸發 bar ±`neighborhood_bars`；分層依 `strata`；`numpy.random.default_rng(seed)` 無放回；label 由條件引擎純函式以觸發批之 `label_definition.canonical_digest` 同一規則評值；每列 `control_kind=platform_random_bars`、`label_origin=platform_random`、`scenario` 同觸發批；輸出過同一 validator（無 profile 分裂）。
- **驗證**：`pytest tests/momentum/event_samples/test_random_control.py -q` ≥4 條：(i) 同 seed 同 universe 重抽 `sample_ids_digest` 相等；(ii) 改 seed ⇒ 必不等；(iii) 抽中 bar 與觸發 bar 距離皆 `> neighborhood_bars`；(iv) 產出全過 validator。
- **邊界**：①候選數 < n_requested ⇒ `n_drawn=候選數` 並揭露；②候選數 0 ⇒ `unavailable`。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得以隨機 bar 補入觸發批之反例。

**Task D5.3 — 分析層：prevalence 並排與 `unavailable`；API／前端解灰**
- 目標：隨機批可匯入、可算條件 IC、報表與觸發批並排 prevalence。　檔案：`api/routes/event_import.py`（新端點 `POST /events/random-control` 產生並落檔）；`ic_analysis_service`（`sample_design='unconditional_random'` 揭露；比較觸發批 vs 隨機批時缺任一 prevalence ⇒ `unavailable:random_control_prevalence_missing`）；`eventDimensions.ts` 鏡像同步（`accepted` 增值）；`/search` 或 `/ic-analysis` 提供「產生隨機對照批」入口（依附既有觸發批）。
- **驗證**：pytest：隨機批之 IC 分析 `supported=True`、`label_values` 非空；缺 prevalence ⇒ `unavailable`；vitest：`selectable('/search','control_kind')` 含 `platform_random_bars`。
- **邊界**：①隨機批與觸發批 `label_definition.canonical_digest` 不等 ⇒ 比較拒；②隨機批單獨分析允許（其 IC＝無條件 IC 估計，揭露）。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得把隨機批當反例餵辨別表。

**Task D5.4 — golden：抽樣決定性與 label 規則一致**
- 目標：`tests/golden/gap3_random_control/<seed>__<tf>.json` 凍結 `sample_ids_digest`、`n_drawn`、逐列 label。　**驗證**：`--check` rc=0；mutation：改 `neighborhood_bars` ⇒ digest 必變。　**邊界**：universe 跨月分層。　**存活至**：保留。　**覆蓋風險**：無。　不可做：無合成 bar。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT a,d ⇒ 每 Task 附 mutation（上列 ASSERT 行）；最小紅集合：D1.2 `decision_at_close`；D1.4 `direction_sign_dropped`／`label_end_shift_one_bar`；D4.1 `entry_ref_field_swapped`／`entry_refs_dropped`／`entry_ref_value_changed`；D5.2 `seed_changed`／`neighborhood_changed`。
- 測試層級：契約單元（`test_import_contract.py`）／對齊單元（`test_alignment.py`）／producer＋golden（`test_gap3_analysis_label_producer.py`＋`scripts/gap3_label_golden.py --check`）／API（`tests/api -k "event_batch_detail_dims or random_control or decision_offset"`）／前端（vitest 三檔）。皆不需 `run_api.py`。
- **防假綠**：既有 `test_analysis_label_producer_03/05`（`next_open`／`open_to_close` 不支援）於 P1–P3 **不得改**；P4 改為「支援且值正確」時須附 diff 與新 golden；`hand_return` 手算函式於 open 語意須改讀 `bars[field]@open_time`，不得沿用 close。
- **邊界目錄**：空 records（既有拒）／全 None label（NaN mask 全集）／`std=0`（IC 層既有）／重複·亂序 bar（對齊層既有枚舉）／資料末端／跳空 bar（本檔必含）／k 超 feasible／隨機候選 0。
- 每 phase 三家 code review 至閉合（`docs/MULTI_AGENT_ORCHESTRATION.md` §1）；phase 間 commit 可單獨 revert。

## §R 回退
- 每 phase 獨立 commit；`SUPPORTED_MATRIX` 縮回即回到前一 phase 之 fail-closed；`EVENT_DIM_PATH_EXCLUSIONS` 為單一常數，還原即灰回；golden FAIL ⇒ 不 merge。無 feature flag（裁定：驗過即預設 ON，flag 只作對照——`feedback_no_default_off_after_validation`）。

## §N N/A 登記與殘留
- §G：filled（非 N/A）。
- **G3-R13** C 之「收盤後決策（`decision_at = t₀ close`、事件已知可進特徵）」語意 — `為何現在不做: user-ruling:2026-09-03 委員共識（使用者離線）本票不改 D2-2 單一表示法；待使用者裁定是否需要該語意（需 R 重開原 SPEC D2-2）`；觸發：使用者裁定「要」；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` GAP-3 殘留。修法候選：條件引擎 `lag(col,n)` 已支援之 t₀ 重錨（觸發後一根）。
- **兩段式各自 `label_value`／第二段自第一段 close 起算** — `為何現在不做: needs-research:第二段答案窗與反例種類 a 之對應未由使用者定義，且綁裁定③反例分類第二期`；觸發：裁定③第二期開工；登記處：同上。
- **`/search` 端以 future-outcome 規則產 A 之 label** — `為何現在不做: user-ruling:2026-09-02 D-006 已移除 /search 匯出前篩選、使用者於 CSV 自篩自標`；觸發：使用者要求 /search 端選樣支援未來欄；登記處：同上。
- **k 掃描軟上限 `example_default=10` 為判斷值** — `為何現在不做: needs-research:無自然上界（硬上限由對齊可行性逐批導出並揭露）`；觸發：使用者或委員給出推導依據；登記處：同上。
- **全部 K 線驗證接模型分數** — `為何現在不做: user-ruling:2026-09-03 裁定①（屬 IC→ML 橋之後）＋blocked-by:G3-R9`；登記處：`G3-R9`。
- **反例種類自動分類接入報表分組** — `為何現在不做: user-ruling:2026-09-03 裁定③（第二期）`；觸發：本票五 phase 收斂後；登記處：GAP-3 殘留。
- **codex 異議：契約 `decision_offset_bars` 改 optional（legacy-only）** — `為何現在不做: user-ruling:2026-09-03 委員共識採較嚴（保留必填 default 0；§C0 禁放寬 fail-closed）`；觸發：使用者裁定「欄位須消失」；登記處：GAP-3 殘留。

## 戳記
（三家 RECONCILE-STAMP 於對抗審收斂後 append；格式依 `templates/COMMITTEE_FINDING_TEMPLATE.md`。）
