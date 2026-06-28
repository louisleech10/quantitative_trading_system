# B0 實作收尾 — FF 深稽 Task 0.1 + 0.2

**執行者**: Composer 2.5 | **日期**: 2026-06-27 | **範圍**: B0 治理地基 only

## Task 0.1 — requires_kline marker + 雙 job

### 改動
- `pytest.ini`: 註冊 `requires_kline` marker（缺檔 FAIL，PR smoke 用 `-m "not requires_kline"` 排除）
- `tests/conftest.py`: `requires_kline_data(symbol, tf)` factory fixture；缺檔/列數不足/manifest 漂移 → `pytest.fail`
- skip→marker 遷移（correctness 類，skip 改 fail + `@pytest.mark.requires_kline`）:
  - `tests/test_atomic_indicators.py`, `tests/test_talib_wrapper.py`
  - `tests/test_feature_factory_operators.py`, `tests/test_feature_factory_adapters.py`
  - `tests/feature_engineering/test_failopen_correctness.py`（14 測試；`test_v6_asof_oracle_boundary_cases` 保留無 marker）
  - `tests/feature_engineering/test_failopen_matrix.py`（6 matrix 測試；`test_v8_*` 保留無 marker）
  - `tests/feature_engineering/test_failopen_contract.py`（4 kline 測試；truth table 3 測試無 marker）
  - `tests/feature_engineering/test_failopen_layers.py`（module pytestmark）
  - `tests/feature_engineering/test_b6_warmup_trim.py`（11 kline 測試；unit 估計測試無 marker）
  - `tests/feature_engineering/test_mtf_align_golden.py`（3 real-generate；`test_before_baseline_*` 無 marker）
  - `tests/feature_engineering/preprocessing/test_ff_causal_golden.py`（1 測試）
  - `tests/feature_engineering/preprocessing/test_l65_native_tf_real_eth.py`（module pytestmark）
  - `tests/feature_engineering/test_batch2d_dstar_align.py`（3 測試）
  - `tests/feature_engineering/test_batch1_followup.py`（1 測試）

### 保留 skip（非 correctness / 環境依賴，理由）
| 檔案 | 理由 |
|------|------|
| `test_multi_symbol_ic_first.py` | 需 ≥N symbols 的 batch smoke，非單一 kline 正確性 |
| `test_batch_date.py` | API 整合，非 FF correctness |
| `test_feature_factory_optimization_e2e.py` | E2E 優化環境可選 |
| `test_feature_factory_optimization_perf.py` | perf tier opt-in |
| `test_polars_phase4.py` | polars 基礎設施探針 |

### 驗證
```bash
# marker 收集
pytest tests/feature_engineering/ -m requires_kline --collect-only -q
# → 66 collected

# smoke 排除
pytest tests/test_atomic_indicators.py -m "not requires_kline" --collect-only -q
# → 0 selected (5 deselected)

# mutation: 暫移 kline → FAIL 非 skip
mv data_cache/feature_klines/kline_cache.h5 /tmp/...
pytest tests/test_atomic_indicators.py::test_trend_indicator_engine
# → FAILED: missing market data for atomic indicator tests
```

## Task 0.2 — DATA_MANIFEST.json + 校驗器

### 改動
- `tests/fixtures/DATA_MANIFEST.json`: 10 symbol × 3 TF（1h/4h/12h），各含 `min_row_count` + `sha256`（h5py structured array `.tobytes()` 指紋）
- `tests/fixtures/data_manifest.py`: `validate_manifest`, `verify_kline_entry`, `compute_dataset_fingerprint`
- `tests/fixtures/test_data_manifest.py`: 健康路徑 + 3 mutation probe

### 驗證
```bash
pytest tests/fixtures/test_data_manifest.py -v
# 5 passed
```

### Mutation fail 摘要
| mutant | 預期 | 實測 |
|--------|------|------|
| sha256 → `0`*64 | `ManifestValidationError: sha256 mismatch` | PASS |
| 刪 manifest 一筆 | `missing from manifest` | PASS |
| min_row_count → 9_999_999 | `row_count < min_row_count` | PASS |

## 其他測試
```bash
pytest tests/fixtures/test_data_manifest.py tests/test_atomic_indicators.py tests/test_talib_wrapper.py -v
# 15 passed

pytest tests/feature_engineering/test_failopen_correctness.py::test_v6_asof_oracle_boundary_cases \
  tests/feature_engineering/test_mtf_align_golden.py::test_before_baseline_shows_lookahead -v
# passed（無 kline marker 測試仍可跑）
```

## 已知非本批
- `test_v8_frozen_doc_covers_every_existing_assertion_change` 失敗：既有 IC engine 變更未登記 frozen doc（`test_ic_engine.py::test_time_index_parsing_and_alignment`），與 B0 無關。

## §G v0 baseline
未凍結（B0 後、B1 前由後續 batch 處理）。

---

## B0-fix（Codex code review P0 補丁）— 2026-06-28

**執行者**: Composer 2.5 | **範圍**: P0-1 manifest marker + conftest KeyError 收斂

### P0-1 — manifest 測試補 `@pytest.mark.requires_kline`
- `tests/fixtures/test_data_manifest.py`：4 個讀真 kline 的測試掛 marker
  - `test_manifest_valid_passes_when_kline_present`
  - `test_mutation_wrong_sha256_fails`
  - `test_mutation_missing_symbol_tf_fails`
  - `test_mutation_row_count_below_min_fails`
- `test_manifest_file_is_versioned` 保留 smoke（只讀 JSON，不讀 kline）

### conftest KeyError 收斂
- `tests/conftest.py:75`：`except ManifestValidationError` → `except (ManifestValidationError, KeyError)`
- manifest 有 entry 但 h5 dataset 缺時，`verify_kline_entry` → `compute_dataset_fingerprint` 的 `KeyError` 轉 `pytest.fail` 明確訊息

### 驗證
```bash
pytest --collect-only -q tests/fixtures/test_data_manifest.py -m "not requires_kline"
# → 1 selected (test_manifest_file_is_versioned), 4 deselected

pytest --collect-only -q tests/fixtures/test_data_manifest.py -m requires_kline
# → 4 selected, 1 deselected

pytest tests/fixtures/test_data_manifest.py -v
# → 5 passed
```

### 未動
- P0-2 golden/parquet（已由 Claude 還原，未重新生成）
- B1/B2 範圍外檔案

