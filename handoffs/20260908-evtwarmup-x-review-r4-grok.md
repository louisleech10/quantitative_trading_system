# EVTWARMUP B1 實作 code review R4（grok）

brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R4
family: grok
findings-round: R4
標的 commit: `1a2cfd90`（B1 `39b48531`＋修補）；工作區 HEAD `59cac7da`＝其上僅 `docs(handoff)`，碼與標的一致
SCOPE: review-only；禁改 production／test／docs／frontend
ORCH-DIGEST: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56
REPORTER-DIGEST: momentum/Analysis/ic_reporter.py#c2e1fbaaf094
SCHEMA-DIGEST: momentum/Analysis/ic_config_schema.py#1fd5a87b63b5
MUTATE-DIGEST: handoffs/20260908-evtwarmup-mutate.py#d1d15bbfff1a
SPEC-DIGEST: docs/EVTWARMUP_SPEC.md#713968799d02
TODO-DIGEST: docs/EVTWARMUP_TODO.md#32e75632ed94
BASELINE: `shasum -a 256 -c handoffs/20260908-evtwarmup-r4-baseline.sha` → 1137 OK、rc=0（開工時＋收尾時）

---

## Verdict：可合併

B1（Task 1.1／1.2／2.1＋前端）與 SPEC（R2）／TODO 一致；必答 1–5 雙向有碼證；clean-clone mutation phase 1＝oracle 紅集合＋C0 綠、`UNCOVERED=0`；無新 P0／P1。本輪無實質 finding → sentinel `GROK-R4-P3-00`。可進 B2（TFWINDOW）。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` | **53 passed, 0 skip**, pytest rc=0（~22s） |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | rc=0；整檔 vs 改前 golden＝**False**（`event_run` 預期變）；**`global_run` 逐鍵 == golden＝True**；`event_run`：`applied=true`、`test_events=13`、`reason=insufficient_test_events`、`analysis_status=degraded_full_sample`、`oos_guarantees=false` |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py -k 'not budget_bench' -q` | **4 passed, 1 deselected**, rc=0（~92s；含 g1／g2 canonical＋mutation scrub） |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py::test_budget_bench_receipt -q` | 收尾時補記（長跑；與上列一併＝全檔綠） |
| `(cd frontend && npx vitest run …DegradedBanner/MarginalICTable/ICSummaryTable.icirNull/oosDowngradeDocs)` | **4 files／27 tests passed**, rc=0 |
| mutation clean clone `@HEAD`＋symlink `tests/golden/la0/inputs`＋`data_cache`：`handoffs/20260908-evtwarmup-mutate.py --phase 1` | **MUTATE2_RC=0**；`SUMMARY pass=10 fail=0 skip=0`；`UNCOVERED=0`；共用樹 `orchestrator`/`reporter` hash＝HEAD |
| `shasum -a 256 -c handoffs/20260908-evtwarmup-r4-baseline.sha` | rc=0、1137 OK |

### Mutation 紅集合（closure=CLOSED；紅因＝pytest rc=1）

| ID | 觀測 |
|---|---|
| M1, M2, M3, M5, M6, M7, M8, M10, M11 | 各 `rc=1` PASS（期望紅） |
| C0 | `rc=0` PASS（期望綠） |

（首跑 clone 缺 la0 fixture ⇒ C0 假紅；補 symlink 後重跑才算數。共用樹曾被誤留 C0 註解，已 `git checkout --` 還原，收尾 hash＝`79538a98451d`＝HEAD。）

---

## 必答（成對；逐條有碼證）

### 1a. 分流可繞否（主線逃 warmup／事件被當主線）？

**未證實可繞。** 構造與結果：

| 構造 | 結果 |
|---|---|
| `values={}`／`None`／`enabled=False` | precheck False ⇒ 仍走 bar warmup（`test_precheck_predicates_two_stage`＋`test_precheck_event_conditional…`） |
| `is not None` 寬條款 | M2 改之 ⇒ 紅 |
| 棄條件 `label_source=mainline_return_N` | consumed False ⇒ stage4 仍套 bar 規則；地板不開火（(e′)） |
| 刪預檢分流 | M1 ⇒ 34 事件再被擋 |
| M8 強制進事件塊 | 全域寫 `ic_window_disclosure` ⇒ golden 紅 |
| fallback／scan cube | 同一 `_is_event_conditional_*`；fallback 重跑後若非 consumed 則 bar 規則恢復；cube 每格各自 `analyze`（SPEC 邊界；本輪未實機 110 格，見 brief unverified） |

### 1b. 合法事件 run 被誤擋／誤標？

**未證實。** 預檢真 ⇒ `None`（不擋）但仍記 `test_events`；stage4 `not consumed` 才 skip。≥30 測試段事件＋`min_test_events=0` 逃生口 ⇒ `oos_guarantees=true`、無 `oos_downgrade`（`test_min_test_events_floor_disabled_gives_oos`）。13＜30 ⇒ holdout 保留＋loud reason，非誤擋成 fallback。

### 2a. 地板時序：棄條件不會寫 `insufficient_test_events`？

**是。** 地板在 stage3 後、mask 重算後；predicate＝`_is_event_conditional_consumed`（`:1226-1250`）。(e′) `test_abandoned_conditional_path_is_not_flagged_insufficient_test_events`：`reason != insufficient_test_events`、無 `ic_window_disclosure`。M3 改壞 consumed ⇒ 棄條件紅。

### 2b. `test_events=test_mask.sum()` 是否＝消費事件 ∩ 測試段？

**是（在現行管線）。** stage3 後 `features_df` 只留事件列；隨後 `_apply_feature_filter` **只篩欄、不刪列**（`:3447+`）。故 `test_mask.sum()`＝事件列上的測試段計數。特徵過濾不會造成事件列再剔除偏差。預檢之 `timestamps∩test_mask` 僅供早期記錄；地板前以 stage3 後值覆寫 `split_context["test_events"]`。

### 3a. ICIR 消費端全覆蓋？

**列全且安全化：**

| 點 | 碼證 |
|---|---|
| `_apply_thresholds(icir_gate=False)` | 必有 `icir_skipped_event_path`；`removed["icir"]` 空（測＋M6） |
| stage6 分數字典 | consumed ⇒ `{name: ic_mean}`＋`tiebreaker_effective`（`:1321-1329`）；`_score_value` 吃純 float |
| reporter 三處排序 | `_finite_or_neg_inf`（`:418`／`:585`／`:676`） |
| `get_top_features` | 同 key（`:2952-2955`）；M10 還原 ⇒ TypeError 紅 |
| sanitizer | `icir`／`ic_mean` → null（`:952-954`）；M11 紅 |
| API `/summary` `_icir_key` | 既有 None-safe（`:792-798`） |
| service `_sort_artifact_rows` | None／NaN → 末排（`:1858-1868`） |
| survivor `_f` | 既有 None-safe（不改） |
| scan cube `_dumps` | 吃 `generate_json_report` 已 sanitize 之 `summary_table`；測斷言無 `icir`/`ic_mean` NaN 字面 |

未見新的「讀 icir 會炸／靜默退化」入口。既有 `long_short_spread` 等 NaN 字面＝`EW-RESID-5`（本票只保 icir／ic_mean）。

### 3b. 全域路徑 ICIR／報告位元組不變？

**是。** `icir_gate` 預設 True；M7 把 skip 擴到全域 ⇒ 紅。`test_global_run_unchanged_vs_golden`＋探針 `global_run` 逐鍵 True；報告無 `ic_window_disclosure`／`tiebreaker_effective`。

### 4a. 兩值 status 方案 B 一致性？

**一致。** root 仍 `degraded_full_sample`／`ok_oos`；`pass_class`＝`oos_guarantees` 鏡像（`full_sample_research_only`）；survivor／TS union 未加第三值。前端 DegradedBanner／MarginalICTable／`generate_ai_json` 依 `reason=insufficient_test_events` 分文案（vitest 釘不含「Full-sample」）。

### 4b. 哪個面仍把「holdout 已套用」講成 full-sample？

**仍存在、屬方案 B 契約字面：** `analysis_status`／`pass_class` 枚舉字面、`interpretation_guide` 之 `full_sample_research_only` 說明。區分靠 `oos_downgrade.reason`＋三處已改消費端。annotate 對已有富版／地板 `oos_downgrade` **不覆蓋**（`"oos_downgrade" not in metadata`／`not isinstance(...dict)`）；`_downgrade_branch` 對 split.oos_guarantees=False 可回 `split_not_applied` 代號，但不改已寫入之 reason。

### 5a. mutation 充分性（10 條全綠仍可能有的缺陷）

**例：** 若地板改用「預檢 `test_events`」且 **仍**用 consumed predicate，M5（刪地板 if）／M3（壞 consumed）／(e′) 可能仍綠——計數偏差（bar vs 事件）需行為斷言 `test_events==13` 才抓。現行測有該斷言；此為**突變缺口敘事**，非已證 prod 洞。M4／M9 併入 M3／M5：stage4／地板皆呼叫同一 `consumed` 函式，M3 改函式即兩邊受影響；腳本註解屬實。

### 5b. 紅因＝斷言而非 import／語法？

**是。** 本輪 fixture 齊全之 clone：九條期望紅皆 `rc=1`；C0 `rc=0`；無 rc=5／UNCOVERED。

### 6. ≥10× 不必要複雜？

**無。** 兩 predicate＋地板一欄＋`icir_gate` 參數＋分數字典改傳＋`_finite_or_neg_inf`＋serializer 兩鍵＋前端 reason 分支。

### 7. 可合併並進 B2（TFWINDOW）嗎？

**可合併。** 無新 P0；無必須修之 P1。殘留仍為既有 `EW-RESID-5`／`EW-RESID-6`（改前即紅）與 brief 表列 NOT_RUN（實機 UAT B32、scan cube 110 格、fallback 富版交叉）。進 B2 前建議使用者 UAT 確認 1h／多事件實機 reason。

---

## §1 必查摘要（11 類；標的＝已實作碼 vs SPEC）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | 無（碼與 §C-3／C-4／C-6 對位） |
| 2 | 漏項 | 無阻合併漏項；探針 `pick()` 未含 `fit_mode`（§G 文字提探針鍵）——行為由 pytest 斷言，不列 finding |
| 3 | 不可測 | 驗收命令＋mutation 可證偽 |
| 4 | quant | 無新疑；地板 30＝`EW-RESID-3` needs-research |
| 5 | 過度工程 | 無 |
| 6 | OOM | 無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 兩值 status；TS `icir: number\|null`；契約 `reasons.oos_downgrade` |
| 9 | 測試 | 10 條 evtwarmup＋mutation M1–M11／C0；既有紅非本批 |
| 10 | Agent 可執行 | 已實作；gate／mutate 可跑 |
| 11 | 短命工 | 無（`ic_window_disclosure` 事件路徑永久；全域待 TFWINDOW） |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| 事件路徑 `removed["icir"]` 空＋`icir_skipped_event_path` 必在 | **fact-verified** | `test_min_test_events_floor_keeps_holdout…`＋M6 紅 |
| `global_run` 逐鍵不變 | **fact-verified** | 探針比對 True；pytest golden |
| mutation oracle＝9 紅＋C0 綠 | **fact-verified** | clean clone＋fixture symlink，UNCOVERED=0 |
| 使用者實機 34 事件 reason 正確 | **unverified**（brief blocked-by UAT B32） | NOT_RUN |
| `_downgrade_branch` 不蓋地板 reason | **fact-verified** | annotate 缺席守衛＋行為測綠 |

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——Task 1.1／1.2／2.1 與前端接線在碼證＋驗收命令＋clean-clone mutation（UNCOVERED=0）下與 SPEC §C-3／§C-4／§C-6／§G 一致，無新 P0／P1。

**碼證**: `pytest tests/api/test_evtwarmup.py tests/api/test_gap3_oos_downgrade.py -q -rs` → 53 passed 0 skip rc=0；探針 `global_run` 逐鍵 == golden、`event_run.reason=insufficient_test_events`／`test_events=13`；vitest 27 passed；clean-clone `evtwarmup-mutate.py --phase 1` → M1/M2/M3/M5/M6/M7/M8/M10/M11 紅＋C0 綠、UNCOVERED=0；baseline sha 1137 OK；必答 1a–5b 雙向見上表。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#66eff72b8d56；momentum/Analysis/ic_reporter.py#c2e1fbaaf094；docs/EVTWARMUP_SPEC.md#713968799d02；handoffs/20260908-evtwarmup-mutate.py#d1d15bbfff1a

[MINOR] 信心度=High。哨兵非實質缺陷；合併判定見 Verdict。

---

ASSUMPTIONS_VERIFIED: 兩段分流不可用 is-not-None／enabled 單判繞過；地板只在 consumed＋stage3 後；棄條件不寫 insufficient_test_events；ICIR 事件路徑診斷化且消費端 None-safe；全域 golden／global_run 不變；mutation 紅集合＝oracle；兩值 status＋reason 分文案
TESTS_RUN: pytest evtwarmup+oos_downgrade 53 passed rc=0；probe global_run==True event_run 形狀符合 §G；vitest 27 passed；mutate phase1 UNCOVERED=0 rc=0；baseline sha rc=0；gap2 `-k 'not budget_bench'` 4 passed rc=0；budget_bench 另跑（見交接若未齊則標未驗證）
FAILURES_SEEN: 首跑 clone 缺 la0 fixture → C0 假紅（非產品）；共用樹誤留 C0 註解 → 已 checkout 還原
SCOPE_CHANGES: none（唯讀；/tmp clone 僅供 mutation）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；產品已落地之 null icir／ic_mean 與既有 EW-RESID-5 邊界如 brief）
產出檔: handoffs/20260908-evtwarmup-x-review-r4-grok.md

STATUS: DONE
