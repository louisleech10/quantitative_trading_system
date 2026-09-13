# SPLITUNIFY b9 — review-r22（E1／E2 閉合再驗證）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R22`  
**family**: composer  
**findings-round**: R22  
**審查標的**: commit `2f66cf77`；current block＝`tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed`；`docs/SPLITUNIFY_TODO.md` 之 `Task 2.2` 三處與 §E `SU-RESID-2`  
**禁改碼**：review-only。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: xfail 收緊後仍 `1 xfailed` | **fact-verified** | `venv/bin/python -m pytest -rxX "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0 |
| brief fact-verified: `AlignmentViolationError` 為 `ValueError` 子類 | **fact-verified** | `momentum/core/contracts.py:933` `class AlignmentViolationError(ValueError)` |
| brief fact-verified: 六路回歸 706 passed、1 xfailed | **fact-verified** | 六路 `-rxX` → **706 passed, 1 xfailed** rc=0（66.99s） |
| brief fact-verified: `Task 2.2` 三處 SUPERSEDED | **fact-verified** | `grep -n SUPERSEDED docs/SPLITUNIFY_TODO.md` → :225/:242/:265，皆在 `Task 2.2` 段 |
| brief assumed: `Task 2.2` superseded 已涵蓋全部 B9B 互斥處 | **fact-verified（本段內）**；其他舊 Task 段見必答 2 | `Task 2.2` 三處已標；逐段掃見下 |
| brief assumed: `SU-RESID-2` 標「已關閉」正確 | **fact-verified** | B9B 交付範圍＝producer 全量＋`feature_timeframe` 欄＋複合鍵 guard；下游消費面本來就列 `Task 9.3`（見必答 3） |

---

## 必答 1 — 本家 R21 反例重跑（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R20-P1-01`（xfail 錨點測試存在且機械驗收） | **CLOSED** |
| `COMPOSER-R20-P2-01`（多 symbol 三計數具名測試） | **CLOSED** |
| R21 本家對 xfail 收緊之建議（必答 2b：`AlignmentViolationError`＋`match e_x`） | **CLOSED**（`2f66cf77` 已採納，與 codex `CODEX-R21-P1-01` 同型修法） |
| R21 本家對 `xfail(strict=True)` 之裁定（必答 3：現行最好） | **CLOSED**（本輪未重開；decorator 仍在、仍得 `1 xfailed`） |

### (1b)

- **R20-P1-01**：`venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **`1 xfailed`** rc=0（非 `passed`／`no tests ran`）。`:1641` 已為 `pytest.raises(AlignmentViolationError, match="e_x")`。
- **R20-P1-01（--runxfail）**：`venv/bin/python -m pytest --runxfail "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **`1 failed`**；失敗原因 **`Failed: DID NOT RAISE <class 'momentum.core.contracts.AlignmentViolationError'>`**（非 fixture 錯、非 import 錯）——紅因＝9.2b 尚未 raise，符合設計。
- **R20-P2-01**：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py::test_multi_symbol_branch_summary_counts_are_named` → **1 passed** rc=0。
- **E1 收緊複驗**：`AlignmentViolationError` import 自 `momentum.core.contracts`（`:34`）；`--runxfail` 失敗型別為 `DID NOT RAISE AlignmentViolationError`，證明斷言已釘死目標型別而非寬 `Exception`。

---

## 必答 2 — TODO 其他舊 Task 段是否仍有 B9B 互斥描述

### (2a)

逐段掃 `Task 2.1`／`2.3`／`3.1`–`3.3`／`4.1`（關注 `assignments`／`purged` 欄集、`clusters` 粒度、producer 單選、summary 鍵數）：

| Task | B9B 互斥？ | 說明 |
|------|-----------|------|
| **2.1** | **否** | 僅 canonical boundary builder；不涉及複合鍵／summary 鍵集 |
| **2.3** | **否** | golden oracle 以 `feature_index[plan.row_index]` 產 event_id 集合；與複合鍵行粒度相容，未要求 `assignments` 缺 `feature_timeframe` |
| **3.1** | **否** | 接線與 `split_events` 退場；無 schema 舊契約 |
| **3.2** | **否（B9B 維度）** | 仍寫多 symbol raise，但屬 **per-symbol 投影支援** 敘事（R-1 前史），非 producer 單選／複合鍵／16 鍵類互斥；且 `Task 2.2` :247-249 已具名「`Task 3.2` 使 `n_symbols==1`」為預期揭露，與 B9B 多 TF 行不衝突 |
| **3.3** | **否** | event-study-only 分支；無投影 schema |
| **4.1** | **否** | `metadata.split_unify` 揭露；不涉及 `assignments`／`purged` 欄集 |

`Task 2.2` 驗證段 :264 `len(assignments)+len(purged)==len(event_keys)` 與 `event_id` 交集為空——仍為行數守恆／事件級互斥，與複合鍵**不互斥**；:265 已標 SUPERSEDED 指向 16 鍵。

**結論**：除已標 SUPERSEDED 之 `Task 2.2` 三處外，**無**需再貼 superseded 之 B9B 互斥舊段。

### (2b)

**N/A**（無新增互斥處）。

---

## 必答 3 — `SU-RESID-2` 狀態標記

### (3a)

**應標「已關閉」**（不需改「部分關閉」）。

理由：`SU-RESID-2` 之存在理由＝producer 靜默單選＋投影層缺 `(event_id, feature_timeframe)` schema（見 `Task 9.2`／`9.2a` 首句）。B9B 已交付此範圍。原文「複合鍵要連下游一起改」描述的是 **Phase 9 全線**（9.3–9.5），已由依賴序 `9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5` 分拆；下游未做 **不等於** 殘留項半開——否則 `Task 9.1` 亦永遠只能標「部分」。§E 列已保留追溯原文並指向 `Task 9.3`，足夠。

### (3b)

**維持現行字面即可**（`2f66cf77` 已寫入，無需再改）：

```markdown
| ~~`SU-RESID-2`~~ **已關閉（2026-09-14，批次 B9B）** | 多 TF 之 `(event_id, feature_timeframe)` 複合鍵 | — | 🔴 **這條殘留正是 `Task 9.2`＋`9.2a` 的存在理由，已由該批解決**：…原文「…複合鍵要連 `EventSplitPlan` 之下游一起改」保留供追溯——下游消費面改動見 `Task 9.3`（未實作，非本殘留 reopen 理由）。 |
```

（僅建議把「下游確實一起改了」改為「下游消費面改動見 `Task 9.3`」——**doc-literal-only、非 BLOCKING**；本輪禁改 TODO。）

---

## 必答 4 — SPEC 是否第四次同形互斥

### (4a)

掃 `docs/SPLITUNIFY_SPEC.D-002.md`（正文，不含 `HISTORY-BEGIN..END`／「沿革」）：

| 位置 | 內容 | 與 B9B 互斥？ |
|------|------|--------------|
| `D-002-C4` (4.2) | 描述改前「靜默丟棄」實況 | **否**——問題陳述／對 D-001 更正，非施工契約 |
| `(5.2)` | 落地後契約（全量 producer、兩表含欄、`clusters` 事件級） | **否**——與 B9B 一致 |
| §P `Task 9.2` :196-201 | 「現行該處逐字為…必傳…四者同時」 | **否**——**改前碼證＋改法**敘事（施工清單），非未標 superseded 的雙真相；B9B 已完工，實作者進 9.2b 讀 `Task 9.2b` 段 |
| §N :326 | 「TODO §E 該列**現仍**為 needs-research」 | **過期同步句**（TODO 已於 r21 改為已關閉）——doc drift，**非**會導致回退 B9B 之 live 契約 |
| §P `Task 9.2b` :215 | `decision_at_ms` 命中數 0 | **否**——9.2b 前瞻現況碼證，正確 |

**非第四次同形發作**：SPEC 無類似 r21 TODO `Task 2.2` 之「未標 superseded 的 live 雙契約」；僅 §N :326 同步句過期（P3 doc-literal-only）。

### (4b)

**不阻擋**進 `Task 9.2b`。§N 過期句可在日後 doc sync 輪修，不屬 B9C 前置。

---

## 必答 5 — 可否進 `Task 9.2b`（B9C）

### (5a)

**可以進 `Task 9.2b`（批次 B9C）**。無 BLOCKING finding。

### (5b)

已檢查：E1 xfail 收緊後仍 `1 xfailed`；`--runxfail` 失敗為 `DID NOT RAISE AlignmentViolationError`；`Task 2.2` 三處 SUPERSEDED；其他舊 Task 段無 B9B 互斥；`SU-RESID-2` 已關閉判定成立；SPEC 無阻擋性雙真相；六路回歸 **706 passed、1 xfailed**；本家 R20 兩條反例仍 CLOSED。

---

## COMPOSER-R22-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；E1／E2 修補已閉合，可進 `Task 9.2b`。

**碼證**: `venv/bin/python -m pytest -rxX "tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 xfailed** rc=0；`venv/bin/python -m pytest --runxfail "…::test_multi_feature_tf_opposite_sides_must_fail_closed"` → **1 failed**，`DID NOT RAISE AlignmentViolationError`；六路 `-rxX`（`test_splitunify_derive.py`＋`event_samples/`＋`test_splitunify_golden.py`＋`test_splitunify_contract.py`＋`test_splitunify_disclosure.py`＋`test_splitunify_event_study_only.py`）→ **706 passed, 1 xfailed** rc=0；`grep -n SUPERSEDED docs/SPLITUNIFY_TODO.md` → :225/:242/:265。

**來源摘要**: docs/SPLITUNIFY_TODO.md#2ba9ad37

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R20-P1-01,COMPOSER-R20-P2-01

ASSUMPTIONS_VERIFIED: xfail 1 xfailed；--runxfail DID NOT RAISE AlignmentViolationError；706+1xfail 六路回歸；Task 2.2 三處 SUPERSEDED；舊 Task 段無 B9B 互斥；SU-RESID-2 已關閉成立；SPEC 無阻擋雙真相
TESTS_RUN: `pytest -rxX …::test_multi_feature_tf_opposite_sides_must_fail_closed` → 1 xfailed；`pytest --runxfail …` → 1 failed DID NOT RAISE；六路 `pytest -q -rxX`（六檔）→ 706 passed 1 xfailed；`pytest -q …::test_multi_symbol_branch_summary_counts_are_named` → 1 passed
FAILURES_SEEN: none（review-only；--runxfail 預期失敗）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r22-composer.md

STATUS: DONE
