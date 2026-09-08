brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R2
family: grok
findings-round: R2
標的：`docs/EVTWARMUP_SPEC.md`（R1 修訂）、`docs/EVTWARMUP_TODO.md`、`docs/TFWINDOW_SPEC.md`（仍未實作；HEAD=`1b7ad3ea`）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| 三份 template PASS | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → 三條 TEMPLATE PASS, rc=0 |
| 改前 golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`；sha256=`af73d325…` |
| R1 V1–V6 已寫進三份文件 | **fact-verified** | `git diff b96428f2..HEAD -- docs/EVTWARMUP_SPEC.md docs/EVTWARMUP_TODO.md docs/TFWINDOW_SPEC.md` |
| 方案 B 下無「只看 status 決策」消費者 | **fact-verified（決策端）／殘留（展示端）** | `grep -rn pass_class`：寫入僅 `_annotate_root_status_and_pass_class`；決策不依字面。展示端 `MarginalICTable` 仍寫死 Full-sample → 見 P2-02 |
| `ICSummaryTable` 對 `icir=null` 不炸 | **fact-verified** | `formatFinite`／排序 key 對非有限回 `'--'`／`-inf`（`ICSummaryTable.tsx:54-56,93`） |
| Task 1.2 `event_conditional`＝consumed 且在 stage3 後 | **assumption 當可執行細節** | TODO 字面「切分後、預檢後」指向 precheck 變量／stage3 前 → P0-01 |
| Task 2.1 已列全 ICIR 排序消費端 | **assumption 被推翻** | SPEC §C-6 點名 top-features；TODO 未列 `get_top_features`；實跑 None 排序 TypeError → P1-01 |

---

## 1a／1b — R1 原提出方（grok）逐條 CLOSED／OPEN

| R1 ID | 判定 | 文件位置（閉合證據） | 閉合有無新矛盾 |
|---|---|---|---|
| `GROK-R1-P0-01` | **CLOSED** | SPEC §C-4／§G：`analysis_status=="degraded_full_sample"`＋`reason=="insufficient_test_events"`＋`fit_mode=="train_mask"`；撤回第三值；`EW-RESID-4` | 無（與 `_resolve_root_status` 兩值一致） |
| `GROK-R1-P0-02` | **CLOSED** | SPEC §C-3 兩段判；TODO §0／Task 1.1 雙 helper＋驗證 (c)(d)(e)；mutation M2–M4 | 分流本身已閉；**地板判定**另開 P0-01 |
| `GROK-R1-P1-01` | **CLOSED** | 隨方案 B：survivor／TS／normalize **一字不改**（SPEC §C-4；TODO 1.2） | 無 |
| `GROK-R1-P1-02` | **CLOSED（主標的 DegradedBanner）** | TODO Task 1.2：banner 依 reason 分主標、vitest 釘不含 Full-sample；`pass_class` notes＋`EW-RESID-4` | 次表面 `MarginalICTable` 未列 → 新 P2-02，不重開本條 |
| `GROK-R1-P2-01` | **CLOSED（`_score_value`／tiebreaker）** | Task 2.1：呼叫端 `tiebreaker="ic_mean"`；`redundancy_filter.py` 不改 | top-features 排序洞另開 P1-01 |
| `GROK-R1-P2-02` | **CLOSED（層級標註）** | TFWINDOW §G 新子彈：引擎層 vs 接線主 gate；TODO 3.1 mutation M9 | 與舊「重算期望鍵」子彈互斥 → 新 P2-01 |
| `GROK-R1-P2-03` | **CLOSED** | SPEC §C-8／TODO 1.2：`reasons.oos_downgrade` 分類鍵＋既有 8＋新值 | 無 |

**1b 新矛盾摘要**：R1 七條對原缺陷均已對位關閉；本輪新問題來自「閉合後仍可照字面做錯」的執行歧義（地板時序、ICIR 消費端漏列、TFWINDOW §G 舊句殘留），非 R1 處置自打嘴巴。

---

## 必答（成對）

### 2a／2b 方案 B 與 status 字面

- **2a**：決策／契約消費端（survivor validate、normalize、TS union）**只認兩值**，不再有第三值撞牆；`pass_class` 寫入仍是 `oos_guarantees` 鏡像（`:1570-1571`），**不**另做 fit 範圍決策。會誤導的是**展示**：`DegradedBanner` 主標已規定依 reason 改（TODO 1.2）；`MarginalICTable.tsx:62` 仍寫死「Full-sample research-only」並顯示 `pass_class`（見 P2-02）。未發現 export／survivor 依 status 字面**隱藏 holdout 已套用**之事實的決策分支。
- **2b**：最小修法仍在本票文案／notes——擴 banner 同類改 `MarginalICTable` 主句為「非 OOS 保證」＋可選附 reason；**不必**擴 `analysis_status` 枚舉（與 `EW-RESID-4`／方案 B 一致）。

### 3a／3b 兩段分流

- **3a 仍可繞？** 就 §C-3／Task 1.1 兩 helper＋(c)(d)(e)／M2–M4 而言，R1 三反例**不可再靠 `is not None` 繞過**。殘餘風險不在分流鍵，而在 **Task 1.2 地板誤用 precheck 真值**（P0-01）：不會逃 bar gate（stage4 consumed=False 仍套 bar），但會把主線 holdout **錯標**成 `insufficient_test_events`。
- **3b 誤擋合法事件 run？** 設計下不會：34 事件＋enabled 預檢豁免；fallback 重跑／scan cube 各自判定（TODO 1.1 邊界②③）。誤擋風險在寫太窄（只看 enabled）——已禁。

### 4a／4b ICIR

- **4a**：Task 2.1 已列 `_apply_thresholds`、stage6 呼叫端 tiebreaker、`ic_reporter` 三處排序、事件路徑 `icir→None`。**未列** `ICFilterOrchestrator.get_top_features`（`:2895-2907`，同款 `item.get(sort_by, -inf)`）；api `/ic/summary` 的 `_icir_key` 與 service `_sort_artifact_rows` 已自洽。survivor `_f()` 已吃 None。⇒ 消費端**未列全**（P1-01）。
- **4b**：reporter 改 `_finite_or_neg_inf` 後，全域既有**有限** icir 排序鍵不變（SPEC Task 2.1 自述）；NaN 仍非有限→`-inf`，與現況 `nan` 比較行為不同但全域 golden 路徑值若皆有限則順序不變。事件路徑才大量 None。

### 5 ≥10× 複雜？

**無。** 分流兩 helper＋地板一欄＋跳過 icir_min＋呼叫端 tiebreaker；TFWINDOW 單點 `set_timeframe`。

### 6 可進 B1？

**需修補後派工。** P0-01（地板 predicate／時序）未釘死前，Agent 照 TODO「預檢後＋event_conditional」會在 stage3 棄條件後把主線 OOS 標成 degraded。P1-01 未補則事件路徑 `get_top_features`／deep-analysis 選特徵 TypeError。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | TFWINDOW §G「不改期望鍵」vs 舊「重算」→ P2-01；TODO §0 引 §C-7 談全域禁新鍵（實為 §C-2／§C-7 揭露）輕微 |
| 2 | 漏項 | Task 2.1 漏 `get_top_features` → P1-01；Task 1.2 未釘地板於 stage3 後／consumed → P0-01 |
| 3 | 不可測 | §G／mutation／探針可證偽；建議補 mutation：棄條件後不得寫 `insufficient_test_events` |
| 4 | quant | W2 方向仍正確；地板 30＝`EW-RESID-3` 成立 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 兩值方案正確；展示殘留 P2-02 |
| 9 | 測試 | M2–M4 形狀對；缺「棄條件＋地板」反例 |
| 10 | Agent 可執行 | 地板時序字面歧義＝P0；其餘 Task 偽碼足夠 |
| 11 | 短命工 | 無（`ic_window_disclosure` B2 擴範圍已登記） |

§N：`EW-RESID-1..4`／`TW-RESID-1` 三值理由成立；無應收回為 Task。

---

## GROK-R2-P0-01

**斷言**: Task 1.2 地板若依 TODO 字面在「切分後、預檢後」用預檢之 `event_conditional`（`bool(values) and enabled`）寫入 `oos_downgrade.reason=insufficient_test_events`，則 stage3 隨後因 `n_events < min_events` 棄條件（`label_source=mainline_return_N`）後，主線 holdout 仍可能成功，但 root 已被標成 `oos_guarantees=false`／`degraded_full_sample`——假降級；SPEC／TODO 未強制地板使用 `_is_event_conditional_consumed` 且置於 stage3 之後。

**碼證**: TODO Task 1.2：「切分後、預檢後：`if event_conditional and split_context["test_events"] < ...`」；現碼序 `precheck:1147` → `stage3:1193` → 棄條件 `:3311-3324`（`label_source=mainline_return_N`）→ mask 重算 `:1209` → stage4；Task 1.1 驗證(e)只釘 stage4 仍套 bar，**未**釘地板不火。RECHECK: 單測 values 非空＋enabled＋`n_events < min_events`＋測試段 bar 充足 ⇒ 断言 `oos_downgrade is None`（或 reason≠`insufficient_test_events`）且 `analysis_status=="ok_oos"`（或僅有 `conditional_ic.unavailable`）；mutation：地板誤用 precheck 真值 ⇒ 該案紅。

**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf；docs/EVTWARMUP_SPEC.md#c880b0f33f13；momentum/Analysis/ic_filter_orchestrator.py#644bd066457d

[BLOCKING] 信心度=High。會怎麼失敗：Agent 在 precheck 後立刻寫地板 → 棄條件主線被標成「事件不足 holdout」；UI／survivor 鏡像 `full_sample_research_only`，但數值其實是主線 OOS。修法：SPEC／TODO 明訂地板判定＝`_is_event_conditional_consumed(event_info)` 且**僅**在 stage3 成功留在事件路徑之後；棄條件路徑禁止寫 `insufficient_test_events`；補驗證＋mutation。

---

## GROK-R2-P1-01

**斷言**: SPEC §C-6／Task 2.1 要求列全 ICIR 消費端並安全化，但 TODO 只改 `ic_reporter` 三處排序；`ICFilterOrchestrator.get_top_features`（`:2895-2907`）仍 `key=item.get(sort_by, -inf)`——鍵在值為 `None` 時 TypeError；事件路徑 summary 改寫 `icir=None` 後，`api/routes/ic_analysis.py`／`ic_analysis_service._resolve_selected_features` 呼叫會炸。

**碼證**: 實跑 `sorted([{"icir":None},{"icir":0.5}], key=lambda i: i.get("icir", float("-inf")))` → `TypeError`; `get_top_features` 原文同形；對照 api `_icir_key`（`:792-799`）與 `_sort_artifact_rows`（`:1854+`）已 None-safe。RECHECK: TODO 補檔案＋單測 `_finite_or_neg_inf` 用於 `get_top_features`；事件 34 路徑呼叫 `get_top_features(sort_by="icir")` 不 raise。

**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13；docs/EVTWARMUP_TODO.md#b60b4a88a8cf；momentum/Analysis/ic_filter_orchestrator.py#644bd066457d

[MAJOR] 信心度=High。修法：Task 2.1 檔案表加入 `get_top_features`（重用 `_finite_or_neg_inf` 或與 api `_icir_key` 同形）；驗證事件路徑 deep-analysis／top-features 端點不 500。不必改 survivor（`_f` 已安全）。

---

## GROK-R2-P2-01

**斷言**: TFWINDOW §G 同時寫「`test_oos_ic_rolling_warmup`＝引擎層回歸（保留、**不改期望鍵**）」與舊句「該測之 `window_5` 類斷言依 fixture 週期**重算**」——Agent 無法同時遵守；TODO 3.1 與新句一致、與舊句衝突。

**碼證**: `docs/TFWINDOW_SPEC.md` §G 相鄰兩子彈；該測直呼 `_stage4_ic_calculation` 且 metadata 帶 `timeframe=1h` 但不經 `set_timeframe`（`test_ic_1a_cut1_oos.py:129-155`）⇒ 期望鍵本就不隨 fixture 換算。RECHECK: 刪或改寫舊「重算」句，只留引擎層／主 gate 分工。

**來源摘要**: docs/TFWINDOW_SPEC.md#27b6720e2177

[MINOR] 信心度=High。修法：刪 §G 舊「重算期望鍵」句（或改成「B2 不改此測期望；換算驗收只在 `test_tfwindow.py`」）。

---

## GROK-R2-P2-02

**斷言**: Task 1.2 誠實性只改 `DegradedBanner` 主標；同頁 `MarginalICTable` 在 `oos_guarantees=false` 時仍寫死「Full-sample research-only」（`:62`），方案 B 下 `insufficient_test_events`（holdout＋`train_mask`）會再顯示 Full-sample 字面。

**碼證**: `MarginalICTable.tsx:57-63`；TODO 1.2 檔案表無此元件。RECHECK: vitest 對 `pass_class=full_sample_research_only`＋事件不足 reason 之頁面，主句可不含 Full-sample，或改「非 OOS 保證」並顯示 reason。

**來源摘要**: frontend/src/components/ic-analysis/MarginalICTable.tsx#c8a4bd68ad04；docs/EVTWARMUP_TODO.md#b60b4a88a8cf

[MINOR] 信心度=Medium（影響＝次要面板）。修法：Task 1.2 加一行改文案（不必改 `pass_class` 枚舉）；或明示本表面只鏡像 pass_class、主誠實性以 DegradedBanner 為準並接受殘留（若選後者須寫進 §N／notes，否則 Agent 不知可省略）。

---

## Verdict：需修補後派工

R1 grok 七條均 **CLOSED**；本輪新 **P0-01**（地板時序／predicate）與 **P1-01**（`get_top_features`）擋住 B1。P2 兩條不阻開工但建議同批改文件。方案 B／兩段分流主體正確；無 ≥10× 複雜；§N 理由成立。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` | TEMPLATE PASS, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | `與既有 golden 相同？ **True**`；event `rolling_warmup_insufficient`；global `ok_oos` |
| `git diff b96428f2..HEAD -- docs/EVTWARMUP_SPEC.md docs/EVTWARMUP_TODO.md docs/TFWINDOW_SPEC.md` | V1–V6 對位改寫可見 |
| `venv/bin/python -c '…sorted icir=None…'` | `TypeError`（證 P1-01） |
| `grep -rn pass_class momentum api frontend/src --include=*.py --include=*.ts --include=*.tsx` | 決策寫入單一；`MarginalICTable` 展示 Full-sample |
| `grep -n formatFinite frontend/src/components/ic-analysis/ICSummaryTable.tsx` | null → `'--'`，不顯示 NaN 字串 |

未跑 `pytest tests/governance`（brief 禁）。未改碼／未改文件。

---

ASSUMPTIONS_VERIFIED: 模板三 PASS；探針 True；R1→文件 diff 對位；pass_class／ICSummaryTable／get_top_features None 排序均實跑
TESTS_RUN: 見 VERIFY 表；未跑產品 pytest（review-only）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（本產出不改碼）
產出檔: handoffs/20260908-evtwarmup-x-review-r2-grok.md

STATUS: DONE
