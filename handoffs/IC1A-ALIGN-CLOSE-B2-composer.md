# IC1A-ALIGN-CLOSE-B2 — Composer 複驗（B2 三 BLOCKING）

**task-id**: `ic1a-align-close-b2`  
**agent**: Composer | **date**: 2026-07-09  
**basis**: Codex 補完 `handoffs/IC1A-ALIGN-FIX2-B2-RESULT.md`；對照原 BLOCKING `handoffs/IC1A-ALIGN-REVIEW-B2-composer.md`（B2-2.2-03 / B2-M5 / B2-DTYPE-01）

---

## 複驗摘要

| ID | 狀態 | 一句話 |
|----|------|--------|
| B2-2.2-03 / M4 | **CLOSED** | `test_alignment_gate_stage0_wrong_tf_raises` 存在；noop gate mutation 實測轉紅 |
| B2-M5 | **CLOSED** | `test_alignment_gate_m5_dual_leg` 雙腿設計符合 SPEC；腿 B noop 實測 AssertionError |
| B2-DTYPE-01 | **CLOSED** | stage0/stage2 皆 `to_numpy(copy=False)`；dtype hermetic 測試 PASSED |

**VERDICT**: 三項原 BLOCKING 均已補齊且可證偽；建議核准 B2 Gate 關閉。

---

## 1) B2-2.2-03 / M4 — `test_alignment_gate_stage0_wrong_tf_raises`

**狀態: CLOSED**

**存在性**
- `tests/momentum/test_ic_filter_orchestrator.py:600-645`：`test_alignment_gate_stage0_wrong_tf_raises`
- 設計：120-row 12h features（43_200s cadence）+ 1h labels（3_600s cadence，`(n-1)*12+1` bars）；`_log_return_config()` 啟用 Tier-2 log oracle + `_DummyReader` kline；期望 `AlignmentViolationError`

**實跑（gate ON）**
```bash
pytest tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_stage0_wrong_tf_raises -v --tb=short
# → PASSED (0.74s batch with siblings)
```

**Mutation（放行錯 tf / noop gate → 應轉紅）**
- 探針：`validate_alignment` monkeypatch 為 no-op `AlignmentReport` 後呼叫同 fixture → `_stage0_ingestion` **未** raise（`M4_noop_allows_wrong_tf_pass=True`）
- pytest 同 mutation：`pytest ...::test_alignment_gate_stage0_wrong_tf_raises` → **FAILED** `DID NOT RAISE AlignmentViolationError`（`:643`）

**依據**: 測試覆蓋 stage0 整合路徑 cadence mismatch；若 gate 被繞過或錯 tf 被放行，測試必紅。非僅 kernel 單元測 `test_validate_alignment_cadence_mismatch`。

---

## 2) B2-M5 — `test_alignment_gate_m5_dual_leg`

**狀態: CLOSED**

**存在性與雙腿設計**
- `tests/momentum/test_ic_filter_orchestrator.py:648-703`：`test_alignment_gate_m5_dual_leg`
- **腿 A**（`:682-694`）：M1 錯位 — `shifted_returns = r_[correct[1:-1], correct[0], nan]`；`_assert_gate_rejects_shifted_labels()` 以 `AlignmentViolationError` 設 `rejected=True` 斷言
- **腿 B**（`:696-703`）：`monkeypatch.setattr(orchestrator_module, "validate_alignment", _noop_validate)` 後再呼叫同一 helper → `pytest.raises(AssertionError, match="did not reject shifted labels")`

**實跑**
```bash
pytest tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_m5_dual_leg -v --tb=short
# → PASSED
```

**腿 B 有效性（noop 時必 FAIL）**
- 探針：腿 A `M5_legA_rejects_shift=True`；noop 後 `M5_noop_allows_shifted_pass=True` → `_assert_gate_rejects_shifted_labels` 內 `assert rejected` 失敗，對應測試腿 B 的 `AssertionError`
- 腿 B **不是**僅重跑腿 A 期望 pass，而是明確要求「noop 下仍須被拒」的斷言失敗 — 符合 SPEC §V 雙腿 mutation 意圖

**依據**: 同資料、同 helper；gate ON 抓 M1 錯位；gate no-op 時測試邏輯轉紅，可證偽 gate 接線失效。

---

## 3) B2-DTYPE-01 — stage0 close dtype 與 stage2 一致

**狀態: CLOSED**

**Code 對照**
- stage0 Tier-2 close（`momentum/Analysis/ic_filter_orchestrator.py:1776-1778`）：
  `raw_data["close"].to_numpy(copy=False)`
- stage2 kline close（`:1843-1845`）：
  `raw_data["close"].to_numpy(copy=False)`
- `grep astype(np.float64)` 於 `ic_filter_orchestrator.py` → **0 命中**（stage0 不再強制 float64）

**Hermetic dtype 測試**
- `tests/momentum/test_ic_filter_orchestrator.py:706-765`：`test_alignment_gate_stage0_and_stage2_close_preserve_raw_dtype`
- monkeypatch `validate_alignment` 捕捉 `close.dtype`；依序跑 `_stage0_ingestion` + `_stage2_label_generation`
- 斷言：`:765` `captured_close_dtypes == [np.dtype("float32"), np.dtype("float32")]`

**實跑**
```bash
pytest tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_stage0_and_stage2_close_preserve_raw_dtype -v --tb=short
# → PASSED
```

**Regression 邏輯**
- 若 stage0 改回 `astype(float64)`，捕捉序列為 `[float64, float32]`，assert 必敗（`dtype_test_would_fail_on_stage0_float64=True`）

**依據**: 兩路徑 close 建構語意一致；hermetic 測試直接驗證傳入 `validate_alignment` 的 dtype，補足 `_assign_datetime_index_preserving_values` 不涵蓋 close 的缺口（B2-DTYPE-02 註記仍有效、非本次 BLOCKING）。

---

## TESTS_RUN（本次複驗）

```bash
pytest tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_stage0_wrong_tf_raises \
  tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_m5_dual_leg \
  tests/momentum/test_ic_filter_orchestrator.py::test_alignment_gate_stage0_and_stage2_close_preserve_raw_dtype \
  -v --tb=short
# → 3 passed in 0.74s
```

Mutation probes（Python 腳本，非 pytest 用例）：M4 noop → pass without raise；M5 noop → shift allowed；均已記錄於上各節。

---

## ASSUMPTIONS_VERIFIED

- B2 FIX2 三測試已入庫且與 Codex RESULT 描述一致
- `_log_return_config()` 為 M4/M5 必要條件（Tier-2 log oracle + kline_reader）
- stage0/stage2 close 均以 `to_numpy(copy=False)` 保留 raw kline dtype

## SCOPE_CHANGES

none（只讀 code + 跑測試 + 寫本檔）

## NUMERIC_OR_SCHEMA_IMPACT

無新增變更；確認 stage0 close 不再強制 float64，與 FIX2 RESULT 一致。

---

**VERDICT**: 三 BLOCKING 全部 **CLOSED**；B2 Gate 可核准。

Verdict: APPROVE
