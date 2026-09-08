# Reconcile — 20260908-evtwarmup-x-review-r2

**來源** 20260908-evtwarmup-x-review-r2-codex.md, 20260908-evtwarmup-x-review-r2-composer.md, 20260908-evtwarmup-x-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

R1 各家原提出條目：codex 4 條中 P1-01 CLOSED、P1-02 枚舉面 CLOSED、P1-03／P1-04 OPEN（見 X3／X5）；composer 六條全 CLOSED；grok 七條全 CLOSED。
本輪新增 1 P0／7 P1／5 P2，**全部為文件層**；三家皆「需修補後派工」。P1 依制度**必修**（非可選），下列逐條處置皆已寫入 SPEC／TODO／TFWINDOW SPEC。

### X1 🔴 P0 — 地板判定時序與 predicate（`GROK-R2-P0-01`、`COMPOSER-R2-P1-01`）
預檢真值（stage3 前）寫地板 ⇒ 棄條件主線被假降級。**處置**：SPEC §C-4／Task 1.2、TODO Task 1.2：判定只在 stage3 之後、predicate＝`_is_event_conditional_consumed(event_info)`，`test_events` 以實際被消費事件列重算；棄條件路徑禁寫；新增驗證 (e′)＋mutation M9。

### X2 — P1 `oos_downgrade` 寫出點測試鎖 count==2（`COMPOSER-R2-P1-02`）
**處置**：SPEC §C-4、TODO Task 1.2：改為三寫出點＋優先序行為測試（fallback 富版 > analyze 地板 > annotate），測試改名更新，不得同時要求 count==2。

### X3 — P1 `get_top_features` ICIR 排序（`CODEX-R2-P1-01`、`GROK-R2-P1-01`、`COMPOSER-R2-P2-01`；關 codex R1 P1-03）
**處置**：SPEC §C-6／Task 2.1、TODO Task 2.1：`get_top_features` 排序 key 用 `_finite_or_neg_inf`；事件路徑 `sort_by="icir"` 不 raise 之測試；mutation M10。

### X4 — P1 主委 `allow_nan` 事實錯（`CODEX-R2-P1-02`）
codex 實跑推翻：`save_report` 未禁 NaN，會落成非法 JSON `NaN`，前端 `response.json()` 炸。**處置**：SPEC §A 補正 FACT-RECEIPT（明記被推翻）；§C-6／Task 2.1：`_sanitize_summary_table_for_json` 轉 `None`＋`json.loads(parse_constant=<raise>)` gate；mutation M11。主委再犯「引用行號當事實未實讀該函式」——記入 §A。

### X5 — P1 TFWINDOW §G 兩套 oracle 互斥（`CODEX-R2-P1-03`、`GROK-R2-P2-01`；關 codex R1 P1-04）
**處置**：TFWINDOW §G 改單一套：既有欄位投影 sha256 不變＋整份重凍且 `jq del(.metadata.ic_window_disclosure)` 後等於舊 golden；刪「重算期望鍵」舊句，`test_oos_ic_rolling_warmup` 期望不改。

### X6 — P1 其他「Full-sample」字面消費端（`CODEX-R2-P1-04`、`COMPOSER-R2-P2-02`、`GROK-R2-P2-02`）
**處置**：SPEC §C-4、TODO Task 1.2：`MarginalICTable.tsx`、`ic_reporter.generate_ai_json` 依 reason 分文案＋測試；仍不擴 status 枚舉。

### X7 — P2 TS `ICFeatureInfo.icir` 型別（`CODEX-R2-P2-01`）
**處置**：Task 2.1：`number | null`＋`ICSummaryTable.test.tsx` null 顯示／排序 regression。

Verdict: 需修補後派工——X1–X7 已全部改進文件（三份 template_check PASS）；進 R3 閉合輪由原提出方逐條 CLOSED 後派 B1。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**: Task 2.1 未列 `ICFilterOrchestrator.get_top_features` 這個 ICIR 消費端；事件路徑混有 `None` 時 production `/top-features` 會排序崩潰。
**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2895-2908` 仍 `key=lambda item: item.get(sort_by, -inf)`；`api/routes/ic_analysis.py:496-513` 直接呼叫；實跑 `venv/bin/python -c '...get_top_features()'` → `TypeError: '<' not supported between instances of 'float' and 'NoneType'`。
**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf;momentum/Analysis/ic_filter_orchestrator.py#644bd066457d;api/routes/ic_analysis.py#95216b9ddbf0；正文：[MAJOR] 信心度=10/10；補入 TODO 檔案、finite fallback 與事件／混合 None 測試，並涵蓋 API caller。
## CODEX-R2-P1-02
**斷言**: SPEC/TODO 把 `ic_reporter.py:864 allow_nan=False` 當成 `save_report` 事實，但實際 `save_report` 未禁 NaN，非有限 ICIR 可落成非標準 JSON `NaN`。
**碼證**: `momentum/Analysis/ic_reporter.py:812-837` 的 `save_report` 用 `json.dump` 未傳 `allow_nan=False`；`_sanitize_summary_table_for_json:920-934` 不處理 `icir`；實跑 save_report probe stdout=`..."icir":NaN`，而 `frontend/src/hooks/useICAnalysis.ts:37` 直接 `response.json()`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13;docs/EVTWARMUP_TODO.md#b60b4a88a8cf;momentum/Analysis/ic_reporter.py#73006e6bb658；正文：[MAJOR] 信心度=10/10；TODO 須明定 producer/serializer 將非有限 icir 轉 JSON null，並以 raw `json.loads`＋`allow_nan=False` gate 驗收，不能以「不 raise」代替。
## CODEX-R2-P1-03
**斷言**: TFWINDOW §G 同時要求 12h 整份 canonical sha256／逐鍵不變，又要求新增 `ic_window_disclosure` 鍵並重凍；兩個 acceptance oracle 互斥。
**碼證**: `docs/TFWINDOW_SPEC.md:26,29,31` 分別寫「整份報告 sha256 逐位元組不變」「全域報告新增鍵」「12h run 逐鍵不變」；TODO `:58,60` 又要求新增鍵後重凍。正文：[MAJOR] 信心度=10/10；改成「數值／既有欄位 projection 不變＋canonical 新 hash」或排除揭露鍵，並只保留一套可執行 gate。
**來源摘要**: docs/TFWINDOW_SPEC.md#27b6720e2177;docs/EVTWARMUP_TODO.md#b60b4a88a8cf；
## CODEX-R2-P1-04
**斷言**: 方案 B 的 `degraded_full_sample`＋`pass_class` 仍有未列消費端會把「holdout 已套用但事件不足」誤說成 full-sample fallback。
**碼證**: `frontend/src/components/ic-analysis/MarginalICTable.tsx:48-63` 直接顯示 `Full-sample research-only`；`momentum/Analysis/ic_reporter.py:586-604,624-638` 對任一 degraded 無條件輸出 `full-sample fallback`；實跑 `generate_ai_json` with reason=`insufficient_test_events` → 第一條 warning 仍為該字面。
**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13;docs/EVTWARMUP_TODO.md#b60b4a88a8cf;frontend/src/components/ic-analysis/MarginalICTable.tsx#c8a4bd68ad04;momentum/Analysis/ic_reporter.py#73006e6bb658；正文：[MAJOR] 信心度=10/10；最小修法仍在本票：補 reason-aware 文案／notes、列出上述 export／marginal consumer 與測試，不擴 status 枚舉。
## CODEX-R2-P2-01
**斷言**: 事件 summary 的 `icir=None` 與前端承諾不一致：`ICSummaryTable` runtime 已安全顯示 `--`，但 `ICFeatureInfo.icir` 仍宣告為 non-null `number`，且無該 component 的 null regression test。
**碼證**: `frontend/src/lib/types.ts:2039-2045` 為 `icir: number`；`ICSummaryTable.tsx:49-59,91-105,386-388` 以 finite guard 顯示 `--`；`frontend/src/components/ic-analysis` 無 `ICSummaryTable` test。正文：[MINOR] 信心度=9/10；把 API type 改為 `number|null` 並釘 null／NaN 顯示與排序測試；目前 runtime 顯示本身已驗證不炸。
**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf;frontend/src/lib/types.ts#7612e6b1d329;frontend/src/components/ic-analysis/ICSummaryTable.tsx#2e94c8c4c522；
R1 disposition（原提出方 CODEX）：`CODEX-R1-P1-01` CLOSED；`P1-02` 僅 status 枚舉 CLOSED、消費語意殘留見本輪 P1-04；`P1-03` OPEN（top-features／export 漏列）；`P1-04` OPEN（TFWINDOW §G 仍矛盾）。1b 新矛盾＝P1-02 false receipt、P1-03 golden oracle、P1-04 consumer、P2-01 type。
必答：2a 有，P1-01/P1-02/P1-04；2b 文案、serializer gate、consumer notes/test，仍不擴枚舉。3a 兩段 truth table 對 `{}`、disabled、`n_events<min_events` 均 fail-closed；3b fallback rerun／scan cube 每格判定不誤擋（文件已明定）。4a 未列全；4b 有限 ICIR 下 reporter 相對順序不變，但 endpoint/export 仍需釘。5 無 ≥10× 複雜；6 不可進 B1。
類別(1–11)：1=P1-03/04；2=P1-01/04；3=P1-02/03；4=無公式疑慮；5=無；6=無；7=無；8=P1-02/P2-01；9=P1-01/02/P2-01；10=P1-01/03；11=無。
§0：fact-verified＝三 template PASS、baseline probe rc=0 且 `與既有 golden 相同？ True`、top-features TypeError、save_report raw `NaN`、pass_class grep 命中 MarginalICTable；assumed＝未實作後的新增 artifact／測試尚未存在。
TESTS_RUN：三個 `bash scripts/template_check.sh ...` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0／sha256 `af73d325e0c4`／True；兩個最小 Python probes 分別實證 TypeError 與 raw `NaN`。
FAILURES_SEEN：none（未跑 `pytest tests/governance`）。
SCOPE_CHANGES：唯讀審查；未改碼／文件／data_cache；產出=`handoffs/20260908-evtwarmup-x-review-r2-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT：本次未修改；指出預定 JSON null、TS nullable、golden hash oracle 之契約影響。
STATUS: DONE
## COMPOSER-R2-P1-01

**斷言**: Task 1.2 地板判定寫在「切分後、預檢後」且條件為未定義的 `event_conditional`，實作者若在 stage3 前執行，會對 Task 1.1 驗證 (e)（values 非空＋enabled 但 `n_events<min_events` ⇒ `label_source=mainline_return_N` ⇒ stage4 仍 bar skip）先寫 `oos_downgrade.reason=insufficient_test_events`／`ic_train_test_split.oos_guarantees=false`，與「棄條件 IC 走主線」矛盾。

**碼證**: `docs/EVTWARMUP_TODO.md` Task 1.2「切分後、預檢後：`if event_conditional and split_context["test_events"]<...`」；同檔 Task 1.1 驗證 (e)；`analyze` 現序：precheck（`:1147`）→ stage3（`:1193`）→ stage4（`:1228`）。RECHECK: 對照若地板寫在 `:1163` 前 vs stage3 後＋`_is_event_conditional_consumed(event_info)`，case (e) 是否仍僅 bar skip。

**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf

[MAJOR] 信心度=High。修法：Task 1.2 改「stage3 之後、stage4 之前」且條件＝`_is_event_conditional_consumed(event_info)`（與 §C-3 stage4 段一致）；`split_context["test_events"]` 在 stage3 後重算後再比 `min_test_events`。SPEC Task 1.2 同步一句。

---

## COMPOSER-R2-P1-02

**斷言**: Task 1.2 要求在 `analyze` 新增 `metadata["oos_downgrade"]={reason:insufficient_test_events,...}` 第三寫出點，但驗收要求 `pytest tests/api/test_gap3_oos_downgrade.py -q` 全綠且僅聲明 `test_resolve_root_status_behaviour_is_baseline` 不改——現有 `test_oos_downgrade_has_exactly_two_write_sites_with_precedence` 以 `src.count('"oos_downgrade"] = ')==2` 鎖死，實作後必紅。

**碼證**: `tests/api/test_gap3_oos_downgrade.py:29-42`；`momentum/Analysis/ic_filter_orchestrator.py` 現僅兩處（`:1418` fallback、`:1564` annotate 補寫）；TODO Task 1.2 驗證「`test_gap3_oos_downgrade.py -q` rc=0（基線不改）」。RECHECK: 假想 `analyze` 加第三處 `"oos_downgrade"] = ` → 該測試 count==3 失敗。

**來源摘要**: docs/EVTWARMUP_TODO.md#b60b4a88a8cf

[MAJOR] 信心度=High。修法：TODO 1.2 驗證表明列更新 `test_oos_downgrade_has_exactly_two_write_sites` 為「三寫出點＋優先序」（fallback 富版 > analyze 事件地板 > annotate 缺席補寫），或改為行為測試「富版不被覆蓋」；不可同時要求 count==2 與第三寫出點。

---

## COMPOSER-R2-P2-01

**斷言**: SPEC §C-6 要求「survivor／top-features／export 之 ICIR 讀取點由 TODO 逐一列出」，但 Task 2.1 檔案表未列 `ic_filter_orchestrator.get_top_features`；事件路徑 summary `icir=None` 時 `sorted(..., key=lambda item: item.get("icir", float("-inf")))` 取到 `None`（鍵存在）⇒ Python 3 `TypeError`，API `get_top_features`／export 可能炸。

**碼證**: `docs/EVTWARMUP_SPEC.md` §C-6；`docs/EVTWARMUP_TODO.md` Task 2.1 檔案表（無 `get_top_features`）；`ic_filter_orchestrator.py:2903-2907`；`api/routes/ic_analysis.py:497-508`。RECHECK: 事件路徑報告含 `icir: null` 呼叫 `get_top_features(sort_by="icir")` 是否 raise。

**來源摘要**: docs/EVTWARMUP_SPEC.md#c880b0f33f13

[MINOR] 信心度=High。修法：Task 2.1 補 `get_top_features` 排序 key 用 `_finite_or_neg_inf`（或事件路徑預設 `sort_by="ic_mean"`）＋單測；或 §C-6 降級聲明「top-features API 事件路徑禁用 icir 排序」。

---

## COMPOSER-R2-P2-02

**斷言**: Task 1.2 只規範 `DegradedBanner` 依 reason 分標，但 `MarginalICTable`（`oos_guarantees===false` ⇒ 固定「Full-sample research-only」）與 `ic_reporter.generate_ai_json`（degraded 一律插入「full-sample fallback」警語）未列入修改；holdout+`insufficient_test_events` 使用者在邊際 IC／AI 匯出仍見 full-sample 字面，與 consult W2 部分矛盾。

**碼證**: `frontend/src/components/ic-analysis/MarginalICTable.tsx:48-62`；`momentum/Analysis/ic_reporter.py:598-604`；Task 1.2 檔案表僅 `DegradedBanner.tsx`。RECHECK: 模擬 `oos_guarantees=false`＋`oos_downgrade.reason=insufficient_test_events` 渲染 MarginalICTable／generate_ai_json 輸出字串。

**來源摘要**: frontend/src/components/ic-analysis/MarginalICTable.tsx#948bd7a9a5dd

[MINOR] 信心度=Medium。修法：Task 1.2 增 MarginalICTable（讀 `oos_downgrade.reason` 或 `fit_mode`）與 `generate_ai_json` degraded 文案分流；或 EW-RESID-4 延伸登記「非 banner 消費端仍誤名」並接受研究用途風險。

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

