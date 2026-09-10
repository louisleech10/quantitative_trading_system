# EVTLABEL — 事件型 label 三缺陷修補＋匯入標籤模式 — SPEC

> 來源 PLAN/診斷：`HANDOFF.md` 🔴 EVTLABEL 段（2026-09-09 晚使用者裁定）｜日期：2026-09-10｜對應 TODO：`docs/EVTLABEL_TODO.md`
> 票：`EVTLABEL`　起草：Claude（主委）　審查：Codex＋Composer＋Grok 三家 adversarial（`scripts/governance_roles.json`）
> **狀態（2026-09-10）**：v4；R1/R2/R3 三家 RECONCILE-STAMP APPROVED（`0dbe40ff`）。**Phase 1／Phase 2 FROZEN**（使用者 9/10 白話閘：「purge 的部分同意」）；**Phase 3 Internal Frozen，待使用者看完標籤部分放行**。全域主線 horizon 靜默取第一個 ⇒ 另開小票 GLOBALH（ROADMAP），不入本票。

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
- `ASSUME-3`（**R1 三家讀碼＋codex 實跑成立**）：`validate_event_given` 對 0/1 float 之逐值相等檢查可重用（`contracts.py:1084-1092`；codex 實跑 `checked_samples=2, consumed_event_labels={e0:0.0,e1:1.0}`）。它**不驗值域**——值域閘由 Task 3.3 在 staging 補（R1 C14c）。

### R1 裁定（三家 adversarial 之結果；收斂檔 `handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`）
- `ASSUME-2` 部分成立：clean 向量化 0.41–0.77s（codex／composer 實跑 39,373×165）；10% NaN 逐欄 5.48s（composer）。完整路徑 benchmark 為 Task 3.7 之測試（超 120s ⇒ FAIL）。
- 🔴 「`rank_biserial` 餵既有 `ic_mean_min`」**推翻**（C1）：有號比較會殺掉反向強分辨；且 IC 的 0.02 非同一 estimand 之門檻 ⇒ 另設 `rank_biserial_min`（取絕對值）。
- 🔴 `auto` 判定改在 **orchestrator stage3 切分已知後**以實際 selection scope 每類計數決定（C2）；受理 run test 段 17 正／14 反（三家實算一致）。
- 🔴 負對照非零 ⇒ **fail-closed**（C3）；stage3 驗證後之 binary 向量以 immutable digest 綁到 stage5 消費（C4）；三元組加 timestamp 腿＋雙鍵回比（C5）。
- P2 控制通道改顯式 kwarg `event_isolation`（C8）——`ICConfig` 未知鍵會被靜默丟（三家實跑）。
- P2「語意錯位非洩漏」成立；總隔離 h1 c2c 149→156、h12 o2hc 161→300；`D=0,C=0,W>H` 時總隔離可小於改前但仍 ≥ max(W,D)。
- ICConfig `extra`：非 forbid（Pydantic 預設 ignore）。

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
- **G-3 受理事件 run 重現（P2）**：以 `data_cache/events/20260909T130533Z-7f73e4c7.json`（165 事件）配同一 1h feature run 重跑；期望 `metadata.ic_train_test_split = {purge_gap: 12, purge_gap_source: "event_label_window", event_label_window_rows: 12, lookahead_depth_rows: 144, embargo: 144}` 且 `metadata.isolation.embargo.source == "event_lookahead_depth"`、`isolation.total_bars == 156`（改前 5/144/149）。若 feature run 已不存在 ⇒ 以探針 G-2 之事件組替代並在 TODO 具名。
- **G-6 survivor payload golden（P3；R1 C12）**：P3 動工前以 `return_rule` 事件 run 與全域 run 各凍結一份 survivor payload canonical bytes（去 `generated_at`）與 sha256、欄集、null mask、檔案大小至 `tests/golden/evtlabel/survivor_{event_return_rule,global}.json`；P3 改後逐項相等，任一新鍵／排序漂移 ⇒ FAIL。
- **G-4 事件 return_rule 模式報告不變（P3）**：P3 完工後以 `label_mode=return_rule` 重跑 G-3 之 run，刪除 `metadata.event_label_rule`／`metadata.label_mode` 兩新鍵後 canonical sha 與 P2 完工時相同。
- **G-5 統計 oracle（P3）**：見 §V mutation；植入 label 之 AUC 期望值精確（`==1.0`）、鏡像 label 之 rank-biserial 精確取負（`abs≤1e-12`）。

---

## §P Phase 與依賴

### Phase 1 — 揭露實際 label 規則＋UI 單位（依賴：無）

**Task 1.1 — `metadata.event_label_rule` 揭露（後端）**
- 目標：事件 run 之報告寫入本次**實際消費**的 label 規則與單位換算。
- 檔案：`api/services/ic_analysis_service.py` 新增 `_inject_label_rule_disclosure(staged, report)`，掛在 `_inject_isolation_source` 同一呼叫序（主路徑與掃描格路徑皆掛）。
- 既有 caller/影響面：新建；只在事件路徑（有 `staged`）寫鍵；非事件 run 不寫 ⇒ G-1 不變。
- 改法：由 `staged["prepared"].normalized_spec_bytes` 解析 spec（**不讀 request**，request 可能是 route seed 前的值）；由 `staged["prepared"].windows` 取 `max(label_end_ms − label_start_ms)`；由 `report.metadata.timeframe`（特徵週期）與 windows 之 `timeframe`（事件週期）算 `feature_bars_per_event_bar = event_bar_s / feature_bar_s`（非整數 ⇒ 寫 `null` 並 `ratio_integral=false`）。鍵集（closed；列於 `event_label_mode.json` 之 `event_label_rule_keys`，P3 Task 3.1 建檔前先以本 Task 建檔）：`label_source`（抄 `event_filter.label_source`）、`statistic_kind`（抄 `event_filter.statistic_kind`）、`horizon_bars`、`decision_offset_bars`、`entry_price_semantic`、`label_return_mode`、`h_unit="event_timeframe_bars"`、`event_timeframe`、`feature_timeframe`、`feature_bars_per_event_bar`、`label_window_feature_bars`（ceil(window_ms/feature_bar_ms)）、`return_formula`（由 `label_return_mode`＋`entry_price_semantic` 機械組字串，如 `close[t0+h]/close[t0]-1 × direction_sign`）、`imported_binary_label={present, n_pos, n_neg, used}`（P1 時 `used=false`；P3 改由 label_mode 決定）、`n_events_consumed`、`uniqueness={mean, min, n_eff, n_overlapping_pairs}`（R-1 不重工預留，使用者 2026-09-10：每事件權重＝1／與其 label 視窗 `[label_start_ms, label_end_ms)` 相交之事件數（含自己；同 `dedupe.py:86` 定義），`n_eff=Σw`；**只揭露不參與計算**）。
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
- 改法：兩注入點改為 `cell_override["embargo"] = max(config.embargo, lookahead_depth_rows)`，並以**顯式 kwarg** `analyzer.analyze(..., event_isolation=EventIsolationRows(label_window_rows, lookahead_depth_rows))` 傳給 orchestrator（R1 C8：**不走** `config_override`——`ICConfig` 對未知鍵靜默丟，三家實跑證實）；`EventIsolationRows` 為 frozen dataclass 於 `momentum/core/contracts.py`；`staged["embargo_before_event"]` 語意不變。
- **驗證**：`pytest tests/momentum/event_samples/test_isolation_terms.py -q` rc=0：12h×h=1 事件於 1h 特徵 ⇒ `label_window_rows==12`；`lookahead_bars_declared={"12h":12}` ⇒ `lookahead_depth_rows==144`；`open_to_close` ⇒ `label_window_rows==12`（一根事件週期）；4h×h=3 於 1h ⇒ 12。不變式測試：對 G-2 九組，`max(label_window_rows, lookahead_depth_rows) == purge_rows(舊)`。
- **邊界**：①`lookahead_bars_declared[tf]==0` ⇒ `lookahead_depth_rows==0`（embargo 回 config）；②windows 空 ⇒ 兩值 0 且不 raise（由既有 `ts_map` 空檢查 loud）；③feature_bar_s > event_bar_s（細事件配粗特徵）⇒ ceil 給 1，不給 0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `purge_lower_bound_rows` 公式；不動事件切分 `split_events`。

**Task 2.2 — split 之 purge 吃事件 label 視窗（orchestrator）**
- 目標：`purge_gap = max(effective_horizon, event_isolation.label_window_rows)`；embargo 只承載 config／look-ahead 深度。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`：`analyze(...)` 與 `_run_full_sample_fallback` 新增顯式 kwarg `event_isolation: Optional[EventIsolationRows] = None`（R1 C8 定死；**禁**經 `config_override`）；`:1102-1160` 呼叫 `_build_holdout_split_plan(purge_gap=max(effective_horizon, event_isolation.label_window_rows if event_isolation else 0))`；`metadata["ic_train_test_split"]` 新增三鍵 `purge_gap_source ∈ {mainline_horizon, event_label_window}`、`event_label_window_rows`、`lookahead_depth_rows`（**`embargo_source` 不在此寫**——R1 C7 定死由 service 寫在 `metadata.isolation.embargo.source`）。
- 既有 caller/影響面：`_build_holdout_split_plan` 之 `purge_gap < effective_horizon ⇒ raise` 守衛保留（max 後恆成立）；`SplitPlan.purge_gap < len(row_index)` 不變式保留；跨截面路徑不動。fail-closed 守衛：`config_override` 含 `event_purge_rows`／`lookahead_depth_rows`／`event_isolation` 任一鍵 ⇒ `analyze` 入口 raise（防走錯通道被靜默丟）。
- 改法：只改 purge 之取值與 metadata 三鍵；`_build_holdout_split_plan` 之 `test_rows` 算式改呼叫 `momentum/core/split_preview.py::holdout_test_row_index`（R3 單一實作，供 Task 3.3 預檢共用；純算術等價，G-2 全域組逐位元組不變為證）；`split_context["effective_horizon"]` **不改**（HAC lag 議題見 §N R-1）。
- **驗證**：G-2 探針 `--diff` 三條通過條件；G-3 重現 `purge_gap=12, embargo=144`；`pytest tests/momentum/Analysis/test_ic_1a_cut1_split.py tests/momentum/core/test_split_contract.py tests/golden/ic_phase1_contract -q` rc=0（全域路徑不變）；`ASSERT venv/bin/python handoffs/20260907-probe-split-baseline.py --check WHEN group=global THEN rc=0`；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_isolation_channel.py -q WHEN config_override=event_purge_rows THEN rc=0`（測試斷言 raise）。
- **邊界**：①`label_window_rows > n_rows − split_point − embargo` ⇒ 既有 `SkippedResult(INSUFFICIENT_DATA)` 路徑（loud、走 fallback）；②`event_isolation=None`（非事件）⇒ 行為逐位元組同改前；③`label_window_rows < effective_horizon` ⇒ `purge_gap_source="mainline_horizon"`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `_resolve_effective_label_horizon`；不改 embargo 語意為「含 label 視窗」（那是改前錯位）；不在 orchestrator 換算 ms（列數由 service 給）。

**Task 2.3 — 隔離區揭露改讀新來源（service＋前端）**
- 目標：`metadata.isolation.purge.source` 反映真實來源。
- 檔案：`api/services/ic_analysis_service.py::_inject_isolation_source`（`purge.source` 抄 `ic_train_test_split.purge_gap_source`，`purge.note` 改為機械組字串；`embargo.source` 由 service **自算**：`staged["lookahead_depth_rows"] > staged["embargo_before_event"]` ⇒ `event_lookahead_depth` 否則 `config_embargo`——R1 C7 唯一寫入點；另寫 `embargo.lookahead_depth_rows`）；`frontend/src/lib/icIsolation.ts` `SOURCE_TEXT` 新增 `event_label_window`／`event_lookahead_depth` 兩鍵（保留舊鍵供舊報告）。
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
- 檔案：新建 `momentum/Analysis/contracts/event_label_mode.json`（含 `event_label_rule_keys`——P1 先建此檔之該鍵）；`momentum/core/contracts.py:1030` `LABEL_KIND_BY_SOURCE` 新增 `imported_binary_label → event_given`（Python 常數＋測試對證 JSON，定死）；同檔新增 `EventIsolationRows`（P2）、`ValidatedBinaryLabel(series, digest, rows_frozenset, n_pos, n_neg)` frozen dataclass（`rows_frozenset`＝驗證時 `(event_id, ts_ms, label)` 集合，供 stage5 對 selection 子集逐筆 `in` 對證）、`is_event_label_consumed(event_info) -> bool`（涵蓋 `event_label_value` 與 `imported_binary_label`；R1 C9 單一 predicate）；`momentum/Analysis/contracts/ic_survivor_contract.json` `sample_scope.event.label_source` `_doc` 補 `imported_binary_label`、新增 `label_binary` 子物件鍵（`import_id`／`n_pos`／`n_neg`／`label_origin_values`；nullable，非 binary 模式為 null）；`momentum/Analysis/ic_config_schema.py`：`EventFilterConfig.min_events_per_class:int=10`（文件明寫：exact MW 可算之最低條件，**非 power 依據**）、`EventFilterConfig.perm_budget_total:int=200000`、`EventFilterConfig.negative_control_n:int=50`（R3 E2）、`EventFilterConfig.oracle_seed:int=20260910`、`ThresholdsConfig.rank_biserial_min:float=0.10`（＝AUC 0.55；取絕對值比較；非 power 校準之預註冊效應量門檻，主閘＝FDR＋依賴感知置換——R1 C1）。
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
- 改法：route／service 只透傳 `requested`；effective mode 於 orchestrator stage3 決定（Task 3.4；R2 D5）。
- **驗證**：`pytest tests/api/test_ic_analysis_api.py -q -k label_mode` rc=0（缺 import_id 帶 `imported_binary` ⇒ 400；預設 `auto`）；`cd frontend && npx vitest run src/hooks/icEventAnalysisRequest.test.ts` rc=0（legacy `event_timestamps` 分支**不送**此欄）。
- **邊界**：①`event_timestamps` 路徑帶此欄 ⇒ 400；②大小寫錯 ⇒ 422（Pydantic）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不新增第四種模式；不把 `auto` 解析放路由。

**Task 3.3 — staging：binary label 向量與 `auto` 解析（service）**
- 目標：與 `ts_map` 同一迴圈、同一鍵（feature_cutoff_ms）產出 `event_binary_labels: {ms: 0|1}`；另由匯入 records **獨立快照**建 `event_binary_rows_by_id: {event_id: (ms, 0|1)}`（R1 C5：三元組來源不與 consumer map 同源）；值域閘；**不決定** effective mode（R1 C2：決策點移至 orchestrator stage3）。
- 檔案：`api/services/ic_analysis_service.py:700-772`；`_run_event_label_stages` 兩路徑透傳 kwargs `event_binary_labels`、`label_mode_requested`。
- 既有 caller/影響面：`_assert_event_triple_bound` 改依 `label_source` 分派（R1 C5）：`event_label_value` ⇒ 既有回比；`imported_binary_label` ⇒ **雙鍵**回比——報酬 `consumed_event_labels` vs `event_label_by_id` **且** binary `consumed_event_binary_rows={event_id:(ms,value)}` vs `event_binary_rows_by_id` 三項逐筆；其他 source 維持既有語意。掃描格路徑：binary 模式下 `event_label_scan` 非空 ⇒ 400 `scan_not_applicable_in_imported_binary_mode`（0/1 不隨 h/k 變）。
- 改法：值域閘（R1 C14c）：`label` 須 finite、整數、精確 ∈ {0,1}、批內無缺值；違反 ⇒ `requested=imported_binary` raise（422）、`requested=auto` ⇒ 不送 binary map 並記 `label_mode_hint=label_invalid_domain`（進 `metadata.label_mode.reason`）。`label` 欄缺（legacy）⇒ `hint=no_label_column`。其餘情況一律送 binary map，由 orchestrator 依 selection scope 決定。**顯式模式 fast-fail（R2 D4）**：`requested=imported_binary` 時，service 以**同一純函式** `momentum/core/split_preview.py::holdout_test_row_index(n_rows, *, oos_test_size, purge_gap, embargo) -> np.ndarray`（R3：orchestrator `_build_holdout_split_plan` 之 `test_rows` 算式亦改呼叫此函式——單一實作，G-2 全域組逐位元組不變證明其純算術等價）對 feature index 預估 test 段（`purge_gap=max(effective_horizon,label_window_rows)`；`effective_horizon` 由 service 以 `_resolve_effective_label_horizon` 同源解析），計 binary map 於該段之每類數；`< min_events_per_class` ⇒ 立即 422 `class_below_min_selection_preview`（不進 preprocessing）。`auto` 不預擋。預檢與 stage3 用**同一函式、同一輸入**（`n_rows`＝feature 列數、同 `purge_gap`／`embargo`）⇒ 兩者不一致＝內部 bug：stage3 以 `AlignmentViolationError("selection preview mismatch")` raise（R3 codex P1-04：不接受「以 stage3 為準並揭露」之容忍流）；`metadata.label_mode.selection_preview={n_pos,n_neg}` 揭露預檢值。
- **驗證**：`pytest tests/api/test_evtlabel_staging.py -q` rc=0：165 批（測試自建 records）⇒ `len(event_binary_labels)==len(event_label_values)` 且鍵集相等、`event_binary_rows_by_id` 之 ms 與 `event_label_owners` 反查一致；records 注入 `2,-1,0.5,NaN,None` 各一 ⇒ `auto` 給 `label_invalid_domain`、`ASSERT venv/bin/python -m pytest tests/api/test_evtlabel_staging.py -q -k explicit_binary_invalid_domain WHEN label_mode=imported_binary THEN rc=0`（測試斷言 raise）；三元組：交換兩個同值事件之 owner ⇒ `_assert_event_triple_bound` raise（timestamp 腿）。
- **邊界**：①legacy 無 `label` ⇒ `no_label_column`；②缺值混雜 ⇒ 見值域閘；③symbol 過濾後單類 ⇒ 仍送 map，由 stage3 判 `one_class`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `ts_map` 鍵；不在此算統計。

**Task 3.4 — stage3：binary label 綁定與驗證（orchestrator）**
- 目標：`_stage3_event_filter` 決定 `label_mode_effective`（R1 C2）；`imported_binary` 下同時保留報酬 label（第二欄）與 0/1 label（主統計），兩者皆過 `validate_event_given`；binary 向量以 immutable `ValidatedBinaryLabel` 交付 stage5（R1 C4）。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py:3348-3480`；`self._ic_cache["event_binary_label"]: ValidatedBinaryLabel`（frozen；`series` 為唯讀 copy、`digest`＝sha256 over sorted `(event_id, ts_ms, label)`）。
- 既有 caller/影響面：`event_info` 新增 `consumed_event_binary_rows`、`binary_label_digest`、`label_source="imported_binary_label"`、`statistic_kind="binary_discrimination"`、`secondary_statistic="conditional_ic"`；`metadata.label_mode={requested, effective, reason, n_pos_batch, n_neg_batch, n_pos_selection, n_neg_selection, selection_scope}`；`return_rule` 模式下 `event_info` **逐鍵不變**（G-4）。既有 `_is_event_conditional_consumed` 之所有呼叫點改為 `is_event_label_consumed`（R1 C9），ICIR 閘在兩 source 下皆關。
- 改法：mode 決策：`requested=auto` 且 binary map 存在 ⇒ 以 **selection scope**（有切分＝test 段事件列；full-sample fallback＝全部事件列）每類 ≥ `min_events_per_class` ⇒ `imported_binary`，否則 `return_rule`＋`reason ∈ {no_label_column, label_invalid_domain, one_class, class_below_min_selection}`；`requested=imported_binary` 不足 ⇒ raise（non-retryable）。binary 向量以 `validate_consumed_label(label_kind=derive_label_kind("imported_binary_label"), expected_values=binary, event_owners=owners)` 驗證（ASSUME-3；R1 C6 修 kwarg），回傳新增 `consumed_event_rows`（additive；報酬路徑回傳鍵不變）；報酬 label 仍走既有驗證。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q` rc=0：錯位一格之 binary 向量 ⇒ `AlignmentViolationError`；`return_rule` 下 `event_info` 鍵集 == 改前鍵集；`imported_binary` 下 `consumed_event_binary_rows` 值集 ⊆ {0.0, 1.0}；fixture 全批 20/20、test 段 18/2 ⇒ `auto` 得 `return_rule`／`class_below_min_selection`；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage3.py -q -k icir_gate_off_binary WHEN label_source=imported_binary_label THEN rc=0`（ICIR 低於門檻之 binary 特徵不被移除）。
- **邊界**：①事件不足 fallback（`conditional_ic_abandoned`）⇒ binary 亦放棄，`statistic_kind="binary_discrimination_unavailable"`、`label_source="mainline_return_N"`；②binary 向量含 NaN ⇒ raise；③selection scope 單類 ⇒ `one_class`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不覆寫 `consumed_event_labels`（報酬三元組鍵）。

**Task 3.5 — 純統計模組：Mann-Whitney／AUC／rank-biserial（向量化）**
- 目標：對 `features (n×p)` 與 `y∈{0,1}^n` 逐欄算 AUC、rank-biserial、U、雙尾 p；NaN 逐欄 pairwise 去列並記 `n_used`。
- 檔案：新建 `momentum/Analysis/binary_discrimination.py::mann_whitney_table(features: pd.DataFrame, y: np.ndarray, *, min_class_n: int, weights: Optional[np.ndarray] = None) -> pd.DataFrame`（`weights` 為 R-1 不重工預留：本票一律 `None`；傳入非 None ⇒ `NotImplementedError("weighted MW 屬 R-1 票")`，禁靜默忽略）（欄：`auc, rank_biserial, mw_u, p_value, n_pos, n_neg, n_used, status`；`status ∈ {ok, unavailable:<reason>}` 枚舉入 JSON）。
- 既有 caller/影響面：新建；Task 3.6 唯一 caller。
- 改法：`scipy.stats.mannwhitneyu(x_pos, x_neg, alternative="two-sided", method="auto", axis=0, nan_policy="omit")`（scipy 1.13.1 已裝；ties/continuity 由 scipy 處理；NaN 逐欄 omit 由 scipy 向量化——R3 codex P1-03：逐欄 python 迴圈於 10% NaN 39k 欄實測 8.9s/次，×50 負對照不可接受，故**禁**逐欄迴圈）；`auc = U_pos / (n_pos·n_neg)`；`rank_biserial = 2·auc − 1`；`n_used`／`n_pos`／`n_neg` 逐欄由 finite mask 算；`min_class_n` 逐欄判。測試以逐欄標量呼叫對證 `nan_policy="omit"` 之逐欄等價（`rel≤1e-9`）。
- **驗證**：`pytest tests/momentum/Analysis/test_binary_discrimination.py -q` rc=0：①`y = 1[x > median(x)]` ⇒ `auc==1.0`（exact）；②`y` 鏡像（1−y）⇒ `rank_biserial` 逐欄取負 `abs≤1e-12`；③與逐欄 `scipy.stats.mannwhitneyu` 標量呼叫逐欄相等（`p` `rel≤1e-9`）；④benchmark receipt：39,373 欄 × 165 列（真實 feature run 或同形隨機矩陣）耗時印出，`< 60s`（ASSUME-2）；⑤全 NaN 欄 ⇒ `status=unavailable:all_nan`；⑥常數欄 ⇒ `auc==0.5`、`p==1.0` 或 `status=unavailable:constant`（二擇一在 TODO 定死並測）。
- **邊界**：①某類去 NaN 後 `< min_class_n` ⇒ `unavailable:class_below_min`；②`n_used==0`；③極端 ties（整欄兩值）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不做多特徵組合；不做 bootstrap CI（置換 oracle 見 3.7）；不在 hot loop log。

**Task 3.6 — stage5：binary 統計進 summary_table＋門檻（orchestrator）**
- 目標：`imported_binary` 下 summary_table 每列新增 binary 欄，主統計＝`rank_biserial`，p 走 Mann-Whitney→BH（`apply_fdr`）；報酬版 `ic_mean`／`t_stat`／`p_value` 保留為第二欄（改名**不做**，以 `metadata.event_label_rule.primary_statistic="rank_biserial"`＋`secondary_statistic="ic_mean"`＋`p_assumption="iid_events"` 揭露）；stage6／6b 之消費規則定死（R1 C9）。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 事件分支（`:3766-3900`）、stage6 redundancy（`:3266-3281`）、stage6b（`:4609-4649`）；`_apply_thresholds(..., binary_mode: bool = False)`。
- 既有 caller/影響面：`_apply_thresholds` 既有呼叫預設值不變（全域逐位元組不變）；summary_table 新增欄 `auc, rank_biserial, mw_u, mw_p_value, mw_p_value_adj, n_pos, n_neg, n_used_binary, binary_status`（`return_rule`／全域下**不寫**這些欄——G-1／G-4）；排序鍵 binary 模式＝`|rank_biserial|` desc、tiebreak `feature_name` 字典序。
- 改法：stage5 消費前之**唯一守衛**（R2 D1，取代任何「digest 相等」比對；`digest` 只作 stage3 封存／揭露）：`X = features.loc[sel_idx, feature_cols]`、`y = vb.series.loc[sel_idx]`；斷言 ① `X.index.equals(pd.Index(sel_idx))` 且 `len(y)==len(X)`；② `all((owner[ts], ts, int(y_i)) in vb.rows_frozenset for ts, y_i in zip(sel_idx_ms, y))`；任一不成立 ⇒ `AlignmentViolationError`，不產 report。統計對象＝selection scope 之事件列（有切分＝test 段；與條件 IC 同 scope）。stage6b（R2 D7）：入參 label 固定為報酬列（既有 `label_series`），該節 metadata 寫 `role="diagnostic"`、`label_source="return_rule_diagnostic"`。`binary_mode=True` 時：效應量閘＝`abs(rank_biserial) >= thresholds.rank_biserial_min`（R1 C1；`removed["rank_biserial"]`）；p 閘讀 `mw_p_value_adj`；`ic_mean`／`icir`／`ic_hit_rate`／`monotonicity`／`coverage`／`long_short_spread` 閘全部**記錄不剔除**（鍵名＝JSON `threshold_skip_keys_binary`）；`binary_status != ok` ⇒ `removed["binary_unavailable"]`。stage6 redundancy：binary 模式分數＝`|rank_biserial|`（同 tiebreak）；stage6b marginal／composite 在 binary 模式標 `role="diagnostic"`，其結果**不得**移除 binary 倖存者。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q` rc=0：植入特徵（Task 3.5 ①）⇒ `passed`、`mw_p_value_adj < 0.05`；**負向植入（rb≈−0.8）亦 `passed`**；`rank_biserial_min=0.9` ⇒ 弱特徵進 `removed["rank_biserial"]`；`p_value_max=0.001` ⇒ 弱特徵 `removed["p_value"]`；`return_rule` 下 summary_table 欄集 == 改前欄集（G-4）；stage3 驗後替換 cache 為另一向量 ⇒ stage5 raise 且不產 report（M-P3-5）；對證後 permute `X` 列序（`X.iloc[perm]`）⇒ 斷言① raise（M-P3-5b，grok R2 2a 反例）；具名殘形（grok R3 P2-03，不加 value-digest）：「保 index 之值列重排」`pd.DataFrame(X.to_numpy()[perm], index=X.index, columns=X.columns)` 可過三守衛——以 TODO 3.6 要點 1「對證後直接餵入、中間不得重排」之祈使句＋code review 擋，測試以 `inspect` 斷言 stage5 對證與 `mann_whitney_table` 呼叫間無 `X =` 再賦值（靜態守衛）；雙特徵 fixture（A 只對 0/1 分離、B 只對報酬強）跑 stage3→6b ⇒ 倖存集含 A 不含 B；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_stage5.py -q -k threshold_reads_abs_rank_biserial WHEN label_mode=imported_binary THEN rc=0`。
- **邊界**：①selection scope 單類 ⇒ 全表 `unavailable:one_class_selection`、倖存者 0、`degraded` loud（已由 stage3 轉 `return_rule`，此為顯式 binary 之防線）；②`rolling IC` 空（pooled fallback）與 binary 並存；③特徵全 `unavailable` ⇒ FDR `n_tests=0` 不除零。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不把 `rank_biserial` 寫進 `ic_mean` 欄冒充；不共用 `ic_mean_min`；不改全域 `_apply_thresholds` 預設路徑一字。

**Task 3.7 — 置換自檢＋負對照（fail-closed）**
- 目標：(C) consumable 放行＝倖存者逐一以**依賴感知 block permutation**（R1 C10）對 AUC 重驗，置換帶內（不顯著）或 `unavailable` ⇒ 移出 consumable（特徵級 fail-closed，`removed["permutation_oracle_disagree"]`／`["permutation_unavailable"]`）。(B) 整批負對照（R2 D2 校準；取代 R1 C3 之單次 `>0`）：**N=50 次** block 置亂（seed 遞增；R3 codex P1-02：離散 order statistic 需足夠尾部解析度）各重跑 Task 3.5＋BH＋效應量閘得整數 `shuffled_counts[50]`；`q95 = np.quantile(shuffled_counts, 0.95, method="higher")`（整數 order statistic，不插值）；`n_observed == 0` ⇒ 不跑負對照、`negative_control.status="skipped:no_survivors"`（R3：與邊界①同路徑，不得標 failed）；`n_observed > 0` 且 `n_observed <= quantile(shuffled_counts, 0.95)` ⇒ **suppressed**（觀測倖存數與 null 無法區分；`survivor_output.status="suppressed"`、`reason="negative_control_failed"`，報告 `degraded`、診斷表保留）；否則寫 `metadata.event_label_rule.negative_control={n_observed, shuffled_counts, q95, seed_base}` 揭露。預註冊：獨立近似下整批誤殺率 ≈ α（grok R2 模擬 P(R>0)≈0.03–0.07），可接受。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py` stage5 binary 分支末；`momentum/Analysis/binary_discrimination.py::block_permutation_oracle(values, y, block_ids, stat_fn, oracle_config)`（新；置換單位＝block，沿 `baseline.py::permutation_oracle` 三道硬檢，`_permute` 改為 block 級置換供 mutation guard）。
- 既有 caller/影響面：`baseline.py::permutation_oracle` 不改（B1.4 仍用）；常數欄已於 3.5 `unavailable`，不進倖存者。
- 改法：block 長度 `L = max(1, ceil(W / max(1, min_gap_rows)), ceil(W / median_gap_rows))`（W＝`label_window_feature_bars`；取較大者以吸收局部密集段——R2 D3），事件依時間順序每 L 個為一 block；`n_blocks < 10`（預註冊常數，非推導）⇒ 置換 `unavailable:insufficient_blocks`，該特徵不得成為 consumable 倖存者（記 `removed["permutation_unavailable"]`），`permutation_receipt.status` 與 `label_mode.note` loud 揭露（長視窗之預期限制，見 §N R-7）。預算（R1 C14a）：候選 K 依 `|rb|` desc／`feature_name` 排序；`n_perm = clamp(perm_budget_total // K, 200, 1000)`；receipt（seed、`n_perm`、`L`、`n_blocks`、`first_permutation_digest`）寫 `metadata.event_label_rule.permutation_receipt`。受理 run（h=1、事件間距 ≥1 根 12h）⇒ `L=1`，與普通置換等價。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_oracle.py -q` rc=0：植入特徵 `in_band==False` 留下；植入 fixture（200 合成特徵×165 真實 kline 列，含 1 個植入）⇒ `n_observed > q95(shuffled_counts)`、survivor 可寫；全 null fixture（無植入）⇒ `n_observed <= q95` ⇒ `survivor_output.status=="suppressed"`、`reason=="negative_control_failed"`、無 consumable 檔（M-P3-6）；mutation：monkeypatch `_permute_blocks` 為恆等 ⇒ 硬檢 (ii) raise；`L=3` fixture ⇒ 同一 block 內標籤在置換後仍相鄰（block 完整性）；密集段 fixture（前 10 事件 gap=1、其後 gap=20、W=12）⇒ `L>=12`（`test_dense_cluster_block_len`）；W=156、median_gap=1 fixture ⇒ `n_blocks<10`、`status=unavailable:insufficient_blocks`、無 consumable；benchmark（兩道獨立閘，R3 codex P1-03）：(a) per-survivor 置換 K=2000、`perm_budget_total=200000` 於 39,373×165 fixture `< 120s`；(b) 負對照 N=50 於 39,373×31 之 clean 與 10% NaN 兩形狀各 `< 120s`；任一超時 **FAIL**（非只印 receipt）。
- **邊界**：①倖存者 0 ⇒ 不跑置換、receipt 寫 `skipped:no_survivors`；②`n_perm` 下限 200，`perm_budget_total < 200×K` ⇒ n_perm=200 並記 `budget_floor_hit`；③`n_blocks < 10`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不把置換 p 取代 MW p（置換只作自檢與依賴感知放行）；不對全表 39k 欄跑置換。

**Task 3.8 — 倖存者輸出帶標籤來源**
- 目標：`survivor_output.sample_scope = {kind: "event", event: {…六鍵, label_source: "imported_binary_label", label_binary: {import_id, n_pos, n_neg, label_origin_values}}}`；`statistic_kind` 進 `sample_scope.event`（Task 3.1 契約）。
- 檔案：`momentum/Analysis/survivor_contract.py::build_survivor_output`（`:411-700`）、`validate_survivor_output`（`:238-310`）；`_write_survivor_output`。
- 既有 caller/影響面：`tests/momentum/Analysis/test_survivor_contract.py`、`test_gap2_survivor_persist.py`（return_rule／全域 payload 逐位元組不變）。
- 改法：由 `event_context`＋`event_info` 導出；`return_rule` 下 `label_binary=null`；`negative_control_failed`（Task 3.7）⇒ `survivor_output={status:"suppressed", reason:"negative_control_failed"}`，不寫 consumable 檔（reason 入 `_survivor_reason` 詞彙表）。
- **驗證**：`pytest tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_gap2_survivor_persist.py -q` rc=0；G-6 survivor golden 逐項相等；新測：binary run 之倖存者檔 `sample_scope.event.label_source=="imported_binary_label"`、`label_binary.n_pos==136`；`validate_survivor_output` 對 `label_binary` 缺 `import_id` ⇒ raise。
- **邊界**：①倖存者 0 ⇒ 既有 suppressed stub 路徑、`sample_scope` 仍寫；②掃描格不寫 survivor（既有）。
- **存活至**：全票完工後保留；此檔即「餵 ML」之交接物。
- **覆蓋風險**：無。
- 不可做：不改 `sample_scope_kind_values`；不改倖存者檔路徑規則。

**Task 3.9 — 前端：模式選擇＋表格欄＋揭露**
- 目標：事件參數面板加 `label_mode` 三選（auto／return_rule／imported_binary，`data-testid="ic-param-label-mode"`，顯示批內正反數）；結果頁 summary 表在 binary 模式優先顯示 `AUC／rank-biserial r／U／p／q／n⁺／n⁻`（**表頭一律統計學標準名、不自創**——使用者 2026-09-10；rank-biserial correlation＝Cureton 1956、q＝Benjamini–Hochberg），報酬版 IC 欄後移並標「第二欄」；隔離區第四行改「已用」分支；`DegradedBanner` 顯示 `label_mode.reason`（auto 回退時）；`imported_binary` 生效時亦顯示非 degrade 之模式摘要 banner（`data-testid="label-mode-banner"`：「本次 IC 對象＝你匯入的 0/1 標籤（selection 段正 n／反 m）」，R1 C14b）；`survivor_output.status=suppressed` 且 `reason=negative_control_failed` ⇒ 紅色 banner（R1 C3／R2 D2）；`permutation_receipt.status=unavailable:insufficient_blocks` ⇒ 琥珀 banner「label 視窗太長、可置換區塊不足：本次無法做依賴感知放行，倖存者不可餵 ML（預期限制，見說明）」（R2 D3）。
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
- 改法（R1 C11：移除 sign oracle）：斷言 (i) 兩模式之事件身分（`consumed_event_count`、event_id 集合、對應 ts）逐位元組 parity；(ii) 同一 run `return_rule` 與 `imported_binary` 之報酬欄 `ic_mean`／`t_stat`／`p_value` 逐特徵相等（第二欄＝原 IC）；(iii) 真實 kline 上植入單調特徵 `feat_planted(t)=close_12h(t0+1)/close_12h(t0)`（與 label 規則同源）⇒ `auc==1.0`、`passed`；(iv) PIT：binary label 整體往前錯一事件 ⇒ `AlignmentViolationError`（由 3.4）；(v) 三方各自實跑探針並附 receipt（簽核鐵律）。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_e2e_realkline.py -q` rc=0；探針印 receipt（事件數、n_pos/n_neg、selection scope 類數、倖存者數、negative_control、permutation L／n_blocks）。
- **邊界**：①kline cache 缺 ETHUSDT ⇒ `pytest.skip` 並印明（不得假綠）；②事件 < `min_events` ⇒ 測試自建足量事件。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：禁合成價格；禁用 `data_cache/events/*`（未追蹤、不可攜）當 fixture。

**Task 3.11 — 倖存者檔之 ML 消費契約測試（R1 C13）**
- 目標：證明 binary 路徑產出的 survivor payload 是既有純函式 consumer 可接收的 ML 輸入，而非只是一個檔案。
- 檔案：`tests/momentum/Analysis/test_evtlabel_survivor_consumer.py`；consumer＝`momentum/Analysis/event_samples/pattern_bridge.py`（`survivor_v2` 入口，`:52-64`／`:89-105`）。
- 既有 caller/影響面：無（測試）；**不接** ML 訓練殼、不加 API caller（成熟度地圖 2026-08-17 禁改殼）。
- 改法：以 Task 3.10 之 binary run 產出 survivor payload → 餵 `pattern_bridge` 之 `survivor_v2` 入口 → 斷言接收成功、`sample_scope.event.label_source=="imported_binary_label"`、`label_binary` 四鍵保留、倖存特徵集合與 payload 一致；`return_rule` payload 同測（`label_binary=null`）。
- **驗證**：`pytest tests/momentum/Analysis/test_evtlabel_survivor_consumer.py -q` rc=0；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_evtlabel_survivor_consumer.py -q -k suppressed_not_consumable WHEN survivor_status=suppressed THEN rc=0`（negative_control_failed 之 payload 餵入 ⇒ consumer raise／拒收）。
- **邊界**：①倖存者 0 之 stub payload ⇒ consumer **loud raise**（既有 `_survivor_feature_names` 對空 `survivors[]` raise，`pattern_bridge.py:24`；Claude 讀碼 2026-09-10）；②`schema_version=1` 舊 payload ⇒ 既有 validator 拒收（`:17-18`）；③suppressed stub 無 `survivors` 鍵 ⇒ 既有 raise（`:20-21`）——三者皆為「不得靜默回空」之既有行為，測試只釘住不改。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不改 `pattern_bridge` 行為；不建 ML pipeline caller。

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a/d ⇒ 必附。設計（`docs/TEST_DESIGN_CHARTER.md`）：
  - M-P2-1：把 Task 2.2 之 `max(effective_horizon, label_window_rows)` 改回 `effective_horizon` ⇒ G-2 條件 (ii) FAIL、G-3 期望 12 變 5 ⇒ 紅。
  - M-P2-2：把 embargo 注入改回 `max(config, purge_rows)` ⇒ `embargo_source` 斷言紅（depth<window 情境）。
  - M-P3-1：Task 3.5 `auc` 改 `1−auc` ⇒ 植入 oracle `auc==1.0` 紅。
  - M-P3-2：Task 3.6 p 閘仍讀報酬 `p_value_adj` ⇒ `threshold_reads_rank_biserial` 斷言紅。
  - M-P3-3：Task 3.4 binary 向量不過 `validate_event_given` ⇒ 錯位測試由紅轉綠 ⇒ 抓到（測試斷言必 raise）。
  - M-P3-4：Task 3.7 `_permute` 恆等 ⇒ 硬檢 (ii) raise。
  - M-P3-5：stage3 驗後替換 `_ic_cache["event_binary_label"]` 為另一 `ValidatedBinaryLabel`（錯 `rows_frozenset`／錯 series）⇒ stage5 三守衛 raise、不產 report（R1 C4／R2 D1；驗了＝用的；**無** digest 相等比對）。M-P3-5b：對證後 `X.iloc[perm]` ⇒ 斷言① raise。
  - M-P3-6：Task 3.7 `n_observed <= q95` 之 suppressed 路徑改回 warning-only ⇒ `suppressed_not_consumable` 斷言紅（R1 C3／R2 D2）。
  - M-P3-7：Task 3.6 效應量閘去掉 `abs` ⇒ 負向植入 `passed` 斷言紅（R1 C1）。
  - M-P2-3：`event_isolation` 改走 `config_override` ⇒ 入口 fail-closed 斷言紅（R1 C8）。
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

- **R-1 事件序列依賴之解析式 p（含事件路徑 HAC lag）** — `為何現在不做: needs-research:具體題目已定（使用者 2026-09-10 討論）＝AFML 樣本唯一性加權——GAP-3 已算之每事件 uniqueness 權重接進 Mann-Whitney／AUC（加權 U 統計量＋有效樣本數 n_eff=Σw 算 p），長視窗（R-7）亦可給 p；式子與 oracle 須委員會定，非本票範圍。本票以 block permutation 作依賴感知放行（Task 3.7）、MW p 標 iid_events 揭露；事件路徑 HAC lag 沿主線 5 只揭露不改（不等距下無正確 lag）`。**不重工預留（本票做）**：Task 3.5 `mann_whitney_table(..., weights: Optional[np.ndarray] = None)` 簽名預留（本票不傳）；Task 1.1 將每事件 uniqueness 權重摘要寫入 `metadata.event_label_rule.uniqueness={mean, min, n_eff, n_overlapping_pairs}`（只揭露不參與計算）。加權 p 進來時只替換 `mw_p_value` 欄之來源，FDR／門檻／表格／前端／倖存者檔不動；R-7 之「塊不足 ⇒ 不可餵 ML」屆時可改由加權 p 放行（加一條路，不拆東西）；觸發：委員會定出加權 U 之變異數式與 oracle；登記處：registry。
- **R-2 跨 symbol 合併之 binary 辨別** — `為何現在不做: blocked-by:Pooled/Panel IC 票（registry #4）；本路徑 symbol 過濾同條件 IC`；觸發：#4 開票；登記處：registry #4。
- **R-3 triple-barrier／出場最佳化** — `為何現在不做: user-ruling:2026-08-19 J5（第一版時間出場）`；觸發：使用者提出且回測層成熟；登記處：registry「GAP-3 殘留」#1（不重登）。
- **R-4 ML 訓練殼吃倖存者檔（主目標之「餵 ML」後半）** — `為何現在不做: blocked-by:成熟度地圖（2026-08-17）ML/回測為不完整層，禁改殼；本票交付物＝倖存者檔（sample_scope=event＋標籤來源）作為契約輸入`；觸發：ML 殼契約先行票開啟；登記處：registry。🔴 白話簡述頭條必列此條，由使用者決定是否接受此邊界。
- **R-5 掃描立方體（h/k 掃描）於 binary 模式** — `為何現在不做: user-ruling:2026-09-09 裁定 P3 範圍＝IC 直接對 0/1 算；0/1 不隨 h/k 變，掃描無定義（Task 3.3 明擋 400）`；觸發：使用者提出「按 k 掃描 binary」需求；登記處：registry。
- **R-7 長 label 視窗下 binary consumable 結構性不可得（R2 D3）** — `為何現在不做: needs-research:W≫事件間距時 block 數 <10，置換無法作依賴感知放行；解析式 dependence-aware p 未定義（同 R-1）；本票以 unavailable＋琥珀 banner 揭露為預期限制，不降 10 充綠`；觸發：R-1 之估計式定出、或委員會簽核較低 block 下限；登記處：registry。
- **R-8 非單調特徵之辨別力診斷（使用者 2026-09-10 裁定登記）** — `為何現在不做: user-ruling:2026-09-10 使用者裁定先以單調統計（Spearman IC／rank-biserial／AUC）篩特徵，非單調（U 型）特徵留給 ML；第一版不加分位／分組式辨別診斷`；影響：U 型特徵之 IC 與 AUC 皆近 0，會被篩掉；現有 `monotonicity_score` 欄可作報酬版之旁證，標籤版無對應欄；觸發：使用者發現重要特徵被漏、或要求分位式辨別表；登記處：registry。
- **R-5 修正（2026-09-10）**：「0/1 不隨 h／k 變」只對 h 成立——k（決策點偏移）改變特徵取列，標籤版下 **k 掃描有意義**（「提前 k 根仍分得開嗎」）；h 掃描無意義（每格答案相同）。本票：`imported_binary` 下 `event_label_scan` 任何形式 ⇒ 400（含 k）；k 掃描為真殘留，觸發＝使用者提出。
- **R-6 `single_feature_binary_baseline`（GAP-3 B1.4）與本票 Task 3.5 之合流** — `為何現在不做: blocked-by:B1.4 吃 EventSplitPlan（事件切分）而本票走 IC 切分列索引，兩者 split 模型不同；本票只重用 permutation_oracle`；觸發：事件切分與 IC 切分統一票；登記處：registry。
