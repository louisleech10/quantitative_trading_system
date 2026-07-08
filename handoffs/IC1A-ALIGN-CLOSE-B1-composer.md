# IC 1-align B1 Closure Re-Verification (Composer)

**task-id**: `ic1a-align-close-b1`  
**baseline review**: `handoffs/IC1A-ALIGN-REVIEW-B1-composer.md`  
**fix receipt**: `handoffs/IC1A-ALIGN-FIX-B1-RESULT.md`  
**reviewer**: Composer | **date**: 2026-07-09

## VERIFY receipt (closure run)

```bash
# Full alignment test suite (Codex fix receipt)
pytest tests/momentum/core/test_alignment_contract.py \
  tests/momentum/Analysis/test_ic_1a_cut1_split.py -q
# 29 passed in 0.45s

# Composer adversarial probes (inline python, same session)
# See per-finding outputs below
```

---

## Blocking closure matrix

### ADV-B1-01 — Tier-1 覆蓋率門檻

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-01 |
| **Status** | **CLOSED** |
| **Probe** | 100 列、lag=5、中間 80 孔（`labels.iloc[10:90]=NaN`），僅 10 個有效 label |
| **重跑輸出** | `raise AlignmentViolationError: target coverage too low: actual=0.1500, required>=0.9405` |
| **Receipt** | `pytest tests/momentum/core/test_alignment_contract.py::test_validate_alignment_low_label_coverage_raises` PASS |

---

### ADV-B1-02 — `rng(0)` 系統性漏抽樣

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-02 |
| **Status** | **CLOSED** |
| **Probe** | 200 列 lag=1、`sample_size=64`；掃描 middle rows 2..197 單點腐化（`shifted.iloc[k]=labels.iloc[k+1]`） |
| **重跑輸出** | `total=196 caught=196 missed=0 leak_rate=0.0000`（原 review：135/196 漏網） |
| **加驗** | `grep rng/default_rng` in `_sample_alignment_positions` → 無；`ADV-B1-02-rng-check: CLOSED` |

---

### ADV-B1-03 — 變異敏感區強制抽樣

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-03 |
| **Status** | **CLOSED** |
| **Probe** | 180 列刪 index 90 造 gap；檢查 `_sensitive_alignment_rows` 含 gap 邊界 {89,90}；各邊界列單點 ±1 bar 腐化 |
| **重跑輸出** | `sensitive_contains=True sensitive_rows=[...,89,90]`；`per_boundary={89: RAISE label mismatch, 90: RAISE label mismatch}` |
| **Receipt** | `test_validate_alignment_gap_boundary_single_point_mismatch_raises` PASS |

---

### ADV-B1-04 — close 軸缺孔 skip（非 hard raise）

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-04 |
| **Status** | **CLOSED** |
| **Probe** | (A) 原 review 24 列刪 1 孔 + label NaN；(B) Codex 300 列刪孔 + label NaN；(C) pytest hermetic |
| **重跑輸出** | (A) `RAISE target coverage too low: actual=0.9167, required>=0.9487` — **無** `missing from close axis` hard raise；(B) `PASS checked=60` skip oracle 續跑；(C) `test_validate_alignment_missing_close_positions_skip_oracle PASSED` |
| **判定** | 邊界②行為已實現：缺孔列 skip oracle；label NaN 交覆蓋率閘門（小樣本可 fail-closed 於覆蓋率，非軸缺失 raise） |

---

### ADV-B1-05 — M1 單點錯位 hermetic + 改壞會紅

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-05 |
| **Status** | **CLOSED** |
| **Probe** | `test_validate_alignment_m1_single_point_misalignment_raises`（200 列 row=100 單點腐化）；mutation 驗證 |
| **重跑輸出** | 正常：`1 passed`；`patch(contracts.np.isclose, True)` → `FAILED: DID NOT RAISE`；還原 `rng(0)` 抽樣 → `FAILED: DID NOT RAISE` |
| **判定** | 測試存在、固定 kernel 下 PASS；oracle/抽樣改壞必紅 |

---

## 加驗：確定性分層抽樣盲區全掃描

| Field | Value |
|-------|-------|
| **ID** | ADV-B1-02+03-BLIND-SCAN |
| **Status** | **CLOSED** |
| **Probe** | 200 列 lag=1：列出 `sampled_set` 未覆蓋之中間列 140 列，對每列單點腐化全掃（非抽查） |
| **重跑輸出** | `unscanned_middle_rows=140 blind_spots_after_full_corruption_scan=0 blind_spot_rows=[]` |
| **判定** | 未入 sample 的列腐化仍被 oracle 捕獲（敏感區+等距層覆蓋有效）；無新盲區 |

---

## Summary

| ID | Status | 原洞 | 重跑關鍵指標 |
|----|--------|------|-------------|
| ADV-B1-01 | CLOSED | 覆蓋率門檻缺失 | 80 孔 → coverage raise |
| ADV-B1-02 | CLOSED | rng(0) 漏網 135/196 | 漏網 0/196 |
| ADV-B1-03 | CLOSED | 無變異敏感區 | gap 邊界強制抽樣 + 單點 raise |
| ADV-B1-04 | CLOSED | close 缺孔 hard raise | skip + 覆蓋率（300 列 PASS） |
| ADV-B1-05 | CLOSED | M1 單點不可證偽 | hermetic 存在；isclose/rng 改壞 → RED |
| BLIND-SCAN | CLOSED | — | 140 未抽樣列腐化全捕 |

5/5 BLOCKING 閉合；確定性分層抽樣全掃無盲區。

---

## VERDICT

**APPROVE** — Codex B1 fix 閉合全部 5 項 BLOCKING；kernel 可進 B2 接線。

Verdict: APPROVE
