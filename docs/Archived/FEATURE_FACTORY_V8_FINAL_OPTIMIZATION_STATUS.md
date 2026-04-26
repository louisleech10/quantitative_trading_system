# Feature Factory V8 Final 優化狀態檢查表

> **目的**：作為日後檢查 Feature Factory 各項優化是否完整保留、預設啟用的單一依據。
> **最後驗證**：2026-04-26
> **驗證命令**：`./venv/bin/pytest tests/ -k "feature_factory or feature_preprocessor or feature_extractor or feature_validator or microstructure or large_trade or phase_d or cgsa or atomic or layer1 or layer2 or layer3 or layer4 or layer5 or layer6 or layer7 or preprocessor"` → **381 passed / 0 failed**
> **目標環境**：MacBook M1 8 GB（最嚴苛 tier；其他 tier 自動放寬）
> **驗證原則**：跨 tier 重複穩定 + 不 OOM + 最高品質 + 最短時間 + 最小輸出檔案

---

## 🟢 1. OOM 防護機制（記憶體穩定性）

| # | 機制 | 檔案 | 行 | 預設 | 狀態 |
|---|------|------|----|------|------|
| 1.1 | L3 rolling memmap (streaming persist) | [operators/rolling_aggregator.py](../momentum/FeatureEngineering/operators/rolling_aggregator.py) | 166 | 自動 | ✅ |
| 1.2 | MultiTF align memmap | [timeframe/tf_aligner.py](../momentum/FeatureEngineering/timeframe/tf_aligner.py) | 181, 325 | 自動 | ✅ |
| 1.3 | L6.5 chunked memmap | [preprocessing/feature_preprocessor.py](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 691 | 自動 | ✅ |
| 1.4 | `_combine_layers` memmap concat | [feature_factory.py](../momentum/FeatureEngineering/feature_factory.py) | 1683 | 自動 | ✅ |
| 1.5 | dedup memmap-safe contiguous-range copy | [feature_factory.py](../momentum/FeatureEngineering/feature_factory.py) | 1705 | 自動 | ✅ |
| 1.6 | spill memmap (fallback) | [feature_factory.py](../momentum/FeatureEngineering/feature_factory.py) | 254 | 自動 | ✅ |
| 1.7 | MultiTF generator memmap | [timeframe/multi_tf_generator.py](../momentum/FeatureEngineering/timeframe/multi_tf_generator.py) | 950 | 自動 | ✅ |
| 1.8 | Block-row 複製 + 心跳日誌（避免 7h 靜默卡死） | [memmap_utils.py](../momentum/FeatureEngineering/memmap_utils.py) | 48 | `FFACT_MEMMAP_COPY_BLOCK_ROWS=1024` | ✅ |
| 1.9 | `_apply_timeframe_tag` 不再跳過 `meta_*`（避免 dedup→11.7GB copy） | feature_factory.py / multi_tf_generator.py | — | 自動 | ✅ |
| 1.10 | MultiTF worker 結束前 `persist+del+gc` per layer | [timeframe/multi_tf_generator.py](../momentum/FeatureEngineering/timeframe/multi_tf_generator.py) | 1071 | 自動 | ✅ |
| 1.11 | MultiTF worker 只回傳 metadata + .npy 路徑（不傳大陣列） | [timeframe/multi_tf_generator.py](../momentum/FeatureEngineering/timeframe/multi_tf_generator.py) | 1126, 542 | 自動 | ✅ |
| 1.12 | MultiTF align block 行控制 | [timeframe/multi_tf_generator.py](../momentum/FeatureEngineering/timeframe/multi_tf_generator.py) | 698 | `FFACT_MULTI_TF_ALIGN_BLOCK_ROWS=1024` | ✅ |
| 1.13 | TF merge chunk 大小 | [timeframe/tf_aligner.py](../momentum/FeatureEngineering/timeframe/tf_aligner.py) | 253 | `FFACT_MERGE_CHUNK_SIZE=5000` | ✅ |

---

## 🟢 2. Hardware Tier 自動降載（[utils/hardware_utils.py](../momentum/FeatureEngineering/utils/hardware_utils.py)）

| 參數 | 8GB | 16GB | 24GB | 32GB | 用途 |
|------|-----|------|------|------|------|
| `l65_workers` | **2** ⚠️ | 6 | 8 | 8 | L6.5 ThreadPool（OOM Fix 從 4↓2） |
| `l65_split_threshold` | **2000** ⚠️ | 8000 | 12000 | 16000 | 大 group 切割（OOM Fix 從 4000↓2000） |
| `l2_category_workers` | **1** ⚠️ | 4 | 6 | 7 | L2 derived 並發（8GB 強制序列） |
| `multi_tf_max_workers` | **1** ⚠️ | 2 | 3 | 4 | Multi-TF 並發（8GB 強制序列） |
| `l3_persist_mode` | **streaming** | streaming | hybrid | in_memory | L3 落地策略 |
| `l3_streaming_buffer_cols` | **2000** | 5000 | 10000 | 20000 | streaming buffer |
| `chunk_bars` | **50,000** | 100,000 | 250,000 | None | 長序列分批 |
| `layer3_chunk_size` | **256** | 512 | 512 | 1024 | Numba rolling chunk |
| `l7_workers` | 4 | 6 | 8 | 8 | L7 寫 parquet 並行 |
| `cgsa_memory_buffer` | 0 | 0 | 32 | 64 | CGSA buffer GB |

> ⚠️ **8GB 5 個關鍵保守值**：所有都已寫死於 `hardware_utils.py`，不會被測試干擾。

---

## 🟢 3. 速度優化（預設 ON）

| # | 開關 | 預設 | 位置 | 影響 |
|---|------|------|------|------|
| 3.1 | `FFACT_USE_POLARS` | **1** | [polars_adapter.py:59](../momentum/FeatureEngineering/polars_adapter.py) | Polars 引擎（V7 baseline default-on） |
| 3.2 | `FFACT_L3_STREAMING` | **1** | [operators/rolling_aggregator.py:95](../momentum/FeatureEngineering/operators/rolling_aggregator.py) | L3 邊算邊落地 |
| 3.3 | `FFACT_L3_MULTI_WINDOW` | **1** | [operators/rolling_aggregator.py:293](../momentum/FeatureEngineering/operators/rolling_aggregator.py) | L3 多窗合算 |
| 3.4 | `FFACT_USE_NUMBA_ROLLING` | **1** | [operators/rolling_aggregator.py:142](../momentum/FeatureEngineering/operators/rolling_aggregator.py) | Numba JIT rolling |
| 3.5 | `FFACT_USE_SEARCHSORTED` | **1** | [timeframe/tf_aligner.py:55](../momentum/FeatureEngineering/timeframe/tf_aligner.py) | 對齊查詢向量化 |
| 3.6 | `FFACT_USE_CGSA` | **1** | [feature_factory.py:479](../momentum/FeatureEngineering/feature_factory.py) | CGSA group registry |
| 3.7 | `FFACT_MULTI_TF_PARALLEL` | **1** | [timeframe/multi_tf_generator.py:995](../momentum/FeatureEngineering/timeframe/multi_tf_generator.py) | Multi-TF 並發（受 tier cap） |
| 3.8 | L4 `apply_to=layer1_and_raw` 快路徑 | **強制 ON**（CGSA 模式下） | [feature_factory.py:1026](../momentum/FeatureEngineering/feature_factory.py) | 省 ~2 min concat |
| 3.9 | L3 window-first cache + 向量化 cumsum slope | ✅ in place | rolling_aggregator | 5.5× 提速（8.5 min→1.5 min） |
| 3.10 | L4 chunked lag | `FFACT_LAYER4_CHUNK_SIZE=200`<br>`FFACT_LAYER4_LAG_BATCH_SIZE=8`<br>`FFACT_LAYER4_FAST_PATH_MAX_COLS=200000` | [operators/lag_processor.py](../momentum/FeatureEngineering/operators/lag_processor.py) | L4 記憶體+速度 |
| 3.11 | L7 Compactor（合併小 parts） | `FFACT_L7_COMPACTOR_ENABLED=1`<br>`FFACT_L7_COMPACTOR_TARGET_ROWS=100000` | [feature_storage.py:655-656](../momentum/FeatureEngineering/feature_storage.py) | 減少檔案數 |

> **未啟用實驗性開關**（保留設計但預設 OFF，需手動評估）：
> - `FFACT_LAYER1_PARALLEL=0` — L1 並發實驗（[feature_factory.py:465](../momentum/FeatureEngineering/feature_factory.py)）
> - `FFACT_MULTI_TF_KEEP_WORKER_NPY=0` — 偵錯/恢復用

---

## 🟢 4. 輸出檔案最小化

| # | 機制 | 設定 | 位置 |
|---|------|------|------|
| 4.1 | L7 Parquet 壓縮 | **zstd level 1** | [feature_storage.py:170](../momentum/FeatureEngineering/feature_storage.py) |
| 4.2 | Parquet `use_dictionary=False`（P4.1: −37% on float16） | 強制關閉 | [feature_storage.py:172, 560](../momentum/FeatureEngineering/feature_storage.py) |
| 4.3 | float16 roundtrip gate（rel_err 1e-3 / abs_err 1e-12，失敗回退 float32） | 強制 ON | [feature_storage.py:526-527, 874](../momentum/FeatureEngineering/feature_storage.py) |
| 4.4 | float16 inf/overflow / underflow 雙向檢測 | 強制 ON | [feature_storage.py:877-885](../momentum/FeatureEngineering/feature_storage.py) |
| 4.5 | L7 Compactor 合併 parts | **預設 ON** | [feature_storage.py:46](../momentum/FeatureEngineering/feature_storage.py) |
| 4.6 | HDF5 features matrix | gzip level 4 + float32 + chunked (256 rows × 512 cols) | [feature_storage.py:245-247, 289](../momentum/FeatureEngineering/feature_storage.py) |
| 4.7 | L7 disk safety factor | `FFACT_L7_DISK_SAFETY_FACTOR=1.5`（寫前檢查可用空間） | [feature_storage.py:991](../momentum/FeatureEngineering/feature_storage.py) |

---

## 🟢 5. 數據品質防線

| # | 機制 | 位置 | 預設 |
|---|------|------|------|
| 5.1 | L7 `inf_ratio` scorecard（catch overflow→inf） | feature_storage.py | ✅ ON |
| 5.2 | Microstructure `_safe_ratio` epsilon mask（避免 0/0→inf） | atomic/microstructure | ✅ ON |
| 5.3 | `warnings.filterwarnings("once")`（防 log I/O storm） | global | ✅ ON |
| 5.4 | Microstructure user-dict-priority（Phase D：`features` dict > legacy `enabled_features` list） | [config_manager.py:720-734](../momentum/FeatureEngineering/config_manager.py) | ✅ ON |
| 5.5 | float16 roundtrip gate（保證壓縮後品質） | feature_storage.py | ✅ ON |
| 5.6 | Compactor row-count 檢查 + duplicate column 檢查 | [feature_storage.py:196, 201](../momentum/FeatureEngineering/feature_storage.py) | ✅ ON |
| 5.7 | float16 dtype hint 一致性檢查（避免同一 group 跨 symbol dtype 不一致） | [feature_storage.py:629, 738](../momentum/FeatureEngineering/feature_storage.py) | ✅ ON |

---

## 📋 完整 FFACT_* 環境變數清單（25 個）

| 類別 | 變數 | 預設 | 說明 |
|------|------|------|------|
| 全域 | `FFACT_MEMORY_TIER` | `auto` | 強制指定 tier (8gb/16gb/24gb/32gb) |
| 引擎 | `FFACT_USE_POLARS` | `1` | Polars 引擎 |
| 引擎 | `FFACT_USE_CGSA` | `1` | CGSA group registry |
| 引擎 | `FFACT_USE_NUMBA_ROLLING` | `1` | Numba JIT |
| 引擎 | `FFACT_USE_SEARCHSORTED` | `1` | 對齊向量化 |
| L1 | `FFACT_LAYER1_PARALLEL` | `0` | L1 並發（實驗性） |
| L1 | `FFACT_LAYER1_MAX_WORKERS` | `4` | L1 worker 上限 |
| L2 | `FFACT_L2_CATEGORY_WORKERS` | `auto` | L2 category ThreadPool（8GB=1） |
| L3 | `FFACT_L3_STREAMING` | `1` | streaming persist |
| L3 | `FFACT_L3_MULTI_WINDOW` | `1` | 多窗合算 |
| L3 | `FFACT_L3_PERSIST_MODE` | `auto` | streaming/hybrid/in_memory |
| L3 | `FFACT_L3_STREAMING_BUFFER_COLS` | `auto` | streaming buffer |
| L3 | `FFACT_LAYER3_CHUNK_SIZE` | `auto` | Numba rolling chunk |
| L4 | `FFACT_LAYER4_CHUNK_SIZE` | `200` | column chunk |
| L4 | `FFACT_LAYER4_LAG_BATCH_SIZE` | `8` | lag batch |
| L4 | `FFACT_LAYER4_FAST_PATH_MAX_COLS` | `200000` | 快路徑上限 |
| L6.5 | `FFACT_L65_WORKERS` | from tier (8GB=2) | L6.5 ThreadPool |
| L6.5 | `FFACT_L65_CHUNK_SIZE` | `2000` | L6.5 chunk size |
| L6.5 | `FFACT_L65_SPLIT_THRESHOLD` | `auto` (8GB=2000) | 大 group 切割 |
| L7 | `FFACT_L7_WORKERS` | from tier (8GB=4) | L7 寫並行 |
| L7 | `FFACT_L7_COMPACTOR_ENABLED` | `1` | Compactor 合併 |
| L7 | `FFACT_L7_COMPACTOR_TARGET_ROWS` | `100000` | 合併目標行數 |
| L7 | `FFACT_L7_DISK_SAFETY_FACTOR` | `1.5` | 寫前磁碟空間檢查 |
| 儲存 | `FFACT_HDF5_CHUNK_ROWS` | `256` | HDF5 chunk |
| 儲存 | `FFACT_HDF5_CHUNK_COLS` | `512` | HDF5 chunk |
| 儲存 | `FFACT_HDF5_GZIP_LEVEL` | `4` | HDF5 gzip |
| Multi-TF | `FFACT_MULTI_TF_PARALLEL` | `1` | Multi-TF 並發 |
| Multi-TF | `FFACT_MULTI_TF_MAX_WORKERS` | `auto` (8GB=1) | worker 上限 |
| Multi-TF | `FFACT_MULTI_TF_ALIGN_BLOCK_ROWS` | `1024` | align block |
| Multi-TF | `FFACT_MULTI_TF_KEEP_WORKER_NPY` | `0` | debug/resume |
| 通用 | `FFACT_MEMMAP_COPY_BLOCK_ROWS` | `1024` | memmap 複製 block + 心跳日誌 |
| 通用 | `FFACT_MERGE_CHUNK_SIZE` | `5000` | TF merge chunk |
| 通用 | `FFACT_CGSA_WORK_DIR` | (auto temp) | CGSA 工作目錄 |
| 通用 | `FFACT_CGSA_MEMORY_BUFFER` | from tier | CGSA buffer |

---

## ✅ 健康檢查指令

```bash
# 1. 跑完整測試掃描（應為 381 passed / 0 failed）
./venv/bin/pytest tests/ -k "feature_factory or feature_preprocessor or feature_extractor or feature_validator or microstructure or large_trade or phase_d or cgsa or atomic or layer1 or layer2 or layer3 or layer4 or layer5 or layer6 or layer7 or preprocessor" --tb=line -q

# 2. 確認所有預設 ON 開關沒被改成 OFF
grep -rE 'FFACT_USE_POLARS|FFACT_L3_STREAMING|FFACT_L3_MULTI_WINDOW|FFACT_USE_NUMBA_ROLLING|FFACT_USE_SEARCHSORTED|FFACT_USE_CGSA|FFACT_MULTI_TF_PARALLEL|FFACT_L7_COMPACTOR_ENABLED' momentum/FeatureEngineering/

# 3. 確認 8GB tier 5 個關鍵保守值仍是 2/2000/1/1/streaming
grep -A2 '"8gb":' momentum/FeatureEngineering/utils/hardware_utils.py

# 4. 確認 Parquet zstd + use_dictionary=False
grep -E 'compression="zstd"|use_dictionary=False' momentum/FeatureEngineering/feature_storage.py

# 5. 確認 float16 roundtrip gate 仍存在
grep -E 'FLOAT16_MAX_REL_ERROR|data_float16.*astype|roundtrip' momentum/FeatureEngineering/feature_storage.py
```

---

## 📌 變更紀錄

| 日期 | 變更 |
|------|------|
| 2026-04-25 | 8GB tier OOM Fix：`l65_workers` 4→2、`l65_split_threshold` 4000→2000、`multi_tf_max_workers` 1（強制序列） |
| 2026-04-25 | Microstructure user-dict-priority（Phase D） |
| 2026-04-26 | 7 個過時測試修正（不影響數據品質、不關閉任何優化）；本表建立 |

---

## 🚫 絕不可變更的 user constraint

> 「之前不就說過這是量化研究分析，**絕對不能用消除特徵的方式做任何優化**？絕對不行！」

所有 10 個 windows × 10 個 aggregators × 全部 L1 indicators 必須完整保留。優化僅可動「執行/儲存方式」，不可動「特徵集合」。
