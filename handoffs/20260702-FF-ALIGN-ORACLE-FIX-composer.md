# FF align oracle 輸入修正 — Composer 實作

## 任務
依 `handoffs/20260702-FF-ALIGN-ORACLE-DESIGN-CODEX.md` Composer 規格，修正 oracle 時間戳來源：`run_dir/timestamps.parquet` + `feature_manifest.json` 的 `row_index`（禁止讀 `raw/timestamps.parquet`）。

## 改動

### `tests/feature_engineering/ff_truncation_mr_helpers.py`
- 新增 `_read_artifact_timestamps(artifact: GenerationArtifacts) -> np.ndarray`：
  - 從 `manifest.row_index` 取 `path`/`count`/`unit`；缺任一 → `AssertionError`。
  - 讀 `artifact.run_dir / path`（非 `raw_dir`）。
  - 驗 `unit == "s"`、`len(ts_vals) == row_index.count == artifact.row_count`。
- `_assert_align_coarse_boundary_lookahead_detected`：改呼叫 `_read_artifact_timestamps(pair.trunc)`；函式簽名與 v2 shape 不變。
- mismatch 訊息加入 `ts=int(ts_vals[idx])` 方便定位。

### `tests/feature_engineering/test_ff_multitf_truncation_mr.py`（smoke 調整）
- `test_align_lookahead_oracle_smoke`：`timestamps.parquet` 寫入 `run_trunc/`（非 `raw/`）；`trunc.manifest` 含 `row_index: {path,count,unit,tz}`。
- 明標 smoke、非驗收證據。

## 未改
- production 程式碼
- 其他 4 個 mutation 探針與主 MR / perturbation 測試

## 驗證（本腿，非慢測驗收）

| 命令 | 結果 |
|------|------|
| `python -m py_compile tests/feature_engineering/ff_truncation_mr_helpers.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` | PASS |
| `pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py --collect-only -q` | 9 collected |
| `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_multitf_truncation_mr.py` | exit 0 |
| `pytest ...::test_align_lookahead_oracle_smoke -vv` | **1 passed**（smoke，非全鏈驗收） |

## 留編排端
- `test_mutation_align_lookahead_fails` / `with_tail_perturb` 全鏈慢測（~30–40 分/個）確認 oracle 不再報 `missing timestamps.parquet in .../raw` 且注入可偵測 mismatch。
- receipt 版 `mutation_probe_check` 全 5 探針。

```
ASSUMPTIONS_VERIFIED:
- 真實管線 `row_index.path` 相對 `run_dir`（FACTS + DESIGN 已確認）；`_run_generation` 已載入 manifest 含 row_index。
- per-feature raw parquet 仍只用於 coarse 欄值比對；時間軸不再從 raw_dir 讀。

TESTS_RUN:
- py_compile 2 檔 PASS
- collect-only 9 tests
- mutation_probe_static exit 0
- test_align_lookahead_oracle_smoke 1 passed (smoke, 非驗收)

FAILURES_SEEN: none

SCOPE_CHANGES: smoke 測試檔 `test_ff_multitf_truncation_mr.py` 同步 fixture（規格要求）；其餘探針未動。

NUMERIC_OR_SCHEMA_IMPACT: none（測試 helper + smoke fixture only）
```

STATUS: DONE
