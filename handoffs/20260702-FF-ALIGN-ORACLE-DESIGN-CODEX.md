# FF align lookahead oracle 設計 — Codex 委員會意見

## 已讀/已驗
- 已讀 `HANDOFF.md`、`CLAUDE.md`、`handoffs/20260702-FF-ALIGN-ORACLE-FACTS.md`、`tests/feature_engineering/ff_truncation_mr_helpers.py`。
- 實測殘留真實 run：`raw/*.parquet` 是每特徵/每 group 檔，index 為 `RangeIndex(0..n-1)`，不能拿來當 timestamp。
- 挑戰事實檔：`raw/timestamps.parquet` 確實不存在，但 `run_dir/timestamps.parquet` 真實存在；`feature_manifest.json.row_index = {"path":"timestamps.parquet","unit":"s","count":row_count}` 指向它。
- production 來源：`FeatureStorage._write_row_index_artifact()` 寫 `run_dir/timestamps.parquet`，欄名 `timestamp`，epoch seconds；`FeatureFactory._derive_row_index_for_artifact()` 從真 raw_data index/欄位轉 DatetimeIndex。

## Oracle 正確輸入
- 時間戳來源：讀 `pair.trunc.manifest["row_index"]["path"]`，相對於 `pair.trunc.run_dir`，即 `<features_root>/BTCUSDT/1h/<config_hash>/timestamps.parquet`；驗 `unit == "s"`、`count == pair.trunc.row_count`、實際列數等於 `pair.n_trunc`。
- 12h 邊界 index：對上面 timestamp array 呼叫既有 `_primary_indices_at_12h_boundaries(ts_vals, warmup=pair.warmup, n_trunc=pair.n_trunc)`；不要從 per-feature parquet index 推時間。
- coarse 欄值來源：讀同名 raw parquet：`pair.full.raw_dir / fname` 與 `pair.trunc.raw_dir / fname`，其中 `fname` 來自 `_build_column_frame_map()`。
- 檔名/欄名 pattern：coarse 檔案可為 `12h_*.parquet`、`4h_*.parquet` 或含 chunk suffix；欄名含 `_<tf>_`，例如 `ms_12h_amihud_illiq_5`、`close_4h_*`。現有 `_coarse_tf_from_column()` 與 `_select_required_probe_columns(..., align_coarse_tfs=["4h","12h"])` 可沿用。
- full 值取 `full_col.to_numpy()[:pair.n_trunc][idx]`；trunc 值取 `trunc_col.to_numpy()[idx]`。絕不可用 row_count/hash 猜 full/trunc。

## 為何注入後必 mismatch
- 注入點 `_lookahead_build_asof_index_map()` 對有效 source index 做 `+1` 並 cap 到最後一列。
- 在 `open_minus` 下，12h 邊界的 1h bar open/close 關係使正常映射剛好切到上一根已收 12h；注入會讀下一根 coarse source。
- 此 mutation 僅套在 `align_lookahead_side="trunc"`，所以同一 primary boundary row 上，full=因果 coarse 值、trunc=forward coarse 值；只要該 coarse 欄相鄰 source 值非完全相同且非雙 NaN，就應超過 `FLOAT16_RTOL/FLOAT16_ATOL`。
- 若全部 probe 欄無 mismatch，這是 oracle/setup 失敗或 selected probe 太弱，應 raise 清楚錯誤，不可讓外層 `pytest.raises` 吃掉。

## Composer 實作規格
在 `tests/feature_engineering/ff_truncation_mr_helpers.py` 新增：

```python
def _read_artifact_timestamps(artifact: GenerationArtifacts) -> np.ndarray:
    """讀 feature_manifest row_index 指向的 primary timestamp sidecar（epoch seconds）。"""
```

行為：
- `row_index = artifact.manifest.get("row_index") or {}`；若缺 path/count/unit，raise `AssertionError("align oracle: missing row_index ...")`。
- `ts_path = artifact.run_dir / str(row_index["path"])`；禁止讀 `artifact.raw_dir / "timestamps.parquet"`。
- 檢查檔案存在、第一欄可轉 `int64`、`unit == "s"`、`len(ts_vals) == int(row_index["count"]) == artifact.row_count`；失敗 raise `AssertionError`，訊息含 path/count/unit。
- return `ts_vals`。

替換：

```python
ts_vals = _read_artifact_timestamps(pair.trunc)
```

保留 `_assert_align_coarse_boundary_lookahead_detected(pair, align_coarse_tfs=...)` 函式簽名；其餘比對邏輯可沿用，但建議 mismatch 訊息加入 `ts=int(ts_vals[idx])` 方便定位。

## Smoke/測試調整
- 更新 `test_align_lookahead_oracle_smoke`：把 synthetic `timestamps.parquet` 寫在 `run_dir`，並在 `GenerationArtifacts.manifest` 放 `{"row_index":{"path":"timestamps.parquet","count":n_trunc,"unit":"s","tz":"UTC"}}`。
- 不要讓 production 產 `raw/timestamps.parquet`，不要新增合併大表。
- 驗證順序：先單跑 `pytest tests/feature_engineering/test_ff_multitf_truncation_mr.py::test_mutation_align_lookahead_fails -m requires_kline -vv --tb=short`，確認 oracle 不再報 missing timestamp 且能偵測 mismatch；再跑全 5 mutation probes receipt 版。

## 風險提醒
- 事實檔的「無 timestamps.parquet」若被 Composer 解讀成「整個 run 無 timestamp sidecar」會導致錯設計；正確表述是「raw 目錄無 timestamps.parquet，run_dir 有 manifest 指向的 sidecar」。
- per-feature parquet 的 RangeIndex 只能作列位置，不是時間軸；用它算 12h boundary 會假綠/假紅。
- 若 `row_index` sidecar 缺失，應 fail closed，而不是從 `time_range` 猜測固定 1h 步長，除非另開設計審查批准 fallback。

STATUS: DONE
