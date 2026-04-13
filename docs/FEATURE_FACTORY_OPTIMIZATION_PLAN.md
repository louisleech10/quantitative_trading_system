# Feature Factory 效能優化規劃書

> **基於**: FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md  
> **目標**: 方案 M（Hybrid — CGSA + Polars + Numba + searchsorted）  
> **約束**: 不減特徵、不降品質、數值完全等價  
> **執行者**: AI Agent（全自動，含測試）  
> **建立日期**: 2026-04-12  
> **硬體**: MacBook M1 8GB RAM  
> **狀態**: 🔒 FROZEN（2026-04-12）— 不可修改，實作變更需開 ADR

---

## 目錄

0. [AI Agent 生成規範](#0-ai-agent-生成規範)
1. [全局約束與驗收標準](#1-全局約束與驗收標準)
2. [Phase 0 — 可觀測性基礎建設](#2-phase-0--可觀測性基礎建設)
3. [Phase 1 — searchsorted + Multi-TF 快修](#3-phase-1--searchsorted--multi-tf-快修)
4. [Phase 2 — CGSA 架構規格與實作](#4-phase-2--cgsa-架構規格與實作)
5. [Phase 3 — Numba L3 融合 Rolling](#5-phase-3--numba-l3-融合-rolling)
6. [Phase 4 — Polars L2 / L6.5（條件性）](#6-phase-4--polars-l2--l65條件性)
7. [Phase 5 — 生產化](#7-phase-5--生產化)
8. [Phase Gate 決策矩陣](#8-phase-gate-決策矩陣)
9. [全局測試策略](#9-全局測試策略)
10. [風險登記簿](#10-風險登記簿)

---

## 0. AI Agent 生成規範

> 本節定義 AI Agent 實作本規劃書時必須遵守的專案規範。  
> 所有規範摘自 `.github/copilot-instructions.md` 及 `docs/ARCHITECTURE.md`，為本專案的「法律」。

### 0.1 解耦 7 規則（Zero Tolerance）

所有新增/修改的程式碼必須通過以下 7 項檢查，違反任一項即 **不可合併**：

| 規則 | 說明 | 驗證方式 |
|------|------|----------|
| **R1** | `momentum/` 不可 import `api/` | `grep -r "from api\." momentum/` → 0 結果 |
| **R2** | 跨 Domain 使用 Protocol 注入 | `from momentum.core.protocols import I*` |
| **R3** | `api/services/` 透過 `momentum/factories.py` 建立物件 | 不可直接 `Engine()` 或 `Registry()` |
| **R4** | Service 之間不互相 import | 無 `from api.services.other_service import` |
| **R5** | Config 單一來源 | Domain config → `momentum/core/config.py`；API config → `api/core/config.py` |
| **R6** | 測試設定隔離 | 測試可獨立執行，不依賴 `run_api.py` |
| **R7** | DTO 不跨域 | `api/models/` 與 `momentum/core/contracts.py` 無相互相依性 |

**本規劃書的具體影響**：
- Phase 2 新增的 `ColumnGroup`, `ColumnGroupRegistry` 位於 `momentum/FeatureEngineering/core/`（R1）
- 若需被 `api/services/` 使用 → 必須在 `momentum/factories.py` 加入 factory 函式（R3）
- 跨子模組依賴（如 `timeframe/` → `core/`）→ 同 Domain 內允許直接 import，跨 Domain 須用 Protocol（R2）

### 0.2 Logging 規範

```python
# ✅ momentum/ 內的模組
from momentum.core.logging import get_logger
logger = get_logger(__name__)

# ✅ api/ 內的模組
from api.core.logging import get_logger
logger = get_logger(__name__)

# ❌ 禁止
print("debug msg")                          # 用 logger
from api.core.logging import get_logger     # 在 momentum/ 中
logger.info(f"row {i}")                     # 在 hot loop 中（改用摘要）
```

**本規劃書的具體影響**：
- Task 0.1/0.2 的 heartbeat log 必須用 `from momentum.core.logging import get_logger`
- L3 Numba 核心內不可呼叫 logger（Numba JIT 內無法呼叫 Python 函式）
- 所有計時 log 格式統一：`logger.info("[L{N}] {action}: {detail} in {elapsed:.2f}s")`

### 0.3 Ultra Think 開發流程

每個 Task 的程式碼生成必須經過 3 步：

```
Step 1 - 初始生成：
    實作功能、基本 error handling、logging
    目標：正確性

Step 2 - 自我審查（不修改程式碼）：
    檢查清單：
    □ 有無 hardcoded data?（Data Truth Principle）
    □ Error handling 完整？
    □ Logging 符合規範？
    □ 命名清晰（禁止 df1, temp, x）？
    □ 有無重複程式碼？
    □ 效能：是否已向量化？
    □ Type hints 完整？
    輸出：改善清單

Step 3 - 最終優化：
    套用 Step 2 清單
    複雜邏輯加註解
    生成 production-ready 版本
```

### 0.4 Error Handling 模式

```python
# 所有涉及 I/O 的操作必須使用 FailureType 分類
from enum import Enum

class FailureType(Enum):
    IO_ERROR = "io_error"          # .npy / Parquet 寫入失敗 → retryable
    OOM = "oom"                     # 記憶體不足 → 不 retry，降級處理
    VALIDATION = "validation"       # 數值驗證失敗 → 不 retry，回退
    CONFIG = "config"               # 設定錯誤 → 不 retry，修正 config

# persist 失敗範例
try:
    np.save(path, data)
except OSError as e:
    raise PersistError(f"Failed to save {group_id}: {e}", failure_type=FailureType.IO_ERROR)
```

### 0.5 Type Hints 要求

所有新增函式必須有完整 type annotations：

```python
# ✅ 正確
def build_asof_index_map(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    offset_ns: int = 0,
) -> np.ndarray:
    ...

# ❌ 禁止
def build_asof_index_map(primary_ts, source_ts, offset_ns=0):
    ...
```

### 0.6 命名規範

| 類型 | 規則 | 範例 |
|------|------|------|
| 函式 | snake_case，動詞開頭 | `build_asof_index_map()`, `validate_no_future_leak()` |
| 類別 | PascalCase | `ColumnGroup`, `ColumnGroupRegistry` |
| 常數 | UPPER_SNAKE_CASE | `MEMMAP_THRESHOLD_BYTES`, `GOLDEN_CONFIG_OVERRIDE` |
| 變數 | snake_case，語義清楚 | `primary_timestamps`, `aligned_outputs` |
| 禁止 | — | `df1`, `temp`, `x`, `data2`, `result_new` |

### 0.7 測試規範

```python
# 測試函式名稱：test_{功能}_{場景}
# 必須有中文 docstring 說明
# 使用 pytest fixture 管理共用狀態

import pytest
import numpy as np

def test_build_asof_index_map_basic():
    """測試 build_asof_index_map 基本對齊：source=[0,10,20], primary=[5,15,25]"""
    primary = np.array([5, 15, 25], dtype=np.int64)
    source = np.array([0, 10, 20], dtype=np.int64)
    result = TimeframeAligner.build_asof_index_map(primary, source)
    np.testing.assert_array_equal(result, [0, 1, 2])

# Fixture 範例（合成資料用 make_kline_df）
@pytest.fixture
def sample_kline_1h():
    """產生 1h K-line 合成資料（12,888 rows）"""
    return make_kline_df(n_rows=12888, timeframe_seconds=3600)

# 效能測試標記
@pytest.mark.slow
def test_searchsorted_align_speed(sample_kline_1h):
    """測試 searchsorted align 效能：227k cols < 30s"""
    ...
```

**測試檔案結構規則**：
- 路徑：`tests/test_{module_name}.py`
- 效能測試：`tests/performance/test_{module_name}_perf.py`
- 測試可獨立執行（Rule 6），不需啟動 API server

### 0.8 效能程式碼慣例

```python
# 優先順序（從快到慢）：
# 1. 向量化 numpy/pandas
# 2. Numba @njit
# 3. async / multiprocessing
# 4. Python loop（最後手段）

# ✅ 向量化
price_change = (df['close'] / df['open'] - 1)

# ✅ Numba（必須用 cache=True 避免 cold start）
@numba.njit(cache=True)
def _welford_update(count, mean, M2, new_value):
    ...

# ❌ Python loop 處理大量數據
for i in range(len(df)):
    results.append(df['close'].iloc[i] / df['open'].iloc[i] - 1)
```

### 0.9 Factory 注入模式

新增被 `api/services/` 使用的 class 時，必須在 `momentum/factories.py` 加入 factory 函式：

```python
# momentum/factories.py（新增）
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

def create_column_group_registry(work_dir: Optional[Path] = None) -> ColumnGroupRegistry:
    """Factory for ColumnGroupRegistry."""
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="ffact_cgsa_"))
    return ColumnGroupRegistry(work_dir=work_dir)
```

### 0.10 Git Branch 與 Commit 慣例

```bash
# Branch 命名
perf/phase-0-observability
perf/phase-1-searchsorted
perf/phase-2-cgsa
perf/phase-3-numba-rolling
perf/phase-4-polars        # 條件性
perf/phase-5-production

# Commit message 格式
perf(feature-factory): Phase 1.1 - implement build_asof_index_map
perf(feature-factory): Phase 1.4 - skip primary self-alignment
test(feature-factory): T1.1~T1.5 searchsorted correctness tests
fix(feature-factory): T1.B7 raise ValueError on unsorted source
```

### 0.11 Data Truth Principle

```python
# ❌ 禁止在生產程式碼中出現
symbols = ['ETHUSDT', 'BTCUSDT']   # hardcoded
fake_data = np.random.randn(100)    # 假數據

# ✅ 測試中允許合成資料（透過 make_kline_df fixture）
# ✅ 生產程式碼從 config / API / 檔案讀取
symbols = config.get_symbols()
```

### 0.12 向後相容原則

每個 Phase 的行為變更必須提供 fallback 機制，確保可無縫切回舊行為：

| Phase | Fallback 機制 | 環境變數 |
|-------|--------------|----------|
| Phase 1 | searchsorted → merge_asof | `FFACT_USE_SEARCHSORTED=0` |
| Phase 2 | CGSA → legacy concat | `FFACT_USE_CGSA=0` |
| Phase 3 | Numba fused → pandas rolling | `FFACT_USE_NUMBA_ROLLING=0` |
| Phase 4 | Polars → pandas | `FFACT_USE_POLARS=0` |

**規則**：
- 舊路徑程式碼保留至少到下一 Phase Gate 通過
- Fallback 必須在 CI 中定期測試（確保不 bitrot）
- `momentum/FeatureEngineering/core/` 為 Phase 2 新增的子目錄（`__init__.py` 需建立）

### 0.13 Pre-Commit 檢查清單（每個 Task 完成後）

```
□ Ultra Think 3 步完成
□ grep -r "from api\." momentum/ → 0 結果（R1）
□ 無 hardcoded data
□ 所有函式有 type hints
□ Error handling 使用 FailureType 分類
□ Logging 符合 §0.2 規範
□ 命名符合 §0.6 規範
□ 測試有中文 docstring
□ 測試可獨立執行（無需 run_api.py）
□ .npy / .parquet 不在 git track 中
□ 效能程式碼已向量化（§0.8）
□ Fallback env var 可切回舊行為（§0.12）
```

---

## 1. 全局約束與驗收標準

### 1.1 不可退讓的硬約束

| # | 約束 | 驗證方式 |
|---|---|---|
| C1 | **數值等價**：優化後的 feature 矩陣與 golden output 欄位名稱完全相同、數值 `np.allclose(atol=1e-6, equal_nan=True)` | Golden output test suite |
| C2 | **不減特徵**：feature_count 不變（453,953 cols for ETHUSDT 2TF） | `assert new_count == golden_count` |
| C3 | **不改 column name**：包含 TF prefix、indicator name、window size 等 | `assert set(new_cols) == set(golden_cols)` |
| C4 | **RAM 峰值 ≤ 6 GB**（8GB 機器留 2GB 給 OS） | `psutil.Process().memory_info().rss` 監控 |
| C5 | **無 future leakage**：align 後 12h 特徵不超前 primary 1h | `TimeframeAligner.validate_no_future_leak()` |
| C6 | **NaN 語義一致**：rolling window 開頭的 NaN pattern 完全相同 | per-column NaN mask comparison |

### 1.2 每 Phase 通用驗收流程

```
1. 建立 git branch: perf/phase-{N}-{description}
2. 跑完目標修改
3. 執行 golden output comparison（C1~C3, C6）
4. 執行 future leak test（C5）
5. 記錄 RSS 峰值（C4）
6. 記錄 wall-clock time
7. 全部 PASS → 合併到 main；任一 FAIL → 回退到 branch 起點，定位問題
```

### 1.2.1 回退策略

每個 Phase 都在獨立 branch 上開發，失敗時：
1. `git stash` 保留修改
2. `git checkout main` 回到穩定版
3. 分析失敗原因，修正後在同 branch 重試
4. 連續失敗 3 次以上 → 重新評估該 Phase 的技術方案

### 1.3 Golden Output 基準定義

- **Symbol**: ETHUSDT
- **Timeframes**: primary=1h, training=[1h, 12h]
- **Config**: 使用 `scan_config.yaml` 預設設定（全開 L1~L6）
- **L6.5**: 如果現行 pipeline 跑不完（F 段 OOM），golden output 定義為 **L6.5 之前的 merged_df**（concat 階段的輸出）
- **OOM 降級策略**: 若全量 config 也 OOM → 使用 reduced config（Phase 0 定義的 GOLDEN_CONFIG_OVERRIDE）。若 reduced config 也 OOM → 僅產生 L1 golden（單層比對，仍可驗證 L1 正確性）
- **多層 Golden**: 儲存 `golden_l1.parquet`, `golden_l3_pre_concat.parquet`, `golden_final.parquet`，視可用性而定
- **儲存格式**: `data_cache/golden_output/ETHUSDT_1h_2tf_golden.parquet` + `_columns.json` + `_nan_mask.npz`

---

## 2. Phase 0 — 可觀測性基礎建設

**目標**: 不改變現有行為，只增加觀測能力  
**預計時間**: 短  
**風險**: 零（純增加 log）

### 2.1 任務清單

#### Task 0.1: L2 前後計時 log

**檔案**: `momentum/FeatureEngineering/feature_factory.py`

**變更**: 在 `_layer2_derived_features()` 開頭和結尾加計時 log

```python
def _layer2_derived_features(self, layer1, raw_data, config):
    import time
    t0 = time.perf_counter()
    logger.info("[L2] Starting derived features: %d L1 cols", layer1.shape[1])
    # ... existing code ...
    elapsed = time.perf_counter() - t0
    logger.info("[L2] Completed: %d cols in %.2fs", result.shape[1], elapsed)
    return result
```

#### Task 0.2: F 段 heartbeat log

**檔案**: `momentum/FeatureEngineering/memmap_utils.py`

**變更**: 在 `concat_with_memmap()` 的 block copy loop 中，每 30 秒輸出進度

```python
# 在 block copy 迴圈內
if time.perf_counter() - last_heartbeat > 30:
    logger.info("[concat_memmap] Progress: %d/%d rows copied, RSS=%.0f MB",
                row_offset, total_rows, get_rss_mb())
    last_heartbeat = time.perf_counter()
```

#### Task 0.3: 建立 Golden Output

**新檔案**: `scripts/generate_golden_output.py`

**邏輯**:
1. 執行 Feature Factory pipeline（可用 reduced config：僅 close 單一 data source，減少特徵數）
2. 儲存到 `data_cache/golden_output/` 作為基準
3. 若全量跑不完，改用 reduced config 建立 golden
4. 同時儲存 `columns.json`（欄位名列表）和 `nan_mask.npz`（NaN pattern）

**Reduced config 定義**（Phase 0 golden 用）:
```python
GOLDEN_CONFIG_OVERRIDE = {
    "data_sources": {"enabled_sources": ["close"]},  # 僅 close → ~100 L1 cols
    "atomic_indicators": {
        "trend": {"enabled": True},
        "momentum": {"enabled": True},
    },
    "operators": {"derived": {"enabled": True}},
    "rolling": {"windows": [5, 21, 55], "aggregators": ["mean", "std", "rank"]},
    "preprocessing": {"enabled": False},  # 先不跑 L6.5
}
```

### 2.2 測試項目

| 測試 ID | 測試名稱 | 驗證內容 | 邊界條件 |
|---|---|---|---|
| T0.1 | `test_l2_timing_log_emitted` | L2 log 包含 "Starting" 和 "Completed" | L1 為空 DF → 不應 crash |
| T0.2 | `test_heartbeat_emitted_during_concat` | 合成 >30s 的 concat 能看到 heartbeat | 小 DF（<30s）→ 不輸出 heartbeat |
| T0.3 | `test_golden_output_generated` | `golden.parquet` 存在、欄位 >0、無 inf | data_cache 無資料 → pytest.skip |
| T0.4 | `test_golden_columns_json_matches` | `columns.json` 與 parquet 欄位一致 | — |

---

## 3. Phase 1 — searchsorted + Multi-TF 快修

**目標**: 最低風險快速見效  
**預計效果**: B2(298s)→0s（skip self-align）, D(156s)→~5s（searchsorted）。合計省 ~449s ≈ 7.5 min  
**風險**: 低

### 3.1 Task 1.1: 實作 `build_asof_index_map()`

**檔案**: `momentum/FeatureEngineering/timeframe/tf_aligner.py`

**新增方法**:
```python
@staticmethod
def build_asof_index_map(
    primary_ts: np.ndarray,   # int64 ms timestamps, sorted
    source_ts: np.ndarray,    # int64 ms timestamps, sorted
    offset_ns: int = 0,       # OPEN_MINUS = -1 (ns)
) -> np.ndarray:
    """Build index map: output[i] = j where source_ts[j] <= primary_ts[i] + offset.

    Equivalent to merge_asof(direction='backward').
    Requires both arrays to be sorted in ascending order.

    Parameters
    ----------
    primary_ts : array of int64
        Primary timeframe timestamps in milliseconds. Must be sorted ascending.
    source_ts : array of int64
        Source timeframe timestamps in milliseconds. Must be sorted ascending.
    offset_ns : int
        Offset in nanoseconds for OPEN_MINUS alignment.
        For OPEN_MINUS with non-primary TF, use -1.
        This shifts primary to primary_ns = primary_ms * 1e6 + offset_ns,
        so -1 means: exclude source bars at exactly the primary timestamp.

    Returns
    -------
    np.ndarray of int64
        Index map. -1 indicates no valid source row.

    Raises
    ------
    ValueError
        If source_ts is not sorted ascending.
    """
    # Input validation
    if len(source_ts) > 1 and np.any(source_ts[1:] < source_ts[:-1]):
        raise ValueError("source_ts must be sorted in ascending order")

    # Convert ms → ns for precision, apply offset
    primary_ns = primary_ts.astype(np.int64) * 1_000_000 + offset_ns
    source_ns = source_ts.astype(np.int64) * 1_000_000

    # searchsorted: find insertion point for each primary in source
    idx = np.searchsorted(source_ns, primary_ns, side='right') - 1

    # Mark out-of-range as -1
    idx[idx < 0] = -1

    # Validate: source_ns[idx] must be <= primary_ns
    valid = idx >= 0
    mismatch = valid & (source_ns[idx[valid]] > primary_ns[valid])
    # (should not happen with side='right' - 1, but safety check)
    if np.any(mismatch):
        idx[np.where(valid)[0][mismatch]] = -1

    return idx
```

### 3.2 Task 1.2: 新增 `_searchsorted_align()` 方法

**檔案**: `momentum/FeatureEngineering/timeframe/tf_aligner.py`

**新增方法**: 使用 `build_asof_index_map` 做 alignment，替代 `_merge_asof_align_chunked`

```python
@staticmethod
def _searchsorted_align(
    source_values: pd.DataFrame,
    source_index: pd.DatetimeIndex,
    primary_index: pd.DatetimeIndex,
    offset_ns: int = 0,
) -> pd.DataFrame:
    """Align using searchsorted — O(N log M) vs merge_asof O(N·M/chunk)."""
    source_ms = source_index.astype(np.int64) // 1_000_000
    primary_ms = primary_index.astype(np.int64) // 1_000_000

    idx_map = TimeframeAligner.build_asof_index_map(
        primary_ms.to_numpy(), source_ms.to_numpy(), offset_ns=offset_ns,
    )

    n_rows = len(primary_index)
    n_cols = source_values.shape[1]
    source_arr = source_values.to_numpy(dtype=np.float32, na_value=np.nan)

    # Allocate output
    est_bytes = n_rows * n_cols * 4
    if est_bytes >= MEMMAP_THRESHOLD_BYTES:
        out = create_temp_memmap((n_rows, n_cols), prefix="ss_align_")
    else:
        out = np.empty((n_rows, n_cols), dtype=np.float32)

    valid = idx_map >= 0
    out[valid] = source_arr[idx_map[valid]]
    out[~valid] = np.nan

    aligned = pd.DataFrame(out, index=primary_index, columns=source_values.columns, copy=False)

    # Store source timestamps for future leak validation
    source_ts_mapped = np.full(n_rows, np.datetime64('NaT'), dtype='datetime64[ns]')
    source_ts_mapped[valid] = source_index.to_numpy()[idx_map[valid]]
    aligned.attrs["source_timestamps"] = pd.DatetimeIndex(source_ts_mapped)

    return aligned
```

### 3.3 Task 1.3: 修改 `align_to_primary()` 使用 searchsorted

**檔案**: `momentum/FeatureEngineering/timeframe/tf_aligner.py`

**變更**: 在 `align_to_primary()` 中，將 `_merge_asof_align` 呼叫替換為 `_searchsorted_align`

```python
# 現行:
aligned = TimeframeAligner._merge_asof_align(source_values, source_index, anchor_index)

# 改為:
offset_ns = -1 if (alignment_mode == AlignmentMode.OPEN_MINUS and source_tf != primary_tf) else 0
aligned = TimeframeAligner._searchsorted_align(
    source_values, source_index, primary_index, offset_ns=offset_ns,
)
```

**注意**: 保留 `_merge_asof_align` 和 `_merge_asof_align_chunked` 作為 fallback（透過環境變數 `FFACT_USE_SEARCHSORTED=0` 切回）

### 3.4 Task 1.4: 跳過 Primary TF Self-Alignment

**檔案**: `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`

**變更位置**: `generate_multi_tf()` 方法中，第 ~120-126 行

```python
# 現行（第 ~125-133 行）:
combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
aligned = TimeframeAligner.align_to_primary(
    combined, timeframe, primary_timestamps,
    self._primary_tf, self._config.timeframes.alignment_mode,
)
aligned.attrs = {}
aligned = self._apply_timeframe_tag(aligned, timeframe)

# 改為:
combined = self._combine_layers([layer1, layer2, layer3, layer4, layer5, layer6])
if timeframe == self._primary_tf:
    # Primary TF self-alignment is identity — skip entirely.
    # combined.index comes from raw_data.index (integer or DatetimeIndex),
    # need to set to primary_timestamps (DatetimeIndex) to match non-primary outputs.
    logger.info("[multi_tf] Skipping self-alignment for primary TF %s (%d cols)",
                timeframe, combined.shape[1])
    aligned = combined.copy(deep=False)  # shallow copy, avoid mutating combined
    aligned.index = primary_timestamps    # already DatetimeIndex from line 62
else:
    aligned = TimeframeAligner.align_to_primary(
        combined, timeframe, primary_timestamps,
        self._primary_tf, self._config.timeframes.alignment_mode,
    )
aligned.attrs = {}
aligned = self._apply_timeframe_tag(aligned, timeframe)
```

**關鍵細節**:
- `primary_timestamps` 在第 62 行已計算為 `DatetimeIndex`
- `combined.index` 可能是 int64 timestamp 或 DatetimeIndex（取決於 L1 的 raw_data index）
- self-align skip 必須將 `aligned.index` 統一為 DatetimeIndex（`primary_timestamps`）
- 使用 `copy(deep=False)` 避免修改 `combined` 的 index（影響後續 debug）
- 行數驗證：`assert len(combined) == len(primary_timestamps)` — 因 primary_raw 是 L0 的輸入，長度必然一致

### 3.5 Task 1.5: Multi-TF 平行化

**檔案**: `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`

**變更**: 將 `for` 迴圈改為 `concurrent.futures.ThreadPoolExecutor`（不用 ProcessPool，因為 TA-Lib 有 GIL 但 L3 pandas rolling 也有 GIL，ThreadPool 對 IO-bound memmap 操作仍有收益）

**注意**: 此 Task 的風險較高，建議在 Phase 1 的最後才做，且可暫時不做（效益僅 C=37s）

```python
# 結構變更概念
def _process_single_tf(self, symbol, timeframe, primary_raw, primary_timestamps):
    """處理單一 TF 的 L0~L6 + combine + align + tag，回傳 aligned DF"""
    # ... 包含 L0~L6 計算 + combine + align + tag 邏輯 ...
    return aligned, tf_layer_counts

# 在 generate_multi_tf 中：
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=min(len(self._training_tfs), 4)) as pool:
    futures = {
        pool.submit(self._process_single_tf, symbol, tf, primary_raw, primary_timestamps): tf
        for tf in self._training_tfs
    }
    for future in as_completed(futures):
        tf = futures[future]
        aligned, counts = future.result()
        aligned_outputs.append(aligned)
        tf_layer_counts[tf] = counts
```

**Phase 1 中此任務為 OPTIONAL**：如果 Phase 1.1~1.4 完成後 profile 顯示 C 段佔比極低，可延後。

### 3.6 Phase 1 測試項目

#### 3.6.1 核心正確性測試

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T1.1 | `test_build_asof_index_map_basic` | 基本對齊：source=[0,10,20], primary=[5,15,25] → idx=[0,1,2] |
| T1.2 | `test_build_asof_index_map_with_offset` | OPEN_MINUS offset=-1ns：primary_ts exactly at source_ts → 取上一個 |
| T1.3 | `test_searchsorted_vs_merge_asof_numeric_equivalence` | 對真實 ETHUSDT 資料，比較 searchsorted 和 merge_asof 結果，`np.allclose(atol=1e-6, equal_nan=True)` |
| T1.4 | `test_searchsorted_align_preserves_column_names` | 欄位名完全一致 |
| T1.5 | `test_searchsorted_align_nan_pattern` | NaN 位置（head/tail/middle）與舊方法一致 |
| T1.6 | `test_primary_self_align_skip_produces_same_output` | 跳過 self-align 後 vs 不跳過的結果完全一致 |
| T1.7 | `test_multi_tf_golden_output_equivalence` | 整個 multi-TF pipeline 的 golden output 比對 |
| T1.8 | `test_no_future_leak_after_searchsorted` | `validate_no_future_leak()` 仍 PASS |
| T1.9 | `test_searchsorted_align_preserves_source_timestamps_attr` | `aligned.attrs["source_timestamps"]` 存在且類型為 `pd.DatetimeIndex` |
| T1.10 | `test_env_var_fallback_to_merge_asof` | `FFACT_USE_SEARCHSORTED=0` 時走舊路徑，結果一致 |

#### 3.6.2 邊界條件測試

| 測試 ID | 測試名稱 | 邊界條件 | 預期行為 |
|---|---|---|---|
| T1.B1 | `test_build_asof_index_map_empty_source` | source_ts = [] | 回傳全 -1 array |
| T1.B2 | `test_build_asof_index_map_empty_primary` | primary_ts = [] | 回傳空 array |
| T1.B3 | `test_build_asof_index_map_single_row` | source=[100], primary=[50,100,150] | idx=[-1, 0, 0] |
| T1.B4 | `test_build_asof_index_map_primary_before_all_source` | primary 全部早於 source | 全 -1 |
| T1.B5 | `test_build_asof_index_map_primary_after_all_source` | primary 全部晚於 source | 全指向 source 最後一行 |
| T1.B6 | `test_build_asof_index_map_duplicate_timestamps` | source 有重複 ts | 取最後一個（side='right'-1） |
| T1.B7 | `test_build_asof_index_map_unsorted_source` | source 未排序 | raise `ValueError("source_ts must be sorted")` |
| T1.B8 | `test_searchsorted_align_all_nan_columns` | source_values 全 NaN 欄位 | aligned 也全 NaN |
| T1.B9 | `test_searchsorted_align_mixed_dtypes` | source 含 float64 和 float32 | 統一輸出 float32 |
| T1.B10 | `test_searchsorted_align_very_wide_df` | 227k columns | 不 OOM，結果正確 |
| T1.B11 | `test_self_align_skip_with_mismatched_index` | primary_raw.index 與 combined.index 長度一致但值不同 | 正確重設 index |
| T1.B12 | `test_self_align_skip_with_nan_in_combined` | combined 含 NaN（L1 計算產生的） | NaN 保留不變 |
| T1.B13 | `test_self_align_skip_preserves_column_order` | 跳過 align 後欄位順序不變 | `assert list(combined.columns) == list(aligned.columns)` |
| T1.B14 | `test_offset_ns_minus_one_at_exact_boundary` | primary_ts == source_ts（精確到 ms），offset=-1ns | 取上一個，不取同一個 |
| T1.B15 | `test_build_asof_index_map_int_overflow` | 極大 timestamp（2030年以後） | 不溢出 |

#### 3.6.3 效能驗收測試

| 測試 ID | 測試名稱 | 驗收標準 |
|---|---|---|
| T1.P1 | `test_searchsorted_align_speed` | 227k cols × 12888 rows align 完成 < 30s（vs 舊 298s） |
| T1.P2 | `test_searchsorted_align_memory` | RSS 增量 < 500 MB（vs 舊 11.73 GB memmap） |
| T1.P3 | `test_self_align_skip_eliminates_memmap` | 跳過 self-align 後無新 memmap 檔案建立 |

---

## 4. Phase 2 — CGSA 架構規格與實作

**目標**: 消除所有全域 concat（B1+E+F 共 ~9,000s）  
**預計效果**: 每 float 觸碰次數 11→2(primary)/4(non-primary)  
**風險**: 中等（核心架構重構）

### 4.1 ColumnGroup 資料結構規格

#### 4.1.1 Dataclass 定義

**新檔案**: `momentum/FeatureEngineering/core/column_group.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import numpy as np


class LayerSource(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L65 = "L6.5"


@dataclass(frozen=True)
class ColumnGroup:
    """Immutable metadata for a group of related feature columns.

    A ColumnGroup represents the smallest unit of independent computation
    in the CGSA pipeline. All columns within a group share the same:
    - source data column (e.g., 'close')
    - indicator (e.g., 'EMA')
    - layer origin (e.g., L1, L3)
    - timeframe (e.g., '1h')
    """
    group_id: str               # e.g. "1h_trend_EMA_close"
    layer: LayerSource
    timeframe: str              # e.g. "1h", "12h"
    data_source: str            # e.g. "close", "volume"
    indicator: str              # e.g. "EMA", "RSI"
    columns: tuple[str, ...]    # frozen column names
    shape: tuple[int, int]      # (n_rows, n_cols)
    dtype: str = "float32"
    disk_path: Optional[Path] = None  # path to .npy file

    @property
    def n_rows(self) -> int:
        return self.shape[0]

    @property
    def n_cols(self) -> int:
        return self.shape[1]

    @property
    def est_bytes(self) -> int:
        elem_size = 4 if self.dtype == "float32" else 8
        return self.n_rows * self.n_cols * elem_size
```

#### 4.1.2 Group ID 命名規則

```
{timeframe}_{category}_{indicator}_{data_source}[_{layer_suffix}]

範例:
  1h_trend_EMA_close             → L1 EMA on close (1h)
  1h_trend_EMA_close_Derived     → L2 derived operators on EMA close
  1h_trend_EMA_close_Mean_W5     → L3 rolling mean window=5
  1h_trend_EMA_close_Lag         → L4 lag features
  12h_momentum_RSI_close         → L1 RSI on close (12h)
```

**命名規則確保**：
- TF prefix 天然包含 → 消除 `_apply_timeframe_tag()` 的 `.rename()`
- Group ID 全域唯一 → Registry 可用 dict lookup
- 可由 group_id 反向解析出 layer/TF/indicator

#### 4.1.3 Registry API

**新檔案**: `momentum/FeatureEngineering/core/column_group_registry.py`

```python
class ColumnGroupRegistry:
    """In-memory registry tracking all column groups for a single symbol run."""

    def __init__(self, work_dir: Path):
        self._groups: dict[str, ColumnGroup] = {}
        self._work_dir = work_dir  # temp dir for .npy files

    def register(self, group: ColumnGroup) -> None:
        """Register a column group. Raises if group_id already exists."""
        if group.group_id in self._groups:
            raise ValueError(f"Duplicate group_id: {group.group_id}")
        self._groups[group.group_id] = group

    def get(self, group_id: str) -> ColumnGroup:
        """Get a column group by ID. Raises KeyError if not found."""
        return self._groups[group_id]

    def list_by_layer(self, layer: LayerSource) -> list[ColumnGroup]:
        """List all groups from a specific layer."""
        return [g for g in self._groups.values() if g.layer == layer]

    def list_by_timeframe(self, tf: str) -> list[ColumnGroup]:
        """List all groups from a specific timeframe."""
        return [g for g in self._groups.values() if g.timeframe == tf]

    def load_data(self, group_id: str) -> np.ndarray:
        """Load column group data from disk (memory-mapped read-only)."""
        group = self.get(group_id)
        return np.load(group.disk_path, mmap_mode='r')

    def save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup:
        """Save data to disk, register group, return updated group with disk_path."""
        path = self._work_dir / f"{group.group_id}.npy"
        np.save(path, data.astype(np.float32))
        updated = ColumnGroup(
            group_id=group.group_id, layer=group.layer,
            timeframe=group.timeframe, data_source=group.data_source,
            indicator=group.indicator, columns=group.columns,
            shape=data.shape, dtype="float32", disk_path=path,
        )
        self.register(updated)
        return updated

    def total_columns(self) -> int:
        return sum(g.n_cols for g in self._groups.values())

    def all_column_names(self) -> list[str]:
        """Get all column names in registration order."""
        names = []
        for g in self._groups.values():
            names.extend(g.columns)
        return names

    def cleanup(self) -> None:
        """Delete all .npy files."""
        for g in self._groups.values():
            if g.disk_path and g.disk_path.exists():
                g.disk_path.unlink()
        self._groups.clear()
```

### 4.2 L2 跨 Group 依賴解決方案

**問題**: L2 的 Cross/Ratio 需要同時存取兩個不同 indicator 的數據（如 EMA_5 - EMA_21，RSI / EMA）

**解法**: 分兩階段計算 L2

```
Stage A: L1 完成後，L1 全量保留在 RAM（1,683 cols × 12,888 rows = 87 MB）
  → 計算所有 Cross/Ratio/Distance/BinarySignal/Momentum（需跨 indicator）
  → 產出 L2 column-groups，逐個 save_data() 到 disk

Stage B: L1 data 釋放
  → 後續 L3/L4/L6 只需 per-group 讀取
```

**RAM 預算**: L1 = 87 MB + L2 最大單 group ~5 MB = **< 100 MB**。完全在預算內。

### 4.3 L6.5 per-group rank 語義定義

**問題**: `rank(pct=True)` 需要看同一列所有 rows 的分佈。但 per-group 處理時，rank 的 scope 不變。

**解法**: rank 是 **row-wise** 操作（對同一列的所有 rows 排序），per-group 處理時，每個 group 的每一列仍然有完整的 rows → **rank scope 不變**。

```
group = registry.load_data("1h_trend_EMA_close_Mean_W5")  # shape (12888, 10)
# 對 group 的每一列做 rank：
for col_idx in range(group.shape[1]):
    col_data = group[:, col_idx]  # 12888 rows — 完整 rank 所需的全部 rows
    ranked = scipy.stats.rankdata(col_data, nan_policy='omit') / np.sum(~np.isnan(col_data))
```

**結論**: rank 的 scope 是「同一列的所有 rows」，不是「同一 row 的所有 columns」→ per-group 無影響。

### 4.4 Persist 格式規格

**選擇**: per-group Parquet files

```
data_cache/features/{symbol}/{config_hash}/
├── manifest.json                          # registry metadata
├── 1h_trend_EMA_close.parquet            # ~10 cols
├── 1h_trend_EMA_close_Derived.parquet    # ~30 cols
├── 1h_trend_EMA_close_Mean_W5.parquet   # ~10 cols
├── ...
├── 12h_momentum_RSI_close.parquet        # ~10 cols
└── labels.parquet                         # label columns
```

**manifest.json 結構**:
```json
{
    "symbol": "ETHUSDT",
    "primary_tf": "1h",
    "training_tfs": ["1h", "12h"],
    "config_hash": "abc123",
    "total_features": 453953,
    "total_groups": 4500,
    "groups": [
        {
            "group_id": "1h_trend_EMA_close",
            "layer": "L1",
            "columns": ["close_1h_trend_EMA_5", "..."],
            "shape": [12888, 10],
            "parquet_path": "1h_trend_EMA_close.parquet"
        }
    ],
    "created_at": "2026-04-12T10:00:00"
}
```

**下游讀取方式**:
- IC Analysis: `pl.read_parquet("1h_trend_EMA_close.parquet")` → 只讀需要的 group
- ML Training: `DuckDB: SELECT * FROM read_parquet('*.parquet')` → DuckDB 合併
- 全量合併（向後相容）: 遍歷 manifest → 逐 group 讀入 → concat（僅在必要時）

### 4.5 遷移策略：雙軌 A/B 驗證

```
Phase 2 期間的遷移路徑：

1. [保留現行 pipeline]（feature_factory.py 現有 _combine_layers 路徑）
2. [新增 CGSA pipeline]（新的 streaming 路徑）
3. 兩條路徑都跑一次同一資料
4. 比對輸出（C1~C6 全量驗證）
5. 通過後切換 default，並 deprecate 舊路徑
```

**切換控制**: 透過 config flag 或環境變數 `FFACT_USE_CGSA=1`

### 4.5.1 CGSA Pipeline 新流程圖

```
                    ┌──────────────────────────────────────────────┐
                    │  CGSA Pipeline（per symbol）                  │
                    └──────────────────────────────────────────────┘

per-TF loop:        ┌─ TF=1h ─────────────────────────────────────┐
                    │  L0: load kline                              │
                    │  L1: per-indicator → ColumnGroup + .npy      │
                    │  L2 Stage A: cross-indicator ops (L1 in RAM) │
                    │  L2 Stage B: per-group .npy emit, free L1    │
                    │  ↓                                           │
                    │  per-group streaming:                        │
                    │    L3: fused rolling → ColumnGroup + .npy    │
                    │    L4: lag features → ColumnGroup + .npy     │
                    │    L5: cross-sectional → ColumnGroup + .npy  │
                    │    L6: meta features → ColumnGroup + .npy    │
                    └──────────────────────────────────────────────┘

                    ┌─ TF=12h ────────────────────────────────────┐
                    │  同上，但加 searchsorted align 後 save       │
                    │  group 的 row index 已對齊 primary           │
                    └──────────────────────────────────────────────┘

post-loop:          Registry 已收集所有 ColumnGroups
                    │
                    ├── L6.5: per-group preprocessing → overwrite .npy
                    │
                    ├── L7: validate (per-group scan) + persist (per-group Parquet)
                    │   └── manifest.json
                    │
                    └── 向後相容: 如果下游需要 wide DataFrame → lazy concat

注意:
  - 全程無 pd.concat() 全域 merge
  - RAM 中最大同時存活: max(single L1 全量, single group .npy) ≈ 100 MB
  - .npy 中介檔在 persist 為 Parquet 後可刪
```

### 4.5.2 L7 整合說明

**現行 L7** (`_layer7_validate_and_persist`)：接收整個 `features_df` wide DataFrame → validate → persist。

**CGSA L7 變更**：
- **validate**: 改為遍歷 Registry 中的所有 ColumnGroups，逐個 load + validate（inf check、NaN ratio check）
- **persist**: 逐個 ColumnGroup 轉 Parquet（已在 Task 2.8 定義）+ 產出 manifest.json
- **向後相容**: 保留一個 `materialize_wide_df()` 方法，從 Registry 的 Parquet files 重組 wide DataFrame（僅在 IC Analysis 或 ML Training 明確需要時呼叫）

### 4.6 Task 清單

| Task | 描述 | 檔案 | 依賴 |
|---|---|---|---|
| 2.1 | 建立 `ColumnGroup` dataclass | `momentum/FeatureEngineering/core/column_group.py` | — |
| 2.2 | 建立 `ColumnGroupRegistry` | `momentum/FeatureEngineering/core/column_group_registry.py` | 2.1 |
| 2.3 | L1 輸出改為 per-indicator column-group `.npy` | `feature_factory.py` → `_layer1_atomic_indicators` | 2.2 |
| 2.4 | L2 兩階段計算（Stage A: 跨 group; Stage B: per-group emit） | `derived_operators.py` | 2.3 |
| 2.5 | `_combine_layers()` 改為 registry-based | `feature_factory.py` | 2.2 |
| 2.6 | Multi-TF: column tagging 改為 group_id 命名 | `multi_tf_generator.py` | 2.2 |
| 2.7 | L6.5 改為 per-group 處理 | `feature_preprocessor.py` | 2.5 |
| 2.8 | Persist 改為 per-group Parquet | `feature_storage.py` | 2.7 |
| 2.9 | manifest.json 生成 | 新檔案 | 2.8 |
| 2.10 | L7 validate 改為 per-group scan | `feature_factory.py` → `_layer7_validate_and_persist` | 2.8 |
| 2.11 | `materialize_wide_df()` 向後相容方法 | `column_group_registry.py` | 2.8 |
| 2.12 | 雙軌 A/B 驗證框架 | `scripts/validate_cgsa_ab.py` | 2.11 |

### 4.7 Phase 2 測試項目

#### 4.7.1 單元測試

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T2.1 | `test_column_group_immutable` | frozen dataclass 不可修改 |
| T2.2 | `test_column_group_est_bytes` | bytes 計算正確 |
| T2.3 | `test_registry_register_and_get` | 註冊後可取回 |
| T2.4 | `test_registry_duplicate_raises` | 重複 group_id → ValueError |
| T2.5 | `test_registry_save_and_load_roundtrip` | save → load → data 完全一致 |
| T2.6 | `test_registry_list_by_layer` | 按 layer 過濾正確 |
| T2.7 | `test_registry_list_by_timeframe` | 按 TF 過濾正確 |
| T2.8 | `test_registry_all_column_names_order` | 全域欄位名按註冊順序 |
| T2.9 | `test_registry_cleanup_deletes_files` | cleanup 後 .npy 全刪 |
| T2.10 | `test_registry_total_columns` | total == sum of all group n_cols |

#### 4.7.2 整合測試

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T2.11 | `test_cgsa_vs_legacy_numeric_equivalence` | CGSA pipeline output == legacy output（C1~C3, C6） |
| T2.12 | `test_cgsa_no_global_concat` | CGSA 路徑中無任何 `concat_with_memmap` 呼叫 |
| T2.13 | `test_cgsa_ram_peak_under_2gb` | RSS 峰值 < 2 GB |
| T2.14 | `test_cgsa_manifest_valid` | manifest.json 格式正確、groups 數量 > 0 |
| T2.15 | `test_cgsa_parquet_readable_by_duckdb` | DuckDB 可讀取全部 parquet 並 count columns == total |
| T2.16 | `test_cgsa_l2_cross_group_operators` | Cross/Ratio 結果精確等於 legacy |
| T2.17 | `test_cgsa_l65_rank_matches_legacy` | per-group rank == legacy wide-table rank |

#### 4.7.3 邊界條件測試

| 測試 ID | 邊界條件 | 預期行為 |
|---|---|---|
| T2.B1 | L1 只有 1 個 indicator（1 個 group） | 正常執行 |
| T2.B2 | L2 無跨 group 操作（config 關閉 Cross/Ratio） | 直接 per-group emit |
| T2.B3 | 某個 group 全 NaN（如 micro_features on missing trades） | group 正常 register，persist 時保留全 NaN |
| T2.B4 | group 有 0 cols（空 layer 產出） | 不 register，不 persist |
| T2.B5 | 磁碟空間不足（work_dir 寫入失敗） | raise 明確的 IOError |
| T2.B6 | 同一 group_id 在不同 TF 出現 | 因 TF prefix 不同而不衝突 |
| T2.B7 | 453,953 個 columns 的 manifest.json 大小 | < 50 MB（JSON 可讀） |
| T2.B8 | L6.5 的 fracdiff transform（非 element-wise） | 需要同一列的所有 rows → per-group 可行 |
| T2.B9 | cleanup 被中斷（process killed） | .npy 殘留 → 下次執行需自動清理 work_dir |

---

## 5. Phase 3 — Numba L3 融合 Rolling

**目標**: L3 掃描次數 100N → 1N  
**預計效果**: A4 385s → ~60s  
**風險**: 中等（數值穩定性）

### 5.1 Task 清單

| Task | 描述 | 依賴 |
|---|---|---|
| 3.1 | 實作 `fused_rolling_stats()` — mean/std/min/max/range/zscore | — |
| 3.2 | 實作 online skew/kurt（Pebay algorithm） | 3.1 |
| 3.3 | 實作 rolling rank（sorted buffer + bisect） | — |
| 3.4 | 實作 slope（running sums） | — |
| 3.5 | 整合到 RollingAggregator | 3.1~3.4 |
| 3.6 | 數值等價驗證 suite | 3.5 |

**Fallback**: 透過 `FFACT_USE_NUMBA_ROLLING=0` 切回 pandas rolling 路徑。舊路徑保留至 Phase Gate 3→4 通過。

### 5.2 演算法規格

#### 5.2.1 Welford Online Mean/Var（float64 累加器）

**NaN 處理語義**（必須與 pandas 一致）：
- `min_periods` = window size（即 pandas 預設）。前 W-1 行輸出 NaN。
- 遇到 NaN 值時：跳過（不計入 count），如果 window 中有效值 < min_periods → 輸出 NaN
- 與 pandas `rolling(W, min_periods=W).mean()` 完全等價

```python
@numba.njit
def _welford_update(count, mean, M2, new_value):
    """Welford's online algorithm for mean and variance."""
    count += 1
    delta = new_value - mean
    mean += delta / count
    delta2 = new_value - mean
    M2 += delta * delta2
    return count, mean, M2

@numba.njit
def _welford_remove(count, mean, M2, old_value):
    """Inverse Welford: remove oldest from sliding window."""
    count -= 1
    if count == 0:
        return 0, 0.0, 0.0
    delta = old_value - mean
    mean -= delta / count
    delta2 = old_value - mean
    M2 -= delta * delta2
    return count, mean, M2
```

**關鍵**: 累加器必須用 `float64`，最後輸出轉 `float32`。

#### 5.2.2 Monotonic Deque Min/Max（O(1) amortized）

```python
# 使用固定大小 ring buffer + deque index
# deque 維護遞增序列（for min）或遞減序列（for max）
# 每次新增/移除：amortized O(1)
```

#### 5.2.3 Rolling Rank（Sorted Buffer + Bisect）

```python
# 維護一個 sorted array of size W
# 新值加入：bisect_insort → O(W) shift
# 舊值移除：bisect_left → O(W) shift
# Rank = bisect_left(sorted, current) / count
# 總複雜度：O(N·W) — 比 pandas rolling.rank O(N·W·log(W)) 快
```

#### 5.2.4 Pebay Online Skew/Kurt（float64 累加器 + 定期校正）

```
每 W 步從 ring buffer 重新計算一次，避免 catastrophic cancellation。
校正成本：O(W) per W steps = amortized O(1) per step。
```

### 5.3 Phase 3 測試項目

#### 5.3.1 數值正確性（每個聚合函式獨立驗證）

| 測試 ID | 測試名稱 | 驗證方式 |
|---|---|---|
| T3.1 | `test_numba_rolling_mean_vs_pandas` | `np.allclose(numba_out, pd.rolling.mean(), atol=1e-6, equal_nan=True)` |
| T3.2 | `test_numba_rolling_std_vs_pandas` | 同上，`pd.rolling.std(ddof=1)` |
| T3.3 | `test_numba_rolling_min_vs_pandas` | 同上 |
| T3.4 | `test_numba_rolling_max_vs_pandas` | 同上 |
| T3.5 | `test_numba_rolling_range_vs_pandas` | max - min |
| T3.6 | `test_numba_rolling_zscore_vs_pandas` | (val - mean) / std |
| T3.7 | `test_numba_rolling_skew_vs_pandas` | `atol=1e-4`（skew 精度較低）: `pd.rolling.skew()` |
| T3.8 | `test_numba_rolling_kurt_vs_pandas` | `atol=1e-4`: `pd.rolling.kurt()` |
| T3.9 | `test_numba_rolling_rank_vs_pandas` | `atol=1e-6`: `pd.rolling.rank(pct=True)` |
| T3.10 | `test_numba_rolling_slope_vs_existing` | 比對現有 vectorized slope 實作 |

#### 5.3.2 多 window 融合測試

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T3.11 | `test_fused_multi_window_equivalent` | 融合 10 windows 結果 == 單獨 10 次 rolling 結果 |
| T3.12 | `test_fused_golden_output_match` | 融合結果 vs golden output（全量比對） |

#### 5.3.3 邊界條件測試

| 測試 ID | 邊界條件 | 預期行為 |
|---|---|---|
| T3.B1 | 輸入全 NaN | 輸出全 NaN |
| T3.B2 | 輸入單一值（constant） | mean=val, std=0, rank=NaN(或 0.5), skew=NaN, kurt=NaN |
| T3.B3 | Window=1 | mean=val, std=NaN, rank=NaN |
| T3.B4 | N < W（rows < window） | 前 W-1 行 NaN（等價 pandas min_periods=W） |
| T3.B5 | 極大值（1e30）和極小值（1e-30）交替 | 不 overflow/underflow |
| T3.B6 | Window=233（最大） | 正確計算到 tail |
| T3.B7 | 連續 +inf 和 -inf | 正確傳播 inf/NaN |
| T3.B8 | N=1（只有一行） | 全 NaN（沒有完整 window） |
| T3.B9 | 重複值（rank 驗證） | rank 使用 average method |
| T3.B10 | float64 vs float32 累加器精度差異 | float64 累加器 → float32 輸出，skew/kurt 誤差 < 1e-4 |
| T3.B11 | Window 內含間歇 NaN（如 [1, NaN, 3, NaN, 5]） | 跳過 NaN，有效 count < min_periods → 輸出 NaN |
| T3.B12 | min_periods 行為等價 pandas | 前 W-1 行全 NaN，第 W 行開始輸出值 |
| T3.B13 | 全部 window sizes 同時融合（5,8,13,21,34,55,89,144,233 = 9 windows） | 多 window 平行正確 |

#### 5.3.4 效能驗收

| 測試 ID | 驗收標準 |
|---|---|
| T3.P1 | 1,683 cols × 10 windows × 10 aggs × 12,888 rows < 120s（vs 舊 385s） |
| T3.P2 | RAM 增量 < 500 MB（ring buffers only） |

---

## 6. Phase 4 — Polars L2 / L6.5（條件性）

**決策門檻**: Phase 3 完成後重新 profile。僅當 L2 或 L6.5 是剩餘的 top-2 瓶頸時才推進。

### 6.1 Task 清單

| Task | 描述 | 依賴 |
|---|---|---|
| 4.1 | L1 → Polars DataFrame（`pl.from_numpy` zero-copy） | Phase 2 |
| 4.2 | L2 DerivedOperatorEngine → Polars `with_columns()` batch | 4.1 |
| 4.3 | L6.5 FeaturePreprocessor → Polars expressions | Phase 2 |
| 4.4 | NaN 語義對齊驗證 | 4.2, 4.3 |

### 6.2 Phase 4 測試項目

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T4.1 | `test_polars_l2_vs_pandas_l2` | 全量數值等價 |
| T4.2 | `test_polars_l65_vs_pandas_l65` | 全量數值等價 |
| T4.3 | `test_polars_nan_min_periods` | rolling 開頭 NaN 行數一致 |
| T4.4 | `test_polars_division_by_zero` | 比較 NaN/inf 行為 |

#### 邊界條件

| 測試 ID | 邊界條件 | 預期行為 |
|---|---|---|
| T4.B1 | Polars 的 null vs NaN 差異 | 統一為 NaN（Polars null → NaN on to_numpy） |
| T4.B2 | float64 → float32 precision loss | 在 L2 output 精度損失 < 1e-6 |
| T4.B3 | Empty DataFrame → Polars | 正確處理空 DF |

---

## 7. Phase 5 — 生產化

**目標**: multi-symbol 平行化 + 下游 DuckDB 整合

### 7.1 Task 清單

| Task | 描述 | 依賴 |
|---|---|---|
| 5.1 | ProcessPoolExecutor multi-symbol | Phase 2 |
| 5.2 | Arrow IPC 作為 column-group intermediate | Phase 2 |
| 5.3 | DuckDB 讀取 Parquet 下游介面 | Phase 2 |
| 5.4 | 預估：100 sym × 4 TF × 8 workers < 90 min | 5.1 |

### 7.2 Phase 5 測試項目

| 測試 ID | 測試名稱 | 驗證內容 |
|---|---|---|
| T5.1 | `test_multi_symbol_parallel_correctness` | 2 symbols × 2 TF 平行 → 各自 golden 一致 |
| T5.2 | `test_multi_symbol_no_crosstalk` | 確認無共享 Registry 污染 |
| T5.3 | `test_duckdb_read_parquet_all_columns` | DuckDB count 所有 columns == manifest total |

#### 邊界條件

| 測試 ID | 邊界條件 | 預期行為 |
|---|---|---|
| T5.B1 | 其中一個 symbol 失敗 | 其他 symbols 不受影響 |
| T5.B2 | Worker process OOM killed | 主進程捕獲 exc，記錄失敗 symbol |
| T5.B3 | 磁碟空間不足（mid-run） | 提前失敗，清理已寫 .npy |

---

## 8. Phase Gate 決策矩陣

### 8.1 Phase 0 → Phase 1 Gate

| 條件 | 要求 |
|---|---|
| Golden output 已建立 | `data_cache/golden_output/` 存在且可讀 |
| L2 計時 log 可見 | 確認 A3 = 307s 的分布 |

### 8.2 Phase 1 → Phase 2 Gate

| 條件 | 要求 |
|---|---|
| T1.3 PASS | searchsorted vs merge_asof 數值一致 |
| T1.6 PASS | self-align skip 數值一致 |
| T1.7 PASS | 整個 multi-TF golden 等價 |
| 效能改善實測 | B2+D 合計從 ~454s 降至 < 50s |
| re-profile 完成 | 新的時間分布記錄（確認下個瓶頸） |

### 8.3 Phase 2 → Phase 3 Gate

| 條件 | 要求 |
|---|---|
| T2.11 PASS | CGSA vs legacy 數值一致 |
| T2.13 PASS | RSS < 2 GB |
| 無 global concat | T2.12 確認 |
| re-profile 完成 | 確認 L3 是剩餘 top-1 瓶頸 |

### 8.4 Phase 3 → Phase 4 Gate（條件性）

| 條件 | 要求 |
|---|---|
| T3.12 PASS | 融合結果 vs golden 一致 |
| re-profile 完成 | **僅當 L2 或 L6.5 是 top-2 瓶頸時才推進 Phase 4** |
| 否則 → 跳到 Phase 5 | |

### 8.5 Phase 4/5 → Done Gate

| 條件 | 要求 |
|---|---|
| 全量 golden output 比對 PASS | C1~C6 全通過 |
| 1 sym × 2 TF < 20 min（Phase 2 後） | 或 < 7 min（Phase 3 後） |
| RSS 峰值 < 2 GB | Phase 2+ 之後 |

---

## 9. 全局測試策略

### 9.1 測試分類

| 類別 | 數量 | 執行時機 | 備註 |
|---|---|---|---|
| 單元測試 | ~55 | 每次修改後 | 純函式、不需真實資料 |
| 邊界條件測試 | ~35 | 每次修改後 | 合成資料 |
| 整合測試 | ~12 | Phase 完成時 | 需要真實 ETHUSDT 資料 |
| Golden 等價測試 | ~5 | Phase 完成時 | 需要 golden output |
| 效能驗收測試 | ~8 | Phase 完成時 | 需要真實資料 + 計時 |

**測試 ID 統計**:
- Phase 0: T0.1~T0.4 = 4 項
- Phase 1: T1.1~T1.10 (核心) + T1.B1~T1.B15 (邊界) + T1.P1~T1.P3 (效能) = 28 項
- Phase 2: T2.1~T2.10 (單元) + T2.11~T2.17 (整合) + T2.B1~T2.B9 (邊界) = 26 項
- Phase 3: T3.1~T3.12 (核心) + T3.B1~T3.B13 (邊界) + T3.P1~T3.P2 (效能) = 27 項
- Phase 4: T4.1~T4.4 + T4.B1~T4.B3 = 7 項
- Phase 5: T5.1~T5.3 + T5.B1~T5.B3 = 6 項
- **總計: 98 項測試**

### 9.2 測試檔案結構

```
tests/
├── test_golden_output_generation.py    # Phase 0 — T0.1~T0.4
├── test_searchsorted_align.py          # Phase 1 — T1.1~T1.5, T1.8~T1.10, T1.B1~T1.B10, T1.B14~T1.B15
├── test_primary_self_align_skip.py     # Phase 1 — T1.6, T1.B11~T1.B13
├── test_multi_tf_golden_equivalence.py # Phase 1 — T1.7
├── test_golden_equivalence.py          # Phase 0~5 — 通用 golden comparison
├── test_column_group.py                # Phase 2 — T2.1~T2.10
├── test_cgsa_pipeline.py              # Phase 2 — T2.11~T2.17, T2.B1~T2.B9
├── test_numba_rolling.py               # Phase 3 — T3.1~T3.12, T3.B1~T3.B13
├── test_polars_engines.py              # Phase 4 — T4.1~T4.4, T4.B1~T4.B3
├── test_multi_symbol_parallel.py       # Phase 5 — T5.1~T5.3, T5.B1~T5.B3
├── performance/
│   ├── test_searchsorted_perf.py       # T1.P1~T1.P3
│   ├── test_numba_rolling_perf.py      # T3.P1~T3.P2
│   └── test_cgsa_memory.py             # T2.13
```

### 9.3 合成資料生成器（測試 Fixture）

```python
# conftest.py 或 test_fixtures.py
import numpy as np
import pandas as pd

def make_kline_df(n_rows: int, timeframe_seconds: int, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic kline-like DataFrame with realistic structure."""
    rng = np.random.RandomState(seed)
    base = 3000.0  # ETHUSDT-like price
    close = base + np.cumsum(rng.randn(n_rows) * 10)
    open_ = close + rng.randn(n_rows) * 2
    high = np.maximum(open_, close) + rng.rand(n_rows) * 5
    low = np.minimum(open_, close) - rng.rand(n_rows) * 5
    volume = rng.rand(n_rows) * 1000 + 100
    timestamps = np.arange(n_rows) * timeframe_seconds * 1000  # ms

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })

def make_feature_df(n_rows: int, n_cols: int, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic feature DataFrame."""
    rng = np.random.RandomState(seed)
    data = rng.randn(n_rows, n_cols).astype(np.float32)
    # Add realistic NaN pattern (first 20% of rows)
    for j in range(n_cols):
        nan_len = rng.randint(0, n_rows // 5)
        data[:nan_len, j] = np.nan
    cols = [f"feat_{i:05d}" for i in range(n_cols)]
    return pd.DataFrame(data, columns=cols)
```

---

## 10. 風險登記簿

| # | 風險 | 影響 | 機率 | 緩解措施 |
|---|---|---|---|---|
| R1 | searchsorted 在 timestamp 精度（ms vs ns）上產生 off-by-one | 數值不等價，C1 fail | 中 | T1.2 offset 測試 + T1.B14 精確邊界測試 |
| R2 | self-align skip 後 index 對齊不一致 | 後續 concat 列數不匹配 | 低 | T1.B11 index mismatch 測試 |
| R3 | CGSA per-group persist 導致過多小檔案（~4,500 Parquet） | IO 效能下降 | 中 | 可合併相同 indicator 的 groups 到一個 Parquet |
| R4 | Numba fused rolling 的 skew/kurt 數值不穩定 | atol=1e-4 fail | 中 | Pebay + 每 W 步校正 + float64 累加器 |
| R5 | Polars 的 null ≠ NaN 語義差異 | C6 fail | 中 | T4.B1 + `pl.Series.fill_null(float('nan'))` |
| R6 | 多 TF 平行化時 TA-Lib GIL 競爭 | 效能無改善或更差 | 中 | 改用 ProcessPoolExecutor 而非 ThreadPoolExecutor |
| R7 | 現有 pipeline 跑不完 → 無法建立完整 golden output | 無法做 C1 驗證 | 高 | 用 reduced config golden；單 layer golden |
| R8 | .npy 中介檔案硬碟暴漲 | work_dir 爆滿 | 低 | persist 後即刪 + cleanup finally block |
| R9 | L2 的 Cross/Ratio 跨 group 依賴在 config 變更後增加新 operators | 新 operator 打破 per-group 假設 | 低 | 明確在 L2 engine 文件中記錄「跨 group operators 必須在 Stage A」 |
| R10 | Parquet schema 45 萬欄位 metadata 極大 | 下游讀取慢 | 高 | 改為 per-group parquet files（已在規格中定義） |
| R11 | TA-Lib 非 thread-safe（Task 1.5 ThreadPoolExecutor） | segfault 或結果錯誤 | 高 | Task 1.5 標記 OPTIONAL；若實作改用 ProcessPoolExecutor |
| R12 | Numba JIT 首次編譯耗時（cold start ~30s） | 首次執行慢 | 低 | 使用 `@numba.njit(cache=True)` 磁碟快取 |
| R13 | `build_asof_index_map` 的 int64 ms→ns 轉換溢出（year > 2262） | idx 全錯 | 極低 | T1.B15 overflow 測試；加 assert year < 2100 |
| R14 | CGSA 雙軌 A/B 同時執行 → RAM 翻倍 → OOM | Phase 2 測試無法完成 | 中 | A/B 不同時在記憶體中；legacy 先跑完存 parquet，再跑 CGSA 比對 |

---

## 附錄 A: 效能預估對照表

**Phase 1 預估細節**: 現行 170+ min 中，B2(self-align)=298s + D(12h align)=156s = 454s ≈ 7.5 min 節省 → 162 min

| 場景 | 現行 | +Phase 1 | +Phase 2 | +Phase 3 | +Phase 4 | +Phase 5 |
|---|---|---|---|---|---|---|
| 1 sym × 2 TF | 170+ min ❌ | ~163 min | ~20 min | ~7 min | ~3.3 min | ~3.3 min |
| 1 sym × 4 TF | OOM ❌ | OOM | ~40 min | ~14 min | ~6.5 min | ~6.5 min |
| 100 sym × 2 TF | OOM ❌ | OOM | ~33 hrs | ~12 hrs | ~5.5 hrs | ~41 min |
| 100 sym × 4 TF × 8w | OOM ❌ | OOM | N/A | N/A | N/A | ~82 min |

**說明**: Phase 1 的主要價值不在絕對時間節省，而是消除 self-align 的無謂 memmap I/O，降低磁碟壓力，為 Phase 2 鋪路。Phase 2（CGSA）是最大的性能飛躍，消除所有 global concat 的 ~9,000 秒 memmap I/O。

## 附錄 B: 參考文件

- [FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md](./FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md) — 效能研究報告
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系統架構
- `momentum/FeatureEngineering/timeframe/tf_aligner.py` — 現行 align 實作
- `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` — 現行 Multi-TF 實作
- `momentum/FeatureEngineering/feature_factory.py` — 主 pipeline
- `momentum/FeatureEngineering/memmap_utils.py` — memmap 工具
- `momentum/FeatureEngineering/operators/rolling_aggregator.py` — L3 rolling
- `momentum/FeatureEngineering/operators/derived_operators.py` — L2 derived
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` — L6.5

---

## 附錄 C: AI Agent 執行清單（按序）

```
Phase 0:
  □ 0.1  加 L2 計時 log → feature_factory.py
  □ 0.2  加 heartbeat log → memmap_utils.py
  □ 0.3  建立 generate_golden_output.py + 執行建立 golden
  □ 0.4  跑 T0.1~T0.4

Phase 1:
  □ 1.1  實作 build_asof_index_map() → tf_aligner.py
  □ 1.2  實作 _searchsorted_align() → tf_aligner.py
  □ 1.3  修改 align_to_primary() 切換到 searchsorted → tf_aligner.py
  □ 1.4  加 self-align skip → multi_tf_generator.py
  □      跑 T1.1~T1.10 全部核心正確性測試
  □      跑 T1.B1~T1.B15 全部邊界條件測試
  □      跑 T1.P1~T1.P3 效能驗收
  □      Phase Gate 1→2 檢查
  □ 1.5  (OPTIONAL) Multi-TF 平行化 → multi_tf_generator.py

Phase 2:
  □ 2.1  建立 ColumnGroup dataclass
  □ 2.2  建立 ColumnGroupRegistry
  □ 2.3  L1 per-indicator output
  □ 2.4  L2 兩階段計算
  □ 2.5  _combine_layers registry-based
  □ 2.6  Multi-TF column tagging via group_id
  □ 2.7  L6.5 per-group
  □ 2.8  Persist per-group Parquet
  □ 2.9  manifest.json
  □ 2.10 L7 per-group validate
  □ 2.11 materialize_wide_df() 向後相容
  □ 2.12 雙軌 A/B 驗證
  □      跑 T2.1~T2.17 + T2.B1~T2.B9
  □      Phase Gate 2→3 檢查

Phase 3:
  □ 3.1  fused_rolling_stats (mean/std/min/max/range/zscore)
  □ 3.2  online skew/kurt (Pebay)
  □ 3.3  rolling rank (sorted buffer)
  □ 3.4  slope (running sums)
  □ 3.5  整合到 RollingAggregator
  □ 3.6  跑 T3.1~T3.12 + T3.B1~T3.B13 + T3.P1~T3.P2
  □      Phase Gate 3→4 檢查（re-profile 決定是否進 Phase 4）

Phase 4 (條件性):
  □ 4.1~4.4  Polars L2/L6.5 改寫
  □          跑 T4.1~T4.4 + T4.B1~T4.B3

Phase 5:
  □ 5.1~5.3  生產化（multi-symbol, Arrow IPC, DuckDB）
  □          跑 T5.1~T5.3 + T5.B1~T5.B3
  □          最終全量 golden 驗證
```
