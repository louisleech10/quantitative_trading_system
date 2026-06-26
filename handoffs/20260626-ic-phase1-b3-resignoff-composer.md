# IC Phase 1 B3 — Composer 獨立重簽核（round-2 修補後）

> **Reviewer**: Composer（adversarial 心態，非簽核式掃描）  
> **Scope**: `momentum/core/contracts.py`（validate_split_integrity / validate_split_pair_integrity / split_per_symbol）、`momentum/Analysis/ic_split_adapter.py`、對應測試  
> **Baseline**: Codex round-1 自挑戰 6 LEAK → round-2 修補（`handoffs/20260626-ic-phase1-b3-signoff-RESULT.md`）  
> **Date**: 2026-06-26

---

## Verdict

**資料正確：PASS**

Codex 抓到的 L1–L6 六條洩漏向量在 round-2 修補後**均已關閉**（程式邏輯 + 真實 kline 反例 + 自構 adversarial probe）。未發現等同嚴重度的**新洩漏洞**足以 BLOCK B3。

**殘餘風險（非 B3 回修阻塞，列為 follow-up）**見 §Residual。

---

## 方法

1. 逐函式讀修補後源碼（非只看測試名）。
2. 跑既有 20 項 pytest（真實 `kline_cache.h5`）。
3. 自構 15 組 adversarial probe（含 Codex 原 LEAK 變體 + 新攻擊面），實跑 Python 腳本驗證 fail-closed / 刻意 bypass 嘗試。
4. 對照 SPEC §1.3/§1.4 與 TODO B3 驗收條款。

---

## L1–L6 逐項重驗

### L1 — rows purge 必須 expected_freq（gap 不可 silent 放過）

**原 LEAK**: `expected_freq=None` + `purge_semantic=rows` 時 gap 偵測被短路。

**修補**（`contracts.py:450-453`）:
```python
if plan.purge_semantic == "rows" and plan.expected_freq is None:
    raise TimestampDiscontinuityError(...)
```

**驗證**:
- 測試 `test_l1_rows_purge_requires_expected_freq` PASS。
- **ADV-1（gap + timedelta + no freq）**: 刻意 bypass → **PASS by design**（SPEC §1.3：gap 模式須 `purge_semantic=="timedelta"`，Phase 1 不實作 timedelta purge 數學）。
- **ADV-2（wrong freq 過大）**: `expected_freq="7D"` 於 1h 連續資料 + 刪 3 bar gap → **仍 PASS gap 檢查**（max_gap=4h < 7D×1.05）。這是 **caller 誤設 freq** 的 footgun，**不是 L1 原 bug 復活**；B5/B6 已列「expected_freq 須從 timeframe 推導」→ §Residual R1。

**判定**: ✅ **關閉**（原 LEAK 路徑已 raise；錯 freq 屬配置風險）。

---

### L2 — train/test pair-level purge+embargo 禁止區

**原 LEAK**: 只驗單 plan，train 可踩 test purge/embargo 區。

**修補**（`contracts.py:492-520`）:
- 新增 `validate_split_pair_integrity(train_plan, test_plan, ts, symbols)`。
- 對 test 每段 contiguous range 建 `[start-purge_gap, end+purge_gap+embargo)` 半開區間，assert train row 不落入。
- `split_per_symbol` / adapter `_build_plan_pair` 皆呼叫 pair 校驗。

**Adversarial probes**:
| Probe | 攻擊 | 結果 |
|-------|------|------|
| ADV-3 | train row 11 落在 test [10,13) + embargo | `SplitPairLeakageError` ✅ |
| ADV-7 | 非連續 test 兩段，train 落 purge 區 | `SplitPairLeakageError` ✅ |
| ADV-15 | train==test 完全相同 | `SplitPairLeakageError` ✅ |
| ADV-8 | timedelta semantic，train@11 在 test 內 | `SplitPairLeakageError` ✅ |

**判定**: ✅ **關閉**。

---

### L3 — 空 row_index 不可繞過 symbol 必填

**原 LEAK**: `row_index.size==0` 提早 return，跳過 `symbol is None` 檢查。

**修補**（`contracts.py:447-460`）: **先**驗 `plan.symbol` + rows/expected_freq，**再** empty return。

**Adversarial probes**:
- `test_l3_empty_row_index_still_requires_symbol` PASS（symbol=None → raise）。
- **ADV-5**: 空 train + 合法 symbol → 單 plan `validate_split_integrity` PASS；但 `validate_split_pair_integrity` 要求 non-empty（504-505）→ adapter 路徑 fail-closed ✅。

**判定**: ✅ **關閉**（契約層允許空 plan 建構，但 production 路徑 pair 強制 non-empty）。

---

### L4 — NaN / bytes symbol fail-closed

**原 LEAK**: bytes 靜默通過；NaN symbol 被 `groupby(dropna=True)` 丟棄。

**修補**:
- `_normalize_symbol_value` / `_normalize_symbol_array`（396-418）：None/NA/空 str/非法 bytes → `CrossSymbolLeakageError`。
- `split_per_symbol` / adapter：`groupby(..., dropna=False)` + frame 入場正規化。

**Adversarial probes**:
| Probe | 結果 |
|-------|------|
| `test_l4_nan_symbol_group_fails_closed` | PASS ✅ |
| `test_l4_bytes_symbol_decodes_before_purity_check` | PASS ✅ |
| ADV-6 NaN 在 universe 但不在 row_index | `_normalize_symbol_array` 全陣列掃描 → raise ✅ |
| ADV-11 NaN 在 DataFrame symbol 欄 | `split_per_symbol` → raise ✅ |
| ADV-14 plan.symbol=BTC 但 row_index 指 ETH rows | `CrossSymbolLeakageError` ✅ |

**判定**: ✅ **關閉**。

---

### L5 — WF 跨 fold embargo

**原 LEAK**: adapter 只寫 embargo metadata，不檢查後續 fold train 是否踩前 fold test 後 embargo 區。

**修補**（`ic_split_adapter.py:132-141, 365-385`）:
- `_assert_wf_cross_fold_embargo`: 對每個 prior `(test_start, test_end)`，assert 當前 train ∉ `[test_end, test_end+embargo_len)`。

**驗證**:
- `test_l5_wf_cross_fold_embargo_violation_raises`（embargo_pct=0.02, 220 bars）→ `EmbargoRelaxedError` PASS ✅。
- **ADV-10**（embargo_pct=0.001 極小）: adapter PASS — 因 rolling WF 的 train 窗口與 embargo 區不重疊（數學上合法，非 silent bypass）。

**ADV-9（重要澄清，非 L5 回歸）**:
- Rolling WF fold1 train `[40,120)` **包含** fold0 test `[85,115)` 共 30 rows。
- adapter **不檢**「later train 含 prior test 本體」— 這是 ML 孤島 `_generate_rolling_splits` 的 **rolling window 語意**（SPEC §1.4：不改 WF 內部邏輯，只讀 range tuple）。
- L5 修補目標是 **embargo 帶**（test 結束後 N rows），不是禁止 expanding/rolling train 含歷史 test 期。**非 B3 新 LEAK**；若 Phase 1 要禁止 prior-test-in-train 需另開 1a scope → §Residual R2。

**判定**: ✅ **關閉**（L5 定義的 embargo 向量已擋）。

---

### L6 — CPCV test boundary 獨立重建

**原 LEAK**: strict check 只信 returned test；splitter 改邊界且 train 一致則漏。

**修補**（`ic_split_adapter.py:311-362`）:
- `_expected_cpcv_test_group_sets` + `_compute_group_boundaries` 依 config 重建 expected test indices。
- `max_paths` 子集用 `np.random.default_rng(42)` — **與** `combinatorial_purged_cv.py:59` **同 seed** ✅。

**驗證**:
- `test_l6_cpcv_test_boundaries_rebuilt_independently`（`_FakeShiftedCPCV` 偏移 test）→ `EmbargoRelaxedError` PASS ✅。
- ADV-13 `max_paths=5` 多 symbol：8 pairs（BTC+ETH 各 4 fold），邊界對齊 ✅。

**判定**: ✅ **關閉**。

---

## 測試執行

```bash
pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py -v
# 20 passed in 0.39s（真實 kline_cache.h5）
```

解耦：`grep -r "from api\." momentum/` → 0（目視 + 既有慣例）。

---

## §Residual — 殘餘風險（不 BLOCK B3）

| ID | 風險 | 嚴重度 | 說明 |
|----|------|--------|------|
| R1 | 錯誤 `expected_freq` 過大可放 gap | MINOR | ADV-2 實證；需 B5/B6 從 timeframe 推導 SSOT，禁 caller 隨意填 |
| R2 | Rolling WF later-train ⊃ prior-test | DOCUMENTED | ADV-9；ML 孤島設計，SPEC 明確不改 WF 數學；非 L5 範圍 |
| R3 | `split_per_symbol` 無專項 pytest | MINOR | HANDOFF 已列 G3 待補；函式邏輯與 adapter 同构且 L4 探針已覆蓋 |
| R4 | `validate_split_pair_integrity` 只用 `test_plan.embargo` | LOW | adapter/split_per_symbol 雙 plan 同源寫入；手動構 plan 可不一致 — 非 production 路徑 |
| R5 | `split_per_symbol` 空 splitter 回 `[]` 靜默 | LOW | ADV-12；caller 責任，adapter 對空 plans raise |

---

## 與首輪 Composer PASS 的差異

首輪簽核式 review 漏掉 Codex adversarial 6 LEAK（HANDOFF 已記 [[feedback_adversarial_beats_signoff]]）。本輪：

1. **每條 LEAK 對照修補行號 + 自構反例**（非只 grep 測試名）。
2. **主動攻擊** wrong-freq、WF prior-test overlap、asymmetric embargo、multi-symbol CPCV、NaN frame 等 15 probes。
3. 區分「修補未關閉」vs「SPEC 已知/deferred」vs「ML 孤島語意」。

---

## 結論摘要

| LEAK | Round-2 狀態 | Composer 重簽 |
|------|-------------|---------------|
| L1 rows+freq | raise if rows & freq=None | ✅ PASS |
| L2 pair-level | validate_split_pair_integrity | ✅ PASS |
| L3 empty bypass | symbol before empty return | ✅ PASS |
| L4 NaN/bytes | normalize + dropna=False | ✅ PASS |
| L5 WF embargo | _assert_wf_cross_fold_embargo | ✅ PASS |
| L6 CPCV boundary | independent rebuild + seed 42 | ✅ PASS |

**Verdict: 資料正確 PASS** — B3 round-2 修補可進 B4；R1/R3 建議 B5/B6 接線時補強，R2 若產品要禁 rolling-test-in-train 需另開 1a。

---

```
ASSUMPTIONS_VERIFIED: L1-L6 修補行為用真實 kline + 15 adversarial probes 實跑；CPCV max_paths seed 與源碼一致；WF rolling overlap 為 ML 孤島設計非 patch 回歸
TESTS_RUN: pytest tests/momentum/core/test_split_contract.py tests/momentum/Analysis/test_ic_split_adapter.py → 20/20 PASS
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀 review + 本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE
