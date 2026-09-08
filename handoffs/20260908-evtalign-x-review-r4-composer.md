brief-kind: review
task-id: 20260908-EVTALIGN-X-REVIEW-R4
family: composer
findings-round: R4
標的 commit: `d398b194`（HEAD）；審查範圍 `ba408826..d398b194`

---

## 被當成事實的未驗證假設（§0）

| 前提 | 裁定 | 覆核摘要 |
|---|---|---|
| 新測試 53 條 0 skip | **fact-verified** | `pytest tests/api/test_period_auto_align.py … test_gap3_feature_coverage_gate.py -q -rs` → 53 passed, rc=0 |
| split golden 對證 | **fact-verified** | `handoffs/20260907-probe-split-baseline.py` → `與既有 golden 相同？ **True**` |
| baseline sha 未改碼 | **fact-verified** | `shasum -a 256 -c handoffs/20260908-evtalign-r4-baseline.sha` → 全 OK |
| 前端三 lib vitest | **fact-verified** | `npx vitest run icProgressLabel/icPeriodAlignment/icIsolation.test.ts` → 11 passed, rc=0 |
| 正常機器無 memory WARN | **fact-verified（推翻 brief assumed 待驗）** | `run_analyze` 12 payloads、`warning_payloads=0`（見 VERIFY） |
| gap2_golden 全綠 | **fact-verified（brief）** | 本輪單檔前景 >7min 未完成；brief 134 passed 含 gap2；`test_non_event_report_unchanged_without_injection` 綠 |
| phase gate 2–5 mutation | **fact-verified（brief）** | 共用工作樹未重跑 mutate（brief 禁並行 gate）；oracle 清單與 `handoffs/20260907-evtalign-mutate.py` 對讀一致 |
| 預載 label + feature∩K線裁切 | **fail-closed（讀碼＋R3 E2 測）** | R3 `test_stage0_preloaded_labels_from_longer_close_still_raise…` 證守衛 raise；B3 裁切後仍 `reindex`+`validate_alignment`（`:2912-2953`）；**未構造**「預載＋intersect 裁切」專用 receipt |
| API 端到端部分涵蓋 | **blocked-by** | brief `NOT_RUN` |
| psutil swap Linux 可移植 | **needs-research** | brief `cost` |
| 瀏覽器三面板渲染 | **blocked-by** | brief `NOT_RUN` |

---

## 必答（成對 verdict）

### 1a. B3 會不會漏（裁切／丟事件後 look-ahead／錯配）

**主徑已封，殘留為 R3 同型誠實邊界（非新 P0）。**

- **feature∩K線裁切**：`_intersect_features_with_kline_period` 在切分前執行（`:2910-2914`）；真裁才寫 `metadata.period_alignment`（`:1078-1082`）；交集空 fail-closed 含三期間（`:310-318`）。
- **逐事件丟失**：`check_feature_run_coverage` 左界 `decision_at_ms`、右界 `label_end_ms` 閉區間（`:341-348`）；`apply_event_coverage` 縮 `allowed`（service `:612-616`）；`label_values` 只含 covered（live 測 `test_live_event_stages_drop_out_of_range_event…`）。
- **預載 labels**：裁切後 `normalized_labels.reindex(feature_index)`（`:2925-2926`）不重生 HDF5；R3 E2 已證「長 K 線離線預載 ⇒ 尾端 lag 不符 ⇒ 守衛 raise」（`test_close_coterminalize.py:131-151`）。**未能構造** intersect 裁切後仍 PASS 但含 look-ahead 的反例。
- **`event_period_ms`**：僅進錯誊與 `period_alignment.event_period`（`:328-332`），不參與裁切判定——設計如此，非漏檢。

### 1b. B3 會不會誤擋／誤丟

**未見新誤擋。** `label_end_ms == run_end_ms` 與 `decision_at_ms == run_start_ms` 之 over 向對照在 `test_feature_coverage_gate_05`（`:165-171`）與 `test_period_auto_align` 部分涵蓋案例。K 線比 feature 長 ⇒ 零 feature 裁切（`:168-170`），交 `_coterminalize_close`。全丟才 `feature_coverage_insufficient`（A9 mutation 紅）。

### 2a. B4 會不會擋／吵

**不擋；正常機器不發 WARN（本輪實測）。** `_memory_snapshot` 例外吞掉回 `None`（`:252-253`）；`_memory_pressure` 永不 raise（`:259-275`）；hook 缺 baseline 當 `{}`（`:268`）。`run_analyze` 真實 la0 fixture：**12 payloads、0 含 `warning`**。單元測 `test_memory_warn_is_not_blocking…`／`test_no_warn_when_memory_normal` 綠。

### 2b. B4 會不會假

**未見假進度。** 第一次 `eta_state=estimating`（`test_first_report_is_estimating_no_fake_eta`）；`done` 單調（`:48`）；回報次數 `3 <= n <= max(3, ceil(n/100))`（`:45`）；真實 fixture sub_progress 上界含 fallback 重跑倍數（`:136-138`）。無 M 秒節流——brief 標 `cost`；39k 欄 ⇒ ~390 次 callback，屬設計取捨非假進度。

### 3a. B5 數字能不能被偽造

**bars 不可由 service 單方面偽造；source 欄為揭露衍生。** `purge`/`embargo` bars 逐值取自 `metadata.ic_train_test_split`（`:169-170`）；`test_isolation_total_equals_sum…` 對證。`embargo.source` 由 staged `purge_rows` vs `embargo_before_event` 比較（`:182`），兩者來自 service 事件迴圈（producer-bound）；A13 mutation 改寫死 ⇒ 紅。service 無法在不改 orchestrator split 的情況下改 bars。

### 3b. B5 落點改 service 是否成立

**成立，維持 service。** 非事件 run 不寫 `isolation`（`:160-161`、`test_non_event_report_unchanged_without_injection`）⇒ §G-1 golden 不變；事件混淆點（purge vs embargo 來源）僅事件路徑需要。回 orchestrator 全 run 加鍵會弄紅 `test_gap2_golden`——brief 理由成立。**可接受**非事件 run 無 isolation 揭露（全域切分語意不同）。

### 4a. Task 2.2 不變式可否被繞

**analyze 主徑不可繞；明確例外已留痕。** `analyze_full` 仍走 `analyze()`（`:2149-2155`）⇒ spy 可見。`refilter` 重用 cache 不重跑 stage0–4（`:2045+`）⇒ **不在 Task 2.2 契約範圍**（測試 `SCENARIOS` 僅列 analyze 情境）。`cross_sectional`：`EA-RESID-2` not_applicable（源碼無守衛 grep）。直連 orchestrator  bypass service 三元組為 R1 已知邊界，非 B2 新洞。

### 4b. 會不會誤紅（fallback 重跑）

**未見。** `test_validated_series_is_used_series` 四情境（含 event 鷹架≠消費）綠；`run_analyze` fallback 時 preprocessing 重跑但同一 label 鏈，最後 `validated[-1]` 仍對 `consumed[-1]`。

### 5a. mutation 充分性（phase 2–5 全綠之缺陷）

**一種：stage0 預載 labels + B3 `feature∩K線` 裁切後，僅 reindex 不重生——若磁碟 label 在**裁切邊界內**含與當前 K 線不一致的逐值（非尾端 lag 契約能抓的型態），10 條 mutation 全綠。** 理由：A6 改 stage4 回傳；A8 只驗 feature 行數不驗 label payload；R3 E2 測 coterminalize 未測 intersect+預載組合。信心度 Medium；守衛仍 fail-closed 於 lag 契約。

### 5b. 紅因

**brief fact-verified。** 本輪未在共用工作樹重跑；對讀 `handoffs/20260907-evtalign-mutate.py`：phase 2 A6a/A6b、3 A7/A8/A9、4 A8/A10/A11、5 A12/A13 皆 `-k` 精準選子；rc=5 計 UNCOVERED（A11 選擇子錯誤已修）。`closure=CLOSED`（oracle-artifact 一致）。

### 6. ≥10× 不必要複雜？

**無。** `period_alignment` 兩層（orchestrator 裁 feature、service 丟事件）職責分離；`_inject_period_alignment` 合併不覆蓋 `trimmed_bars`（`test_inject_period_alignment_only_when_something_dropped`）。不值得合一成單一模組。

### 7. 可收案嗎（B0–B5）

**可收案 → 進 UAT（B28–B31）。** 無新 P0；R3 E1（D5 延後裁定）已在 B1 後續實作；B2–B5 測試＋golden 設計（§G-1）一致。殘留 blocked-by／needs-research 項不阻擋本批合併。

---

## mutation closure（phase 2–5）

| Phase | Oracle 紅集合 | COMPOSER 裁定 |
|---|---|---|
| 2 | A6a, A6b | **CLOSED**（brief gate PASS；對讀 mutate.py） |
| 3 | A7, A8, A9 | **CLOSED** |
| 4 | A8, A10, A11 | **CLOSED** |
| 5 | A12, A13 | **CLOSED** |

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | B5 service 落點與 TODO 字面差異已有理由；3b 裁定維持 service |
| 2 漏項 | API e2e／瀏覽器渲染 blocked-by；intersect+預載 receipt 為 cost |
| 3 不可測 | 53 條＋vitest＋probe 可執行；mutation oracle 可對讀 |
| 4 quant | 裁切／逐事件丟失／fail-closed 邊界有測；無新洩漏反例 |
| 5 過度工程 | 無 |
| 6 OOM | WARN 不擋；真實 fixture 無 WARN |
| 7 Cache | 未動 cache key |
| 8 API/相容 | §G-1 零裁切零丟鍵不新增 |
| 9 測試 | 核心路徑覆蓋；5a 列 mutation 盲區（非 P0） |
| 10 Agent | B2–B5 與 SPEC/TODO 一致 |
| 11 短命工 | 無 |

---

## COMPOSER-R4-P3-00

**斷言**: 本輪對 B2–B5（`ba408826..d398b194`）逐項核對必答 1a–7、§1 十一類與 mutation oracle 後，無達 P0/P1 門檻之新 finding。

**碼證**: ① `pytest` 驗收 53 passed/0 skip（rc=0）；② `probe-split-baseline` True；③ vitest 11 passed；④ `run_analyze` payloads `warning_payloads=0`；⑤ 讀碼 `ic_filter_orchestrator.py:278-335,1078-1082,2910-2953,3030-3054`、`ic_analysis_service.py:152-205,278-358`、`data_preprocessor.py:43-72`；⑥ R3 E2 `test_stage0_preloaded_labels_from_longer_close_still_raise…` 仍綠；⑦ 5a 所列 mutation 盲區為 Medium 信心測試缺口，守衛 fail-closed，不升格 blocking。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4eacd28757b; api/services/ic_analysis_service.py#902a944497ac; handoffs/20260908-EVTALIGN-X-REVIEW-R4-BRIEF.md

[NON-BLOCKING] 信心度=High；核對依據=必答全格雙向 verdict＋驗收命令實跑＋brief 未查表逐條標三態；停輪條件 ①–④ 滿足（3b=維持 service）。

---

## Verdict：可收案——B2–B5 實作與 SPEC/TODO 一致，無新 P0/P1；§G-1 golden 設計成立；進 UAT B28–B31

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `pytest tests/api/test_period_auto_align.py … test_gap3_feature_coverage_gate.py -q -rs` | 53 passed, rc=0 |
| `venv/bin/python handoffs/20260907-probe-split-baseline.py` | `與既有 golden 相同？ **True**` |
| `shasum -a 256 -c handoffs/20260908-evtalign-r4-baseline.sha` | 全 OK |
| `cd frontend && npx vitest run src/lib/icProgressLabel.test.ts … icIsolation.test.ts` | 11 passed, rc=0 |
| `pytest tests/api/test_stage_progress.py::test_real_fixture_analyze_emits_sub_progress_within_bounds -q` | 1 passed, rc=0 |
| `run_analyze` payload 掃描（本輪） | `payload_count=12`, `warning_payloads=0` |
| `pytest tests/momentum/Analysis/test_gap2_golden.py -q` | 前景 >7min 未完成（brief 134 passed 代用） |

---

ASSUMPTIONS_VERIFIED: 驗收 pytest 53 條、probe、baseline sha、vitest、真實 fixture 無 WARN、核心讀碼
TESTS_RUN: 見 VERIFY
FAILURES_SEEN: gap2_golden 單檔前景逾時（未否證 brief 134 passed）
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）

產出: `handoffs/20260908-evtalign-x-review-r4-composer.md`

STATUS: DONE
