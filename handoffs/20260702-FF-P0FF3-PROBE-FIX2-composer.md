# P0-FF-3 align 探針 BLOCKING 修補 — Composer 收尾

## 背景

Codex review（`handoffs/20260702-FF-P0FF3-PROBE-REVIEW-CODEX.md`）BLOCKING：兩個 align mutation 探針把 `_build_truncation_pair`、`_assert_align_coarse_boundary_lookahead_detected`、`_assert_truncation_invariants` 全包進同一個寬 `pytest.raises(AssertionError)`。oracle 在「找不到 coarse 欄 mismatch」時也 raise AssertionError（`ff_truncation_mr_helpers.py:1259-1263`），導致注入失效（monkeypatch 未生效 / side 被移除）時 pair 退化為 baseline、oracle 報 no mismatch、探針仍通過 = 無牙齒卻綠。

## 修法（照 Codex 指定 shape）

**檔案**：`tests/feature_engineering/test_ff_multitf_truncation_mr.py`

兩個探針（`test_mutation_align_lookahead_fails`、`test_mutation_align_lookahead_with_tail_perturb_fails`）改為：

1. 先 `_build_truncation_pair(..., align_lookahead_side="trunc", ...)` 建注入後 pair（在 `pytest.raises` 外）。
2. `_assert_align_coarse_boundary_lookahead_detected(pair, ...)` **移出** `pytest.raises` — 正向通過；注入失效 → 此 assertion 直接 fail → 探針紅。
3. **僅** `_assert_truncation_invariants(...)` 包進 `with pytest.raises(AssertionError)` — look-ahead 應使 MR 不變量失敗。

未改：baseline 測試（`test_c3_*`）、其他探針（center/winsor/lag）、production、`ff_truncation_mr_helpers.py`。

## 結構對照

| 步驟 | 修前 | 修後 |
|------|------|------|
| build pair | 在 `pytest.raises` 內 | 在 `pytest.raises` 外 |
| oracle | 在 `pytest.raises` 內（no-mismatch 可被吞） | 在 `pytest.raises` 外（必須正向通過） |
| MR invariants | 在 `pytest.raises` 內 | 單獨在 `pytest.raises` 內 |

## 驗證邊界

未跑 `requires_kline` / `generate_features` 全鏈慢測（~25 分/探針）；receipt 版 mutation_probe_check 全 5 探針由編排端執行。

---

ASSUMPTIONS_VERIFIED: 讀取 FIX2-PROMPT + Codex REVIEW；確認 oracle no-mismatch 路徑為 AssertionError；diff 僅動兩個 align 探針的 `pytest.raises` 範圍。
TESTS_RUN:
- `PYTHONPYCACHEPREFIX=/private/tmp/pycache_ff_fix2 python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` → pass
- `pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py --collect-only -q` → 9 collected
- `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` → exit 0
- smoke（非驗收）: `pytest ...::test_align_lookahead_oracle_smoke ...::test_multitf_sampling_helper_smoke -q` → 2 passed
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 `test_ff_multitf_truncation_mr.py` 兩函式）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
