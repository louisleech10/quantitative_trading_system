# P0-FF-3 align 探針修牙 — Composer 收尾

## 根因確認（與 prompt 一致）

讀 `test_mutation_align_*` + `ff_truncation_mr_helpers._build_truncation_pair`：舊探針在 `_build_truncation_pair` 前 `monkeypatch.setattr(TimeframeAligner.build_asof_index_map, +1)`，full 與 trunc 兩次 `generate_features` 皆走同一偏置 → `[warmup:n_trunc)` MR 比較區差異抵消 → `pytest.raises(AssertionError)` 不觸發（`DID NOT RAISE`）。與 traceback b8uou6xj6 定性一致。

## 修向選擇

**A + B 併用**：

- **A（不對稱注入）**：`align_lookahead_side="trunc"` 僅 trunc 跑帶 +1 forward `build_asof_index_map`；full 跑還原因果對齊。理由：直接消除對稱抵消根因，讓 MR 比較能看到單側偏置。
- **B（oracle 直斷）**：`_assert_align_coarse_boundary_lookahead_detected` 在已知 12h 邊界 primary index 比對 4h/12h coarse probe 欄 full vs trunc。理由：fail 訊息可讀（`fname::col idx=N full=… trunc=…`），不依大抽樣自然命中。

## 改動摘要

| 檔案 | 變更 |
|------|------|
| `tests/feature_engineering/ff_truncation_mr_helpers.py` | `align_lookahead_side` 參數；`_lookahead_build_asof_index_map` / `_set_align_lookahead_patch`；`_assert_align_coarse_boundary_lookahead_detected` + `_primary_indices_at_12h_boundaries` |
| `tests/feature_engineering/test_ff_multitf_truncation_mr.py` | 重寫 `test_mutation_align_lookahead_fails`、`test_mutation_align_lookahead_with_tail_perturb_fails`（不對稱注入 + oracle + 保留 `_assert_truncation_invariants`）；新增 `test_align_lookahead_oracle_smoke`（synthetic，非驗收） |

未改 production、未改其他探針/主 MR/perturbation 測試。

## TESTS_RUN

```
python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py
→ exit 0

python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_multitf_truncation_mr.py
→ exit 0（5 支 test_mutation_* 靜態 PASS）

pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py --collect-only -q
→ 9 tests collected

pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_align_lookahead_oracle_smoke tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_multitf_sampling_helper_smoke -q
→ 2 passed（smoke,非驗收證據）

# 未跑：generate_features 全鏈 mutation_probe_check / requires_kline 慢測（依派工鐵律由編排端驗收）
```

## FAILURES_SEEN

- `test_align_lookahead_oracle_smoke` 首輪：synthetic timestamp 未落 12h 邊界 → fixture assert 失敗；改為 `2026-01-01 11:00:00` 起算 1h 序列後 PASS。

## SCOPE_CHANGES

- 為不對稱注入新增 helpers 輔助（`align_lookahead_side`、oracle 斷言）；探針本體仍在 `test_ff_multitf_truncation_mr.py`。無 production 變更。

## NUMERIC_OR_SCHEMA_IMPACT

none

## 編排端待辦

receipt 版 `mutation_probe_check` 全 5 探針（4h timeout）+ Codex review diff。

STATUS: DONE
