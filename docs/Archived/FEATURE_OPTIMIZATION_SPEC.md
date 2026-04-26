# Feature Factory V8 效能優化規劃書（SPEC）

> **搭配工具**: `templates/TODO_GENERATION_PROMPT.md`（V6+）可直接消化符合本模板的 SPEC。
> 結構完整的 SPEC 會跳過正規化階段，直接進入索引提取。
>
> **基於**: `docs/OPTIMIZATION_TODO_PLANNING.md` (v3) + `Pre-opt_vs_V7_Comparison.md`
> **目標**: V7 Baseline 7,756s → 8GB 目標 ~5,300s / 24GB 目標 ~3,500s / 32GB 目標 ~2,000s，全硬體層級自適應
> **約束**: 不減特徵、不降品質、數值完全等價、向後相容（所有優化可透過 env var 關閉）
> **執行者**: AI Agent（全自動，含測試）
> **建立日期**: 2026-04-20
> **修訂日期**: 2026-04-20（Review pass — 修復 11 項缺陷後凍結）
> **版本**: V1
> **硬體**: MacBook M1 8GB RAM（主要）；16/24/32GB 層級同步實作
> **狀態**: 🔒 FROZEN
>
> **V7 Baseline 數字**:
> | 指標 | 數值 |
> |------|------|
> | Pipeline 總耗時 | 7,756s (129 min) |
> | 特徵數 | 435,389 |
> | 輸出大小 | 15,799 MB (15.8 GB), 724 files |
> | Peak RSS | 3,990 MB |
> | L2 Derived Features | ~2,055s (27.8%) |
> | L3 Rolling Aggregation | ~2,051s (27.8%) |
> | L6.5 Preprocessing | ~2,424s (32.8%, 708 groups × 平均 3.42s) |
> | L7 Validate+Persist | ~467s (6.3%) |

---

## 目錄

0. [AI Agent 生成規範](#0-ai-agent-生成規範)
1. [全局約束與驗收標準](#1-全局約束與驗收標準)
2. [Phase 0 — 硬體偵測基礎建設](#2-phase-0--硬體偵測基礎建設)
3. [Phase 1 — Resume 啟用 + CGSA 修正](#3-phase-1--resume-啟用--cgsa-修正)
4. [Phase 2 — L6.5 Preprocessing 平行化（P0）](#4-phase-2--l65-preprocessing-平行化p0)
5. [Phase 3 — L3 Rolling Aggregation 優化（P2）](#5-phase-3--l3-rolling-aggregation-優化p2)
6. [Phase 4 — L7 Parallel Parquet Writes + Async Compactor（P3）](#6-phase-4--l7-parallel-parquet-writes--async-compactorp3)
7. [Phase 5 — 硬體資訊 API + 前端顯示](#7-phase-5--硬體資訊-api--前端顯示)
8. [Phase Gate 決策矩陣](#8-phase-gate-決策矩陣)
9. [全局測試策略](#9-全局測試策略)
10. [風險登記簿](#10-風險登記簿)
- [附錄 A: 效能預估對照表](#附錄-a-效能預估對照表)
- [附錄 B: 參考文件](#附錄-b-參考文件)
- [附錄 C: AI Agent 執行清單](#附錄-c-ai-agent-執行清單)
- [附錄 D: 環境變數 / Feature Flag 彙整](#附錄-d-環境變數--feature-flag-彙整)
- [附錄 E: 關鍵常數](#附錄-e-關鍵常數)

---

## 0. AI Agent 生成規範

> 本節摘錄自 `.github/copilot-instructions.md` 及 `docs/ARCHITECTURE.md`，
> 列出與本 SPEC 最直接相關的規則子集。Agent 實作時必須遵守。

### 0.1 解耦/架構規則

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
- `hardware_utils.py` 位於 `momentum/FeatureEngineering/utils/`（R1 — 不可 import api/）
- `GET /config/hardware` endpoint 在 `api/routes/config.py`（R3 — 透過 import `hardware_utils` 而非 factory）
- 前端 `HardwareStatusPanel.tsx` 在 `frontend/src/components/feature-factory/`（獨立元件）

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
logger.info(f"Processing group {i}")        # 在 hot loop 中（改用摘要）
```

**本規劃書的具體影響**：
- P0 ThreadPool 完成後 log 摘要：`logger.info("[L6.5] Parallel complete: %d groups in %.2fs, %d workers", ...)`
- L3 multi-window kernel 不可在 Numba 內部 log（Numba JIT 不支援 Python 呼叫）
- L7 parallel writes 完成後 log：`logger.info("[L7] Parallel persist: %d parts in %.2fs", ...)`

### 0.3 Error Handling 模式

```python
from enum import Enum

class FailureType(Enum):
    IO_ERROR = "io_error"          # .npy / Parquet 寫入失敗 → retryable
    OOM = "oom"                     # 記憶體不足 → 不 retry，降級處理
    VALIDATION = "validation"       # 數值驗證失敗 → 不 retry，回退
    CONFIG = "config"               # 設定錯誤 → 不 retry，修正 config
```

### 0.4 命名規範

| 類型 | 規則 | 範例 |
|------|------|------|
| 函式 | snake_case，動詞開頭 | `get_memory_tier()`, `transform_registry_parallel()` |
| 類別 | PascalCase | `TimeChunkIterator`, `HardwareStatusPanel` |
| 常數 | UPPER_SNAKE_CASE | `TIER_THRESHOLDS`, `_WORKERS_BY_TIER` |
| 變數 | snake_case，語義清楚 | `memory_tier`, `n_workers`, `chunk_bars` |
| 禁止 | — | `df1`, `temp`, `x`, `data2`, `result_new` |

### 0.5 Type Hints 要求

所有新增函式必須有完整 type annotations：

```python
# ✅ 正確
def get_memory_tier() -> str:
    ...

def transform_registry_groups(
    self,
    registry: 'ColumnGroupRegistry',
    n_workers: int = 1,
) -> int:
    ...

# ❌ 禁止
def get_memory_tier():
    ...
```

### 0.6 測試規範

```python
# 測試函式名稱：test_{功能}_{場景}
# 必須有中文 docstring 說明
# 使用 pytest fixture 管理共用狀態

import pytest

def test_get_memory_tier_auto_detection():
    """測試 get_memory_tier 自動偵測：根據 psutil 回傳正確 tier"""
    ...

def test_get_memory_tier_env_override():
    """測試 FFACT_MEMORY_TIER 環境變數覆蓋：設定 '16gb' 應回傳 '16gb'"""
    ...
```

**測試檔案結構規則**：
- 路徑：`tests/test_{module_name}.py`
- 效能測試：`tests/performance/test_{module_name}_perf.py`
- 測試可獨立執行（Rule 6），不需啟動 API server

### 0.7 效能程式碼慣例

```python
# 優先順序（從快到慢）：
# 1. 向量化 numpy/pandas
# 2. Numba @njit
# 3. ThreadPoolExecutor (I/O bound) / ProcessPoolExecutor (CPU bound)
# 4. Python loop（最後手段）

# ✅ Numba（必須用 cache=True）
@numba.njit(cache=True, parallel=True)
def fused_rolling_stats_multi_window(values, windows):
    ...

# ✅ ThreadPool for I/O-bound parallel
with ThreadPoolExecutor(max_workers=n_workers) as pool:
    results = list(pool.map(_write_one, parts_queue))
```

### 0.8 向後相容原則

> 每個 Phase 的行為變更應提供 fallback 機制，確保可切回舊行為。

| Phase | Fallback 機制 | 環境變數/Feature Flag |
|-------|--------------|---------------------|
| Phase 2 | L6.5 串行路徑 | `FFACT_L65_WORKERS=1` |
| Phase 3 | 現有 per-window kernel | `FFACT_L3_MULTI_WINDOW=0`（回到逐 window 呼叫） |
| Phase 4 | L7 串行 writes + 停用背景合併 | `FFACT_L7_WORKERS=1`, `FFACT_L7_COMPACTOR_ENABLED=0` |
| Phase 0/1 | 無需 fallback（純增、純修正） | — |
| Phase 5 | 無需 fallback（獨立新功能，不影響核心 pipeline） | — |

### 0.9 Pre-Commit 檢查清單（每個 Task 完成後）

```
□ Ultra Think 3 步完成（生成 → 自審 → 優化）
□ grep -r "from api\." momentum/ → 0 結果（R1）
□ 無 hardcoded data（Data Truth Principle）
□ 所有函式有 type hints
□ Error handling 使用 FailureType 分類（涉及 I/O 時）
□ Logging 符合 §0.2 規範
□ 命名符合 §0.4 規範
□ 測試有中文 docstring
□ 測試可獨立執行（無需 run_api.py）
□ .npy / .parquet 不在 git track 中
□ 效能程式碼已向量化（§0.7）
□ Fallback env var 可切回舊行為（§0.8）
□ ruff check momentum/ → 0 error
□ smoke test：pytest tests/ -m "not slow" -x -q → 0 error
```

---

## 1. 全局約束與驗收標準

### 1.1 硬約束（不可退讓）

| ID | 約束 | 驗收條件 | 驗證方式 |
|----|------|---------|---------|
| C1 | **數值等價**：優化後 pipeline 輸出與 V7 Baseline 完全一致 | 全欄位 `np.allclose(atol=1e-4, equal_nan=True)` | Golden output test suite |
| C2 | **不減特徵**：feature_count = 435,389（ETHUSDT 2TF） | `assert new_count == 435_389` | Pipeline 輸出比對 |
| C3 | **不改 column name**：欄位名稱集合完全一致 | `assert set(new_cols) == set(golden_cols)` | Column set 比對 |
| C4 | **RAM 峰值 ≤ 6 GB**（8GB 機器留 2GB 給 OS） | `psutil.Process().memory_info().rss` < 6 × 1024³ | RSS 監控 |
| C5 | **無 future leakage**：align 後 12h 特徵不超前 primary 1h | `validate_no_future_leak()` PASS | 現有驗證函式 |
| C6 | **NaN 語義一致**：rolling window 開頭的 NaN pattern 完全相同 | per-column NaN mask comparison | `np.array_equal(nan_mask_new, nan_mask_golden)` |
| C7 | **硬體自適應**：所有優化自動偵測硬體 tier 並啟用最佳路徑 | 4 tier 路徑均可執行 | `FFACT_MEMORY_TIER={8gb,16gb,24gb,32gb}` 各跑一次 |

### 1.2 每 Phase 通用驗收流程

```
1. 建立 git branch: perf/v8-phase-{N}-{description}
2. 完成目標修改
3. 執行 golden output comparison（C1~C3, C6）
4. 執行 future leak test（C5）
5. 記錄 RSS 峰值（C4）
6. 記錄 wall-clock time（各 layer 分別計時）
7. 全部 PASS → 合併到 main；任一 FAIL → 回退到 branch 起點，定位問題
```

### 1.3 回退策略

每個 Phase 都在獨立 branch 上開發，失敗時：
1. `git stash` 保留修改
2. `git checkout main` 回到穩定版
3. 分析失敗原因，修正後在同 branch 重試
4. 連續失敗 3 次以上 → 重新評估該 Phase 的技術方案

### 1.4 Golden Output / Baseline 基準定義

- **Symbol**: ETHUSDT
- **Timeframes**: primary=1h, training=[1h, 12h]
- **Config**: `scan_config.yaml` 預設設定（全開 L1~L6, L6.5 ON）
- **Baseline**: V7 完整輸出（7,756s run, 435,389 features, 724 files）
- **儲存位置**: `data_cache/features/` 下的 V7 輸出即為 golden baseline
- **比對精度**: 全量 `atol=1e-4`（取最寬鬆 layer 的上限，與 FEATURE_FACTORY_OPTIMIZATION_SPEC.md §1.1 一致）

### 1.5 明確排除項目（Out of Scope）

以下項目經評估後**明確排除**於本 SPEC 範圍外，AI Agent 不應重新調查或實作：

| 項目 | 排除理由 | 來源 |
|------|---------|------|
| `FFACT_LAYER1_PARALLEL`（L1 平行化） | L1 耗時僅 3.3s（佔總時間 0.04%），ROI 極低，維持關閉 | TODO §3.3 |
| `compression_level` 調整 | 目前 zstd level=1 已是速度優先設定，維持不變 | TODO §3.2 |
| L1 Kline Data Ingestion 優化 | L1 耗時 3.3s（0.04%），非瓶頸 | TODO §四 分析 |
| L4/L5/L6 優化 | L4(22s) + L5(0.6s) + L6(0s) 合計 < 0.3%，非瓶頸 | Pre-opt_vs_V7 |

---

## 2. Phase 0 — 硬體偵測基礎建設

> **目標**: 建立 `get_memory_tier()` 硬體自動偵測框架，作為所有後續優化的前置依賴
> **預計效果**: 建立觀測能力，零效能影響
> **風險**: 低（純新增工具模組，不改變現有行為）

### 2.1 任務清單

#### Task 0.1: 建立 `hardware_utils.py`（get_memory_tier）

- **目標**: 實作記憶體層級自動偵測，支援環境變數覆蓋
- **修改檔案**: `momentum/FeatureEngineering/utils/hardware_utils.py`（**新增**）
- **實作規格**:
  - 函式簽名：
    ```python
    def get_memory_tier() -> str:
        """
        Returns hardware tier string: '8gb' | '16gb' | '24gb' | '32gb'.
        
        Override via: FFACT_MEMORY_TIER=auto|8gb|16gb|24gb|32gb
        Auto-detection uses psutil.virtual_memory().total.
        """
    ```
  - 記憶體層級定義：

    | Tier | 自動偵測閾值 | 代表機器 |
    |------|------------|---------|
    | `8gb`  | < 12 GB | 8 GB M1 Air（現況） |
    | `16gb` | 12-20 GB | 16 GB M1/M2 |
    | `24gb` | 20-28 GB | 24 GB M2 Pro |
    | `32gb` | ≥ 28 GB | 32/36 GB M2 Max/Ultra |

  - 偵測邏輯：
    ```python
    TIER_THRESHOLDS = [
        (28, "32gb"),
        (20, "24gb"),
        (12, "16gb"),
        (0,  "8gb"),
    ]
    
    def get_memory_tier() -> str:
        override = os.getenv("FFACT_MEMORY_TIER", "auto").strip().lower()
        if override and override != "auto":
            return override
        total_gb = psutil.virtual_memory().total / 1024 ** 3
        for threshold, tier in TIER_THRESHOLDS:
            if total_gb >= threshold:
                return tier
        return "8gb"
    ```
  - 邊界條件：
    1. `FFACT_MEMORY_TIER` 設定為無效值（如 `"64gb"`）→ 原值回傳（由呼叫端負責驗證）
    2. `psutil` 不可用 → fallback 為 `"8gb"`（最保守）
- **輸出**: `str`（`"8gb"` | `"16gb"` | `"24gb"` | `"32gb"`）
- **禁止事項**: 不可 import `api/`；不可加入 logging（此為純工具函式）

#### Task 0.2: 建立各層級功能矩陣常數

- **目標**: 定義各 tier 對應的 workers、buffer 等參數常數
- **修改檔案**: `momentum/FeatureEngineering/utils/hardware_utils.py`（同 Task 0.1 檔案內新增）
- **實作規格**:
  ```python
  # 各層級開啟的功能矩陣
  _WORKERS_BY_TIER: Dict[str, int] = {
      "8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8
  }
  _CGSA_BUFFER_BY_TIER: Dict[str, int] = {
      "8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64
  }
  _L7_WORKERS_BY_TIER: Dict[str, int] = {
      "8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8
  }
  _CHUNK_BARS_BY_TIER: Dict[str, Optional[int]] = {
      "8gb": 50_000, "16gb": 100_000, "24gb": 250_000, "32gb": None
  }
  
  def get_tier_config(tier: str) -> Dict[str, Any]:
      """Returns recommended configuration for the given memory tier."""
      return {
          "l65_workers": _WORKERS_BY_TIER.get(tier, 4),
          "cgsa_memory_buffer": _CGSA_BUFFER_BY_TIER.get(tier, 0),
          "l7_workers": _L7_WORKERS_BY_TIER.get(tier, 4),
          "chunk_bars": _CHUNK_BARS_BY_TIER.get(tier, 50_000),
      }
  ```
  - 邊界條件：
    1. 未知 tier 字串 → 回傳 8gb 的保守值
    2. `get_tier_config` 回傳的所有值必須為安全預設值
- **輸出**: `Dict[str, Any]`
- **禁止事項**: 不可有任何副作用（純查表函式）
- **風險緩解**: R1（無 api import）

### 2.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T0.1 | `test_get_memory_tier_auto_detection` | psutil 回傳值對應正確 tier | 8GB M1 → `"8gb"` | Task 0.1 |
| T0.2 | `test_get_memory_tier_env_override` | `FFACT_MEMORY_TIER=16gb` → `"16gb"` | 環境變數覆蓋生效 | Task 0.1 |
| T0.3 | `test_get_tier_config_returns_valid_dict` | 所有 4 個 tier 回傳的 dict 包含必要 keys | keys = {l65_workers, cgsa_memory_buffer, l7_workers, chunk_bars} | Task 0.2 |
| T0.4 | `test_get_tier_config_unknown_tier_fallback` | 未知 tier → 回傳 8gb 值 | `l65_workers == 4` | Task 0.2 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T0.B1 | `test_get_memory_tier_env_auto` | `FFACT_MEMORY_TIER=auto` | 走 psutil 偵測路徑 |
| T0.B2 | `test_get_memory_tier_env_empty` | `FFACT_MEMORY_TIER=""` | 走 psutil 偵測路徑 |
| T0.B3 | `test_get_memory_tier_psutil_unavailable` | mock psutil 失敗 | 回傳 `"8gb"` |

### 2.3 Phase 0 → Phase 1 Gate

- [ ] T0.1~T0.4 全部通過
- [ ] T0.B1~T0.B3 全部通過
- [ ] `hardware_utils.py` 無 `from api.` import

---

## 3. Phase 1 — Resume 啟用 + CGSA 修正

> **目標**: 啟用已實作但未被 production 呼叫的 `resume_from_manifest()` 功能
> **預計效果**: 崩潰場景從重跑 2,424s → resume 剩餘部分；正常執行無效能影響
> **風險**: 低（2-10 行修改，最低風險的必要修正）

### 3.1 任務清單

#### Task 1.1: 修正 `_prepare_cgsa_registry()` 使用決定性路徑

- **目標**: 將 `tempfile.mkdtemp()` 隨機路徑改為基於 symbol/timeframe/config_hash 的決定性路徑
- **修改檔案**: `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`
- **實作規格**:
  ```python
  def _prepare_cgsa_registry(
      self,
      symbol: str,
      timeframe: str,
      config_hash: str = "",
  ) -> Optional['ColumnGroupRegistry']:
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
  - 邊界條件：
    1. `config_hash` 為空字串 → 使用 `"nohash"` prefix
    2. `symbol` 含特殊字元（如 `BTC/USDT`）→ `re.sub` 清理為 `BTC_USDT`
    3. manifest.json 存在但損壞（非法 JSON）→ log warning 並建立新 Registry
- **輸出**: `Optional[ColumnGroupRegistry]`
- **禁止事項**: 不可刪除舊的 `tempfile.mkdtemp()` 程式碼路徑（透過 `FFACT_CGSA_WORK_DIR` 保留）

#### Task 1.2: 呼叫端補傳 `config_hash` 參數

- **目標**: 在 `feature_factory.py` 呼叫 `_prepare_cgsa_registry` 處補傳 `config_hash`
- **修改檔案**: `momentum/FeatureEngineering/feature_factory.py` → 呼叫端（~L135）
- **實作規格**:
  ```python
  # 現行:
  self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe)
  
  # 改為:
  self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe, config_hash)
  ```
  - 邊界條件：
    1. `config_hash` 在呼叫處已可用（從 config 計算）
    2. 若 config_hash 不在當前 scope → 需追蹤來源，確認傳入正確值
- **輸出**: 無（修改呼叫簽名）
- **禁止事項**: 不可在此步驟改動 `resume_from_manifest()` 的邏輯（已有實作）

#### Task 1.3: 處理損壞的 manifest.json

- **目標**: 增加 resume 時的容錯處理
- **修改檔案**: `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`
- **實作規格**:
  ```python
  if manifest_path.exists():
      try:
          logger.info("[CGSA] Resuming from manifest at %s", work_dir)
          return ColumnGroupRegistry.resume_from_manifest(work_dir)
      except (json.JSONDecodeError, KeyError, OSError) as e:
          logger.warning("[CGSA] Corrupt manifest at %s: %s, starting fresh", work_dir, e)
          # 不刪除 manifest，讓使用者可以手動檢查
  ```
  - 邊界條件：
    1. manifest.json 為空檔案 → JSONDecodeError → 建新 Registry
    2. manifest.json 缺少必要 key → KeyError → 建新 Registry
- **輸出**: 容錯 fallback 到新 Registry
- **風險緩解**: R2（manifest 損壞不再導致整個 pipeline 失敗）

### 3.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T1.1 | `test_cgsa_deterministic_path` | 相同 symbol/tf/hash → 相同路徑 | 兩次呼叫回傳相同 work_dir | Task 1.1 |
| T1.2 | `test_cgsa_resume_from_existing_manifest` | manifest 存在時 resume 而非新建 | `resume_from_manifest` 被呼叫 | Task 1.1 |
| T1.3 | `test_cgsa_config_hash_passed_correctly` | config_hash 從呼叫端正確傳入 | work_dir 包含 hash prefix | Task 1.2 |
| T1.4 | `test_cgsa_corrupt_manifest_fallback` | 損壞 manifest → 建新 Registry | 不 raise exception | Task 1.3 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T1.B1 | `test_cgsa_empty_config_hash` | config_hash="" | work_dir 含 "nohash" |
| T1.B2 | `test_cgsa_special_chars_in_symbol` | symbol="BTC/USDT:PERP" | 清理為 `BTC_USDT_PERP` |
| T1.B3 | `test_cgsa_work_dir_env_override` | `FFACT_CGSA_WORK_DIR=/tmp/test` | 使用環境變數路徑 |
| T1.B4 | `test_cgsa_empty_manifest_json` | manifest.json 內容為 `""` | JSONDecodeError → 建新 |
| T1.B5 | `test_cgsa_missing_npy_files_in_manifest` | manifest 記錄的 .npy 不存在 | 跳過該 group，不 crash |

### 3.3 Phase 1 → Phase 2 Gate

- [ ] T1.1~T1.4 全部通過
- [ ] T1.B1~T1.B5 全部通過
- [ ] 正常執行（無崩潰）的 pipeline 輸出與 V7 Baseline 數值等價（C1）
- [ ] Resume 場景：手動殺掉 L6.5 中間 → 重跑 → 從中斷點繼續

---

## 4. Phase 2 — L6.5 Preprocessing 平行化（P0）

> **目標**: 將 L6.5 `transform_registry_groups()` 從串行改為 ThreadPool 平行，並支援 CGSA In-Memory Buffer 和 Polars Wide Matrix
> **預計效果**: L6.5 從 2,424s → ~606s (8GB/4w) / ~404s (16GB/6w) / ~303s (24GB/8w)。**最高 ROI 項目，節省 -1,818s**
> **風險**: 中（ThreadPool 並發需確保 thread-safety）

### 4.1 任務清單

#### Task 2.1: 實作 `_transform_registry_parallel()` — P0-A ThreadPool

- **目標**: 新增 ThreadPoolExecutor 平行路徑，保留串行路徑作為 fallback
- **修改檔案**: `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `transform_registry_groups()`
- **實作規格**:
  ```python
  def transform_registry_groups(
      self,
      registry: 'ColumnGroupRegistry',
      n_workers: int = 1,
  ) -> int:
      """Transform all registry groups with optional parallelism.
      
      Args:
          registry: The column group registry containing groups to transform.
          n_workers: Number of parallel workers. 1 = serial (existing path).
      
      Returns:
          Number of groups transformed.
      """
      if n_workers > 1:
          return self._transform_registry_parallel(registry, n_workers)
      return self._transform_registry_serial(registry)  # 現有串行路徑不變
  
  def _transform_registry_parallel(
      self,
      registry: 'ColumnGroupRegistry',
      n_workers: int,
  ) -> int:
      """ThreadPool parallel transform of registry groups."""
      from concurrent.futures import ThreadPoolExecutor, as_completed
      
      groups = registry.list_all_groups()

      # 【新增 — 盲點二】貪婪排程（Greedy Scheduling）：按欄位數降序排列
      # 風險來源：L65_AVG_S_PER_GROUP=3.42s 是平均值，但 L2_Momentum（~16,110 欄）
      # 可能耗時百倍於小型 Group（<50 欄）。若使用原始順序提交，可能出現「3 個 Worker
      # 已完成所有小任務，第 4 個 Worker 才剛開始大任務」的長尾效應。
      # 解法：最大 Group 優先進 Pool，使大任務與小任務盡量並行。
      groups = sorted(
          groups,
          key=lambda g: getattr(g, 'n_columns', 0),
          reverse=True,
      )

      logger.info("[L6.5] Starting parallel transform: %d groups, %d workers",
                  len(groups), n_workers)
      
      completed = 0
      failed = 0
      t0 = time.perf_counter()
      
      with ThreadPoolExecutor(max_workers=n_workers) as pool:
          futures = {
              pool.submit(self._transform_single_group, registry, g): g
              for g in groups
          }
          for future in as_completed(futures):
              group = futures[future]
              try:
                  future.result()
                  completed += 1
              except Exception as e:
                  failed += 1
                  logger.error("[L6.5] Failed to transform group %s: %s",
                              group.group_id, e, exc_info=True)
      
      elapsed = time.perf_counter() - t0
      logger.info("[L6.5] Parallel complete: %d/%d groups in %.2fs (%d failed), %d workers",
                  completed, len(groups), elapsed, failed, n_workers)
      return completed
  ```
  - Thread-safety 保證：
    - `overwrite_data()` 使用原子寫入（temp + `os.replace`）→ thread-safe ✅
    - `load_data(mmap_mode="r")` → 多執行緒讀取安全 ✅
    - 各 group 完全獨立，無共享可變狀態 ✅
    - **注意**：當 CGSA buffer > 0（24/32GB），`save_data()` 經由 `_buffer_lock` 保護（見 Task 2.4）
  - 邊界條件：
    1. `n_workers=0` → 等同 `n_workers=1`，串行執行
    2. groups 為空列表 → 直接回傳 0
    3. 某個 group transform 失敗 → log error，繼續其他 groups
    4. **【新增 — 盲點二】** 所有 groups `n_columns=0`（屬性不存在）→ `sorted` 排序無效但不影響正確性（退化為原始順序）
- **輸出**: `int`（成功 transform 的 group 數）
- **禁止事項**: 不可使用 ProcessPoolExecutor（L6.5 內無 TA-Lib，ThreadPool 足夠且開銷小）

#### Task 2.2: 呼叫端整合 — 硬體自適應 workers

- **目標**: 在呼叫端根據 `get_memory_tier()` 自動選擇 workers 數
- **修改檔案**: `momentum/FeatureEngineering/feature_factory.py`（或 `api/services/feature_factory_service.py`，視呼叫位置）
- **實作規格**:
  ```python
  from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config
  
  tier = get_memory_tier()
  tier_cfg = get_tier_config(tier)
  n_workers = int(os.getenv("FFACT_L65_WORKERS", str(tier_cfg["l65_workers"])))
  buffer_groups = int(os.getenv("FFACT_CGSA_MEMORY_BUFFER", str(tier_cfg["cgsa_memory_buffer"])))
  
  # CGSA buffer 參數傳入 registry
  registry = ColumnGroupRegistry(work_dir=work_dir, memory_buffer_groups=buffer_groups)
  
  # L6.5 平行化
  preprocessor.transform_registry_groups(registry, n_workers=n_workers)
  ```
  - 邊界條件：
    1. `FFACT_L65_WORKERS=1` → 強制串行（fallback）
    2. `FFACT_L65_WORKERS=0` → 等同 1（串行）
- **輸出**: 無（修改呼叫邏輯）
- **風險緩解**: R3（workers=1 即為完整 fallback）

#### Task 2.3: Numba warmup 確保 JIT 完成 — P0-A 前置

- **目標**: 主執行緒先 warmup Numba JIT，再啟動 ThreadPool
- **修改檔案**: `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- **實作規格**:
  ```python
  def _warmup_numba_if_needed(self) -> None:
      """Ensure Numba JIT compilation is complete before parallel execution."""
      if not hasattr(self, '_numba_warmed_up'):
          try:
              from momentum.FeatureEngineering.operators.numba_rolling import warmup_numba
              warmup_numba()
              self._numba_warmed_up = True
          except ImportError:
              self._numba_warmed_up = True  # No numba functions to warm up
  ```
  - 在 `_transform_registry_parallel()` 開頭呼叫
  - 邊界條件：
    1. Numba 未安裝 → ImportError → skip warmup
    2. 多次呼叫 → 只 warmup 一次（`_numba_warmed_up` flag）
    3. **【新增 — 盲點三】** 快取目錄不可寫入（唯讀環境）→ `cache=True` 失效，Numba 每次重新編譯並記錄 warning
    4. **【新增 — 盲點三】** 第一次執行（無磁碟快取）＋ ProcessPoolExecutor → 務必在 `fork()` 前完成主進程 warmup，否則每個子進程各自觸發編譯

  - **【新增 — 盲點三】ThreadPool vs ProcessPool 安全性差異**：
    - **目前實作（ThreadPool）**：所有 Worker 執行緒共用同一進程記憶體，主執行緒 warmup 後 JIT 結果即可直接使用 ✅
    - **若未來引入 ProcessPoolExecutor**（如跨 Symbol 平行化）：fork 出的子進程**不繼承** JIT 編譯結果。8 個子進程同時觸發 Numba 編譯 → CPU 突波 × 8、RAM 突波 → OOM 風險（已列入 R13）
    - **根本防禦**：所有 `@numba.njit` 函式必須設定 `cache=True`（§0.7 已規範）。主進程 warmup 後，Numba 將機器碼快取至磁碟（`~/.cache/numba/` 或 `__pycache__/`）。Fork 出的子進程直接讀取磁碟快取 → 跳過重新編譯
    - **驗證方式**：主進程 warmup 後確認 `.nbi`/`.nbc` 快取檔案存在；子進程啟動時 log 中無 `"numba: compiling"` 訊息

#### Task 2.4: CGSA In-Memory Buffer — P0-B（24/32GB）

- **目標**: 24/32GB tier 緩衝多個 group 的 .npy 陣列，批次寫入減少 disk I/O
- **修改檔案**: `momentum/FeatureEngineering/core/column_group_registry.py` → `ColumnGroupRegistry`
- **實作規格**:
  ```python
  import threading
  
  class ColumnGroupRegistry:
      def __init__(self, work_dir: Path, memory_buffer_groups: int = 0):
          # memory_buffer_groups=0 → 立即 flush（現有行為，8/16GB）
          # memory_buffer_groups=N → 緩衝 N 個 group 後批次寫入
          self._memory_buffer: Dict[str, np.ndarray] = {}
          self._memory_buffer_limit = memory_buffer_groups
          self._buffer_lock = threading.Lock()  # Thread-safe for Task 2.1 ThreadPool
  
      def save_data(self, group_id: str, data: np.ndarray) -> None:
          if self._memory_buffer_limit > 0:
              with self._buffer_lock:
                  self._memory_buffer[group_id] = data
                  if len(self._memory_buffer) >= self._memory_buffer_limit:
                      self._flush_buffer()
          else:
              self._write_npy(group_id, data)  # 現有路徑（無需 lock，各 group 寫獨立檔案）
  
      def _flush_buffer(self) -> None:
          """Batch write buffered groups to disk. Caller must hold _buffer_lock."""
          for group_id, data in self._memory_buffer.items():
              self._write_npy(group_id, data)
          self._memory_buffer.clear()
  
      def finalize(self) -> None:
          """Flush remaining buffer on pipeline completion."""
          with self._buffer_lock:
              if self._memory_buffer:
                  self._flush_buffer()
  ```
  - **Thread-safety 說明**：
    - `_buffer_lock` 保護 buffer 的讀寫 + flush 複合操作
    - 當 buffer=0（8/16GB），`save_data` 直接 `_write_npy`，各 group 寫獨立檔案，無 lock 開銷
    - 當 buffer>0（24/32GB），lock 範圍僅覆蓋 dict 操作，I/O（`_flush_buffer` 內的 `_write_npy`）也在 lock 內以避免並發 flush 衝突。可接受，因為 flush 頻率低（每 32 groups 一次）
  - 邊界條件：
    1. buffer=0（8/16GB）→ 完全向後相容，現有行為不變，無 lock 開銷
    2. Pipeline 中途崩潰 → buffer 中的 data 遺失（可接受，resume 會重算）
    3. `finalize()` 必須在 pipeline 結束時呼叫（確保剩餘 buffer 寫入）
  - **呼叫端整合（finalize）**：
    ```python
    # 在 feature_factory.py 的 L6.5 transform 完成後呼叫
    preprocessor.transform_registry_groups(registry, n_workers=n_workers)
    registry.finalize()  # ← 確保剩餘 buffer 全部寫入 disk
    ```
- **輸出**: 減少 disk writes（708 次 → ~22 次 at buffer=32）
- **禁止事項**: 不可在 8/16GB tier 啟用 buffer（記憶體不足）

#### Task 2.5: Polars Wide Matrix 路徑 — P0-C（32GB）— ⚠️ DEFERRED

> #### Task 2.5: Polars Wide Matrix — ⚠️ DEFERRED to future version
>
> - **延後理由**: 435K cols × 17,928 rows × float32 = ~30 GB，僅在 32GB tier 可行。目前開發機為 8GB，無法測試。且 Polars API 跨版本有 breaking changes（R8）
> - **觸發條件**: 當開發機升級至 32GB，且 P0-A ThreadPool 效果不足時
> - **若跳過的影響**: 32GB tier 使用 ThreadPool 8 workers（~303s），而非 Polars 預估的 ~200s。差距可接受。

### 4.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T2.1 | `test_parallel_transform_matches_serial` | 4 workers 結果 == 1 worker 結果 | `np.allclose(atol=1e-4, equal_nan=True)` | Task 2.1 |
| T2.2 | `test_parallel_transform_all_groups_complete` | 所有 groups 均被處理 | `completed == len(groups)` | Task 2.1 |
| T2.3 | `test_tier_auto_selects_workers` | 8GB tier → 4 workers | `n_workers == 4` | Task 2.2 |
| T2.4 | `test_cgsa_buffer_batch_write` | buffer=4 時每 4 groups 才 flush | mock `_write_npy` 呼叫次數 | Task 2.4 |
| T2.5 | `test_cgsa_buffer_finalize_flushes_remaining` | finalize 清空剩餘 buffer | buffer 為空 | Task 2.4 |
| T2.6 | `test_parallel_greedy_scheduling_largest_groups_first` | 平行提交順序按 `n_columns` 降序 | 最大 group 最先進入 pool | Task 2.1 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T2.B1 | `test_parallel_zero_groups` | 空 groups 列表 | 回傳 0，不 crash |
| T2.B2 | `test_parallel_single_group` | 只有 1 個 group | 正常處理 |
| T2.B3 | `test_parallel_one_group_fails` | 1 個 group raise Exception | 其他 groups 不受影響，回傳 completed < total |
| T2.B4 | `test_parallel_workers_1_is_serial` | n_workers=1 | 走串行路徑 |
| T2.B5 | `test_cgsa_buffer_zero_is_immediate_flush` | buffer=0 | 每次 save 立即 write |
| T2.B6 | `test_cgsa_buffer_crash_loses_unflushed` | buffer=4, 存 2 個後模擬 crash | 只有 0 個寫入 disk |
| T2.B7 | `test_numba_warmup_runs_before_process_pool_fanout` | 模擬未來 ProcessPool 路徑 | 主進程 warmup 先於 worker 啟動 |

#### 效能驗收測試

| ID | 測試名稱 | 驗收標準 |
|----|---------|---------|
| T2.P1 | `test_l65_parallel_4workers_speedup` | 4 workers 比 1 worker 快 ≥ 2× |
| T2.P2 | `test_l65_parallel_rss_under_limit` | RSS 增量 < 1 GB（vs serial baseline） |

### 4.3 Phase 2 → Phase 3 Gate

- [ ] T2.1~T2.6 全部通過
- [ ] T2.B1~T2.B7 全部通過
- [ ] T2.P1 效能驗收通過（≥ 2× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L65_WORKERS=1` fallback 正常

---

## 5. Phase 3 — L3 Rolling Aggregation 優化（P2）

> **目標**: 擴展 Numba kernel 為多 window 版本，每個 column 讀取 1 次（vs 現行 8 次）
> **預計效果**: L3 從 2,051s → ~1,400s (8GB) / ~800s (24GB)。理論加速 1.5-2×
> **風險**: 中（數值穩定性需驗證，Numba ARM64 相容性）

### 5.1 任務清單

#### Task 3.1: 實作 `fused_rolling_stats_multi_window()` — P2-A Multi-Window Fused Kernel

- **目標**: 每個 column 只讀取 1 次，同時計算所有 windows 的 rolling stats
- **修改檔案**: `momentum/FeatureEngineering/operators/numba_rolling.py`（新增函式）
- **實作規格**:
  ```python
  @numba.njit(parallel=True, cache=True)
  def fused_rolling_stats_multi_window(
      values: np.ndarray,    # shape (n_rows,)
      windows: np.ndarray,   # shape (n_windows,) int32
  ) -> np.ndarray:           # shape (n_rows, n_windows, N_STATS)
      """
      Compute rolling statistics for multiple windows in a single pass per column.
      
      Each column is read once from memory, reducing L1 cache misses.
      N_STATS includes: mean, std, min, max, range, zscore, skew, kurt, rank, slope.
      
      Parameters
      ----------
      values : 1D float32 array (n_rows,)
      windows : 1D int32 array (n_windows,)
      
      Returns
      -------
      3D float64 array (n_rows, n_windows, N_STATS)
          Internal computation in float64, caller converts to float32.
      """
      n_rows = len(values)
      n_windows = len(windows)
      N_STATS = 10  # mean, std, min, max, range, zscore, skew, kurt, rank, slope
      
      out = np.full((n_rows, n_windows, N_STATS), np.nan, dtype=np.float64)
      
      for wi in numba.prange(n_windows):
          w = windows[wi]
          # Per-window rolling using Welford + monotonic deque + sorted buffer
          # ... (reuse existing fused_rolling_stats logic, adapted for single-window)
          # Write results to out[:, wi, :]
      
      return out
  ```
  - **關鍵設計決策**：
    - `numba.prange` 平行化在 window 維度（而非 column 維度）→ 避免 column data race
    - 內部 float64 累加器 → 輸出 float64 → 呼叫端轉 float32
    - 維持現有 `fused_rolling_stats()` 作為 fallback（`FFACT_L3_MULTI_WINDOW=0`）
  - 邊界條件：
    1. `windows` 為空陣列 → 回傳 shape (n_rows, 0, N_STATS)
    2. `values` 全 NaN → 輸出全 NaN
    3. `values` 長度 < max(windows) → 部分 window 全 NaN
- **輸出**: `np.ndarray` shape (n_rows, n_windows, N_STATS)
- **禁止事項**: 不可在 Numba JIT 內呼叫 Python 函式（包括 logger）

#### Task 3.2: 整合到 `_compute_all_streaming_numba()`

- **目標**: 修改 RollingAggregator 呼叫邏輯，改用 multi-window kernel
- **修改檔案**: `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_compute_all_streaming_numba()`
- **實作規格**:
  ```python
  # 現行（逐 window 呼叫）：
  for window in self._windows:          # 8 次外迴圈
      for start in chunk_starts:
          for col_idx, col_name in ...:
              fused = fused_rolling_stats(values, int(window))
  
  # 改為（multi-window 呼叫）：
  windows_array = np.array(self._windows, dtype=np.int32)
  for start in chunk_starts:
      for col_idx, col_name in ...:
          fused_all = fused_rolling_stats_multi_window(values, windows_array)
          for wi, window in enumerate(self._windows):
              fused = fused_all[:, wi, :]  # slice，無額外計算
  ```
  - 邊界條件：
    1. `FFACT_L3_MULTI_WINDOW=0` → 回到逐 window 呼叫（現有路徑）
    2. 單一 window 情境 → multi-window kernel 仍正確
- **輸出**: 與現行相同的 rolling 結果
- **禁止事項**: 不可移除現有的 per-window 路徑（保留作為 fallback）

#### Task 3.3: Batch Variance Filter — P2-B

- **目標**: 每個 window 的所有 agg 計算完畢後，做一次 batch variance filter 再寫入
- **修改檔案**: `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_compute_all_streaming_numba()`
- **實作規格**:
  ```python
  def _batch_variance_filter(
      self,
      window_results: Dict[str, np.ndarray],
      var_threshold: float = 0.0,
  ) -> Dict[str, np.ndarray]:
      """Filter out zero-variance columns from a batch of agg results for one window.
      
      Args:
          window_results: {agg_name: ndarray} for all aggs of a single window.
          var_threshold: Columns with variance <= threshold are dropped.
      
      Returns:
          Filtered dict with only non-zero-variance columns.
      """
      filtered = {}
      for agg_name, data in window_results.items():
          if np.nanvar(data) > var_threshold:
              filtered[agg_name] = data
      return filtered
  ```
  - 整合位置：在 `_compute_all_streaming_numba()` 的 per-window 迴圈尾部
  ```python
  # 現行：每個 (window, agg) step 各自寫入 + filter
  # 改為：
  for wi, window in enumerate(self._windows):
      window_results = {}
      for agg_name in agg_list:
          fused = fused_all[:, wi, :]
          window_results[agg_name] = extract_stat(fused, agg_name)
      
      # Batch filter + write
      filtered = self._batch_variance_filter(window_results)
      for agg_name, data in filtered.items():
          self._write_result(col_name, window, agg_name, data)
  ```
  - 效果：減少 memmap write 次數（80→8，按 window 分批）
  - 邊界條件：
    1. Variance filter 結果依賴 agg → 按 window 分批而非全部一次
    2. 空 batch（所有 aggs 被 filter 掉）→ 不寫入
    3. `var_threshold=0.0` → 只過濾完全零方差（常數列），與現有行為一致
- **輸出**: 與現行相同的 filter 結果，但寫入 I/O 減少
- **禁止事項**: 不可改變 variance filter 的判斷閾值或邏輯（只改批次化時機）

#### Task 3.4: TimeChunkIterator — P2-C（大資料集支援）— ⚠️ DEFERRED

> #### Task 3.4: TimeChunkIterator — ⚠️ DEFERRED to future version
>
> - **延後理由**: 目前資料集為 17,928 rows (1h)，不需要 time chunking。此功能針對 1min 大資料集（630K rows）
> - **觸發條件**: 當需要處理 1min timeframe 的資料集時
> - **若跳過的影響**: 1min 大資料集在 8GB 下可能 OOM。目前 use case 不涉及 1min。
> - **設計已完成**: 見 `OPTIMIZATION_TODO_PLANNING.md` §P2-C 的 `TimeChunkIterator` 規格

### 5.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T3.1 | `test_multi_window_matches_single_window` | multi-window 結果 == 逐 window 結果 | `np.allclose(atol=1e-4, equal_nan=True)` per stat | Task 3.1 |
| T3.2 | `test_multi_window_golden_equivalence` | multi-window pipeline → V7 golden 比對 | C1 全量比對通過 | Task 3.2 |
| T3.3 | `test_multi_window_nan_pattern_preserved` | NaN pattern 與 V7 完全一致 | C6 通過 | Task 3.1 |
| T3.4 | `test_batch_variance_filter_matches_per_step` | batch filter 結果 == per-step filter 結果 | 保留的 column set 一致 | Task 3.3 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T3.B1 | `test_multi_window_all_nan_input` | 輸入全 NaN | 輸出全 NaN |
| T3.B2 | `test_multi_window_constant_values` | 輸入單一常數值 | mean=val, std=0, skew=NaN, kurt=NaN |
| T3.B3 | `test_multi_window_single_window` | windows=[21] 單一 window | 結果與逐 window 一致 |
| T3.B4 | `test_multi_window_short_series` | n_rows=10, max_window=21 | 前 20 行 NaN |
| T3.B5 | `test_multi_window_extreme_values` | 含 1e30 和 1e-30 | 不 overflow/underflow |
| T3.B6 | `test_multi_window_all_windows` | 所有 9 個 window (5,8,13,21,34,55,89,144,233) 同時 | 全部正確 |
| T3.B7 | `test_multi_window_intermittent_nan` | [1, NaN, 3, NaN, 5, ...] | 跳過 NaN，min_periods 行為一致 |
| T3.B8 | `test_fallback_env_var` | `FFACT_L3_MULTI_WINDOW=0` | 走逐 window 舊路徑 |

#### 效能驗收測試

| ID | 測試名稱 | 驗收標準 |
|----|---------|---------|
| T3.P1 | `test_multi_window_speedup` | multi-window 比逐 window 快 ≥ 1.3× |
| T3.P2 | `test_multi_window_rss_stable` | RSS 增量 < 500 MB |

### 5.3 Phase 3 → Phase 4 Gate

- [ ] T3.1~T3.4 全部通過
- [ ] T3.B1~T3.B8 全部通過
- [ ] T3.P1 效能驗收通過（≥ 1.3× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L3_MULTI_WINDOW=0` fallback 正常

---

## 6. Phase 4 — L7 Parallel Parquet Writes + Async Compactor（P3）

> **目標**: ThreadPool 平行寫入 Parquet parts（max_group_split 已生效，可直接做），並以背景合併程序避免小檔案碎片化反噬 IOPS
> **預計效果**: L7 從 467s → ~150s (8GB/4w) / ~100s (24GB/8w)，且輸出檔案數維持在可接受範圍，避免後續 ML 讀取退化
> **風險**: 低到中（Parquet 寫入天然可平行；新增 compactor 需注意 manifest 與 crash recovery）

### 6.1 任務清單

#### Task 4.1: 實作 `_persist_parts_parallel()`

- **目標**: ThreadPool 平行寫入已分割的 Parquet parts
- **修改檔案**: `momentum/FeatureEngineering/feature_storage.py` → `persist_registry_to_parquet()`（或對應 persist 函式）
- **實作規格**:
  ```python
  from concurrent.futures import ThreadPoolExecutor
  
  def _persist_parts_parallel(
      self,
      parts_queue: List[Tuple[str, Any, Path, Path]],
      n_workers: int,
      compactor: Optional['AsyncParquetCompactor'] = None,
  ) -> List[str]:
      """Write prepared (part_id, table, final_path, staging_path) tuples in parallel.
      
      Uses atomic write (staging + os.replace) for crash safety.
      
      Args:
          parts_queue: List of (part_id, arrow_table, final_path, staging_path).
          n_workers: Number of parallel write threads.
          compactor: Optional background compactor. When present, worker threads
              write to staging and enqueue files for asynchronous merge/promotion.
      
      Returns:
          List of accepted part targets. When compactor is enabled, actual merged
          file paths are returned later by `compactor.finalize()`.
      """
      def _write_one(item: Tuple[str, Any, Path, Path]) -> str:
          part_id, table, final_path, staging_path = item
          pq.write_table(table, str(staging_path), compression="zstd")
          if compactor is not None:
              compactor.enqueue((part_id, staging_path))
          else:
              os.replace(str(staging_path), str(final_path))
          return str(final_path)
      
      with ThreadPoolExecutor(max_workers=n_workers) as pool:
          results = list(pool.map(_write_one, parts_queue))
      
      return results
  ```
  - Thread-safety 保證：
    - 每個 part 寫入獨立檔案，無共享狀態 ✅
        - 未啟用 compactor 時使用 `os.replace` 原子替換；啟用時由 compactor 負責最終 promotion ✅
    - staging_path 包含 part_id → 不會衝突 ✅
  - 邊界條件：
    1. `parts_queue` 為空 → 回傳空 list
    2. 某個 part 寫入失敗（磁碟滿）→ raise OSError，其他 parts 可能部分完成
    3. `n_workers=1` → 串行寫入（fallback）
- **輸出**: `List[str]`（已接受的 part 路徑/邏輯目標；若啟用 compactor，最終 merged 檔案由 `finalize()` 回傳）
- **禁止事項**: 不可修改 zstd compression level（維持 level=1 速度優先）

#### Task 4.2: 呼叫端整合 — 硬體自適應 workers

- **目標**: 在 persist 呼叫端根據 tier 選擇 workers
- **修改檔案**: `momentum/FeatureEngineering/feature_storage.py`（或呼叫端）
- **實作規格**:
  ```python
  from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config
  
  tier = get_memory_tier()
  tier_cfg = get_tier_config(tier)
  n_workers = int(os.getenv("FFACT_L7_WORKERS", str(tier_cfg["l7_workers"])))
  
  if n_workers > 1 and len(parts_queue) > 1:
      written = self._persist_parts_parallel(parts_queue, n_workers)
  else:
      written = [self._write_one(item) for item in parts_queue]  # 串行
  ```
  - 邊界條件：
    1. 只有 1 個 part → 不啟動 ThreadPool（開銷不值得）
    2. `FFACT_L7_WORKERS=1` → 強制串行
        3. **【新增】** 啟用 compactor 時，worker 僅保證 staging 寫入成功；最終檔案 promotion 由背景合併程序負責

#### Task 4.3: 實作 `AsyncParquetCompactor` — 【新增】盲點一 IOPS Bottleneck 緩解

- **目標**: 將 L7 Worker 先輸出到 staging 目錄，由背景執行緒批次合併小型 Parquet parts，抑制碎片化檔案數暴增
- **修改檔案**: `momentum/FeatureEngineering/feature_storage.py`（新增 `AsyncParquetCompactor` 與整合點）
- **實作規格**:
    ```python
    class AsyncParquetCompactor:
            """Background compactor for small parquet parts.

            Workers write small parts to a staging directory first. The compactor merges
            them into larger target files to reduce SSD IOPS pressure and downstream
            training read amplification.
            """

            def __init__(
                    self,
                    staging_dir: Path,
                    final_dir: Path,
                    target_rows: int = 100_000,
                    min_files_to_compact: int = 8,
            ) -> None:
                    ...

            def enqueue(self, item: Tuple[str, Path]) -> None:
                    ...

            def start(self) -> None:
                    ...

            def finalize(self) -> List[Path]:
                    """Drain queue, compact remaining files, and return merged outputs."""
                    ...
    ```
    - 背景流程：
        1. L7 worker 將 part 寫到 `staging_dir/part_*.parquet`
        2. worker 完成後呼叫 `compactor.enqueue((part_id, staging_path))`
        3. compactor 執行緒累積到 `min_files_to_compact` 或 `target_rows` 門檻後觸發 merge
        4. merge 後產出 `final_dir/merged_{index}.parquet`，並刪除已吸收的小檔
        5. pipeline 結束時呼叫 `compactor.finalize()`，清空佇列與剩餘 staging 檔
    - 整合方式：
        ```python
        compactor_enabled = os.getenv("FFACT_L7_COMPACTOR_ENABLED", "1") != "0"
        target_rows = int(os.getenv("FFACT_L7_COMPACTOR_TARGET_ROWS", "100000"))

        if compactor_enabled and chunk_bars is not None and max_group_columns <= 5_000:
                compactor = AsyncParquetCompactor(staging_dir, final_dir, target_rows=target_rows)
                compactor.start()
                written = self._persist_parts_parallel(parts_queue, n_workers, compactor=compactor)
                merged_files = compactor.finalize()
        else:
                written = self._persist_parts_parallel(parts_queue, n_workers)
        ```
    - **【新增】盲點一設計說明**：
        - 8GB tier 為了避免 OOM，`CHUNK_BARS=50_000` 且 `MAX_GROUP_COLUMNS=5_000` 會讓 part 數量顯著上升
        - 若直接將 1,000 個小檔寫到最終輸出目錄，CPU 完成後會卡在 SSD IOPS，且後續 ML 訓練讀取這些碎片檔案的延遲很高
        - Async compactor 的角色是把「寫入延遲」與「合併延遲」與主運算路徑解耦，讓 worker 專注於計算與初步落盤
    - 邊界條件：
        1. `FFACT_L7_COMPACTOR_ENABLED=0` → 完全回退到現行直接輸出模式
        2. `parts_queue` 很小（< `min_files_to_compact`）→ 直到 `finalize()` 才做最後合併
        3. merge 過程 crash → staging 目錄保留，下一次啟動可檢查/重跑，不覆寫既有 final 檔
        4. 單一 part 已超過 `target_rows` → 直接 promote 到 final_dir，不再二次合併
        5. 後續 ML 仍需 part-aware 讀取時 → 保留 `manifest.json` 記錄 merged 檔與原始來源對應
- **輸出**: 較少的大型 Parquet 檔案 + manifest
- **禁止事項**: 不可在主 worker thread 同步執行 merge（會把 IOPS 瓶頸重新拉回熱路徑）

### 6.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T4.1 | `test_parallel_persist_matches_serial` | 平行寫入的 Parquet == 串行寫入 | 檔案 binary 比對（排除 metadata timestamp） | Task 4.1 |
| T4.2 | `test_parallel_persist_atomic_write` | 寫入過程中 staging 檔存在，完成後只有 final 檔 | `final_path.exists() and not staging_path.exists()` | Task 4.1 |
| T4.3 | `test_tier_auto_selects_l7_workers` | 8GB tier → 4 workers | `n_workers == 4` | Task 4.2 |
| T4.4 | `test_async_compactor_merges_small_files_into_large_parts` | 多個 staging 小檔被合併 | final 檔案數 < staging 檔案數 | Task 4.3 |
| T4.5 | `test_async_compactor_manifest_tracks_sources` | merge 後 manifest 記錄來源檔案 | manifest 含 merged→source 對應 | Task 4.3 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T4.B1 | `test_parallel_persist_empty_queue` | 空 parts_queue | 回傳空 list |
| T4.B2 | `test_parallel_persist_single_part` | 只有 1 個 part | 串行寫入 |
| T4.B3 | `test_parallel_persist_disk_full` | mock disk full → OSError | raise OSError，不 silent fail |
| T4.B4 | `test_l7_workers_env_override` | `FFACT_L7_WORKERS=2` | 使用 2 workers |
| T4.B5 | `test_async_compactor_disabled_bypasses_merge` | `FFACT_L7_COMPACTOR_ENABLED=0` | 不建立 compactor，直接輸出小檔 |
| T4.B6 | `test_async_compactor_finalize_flushes_remaining_files` | 未達 batch 門檻即結束 | `finalize()` 後 staging 為空 |
| T4.B7 | `test_async_compactor_crash_preserves_staging_files` | merge 中途 raise OSError | staging 檔仍存在，final 不部分覆蓋 |

#### 效能驗收測試

| ID | 測試名稱 | 驗收標準 |
|----|---------|---------|
| T4.P1 | `test_l7_parallel_speedup` | 4 workers 比 1 worker 快 ≥ 2× |
| T4.P2 | `test_async_compactor_controls_file_explosion` | 8GB tier 小檔數被壓到原始 staging 檔數的 ≤ 25% |

### 6.3 Phase 4 → Phase 5 Gate

- [ ] T4.1~T4.5 全部通過
- [ ] T4.B1~T4.B7 全部通過
- [ ] T4.P1~T4.P2 效能驗收通過
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L7_COMPACTOR_ENABLED=0` fallback 正常

---

## 7. Phase 5 — 硬體資訊 API + 前端顯示

> **目標**: 提供 REST API endpoint 暴露硬體資訊和建議設定，前端顯示系統資源面板
> **預計效果**: V2 Chat / V3 Agent 可自動讀取 `memory_tier` 並配置最佳參數
> **風險**: 低（獨立功能，不影響核心 pipeline）

### 7.1 任務清單

#### Task 5.1: 後端 — `GET /config/hardware` endpoint

- **目標**: 新增 API endpoint 回傳硬體資訊、memory tier、建議設定
- **修改檔案**: `api/routes/config.py`（新增 endpoint）
- **實作規格**:
  ```python
  @router.get("/hardware")
  async def get_hardware_info() -> Dict[str, Any]:
      """Returns hardware info, memory tier, and recommended settings."""
      import shutil
      import psutil
      from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config
  
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
      tier_config = get_tier_config(tier)
      
      return {
          "memory_tier": tier,
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
              "FFACT_L65_WORKERS":       tier_config["l65_workers"],
              "FFACT_CGSA_MEMORY_BUFFER": tier_config["cgsa_memory_buffer"],
              "FFACT_L7_WORKERS":        tier_config["l7_workers"],
              "FFACT_L7_COMPACTOR_ENABLED": 1,
          },
      }
  ```
  - 邊界條件：
    1. `data_cache/` 不存在 → disk info 全為 0
    2. psutil 不可用 → 回傳 fallback 值
- **輸出**: JSON response
- **禁止事項**: 不可暴露敏感資訊（API keys, file paths outside data_cache）

#### Task 5.2: 前端 — `HardwareStatusPanel.tsx`

- **目標**: 建立系統資源顯示面板，嵌入 Feature Factory 頁面
- **修改檔案**: `frontend/src/components/feature-factory/HardwareStatusPanel.tsx`（**新增**）
- **實作規格**:
  - UI Layout:
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
  - 顏色邏輯：
    - RAM 可用 ≥ 2 GB → 綠色（正常）
    - RAM 可用 1-2 GB → 黃色（注意）
    - RAM 可用 < 1 GB → 紅色（OOM 風險）
    - 磁碟可用 < 10 GB → 黃色
    - 磁碟可用 < 5 GB → 紅色
  - API 呼叫：`GET /api/v1/config/hardware`
  - 手動重新整理按鈕（不自動輪詢，避免持續 CPU 採樣開銷）
  - 邊界條件：
    1. API 無回應 → 顯示 "無法取得系統資訊" 錯誤狀態
    2. Loading 狀態 → skeleton/spinner
- **輸出**: React 元件
- **禁止事項**: 不可自動輪詢（使用者手動觸發刷新）

#### Task 5.3: 前端 — 嵌入 Feature Factory 頁面

- **目標**: 將 HardwareStatusPanel 嵌入 Feature Factory 頁面
- **修改檔案**: `frontend/src/app/feature-factory/page.tsx`（或對應 layout）
- **實作規格**:
  - 放置位置：頁面頂部或側邊欄，不遮擋主要功能
  - 可折疊（預設展開）
  - 邊界條件：
    1. 未登入 / API 不可用 → 面板隱藏或顯示最小化狀態

### 7.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T5.1 | `test_hardware_endpoint_returns_valid_json` | endpoint 回傳正確 JSON 結構 | 包含 memory_tier, cpu, memory, disk, recommended_settings | Task 5.1 |
| T5.2 | `test_hardware_endpoint_tier_matches_util` | endpoint tier == `get_memory_tier()` | 一致 | Task 5.1 |
| T5.3 | `test_hardware_panel_renders_without_crash` | React 元件正常渲染 | 無 console error | Task 5.2 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T5.B1 | `test_hardware_endpoint_missing_data_cache` | `data_cache/` 不存在 | disk info 全為 0 |
| T5.B2 | `test_hardware_panel_api_error` | API 回傳 500 | 顯示錯誤狀態 |

---

## 8. Phase Gate 決策矩陣

| Gate | 條件 | 通過 → | 失敗 → |
|------|------|--------|--------|
| Phase 0 → 1 | T0.x 全通過 + 無 api import | Phase 1 | 修正 Phase 0 |
| Phase 1 → 2 | T1.x 全通過 + Resume 場景驗證 | Phase 2 | 修正 Phase 1 |
| Phase 2 → 3 | T2.x 全通過 + C1~C6 + ≥2× speedup | Phase 3 | 修正 Phase 2 |
| Phase 3 → 4 | T3.x 全通過 + C1~C6 + ≥1.3× speedup | Phase 4 | 修正 Phase 3 |
| Phase 4 → 5 | T4.x 全通過 + C1~C6 + 小檔數受控 | Phase 5 | 修正 Phase 4 |
| Phase 5 → Done | T5.x 全通過 + API 可用 | ✅ 完成 | 修正 Phase 5 |

---

## 9. 全局測試策略

### 9.1 測試層級

| 層級 | 範圍 | 執行頻率 | 工具 |
|------|------|---------|------|
| 單元測試 | 單一函式 | 每 Task | pytest |
| 整合測試 | 跨模組 | 每 Phase | pytest |
| 效能測試 | 端到端 | 每 Phase Gate | 自定義 benchmark |
| 回歸測試 | Golden 比對 | 每 Phase | pytest + golden files |

### 9.2 測試檔案結構

```
tests/
├── test_hardware_utils.py                # Phase 0 — T0.1~T0.4, T0.B1~T0.B3
├── test_cgsa_resume.py                   # Phase 1 — T1.1~T1.4, T1.B1~T1.B5
├── test_l65_parallel.py                  # Phase 2 — T2.1~T2.5, T2.B1~T2.B6
├── test_multi_window_rolling.py          # Phase 3 — T3.1~T3.4, T3.B1~T3.B8
├── test_l7_parallel_persist.py           # Phase 4 — T4.1~T4.5, T4.B1~T4.B7
├── test_hardware_api.py                  # Phase 5 — T5.1~T5.3, T5.B1~T5.B2
├── performance/
│   ├── test_l65_parallel_perf.py         # T2.P1~T2.P2
│   ├── test_multi_window_perf.py         # T3.P1~T3.P2
│   └── test_l7_persist_perf.py           # T4.P1~T4.P2
```

### 9.3 測試 ID 統計

| Phase | 核心 | 邊界 | 效能 | 小計 |
|-------|------|------|------|------|
| Phase 0 | 4 | 3 | 0 | **7** |
| Phase 1 | 4 | 5 | 0 | **9** |
| Phase 2 | 6 | 7 | 2 | **15** |
| Phase 3 | 4 | 8 | 2 | **14** |
| Phase 4 | 5 | 7 | 2 | **14** |
| Phase 5 | 3 | 2 | 0 | **5** |
| **總計** | **26** | **32** | **6** | **64** |

### 9.4 合成資料生成器（共用 Fixture）

```python
# conftest.py
import numpy as np
import pytest

@pytest.fixture
def sample_feature_array():
    """產生合成 feature 陣列 (1000 rows × 50 cols) for testing."""
    rng = np.random.RandomState(42)
    data = rng.randn(1000, 50).astype(np.float32)
    # Add NaN pattern
    for j in range(50):
        nan_len = rng.randint(0, 200)
        data[:nan_len, j] = np.nan
    return data

@pytest.fixture
def mock_column_group_registry(tmp_path):
    """產生 mock ColumnGroupRegistry for parallel transform testing."""
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    # ... setup mock groups ...
    return registry
```

---

## 10. 風險登記簿

| ID | 風險描述 | 影響 | 機率 | 緩解措施 | 影響 Task |
|----|---------|------|------|---------|----------|
| R1 | `hardware_utils.py` import `api/` 模組 | 違反解耦規則 R1 | 低 | Pre-Commit 檢查 `grep -r "from api." momentum/` | Task 0.1 |
| R2 | manifest.json 損壞導致 resume 失敗 | Pipeline 無法啟動 | 中 | Task 1.3 容錯處理 → fallback 建新 Registry | Task 1.3 |
| R3 | ThreadPool L6.5 並發導致 race condition | 結果不正確 | 低 | 各 group 完全獨立 + 原子寫入；`FFACT_L65_WORKERS=1` fallback | Task 2.1 |
| R4 | Numba multi-window kernel 數值不穩定（skew/kurt） | C1 fail（atol=1e-4） | 中 | float64 累加器 + 定期校正 + T3.B2 全常數邊界測試 | Task 3.1 |
| R5 | Numba ARM64/macOS JIT 相容性 | Phase 3 compile error 或數值錯誤 | 低 | 版本釘選 `numba>=0.57,<0.60`；開發機全量測試 | Task 3.1 |
| R6 | L7 parallel write 磁碟空間不足 | 部分 parts 寫入成功，部分失敗 | 低 | atomic write (staging + replace)；失敗時 raise OSError | Task 4.1 |
| R7 | CGSA In-Memory Buffer 中途崩潰遺失 data | 需要 resume 重算被遺失的 groups | 低 | 可接受 trade-off（resume 會重算）；8/16GB 不啟用 buffer | Task 2.4 |
| R8 | Polars API 跨版本 breaking changes（若實作 Task 2.5） | Polars 升級後程式碼失效 | 中 | Task 2.5 已 DEFERRED；版本釘選 | Task 2.5 |
| R9 | 前端 API 不可用導致 HardwareStatusPanel 白屏 | 使用者體驗差 | 低 | Error boundary + fallback 錯誤訊息 | Task 5.2 |
| R10 | psutil 不可用（極少見的環境） | `get_memory_tier()` 無法偵測 | 極低 | fallback 為 "8gb" 最保守 tier | Task 0.1 |
| R11 | **【新增】** 8GB tier 因小 chunk + 小 group 導致 Parquet 檔案碎片化，SSD IOPS 反成新瓶頸 | L7 寫入與後續 ML 讀取雙重退化 | 中 | Task 4.3 背景 compactor + `FFACT_L7_COMPACTOR_ENABLED=0` fallback + T4.P2 檔案數上限驗證 | Task 4.3 |
| R12 | **【新增】** L6.5 group 成本差異極大，若按原始順序提交會出現長尾效應 | Phase 2 speedup 不達標，CPU 閒置 | 中 | Task 2.1 依 `n_columns` 降序貪婪排程 + T2.6 驗證最大 group 優先 | Task 2.1 |
| R13 | **【新增】** Numba JIT 在多進程冷啟動時同時編譯，造成 CPU/RAM 突波並可能 OOM | Phase 2/未來跨 Symbol 平行化啟動時崩潰 | 中 | Task 2.3 主進程 warmup + `cache=True` 磁碟快取 + T2.B7 驗證 warmup 順序 | Task 2.3 |

---

## 附錄 A: 效能預估對照表

| 項目 | V7 現況 (8GB) | 8GB 目標 | 24GB 目標 | 32GB 目標 |
|------|-------------|---------|---------|---------|
| Resume fix（崩潰場景） | 重跑 2,424s | resume 剩餘 | resume 剩餘 | resume 剩餘 |
| P0-A L6.5 parallel | 2,424s | ~606s (×4) | ~303s (×8) | ~303s (×8) |
| P0-B CGSA buffer | 2,055s (L2†) | 不變 | ~1,300s | ~1,000s |
| P2-A multi-window kernel | 2,051s (L3) | ~1,400s | ~800s | ~400s |
| P3 L7 parallel | 467s | ~150s | ~100s | ~80s |
| P3-B Async compactor | 724 files | ~150-250 files | ~80-160 files | ~40-120 files |
| **合計（8GB ×4）** | **7,756s** | **~5,300s** | **—** | **—** |
| **合計（24GB ×8）** | **7,756s** | **—** | **~3,500s** | **—** |
| **合計（32GB）** | **7,756s** | **—** | **—** | **~2,000s** |

### 三大瓶頸（V7 時間佔比）

> † **P0-B 說明**: CGSA buffer 減少 L2 derived features 產生過程中的 `.npy` 寫入 I/O。L2 的 2,055s 中有顯著比例為 disk I/O（每個 column group 都寫 .npy），buffer 將 708 次寫入減為 ~22 次（buffer=32）。

```
L2 (Derived)        ████████████████████████████  27.8%  (2,055s)
L3 (Rolling)        ████████████████████████████  27.8%  (2,051s)
L6.5 (Preprocess)   █████████████████████████████████  32.8%  (2,424s)
L7 (Persist)        ██████  6.3%  (467s)
Other               █████  5.3%  (390s)
```

---

## 附錄 B: 參考文件

| 文件 | 用途 |
|------|------|
| `docs/OPTIMIZATION_TODO_PLANNING.md` (v3) | 本 SPEC 的規劃來源 |
| `Pre-opt_vs_V7_Comparison.md` | V7 Baseline 效能數據、瓶頸分析 |
| `docs/FEATURE_FACTORY_OPTIMIZATION_SPEC.md` | V7 前期優化 SPEC（參考範本） |
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | L6.5 主要修改檔 |
| `momentum/FeatureEngineering/operators/numba_rolling.py` | L3 Numba kernel |
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | L3 orchestrator |
| `momentum/FeatureEngineering/feature_factory.py` | Pipeline 主檔、CGSA 整合 |
| `momentum/FeatureEngineering/feature_storage.py` | L7 persist |
| `momentum/FeatureEngineering/core/column_group_registry.py` | CGSA Registry |
| `api/routes/config.py` | 硬體資訊 API |

---

## 附錄 C: AI Agent 執行清單

```
Phase 0: (硬體偵測基礎建設)
  □ 0.1  建立 hardware_utils.py (get_memory_tier)
  □ 0.2  建立 tier config 常數 (get_tier_config)
  □      跑 T0.1~T0.4, T0.B1~T0.B3
  □      Gate: hardware_utils.py 無 api import

Phase 1: (Resume 啟用)
  □ 1.1  修正 _prepare_cgsa_registry 決定性路徑
  □ 1.2  呼叫端補傳 config_hash
  □ 1.3  處理損壞的 manifest.json
  □      跑 T1.1~T1.4, T1.B1~T1.B5
  □      Gate: Resume 場景驗證 + C1 等價

Phase 2: (L6.5 平行化 — 最高 ROI)
  □ 2.1  實作 _transform_registry_parallel (ThreadPool)
    □      【新增】依 n_columns 降序做貪婪排程，避免長尾效應
  □ 2.2  呼叫端整合 (tier auto-select workers)
  □ 2.3  Numba warmup 確保 JIT 完成
    □      【新增】驗證主進程 warmup + cache=True 可覆蓋未來 ProcessPool 路徑
  □ 2.4  CGSA In-Memory Buffer (24/32GB)
  □ 2.5  ⚠️ DEFERRED: Polars Wide Matrix (32GB)
    □      跑 T2.1~T2.6, T2.B1~T2.B7, T2.P1~T2.P2
  □      Gate: ≥2× speedup + C1~C6

Phase 3: (L3 Multi-Window Kernel)
  □ 3.1  實作 fused_rolling_stats_multi_window
  □ 3.2  整合到 _compute_all_streaming_numba
  □ 3.3  Batch variance filter
  □ 3.4  ⚠️ DEFERRED: TimeChunkIterator
  □      跑 T3.1~T3.4, T3.B1~T3.B8, T3.P1~T3.P2
  □      Gate: ≥1.3× speedup + C1~C6

Phase 4: (L7 Parallel Persist + Async Compactor)
  □ 4.1  實作 _persist_parts_parallel
  □ 4.2  呼叫端整合 (tier auto-select workers)
    □ 4.3  【新增】實作 AsyncParquetCompactor，背景合併碎片化小檔
    □      跑 T4.1~T4.5, T4.B1~T4.B7, T4.P1~T4.P2
    □      Gate: ≥2× speedup + 小檔數受控 + C1~C6

Phase 5: (硬體資訊 API + 前端)
  □ 5.1  GET /config/hardware endpoint
  □ 5.2  HardwareStatusPanel.tsx
  □ 5.3  嵌入 Feature Factory 頁面
  □      跑 T5.1~T5.3, T5.B1~T5.B2
  □      Gate: API 正常 + 前端渲染
```

---

## 附錄 D: 環境變數 / Feature Flag 彙整

| 變數名 | 預設值 | 作用 | 引入 Phase |
|--------|-------|------|-----------|
| `FFACT_MEMORY_TIER` | `auto` | 覆蓋自動偵測的硬體層級 | Phase 0 |
| `FFACT_CGSA_WORK_DIR` | `""` | 覆蓋 CGSA 工作目錄 | Phase 1（既有） |
| `FFACT_L65_WORKERS` | tier-dependent (4/6/8/8) | L6.5 平行 workers 數 | Phase 2 |
| `FFACT_CGSA_MEMORY_BUFFER` | tier-dependent (0/0/32/64) | CGSA In-Memory Buffer groups 數 | Phase 2 |
| `FFACT_L3_MULTI_WINDOW` | `1` | 啟用 multi-window fused kernel | Phase 3 |
| `FFACT_L7_WORKERS` | tier-dependent (4/6/8/8) | L7 平行 persist workers 數 | Phase 4 |
| `FFACT_L7_COMPACTOR_ENABLED` | `1` | 啟用背景 Parquet 合併程序 | Phase 4 |
| `FFACT_L7_COMPACTOR_TARGET_ROWS` | `100000` | 每個 merged parquet 目標列數 | Phase 4 |
| `FFACT_L65_POLARS` | `auto` | 啟用 Polars wide matrix (32GB only) | DEFERRED |

---

## 附錄 E: 關鍵常數

```python
# 已確認的 V7 數字
MAX_GROUP_COLUMNS    = 5_000    # L7 自動分割閾值（已生效）
MAX_L65_GROUP_COLS   = 16_110   # L2_Momentum（最大群組，RAM 限制因子）
L65_GROUP_COUNT      = 708      # V7 baseline
L65_AVG_S_PER_GROUP  = 3.42    # V7 profiling 測量值
L65_TOTAL_SECONDS    = 2_424    # V7 baseline
L7_TOTAL_SECONDS     = 467      # V7 baseline
CGSA_WORK_DIR_BASE   = "data_cache/cgsa_work"

# 硬體層級預設值
_WORKERS_BY_TIER     = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
_CGSA_BUFFER_BY_TIER = {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}
_L7_WORKERS_BY_TIER  = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
_CHUNK_BARS_BY_TIER  = {"8gb": 50_000, "16gb": 100_000, "24gb": 250_000, "32gb": None}
```

---

## SPEC 結構自檢清單

### ID 體系（Stage 0.5 必檢 — 6/6 = 跳過正規化）

- [x] 每個 Task 有唯一 ID（格式: `Task N.M`）
- [x] 每個測試有唯一 ID（格式: `TN.M` / `TN.BM` / `TN.PM`）
- [x] 每個風險有唯一 ID（格式: `RN`）
- [x] 每個 Phase 有明確標題和編號
- [x] 每個 Phase 有 Gate 條件
- [x] Task 明確標注修改檔案（含 `.py` / `.tsx` 等副檔名路徑）

### 內容深度（TODO §2.2 深度要求）

- [x] 每個 Task 有實作規格（含函式簽名或偽碼）
- [x] 每個 Task 標注修改檔案到函式名層級
- [x] 每個 Task 有 ≥ 2 個邊界條件處理
- [x] 每個測試有具體通過條件（數值 / 命令 / 斷言）
- [x] 硬約束有量化驗收條件

### 結構完整性

- [x] DEFERRED Task 有延後理由和觸發條件（Task 2.5, Task 3.4）
- [x] Golden/Baseline 定義完整
- [x] 環境變數/Feature Flag 有彙整表（附錄 D）
- [x] 風險登記簿中每個 Risk 至少被一個 Task 引用
- [x] 無散文式需求（所有需求已結構化為 Task）
- [x] 明確排除項目已列出（§1.5 Out of Scope）
- [x] Thread-safety 與 buffer 並發問題已處理（Task 2.1 + Task 2.4 _buffer_lock）
- [x] 所有 tier 查表使用 `get_tier_config()`（無直接 `_PRIVATE[tier]` 存取）
- [x] `finalize()` 呼叫位置已明確標註（Task 2.4）
- [x] 向後相容表涵蓋所有 Phase（§0.8）
