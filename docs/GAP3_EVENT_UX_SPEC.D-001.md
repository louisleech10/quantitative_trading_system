# GAP3_EVENT_UX_SPEC — D 延伸 001（`G3-D2` 灰色項目完成：scenario A／B／two_stage、三元組其餘值與 k、`platform_random_bars`）

BASE: docs/GAP3_EVENT_UX_SPEC.md @ 55c0a9d50b92
PREDECESSOR: none

改什麼: 把 §F-1′／Task 7.1／Task 7.6／§N-7 以「本批」限定之三類 disabled 值改為**可選且分析層算得出 `label_value`**，依使用者裁定順序 (a)→(c)→(b) 分五個 phase 交付，每個 phase 有逐組合 exact golden、provenance 與誠實揭露。

為什麼: 票 `docs/IC_QUANT_GAP_REGISTRY.md` `G3-D2`（user-ruling 2026-08-31／2026-09-02：灰項不接受永久灰著、順序 (a)→(c)→(b)）；consult 收斂 `handoffs/reconcile/20260903-gap3d2-x-consult-r1/synth.md`（本機；四來源九群集，Verdict＝需修補後合併、形式＝D 延伸）。原檔 F-5′（L2458）與原 SPEC §N-7 本就把開放寫成有前置之路徑，本檔不推翻既有設計。

## 觸及面宣告
新增: 無新增原檔 heading；本檔內新增 Task D1.1–D5.4（編號以 `D` 前綴與原檔 Task 區隔）。
覆寫: **F-1′ 分析層支援矩陣（封閉集合；R8 由匯出層改掛分析層）**；**F-5′ 開放更多組合之前置**；**Task 7.1 — 五維度全部接出前端（依賴 Task 7.0）**（僅 `EVENT_DIM_PATH_EXCLUSIONS` 之封閉內容與 `scenario` 路徑級限制段）；**Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（R4 群集 C／遺留 E；R8 依 §D-3′ 改寫；R10 定死事實欄形狀）**（③ 分析參數區之可操作集合、`decision_offset_bars` 初始值來源，**以及**「批次事實欄」三分權威表之封閉集合與驗收①之集合相等對象——R1 GROK-R1-P1-02／CODEX-R1-P1-02 擴列）；**G-3 analysis-label golden（R8 新建；R9 擴逐列 purge；R10 加 receipt hash 與混 TF 覆蓋面）**（固定輸入集合擴充＋凍結對象 ⑥ 之 hash payload 增 `entry_price_refs`）；**（iii）分析時 receipt 之唯一性與階段順序（CODEX-R9-P0-01）**（hash 輸入 dict 之唯一合法形狀——R1 GROK-R1-P1-03 擴列；新形狀以 Task D4.1 之 code fence 為唯一權威）。
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
- FACT-RECEIPT: `sed -n 43p momentum/Analysis/event_samples/bars_source.py` → 印出 `"close_time_ms": open_ms + TIMEFRAME_SECONDS[tf] * 1000,`（主委 實跑 2026-09-03）⇒ **時間戳**連續 `open_time(t₀) == close_time(t₀−1)`；🔴 時間戳連續 ≠ 價格連續（R1 COMPOSER-R1-P2-01）——§G 必含案例①用**價格欄**：FACT-RECEIPT: `venv/bin/python` 讀 `load_bars("ETHUSDT",("12h","1h"))` 計 `(open[1:] != close[:-1]).sum()` → 印出 `12h: 828/1696`、`1h: 9909/20352`（主委 實跑 2026-09-03；receipt `handoffs/20260903-gap3d2-review-r1-selfcheck.md`）
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
- 🔴 **本檔新增之契約字面總表（唯一登記處＝`event_import_contract.json`；本表只列名，值與 doc 住契約；各 phase 於其 Task 落地）**：`optional_fields.label_origin.enum = {search_positive_case, user_csv, platform_generator, platform_random, search_unlabeled}` 與 `not_importable = [search_unlabeled]`（D1.1／D2.1）；`import_failure_reasons` 增 `scenario_depth_inconsistent`（D1.1）、`label_origin_not_importable`（D2.1）、`random_control_spec_missing`、`random_control_mixed_batch`（D5.1）；`capability_unavailable_reasons` 增 `missing_decision_offset_disclosure`（D4.3）、`random_control_prevalence_missing`、`random_control_period_mismatch`（D5）；`label_definition.fields.label_return_mode.rejected_pairs = {open_to_close: [trigger_close, decision_bar_close]}` reason `zero_length_label_window`（D4.2）；`analysis_params.decision_offset_bars_scan_max`（D4.3）；`required_fields.entry_price_semantic.default = "trigger_close"`（D4.2 pair 重設之唯一來源；R3）；`receipt_schema.batch.random_control_spec`（D5.1）；`receipt_schema.event_level` 增 `event_known_at_decision`（D1.2）；`derived_fields.names` 不變。前端 `EVENT_DIM_CONTRACT_MIRROR` 逐 phase 同步，漂移由既有測試擋。
- 改法：①`optional_fields.label_origin`：`enum` 如上表，`doc` 說明各值來源；缺值時 validator **不補值**、但 record 級 `scenario ∈ {A, B, two_stage}` 且缺 `label_origin` ⇒ 拒 `conditional_required_missing`（既有 reason）。②`import_failure_reasons` 增 `scenario_depth_inconsistent`；validator 規則：`scenario ∈ {A, two_stage}` ⇒ `max(lookahead_bars_declared.values()) ≥ 1`；`scenario == B` ⇒ 允許 0；`lookahead_bars_declared` 缺 ⇒ 沿用 D-7 L2 既有拒收。③`required_fields.scenario.doc` 改為誠實描述（決策時點恆為 `t₀−k` open；C＝t₀ 條件為深度 0 之事件、收盤後決策不可表示、見 `G3-R13`；A／B＝事件相對決策為未來、`event_known_at_decision=false`；two_stage＝深度取兩段較大者，兩段各自 `label_value` 未交付）。
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
- 目標：**覆寫** Task 7.6 三分權威表之「批次事實欄」封閉集合與驗收①之集合相等對象：由 `{scenario, control_kind, direction, t0, label}` 改為 `{scenario, control_kind, direction, t0, label, label_origin}`；`label_origin` 之 wire shape＝**scalar**（批內常數，異質 ⇒ Task 1.8 拒；舊批無此欄 ⇒ `null`），**不得**進 `event_label_spec`、不可於 IC 頁修改；formatter 依 Task 7.6 欄位級 registry 新增一個。分析 receipt 另揭露 `event_known_at_decision` 之批內值集合（D2-2 下恆 `{False}`）。　檔案（R2 CODEX-R2-P1-06 更正為實際位置）：detail 端點 `api/routes/case.py:366`（`EventImportDetailResponse`）、`api/models/event_import_models.py:159-165`（`EventImportDetailResponse`／`EventDeclarationSeeds`／`EventBatchFactNotes`——`response_model` 過濾，缺欄即靜默丟）、`frontend/src/lib/types.ts`（對應 TS type）、`api/services/case_import_service.py:1390-1394`（填值）、`api/services/ic_analysis_service.py`（分析揭露欄）、`tests/api/test_gap3_event_batch_detail_dims.py`。　既有 caller／影響面：`tests/api -k event_batch_detail_dims`（驗收①之集合相等對象**擴一鍵**，測試須同步改期望集合並附 diff）。
- **驗證**：`pytest tests/api -q -k event_batch_detail_dims` 集合相等於六鍵；`label_origin` 為 scalar（批內常數，異質 ⇒ Task 1.8 拒）。
- **邊界**：①舊批（無 `label_origin`）⇒ detail 回 `null` 且前端顯示「（未宣告）」；②分析揭露於 `supported=False` 時仍列 `event_known_at_decision`。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得以 scalar 冒充 `t0`／`label`（R11）。

### Phase D2 — A（依賴：D1）

**Task D2.1 — `/search` 解灰 `A`：未標籤匯出路徑＋深度≥1**
- 目標：A 於 `/search` 可選，但 label **不得**由 `positive_case` 產生。　檔案：`eventDimensions.ts`（排除值改 `['two_stage']`）；`eventExport.ts`（`scenario ∈ {A}` ⇒ 強制走既有 `includeUnlabeled` 路徑：`label` **鍵缺席**（禁 `""`、禁 `0`；R1 GROK 6a）、`label_origin='search_unlabeled'`（**匯出專用標記**，R1 CODEX-R1-P2-07：未經使用者標註前不得寫 `user_csv`）；`positive_case` 不轉 label）；契約 `label_origin` enum 增 `search_unlabeled` 並列於 `not_importable`（匯入見到即拒 `label_origin_not_importable`，同 `counterexample_kind_not_importable` 先例）；`/data-preparation` 之批次預設（Task 1.8 `batch_defaults`）提供 `label_origin=user_csv` 供使用者補標後匯入；匯出面板固定揭露字面（由契約 `doc` 導出）：「scenario=A／two_stage 時本路徑**不產** label；`label_origin=search_unlabeled` 表示須於 CSV 自填後以 `user_csv` 匯入；補標前匯入必拒」；`/search` 匯出面板之 D-8 宣告框在 `scenario=A` 時 `max(depth) ≥ 1` 前端阻擋（`fetch` call count `== 0`）。
- **驗證**：vitest：(i) 選 A 匯出之每列**無 `label` 鍵**且 `label_origin=='search_unlabeled'`；(ii) 深度 map 全 0 ⇒ 匯出按鈕 disabled 且理由字串含 `scenario_depth_inconsistent`；(iii) 揭露 DOM 含上述固定字面。pytest：(a) 該匯出檔直接匯入 ⇒ reasons 集合 `== {"missing_required_field", "label_origin_not_importable"}`；(b) 補 `label` 後仍帶 `search_unlabeled` ⇒ `label_origin_not_importable`；(c) 補 `label`＋`batch_defaults={"label_origin": "user_csv"}` ⇒ 通過且 record `label_origin=='user_csv'`——三態（R1 CODEX-R1-P2-07 RECHECK）。
- **邊界**：①`includeUnlabeled=false` 且 `scenario=A` ⇒ 前端強制切為 true 並揭露；②CSV 路徑 A 之既有行為不變；③`label: null` 與鍵缺席同視為缺（validator 既有 `r[name] is None`）。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得把 `future_*` 附帶欄接成 /search 選樣條件（殘留，見 §N）。

### Phase D3 — two_stage（依賴：D1；與 D2 同構）

**Task D3.1 — `/search` 解灰 `two_stage`；provenance 與揭露**
- 目標：`two_stage` 可選；同 producer；去重 `all_with_uniqueness`（既有）；深度＝宣告較大者（D-8 既有）。　檔案：同 D2.1（排除值改 `[]`）；揭露文案由契約 `doc`（D1.1 ③）導出；`search_rule_summary` 記兩段條件之 canonical 字串；🔴 `/search` 選 `two_stage` 時**必須**有兩段條件（`stage_count == 2`），僅一段 ⇒ 前端阻擋匯出（理由 `two_stage_requires_two_stages`，`fetch` call count `== 0`），**不降級**為 A／B（R1 CODEX-R1-P2-06）；`stage_count`／兩段各自 canonical digest 記入 record `search_rule_summary`（單一字串，形狀由契約 `doc` 定）。既有 `api/routes/two_stage_search.py` 仍由 `api/main.py:188-193,377-381` 條件式掛載（非註解；R1 更正）——**不動、不接**本 Task，與本路徑隔離（其產物無 provenance，不得匯入為 two_stage 批）。
- **驗證**：vitest `selectable('/search','scenario')` 集合相等 `{'A','B','C','two_stage'}`；pytest：`two_stage` 批之 `dedupe` summary `policy_primary=='all_with_uniqueness'`；深度 0 ⇒ `scenario_depth_inconsistent`。
- **邊界**：①既有 `/two-stage` router 維持現狀、不接本路徑；②兩段各自 `label_value` 不產（殘留）；③一段輸入 ⇒ 匯出阻擋（見上），不得靜默寫 `stage_count=1`。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得新設兩段答案窗欄（D-8 逐 tf 宣告已涵蓋「取較大者」）。

### Phase D4 — (c) 其餘：producer 取價修法、open_to_*／next_open／decision_bar_*、k>0 與 k 之分析參數化（依賴：D1.3／D1.4）

**Task D4.1 — producer 取價：`entry_price_refs` 側載＋進 hash payload（群 1 採較嚴）**
- 目標：open 語意之基準價取 entry bar 之 `open`，消除連續網格別名之靜默錯價。　檔案：`label_value_from_case.py`：新 frozen dataclass `EntryPriceRef(event_id, bar_open_ms, field)`；`PreparedAnalysisWindows.entry_price_refs: tuple[EntryPriceRef, ...]`（與 `windows` 同序同長；`WindowRow` **維持七鍵**）；值逐字取自 `align_events` 收據 `entry_price_source_bar_open_ms`／`entry_price_source_field`；`_receipt_hash` payload 增 `"entry_price_refs": [[event_id, bar_open_ms, field], …]`；`resolve_label_value_at_analyze`：`close_to_close` ⇒ 基準 `close@close_time==label_start_ms`（不變）；`open_to_*` ⇒ 基準 `bars[field]@open_time==bar_open_ms` 且斷言 `label_start_ms == entry_at_ms`（不等 ⇒ `LabelProducerError`）；終點恆 `close@close_time==label_end_ms`。🔴 **hash 輸入 dict 之唯一合法形狀（本檔覆寫原檔（iii）之 code fence；R1 GROK-R1-P1-03）**——原檔 fence（`batch`／`event_level`／`per_tf` 三頂層鍵）與現行 `_receipt_hash`（`label_value_from_case.py:418-447`）**已分叉**（既有漂移，非本檔造成；具名於 §N）。本檔以**現行碼形狀＋新增一鍵**為唯一權威，實作者不得另讀原檔 fence：
  ```python
  payload = {                       # 頂層鍵固定此六個、固定此序，不得增減
    "event_import_id": str,
    "direction_sign": int,
    "normalized_spec_bytes": str,   # normalized event_label_spec 之 S-9 位元組 utf-8 解碼
    "windows": [[event_id, symbol, timeframe, decision_at_ms, entry_at_ms, label_start_ms, label_end_ms], ...],
    "per_tf": [[event_id, timeframe, feature_cutoff_ms], ...],
    "entry_price_refs": [[event_id, bar_open_ms, field], ...],   # 🔴 本檔新增；與 windows 同序同長
  }
  ```
  序列化＝`canonical_event_table_sha256(payload)`（§G S-9 同一 encoder）。　既有 caller／影響面：`apply_event_coverage`（`replace` 攜帶）；`ic_analysis_service` 三處讀 hash（同 token 同 hash 不變式仍成立）；G-3 golden 之 hash 於本 Task 重凍一次（具名）。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k "analysis_label_producer and (open_to or entry_price_ref)"` ≥4 條：(i) 跳空 bar 案例：`trigger_open × open_to_close` 之 `label_value == (close[t0]-open[t0])/open[t0]`（手算自同一 bar 表），且 `!= (close[t0]-close[t0-1])/close[t0-1]`；(ii) `decision_bar_open × open_to_horizon_close, k=2` 基準＝`open[t0−2]`；(iii) mutation：ref.field open↔close 對調 ⇒ golden 紅（`ASSERT venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*open_to*.json" WHEN mutation=entry_ref_field_swapped THEN rc!=0`）；(iv) mutation：刪 refs ⇒ open 語意 `label_value is None` 且 reason 非空（fail-closed，不得回落 t₀−1 close）；(v) 改任一 ref 值 ⇒ `analysis_alignment_receipt_hash` 必變；(vi) 既有 `close_to_close` 組合之 `label_values` 逐位元組不變（hash 合法改變、值不變）。
- **邊界**：①`next_open × open_to_*` 之 `bar_open_ms = ot[t0_idx+1]`；②ref 之 bar 在 bar 表找不到唯一列 ⇒ `None`＋reason。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得依 `normalized_spec.entry_price_semantic` 在 producer 自判 open/close（第二份 D1-6 映射）；不得改 `WindowRow` 鍵數。

**Task D4.2 — 支援矩陣擴充 ②：全矩陣 ＋ k>0；golden 覆蓋**
- 目標：`SUPPORTED_MATRIX` ＝ 5 entry × 3 mode × k∈ℕ **減去幾何上必拒之對**（R1 CODEX-R1-P1-01／GROK-R1-P1-01）：`{trigger_close, decision_bar_close} × open_to_close`（`label_start = entry_at = ct[entry_idx]` 且 `label_end = ct[entry_idx]` ⇒ 窗長 0 ⇒ 三段鏈 `no_boundary_match`，真實 kline 實跑 k∈{0,2} 皆 0 窗）**不在集合內**、UI 對該兩對顯示理由 `zero_length_label_window`（登記於契約 `label_return_mode.rejected_pairs`；🔴 既有 `rejected_with_reason` 為**單維度值**拒收、`dimOptions` 無跨維度成對機制 ⇒ `eventDimensions.ts` 新增第四種 `kind: 'pair_rejected'`：`dimOptions(path, dim, contract, selection)` 於 `dim == label_return_mode` 且 `selection.entry_price_semantic ∈ rejected_pairs[value]` 時標 disabled，反向（`dim == entry_price_semantic` 且 `selection.label_return_mode` 之 pair 含該值）亦標；理由字面由契約導出；鏡像 `EVENT_DIM_CONTRACT_MIRROR` 同步；Task 7.2 三層閘擴一條「pair 對稱性：兩方向 disabled 集合互為映射」。🔴 **接線與既選非法狀態（R2 CODEX-R2-P1-03）**：兩個既有 caller **必改**為傳 `selection`——`frontend/src/components/case/EventDimensionFields.tsx:69`、`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx:130`（`grep -n "dimOptions(" frontend/src` 之全部命中）；`selectable(path, dim, contract, selection?)` 同步加可選 `selection`（無 selection ⇒ 舊行為，供 Task 7.2 之 selection-free 閘沿用）；**既選非法 pair**（改一維使另一維現值落入 pair）⇒ 另一維**自動重設為契約 `default`** 並顯示揭露字串「因 pair 拒收已重設」（不靜默保留非法組合）——🔴 R3 GROK-R3-P1-01：契約 `entry_price_semantic` 現**無** `default` ⇒ D1.1 契約字面總表增 `required_fields.entry_price_semantic.default = "trigger_close"`（＝原檔 §F-3′ 誠實預設之唯一來源，前端現行硬編碼 `trigger_close` 改讀契約；`label_return_mode.default` 既有 `close_to_close`）；重設一律讀契約 `default`，禁前端硬編；vitest 加「兩方向重設皆讀契約 default」一條；送出前守衛：`selection` 落入 `rejected_pairs` ⇒ 阻擋（`fetch` call count `== 0`）；vitest 雙向各一條＋重設一條＋守衛一條。）k 只受對齊可行性限制。🔴 **順序**：先定矩陣、再凍 golden（R1 GROK 9），不得先凍全矩陣再刪。　檔案：`label_value_from_case.py`；`eventDimensions.ts`（`/search`／`/ic-analysis` 三元組排除值清空；`decisionOffsetRange('/ic-analysis')` 改 `{min: 契約 min, max: null, locked: false}`；`/search` 之 k 控制項移除，見 D4.3）；golden 新增至少：`{trigger_open, next_open, decision_bar_open, decision_bar_close} × {open_to_close, open_to_horizon_close}` × k∈{0,2} × {long, short} × 12h（h∈{1,3}）＋ 1h 一組混 TF；含 `next_open × close_to_close` 之 `entry_after_label_start=true` 案例。
- **驗證**：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；`spec_is_supported` 對集合內組合（13 對 × k∈{0,2}）全部 `True`、對 `{trigger_close, decision_bar_close} × open_to_close` 全部 `False` 且 reason `== "zero_length_label_window"`（不得為 `supported=True` 而全批 failures）；k=3 且資料起點不足 ⇒ 該 event 入 failures `warmup_insufficient_12h`（非 None 混入）。🔴 **支援域與 oracle 之誠實對應（R1 CODEX-R1-P1-04 → R2 CODEX-R2-P1-01；R2 CODEX-R2-P1-05）**：宣告之支援域**不是** k∈ℕ×h∈ℕ，也**不是**兩個獨立區間（R3 CODEX-R3-P1-01：`decision_bar_* × open_to_horizon_close` 之 `end_idx = t0_idx − k + h` 使 k、h 耦合），而是**逐事件成對可行性謂詞** `feasible(e, k, h)`（唯一定義，實作於階段 2、以 bar index 閉式算，不重跑對齊）：`(t0_idx(e) − k ≥ 0) ∧ (end_idx(e, k, h) ≤ n_bars(e) − 1) ∧ coverage_ok(e, k)`，其中 `end_idx` 依 mode：`close_to_close ⇒ t0_idx + h`；`open_to_horizon_close ⇒ entry_idx(e, k) + h`；`open_to_close ⇒ entry_idx(e, k)`；`entry_idx` 依 D1-6（`next_open ⇒ t0_idx + 1`、`decision_bar_* ⇒ t0_idx − k`、其餘 `t0_idx`）；`coverage_ok(e, k)` ＝ 階段 3 對 `decision_at(k)` 之 feature coverage。分析時：不可行事件入既有 failures（`warmup_insufficient_<tf>`／`label_window_incomplete`／coverage 剔除，逐事件 loud），**全批不可行** ⇒ `unavailable`；同時揭露兩個**條件上界**（供 UI 顯示、非輸入鎖）：`k_max_feasible_at_h = min_e max{k : feasible(e, k, h_selected)}`、`h_max_feasible_at_k = min_e max{h : feasible(e, k_selected, h)}`（R3 GROK-R3-P2-01：兩者皆有公式、揭露欄、驗收；D4.3 之 `k_max_feasible` 即前者）。🔴 **誠實邊界（R4 CODEX-R4-P2-01／GROK-R4-P2-01）**：兩條件上界為**幾何／coverage 上界**（只對應 `warmup_insufficient_*`／`label_window_incomplete`／coverage）；`align_events` 之 `missing_bar`／`nonpositive_reference_price`／`entry_before_decision`／`feature_after_decision` 仍逐事件 loud 拒、**不納入** `feasible` 閉式——超上界 ⇒ 幾何上必失敗；≤ 上界 ⇒ **不保證**零 failures；UI／驗收文案不得把「≤ 上界」寫成全批成功保證。驗收：真實 kline 取三事件手算兩上界 `==`；mutation：`end_idx` 少算一根 ⇒ 兩上界皆變；`decision_bar_open × open_to_horizon_close` 取 `(k, h) = (k_max_at_h, h)` 通過、`(k_max_at_h + 1, h)` 該事件入 failures。oracle 分三層，缺一即紅：(1) **凍結層**＝有限 golden（§G 清單）；(2) **獨立 raw-bar oracle**（不得引用 receipt 之 `entry_price_ref`／時間戳當期望值）：測試檔內以**期望表**寫死 D1-6 五語意之 `(bar_offset, field)`＝`trigger_open=(0,open)`、`trigger_close=(0,close)`、`next_open=(+1,open)`、`decision_bar_open=(−k,open)`、`decision_bar_close=(−k,close)` 與三 mode 之 `(start_bar, end_bar)`，自 raw bars 以 index 算期望 `entry_at_ms`／`label_start_ms`／`label_end_ms`／`label_value`，再與 receipt＋producer 輸出逐欄 `==`——alignment 與 ref 若協同錯誤，本層獨立紅；(3) **property 層**＝`pytest … -k label_differential_grid`：固定網格 13 對 × k∈{0,1,2,4} × h∈{1,2,3,5,7} × {long, short} **加** seeded 隨機抽樣（`seed=20260903`，每次 40 組 `(k,h)` 均勻取自可行域），逐 event 以 (2) 之期望表比對（`atol=0`），NaN mask 與 failures reason 集合相等。誠實邊界：可行域內未被 (1)(3) 覆蓋之 `(k,h)` 只有 (2) 之同型 oracle 保證，無 exact 凍結——具名於 §N（`needs-research`）。
- **邊界**：①`next_open` 且 `horizon_bars=0` 不存在（h≥1 既有）；②`{trigger_close, decision_bar_close} × open_to_close` 由矩陣層擋（`zero_length_label_window`），對齊層之 `no_boundary_match` 為第二道——golden 須含此對之「矩陣拒收」案例。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得為任一組合寫特例公式。

**Task D4.3 — k 之分析參數化（裁定②）：UI 移除、種子不帶 k、雙值揭露、掃描上限**
- 目標：k 不由使用者於匯出／匯入時填；分析頁可掃。　檔案：契約 `analysis_params.decision_offset_bars_scan_max{value, example_default: 10, doc}`（新鍵；判斷值具名）；`EventDimensionFields.tsx`（`/search`、`/data-preparation` 之 k 控制項移除；CSV 欄對映仍可對映 k 欄——契約欄不變）；`eventExport.ts` 恆寫 `decision_offset_bars: 0`；`api/routes/ic_analysis.py:134-137`（`declaration_seeds` 不再帶 k；分析初始 k＝常數 0）；🔴 **種子表銜接清單（R1 COMPOSER-R1-P2-02；缺一即實作與測試打架）**：`api/models`（`EventDeclarationSeeds` 移除 `decision_offset_bars` 欄）、`api/services/case_import_service.py:1390-1394`（不再填 seeds.k；改填 `batch_fact_notes.decision_offset_bars_record_values: sorted set`）、`tests/api/test_gap3_event_batch_detail_dims.py:28` `SEED_KEYS` 改為兩鍵並附 diff、`EventBatchDisclosurePanel.tsx:172` 之 `?? detail.declaration_seeds.decision_offset_bars` 移除（初始值＝常數 0，記錄值走獨立揭露欄）；`EventBatchDisclosurePanel.tsx`（k 輸入 `max=null`，超過 `scan_max` 顯示警示不擋；必並排「批次記錄 k（record 值集合）／本次分析 k」）；`ic_analysis_service`（揭露 `decision_offset_bars_record_values: sorted set`、`decision_offset_bars_analysis: int`、`k_max_feasible_at_h: int` 與 `h_max_feasible_at_k: int`＝依 D4.2 之 `feasible(e, k, h)` 導出之兩個條件上界（R3：成對謂詞取代獨立區間；coverage 條件不得省略））。
- **驗證**：pytest：(i) 既有 k=1 批（`data_cache/events/20260901T132233Z-363ecc4f.json` 形態之 fixture）分析初始 k `== 0` 且揭露 `decision_offset_bars_record_values == [1]`；(ii) 缺任一揭露欄 ⇒ `capability_status=="unavailable"`（reason 新登記 `missing_decision_offset_disclosure`）；(iii) `k_max_feasible_at_h`／`h_max_feasible_at_k` 對真實 kline 三事件手算相等（含一 `decision_bar_open × open_to_horizon_close` 事件證明耦合）。vitest：`/search` DOM 無 `event-dim-decision_offset_bars`；`/data-preparation` 無 k 控制項但 CSV 對映表仍含 `decision_offset_bars` 欄。
- **邊界**：①分析 k > `k_max_feasible` ⇒ 全批 failures ⇒ `unavailable`（loud）；②分析 k 超 `scan_max` 但 ≤ feasible ⇒ 允許＋警示。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得改契約 `decision_offset_bars` 之必填／default（(乙) 裁定）；不得靜默重設既有批 record k。

### Phase D5 — (b) `platform_random_bars`（依賴：D1.4 golden、D4.1 producer）

**Task D5.1 — 契約：`random_control_spec` 與 estimand 字面**
- 🔴 **nested typed schema（R2 CODEX-R2-P1-02）**：`receipt_schema.batch.random_control_spec` 之值為 typed object 定義（每葉 `{type: <既有 leaf token>, required: bool}`；`universe`／`strata`／`exclusion` 為 nested object、`per_stratum` 為 `list[object]`），`receipt_type_ok` 擴為**遞迴**（新增 `object`／`list[object]` 兩型；既有 leaf tokens 不變、既有欄逐位元組行為不變），negative tests：缺必填葉、葉型別錯、多未知葉 ⇒ 各自 `ValueError` 且訊息含葉路徑（`batch.random_control_spec.universe.symbol`）。
- 目標：抽樣契約與 estimand 唯一住契約，且 **wire 唯一**（R1 CODEX-R1-P1-03）：`random_control_spec` 為**批次級 envelope 物件**（非逐列欄）——匯入 API body `{"records": [...], "random_control_spec": {...}}`；`validate_event_import(records, *, random_control_spec: Optional[Mapping] = None, ...)` 新 keyword；規則：`control_kind == platform_random_bars`（批內常數）⇒ spec **必填**，缺 ⇒ `random_control_spec_missing`；`control_kind != platform_random_bars` 而 spec 出現 ⇒ `random_control_mixed_batch`；通過後 spec 原樣寫入 `receipt.batch.random_control_spec` 並隨批落檔（detail 端點回傳）。　檔案：`event_import_contract.json`：`receipt_schema.batch.random_control_spec{universe{symbol,timeframe,start_ms,end_ms}, strata{symbol,timeframe,period,direction}, allocation:"proportional_to_candidates", exclusion{trigger_ids_digest, neighborhood_bars, embargo_bars}, seed, n_requested, n_drawn, per_stratum:[{key, n_candidates, n_drawn}], replacement(false), candidate_count, sample_ids_digest, data_snapshot_digest, generator_version}`；`control_kind.accepted` 增 `platform_random_bars`、移除其 `rejected_with_reason`；`capability_unavailable_reasons` 增 `random_control_prevalence_missing`；`import_failure_reasons` 增 `random_control_spec_missing`、`random_control_mixed_batch`；`doc` 寫 estimand：「同 universe 之非觸發 eligible bars 以同一 `label_definition` 規則自動標 label、同一 producer 算 `label_value`；回答觸發樣本相對無條件基準之 prevalence／IC lift；不回答反例品質、不補足缺失反例」。
- **驗證（wire 鏈四段，缺一即紅；R1 COMPOSER-R1-P1-02）**：(a) 契約：`jq '.receipt_schema.batch | has("random_control_spec")'` `== true` 且 `flatten_receipt_schema` 輸出含 `batch.random_control_spec`；(b) validator：`pytest tests/momentum/event_samples/test_import_contract.py -q -k random_control` ≥4 條——`control_kind=platform_random_bars` 缺 spec ⇒ `random_control_spec_missing`；非隨機批帶 spec ⇒ `random_control_mixed_batch`；觸發批內 `label_origin=platform_random` ⇒ `random_control_mixed_batch`；隨機批帶合法 spec ⇒ 通過；`inspect.signature(validate_event_import)` 含 keyword-only `random_control_spec`；(c) 落檔 round-trip：`pytest tests/api -q -k random_control_roundtrip`——經 `case_import_service` 落檔後 `get_import(id).receipt.batch.random_control_spec ==` 送入值（逐鍵）；(d) detail 端點回傳同值。D5.3 之 wire 以本表為唯一來源。
- **邊界**：①`n_drawn < n_requested` 允許但揭露；②跨 symbol universe ⇒ 拒。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得保留任何 fallback 分支。

**Task D5.2 — 產生器：確定性抽樣（純函式）**
- 目標：`momentum/Analysis/event_samples/random_control.py::sample_random_bars(bars, spec, trigger_receipts, label_rule) -> (records, receipt)`。　改法：universe＝`all_bars_eval._is_eligible` 判 eligible 之 bar；**排除區間（R1 CODEX-R1-P1-05 定死）**：候選 bar index `i` 被排除 iff ∃ 觸發事件 `t`：`t0_idx(t) − neighborhood_bars ≤ i ≤ label_end_idx(t) + embargo_bars`（前鄰域＝`neighborhood_bars`、後鄰域＝答案窗末＋`embargo_bars`；兩者皆 ≥0，缺任一 ⇒ 契約拒）；**分層配額**＝`allocation="proportional_to_candidates"`（R2 CODEX-R2-P1-04 定死，禁 `round`）：`n_target = min(n_requested, candidate_count)`；各 stratum `base = floor(n_target × n_candidates / candidate_count)`；`remainder = n_target − Σbase`（恆 ≥0），依各 stratum 之小數部分降冪、同分依 stratum key UTF-8 升冪，逐一 +1 至 remainder 用完；每 stratum `n_drawn ≤ n_candidates`（cap；cap 後之缺額依同序再分配，候選耗盡則停）；不變式 `Σ per_stratum.n_drawn == n_drawn == n_target`（測試斷言）；`per_stratum` 寫入 receipt；`strata.period` 須與觸發批之 `[min t0, max label_end]` 有交集，否則 `random_control_period_mismatch`（R1 GROK-R1-P2-02）；`numpy.random.default_rng(seed)` 無放回；label 由條件引擎純函式以觸發批之 `label_definition.canonical_digest` 同一規則評值；每列 `control_kind=platform_random_bars`、`label_origin=platform_random`、`scenario` 同觸發批；輸出過同一 validator（無 profile 分裂）。
- **驗證**：`pytest tests/momentum/event_samples/test_random_control.py -q` ≥7 條：(i) 同 seed 同 universe 重抽 `sample_ids_digest` 相等；(ii) 改 seed ⇒ 必不等；(iii) 抽中 bar 對每個觸發事件皆在排除區間外（`i < t0_idx − neighborhood` 或 `i > label_end_idx + embargo`）；反例 `neighborhood_bars=0, embargo_bars=6` 時觸發前一根**不得**被抽中（前鄰域 0 但該根落在其他觸發之後鄰域內者亦排除）；(iv) 兩 stratum 候選數 3:1 ⇒ `per_stratum.n_drawn` 比例相符且和 `== n_drawn`；(v) `strata.period` 與觸發期無交集 ⇒ `random_control_period_mismatch`；(vi) 產出全過 validator；(vii) mutation：改 `embargo_bars` ⇒ `sample_ids_digest` 必變。
- **邊界**：①候選數 < n_requested ⇒ `n_drawn=候選數` 並揭露；②候選數 0 ⇒ `unavailable`。
- **存活至**：保留。　**覆蓋風險**：無。　不可做：不得以隨機 bar 補入觸發批之反例。

**Task D5.3 — 分析層：prevalence 並排與 `unavailable`；API／前端解灰**
- 目標：隨機批可匯入、可算條件 IC、報表與觸發批並排 prevalence。　檔案：`api/routes/case.py`（既有 `/case/import-events*` 家族；新端點 `POST /case/import-events/random-control`，body `{event_import_id: <觸發批>, random_control_spec: {...}}`，回 `EventImportResponse`；**不新建** `api/routes/event_import.py`——R1 COMPOSER-R1-P1-01，該檔不存在）；`api/services/case_import_service.py`（落檔走既有 storage，`get_import` 回傳 `receipt.batch.random_control_spec`）；`ic_analysis_service`（`sample_design='unconditional_random'` 揭露；比較觸發批 vs 隨機批時缺任一 prevalence ⇒ `unavailable:random_control_prevalence_missing`）；`eventDimensions.ts` 鏡像同步（`accepted` 增值）；`/search` 或 `/ic-analysis` 提供「產生隨機對照批」入口（依附既有觸發批）。
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
- **既有 4 批 `scenario=B`（2026-09-01 UAT 夾具，`rule_id=uat`）無 `label_origin`** — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往（舊資料不合新規預設封存非遷移）`；處置：可繼續分析（讀路徑 `label_origin=null`）、**重匯入必拒** `conditional_required_missing`（loud）；觸發：使用者要求遷移；登記處：GAP-3 殘留（R1 GROK-R1-P2-01）。
- **`_receipt_hash` 現行碼形狀與原檔 §D-3′-a（iii）code fence 既有分叉**（`batch`／`event_level`／`per_tf` vs `event_import_id`／`direction_sign`／`normalized_spec_bytes`／`windows`／`per_tf`）— `為何現在不做: blocked-by:原檔（iii）為 FROZEN 字面，改寫其 fence 屬原檔本體修訂；本檔以 D4.1 code fence 覆寫為唯一權威、不回改原檔`；觸發：原檔下次 R；登記處：GAP-3 殘留（R1 GROK-R1-P1-03）。
- **`B ∧ event_known_at_decision=true ⇒ fail-closed`（consult 群 4）** — `為何現在不做: blocked-by:G3-R13（D2-2 單一表示法下 event_known_at_decision 恆 False，該斷言為真空約束、無可證偽實例；待使用者裁定 C 之收盤後決策語意並重開 D2-2 後才有非真空實例）`；觸發：`G3-R13` 裁定「要」；登記處：GAP-3 殘留（R1 GROK 5a；R1 STAMP CODEX-R1-P2-01）。
- **可行域內未被凍結 golden／固定網格覆蓋之 `(k,h)` 無 exact 凍結值** — `為何現在不做: needs-research:無限（可行域）輸入域無法逐點凍結；現以獨立 raw-bar 期望表 oracle＋seeded 隨機抽樣 property 層保證同型正確，未見更強之可行方法`；觸發：委員會給出可行之逐點 oracle；登記處：GAP-3 殘留（R2 CODEX-R2-P1-01）。
- **codex 異議：契約 `decision_offset_bars` 改 optional（legacy-only）** — `為何現在不做: user-ruling:2026-09-03 委員共識採較嚴（保留必填 default 0；§C0 禁放寬 fail-closed）`；觸發：使用者裁定「欄位須消失」；登記處：GAP-3 殘留。

## 戳記
（戳記本體落在終輪收斂檔 `handoffs/reconcile/20260903-gap3d2-x-review-r4/synth.md`（本機，gitignore）之 `## 戳記`；此處為鏡像。body sha256 `7dbcbd0c954fc4c815a7fe2a319607d970c4f6d70ec14efd39b2677b7ae562bf`。）

RECONCILE-STAMP: grok APPROVED 2026-09-03 sha256:7dbcbd0c954fc4c815a7fe2a319607d970c4f6d70ec14efd39b2677b7ae562bf task:20260903-GAP3D2-X-STAMP-R1
RECONCILE-STAMP: codex BLOCKED 2026-09-03 sha256:7dbcbd0c954fc4c815a7fe2a319607d970c4f6d70ec14efd39b2677b7ae562bf task:20260903-GAP3D2-X-STAMP-R1
RECONCILE-STAMP: codex APPROVED 2026-09-03 sha256:7dbcbd0c954fc4c815a7fe2a319607d970c4f6d70ec14efd39b2677b7ae562bf task:20260903-GAP3D2-X-STAMP-R2
（composer：R2／R3／R4／STAMP-R1／STAMP-R2 連六次 CLI 失敗（`read ETIMEDOUT`／`read ECONNRESET`／`Cannot use this model: composer-2.5`），戳記**待補**——`DEGRADE-COMPOSER-01..04`；codex 與 grok 已代對讀 composer R1 四條皆 CLOSED。三家戳記齊全前，本檔狀態＝**兩家 APPROVED、一家待補**，不得宣稱 FROZEN。）
