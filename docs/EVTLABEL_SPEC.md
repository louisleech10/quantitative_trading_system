# EVTLABEL — 事件型 label 三缺陷修補＋匯入標籤模式 — SPEC

> 來源 PLAN/診斷：`HANDOFF.md` 🔴 EVTLABEL 段（2026-09-09 晚使用者裁定）｜日期：2026-09-10｜對應 TODO：`docs/EVTLABEL_TODO.md`
> 票：`EVTLABEL`　起草：Claude（主委）　審查：Codex＋Composer＋Grok 三家 adversarial（`scripts/governance_roles.json`）

**使用者主目標（逐字，不得改寫；任何審查裁定把本目標延後＝否決點，主委須以 AskUserQuestion 阻塞彈窗，不得自行接受）**：
> 「我在外面標好正反例（標的＋t₀＋0/1 標籤）匯入，平台找出 t₀ 之前哪些特徵能把正反例分開，再把這些特徵餵 ML。」

**使用者裁定之三 Phase（順序不可調，2026-09-09）**：
P1（小）①報告＋隔離區揭露實際 label 規則（h／k／進場價／報酬算法；明寫 h/k 單位＝事件週期根數）＋③IC 頁事件 h/k 輸入旁標單位
→ P2（中）②切分 purge 依 label 視窗換算到特徵週期
→ P3（大）④「匯入標籤模式」：IC 直接對 0/1 標籤算（AUC／rank-biserial；Mann-Whitney＋置換；FDR 照舊），報酬版 IC 留第二欄，倖存者帶 `sample_scope=event`＋標籤來源
→ 全部做完（三 Phase 各自 code review 收斂）才重驗 B26–B34＋新增項目。

---

## §RISK 風險分級

- **大小**：大。
- **命中高風險原則**：(a) 數值/資料品質——P2 動切分 purge 語意、P3 新增統計量進 gatekeeper 主線；(b) 跨模組共用路徑——`api/services/ic_analysis_service.py`（staging）＋`momentum/Analysis/ic_filter_orchestrator.py`（split／stage3／stage5／thresholds）＋`momentum/core/contracts.py`（label_kind 映射）＋survivor contract；(c) 三 Phase、P3 改 survivor 契約難回退；(d) ML 路徑——倖存者檔是 ML 的輸入。
- RISK-HIT: a,b,c,d
- §G Golden 必填；三家 adversarial 必跑（`--adversarial`）；實作者（Claude）不自審。

---

## §A 假設與待使用者確認

### 已驗證事實（附 receipt）

- `FACT-RECEIPT: awk -F, 'NR>1{print $20}' ~/Downloads/events_2026-09-09.csv | sort | uniq -c` → 印出 `29 0` / `136 1`（Claude 實跑 2026-09-10）。CSV `label` 欄＝0/1 正反標籤，兩類皆存在。
- `FACT-RECEIPT: jq '.metadata.event_filter | {label_source, statistic_kind, sample_scope_kind, consumed_event_count}' data_cache/reports/ic_report_ic_gatekeeper.json` → 印出 `event_label_value` / `conditional_ic` / `event` / `165`（Claude 實跑 2026-09-10）。IC 消費的是**規則重算之報酬**；`consumed_event_labels["ETHUSDT:12h:1735776000000"] = -0.004468224…`，與 CSV 同列 `future_1bar_return = -0.004468221…` 相等（float32 精度）⇒ **實際 h=1、單位＝事件週期 12h 一根**；CSV `label` 0/1 未被任何統計消費。
- `FACT-RECEIPT: jq '.metadata.ic_train_test_split' data_cache/reports/ic_report_ic_gatekeeper.json` → 印出 `effective_horizon=5, purge_gap=5, embargo=144, expected_freq="0 days 01:00:00", index_kind="positional"`（Claude 實跑 2026-09-10）。purge 5＝**特徵週期 1h 之根數**，來自主線 `default_horizon`；embargo 144＝事件端 `purge_rows`（`max(lookahead_depth_ms, label_window_ms)/1h`）抬高之值。
- `FACT-RECEIPT: jq '{import_id, n:(.records|length), labels:([.records[].label]|map(tostring)|group_by(.)|map({(.[0]):length})|add), tf:([.records[].timeframe]|unique), h:([.records[].label_definition.window.horizon_bars]|unique), mode:([.records[].label_definition.label_return_mode]|unique), entry:([.records[].entry_price_semantic]|unique), k:([.records[].decision_offset_bars]|unique)}' data_cache/events/20260909T130533Z-7f73e4c7.json` → 印出 `n=165, labels={"0":29,"1":136}, tf=["12h"], h=[12], mode=["close_to_close"], entry=["trigger_close"], k=[0]`（Claude 實跑 2026-09-10）。**0/1 標籤在匯入層已被解析並持久化**（`api/services/case_import_service.py:1485-1500` `EventLabelRow(label=int(r["label"]))`），只是 IC 路徑未讀。
- `FACT-RECEIPT: sed -n 700,740p momentum/Analysis/event_samples/label_value_from_case.py` → `purge_lower_bound_ms = max(lookahead_depth_ms, label_window_ms)` 逐 symbol 取 max；`api/services/ic_analysis_service.py:752` `purge_rows = ceil(purge_ms / feature_bar_ms)`；`:1296-1302` 與 `:1578-1585` 注入為 `config_override["embargo"] = max(config.embargo, purge_rows)`（Claude 讀碼 2026-09-10）。⇒ **現況不洩漏**（purge＋embargo ≥ label 視窗恆成立），但 label 視窗被記在 embargo 而非 purge，purge 欄之數字（5）與事件 label 無關——這是 P2 要修的**語意錯位**，不是洩漏修補。SPEC 不得宣稱「修洩漏」。
- `FACT-RECEIPT: grep -n "_DEFAULT_ANALYSIS_HORIZON_BARS" api/routes/ic_analysis.py` → `:102` 常數 `1`；`:242-289` 依 `lookahead_bars_declared` 深度 seed `("trigger_open","open_to_horizon_close",h=depth)`；使用者未顯式設 ⇒ 分析用 spec 由 route seed，**與 CSV `label_definition` 無關**（Claude 讀碼 2026-09-10）。
- `FACT-RECEIPT: grep -rn "single_feature_binary_baseline" momentum api | grep -v "def \|raise"` → 除測試外**無 caller**（Claude 實跑 2026-09-10）。GAP-3 Task B1.4 之 per-feature AUC＋permutation oracle＋BH（`momentum/Analysis/event_samples/baseline.py`）已存在但未接線；`pipeline.py:523` 辨別表恆為 `not_computed:no_model_scores_in_event_pipeline`。P3 **重用** `permutation_oracle`／`_bh_fdr` 之語意，不重寫 oracle。
- `FACT-RECEIPT: sed -n 4379-4400p momentum/Analysis/ic_filter_orchestrator.py` → `_apply_thresholds` 之 `ic_mean_min` 閘讀 `row["ic_mean"]`、p 閘讀 `p_value_adj`（FDR on）；事件路徑 `icir_gate=False`（Claude 讀碼 2026-09-10）。
- `FACT-RECEIPT: grep -n "isolation" frontend/src/lib/icIsolation.ts frontend/src/components/ic-analysis/IsolationNote.tsx | head -3` → 隔離區只讀 `metadata.isolation`／`metadata.ic_window_disclosure`，`label_source`／`statistic_kind` 前端**零引用**（Explore 代理 2026-09-10）。

### 假設（assumed；附否證觀測）

- `ASSUME-1`（**已實跑成立**）：`prepared1.normalized_spec_bytes` 之 JSON 即分析層實際套用的 spec（`_analysis_copy` 覆寫匯入檔 `label_definition`，`label_value_from_case.py:615-637`）。
  `FACT-RECEIPT: PYTHONPATH=. venv/bin/python handoffs/20260910-probe-label-rule.py` → rc=0；印出 `[h1_c2c] window_ms=43200000 label_window_feature_bars=12 depth_ms=518400000 lookahead_depth_rows=144 purge_lower_bound=518400000 mismatch=0` 與 `[h12_seed] window_ms=561600000 label_window_feature_bars=156 lookahead_depth_rows=144 purge_lower_bound=561600000 mismatch=0`（Claude 實跑 2026-09-10）。
  ⇒ 視窗公式依 mode：`close_to_close: h×bar`；`open_to_horizon_close: (h+1)×bar`（t₀ open→t₀+h close）；`open_to_close: 1×bar`。受理 run（h=1 c2c）label 視窗＝12 根 < 深度 144 根 ⇒ 現行 `purge_rows=144` 由**深度**決定；route seed 情境（h=12 o2hc）視窗 156 > 144 ⇒ 由**視窗**決定。P2 之 G-2/G-3 期望值以此為準（G-3：purge 12／embargo 144）。
- `ASSUME-2`：對 39,373 欄 × ≤165 列，`scipy.stats.mannwhitneyu(axis=0)` 向量化單次 ≤ 10 秒。否證觀測＝實測 > 60 秒。**先跑**：P3 Task 3.5 驗證項③附 benchmark receipt。
- `ASSUME-3`：`validate_event_given` 對 0/1 整數 label（以 float 傳入）之逐值相等檢查可直接重用（`momentum/core/contracts.py:1063-1107`）。否證觀測＝binary 值進 `validate_consumed_label` 拋 `AlignmentViolationError` 或非有限值閘誤擋。

### 待使用者確認

`待確認：無`（使用者 2026-09-10 明示「稽核後直接開票，不要再問我方向」；技術取捨走三家 adversarial 共識）。

### 已確認結果

- `2026-09-09 使用者 裁定三 Phase 順序、票名 EVTLABEL、做完才重驗 B26–B34`（HANDOFF 🔴 EVTLABEL 段）。
- `2026-09-10 使用者 主目標原話入 §A；延後主目標＝否決點彈窗；每批 commit 後 push、更新 白話說明/現在做到哪.md`。
- **主委判斷（非使用者逐字）**：主目標之「再把這些特徵餵 ML」＝本票交付**倖存者檔**（`survivor_output`，`sample_scope.kind=event`＋標籤來源）作為 ML 輸入；ML 訓練殼本身依成熟度地圖為不完整層、**不在本票**。此判斷須在白話簡述頭條向使用者揭露（見 §N 殘留 R-4）。

---

## §C 約束

- 解耦 7 條：`momentum/` 不 import `api/`（P3 新統計模組放 `momentum/Analysis/`，service 只呼叫）；service 不互 import；config 單一來源（`momentum/Analysis/ic_config_schema.py`）；`pytest tests/momentum/` 獨立可跑。
- 不弱化 NaN/inf 閘；不擅改輸出大小（summary_table **新增**欄，不刪既有欄；全域模式報告逐位元組不變）。
- 本任務共用路徑：`_stage_event_batch`／`_run_event_label_stages`（service）→ `analyze(... event_timestamps, event_label_values, event_label_owners, event_context)` kwargs → orchestrator stage0/2 split、stage3 `_stage3_event_filter`、stage5 summary＋`_apply_thresholds`、`build_survivor_output`／`validate_survivor_output`。**掃描立方體（SCANCUBE）路徑 `:1296` 與主路徑 `:1578` 兩個 embargo 注入點必須同改**（EVTALIGN 已踩過「只接一個呼叫點」）。
- 既有 caller 不得破：`_assert_event_triple_bound`（service）回比 `consumed_event_labels`；P3 之 binary 三元組另開鍵 `consumed_event_binary_labels`，**不覆寫**既有鍵。
- **新資料結構一律 JSON 當單一真相源**：P3 之 label_mode／label_source／statistic_kind／summary 新欄／unavailable reason 枚舉集中於 `momentum/Analysis/contracts/event_label_mode.json`（Task 3.1）；本 SPEC 只 pointer，散文不再列舉第二次。
- 白話文件（`白話說明/`）與本 SPEC 分層，本檔不寫白話。

---

## §G Golden / Baseline

- **feature/kline 條件**：P2 涉切分、P3 涉 label／統計 ⇒ 真實 kline `data_cache/feature_klines/kline_cache.h5`；禁合成價格 fixture。統計 oracle（置亂／植入）可用合成 **label 序列**（`docs/TEST_DESIGN_CHARTER.md` §F）。
- **G-1 全域模式逐位元組不變（P1／P2／P3 各自）**：`pytest tests/momentum/Analysis/test_gap2_golden.py -q` rc=0（整份報告 canonical sha）；三 Phase 之新鍵**只在事件路徑寫**（沿 `_inject_isolation_source` 之落點與理由）。
- **G-2 事件切分 golden（P2）**：動工前 `venv/bin/python handoffs/20260907-probe-split-baseline.py --check` 對證 `tests/golden/evtalign/split_baseline.json` sha256 `e378c706…ba7201` 為 True（凍結即現況）。改後同一探針以 `--diff` 輸出逐組 `{purge_gap, embargo, test_rows_start, split_row_fingerprint}` 差異；**通過條件（可證偽）**：(i) 非事件組（`horizon_source≠event`）四欄逐值相同；(ii) 事件組 `purge_gap_after == max(effective_horizon, label_window_rows)`、`embargo_after == max(config.embargo, lookahead_depth_rows)`、`test_rows_start_after − test_rows_start_before == (purge_after+embargo_after) − (purge_before+embargo_before)`；(iii) 任一組 `purge_after + embargo_after < max(label_window_rows, lookahead_depth_rows)` ⇒ FAIL。改後以 `--write` 重凍結並記新 sha 於 TODO。
- **G-3 受理事件 run 重現（P2）**：以 `data_cache/events/20260909T130533Z-7f73e4c7.json`（165 事件）配同一 1h feature run 重跑；期望 `ic_train_test_split = {purge_gap: 12, purge_gap_source: "event_label_window", embargo: 144, embargo_source: "event_lookahead_depth"}`（改前 5/144）。若 feature run 已不存在 ⇒ 以探針 G-2 之事件組替代並在 TODO 具名。
- **G-4 事件 return_rule 模式報告不變（P3）**：P3 完工後以 `label_mode=return_rule` 重跑 G-3 之 run，刪除 `metadata.event_label_rule`／`metadata.label_mode` 兩新鍵後 canonical sha 與 P2 完工時相同。
- **G-5 統計 oracle（P3）**：見 §V mutation；植入 label 之 AUC 期望值精確（`==1.0`）、鏡像 label 之 rank-biserial 精確取負（`abs≤1e-12`）。

---

## §P Phase 與依賴

### Phase 1 — 揭露實際 label 規則＋UI 單位（依賴：無）

**Task 1.1 — `metadata.event_label_rule` 揭露（後端）**
- 目標：事件 run 之報告寫入本次**實際消費**的 label 規則與單位換算。
- 檔案：`api/services/ic_analysis_service.py` 新增 `_inject_label_rule_disclosure(staged, report)`，掛在 `_inject_isolation_source` 同一呼叫序（主路徑與掃描格路徑皆掛）。
- 既有 caller/影響面：新建；只在事件路徑（有 `staged`）寫鍵；非事件 run 不寫 ⇒ G-1 不變。
- 改法：由 `staged["prepared"].normalized_spec_bytes` 解析 spec（**不讀 request**，request 可能是 route seed 前的值）；由 `staged["prepared"].windows` 取 `max(label_end_ms − label_start_ms)`；由 `report.metadata.timeframe`（特徵週期）與 windows 之 `timeframe`（事件週期）算 `feature_bars_per_event_bar = event_bar_s / feature_bar_s`（非整數 ⇒ 寫 `null` 並 `ratio_integral=false`）。鍵集（closed；列於 `event_label_mode.json` 之 `event_label_rule_keys`，P3 Task 3.1 建檔前先以本 Task 建檔）：`label_source`（抄 `event_filter.label_source`）、`statistic_kind`（抄 `event_filter.statistic_kind`）、`horizon_bars`、`decision_offset_bars`、`entry_price_semantic`、`label_return_mode`、`h_unit="event_timeframe_bars"`、`event_timeframe`、`feature_timeframe`、`feature_bars_per_event_bar`、`label_window_feature_bars`（ceil(window_ms/feature_bar_ms)）、`return_formula`（由 `label_return_mode`＋`entry_price_semantic` 機械組字串，如 `close[t0+h]/close[t0]-1 × direction_sign`）、`imported_binary_label={present, n_pos, n_neg, used}`（P1 時 `used=false`；P3 改由 label_mode 決定）、`n_events_consumed`。
- **驗證**：① `PYTHONPATH=. venv/bin/python handoffs/20260910-probe-label-rule.py` rc=0：對 165 事件批逐事件斷言 `label_end_ms − label_start_ms` == 依 mode 之公式（§A ASSUME-1），並印出 `[h1_c2c] label_window_feature_bars=12`（已實跑；Task 1.1 之 `label_window_feature_bars` 一律由 `label_end_ms − label_start_ms` 取，不由 h 重算）。② `pytest tests/api/test_evtlabel_disclosure.py -q` rc=0：事件 run 之 `metadata.event_label_rule` 鍵集 == JSON 契約鍵集（`set` 相等）、`imported_binary_label == {present: true, n_pos: 136, n_neg: 29, used: false}`；非事件 run 無此鍵。
- **邊界**：①批內事件週期不一（mixed tf）⇒ `event_timeframe="mixed"`、`feature_bars_per_event_bar=null`、`label_window_feature_bars` 取 max；②`records` 全無 `label` 欄（legacy schema）⇒ `imported_binary_label={present:false, n_pos:0, n_neg:0, used:false}`；③切分未套用 ⇒ 仍寫本鍵（與 isolation 不同：label 規則與切分無關）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：P3 Task 3.4 會**更新** `imported_binary_label.used` 與 `statistic_kind` 值，鍵集不變；無刪除。
- 不可做：不在 orchestrator 內寫（保 G-1）；不重算 label；不從 request 讀 spec。

**Task 1.2 — 隔離區「label 規則」揭露（前端）**
- 目標：`IsolationNote` 下方新增「本次 label 怎麼算」區塊。
- 檔案：`frontend/src/lib/icLabelRule.ts`（新，讀 `metadata.event_label_rule` → 行陣列）、`frontend/src/components/ic-analysis/IsolationNote.tsx`（多渲染一段，`data-testid="label-rule-note"`）、`frontend/src/lib/types.ts`（`ICEventLabelRule` 介面）。
- 既有 caller/影響面：`page.tsx:709` 既有掛點；無鍵 ⇒ 不渲染。
- 改法：固定行：`h=<horizon_bars> 根（單位＝事件週期 <event_timeframe> 的根數＝<feature_timeframe> 特徵的第 <label_window_feature_bars> 根）`、`k=<decision_offset_bars> 根（同單位）`、`進場價＝<entry_price_semantic>；報酬＝<return_formula>`、`你匯入的 0/1 標籤：<有(正 n_pos／反 n_neg)|無>；本次<已用|未用>（IC 對的是 <規則重算的報酬|你的 0/1 標籤>）`。文案字面由 `icLabelRule.ts` 單點產生。
- **驗證**：`cd frontend && npx vitest run src/lib/icLabelRule.test.ts src/components/ic-analysis/IsolationNote.test.tsx` rc=0：(i) 有鍵 ⇒ 四行皆渲染且含 `第 12 根`；(ii) `feature_bars_per_event_bar=null` ⇒ 第一行退化為 `h=1 根（單位＝事件週期根數）`；(iii) 無鍵 ⇒ `label-rule-note` 不存在。
- **邊界**：①`imported_binary_label.present=false` ⇒ 第四行為「無」；②`return_formula` 缺 ⇒ 該行顯示 `報酬算法未揭露（後端缺欄）`，不得空白。
- **存活至**：全票完工後保留。
- **覆蓋風險**：P3 Task 3.9 改第四行為「已用」分支；行數不變。
- 不可做：不在前端重算單位；不從批次 detail 推 h（只信報告）。

**Task 1.3 — IC 頁事件 h/k 輸入旁標單位（前端）**
- 目標：`ic-param-horizon-bars`／`ic-param-decision-offset-bars` 旁顯示單位說明。
- 檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`（`:320-354`、`:469-495` 兩輸入旁加 `data-testid="ic-param-h-unit"`／`"ic-param-k-unit"`）；`frontend/src/lib/icLabelRule.ts::unitCaption(eventTf, featureTf)`。
- 既有 caller/影響面：`page.tsx:714-737` 需多傳 `featureTimeframe`（自 `config.timeframe`）；批次事件週期取 `detail.summary.timeframes`（單一值才算）。
- 改法：文案 `單位：事件週期（<eventTf>）的根數；1 根＝<featureTf> 特徵的 <ratio> 根`；ratio 非整數或任一 tf 缺 ⇒ `單位：事件週期的根數`。
- **驗證**：`cd frontend && npx vitest run src/components/ic-analysis/icEventBatchDisclosure.test.tsx -t unit` rc=0：12h 事件×1h 特徵 ⇒ 含 `12 根`；4h 事件×1h ⇒ `4 根`；1h×4h ⇒ 退化文案。
- **邊界**：①mixed tf 批 ⇒ 退化文案；②feature run 未選 ⇒ 退化文案。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 h 預設值、不改 seed 邏輯（`IC_ANALYSIS_INITIAL_HORIZON_BARS` 一字不動）。

### Phase 2 — purge 依 label 視窗換算到特徵週期（依賴：Task 1.1 之 `label_window_feature_bars` 計算式）

**Task 2.1 — 隔離兩項分離計算（service）**
- 目標：把「label 視窗」與「批次 look-ahead 深度」拆成兩個列數，分別餵 purge 與 embargo。
- 檔案：`momentum/Analysis/event_samples/label_value_from_case.py` 新增純函式 `isolation_terms_rows(windows, *, lookahead_bars_declared, timeframe_seconds, feature_timeframe) -> IsolationTerms(label_window_rows:int, lookahead_depth_rows:int)`（ceil 除法；**不動** `purge_lower_bound_rows`／`project_purge`——它們是事件切分 `split_events` 的消費者）；`api/services/ic_analysis_service.py::_stage_event_batch` 回傳新增 `label_window_rows`、`lookahead_depth_rows`（保留 `purge_rows` 供對照）。
- 既有 caller/影響面：`_run_event_label_stages` 兩個 embargo 注入點 `:1296-1302`（掃描格）與 `:1578-1585`（主路徑）。
- 改法：兩注入點改為 `cell_override["embargo"] = max(config.embargo, lookahead_depth_rows)`、`cell_override["event_purge_rows"] = label_window_rows`；`staged["embargo_before_event"]` 語意不變。
- **驗證**：`pytest tests/momentum/event_samples/test_isolation_terms.py -q` rc=0：12h×h=1 事件於 1h 特徵 ⇒ `label_window_rows==12`；`lookahead_bars_declared={"12h":12}` ⇒ `lookahead_depth_rows==144`；`open_to_close` ⇒ `label_window_rows==12`（一根事件週期）；4h×h=3 於 1h ⇒ 12。不變式測試：對 G-2 九組，`max(label_window_rows, lookahead_depth_rows) == purge_rows(舊)`。
- **邊界**：①`lookahead_bars_declared[tf]==0` ⇒ `lookahead_depth_rows==0`（embargo 回 config）；②windows 空 ⇒ 兩值 0 且不 raise（由既有 `ts_map` 空檢查 loud）；③feature_bar_s > event_bar_s（細事件配粗特徵）⇒ ceil 給 1，不給 0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `purge_lower_bound_rows` 公式；不動事件切分 `split_events`。

**Task 2.2 — split 之 purge 吃事件 label 視窗（orchestrator）**
- 目標：`purge_gap = max(effective_horizon, event_purge_rows)`；embargo 只承載 config／look-ahead 深度。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`：`analyze(...)` 與 `_run_full_sample_fallback` 透傳新 kwarg `event_purge_rows: Optional[int]`（或由 `config_override["event_purge_rows"]` 讀；擇一、在 TODO 定死）；`:1102-1160` 呼叫 `_build_holdout_split_plan(purge_gap=max(effective_horizon, event_purge_rows or 0))`；`metadata["ic_train_test_split"]` 新增 `purge_gap_source ∈ {mainline_horizon, event_label_window}`、`event_label_window_rows`、`embargo_source ∈ {config_embargo, event_lookahead_depth}`、`lookahead_depth_rows`。
- 既有 caller/影響面：`_build_holdout_split_plan` 之 `purge_gap < effective_horizon ⇒ raise` 守衛保留（max 後恆成立）；`SplitPlan.purge_gap < len(row_index)` 不變式保留；跨截面路徑不動。
- 改法：只改 purge 之取值與 metadata 四鍵；`split_context["effective_horizon"]` **不改**（HAC lag 議題見 §N R-1）。
- **驗證**：G-2 探針 `--diff` 三條通過條件；G-3 重現 `purge_gap=12, embargo=144`；`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/core/test_split_contract.py tests/golden/ic_phase1_contract -q` rc=0（全域路徑不變）；`ASSERT venv/bin/python handoffs/20260907-probe-split-baseline.py --check WHEN group=global THEN rc=0`。
- **邊界**：①`event_purge_rows > n_rows − split_point − embargo` ⇒ 既有 `SkippedResult(INSUFFICIENT_DATA)` 路徑（loud、走 fallback）；②`event_purge_rows=None`（非事件）⇒ 行為逐位元組同改前；③`event_purge_rows < effective_horizon` ⇒ `purge_gap_source="mainline_horizon"`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `_resolve_effective_label_horizon`；不改 embargo 語意為「含 label 視窗」（那是改前錯位）；不在 orchestrator 換算 ms（列數由 service 給）。

**Task 2.3 — 隔離區揭露改讀新來源（service＋前端）**
- 目標：`metadata.isolation.purge.source` 反映真實來源。
- 檔案：`api/services/ic_analysis_service.py::_inject_isolation_source`（`purge.source` 抄 `ic_train_test_split.purge_gap_source`，`purge.note` 改為機械組字串；`embargo.source` 抄 `embargo_source`）；`frontend/src/lib/icIsolation.ts` `SOURCE_TEXT` 新增 `event_label_window`／`event_lookahead_depth` 兩鍵（保留舊鍵供舊報告）。
- 既有 caller/影響面：`tests/api/test_isolation_disclosure.py`、`frontend/src/lib/icIsolation.test.ts` 之既有斷言須**改成新語意**（diff 列於 TODO，禁只放寬）。
- 改法：如上。
- **驗證**：`pytest tests/api/test_isolation_disclosure.py -q` rc=0（新斷言：G-3 情境 `purge.source=="event_label_window"`、`embargo.source=="event_lookahead_depth"`、`total_bars==156`）；`cd frontend && npx vitest run src/lib/icIsolation.test.ts` rc=0。
- **邊界**：①舊報告（無 `purge_gap_source`）⇒ `purge.source="global_default_horizon"`（相容）；②切分未套用 ⇒ 不寫鍵（不變）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不重算列數（只抄 orchestrator 寫的值）。

### Phase 3 — 匯入標籤模式（依賴：Task 1.1 之 `imported_binary_label`、Task 2.2 之切分）

**Task 3.1 — 枚舉單一真相源＋契約**
- 目標：label_mode／label_source／statistic_kind／summary 新欄／unavailable reason／最小每類事件數 全部一檔定義。
- 檔案：新建 `momentum/Analysis/contracts/event_label_mode.json`（含 `event_label_rule_keys`——P1 先建此檔之該鍵）；`momentum/core/contracts.py:1030` `LABEL_KIND_BY_SOURCE` 新增 `imported_binary_label → event_given`（由 JSON 載入或以測試對證 JSON，二擇一在 TODO 定死）；`momentum/Analysis/contracts/ic_survivor_contract.json` `sample_scope.event.label_source` `_doc` 補 `imported_binary_label`、新增 `label_binary` 子物件鍵（`import_id`／`n_pos`／`n_neg`／`label_origin_values`；nullable，非 binary 模式為 null）；`momentum/Analysis/ic_config_schema.py::EventFilterConfig` 新增 `min_events_per_class:int=10`。
- 既有 caller/影響面：`validate_survivor_output`（六鍵＋`label_source` 檢查）；`derive_label_kind` 之 `known=` 錯誤訊息。
- 改法：JSON 為 SoT；Python 端以 `json.load` 或常數＋`test_contract_enums_match_json` 對證。
- **驗證**：`pytest tests/momentum/Analysis/test_event_label_mode_contract.py -q` rc=0：Python 枚舉集合 == JSON 集合；`derive_label_kind("imported_binary_label")=="event_given"`；`validate_survivor_output` 對 `label_source="imported_binary_label"` 且六鍵非 null ⇒ 通過、六鍵有 null ⇒ raise。
- **邊界**：①JSON 缺鍵 ⇒ import 期 raise（fail-closed）；②未知 label_source ⇒ 既有 raise 不變。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不在 SPEC／散文列舉枚舉值第二次；不動 `sample_scope_kind_values`。

**Task 3.2 — 請求／路由：`event_label_mode`**
- 目標：`ICAnalyzeRequest.event_label_mode: Literal["auto","return_rule","imported_binary"] = "auto"`。
- 檔案：`api/models/ic_models.py:166-256`（欄位＋不變式：`event_label_mode≠auto` 且無 `event_import_id` ⇒ 400）；`api/routes/ic_analysis.py:278-289` 透傳；`frontend/src/lib/types.ts::ICAnalysisConfig`、`frontend/src/hooks/useICAnalysis.ts:647-663`（只在 event＋import 分支送）。
- 既有 caller/影響面：`tests/api/test_ic_analysis_api.py`、`icEventAnalysisRequest.test.ts`。
- 改法：`auto` 之解析在 service（Task 3.3）；route 不解析。
- **驗證**：`pytest tests/api/test_ic_analysis_api.py -q -k label_mode` rc=0（缺 import_id 帶 `imported_binary` ⇒ 400；預設 `auto`）；`cd frontend && npx vitest run src/hooks/icEventAnalysisRequest.test.ts` rc=0（legacy `event_timestamps` 分支**不送**此欄）。
- **邊界**：①`event_timestamps` 路徑帶此欄 ⇒ 400；②大小寫錯 ⇒ 422（Pydantic）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不新增第四種模式；不把 `auto` 解析放路由。

**Task 3.3 — staging：binary label 向量與 `auto` 解析（service）**
- 目標：與 `ts_map` 同一迴圈、同一鍵（feature_cutoff_ms）產出 `event_binary_labels: {ms: 0|1}`、`event_binary_label_by_id`，並決定 `label_mode_effective`。
- 檔案：`api/services/ic_analysis_service.py:700-772`；`_run_event_label_stages` 兩路徑透傳 kwargs `event_binary_labels`、`label_mode`。
- 既有 caller/影響面：`_assert_event_triple_bound` 新增 binary 分支（回比 `consumed_event_binary_labels`）；掃描格路徑同樣透傳（掃描格只做 return_rule？**不**——掃描格 h/k 對 binary 統計無意義：binary 模式下掃描格請求 ⇒ 400 `scan_not_applicable_in_imported_binary_mode`，理由：0/1 標籤不隨 h/k 變）。
- 改法：`auto` ⇒ 若 records 之 `label` 欄存在且（symbol 過濾＋coverage 後）兩類各 ≥ `min_events_per_class` ⇒ `imported_binary`，否則 `return_rule`＋`label_mode_reason ∈ {no_label_column, one_class, class_below_min}`（枚舉入 JSON）；顯式 `imported_binary` 但條件不足 ⇒ raise（loud，422）。`staged["label_mode_effective"]`、`staged["label_mode_reason"]` 寫入 `metadata.label_mode`（含 `requested`／`effective`／`reason`／`n_pos`／`n_neg`）。
- **驗證**：`pytest tests/api/test_evtlabel_staging.py -q` rc=0：165 批 ⇒ `effective=="imported_binary"`、`n_pos==136`、`n_neg==29`、`len(event_binary_labels)==len(event_label_values)` 且鍵集相等；全 1 批 ⇒ `return_rule`／`one_class`；`ASSERT venv/bin/python -m pytest tests/api/test_evtlabel_staging.py -q -k explicit_binary_one_class WHEN label_mode=imported_binary THEN rc=0`（測試斷言 raise）。
- **邊界**：①事件有 `label_value` 但無 `label`（legacy）⇒ `return_rule`；②`label` 缺值混雜 ⇒ `imported_binary` 下 raise（禁靜默丟）；③symbol 過濾後單類 ⇒ `one_class`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `ts_map` 鍵；不在此算統計。

**Task 3.4 — stage3：binary label 綁定與驗證（orchestrator）**
- 目標：`_stage3_event_filter` 在 `imported_binary` 下同時保留報酬 label（第二欄）與 0/1 label（主統計），兩者皆過 `validate_event_given`。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py:3348-3480`；`self._ic_cache["event_binary_label"]`（pd.Series，index=filtered_features.index）。
- 既有 caller/影響面：`event_info` 新增 `consumed_event_binary_labels`、`label_source` 改 `imported_binary_label`、`statistic_kind="binary_discrimination"`、`secondary_statistic="conditional_ic"`；`return_rule` 模式下 `event_info` **逐鍵不變**（G-4）。
- 改法：binary 向量以 `validate_consumed_label(label_kind=event_given, expected_values=binary, event_owners=owners)` 驗證（ASSUME-3）；報酬 label 仍走既有驗證。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q` rc=0：錯位一格之 binary 向量 ⇒ `AlignmentViolationError`；`return_rule` 下 `event_info` 鍵集 == 改前鍵集；`imported_binary` 下 `consumed_event_binary_labels` 值集 ⊆ {0.0, 1.0}。
- **邊界**：①事件不足 fallback（`conditional_ic_abandoned`）⇒ binary 亦放棄，`statistic_kind="binary_discrimination_unavailable"`、`label_source="mainline_return_N"`；②binary 向量含 NaN ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不覆寫 `consumed_event_labels`（報酬三元組鍵）。

**Task 3.5 — 純統計模組：Mann-Whitney／AUC／rank-biserial（向量化）**
- 目標：對 `features (n×p)` 與 `y∈{0,1}^n` 逐欄算 AUC、rank-biserial、U、雙尾 p；NaN 逐欄 pairwise 去列並記 `n_used`。
- 檔案：新建 `momentum/Analysis/binary_discrimination.py::mann_whitney_table(features: pd.DataFrame, y: np.ndarray, *, min_class_n: int) -> pd.DataFrame`（欄：`auc, rank_biserial, mw_u, p_value, n_pos, n_neg, n_used, status`；`status ∈ {ok, unavailable:<reason>}` 枚舉入 JSON）。
- 既有 caller/影響面：新建；Task 3.6 唯一 caller。
- 改法：`scipy.stats.mannwhitneyu(x_pos, x_neg, alternative="two-sided", method="auto", axis=0)`（ties/continuity 由 scipy 處理；小樣本無 ties 走 exact）；`auc = U_pos / (n_pos·n_neg)`；`rank_biserial = 2·auc − 1`；NaN 欄以 mask 分組後逐欄呼叫（NaN 欄數少時），無 NaN 之欄一次向量化。
- **驗證**：`pytest tests/momentum/Analysis/test_binary_discrimination.py -q` rc=0：①`y = 1[x > median(x)]` ⇒ `auc==1.0`（exact）；②`y` 鏡像（1−y）⇒ `rank_biserial` 逐欄取負 `abs≤1e-12`；③與逐欄 `scipy.stats.mannwhitneyu` 標量呼叫逐欄相等（`p` `rel≤1e-9`）；④benchmark receipt：39,373 欄 × 165 列（真實 feature run 或同形隨機矩陣）耗時印出，`< 60s`（ASSUME-2）；⑤全 NaN 欄 ⇒ `status=unavailable:all_nan`；⑥常數欄 ⇒ `auc==0.5`、`p==1.0` 或 `status=unavailable:constant`（二擇一在 TODO 定死並測）。
- **邊界**：①某類去 NaN 後 `< min_class_n` ⇒ `unavailable:class_below_min`；②`n_used==0`；③極端 ties（整欄兩值）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不做多特徵組合；不做 bootstrap CI（置換 oracle 見 3.7）；不在 hot loop log。

**Task 3.6 — stage5：binary 統計進 summary_table＋門檻（orchestrator）**
- 目標：`imported_binary` 下 summary_table 每列新增 binary 欄，主統計＝`rank_biserial`，p 走 Mann-Whitney→BH（`apply_fdr`）；報酬版 `ic_mean`／`t_stat`／`p_value` 保留為第二欄（改名**不做**，以 `metadata.event_label_rule.primary_statistic="rank_biserial"`＋`secondary_statistic="ic_mean"` 揭露）。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 事件分支（`:3766-3900`）；`_apply_thresholds(..., primary_field: str = "ic_mean", p_field_override: Optional[str])`。
- 既有 caller/影響面：`_apply_thresholds` 既有呼叫預設值不變（全域逐位元組不變）；summary_table 新增欄 `auc, rank_biserial, mw_u, mw_p_value, mw_p_value_adj, n_pos, n_neg, n_used_binary`（`return_rule`／全域下**不寫**這些欄——G-1／G-4）；排序鍵 binary 模式＝`|rank_biserial|` desc。
- 改法：統計對象＝test split 之事件列（`selection_scope=test`，與條件 IC 同 scope）；`ic_mean_min` 閘改讀 `rank_biserial`（`removed["ic_mean_skipped_binary_mode"]` 記錄報酬版未閘）；p 閘讀 `mw_p_value_adj`；`icir_gate=False` 沿既有；`ic_hit_rate`／`monotonicity` 閘在 binary 模式 N/A（記 `removed["<gate>_skipped_binary_mode"]`）。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q` rc=0：植入特徵（Task 3.5 ①）進 gatekeeper ⇒ 該特徵 `passed`、`mw_p_value_adj < 0.05`；`p_value_max` 改 0.001 ⇒ 弱特徵被 `removed["p_value"]`；`return_rule` 下 summary_table 欄集 == 改前欄集（`set` 相等，G-4）；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q -k threshold_reads_rank_biserial WHEN label_mode=imported_binary THEN rc=0`。
- **邊界**：①test split 事件單類 ⇒ 全表 `unavailable:one_class_test_segment`、倖存者 0、`degraded` loud；②`rolling IC` 空（pooled fallback）與 binary 並存；③特徵全 `unavailable` ⇒ FDR `n_tests=0` 不除零。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不把 `rank_biserial` 寫進 `ic_mean` 欄冒充；不改全域 `_apply_thresholds` 預設路徑一字。

**Task 3.7 — 置換自檢＋負對照（fail-closed）**
- 目標：倖存者逐一以 `permutation_oracle`（`baseline.py`，`OracleConfig(n_perm=1000, seed=config)`）對 AUC 重驗；置換帶內（不顯著）⇒ 移出倖存者 `removed["permutation_oracle_disagree"]`。整批一次 label 置亂（固定 seed）重跑 Task 3.5＋BH ⇒ `n_survivors_shuffled` 寫 `metadata.event_label_rule.negative_control`；`> 0` ⇒ `warnings` 追加 `negative_control_nonzero`（不擋，揭露）。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 binary 分支末；重用 `momentum/Analysis/event_samples/baseline.py::permutation_oracle`（不改它）。
- 既有 caller/影響面：`baseline.py` 之硬檢 (i)(ii) 在常數欄會 raise ⇒ 常數欄已於 3.5 `unavailable`，不進倖存者。
- 改法：只對倖存者跑（成本 ≤ 數百 × 1000 次 AUC）；receipt（seed、`first_permutation_digest`）寫 `metadata.event_label_rule.permutation_receipt`。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_oracle.py -q` rc=0：植入特徵 `in_band==False` 留下；置亂 label 之固定 seed fixture（200 合成特徵×165 真實 kline 列）⇒ `n_survivors_shuffled==0`；mutation：monkeypatch `_permute` 為恆等 ⇒ 硬檢 (ii) raise（沿 `test_mutation_guard.py` M8）。
- **邊界**：①倖存者 0 ⇒ 不跑置換、receipt 寫 `skipped:no_survivors`；②`n_perm` 由 config 讀，`< 200` ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不把置換 p 取代 MW p（置換只作自檢）；不對全表 39k 欄跑置換。

**Task 3.8 — 倖存者輸出帶標籤來源**
- 目標：`survivor_output.sample_scope = {kind: "event", event: {…六鍵, label_source: "imported_binary_label", label_binary: {import_id, n_pos, n_neg, label_origin_values}}}`；`statistic_kind` 進 `sample_scope.event`（Task 3.1 契約）。
- 檔案：`momentum/Analysis/survivor_contract.py::build_survivor_output`（`:411-700`）、`validate_survivor_output`（`:238-310`）；`_write_survivor_output`。
- 既有 caller/影響面：`tests/momentum/Analysis/test_survivor_contract.py`、`test_gap2_survivor_persist.py`（return_rule／全域 payload 逐位元組不變）。
- 改法：由 `event_context`＋`event_info` 導出；`return_rule` 下 `label_binary=null`。
- **驗證**：`pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_gap2_survivor_persist.py -q` rc=0；新測：binary run 之倖存者檔 `sample_scope.event.label_source=="imported_binary_label"`、`label_binary.n_pos==136`；`validate_survivor_output` 對 `label_binary` 缺 `import_id` ⇒ raise。
- **邊界**：①倖存者 0 ⇒ 既有 suppressed stub 路徑、`sample_scope` 仍寫；②掃描格不寫 survivor（既有）。
- **存活至**：全票完工後保留；此檔即「餵 ML」之交接物。
- **覆蓋風險**：無。
- 不可做：不改 `sample_scope_kind_values`；不改倖存者檔路徑規則。

**Task 3.9 — 前端：模式選擇＋表格欄＋揭露**
- 目標：事件參數面板加 `label_mode` 三選（auto／return_rule／imported_binary，`data-testid="ic-param-label-mode"`，顯示批內正反數）；結果頁 summary 表在 binary 模式優先顯示 `AUC／rank-biserial／p(MW)／q／n+／n−`，報酬版 IC 欄後移並標「第二欄」；隔離區第四行改「已用」分支；`DegradedBanner` 顯示 `label_mode.reason`（auto 回退時）。
- 檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`、`ICSummaryTable.tsx`、`IsolationNote.tsx`／`icLabelRule.ts`、`DegradedBanner.tsx`、`lib/types.ts`、`store/icAnalysisStore.ts`。
- 既有 caller/影響面：`ICSummaryTable.paging.test.tsx`（欄動態，分頁不變）；`gap3_event_mode_entry.test.tsx`。
- 改法：欄位存在與否由報告列鍵決定（有 `rank_biserial` 鍵才切 binary 版面），不由 config 推。
- **驗證**：`cd frontend && npx vitest run src/components/ic-analysis` rc=0；新測：binary 報告 ⇒ 表頭第一數值欄為 `rank-biserial`，且含 `第二欄` 字樣；return_rule 報告 ⇒ 表頭與改前 snapshot 相同；`npm run build` rc=0。
- **邊界**：①舊報告（無新鍵）⇒ 版面不變；②`label_mode.reason=one_class` ⇒ banner 顯示原因。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不在前端算統計；不隱藏報酬版欄。

**Task 3.10 — 真實 kline 端到端驗證（三方簽核之 oracle）**
- 目標：以真實 1h feature run（或 `kline_cache.h5` 現算之小特徵集）＋由真實 12h close 以 `close_to_close h=1 ≥ 2%` 規則產生之 0/1 標籤，跑 `imported_binary` 全流程。
- 檔案：`tests/momentum/Analysis/test_evtlabel_e2e_realkline.py`＋探針 `handoffs/20260910-probe-evtlabel-e2e.py`。
- 既有 caller/影響面：無。
- 改法：斷言 (i) 對 `|ic_mean|` 前 20 名特徵，`sign(rank_biserial)==sign(ic_mean)`（label 為報酬之單調閾值函數）；(ii) 同一 run `return_rule` 與 `imported_binary` 之報酬欄 `ic_mean` 逐特徵相等（第二欄＝原 IC）；(iii) PIT：binary label 整體往前錯一事件（用 t₀ 之前一事件的 label）⇒ `AlignmentViolationError`（由 3.4）。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_e2e_realkline.py -q` rc=0；探針印 receipt（事件數、n_pos/n_neg、倖存者數、negative_control）。
- **邊界**：①kline cache 缺 ETHUSDT ⇒ `pytest.skip` 並印明（不得假綠）；②事件 < `min_events` ⇒ 測試自建足量事件。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：禁合成價格；禁用 `data_cache/events/*`（未追蹤、不可攜）當 fixture。

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a/d ⇒ 必附。設計（`docs/TEST_DESIGN_CHARTER.md`）：
  - M-P2-1：把 Task 2.2 之 `max(effective_horizon, event_purge_rows)` 改回 `effective_horizon` ⇒ G-2 條件 (ii) FAIL、G-3 期望 12 變 5 ⇒ 紅。
  - M-P2-2：把 embargo 注入改回 `max(config, purge_rows)` ⇒ `embargo_source` 斷言紅（depth<window 情境）。
  - M-P3-1：Task 3.5 `auc` 改 `1−auc` ⇒ 植入 oracle `auc==1.0` 紅。
  - M-P3-2：Task 3.6 p 閘仍讀報酬 `p_value_adj` ⇒ `threshold_reads_rank_biserial` 斷言紅。
  - M-P3-3：Task 3.4 binary 向量不過 `validate_event_given` ⇒ 錯位測試由紅轉綠 ⇒ 抓到（測試斷言必 raise）。
  - M-P3-4：Task 3.7 `_permute` 恆等 ⇒ 硬檢 (ii) raise。
  - 執行方式：`handoffs/20260910-evtlabel-mutate.py`（沿 `handoffs/20260907-evtalign-mutate.py` 之 rc 判讀：紅只認 rc=1，rc=5 計 UNCOVERED）。
- 測試層級：單元（3.5、2.1）／整合（3.3、3.4、3.6、3.8）／Golden（G-1..G-4）／端到端真實 kline（3.10）／前端 vitest（1.2、1.3、3.9）。全部可 `pytest tests/...` 獨立跑，不需 `run_api.py`。
- **防假綠**：既有斷言改動只允許 Task 2.3 列出的 isolation 語意更新，diff 附 TODO；不得刪測試換綠。**驗收一律讀 pytest 自己的 summary 行，不看 harness exit code。**
- **邊界目錄**：空DF ☑(3.5 ②)／全NaN列 ☑(3.5 ⑤)／Inf ☑(3.4 ②)／std=0 ☑(3.5 ⑥)／重複·亂序 timestamp ☑(3.3 既有 `ts_map` 重複 raise)／API重啟 ☐N/A／並發寫 ☐N/A／OOM降載 ☐N/A（≤165 列）／大尺度浮點 reduction ☑(3.5 ③ 對 scipy 逐欄對照)。
- **性能**：Task 3.5 ④ 與 3.7 之耗時各附 receipt；總增量 < 2 分鐘（現行事件 run preprocessing 11 分鐘為基準）。

---

## §R 回退

- 三 Phase 各獨立 commit，可單獨 revert；P3 內 Task 3.1–3.8 為一 commit 群（契約＋實作同進退），3.9 前端獨立 commit。
- P2 無旗標：舊行為＝改前錯位語意，不提供「回到錯位」開關；回退＝revert commit。
- P3 逃生口＝請求 `event_label_mode=return_rule`（非預設關閉；`auto` 預設在標籤齊備時**開**，依「驗過就別預設關閉」）。
- Golden FAIL（G-1..G-4）⇒ 不 merge。

---

## §N N/A 登記與殘留

**N/A 段**：無（全錨點實填）。

**殘留（本票不做；三值理由；登記處 `docs/IC_QUANT_GAP_REGISTRY.md`「EVTLABEL 殘留」，ROADMAP 只放 pointer）**

- **R-1 事件路徑 HAC lag 仍用主線 `effective_horizon`（5）而非 label 視窗列數（12）** — `為何現在不做: needs-research:事件列非等距，rolling IC 序列在受理 run 為空（pooled fallback），HAC 對事件序列之適用性與正確 lag 未定義；貿然改 lag 只是換一個未證明的數`；觸發：委員會定出事件序列顯著性估計式；登記處：registry。
- **R-2 跨 symbol 合併之 binary 辨別** — `為何現在不做: blocked-by:Pooled/Panel IC 票（registry #4）；本路徑 symbol 過濾同條件 IC`；觸發：#4 開票；登記處：registry #4。
- **R-3 triple-barrier／出場最佳化** — `為何現在不做: user-ruling:2026-08-19 J5（第一版時間出場）`；觸發：使用者提出且回測層成熟；登記處：registry「GAP-3 殘留」#1（不重登）。
- **R-4 ML 訓練殼吃倖存者檔（主目標之「餵 ML」後半）** — `為何現在不做: blocked-by:成熟度地圖（2026-08-17）ML/回測為不完整層，禁改殼；本票交付物＝倖存者檔（sample_scope=event＋標籤來源）作為契約輸入`；觸發：ML 殼契約先行票開啟；登記處：registry。🔴 白話簡述頭條必列此條，由使用者決定是否接受此邊界。
- **R-5 掃描立方體（h/k 掃描）於 binary 模式** — `為何現在不做: user-ruling:2026-09-09 裁定 P3 範圍＝IC 直接對 0/1 算；0/1 不隨 h/k 變，掃描無定義（Task 3.3 明擋 400）`；觸發：使用者提出「按 k 掃描 binary」需求；登記處：registry。
- **R-6 `single_feature_binary_baseline`（GAP-3 B1.4）與本票 Task 3.5 之合流** — `為何現在不做: blocked-by:B1.4 吃 EventSplitPlan（事件切分）而本票走 IC 切分列索引，兩者 split 模型不同；本票只重用 permutation_oracle`；觸發：事件切分與 IC 切分統一票；登記處：registry。
