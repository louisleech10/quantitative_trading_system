# Feature Factory 優化 TODO 規劃文件

> **建立日期**: 2026-04-20  
> **最後更新**: 2026-04-20 (v3)  
> **用途**: 作為產生 TODO 清單的規格來源  
> **基準**: V7 Baseline (7,756s / 435K features / 15.8 GB / Peak RSS 3,990 MB)

---

## 一、現況確認

### V7 Baseline 效能數字

| 指標 | 數值 |
|------|------|
| Pipeline 總耗時 | 7,756s (129 min) |
| 特徵數 | 435,389 |
| 輸出大小 | 15,799 MB (15.8 GB), 724 files |
| Peak RSS | 3,990 MB |
| L6.5 Preprocessing | ~2,424s (708 groups × 平均 3.42s) |
| L7 Validate+Persist | ~467s（V7 log 數字，非 540s） |
| float16 儲存 | ✅ 已啟用 |
| zstd 壓縮 | ✅ level=1（速度優先，**維持不變**） |
| manifest.json 輸出 | ✅ 已實作 |
| FeatureReader 介面 | ✅ 已有 `feature_reader.py` |

### 已確認功能狀態（grep + profiling 驗證）

| 功能 | 狀態 | 確認方式 |
|------|------|---------|
| `FFACT_USE_NUMBA_ROLLING` | ✅ **預設 "1"，V7 已啟用** | `rolling_aggregator.py` L100 `os.getenv(..., "1")`；V7 feature flags JSON 確認 |
| `MAX_GROUP_COLUMNS = 5000` split | ✅ **已生效** | 1h WQ → 6 parts, 12h WQ → 6 parts；part1~6 各約 4,900-5,700 est. cols |
| `FFACT_L3_STREAMING` | ✅ 已啟用（8GB OOM 保護） | V7 feature flags `FFACT_L3_STREAMING: 1` |
| `FFACT_USE_CGSA` | ✅ 已啟用 | V7 feature flags `FFACT_USE_CGSA: 1` |

> P2 的「確認 NUMBA_ROLLING」和 P3 的「確認 max_group_split」**均已確認完畢**，相應工作項目從 TODO 移除。

### 架構方向確認

1. **V7 Architecture P0 項目已全部實作完畢**
2. **速度優化唯一軌道**（Track B 下游整合不在本文件範圍）
3. **所有優化均需多層級設計**：8GB 現在 + 16/24/32GB 升級後，不能僅實作當前硬體路徑

---

## 二、硬體層級自動偵測框架（全域設計，貫穿所有優化）

> **設計原則**：現在就實作所有層級的程式碼路徑，自動偵測硬體並啟用最佳策略；使用者和 AI Agent 可用 `FFACT_MEMORY_TIER` 覆蓋。

### 2.1 記憶體層級定義

| Tier | 實際 RAM | 自動偵測閾值 | 代表機器 |
|------|---------|------------|---------|
| `8gb`  | < 12 GB  | 8 GB M1 Air（現況） |
| `16gb` | 12-20 GB | 16 GB M1/M2 |
| `24gb` | 20-28 GB | 24 GB M2 Pro |
| `32gb` | ≥ 28 GB  | 32/36 GB M2 Max/Ultra |

### 2.2 `get_memory_tier()` 實作

**位置**：`momentum/FeatureEngineering/utils/hardware_utils.py`（新增）

```python
import os
import psutil

TIER_THRESHOLDS = [
    (28, "32gb"),
    (20, "24gb"),
    (12, "16gb"),
    (0,  "8gb"),
]

def get_memory_tier() -> str:
    """
    Returns hardware tier string: '8gb' | '16gb' | '24gb' | '32gb'.
    
    Override via: FFACT_MEMORY_TIER=auto|8gb|16gb|24gb|32gb
    Auto-detection uses psutil.virtual_memory().total.
    """
    override = os.getenv("FFACT_MEMORY_TIER", "auto").strip().lower()
    if override != "auto":
        return override
    total_gb = psutil.virtual_memory().total / 1024 ** 3
    for threshold, tier in TIER_THRESHOLDS:
        if total_gb >= threshold:
            return tier
    return "8gb"
```

### 2.3 各層級開啟的功能矩陣

| 功能 | 8GB | 16GB | 24GB | 32GB |
|------|-----|------|------|------|
| L6.5 FFACT_L65_WORKERS | 4 | 6 | 8 | 8 |
| L6.5 CGSA in-memory buffer | ❌ | ❌ | 32 groups | 64 groups |
| L3 Time chunking | 必要（大資料集）| 選用 | 選用 | ❌（記憶體足夠）|
| L6.5 Polars wide matrix | ❌ | ❌ | ✅（若 cols×rows<24GB）| ✅ |
| L7 ThreadPool workers | 4 | 6 | 8 | 8 |

> **為什麼現在就實作高 tier 路徑**：升級後直接生效，不需要重新研究和開發。AI Agent 也可以用 `FFACT_MEMORY_TIER=24gb` 在模擬環境下測試高 tier 路徑的正確性。

---

## 三、未被啟用的既有功能盤點

### 3.1 `resume_from_manifest()` — 已實作，從未在 production 呼叫（最重要）

| 項目 | 狀態 |
|------|------|
| **實作位置** | `column_group_registry.py` L342 |
| **呼叫現況** | 僅在 `tests/test_column_group.py`；production 從未呼叫 |
| **根本原因** | `_prepare_cgsa_registry()` 每次呼叫 `tempfile.mkdtemp()` 建立隨機路徑，且**不傳入 config_hash** → 崩潰後無法找回舊的 work_dir |
| **影響** | L6.5 在第 700/708 群組崩潰 → 必須從頭重跑 2,424s |

**修正原則（預設為開，無需任何 env var）**：

```python
# 修正後：feature_factory.py 兩處改動

# (1) 呼叫端 L135 — 補傳 config_hash
self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe, config_hash)

# (2) _prepare_cgsa_registry 函式本體
def _prepare_cgsa_registry(self, symbol, timeframe, config_hash: str = "") -> Optional[ColumnGroupRegistry]:
    if not self._cgsa_enabled():
        return None

    configured_work_dir = os.getenv("FFACT_CGSA_WORK_DIR", "").strip()
    if configured_work_dir:
        work_dir = Path(configured_work_dir)
    else:
        # ✅ 決定性路徑：不再用 tempfile.mkdtemp()
        safe_symbol = re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)
        safe_tf     = re.sub(r"[^A-Za-z0-9_.-]+", "_", timeframe)
        hash_prefix = config_hash[:8] if config_hash else "nohash"
        work_dir = Path("data_cache/cgsa_work") / f"{safe_symbol}_{safe_tf}_{hash_prefix}"
        work_dir.mkdir(parents=True, exist_ok=True)

    # ✅ 預設為開：manifest 存在就 resume
    manifest_path = work_dir / "manifest.json"
    if manifest_path.exists():
        logger.info("[CGSA] Resuming from manifest at %s", work_dir)
        return ColumnGroupRegistry.resume_from_manifest(work_dir)

    logger.info("[CGSA] Initialized fresh ColumnGroupRegistry at %s", work_dir)
    return ColumnGroupRegistry(work_dir=work_dir)
```

---

### 3.2 `compression_level` — ✅ 維持 level=1，速度優先

**決定**：維持 `compression="zstd"`（無 level 參數，預設 level=1）。速度優先，不更改。

---

### 3.3 `FFACT_LAYER1_PARALLEL` — Phase 5 完成，**維持關閉**

L1 耗時 3.3s（0.04% of total），ROI 不符合，風險存在。詳見 VERIFICATION doc R21。

---

## 四、優化優先順序 P0–P3（全硬體層級）

### P0 — L6.5 Preprocessing 平行化

**瓶頸**：`transform_registry_groups()` 純串行；708 群組完全獨立。

#### P0-A：ThreadPoolExecutor（8GB 現況，立即可做）

```python
# feature_preprocessor.py
def transform_registry_groups(self, registry, n_workers: int = 1) -> int:
    if n_workers > 1:
        return self._transform_registry_parallel(registry, n_workers)
    # 現有串行路徑不變

# 呼叫端（feature_factory_service.py 或 feature_factory.py）
from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier
_WORKERS_BY_TIER = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
tier = get_memory_tier()
n_workers = int(os.getenv("FFACT_L65_WORKERS", _WORKERS_BY_TIER[tier]))
preprocessor.transform_registry_groups(registry, n_workers=n_workers)
```

- `overwrite_data()` 原子寫入（temp + os.replace）→ thread-safe ✅
- `load_data(mmap_mode="r")` → 多執行緒讀取安全 ✅
- 主執行緒先 `warmup_numba()` → 確保 JIT compile 完成再啟動 pool

| Tier / Workers | 預估 L6.5 耗時 | 節省 |
|---------------|--------------|------|
| 8GB / 4 workers | ~606s | **-1,818s** |
| 16GB / 6 workers | ~404s | **-2,020s** |
| 24GB / 8 workers | ~303s | **-2,121s** |

#### P0-B：CGSA In-Memory Buffer（24/32GB，同步實作）

**問題**：L2 生成 46,677 cols 期間，每個 group 計算後立即 flush（708 次 disk write）。  
**解決**：24/32GB 有足夠 RAM 緩衝多個 group 的 .npy 陣列，批次寫入。

```python
# column_group_registry.py 新增
class ColumnGroupRegistry:
    def __init__(self, work_dir, memory_buffer_groups: int = 0):
        # memory_buffer_groups=0 → 立即 flush（現有行為）
        # memory_buffer_groups=N → 緩衝 N 個 group 後批次寫
        self._memory_buffer: Dict[str, np.ndarray] = {}
        self._memory_buffer_limit = memory_buffer_groups

    def save_data(self, group_id: str, data: np.ndarray):
        if self._memory_buffer_limit > 0:
            self._memory_buffer[group_id] = data
            if len(self._memory_buffer) >= self._memory_buffer_limit:
                self._flush_buffer()
        else:
            self._write_npy(group_id, data)  # 現有路徑

# 呼叫端
_CGSA_BUFFER_BY_TIER = {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}
buffer = int(os.getenv("FFACT_CGSA_MEMORY_BUFFER", _CGSA_BUFFER_BY_TIER[tier]))
registry = ColumnGroupRegistry(work_dir, memory_buffer_groups=buffer)
```

- buffer=0（8/16GB）→ 完全向後相容，現有行為不變
- buffer=32（24GB）→ 每 32 個 group 一次 disk write，約 709/32 ≈ 22 次 write（vs 708 次）

#### P0-C：Polars Wide Matrix（32GB，同步實作）

**前提**：435K cols × 17,928 rows × float32 = ~30 GB → 只在 32GB tier 可行  
**實作**：在 `feature_preprocessor.py` 新增 `_transform_polars_wide()` 路徑

```python
def transform_registry_groups(self, registry, n_workers: int = 1) -> int:
    tier = get_memory_tier()
    
    if tier == "32gb" and os.getenv("FFACT_L65_POLARS", "auto") != "0":
        return self._transform_polars_wide(registry)  # 全群組一次 Polars 操作
    
    if n_workers > 1:
        return self._transform_registry_parallel(registry, n_workers)
    
    return self._transform_registry_serial(registry)  # 現有路徑
```

- 32GB tier 預設啟用；可用 `FFACT_L65_POLARS=0` 關閉（回到 ThreadPool）
- 消除 708 次 .npy load/save round-trip
- 使用 Polars lazy evaluation + row-wise winsorize kernel

---

### P1 — L2 CGSA I/O 優化

**工作項目**：

1. **Resume 啟用**（即第三節 3.1 修正，最優先）

2. **批次 .npy writes**（即 P0-B CGSA In-Memory Buffer，兩者是同一個修正）

3. **CGSA disk I/O 在各 tier 的分析**

| Tier | 策略 | 理由 |
|------|------|------|
| 8GB | 維持現有逐群 flush | 記憶體不足，必須 disk-backed |
| 16GB | 同 8GB | 30GB 矩陣仍超過 16GB |
| 24GB | buffer=32 groups | 足夠緩衝 32 × ~43MB avg = ~1.4GB |
| 32GB | buffer=64 groups + Polars wide | 無 disk I/O（除崩潰 checkpoint） |

---

### P2 — L3 Rolling Aggregation 優化

**現況確認**：
- `FFACT_USE_NUMBA_ROLLING`: ✅ **預設 "1"，V7 已啟用** → 非 TODO
- `FFACT_L3_STREAMING=1`: ✅ 已啟用

#### P2-A：Multi-Window Fused Kernel（自動最佳化，不需旗標）

**當前瓶頸**：`_compute_all_streaming_numba()` 的內層迴圈：

```python
for window in self._windows:          # 8 次外迴圈
    for start in chunk_starts:         # N chunks 外迴圈
        for col_idx, col_name in ...:  # per-column
            fused = fused_rolling_stats(values, int(window))  # 每 col 每 window 各呼叫一次
```

每個 column 被讀取 **8 次**（每 window 一次），L1 cache 無法保留。

**優化**：擴展 numba kernel 為多 window 版本，每個 column **讀取 1 次**：

```python
# numba_rolling.py 新增
@numba.njit(parallel=True, cache=True)
def fused_rolling_stats_multi_window(
    values: np.ndarray,    # shape (n_rows,)
    windows: np.ndarray,   # shape (n_windows,) int32
) -> np.ndarray:           # shape (n_rows, n_windows, N_STATS)
    ...

# 呼叫端 _compute_all_streaming_numba 改為：
for start in chunk_starts:             # ← 改為外迴圈
    for col_idx, col_name in ...:
        fused_all = fused_rolling_stats_multi_window(values, windows_array)  # 一次讀取
        for wi, window in enumerate(self._windows):
            fused = fused_all[:, wi, :]  # slice，無額外計算
```

**效益**：column 讀取次數 8→1（減少 cache miss），理論加速 1.5-2×（記憶體頻寬瓶頸時）  
**可行性**：完全向後相容，不需要新旗標，直接替換為預設路徑

#### P2-B：Wider Streaming（多 Window 同時跑 Variance Filter）

當前：每個 (window, agg) step 各自做 variance filter（80 步分別寫入 out_arr）  
改進：每個 window 的所有 agg 計算完畢後，做一次 batch variance filter 再寫入  
效果：減少 memmap write 次數（80→8，按 window 分批）  
需確認：variance filter 結果是否依賴 agg（是）→ 按 window 分批而非全部一次

#### P2-C：Time Chunking（全硬體層級設計，現在規劃）

**目的**：支援 1min 大資料集（5yr × 1min = ~630K rows）

**設計**：

```python
# momentum/FeatureEngineering/utils/time_chunk_iterator.py（新增）

_CHUNK_BARS_BY_TIER = {
    "8gb":  50_000,   # ~3 months of 1min
    "16gb": 100_000,  # ~6 months
    "24gb": 250_000,  # ~15 months
    "32gb": None,     # None = 不分割，整體讀入
}

class TimeChunkIterator:
    """
    Splits a time-indexed DataFrame into overlapping chunks for streaming pipeline.
    
    Overlap ensures L3 rolling correctness:
      - overlap_bars = max_window - 1 (e.g., window=89 → overlap=88)
      - Overlap rows are trimmed from the OUTPUT of each chunk before merge.
    
    Usage:
        iterator = TimeChunkIterator(df, tier=get_memory_tier(), max_window=89)
        for chunk, ctx in iterator:
            result_chunk = pipeline.run(chunk)
            result_chunk = ctx.trim_overlap(result_chunk)  # remove lookback rows
            results.append(result_chunk)
        final = pd.concat(results)
    """
    def __init__(
        self, 
        df: pd.DataFrame,
        tier: str | None = None,
        max_window: int = 89,
        chunk_bars: int | None = None,  # 明確指定覆蓋 tier
    ):
        self._tier = tier or get_memory_tier()
        self._max_window = max_window
        self._chunk_bars = chunk_bars or _CHUNK_BARS_BY_TIER[self._tier]
        self._df = df
    
    def __iter__(self):
        if self._chunk_bars is None:
            # 32GB tier：整體處理，no chunking
            yield self._df, ChunkContext(overlap=0, is_last=True)
            return
        
        n = len(self._df)
        overlap = self._max_window - 1
        start = 0
        while start < n:
            end = min(start + self._chunk_bars, n)
            # 前向補 overlap（除了第一個 chunk）
            actual_start = max(0, start - overlap)
            chunk = self._df.iloc[actual_start:end]
            ctx = ChunkContext(
                trim_start=(start - actual_start),
                is_last=(end == n),
            )
            yield chunk, ctx
            start = end
```

**整合到 Feature Factory**：

```python
# feature_factory.py generate_features() 中
tier = get_memory_tier()
chunk_bars = _CHUNK_BARS_BY_TIER[tier]

if chunk_bars is not None and len(df) > chunk_bars * 1.2:
    # 大資料集：分段處理
    return self._generate_features_chunked(df, symbol, timeframe, config_hash, tier)
else:
    # 小資料集（現有路徑）
    return self._generate_features_single(df, symbol, timeframe, config_hash, tier)
```

**各 tier 的 chunk size 依據**：

| Tier | chunk_bars | 記憶體佔用估計（以 L3 peak 為準） |
|------|-----------|--------------------------------|
| 8GB  | 50,000    | ~1.8 GB per chunk (safe) |
| 16GB | 100,000   | ~3.6 GB per chunk (safe) |
| 24GB | 250,000   | ~9 GB per chunk (safe) |
| 32GB | None      | 整體 630K rows ≈ 23 GB (can fit) |

---

### P3 — L7 Parallel Parquet Writes

**✅ max_group_split 已確認生效**：
- 1h L2_WorldQuant → 6 parts (part1~6)，各約 180-195 MB
- 12h L2_WorldQuant → 6 parts，各約 139-178 MB
- **P3 ThreadPool 已可直接實作**，不需等待分割

**工作項目**：

```python
# feature_storage.py persist_registry_to_parquet() 改進
from concurrent.futures import ThreadPoolExecutor

def _persist_parts_parallel(self, parts_queue, output_dir, n_workers: int):
    """Write prepared (part_id, table) tuples in parallel."""
    def _write_one(item):
        part_id, table, final_path, staging_path = item
        pq_writer.write_table(table, staging_path, compression="zstd")
        os.replace(staging_path, final_path)
        return str(final_path.resolve())
    
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        return list(pool.map(_write_one, parts_queue))
```

**呼叫端**（硬體自適應 workers）：

```python
tier = get_memory_tier()
_L7_WORKERS_BY_TIER = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
n_workers = int(os.getenv("FFACT_L7_WORKERS", _L7_WORKERS_BY_TIER[tier]))
```

---

## 五、硬體資訊 API + 前端顯示

### 5.1 後端：`GET /config/hardware` endpoint

**檔案**：`api/routes/config.py`

```python
@router.get("/hardware")
async def get_hardware_info():
    import os, shutil
    import psutil
    from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier

    vm = psutil.virtual_memory()
    data_cache_path = Path("data_cache").resolve()
    try:
        disk = shutil.disk_usage(data_cache_path)
        disk_free_gb  = round(disk.free  / 1024**3, 1)
        disk_total_gb = round(disk.total / 1024**3, 1)
        disk_used_pct = round(disk.used / disk.total * 100, 1)
    except OSError:
        disk_free_gb = disk_total_gb = disk_used_pct = 0.0

    tier = get_memory_tier()
    return {
        "memory_tier": tier,           # ← AI Agent 可用此判斷最佳參數
        "cpu": {
            "logical_cores":  os.cpu_count() or 1,
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "usage_pct":      psutil.cpu_percent(interval=0.1),
        },
        "memory": {
            "total_gb":     round(vm.total     / 1024**3, 1),
            "available_gb": round(vm.available / 1024**3, 1),
            "used_pct":     round(vm.percent, 1),
        },
        "disk": {
            "path":      str(data_cache_path),
            "free_gb":   disk_free_gb,
            "total_gb":  disk_total_gb,
            "used_pct":  disk_used_pct,
        },
        "recommended_settings": {
            "FFACT_L65_WORKERS": {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}[tier],
            "FFACT_CGSA_MEMORY_BUFFER": {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}[tier],
            "FFACT_L7_WORKERS": {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}[tier],
        },
    }
```

> `memory_tier` 和 `recommended_settings` 讓 V2 Chat / V3 Agent 可直接讀取並自動配置。

### 5.2 前端：`HardwareStatusPanel.tsx`

**位置**：`frontend/src/components/feature-factory/HardwareStatusPanel.tsx`（新增）

```
┌─────────────────────────────────────────────────────┐
│  系統資源                       Tier: 8GB  [重新整理] │
│  CPU   8 核（4 實體）  使用率 23%                    │
│  RAM   8.0 GB  可用 4.2 GB  已用 47%                │
│  磁碟  228 GB  可用 142 GB  已用 38%                 │
│  ─────────────────────────────────────────────────  │
│  建議設定：L65_WORKERS=4  CGSA_BUFFER=0  L7_WORKERS=4 │
└─────────────────────────────────────────────────────┘
```

顏色邏輯：RAM 可用 < 2 GB → 黃色；< 1 GB → 紅色（OOM 風險）

---

## 六、Pre-opt_vs_V7 建議方向 × 本文件對照

| 優先級 | Pre-opt doc 建議 | 本文件方案 | 一致性 |
|--------|-----------------|-----------|--------|
| **P0** L6.5 2-4× | Polars vectorized, 減少 per-group overhead | 8GB=ThreadPool；24GB=CGSA buffer；32GB=Polars wide（**全部現在實作**）| ✅ |
| **P1** L2 1.5-2× | CGSA registry I/O 優化, batch .npy writes | Resume fix + P0-B CGSA buffer | ✅ |
| **P2** L3 1.3× | Numba fused kernels, wider streaming steps | multi-window kernel + batch variance filter（Time chunking 補入）| ✅ |
| **P3** L7 2× | Parallel parquet writes, compression tuning | ThreadPool parallel（split 已生效，可直接做）| ✅ |

---

## 七、執行優先順序總覽

```
優先序（依 ROI + 依賴關係）：

  1. hardware_utils.py （get_memory_tier）— 所有其他優化的前置依賴
  2. Resume fix（3.1 修正，2-10 行，最低風險）
  3. P0-A: L6.5 ThreadPool（最高 ROI，-1,818s at 4 cores）
  4. P0-B: CGSA In-Memory Buffer（與 P0-A 同 PR，24/32GB 自動啟用）
  5. P0-C: Polars wide matrix（與 P0-A 同 PR，32GB 自動啟用）
  6. P2-A: Multi-window fused kernel（L3，替換現有 kernel，無新旗標）
  7. P2-B: Batch variance filter（L3，低風險）
  8. P2-C: TimeChunkIterator（1min 大資料集支援）
  9. P3: L7 ThreadPool parallel writes（max_group_split 已生效，直接做）
  10. 硬體資訊 API + 前端（獨立，任何時間可做）

  FFACT_LAYER1_PARALLEL（L1=3.3s，ROI 太低，永久不啟用）
```

---

## 八、改動檔案索引

| 檔案 | 改動類型 | 對應項目 |
|------|---------|---------|
| `momentum/FeatureEngineering/utils/hardware_utils.py` | **新增**（~30 行） | 全局 tier 偵測 |
| `momentum/FeatureEngineering/feature_factory.py` | 函式簽名 + 路徑邏輯（~10 行） | Resume fix + Tier 整合 |
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | n_workers + Polars wide 路徑 | P0-A/C |
| `momentum/FeatureEngineering/core/column_group_registry.py` | memory_buffer 參數 | P0-B |
| `momentum/FeatureEngineering/operators/numba_rolling.py` | multi-window kernel | P2-A |
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | 改用 multi-window kernel + batch variance filter | P2-A/B |
| `momentum/FeatureEngineering/utils/time_chunk_iterator.py` | **新增** | P2-C |
| `momentum/FeatureEngineering/feature_storage.py` | ThreadPool parallel writes | P3 |
| `api/routes/config.py` | 新增 endpoint | 硬體資訊 |
| `frontend/src/components/feature-factory/HardwareStatusPanel.tsx` | **新增** | 硬體資訊 |

---

## 九、關鍵常數（實作時參考）

```python
MAX_GROUP_COLUMNS    = 5_000    # L7 自動分割閾值（已生效）
MAX_L65_GROUP_COLS   = 16_110   # L2_Momentum（最大群組，RAM 限制因子）
L65_GROUP_COUNT      = 708      # V7 baseline
L65_AVG_S_PER_GROUP  = 3.42    # V7 profiling 測量值
L65_TOTAL_SECONDS    = 2_424    # V7 baseline
CGSA_WORK_DIR_BASE   = "data_cache/cgsa_work"

# 硬體層級預設值
_WORKERS_BY_TIER     = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
_CGSA_BUFFER_BY_TIER = {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}
_CHUNK_BARS_BY_TIER  = {"8gb": 50_000, "16gb": 100_000, "24gb": 250_000, "32gb": None}
```

---

## 十、效益預估總覽

| 項目 | 現況（8GB）| 8GB 目標 | 24GB 目標 | 32GB 目標 |
|------|-----------|---------|---------|---------|
| Resume fix（崩潰場景）| 重跑 2,424s | resume 剩餘 | resume 剩餘 | resume 剩餘 |
| P0-A L6.5 parallel | 2,424s | ~606s (×4) | ~303s (×8) | ~303s (×8) |
| P0-B CGSA buffer | 2,055s (L2) | 不變 | ~1,300s | ~1,000s |
| P0-C Polars wide | 2,424s | 不可行 | 不可行 | ~500s |
| P2-A multi-window kernel | 2,051s (L3) | ~1,400s | ~800s | ~400s |
| P3 L7 parallel | 467s | ~150s | ~100s | ~80s |
| **合計（8GB ×4）** | **7,756s** | **~5,300s** | **—** | **—** |
| **合計（24GB ×8）** | **7,756s** | **—** | **~3,500s** | **—** |
| **合計（32GB）** | **7,756s** | **—** | **—** | **~2,000s** |

> ⚠️ `hardware_utils.py` 是所有其他項目的前置依賴，應第一個實作。所有優化路徑現在就寫好，硬體升級後自動生效。