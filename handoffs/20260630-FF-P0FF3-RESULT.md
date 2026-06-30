# P0-FF-3 實作收尾 — Composer

## 變更摘要

1. **新建** `tests/feature_engineering/ff_truncation_mr_helpers.py`
   - 從 B2 抽出 TruncationPair/GenerationArtifacts/gates/批次 parquet 讀/分層抽樣
   - `_build_truncation_pair` 參數化 `primary_tf`/`training_tfs`/`symbol`/`align_margin`/`window_date_fn`
   - `_select_required_probe_columns` + `_assert_mutation_layer_coverage` 擴展對齊層（`4h`/`12h`）
   - `_assert_metadata_gate` 擴展 `expected_training_tfs`（`present_timeframes` + `config_used.training`）
   - `_bar_window_dates_at_12h_boundary`（align mutation 12h 收盤邊界選窗）
   - 常數 `ALIGN_MARGIN=12`、`FLOAT16_RTOL=2e-3` 等

2. **改** `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`
   - 改 `from ff_truncation_mr_helpers import ...`；行為不變（P0-FF-2）

3. **新建** `tests/feature_engineering/test_ff_multitf_truncation_mr.py`
   - config: `primary=1h`, `training=[1h,4h,12h]`, `open_minus`, BTCUSDT
   - window: `2051 + 10 + 20 + 12 = 2093`（實測 warmup=2051）
   - `test_c3_multitf_truncation_invariant` + tail perturb + 5 mutation（含 `test_mutation_align_lookahead_fails` 12h 邊界窗）
   - B2 center/winsor/lag mutation 改 multi-TF config 仍 `pytest.raises(AssertionError)`
   - `test_multitf_sampling_helper_smoke`（秒級合成 frame）

## 驗證（本腿已跑）

```bash
python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py \
  tests/feature_engineering/test_ff_fullchain_truncation_mr.py \
  tests/feature_engineering/test_ff_multitf_truncation_mr.py
# PASS

python scripts/mutation_probe_static.py \
  tests/feature_engineering/test_ff_fullchain_truncation_mr.py \
  tests/feature_engineering/test_ff_multitf_truncation_mr.py
# PASS (exit 0)

pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_b2_sampling_helper_smoke \
  tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_multitf_sampling_helper_smoke -q
# 2 passed in 0.38s

# 快速 sanity（非 pytest）
# warmup=2051 window=2093; 12h boundary window found on BTCUSDT/1h kline
```

## 留 Claude 驗（慢全鏈，timeout 14400）

```bash
pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -m requires_kline -v --tb=short
pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py -m requires_kline -v --tb=short
```

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - estimate_max_warmup_bars(1h,[1h,4h,12h])=2051; window=2093 (python 實跑)
  - _bar_window_dates_at_12h_boundary 在 BTCUSDT/1h 真 kline 找到合法窗
  - lookahead mutation 用 import-time 保存的 _ORIGINAL_BUILD_ASOF_INDEX_MAP 避免遞迴 patch
  - B2 helper smoke + multi-TF helper smoke PASS

TESTS_RUN:
  - py_compile 3 files PASS
  - mutation_probe_static.py 2 files PASS
  - pytest helper smoke 2/2 PASS

FAILURES_SEEN: none

SCOPE_CHANGES: none（僅測試 + helper；未改 production）

NUMERIC_OR_SCHEMA_IMPACT: none（測試/helper only）
```

STATUS: DONE

---

## METAFIX（2026-06-30）— metadata gate 對齊 columns gate

### 變更
- `ff_truncation_mr_helpers.py` `_assert_metadata_gate`：移除 `feature_schema_hash` 與 `total_features` exact 斷言（欄集差異已由 columns gate 有界把關；`total_features` 同源於欄計數，多 TF churn 會同樣矛盾）。
- 保留：symbol/tf、row_count 截斷預期、time_range end 變化、`expected_training_tfs`（present_timeframes + config_used.training）。

### 驗證（本腿）
```bash
python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py \
  tests/feature_engineering/test_ff_fullchain_truncation_mr.py \
  tests/feature_engineering/test_ff_multitf_truncation_mr.py
# PASS

pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_b2_sampling_helper_smoke \
  tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_multitf_sampling_helper_smoke -q
# 2 passed
```

### 留 Claude（慢全鏈 timeout 14400）
```bash
pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py -m requires_kline -v --tb=short
pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py -m requires_kline -v --tb=short
```

```
ASSUMPTIONS_VERIFIED:
  - columns gate 已接受有界 asymmetric churn；schema_hash/total_features exact 與之矛盾
  - 單 TF B2 欄集通常相同，移除斷言不改因果檢驗路徑

TESTS_RUN:
  - py_compile 3 files PASS
  - helper smoke 2/2 PASS

FAILURES_SEEN: none

SCOPE_CHANGES: none（僅 helper 一處）

NUMERIC_OR_SCHEMA_IMPACT: none（測試 gate 邏輯 only）
```

STATUS: DONE
