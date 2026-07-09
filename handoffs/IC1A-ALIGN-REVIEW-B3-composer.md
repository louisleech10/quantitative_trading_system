# IC1A-ALIGN-REVIEW-B3 — Composer Code Review

- **task-id**: `ic1a-align-review-b3`
- **reviewer**: Composer
- **baseline**: `docs/IC_PHASE1_1A_ALIGN_SPEC.md` v3 Task 2.5/2.6 + `docs/IC_PHASE1_1A_ALIGN_TODO.md`
- **diff scope**: `momentum/Analysis/ic_engine.py`, `momentum/Analysis/ic_filter_orchestrator.py`, `tests/momentum/test_ic_engine.py`, `tests/momentum/test_ic_filter_orchestrator.py`
- **date**: 2026-07-09

## Executive Summary

B3 實作正確消滅 Task 2.5 同長 index 靜默 positional 對齊；Task 2.6 在 `labels_path` reindex 前接入 MultiIndex Tier-1 驗證與 D-1 timestamp 正規化。M2 mutation 可證偽；caller 清點完整；debug iteration 1「full MultiIndex uniqueness」修法無同 symbol 重複 ts 漏網；cut2 18 測試零修改且全綠。存在 2 項 NON-BLOCKING 規格/覆蓋率缺口，不阻擋合併。

---

## Checklist Receipts

### 1) Task 2.5 — 等長 index 不等 → raise 真擋 + mutation

| 項目 | 結果 |
|------|------|
| 實作 | `ic_engine.py:599-604` 先 `.equals()` 快路徑；`len` 相等且 index 不等 → `AlignmentViolationError` |
| 新測試 | `test_align_label_to_group_rejects_equal_length_misalignment` PASSED |
| M2 mutation | 還原舊 silent positional 邏輯後 **不 raise**；`pytest.raises(AlignmentViolationError)` **FAIL**（符合 M2 轉紅要求） |

```text
# mutation probe (python one-off)
old_silent_positional_returns=True
new_raises=True
M2 pytest_on_old: FAIL_AS_EXPECTED (old silent path does not raise)
```

```bash
pytest tests/momentum/test_ic_engine.py::test_align_label_to_group_rejects_equal_length_misalignment -q
# 1 passed
```

### 2) Task 2.5 — caller 清點

```bash
rg -n "_align_label_to_group" momentum/ tests/ --glob '*.py'
```

| 位置 | 角色 |
|------|------|
| `ic_engine.py:585` | 唯一 production caller：`_compute_l7_raw_group_ic` |
| `ic_engine.py:596` | 定義 |
| `ic_engine.py:213` | 間接 caller：`compute_ic_from_l7_raw` 迴圈 |
| `test_ic_engine.py` | 新增單元測試 |

`compute_grouped_ic` 走 `_align_with_raw_data` + `.loc[idx]`，**不**經 `_align_label_to_group`（與 TODO「grep ic_engine.py 全列」一致，無漏接）。

### 3) Task 2.6 — MultiIndex 正規化語義 + uniqueness 修法

**語義探針（`_normalize_cross_sectional_labels_index`）**

| 輸入 | 行為 | receipt |
|------|------|---------|
| `DatetimeIndex` timestamp level | 直通 | `datetime: OK unchanged=True` |
| int64 epoch 秒 | `pd.to_datetime(..., unit="s")` | `int64_seconds: OK first_ts=2024-01-01 00:00:00` |
| 毫秒級 int64 (`>1e12`) | raise `InvalidInputError` | `millisecond: RAISED ...milliseconds...` |
| 同 ts 不同 symbol | 允許（cross-sectional 正常） | `same_ts_diff_symbol: OK unique=True` |
| 同 symbol 同 ts 重複 | raise `index must be unique` | `duplicate_same_symbol_ts: RAISED` |
| 亂序 full MultiIndex | raise monotonic | 新測試 `test_cross_sectional_labels_path_rejects_unsorted_index` PASSED |

**debug iteration 1 漏洞評估**：改為 **full `MultiIndex.is_unique`**（前後各驗一次）後，同 symbol 重複 timestamp **可抓**；不再誤殺「同 ts 跨 symbol」合法列。未發現 BLOCKING 漏洞。

**F4 委派**：disjoint timestamps reindex 後 → `_enforce_cross_sectional_label_coverage` raise `all-NaN labels`（既有 cut2 守衛，未繞過）。

```text
disjoint_ts: RAISED symbol BTCUSDT has all-NaN labels (fail-closed)
```

### 4) cut2 18 測試斷言零修改

```bash
git diff tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py
# (empty)

git diff tests/momentum/test_ic_filter_orchestrator.py tests/momentum/test_ic_engine.py | grep '^-' | grep -v '^---' | wc -l
# 0 removed lines — 僅純新增測試/import，無既有 assert 刪改
```

```bash
pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -q
# 18 passed
```

### 5) 既有斷言未放寬

- `test_ic_engine.py` / `test_ic_filter_orchestrator.py` diff 無刪行、無 assert 門檻下調。
- `test_grouped_ic_by_regime` 回歸 PASSED。
- `pytest tests/momentum/ -k "grouped or align_label or cross_sectional" -q` → **20 passed**。

---

## Findings

### B3-F01 — NON-BLOCKING — Task 2.5 未套用 D-1 同型化再比對（與 2.3 字面差距）

- **問題**: SPEC/TODO 2.5 寫「同 2.3 語義」；2.3 (`_slice_by_mask:636-639`) 在等長時先 `_normalize_ic_time_index` 再 `.equals()`。2.5 用裸 `.equals()`，等長但 int64 秒 vs `DatetimeIndex`（語義相同）會 raise 而非對齊後放行。
- **receipt**:
```python
# probe: same 3 bars, label index=int64 epoch s, group index=DatetimeIndex
ICEngine._align_label_to_group(label, group_df)
# AlignmentViolationError: equal length; refusing positional alignment
```
- **修法**: 在 `_align_label_to_group` 等長分支引入與 orchestrator 同契約的 D-1 正規化（可抽至 `contracts` 共用 kernel，避免 `ic_engine` import orchestrator）；正規化後相等則快路徑，仍不等才 raise。優先級低——較舊 silent positional 安全，且 L7 raw 路徑 §N 未全面 gate。

### B3-F02 — NON-BLOCKING — Task 2.6 邊界 hermetic 覆蓋不全（探針過、pytest 未鎖）

- **問題**: TODO 2.6 邊界 ②③ 中，毫秒拒絕、同 symbol 重複 ts、reindex 全落空→F4 僅部分有 pytest；F4 全落空依 cut2 既有測試間接覆蓋。
- **receipt**: 上表 python probe 全過；新增測試僅覆蓋 int64 秒放行 + 亂序拒絕。
- **修法**: 補 3 個 hermetic：`test_cross_sectional_labels_path_rejects_millisecond_timestamps`、`test_cross_sectional_labels_path_rejects_duplicate_symbol_timestamp`、`test_cross_sectional_labels_path_disjoint_index_triggers_f4`（可選，cut2 已覆 F4）。

### B3-F03 — NON-BLOCKING — 2.6 用 `InvalidInputError` 非 `AlignmentViolationError`

- **問題**: Tier-1 kernel 統一用 `AlignmentViolationError`；2.6 helper 用 `InvalidInputError`。
- **receipt**: 與 `analyze_cross_sectional` / cut2 F2-F4 既有慣例一致；cut2 18 全綠。
- **修法**: 可 defer；若需統一例外族，另開小 refactor。

---

## VERDICT

**APPROVE** — Task 2.5 核心缺陷（同長靜默 positional）已 fail-closed 關閉，M2 mutation 可證偽；Task 2.6 Tier-1 接入點正確，uniqueness 修法無已知漏洞；cut2 18 零 assert 修改且回歸全綠。B3-F01~F03 為 follow-up，不阻擋 B3 驗收。

```text
ASSUMPTIONS_VERIFIED: M2 mutation old-path silent / new-path raise; caller grep complete (585 only); full MultiIndex uniqueness catches duplicate (sym,ts); cut2 18 diff empty + 18 passed; no test assert weakening
TESTS_RUN: pytest B3 new tests (5) passed; pytest -k "grouped or align_label or cross_sectional" 20 passed; cut2+api 18 passed; python edge probes for 2.6 dtypes/uniqueness
FAILURES_SEEN: none
SCOPE_CHANGES: none (review-only)
NUMERIC_OR_SCHEMA_IMPACT: none observed in diff
```

**Verdict: APPROVE**
