brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R3
family: composer
findings-round: R3
標的：`docs/EVTWARMUP_SPEC.md`（R2 修訂）、`docs/EVTWARMUP_TODO.md`、`docs/TFWINDOW_SPEC.md`（**仍未實作**）

## 被當成事實的未驗證假設（§0）

| 前提 | 裁定 | 覆核摘要 |
|---|---|---|
| 三份 template | **fact-verified** | 三條 `bash scripts/template_check.sh …` → TEMPLATE PASS, rc=0 |
| golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → sha256 `af73d325e0c4…`／`與既有 golden 相同？ **True**`, rc=0 |
| R2 X1–X7 已落檔 | **fact-verified** | `git diff d090b13c..HEAD -- docs/EVTWARMUP_*.md docs/TFWINDOW_SPEC.md` 252 行；§C-4／Task 1.2／Task 2.1／TFWINDOW §G 與 `handoffs/reconcile/20260908-evtwarmup-x-review-r2/synth.md` 逐條對照 |
| Task 1.1 與 1.2 之 `test_events` 並存 | **fact-verified（推翻 brief assumed）** | TODO 1.1 於 precheck 寫 `split_context["test_events"]`；TODO 1.2 明示「stage3 後**先重算**再比地板」；SPEC §C-4 同句——地板以 1.2 重算值為準，非矛盾 |
| scan_cube `_dumps` 與 reporter 一致 | **unverified（brief NOT_RUN）** | `scan_cube.py:71-73` 仍 `json.dumps` 無 `allow_nan`；依賴 Task 2.1 上游 `generate_json_report`→`_sanitize_summary_table_for_json` 產 `icir=null`；本輪未跑 cube 格 probe |
| `pass_class` 字面誤導 | **assumed（文件已收）** | EW-RESID-4 `user-ruling`；Task 1.2 已列 reason-aware 文案三處；`pass_class` 仍鏡像 `oos_guarantees` |

---

## 1a. R2 逐條 CLOSED／OPEN（COMPOSER 原提出方覆核）

| R2 ID | 裁定 | R2 修訂後碼證 |
|---|---|---|
| **COMPOSER-R2-P1-01** | **CLOSED** | SPEC §C-4「只在 stage3 之後、stage4 之前」＋predicate `_is_event_conditional_consumed`；TODO Task 1.2 同句＋驗證 **(e′)**；mutation M9 |
| **COMPOSER-R2-P1-02** | **CLOSED** | SPEC §C-4 三寫出點＋優先序；TODO 1.2 改名 `..._three_write_sites_with_precedence`、count==3；`test_resolve_root_status_behaviour_is_baseline` 仍不改 |
| **COMPOSER-R2-P2-01** | **CLOSED** | SPEC §C-6＋Task 2.1 檔案表列 `get_top_features`；TODO Task 2.1 同；mutation M10 |
| **COMPOSER-R2-P2-02** | **CLOSED** | SPEC §C-4／Task 1.2 列 `MarginalICTable.tsx`、`generate_ai_json`；TODO 1.2 檔案＋vitest 三檔；驗證主句不含「Full-sample」 |

**1b. 閉合是否製造新矛盾（SPEC↔TODO 逐句）**：**無 blocking 新矛盾**。分流／地板時序／寫出點／ICIR 消費端／Full-sample 文案／TFWINDOW 單一 oracle 兩份文件一致。**殘留觀測（非 finding）**：SPEC Task 2.1 驗證要求三序列化入口（`save_report`／`export_all` `:726`／`scan_cube._dumps`）皆 `parse_constant` gate；TODO Task 2.1 驗證節僅列 `save_report`——實作應以 SPEC 為準補驗，不阻 B1。

---

## 必答（成對 verdict）

### 2a. 地板 predicate／時序在 fallback 重跑與 scan cube 格內是否仍正確

**是。** SPEC §C-4／TODO 1.2：地板僅 `_is_event_conditional_consumed` 且 stage3 後；棄條件（`mainline_return_N`）禁寫 `insufficient_test_events`；**(e′)**＋M9 釘假降級。Task 1.1 邊界② fallback 重跑 predicate 重算；邊界③ scan cube「每格各自判定」、TODO 1.2 邊界⑤ reason 透傳不拒枚舉。

### 2b. 是否會誤標合法事件 run

**不會（照修訂版做）。** 34 測試段事件：precheck 豁免＋consumed 真仍走 holdout；13<30 才地板。case (e)／(e′)：`n_events<min_events`⇒`label_source=mainline_return_N`⇒地板 predicate 假⇒`ok_oos`＋`conditional_ic.unavailable`，不誤標 full-sample fallback。

### 3a. serializer gate＋`_finite_or_neg_inf` 是否覆蓋全部 ICIR 讀取點

**文件層已列全。** §C-6／Task 2.1：`_apply_thresholds`（跳過）、stage6 `tiebreaker=ic_mean`、reporter 三處排序、`get_top_features`、`_sanitize_summary_table_for_json`（擴 `icir`／`ic_mean`）、前端 `ICFeatureInfo.icir: number|null`。生產落盤主路徑：`generate_json_report`（`:323`）已呼叫 `_sanitize_summary_table_for_json` 後才 `save_report`（orchestrator `:1921`→`:4574`）。**驗收覆蓋**：TODO 應同步 SPEC 之三入口 `parse_constant` gate（見 1b 殘留觀測）。

### 3b. 全域順序／golden 是否不變

**是。** §C-2／§G `global_run` 逐鍵；B1 禁全域新增 metadata 鍵；Task 2.1「既有值皆有限⇒順序不變」＋`test_gap2_golden`／`test_ic1d_baseline`；探針 `global_run` True。事件路徑 `icir=null` 不進 byte-locked global golden。

### 4. ≥10× 不必要複雜？

**無。** B1 三 Task＋獨票 B2；無 queue／framework；mutation M1–M11 對應具名失敗模式。

### 5. 可進 B1 實作嗎？

**可派工。** R2 本人四條全 CLOSED；無新 P0／P1；照 SPEC＋TODO 實作不會重現 R2 假降級、gap3 count==2 衝突、top-features TypeError、Full-sample 字面誤導。

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | 無 blocking；TODO 2.1 驗證節略列序列化入口（見 1b） |
| 2 漏項 | R2 所列消費端已補；scan_cube 實跑 gate 留實作驗 |
| 3 不可測 | §G／mutation M1–M11／探針可證偽 |
| 4 quant | W2 holdout+事件地板方向正確；EW-RESID-1/2/3 理由仍成立 |
| 5–11 | 無過度工程；§N 殘留 `blocked-by`／`user-ruling`／`needs-research` 成立；無短命白工 |

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的 P0／P1／P2 finding；R2 本人提出之四條均已 CLOSED，SPEC↔TODO 閉合無新 blocking 矛盾。

**碼證**: `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md`／`…TFWINDOW_SPEC.md`／`…todo docs/EVTWARMUP_TODO.md` → TEMPLATE PASS×3, rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`, rc=0；`git diff d090b13c..HEAD -- docs/EVTWARMUP_SPEC.md docs/EVTWARMUP_TODO.md docs/TFWINDOW_SPEC.md` 對照 R2 synth X1–X7 處置位；COMPOSER-R2-P1-01/02/P2-01/02 修訂句在 SPEC §C-4／§C-6／Task 1.2／2.1 與 TODO 同檔同段可搜；TFWINDOW §G「單一套 oracle」刪舊重算句；brief assumed `test_events` 並存→TODO 1.2「先重算」已否證。

**來源摘要**: docs/EVTWARMUP_SPEC.md#ef3c3c555571;docs/EVTWARMUP_TODO.md#5de8901b9f6e;docs/TFWINDOW_SPEC.md#e51179a38d97;handoffs/reconcile/20260908-evtwarmup-x-review-r2/synth.md

---

## Verdict：可派工

R2 四條 COMPOSER finding 全 CLOSED；閉合輪「照這版做會不會做錯」——地板時序／predicate／寫出點／ICIR 消費端／文案／golden 互斥均已文件化且 SPEC↔TODO 一致。可進 B1；TODO 2.1 驗收節建議實作時補列 `export_all`／`scan_cube._dumps` 之 `parse_constant` gate（SPEC 已有，非 merge-blocking）。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh spec docs/TFWINDOW_SPEC.md` | TEMPLATE PASS, rc=0 |
| `bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` | TEMPLATE PASS, rc=0 |
| `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` | `與既有 golden 相同？ **True**`, rc=0 |
| `git diff d090b13c..HEAD -- docs/EVTWARMUP_*.md docs/TFWINDOW_SPEC.md` | 252 行，含 X1–X7 處置 |

---

ASSUMPTIONS_VERIFIED: 模板三 PASS；探針 True；R2 diff 對照 synth；test_events 1.1/1.2 重算句；scan_cube._dumps 讀碼（brief NOT_RUN 未 probe）
TESTS_RUN: 見 VERIFY 表（未跑 `pytest tests/governance`）
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查）
產出檔: handoffs/20260908-evtwarmup-x-review-r3-composer.md

STATUS: DONE
