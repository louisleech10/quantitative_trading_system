brief-kind: review
task-id: 20260908-EVTALIGN-X-REVIEW-R4
family: grok
findings-round: R4
標的 commit: `d398b194`（審查範圍 `ba408826..d398b194`；工作區 HEAD `5bbba542` 僅 HANDOFF，碼與標的一致）
SCOPE: review-only；禁改 production／test／docs／frontend
ORCH-DIGEST: momentum/Analysis/ic_filter_orchestrator.py#e4eacd28757b
SERVICE-DIGEST: api/services/ic_analysis_service.py#902a944497ac
PREPROC-DIGEST: momentum/Analysis/data_preprocessor.py#976406c53838
MUTATE-DIGEST: handoffs/20260907-evtalign-mutate.py#a814de569314
TODO-DIGEST: docs/GAP3_EVENT_ALIGNMENT_TODO.md#720d74b58b85
BASELINE: handoffs/20260908-evtalign-r4-baseline.sha → `shasum -a 256 -c` 全 OK（開工時）

---

## Verdict：可收案——無新 P0／P1；B5 落點維持 service；進使用者 UAT（B26–B31）

B2–B5 實作與前端接線在碼證＋驗收命令＋clean-clone mutation phase 2–5（UNCOVERED=0、紅皆 pytest rc=1）下與 SPEC／TODO 一致。  
必答 1a–4b 雙向皆有反例或碼路徑；3b 裁定：**維持 service 落點**（非事件揭露缺口可接受）。  
本輪無實質 finding → 見 sentinel `GROK-R4-P3-00`。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_period_auto_align.py tests/api/test_stage_progress.py tests/api/test_isolation_disclosure.py tests/momentum/test_validated_series_is_used_series.py tests/api/test_gap3_feature_coverage_gate.py -q -rs` | **53 passed, 0 skip**, rc=0（~162s） |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py -k 'not budget_bench' tests/momentum/event_samples/test_gap3_conditional_ic.py -q` | **12 passed, 1 deselected**, rc=0；含 g1／g2 canonical sha 綠 |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py::test_budget_bench_receipt -q` | **1 passed**, rc=0（~164s）⇒ gap2_golden **全檔綠** |
| `venv/bin/python handoffs/20260907-probe-split-baseline.py` | rc=0；`與既有 golden 相同？ **True**`；sha256=`e378c706…ba7201` |
| `(cd frontend && npx vitest run src/lib/icProgressLabel.test.ts src/lib/icPeriodAlignment.test.ts src/lib/icIsolation.test.ts)` | **11 passed**, rc=0 |
| mutation（clean clone `@d398b194`，非共用樹）`--phase 2..5` | 皆 rc=0；`UNCOVERED=0`；紅集合＝oracle（見下）；共用樹 `momentum/`／`api/` 未髒 |
| `shasum -a 256 -c handoffs/20260908-evtalign-r4-baseline.sha` | 全 OK |

### Mutation 紅集合（closure=CLOSED）

| Phase | IDs | 觀測 |
|---|---|---|
| 2 | A6a, A6b | 各 `rc=1` PASS（期望紅） |
| 3 | A7, A8-feature-trim, A9 | 各 `rc=1` |
| 4 | A8-memory-warn-raise, A10, A11 | 各 `rc=1`（A11 選擇子 `first_report_is_estimating` 已對） |
| 5 | A12, A13 | 各 `rc=1` |

---

## 必答（成對；逐條有碼證）

### 1a. B3 會不會漏（裁／丟後仍 look-ahead 或錯配）？

**未證實新洩漏。** 逐提示：

| 構造 | 結果 |
|---|---|
| 預載 labels 未「同步裁」 | stage0 裁 feature 後 `normalized_labels.reindex(feature_index)`；oracle 類另 `_coterminalize_close`＋`validate_alignment`（可延後）。reindex 保留**同 timestamp** 原值，不另造未來值。 |
| `event_period_ms` 只用於訊息 | `_intersect_features_with_kline_period` 裁切判準＝feature∩kline index；`event_period_ms` 僅空交集訊息／`event_period` 揭露鍵（orch `:329-332`）。 |
| `dropped_events` 閉區間 | `run_start ≤ decision_at` 且 `label_end ≤ run_end`（service `:345-348`）。探針：`label_end==run_end` 保留；`+1ms` 丟。 |
| owner 迴圈 vs allowed | `apply_event_coverage` **只縮** `allowed_event_ids`、不縮 `windows`（`label_value_from_case.py:915`）；`resolve_label_value_at_analyze` 以 `if w.event_id not in allowed: continue`（`:991-992`）過濾；owner 迴圈對 `label_values.get→None` 的 dropped **continue**（service `:669-674`）。live 測：`event_label_values` 只剩 covered（`test_live_event_stages_…`）。**不進 IC。** |

### 1b. B3 會不會誤擋／誤丟？

**邊界相等不誤丟**（閉區間探針：`BOUNDARY_EQ_KEPT ('eq',)`）。  
合法 feature 同頭同尾／K 線更長 ⇒ `trimmed_bars` 全 0、不寫報告鍵（`test_report_metadata_key_present_only_when_trimmed…`＋真實 fixture `period_alignment` 缺席）。  
全丟才 `feature_coverage_insufficient`；部分丟揭露 ids（A7 錨）。

### 2a. B4 會不會擋／吵？

**不擋。** `_memory_pressure`／hook：**不 raise**；psutil 失敗 → snapshot `None` → pressure `None`（`:264-266`）；`baseline` 缺 → swap 增長用 `now` 當基線 ⇒ 增長 0 ⇒ 不發。A8 mutation 改 raise ⇒ `not_blocking` 紅。  
**正常機器不吵：** 真實 fixture `run_analyze` payloads → `REAL_FIXTURE_WARN_COUNT 0`（本輪探針；補 brief 所請之 payloads 驗）。

### 2b. B4 會不會假？

| 檢查 | 結果 |
|---|---|
| 第一次就有 ETA | 否；`reports >= 2` 才估（preproc `:61-63`）；測＋探針 `first_est=True` |
| `done/total` | 末次 `done==total==n_cols`；探針 `done_eq=True` |
| 回報次數 | ∈`[3, max(3,ceil(n/100))]`（14／157／300／1000 探針皆 `in_bounds`） |
| done 單調 | 探針 `mono=True` |

### 3a. B5 數字能不能被偽造？

**bars 不能由 service 自造：** `_inject_isolation_source` 之 `purge_bars`／`embargo_bars` **只**讀 `metadata.ic_train_test_split`（`:169-170`）；與 split 逐值相同有測。  
`embargo.source` 用 staged 之 `purge_rows`／`embargo_before_event`（service 在抬高 embargo **之前**寫入 `:1533`）——**來源標籤** producer-bound，不改 bars。A13 寫死 source ⇒ 紅。

### 3b. B5 落點改 service 是否成立？**裁定：維持 service。**

- 混淆點（purge＝全域 h vs 事件 h）**只在事件路徑**；非事件報告已有 `ic_train_test_split.{purge_gap,embargo}`。
- orchestrator 對所有切分 run 加 `isolation` 會弄紅 `test_gap2_golden` 整份 canonical sha；service 僅事件＋`applied` 時寫 ⇒ §G-1 守住（`test_non_event_report_unchanged_without_injection` 綠）。
- TODO 要點 3 已寫落點改寫理由；「修改檔案」列仍寫 orchestrator／DegradedBanner＝**文件表頭殘留**，非行為洞（不列 finding；收案後可順手改表頭）。

### 4a. Task 2.2 不變式可否被繞？

**主 IC 路徑不可繞。** spy 掛 `validate_alignment`／`validate_consumed_label`／`_stage4_ic_calculation`。  
`analyze_full` → `analyze()`（`:2149`）。`refilter` **不重跑** stage4，重用 `_ic_cache["label_series"]`（已於首跑驗證）。  
`cross_sectional`：源碼無守衛呼叫 → `EA-RESID-2` not_applicable（有意）。  
無第二生產入口對「進 IC 的 series」另驗另用。

### 4b. 會不會誤紅（fallback 致 `validated[-1]`≠`consumed[-1]`）？

**設計上不誤紅。** 每次 analyze（含 fallback 重跑）重置 deferred／完整 stage2→3→4；spy 比對**最後一次**驗證與**最後一次** stage4。事件不足 fallback 消費鷹架時 `_settle_deferred_scaffold(scaffold_consumed=True)` 仍 raise 延後違規——不變式比的是通過路徑上的成對序列。A6a／A6b 刻意錯配才紅。

### 5a. mutation 充分性（10 條全綠仍可能有的缺陷）

**例：** `resolve_label_value_at_analyze` 若刪掉 `allowed_event_ids` 過濾，dropped 事件可進 `label_values`；A7／A8／A9／A12／A13 **全綠也抓不到**（它們不突變 resolve）。現行碼有過濾（`:991`）——此為**突變缺口**，非已證 prod 洞。

### 5b. 紅因？

本輪 phase 2–5 每條均 `rc=1`（斷言失敗），**無** import／語法／rc=5。腳本對 rc=5 計 UNCOVERED（brief 已記 A11 選擇子事故，標的 commit 已修）。

### 6. ≥10× 不必要複雜？`period_alignment` 兩層可否合一？

**無 10×。** orchestrator＝feature∩kline 裁切；service＝事件 vs manifest 丟 ID。職責不同、合併寫入已測不覆蓋 `trimmed_bars`（`test_inject_period_alignment_only_when_something_dropped`）。強制單一 writer 需跨層傳事件窗或裁切結果，不比較現況簡單。

### 7. 可以收案嗎（B0–B5）？

**可以收案** → 進使用者 UAT B26–B31。無 BLOCKING／無新 P1 必改。殘留仍為既有 `EA-RESID-*`（含 EA-RESID-6 四條既有紅），非本批。

---

## §0 挑戰前提

| 宣稱 | 裁定 | 證據 |
|---|---|---|
| fact: 新測試 0 skip | **成立** | 53 passed，summary 無 skipped |
| fact: gate 1–5／mutation UNCOVERED=0 | **成立**（本輪自跑 mutate 2–5） | 各 `UNCOVERED=0` |
| fact: B4 後 golden 134 含 gap2 | **本輪抽驗** g1／g2／conditional 綠；budget_bench 另檔慢測 |
| assumed: 零裁零丟報告逐位元組不變 | **成立** | 真實 fixture 無 `period_alignment`／無 `isolation`；gap2 sha 測綠 |
| assumed: 正常機器不發 memory WARN | **成立（本機 fixture）** | `REAL_FIXTURE_WARN_COUNT 0` |
| unverified: 真實事件批 E2E／瀏覽器面板 | **仍 NOT_RUN** | 同意 brief 表；不升 P0 |

### 被當成事實的未驗證假設（§0）

無新增「當事實卻未驗」且會擋收案者。brief 列之 NOT_RUN（真實 thrash、macOS/Linux swap 語意、瀏覽器 e2e）維持 research／blocked-by，非本輪偽綠。

---

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——B2–B5 碼路徑與 SPEC／TODO 一致，必答 1a–4b 雙向皆有碼證或反例，mutation phase 2–5 紅集合等於 oracle 且紅因皆 pytest rc=1，無新 P0／P1。

**碼證**: 驗收表（53 passed／0 skip；gap2 非 budget 12 passed；probe True；vitest 11；mutate 2–5 UNCOVERED=0）；探針 `REAL_FIXTURE_WARN_COUNT 0`、`BOUNDARY_EQ_KEPT`、progress `first_est`／`in_bounds`；關鍵路徑 `ic_filter_orchestrator.py` `_intersect_features_with_kline_period`／`_stage1_progress_hook`／`_memory_pressure`，`ic_analysis_service.py` `check_feature_run_coverage`／`_inject_period_alignment`／`_inject_isolation_source`，`data_preprocessor.py` `_emit_progress`；3b 裁定維持 service。RECHECK：重跑上表命令＋clean-clone `handoffs/20260907-evtalign-mutate.py --phase {2,3,4,5}`。

**來源摘要**: handoffs/20260908-EVTALIGN-X-REVIEW-R4-BRIEF.md#d398b194dc4e; momentum/Analysis/ic_filter_orchestrator.py#e4eacd28757b; api/services/ic_analysis_service.py#902a944497ac; momentum/Analysis/data_preprocessor.py#976406c53838; handoffs/20260907-evtalign-mutate.py#a814de569314

[MINOR] 信心度=High。sentinel（零實質 finding）；非湊數。文件表頭 TODO 5.1「修改檔案」仍列 orchestrator 屬收案後順手清理，不升 finding。

---

STATUS: DONE
