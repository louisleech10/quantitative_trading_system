# Feature Factory V8 效能優化 TODO
> **版本**: V1
> **狀態**: DRAFT
> **基於 SPEC**: Feature Factory V8 效能優化規劃書（SPEC）V1 (2026-04-20 FROZEN)
> **生成日期**: 2026-04-21

---

## 0. 全域規則與約束（從 SPEC §0 + §1 提取）

> 本節確保執行 Agent 不需回頭讀 SPEC 就能遵守所有規則。

### 0.1 必遵開發規則

#### 規則 A: 解耦架構（7 規則） — 影響全部 Task

所有新增/修改的程式碼必須通過以下 7 項檢查，違反任一項即**不可合併**：

| 規則 | 說明 | 驗證方式 |
|------|------|----------|
| R1 | `momentum/` 不可 import `api/` | `grep -r "from api\." momentum/` → 0 結果 |
| R2 | 跨 Domain 使用 Protocol 注入 | `from momentum.core.protocols import I*` |
| R3 | `api/services/` 透過 `momentum/factories.py` 建立物件 | 不可直接 `Engine()` |
| R4 | Service 之間不互相 import | 無 `from api.services.other import` |
| R5 | Config 單一來源 | Domain → `momentum/core/config.py`；API → `api/core/config.py` |
| R6 | 測試設定隔離 | 測試可獨立執行，不依賴 `run_api.py` |
| R7 | DTO 不跨域 | `api/models/` 與 `momentum/core/contracts.py` 無相互相依 |

**具體影響**：
- `hardware_utils.py` 位於 `momentum/FeatureEngineering/utils/`（R1 — 不可 import api/）→ 影響 Task 0.1, 0.2
- `GET /config/hardware` endpoint 在 `api/routes/config.py`（R3）→ 影響 Task 5.1
- 前端 `HardwareStatusPanel.tsx` 獨立元件 → 影響 Task 5.2

#### 規則 B: Logging 規範 — 影響 Task 2.1, 2.4, 3.2, 4.1

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

**具體影響**：
- Task 2.1: ThreadPool 完成後 log 摘要 `logger.info("[L6.5] Parallel complete: %d groups in %.2fs, %d workers", ...)`
- Task 3.1: Numba JIT 內部**不可 log**（Numba 不支援 Python 呼叫）
- Task 4.1: parallel writes 完成後 log `logger.info("[L7] Parallel persist: %d parts in %.2fs", ...)`

#### 規則 C: Error Handling 模式 — 影響 Task 1.3, 2.1, 2.4, 4.1

```python
from enum import Enum

class FailureType(Enum):
    IO_ERROR = "io_error"          # .npy / Parquet 寫入失敗 → retryable
    OOM = "oom"                     # 記憶體不足 → 不 retry，降級處理
    VALIDATION = "validation"       # 數值驗證失敗 → 不 retry，回退
    CONFIG = "config"               # 設定錯誤 → 不 retry，修正 config
```

#### 規則 D: 命名規範 — 影響全部 Task

| 類型 | 規則 | 範例 |
|------|------|------|
| 函式 | snake_case，動詞開頭 | `get_memory_tier()`, `transform_registry_parallel()` |
| 類別 | PascalCase | `TimeChunkIterator`, `HardwareStatusPanel` |
| 常數 | UPPER_SNAKE_CASE | `TIER_THRESHOLDS`, `_WORKERS_BY_TIER` |
| 變數 | snake_case，語義清楚 | `memory_tier`, `n_workers`, `chunk_bars` |
| 禁止 | — | `df1`, `temp`, `x`, `data2`, `result_new` |

#### 規則 E: Type Hints — 影響全部 Task

所有新增函式必須有完整 type annotations：

```python
# ✅ 正確
def get_memory_tier() -> str: ...
def transform_registry_groups(self, registry: 'ColumnGroupRegistry', n_workers: int = 1) -> int: ...

# ❌ 禁止
def get_memory_tier(): ...
```

#### 規則 F: 效能程式碼慣例 — 影響 Task 2.1, 3.1, 3.3, 4.1

優先順序（從快到慢）：
1. 向量化 numpy/pandas
2. `@numba.njit(cache=True)` — 必須用 `cache=True`
3. `ThreadPoolExecutor` (I/O bound) / `ProcessPoolExecutor` (CPU bound)
4. Python loop（最後手段）

#### 規則 G: 向後相容 — 影響 Task 2.1, 2.2, 3.2, 4.2

| Phase | Fallback 機制 | 環境變數 |
|-------|--------------|---------|
| Phase 2 | L6.5 串行路徑 | `FFACT_L65_WORKERS=1` |
| Phase 3 | 現有 per-window kernel | `FFACT_L3_MULTI_WINDOW=0` |
| Phase 4 | L7 串行 writes | `FFACT_L7_WORKERS=1` |
| Phase 0/1/5 | 無需 fallback（純增 / 純修正 / 獨立新功能） | — |

#### 規則 H: 測試規範 — 影響全部 Test

```python
# 測試函式名稱：test_{功能}_{場景}
# 必須有中文 docstring
# 使用 pytest fixture 管理共用狀態
# 路徑：tests/test_{module_name}.py | tests/performance/test_{module}_perf.py
# 測試可獨立執行（Rule 6），不需啟動 API server
```

### 0.2 硬約束與驗收標準

| ID | 約束 | 驗收條件 | 驗證方式 |
|----|------|---------|----------|
| C1 | **數值等價**：優化後 pipeline 輸出與 V7 Baseline 完全一致 | 全欄位 `np.allclose(atol=1e-4, equal_nan=True)` | Golden output test suite |
| C2 | **不減特徵**：feature_count = 435,389（ETHUSDT 2TF） | `assert new_count == 435_389` | Pipeline 輸出比對 |
| C3 | **不改 column name**：欄位名稱集合完全一致 | `assert set(new_cols) == set(golden_cols)` | Column set 比對 |
| C4 | **RAM 峰值 ≤ 6 GB**（8GB 機器留 2GB 給 OS） | `psutil.Process().memory_info().rss < 6 * 1024**3` | RSS 監控 |
| C5 | **無 future leakage**：align 後 12h 特徵不超前 primary 1h | `validate_no_future_leak()` PASS | 現有驗證函式 |
| C6 | **NaN 語義一致**：rolling window 開頭的 NaN pattern 完全相同 | per-column NaN mask comparison | `np.array_equal(nan_mask_new, nan_mask_golden)` |
| C7 | **硬體自適應**：所有優化自動偵測硬體 tier 並啟用最佳路徑 | 4 tier 路徑均可執行 | `FFACT_MEMORY_TIER={8gb,16gb,24gb,32gb}` 各跑一次 |

### 0.3 每 Phase 通用驗收流程

```
1. 建立 git branch: perf/v8-phase-{N}-{description}
2. 完成目標修改
3. 執行 golden output comparison（C1~C3, C6）
4. 執行 future leak test（C5）
5. 記錄 RSS 峰值（C4）
6. 記錄 wall-clock time（各 layer 分別計時）
7. 全部 PASS → 合併到 main；任一 FAIL → 回退到 branch 起點，定位問題
```

**回退策略**：
- 每個 Phase 都在獨立 branch 上開發
- 失敗時 `git stash` → `git checkout main` → 分析 → 重試
- 連續失敗 3 次以上 → 重新評估技術方案

**Golden Baseline 定義**：
- Symbol: ETHUSDT
- Timeframes: primary=1h, training=[1h, 12h]
- Config: `scan_config.yaml` 預設（全開 L1~L6, L6.5 ON）
- Baseline: V7 完整輸出（7,756s, 435,389 features, 724 files）
- 儲存位置: `data_cache/features/` 下的 V7 輸出
- 比對精度: `atol=1e-4`

### 0.4 Pre-Commit Checklist（每個 Task 完成後）

```
□ Ultra Think 3 步完成（生成 → 自審 → 優化）
□ grep -r "from api\." momentum/ → 0 結果（R1）
□ 無 hardcoded data（Data Truth Principle）
□ 所有函式有 type hints
□ Error handling 使用 FailureType 分類（涉及 I/O 時）
□ Logging 符合 §0.2 規範（不在 hot loop 中 log）
□ 命名符合 §0.4 規範
□ 測試有中文 docstring
□ 測試可獨立執行（無需 run_api.py）
□ .npy / .parquet 不在 git track 中
□ 效能程式碼已向量化（§0.7）
□ Fallback env var 可切回舊行為（§0.8）
□ ruff check momentum/ → 0 error
□ smoke test：pytest tests/ -m "not slow" -x -q → 0 error
```

### 0.5 全域前置條件

- [ ] Python 3.11+ 環境已啟用（`source venv/bin/activate`）
- [ ] `pip install psutil numba` 確保 psutil 和 numba 可用
- [ ] `data_cache/features/` 下有 V7 golden baseline 輸出（ETHUSDT, 2TF）
- [ ] `scan_config.yaml` 為 V7 預設設定（全開 L1~L6, L6.5 ON）
- [ ] Git branch 已建立：`git checkout -b perf/v8-feature-factory-optimization`

---

## 執行策略（最少批次計劃）

> **目的**: 將所有 Task 依據依賴拓撲分組為最少的執行批次（Batch）。
> 每個 Batch = 一次 Agent prompt。Batch 內的 Task 互不依賴，可合併執行。

### 依賴拓撲總覽

```
Batch 1: [Phase 0 + Phase 1] ──── 無前置依賴
  Task 0.1, 0.2 (hardware_utils.py — 新增)
  Task 1.1, 1.2, 1.3 (CGSA resume — 修改 feature_factory.py)
  （Phase 0 和 Phase 1 修改不同檔案，無互依賴）
    │
    ▼ Gate: T0.x + T1.x 全通過，hardware_utils 無 api import
Batch 2: [Phase 2] ──── 依賴 Batch 1（hardware_utils + CGSA registry）
  Task 2.1, 2.2, 2.3, 2.4
    │
    ▼ Gate: T2.x 全通過，C1~C6，≥2× speedup
Batch 3: [Phase 3] ──── 依賴 Batch 2 Gate（L6.5 必須正確後才改 L3）
  Task 3.1, 3.2, 3.3
    │
    ▼ Gate: T3.x 全通過，C1~C6，≥1.3× speedup
Batch 4: [Phase 4] ──── 依賴 Batch 3 Gate
  Task 4.1, 4.2
    │
    ▼ Gate: T4.x 全通過，C1~C6，≥2× speedup
Batch 5: [Phase 5] ──── 依賴 Batch 4 Gate + Phase 0（hardware_utils）
  Task 5.1, 5.2, 5.3
    │
    ▼ Gate: T5.x 全通過，API + 前端可用
```

### 批次明細

| Batch | 包含項目 | 依賴前置 | 合併理由 | 預估規模 |
|-------|---------|---------|---------|----------|
| 1 | Phase 0 (Task 0.1, 0.2) + Phase 1 (Task 1.1, 1.2, 1.3) | — | 修改不同檔案（新增 hardware_utils vs 修改 feature_factory），無互依賴 | 中（5 Task，但邏輯簡單） |
| 2 | Phase 2 (Task 2.1, 2.2, 2.3, 2.4) | Batch 1 | 依賴 hardware_utils (Task 0.1) + CGSA registry 修改 (Task 1.x) | 中（4 Task，涉及 ThreadPool 並發核心邏輯） |
| 3 | Phase 3 (Task 3.1, 3.2, 3.3) | Batch 2 | 依賴 Phase 2 Gate 通過（確認 L6.5 正確後才改 L3） | 中（3 Task，涉及 Numba JIT 核心邏輯） |
| 4 | Phase 4 (Task 4.1, 4.2) | Batch 3 | 依賴 Phase 3 Gate 通過 | 小（2 Task，邏輯與 Phase 2 類似） |
| 5 | Phase 5 (Task 5.1, 5.2, 5.3) | Batch 4 | 依賴 hardware_utils + 所有核心 Phase 完成 | 中（3 Task，跨前後端） |

### 批次間 Gate 檢查

| 轉換 | 必須通過的驗證 | 驗證命令 |
|------|-------------|----------|
| Batch 1 → 2 | T0.1~T0.4, T0.B1~T0.B3, T1.1~T1.4, T1.B1~T1.B5 + `grep -r "from api\." momentum/` = 0 | `./venv/bin/pytest tests/test_hardware_utils.py tests/test_cgsa_resume.py -v && grep -r "from api\." momentum/ \| wc -l` |
| Batch 2 → 3 | T2.1~T2.5, T2.B1~T2.B6, T2.P1~T2.P2 + C1~C6 全量比對 + `FFACT_L65_WORKERS=1` fallback | `./venv/bin/pytest tests/test_l65_parallel.py tests/performance/test_l65_parallel_perf.py -v` |
| Batch 3 → 4 | T3.1~T3.4, T3.B1~T3.B8, T3.P1~T3.P2 + C1~C6 + `FFACT_L3_MULTI_WINDOW=0` fallback | `./venv/bin/pytest tests/test_multi_window_rolling.py tests/performance/test_multi_window_perf.py -v` |
| Batch 4 → 5 | T4.1~T4.3, T4.B1~T4.B4, T4.P1 + C1~C6 | `./venv/bin/pytest tests/test_l7_parallel_persist.py tests/performance/test_l7_persist_perf.py -v` |
| Batch 5 → Done | T5.1~T5.3, T5.B1~T5.B2 + API 回傳正確 JSON | `./venv/bin/pytest tests/test_hardware_api.py -v` |

### 快速執行參考（複製貼上用）

**Batch 1**:
```
請執行以下 Task：Phase 0 全域前置 + Task 0.1 + Task 0.2 + Task 1.1 + Task 1.2 + Task 1.3
完成後執行驗證：
  ./venv/bin/pytest tests/test_hardware_utils.py tests/test_cgsa_resume.py -v
  grep -r "from api\." momentum/ | wc -l  # 必須為 0
```

**Batch 2**:
```
前置已完成：Batch 1（Phase 0 + Phase 1 全部 Task + Gate 通過）
請執行：Task 2.1 + Task 2.2 + Task 2.3 + Task 2.4
完成後執行驗證：
  ./venv/bin/pytest tests/test_l65_parallel.py tests/performance/test_l65_parallel_perf.py -v
  FFACT_L65_WORKERS=1 ./venv/bin/pytest tests/test_l65_parallel.py -v  # fallback 驗證
```

**Batch 3**:
```
前置已完成：Batch 1-2（Phase 0-2 全部 Task + Gate 通過）
請執行：Task 3.1 + Task 3.2 + Task 3.3
完成後執行驗證：
  ./venv/bin/pytest tests/test_multi_window_rolling.py tests/performance/test_multi_window_perf.py -v
  FFACT_L3_MULTI_WINDOW=0 ./venv/bin/pytest tests/test_multi_window_rolling.py -v  # fallback
```

**Batch 4**:
```
前置已完成：Batch 1-3（Phase 0-3 全部 Task + Gate 通過）
請執行：Task 4.1 + Task 4.2
完成後執行驗證：
  ./venv/bin/pytest tests/test_l7_parallel_persist.py tests/performance/test_l7_persist_perf.py -v
  FFACT_L7_WORKERS=1 ./venv/bin/pytest tests/test_l7_parallel_persist.py -v  # fallback
```

**Batch 5**:
```
前置已完成：Batch 1-4（Phase 0-4 全部 Task + Gate 通過）
請執行：Task 5.1 + Task 5.2 + Task 5.3
完成後執行驗證：
  ./venv/bin/pytest tests/test_hardware_api.py -v
  curl http://localhost:8000/api/v1/config/hardware | python -m json.tool  # 手動檢查
```

---

## Phase 0 — 硬體偵測基礎建設

### Phase 0 目標與驗收標準
> 建立 `get_memory_tier()` 硬體自動偵測框架 + `get_tier_config()` 參數查表，作為所有後續優化的前置依賴。完成後系統能自動偵測 8/16/24/32 GB 記憶體層級並回傳對應最佳設定。零效能影響。

### Task 0.1 — 建立 `hardware_utils.py`（get_memory_tier）
- [x] **SPEC ref**: Task 0.1, §2.1
- [ ] **目標**: 實作記憶體層級自動偵測函式，支援環境變數覆蓋
- [ ] **輸入**: 無（讀取 `psutil.virtual_memory().total` 和 `os.getenv("FFACT_MEMORY_TIER")`）
- [ ] **輸出**: `str`（`"8gb"` | `"16gb"` | `"24gb"` | `"32gb"`）
- [ ] **實作要點**:
  - 新建檔案 `momentum/FeatureEngineering/utils/hardware_utils.py` 及 `__init__.py`
  - 定義常數 `TIER_THRESHOLDS: List[Tuple[int, str]]`：
    ```python
    TIER_THRESHOLDS = [(28, "32gb"), (20, "24gb"), (12, "16gb"), (0, "8gb")]
    ```
  - 實作 `get_memory_tier() -> str`：
    ```
    1. 讀取 env = os.getenv("FFACT_MEMORY_TIER", "auto").strip().lower()
    2. if env != "auto" and env != "" → return env（原值回傳，不做驗證）
    3. try: total_gb = psutil.virtual_memory().total / 1024**3
       except → return "8gb"（fallback）
    4. 遍歷 TIER_THRESHOLDS，回傳第一個 total_gb >= threshold 的 tier
    5. 無匹配 → return "8gb"
    ```
  - Edge case 處理：
    - `FFACT_MEMORY_TIER="64gb"`（無效值）→ 原值回傳，由呼叫端負責驗證
    - `FFACT_MEMORY_TIER="auto"` → 走 psutil 偵測
    - `FFACT_MEMORY_TIER=""` → 走 psutil 偵測
    - `psutil` import 失敗 → fallback 為 `"8gb"`
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/utils/__init__.py`（**新增**，空檔案）
  - `momentum/FeatureEngineering/utils/hardware_utils.py`（**新增**）→ `get_memory_tier()`, `TIER_THRESHOLDS`
- [ ] **不可做**:
  - 不可 import `api/` 任何模組（R1）
  - 不可加入 logging（此為純工具函式，無副作用）
  - 不可在此函式內加入 config file 讀取邏輯（保持純函式）
- [ ] **風險緩解**: R1（解耦）, R10（psutil 不可用）
- [ ] **驗證**: T0.1, T0.2, T0.B1, T0.B2, T0.B3

### Task 0.2 — 建立各層級功能矩陣常數（get_tier_config）
- [x] **SPEC ref**: Task 0.2, §2.1
- [ ] **目標**: 定義各 tier 對應的 workers、buffer 等參數常數，提供統一查表函式
- [ ] **輸入**: `tier: str`（由 `get_memory_tier()` 回傳）
- [ ] **輸出**: `Dict[str, Any]`，keys: `l65_workers`, `cgsa_memory_buffer`, `l7_workers`, `chunk_bars`
- [ ] **實作要點**:
  - 在 `hardware_utils.py` 內新增 module-level 常數（以 `_` 開頭表示 private）：
    ```python
    _WORKERS_BY_TIER: Dict[str, int] = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
    _CGSA_BUFFER_BY_TIER: Dict[str, int] = {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}
    _L7_WORKERS_BY_TIER: Dict[str, int] = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
    _CHUNK_BARS_BY_TIER: Dict[str, Optional[int]] = {"8gb": 50_000, "16gb": 100_000, "24gb": 250_000, "32gb": None}
    ```
  - 實作 `get_tier_config(tier: str) -> Dict[str, Any]`：
    ```
    1. 從各 dict 取值，使用 .get(tier, 預設值) 確保未知 tier 有 fallback
    2. 預設值為 8gb 的值（最保守）
    3. 回傳 dict 包含 4 個 key
    ```
  - Edge case 處理：
    - 未知 tier 字串（如 `"64gb"`）→ 回傳 8gb 的保守值
    - 所有回傳值必須為安全預設值（不會導致 OOM）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/utils/hardware_utils.py` → `get_tier_config()`, `_WORKERS_BY_TIER`, `_CGSA_BUFFER_BY_TIER`, `_L7_WORKERS_BY_TIER`, `_CHUNK_BARS_BY_TIER`
- [ ] **不可做**:
  - 不可有任何副作用（純查表函式）
  - 不可直接暴露 `_PRIVATE` dict 給外部（只透過 `get_tier_config` 存取）
- [ ] **風險緩解**: R1（解耦）
- [ ] **驗證**: T0.3, T0.4

### Phase 0 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T0.1 | `test_get_memory_tier_auto_detection` | psutil 回傳值對應正確 tier | 8GB M1 → `"8gb"` | §2.2 |
| ☐ | T0.2 | `test_get_memory_tier_env_override` | `FFACT_MEMORY_TIER=16gb` → `"16gb"` | 環境變數覆蓋生效 | §2.2 |
| ☐ | T0.3 | `test_get_tier_config_returns_valid_dict` | 所有 4 個 tier 回傳的 dict 包含必要 keys | keys = {l65_workers, cgsa_memory_buffer, l7_workers, chunk_bars} | §2.2 |
| ☐ | T0.4 | `test_get_tier_config_unknown_tier_fallback` | 未知 tier → 回傳 8gb 值 | `l65_workers == 4` | §2.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T0.B1 | `test_get_memory_tier_env_auto` | `FFACT_MEMORY_TIER=auto` | 走 psutil 偵測路徑 | §2.2 |
| ☐ | T0.B2 | `test_get_memory_tier_env_empty` | `FFACT_MEMORY_TIER=""` | 走 psutil 偵測路徑 | §2.2 |
| ☐ | T0.B3 | `test_get_memory_tier_psutil_unavailable` | mock psutil 失敗 | 回傳 `"8gb"` | §2.2 |

#### 測試檔案：`tests/test_hardware_utils.py`

### Phase 0 → Phase 1 Gate
- [ ] T0.1~T0.4 全部通過
- [ ] T0.B1~T0.B3 全部通過
- [ ] `grep -r "from api\." momentum/FeatureEngineering/utils/` → 0 結果

---

## Phase 1 — Resume 啟用 + CGSA 修正

### Phase 1 目標與驗收標準
> 啟用已實作但未被 production 呼叫的 `resume_from_manifest()` 功能，修改 CGSA work_dir 為決定性路徑，增加 manifest 損壞容錯。完成後崩潰場景可 resume 剩餘部分（而非重跑全部 2,424s）；正常執行無效能影響。

### Task 1.1 — 修正 `_prepare_cgsa_registry()` 使用決定性路徑
- [x] **SPEC ref**: Task 1.1, §3.1
- [ ] **目標**: 將 `tempfile.mkdtemp()` 隨機路徑改為基於 symbol/timeframe/config_hash 的決定性路徑
- [ ] **輸入**: `symbol: str`, `timeframe: str`, `config_hash: str = ""`
- [ ] **輸出**: `Optional[ColumnGroupRegistry]`
- [ ] **實作要點**:
  - 修改 `_prepare_cgsa_registry()` 簽名，新增 `config_hash: str = ""` 參數
  - 路徑生成邏輯（取代 `tempfile.mkdtemp()`）：
    ```python
    safe_symbol = re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol)
    safe_tf = re.sub(r"[^A-Za-z0-9_.-]+", "_", timeframe)
    hash_prefix = config_hash[:8] if config_hash else "nohash"
    work_dir = Path("data_cache/cgsa_work") / f"{safe_symbol}_{safe_tf}_{hash_prefix}"
    work_dir.mkdir(parents=True, exist_ok=True)
    ```
  - 保留 `FFACT_CGSA_WORK_DIR` 環境變數覆蓋（最高優先）
  - 如果 `manifest.json` 存在 → 呼叫 `ColumnGroupRegistry.resume_from_manifest(work_dir)` 以 resume
  - 如果不存在 → `ColumnGroupRegistry(work_dir=work_dir)` 新建
  - Edge case 處理：
    - `config_hash=""` → 使用 `"nohash"` prefix
    - `symbol="BTC/USDT:PERP"`（含特殊字元）→ `re.sub` 清理為 `BTC_USDT_PERP`
    - manifest.json 存在但損壞 → 交由 Task 1.3 處理
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`（修改簽名+路徑邏輯）
- [ ] **不可做**:
  - 不可刪除 `FFACT_CGSA_WORK_DIR` 環境變數路徑（保留作為手動覆蓋）
  - 不可修改 `ColumnGroupRegistry` 的 `__init__` 或 `resume_from_manifest` 簽名
- [ ] **風險緩解**: R2（manifest 損壞）
- [ ] **驗證**: T1.1, T1.2, T1.B1, T1.B2, T1.B3

### Task 1.2 — 呼叫端補傳 `config_hash` 參數
- [x] **SPEC ref**: Task 1.2, §3.1
- [ ] **目標**: 在 `feature_factory.py` 呼叫 `_prepare_cgsa_registry` 處補傳 `config_hash`
- [ ] **輸入**: 當前 scope 中的 `config_hash` 值
- [ ] **輸出**: 無（修改呼叫簽名）
- [ ] **實作要點**:
  - 定位呼叫處：`feature_factory.py` 約 L135
    ```python
    # 現行：
    self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe)
    # 改為：
    self._cgsa_registry = self._prepare_cgsa_registry(symbol, timeframe, config_hash)
    ```
  - 確認 `config_hash` 在呼叫處已可用（通常從 `self._config` 或 pipeline 參數計算）
  - 如果 `config_hash` 不在當前 scope → 追蹤其來源，確認傳入正確值
  - Edge case 處理：
    - `config_hash` 為 None → 轉為空字串 `""`（防禦性 programming）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → 呼叫端（~L135 附近）
- [ ] **不可做**:
  - 不可在此步驟改動 `resume_from_manifest()` 的邏輯
  - 不可修改 config_hash 的計算方式
- [ ] **驗證**: T1.3

### Task 1.3 — 處理損壞的 manifest.json
- [x] **SPEC ref**: Task 1.3, §3.1
- [ ] **目標**: 增加 resume 時的容錯處理，manifest 損壞時 fallback 到新 Registry
- [ ] **輸入**: 已存在的 manifest.json（可能損壞）
- [ ] **輸出**: 容錯 fallback 到新 `ColumnGroupRegistry`
- [ ] **實作要點**:
  - 在 `_prepare_cgsa_registry()` 的 resume 路徑加入 try/except：
    ```python
    if manifest_path.exists():
        try:
            logger.info("[CGSA] Resuming from manifest at %s", work_dir)
            return ColumnGroupRegistry.resume_from_manifest(work_dir)
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning("[CGSA] Corrupt manifest at %s: %s, starting fresh", work_dir, e)
            # 不刪除 manifest，讓使用者可以手動檢查
    ```
  - Edge case 處理：
    - manifest.json 為空檔案 → `json.JSONDecodeError` → 建新 Registry
    - manifest.json 缺少必要 key → `KeyError` → 建新 Registry
    - manifest 記錄的 .npy 檔案不存在 → `ColumnGroupRegistry.resume_from_manifest` 內部處理（若該函式 raise OSError → 被此處 catch）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`（增加 try/except）
- [ ] **不可做**:
  - 不可自動刪除損壞的 manifest（保留供人工檢查）
  - 不可 catch bare `Exception`（只 catch 預期的 3 種）
- [ ] **風險緩解**: R2（manifest 損壞不再導致 pipeline 失敗）
- [ ] **驗證**: T1.4, T1.B4, T1.B5

### Phase 1 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T1.1 | `test_cgsa_deterministic_path` | 相同 symbol/tf/hash → 相同路徑 | 兩次呼叫回傳相同 work_dir | §3.2 |
| ☐ | T1.2 | `test_cgsa_resume_from_existing_manifest` | manifest 存在時 resume 而非新建 | `resume_from_manifest` 被呼叫（mock 驗證） | §3.2 |
| ☐ | T1.3 | `test_cgsa_config_hash_passed_correctly` | config_hash 從呼叫端正確傳入 | work_dir 路徑含 hash prefix（前 8 字元） | §3.2 |
| ☐ | T1.4 | `test_cgsa_corrupt_manifest_fallback` | 損壞 manifest → 建新 Registry | 不 raise exception，回傳有效 Registry | §3.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T1.B1 | `test_cgsa_empty_config_hash` | `config_hash=""` | work_dir 含 `"nohash"` | §3.2 |
| ☐ | T1.B2 | `test_cgsa_special_chars_in_symbol` | `symbol="BTC/USDT:PERP"` | 清理為 `BTC_USDT_PERP` | §3.2 |
| ☐ | T1.B3 | `test_cgsa_work_dir_env_override` | `FFACT_CGSA_WORK_DIR=/tmp/test` | 使用環境變數路徑（不走決定性路徑） | §3.2 |
| ☐ | T1.B4 | `test_cgsa_empty_manifest_json` | manifest.json 內容為 `""` | `JSONDecodeError` → 建新 Registry | §3.2 |
| ☐ | T1.B5 | `test_cgsa_missing_npy_files_in_manifest` | manifest 記錄的 .npy 不存在 | 跳過該 group（不 crash），或建新 Registry | §3.2 |

#### 測試檔案：`tests/test_cgsa_resume.py`

### Phase 1 → Phase 2 Gate
- [ ] T1.1~T1.4 全部通過
- [ ] T1.B1~T1.B5 全部通過
- [ ] 正常執行的 pipeline 輸出與 V7 Baseline 數值等價（C1）
- [ ] Resume 場景：手動殺掉 L6.5 中間 → 重跑 → 從中斷點繼續

---

## Phase 2 — L6.5 Preprocessing 平行化（P0）

### Phase 2 目標與驗收標準
> 將 L6.5 `transform_registry_groups()` 從串行改為 ThreadPool 平行，支援 CGSA In-Memory Buffer（24/32GB tier）。完成後 L6.5 從 2,424s → ~606s (8GB/4w) / ~404s (16GB/6w) / ~303s (24GB/8w)。**最高 ROI 項目**。

### Task 2.1 — 實作 `_transform_registry_parallel()` — P0-A ThreadPool
- [x] **SPEC ref**: Task 2.1, §4.1
- [ ] **目標**: 新增 ThreadPoolExecutor 平行路徑，保留串行路徑作為 fallback
- [ ] **輸入**: `registry: ColumnGroupRegistry`, `n_workers: int`
- [ ] **輸出**: `int`（成功 transform 的 group 數）
- [ ] **實作要點**:
  - 修改 `transform_registry_groups()` 簽名，新增 `n_workers: int = 1` 參數
  - `n_workers > 1` → 走 `_transform_registry_parallel()`；`n_workers <= 1` → 走現有串行路徑（重命名為 `_transform_registry_serial()`）
  - 平行路徑實作偽碼：
    ```python
    def _transform_registry_parallel(self, registry, n_workers):
        groups = registry.list_all_groups()  # 取得所有 group 列表
        completed, failed = 0, 0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {pool.submit(self._transform_single_group, registry, g): g for g in groups}
            for future in as_completed(futures):
                try:
                    future.result()
                    completed += 1
                except Exception as e:
                    failed += 1
                    logger.error("[L6.5] Failed group %s: %s", futures[future].group_id, e, exc_info=True)
        elapsed = time.perf_counter() - t0
        logger.info("[L6.5] Parallel complete: %d/%d in %.2fs (%d failed), %d workers",
                    completed, len(groups), elapsed, failed, n_workers)
        return completed
    ```
  - Thread-safety 保證：
    - `overwrite_data()` 使用原子寫入（temp + `os.replace`）→ thread-safe ✅
    - `load_data(mmap_mode="r")` → 多執行緒讀取安全 ✅
    - 各 group 完全獨立，無共享可變狀態 ✅
  - Edge case 處理：
    - `n_workers=0` → 等同 `n_workers=1`，串行執行
    - groups 為空列表 → 直接回傳 0
    - 某個 group transform 失敗 → log error，繼續其他 groups，最終回傳 completed < total
  - ⚠️ 矛盾注意：若 CGSA buffer > 0（24/32GB），`save_data()` 經由 `_buffer_lock` 保護（見 Task 2.4）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `transform_registry_groups()`（修改簽名）, `_transform_registry_parallel()`（新增）, `_transform_registry_serial()`（重命名現有邏輯）
- [ ] **不可做**:
  - 不可使用 ProcessPoolExecutor（L6.5 內無 TA-Lib GIL 問題，ThreadPool 足夠且開銷小）
  - 不可移除串行路徑（`n_workers=1` 必須走串行）
  - 不可在 `_transform_single_group` 內部 log 每個 group（在 hot loop 中）
- [ ] **風險緩解**: R3（ThreadPool 並發 race condition — 靠獨立 group + 原子寫入緩解）
- [ ] **驗證**: T2.1, T2.2, T2.B1, T2.B2, T2.B3, T2.B4

### Task 2.2 — 呼叫端整合 — 硬體自適應 workers
- [x] **SPEC ref**: Task 2.2, §4.1
- [ ] **目標**: 在呼叫端根據 `get_memory_tier()` 自動選擇 workers 數
- [ ] **輸入**: 無（讀取 tier + env var）
- [ ] **輸出**: 無（修改呼叫邏輯）
- [ ] **實作要點**:
  - 在 L6.5 呼叫端（`feature_factory.py` 或 `feature_factory_service.py`）整合：
    ```python
    from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config
    
    tier = get_memory_tier()
    tier_cfg = get_tier_config(tier)
    n_workers = int(os.getenv("FFACT_L65_WORKERS", str(tier_cfg["l65_workers"])))
    buffer_groups = int(os.getenv("FFACT_CGSA_MEMORY_BUFFER", str(tier_cfg["cgsa_memory_buffer"])))
    
    # 傳入 registry 和 preprocessor
    preprocessor.transform_registry_groups(registry, n_workers=n_workers)
    ```
  - Edge case 處理：
    - `FFACT_L65_WORKERS=1` → 強制串行（完整 fallback）
    - `FFACT_L65_WORKERS=0` → 等同 1（串行）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py`（或 `api/services/feature_factory_service.py`，視呼叫位置）→ L6.5 呼叫點
- [ ] **不可做**:
  - 不可 hardcode workers 數（必須從 tier config 讀取）
- [ ] **風險緩解**: R3（workers=1 即為完整 fallback）
- [ ] **驗證**: T2.3

### Task 2.3 — Numba warmup 確保 JIT 完成
- [x] **SPEC ref**: Task 2.3, §4.1
- [ ] **目標**: 主執行緒先 warmup Numba JIT，再啟動 ThreadPool（避免多緒同時觸發 JIT 編譯）
- [ ] **輸入**: 無
- [ ] **輸出**: 無（副作用：Numba functions 已 JIT 編譯完成）
- [ ] **實作要點**:
  - 新增 `_warmup_numba_if_needed(self) -> None`：
    ```python
    def _warmup_numba_if_needed(self) -> None:
        if not hasattr(self, '_numba_warmed_up'):
            try:
                from momentum.FeatureEngineering.operators.numba_rolling import warmup_numba
                warmup_numba()  # 觸發 JIT 編譯
                self._numba_warmed_up = True
            except ImportError:
                self._numba_warmed_up = True  # No numba to warm up
    ```
  - 在 `_transform_registry_parallel()` **開頭**呼叫此函式
  - Edge case 處理：
    - Numba 未安裝 → `ImportError` → skip warmup
    - 多次呼叫 → 只 warmup 一次（`_numba_warmed_up` flag）
    - `warmup_numba()` 不存在 → 需先確認 `numba_rolling.py` 是否有此函式，若無則新增一個小型 warmup 函式
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_warmup_numba_if_needed()`（新增）
- [ ] **不可做**:
  - 不可在 warmup 中執行耗時操作（只做最小必要的 JIT 觸發）
- [ ] **驗證**: 透過 T2.1 隱含驗證（平行路徑不會因 JIT race 而 crash）

### Task 2.4 — CGSA In-Memory Buffer — P0-B（24/32GB tier）
- [x] **SPEC ref**: Task 2.4, §4.1
- [ ] **目標**: 24/32GB tier 緩衝多個 group 的 .npy 陣列，批次寫入減少 disk I/O
- [ ] **輸入**: `memory_buffer_groups: int`（0=立即 flush, N=緩衝 N 個 group）
- [ ] **輸出**: 減少 disk writes（708 次 → ~22 次 at buffer=32）
- [ ] **實作要點**:
  - 修改 `ColumnGroupRegistry.__init__()` 新增 `memory_buffer_groups: int = 0` 參數
  - 新增 instance 變數：
    ```python
    self._memory_buffer: Dict[str, np.ndarray] = {}
    self._memory_buffer_limit = memory_buffer_groups
    self._buffer_lock = threading.Lock()  # Thread-safe for Task 2.1 ThreadPool
    ```
  - ⚠️ **SPEC vs 程式碼差異**: SPEC 偽碼寫 `save_data(self, group_id: str, data)` 但實際簽名為 `save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup`。實作時需使用 `group.group_id` 作為 buffer key，不可改變現有簽名。
  - 修改 `save_data()` 邏輯（在現有 `np.save` 前加入 buffer 判斷）：
    ```python
    if self._memory_buffer_limit > 0:
        with self._buffer_lock:
            self._memory_buffer[group.group_id] = data
            if len(self._memory_buffer) >= self._memory_buffer_limit:
                self._flush_buffer()
    else:
        # 現有路徑（buffer=0），無需 lock
        np.save(path, data_fp32, allow_pickle=False)  # 維持現有邏輯
    ```
  - 新增 `_flush_buffer(self) -> None` 和 `finalize(self) -> None`：
    ```python
    def _flush_buffer(self) -> None:
        """Batch write. Caller must hold _buffer_lock."""
        for group_id, data in self._memory_buffer.items():
            path = self._work_dir / f"{group_id}.npy"
            np.save(path, np.asarray(data, dtype=np.float32), allow_pickle=False)
        self._memory_buffer.clear()
    
    def finalize(self) -> None:
        """Flush remaining buffer on pipeline completion."""
        with self._buffer_lock:
            if self._memory_buffer:
                self._flush_buffer()
    ```
  - **呼叫端整合**：在 `feature_factory.py` 的 L6.5 transform 完成後呼叫 `registry.finalize()`
  - Edge case 處理：
    - buffer=0（8/16GB）→ 完全向後相容，現有行為不變，無 lock 開銷
    - Pipeline 中途崩潰 → buffer 中的 data 遺失（可接受，resume 會重算）
    - `finalize()` 必須在 pipeline 結束時呼叫
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/core/column_group_registry.py` → `__init__()`（加參數）, `save_data()`（加 buffer 邏輯）, `_flush_buffer()`（新增）, `finalize()`（新增）
  - `momentum/FeatureEngineering/feature_factory.py` → L6.5 完成後呼叫 `registry.finalize()`
- [ ] **不可做**:
  - 不可在 8/16GB tier 啟用 buffer（記憶體不足）
  - 不可改變 `save_data()` 的外部簽名（`group: ColumnGroup, data: np.ndarray`）
  - 不可在 `_flush_buffer()` 外部直接操作 `_memory_buffer`
- [ ] **風險緩解**: R7（buffer 崩潰遺失 — 接受 trade-off）
- [ ] **驗證**: T2.4, T2.5, T2.B5, T2.B6

### Phase 2 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T2.1 | `test_parallel_transform_matches_serial` | 4 workers 結果 == 1 worker 結果 | `np.allclose(atol=1e-4, equal_nan=True)` | §4.2 |
| ☐ | T2.2 | `test_parallel_transform_all_groups_complete` | 所有 groups 均被處理 | `completed == len(groups)` | §4.2 |
| ☐ | T2.3 | `test_tier_auto_selects_workers` | 8GB tier → 4 workers | `n_workers == 4` | §4.2 |
| ☐ | T2.4 | `test_cgsa_buffer_batch_write` | buffer=4 時每 4 groups 才 flush | mock `np.save` 呼叫次數（⚠️ SPEC 原文為 `_write_npy`；因實作無獨立 helper，改 mock `np.save`） | §4.2 |
| ☐ | T2.5 | `test_cgsa_buffer_finalize_flushes_remaining` | finalize 清空剩餘 buffer | `len(registry._memory_buffer) == 0` | §4.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T2.B1 | `test_parallel_zero_groups` | 空 groups 列表 | 回傳 0，不 crash | §4.2 |
| ☐ | T2.B2 | `test_parallel_single_group` | 只有 1 個 group | 正常處理 | §4.2 |
| ☐ | T2.B3 | `test_parallel_one_group_fails` | 1 個 group raise Exception | 其他 groups 不受影響，completed < total | §4.2 |
| ☐ | T2.B4 | `test_parallel_workers_1_is_serial` | n_workers=1 | 走串行路徑 `_transform_registry_serial` | §4.2 |
| ☐ | T2.B5 | `test_cgsa_buffer_zero_is_immediate_flush` | buffer=0 | 每次 save 立即 write（現有行為） | §4.2 |
| ☐ | T2.B6 | `test_cgsa_buffer_crash_loses_unflushed` | buffer=4, 存 2 個後模擬 crash | 只有 0 個寫入 disk（未 flush） | §4.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☐ | T2.P1 | `test_l65_parallel_4workers_speedup` | 4 workers 比 1 worker 快 ≥ 2× | §4.2 |
| ☐ | T2.P2 | `test_l65_parallel_rss_under_limit` | RSS 增量 < 1 GB（vs serial baseline） | §4.2 |

#### 測試檔案：`tests/test_l65_parallel.py` + `tests/performance/test_l65_parallel_perf.py`

### Phase 2 → Phase 3 Gate
- [ ] T2.1~T2.5 全部通過
- [ ] T2.B1~T2.B6 全部通過
- [ ] T2.P1 效能驗收通過（≥ 2× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L65_WORKERS=1` fallback 正常

---

## Phase 3 — L3 Rolling Aggregation 優化（P2）

### Phase 3 目標與驗收標準
> 擴展 Numba kernel 為多 window 版本，每個 column 讀取 1 次（vs 現行 8 次），加上 batch variance filter 減少 memmap writes。完成後 L3 從 2,051s → ~1,400s (8GB)。

### Task 3.1 — 實作 `fused_rolling_stats_multi_window()` — P2-A Multi-Window Fused Kernel
- [x] **SPEC ref**: Task 3.1, §5.1
- [ ] **目標**: 每個 column 只讀取 1 次，同時計算所有 windows 的 rolling stats
- [ ] **輸入**: `values: np.ndarray` shape (n_rows,), `windows: np.ndarray` shape (n_windows,) int32
- [ ] **輸出**: `np.ndarray` shape (n_rows, n_windows, N_STATS)，internal float64
- [ ] **實作要點**:
  - 新增函式於 `numba_rolling.py`：
    ```python
    @numba.njit(parallel=True, cache=True)
    def fused_rolling_stats_multi_window(values, windows):
        n_rows = len(values)
        n_windows = len(windows)
        N_STATS = 10  # mean, std, min, max, range, zscore, skew, kurt, rank, slope
        out = np.full((n_rows, n_windows, N_STATS), np.nan, dtype=np.float64)
        for wi in numba.prange(n_windows):
            w = windows[wi]
            # Per-window rolling 邏輯（reuse Welford + monotonic deque pattern from fused_rolling_stats）
            # 額外計算 skew, kurt, rank, slope（目前不在 fused_rolling_stats 中）
        return out
    ```
  - ⚠️ **注意**: 現有 `fused_rolling_stats` 只計算 6 項（mean/std/min/max/range/zscore），不含 skew/kurt/rank/slope。Multi-window 版需整合：
    - skew: 第三中心矩 / std³（可用 Welford 擴展到 m3）
    - kurt: 第四中心矩 / std⁴（Welford 擴展到 m4）
    - rank: 從現有 `rolling_rank()` 邏輯移植（sorted buffer + bisect）
    - slope: 線性回歸斜率（x=0..w-1, y=values）
  - `numba.prange` 平行化在 window 維度（非 column 維度）→ 避免 data race
  - 內部 float64 累加器 → 輸出 float64 → 呼叫端轉 float32
  - 維持現有 `fused_rolling_stats()` 作為 fallback（`FFACT_L3_MULTI_WINDOW=0`）
  - Edge case 處理：
    - `windows` 為空陣列 → 回傳 shape (n_rows, 0, N_STATS)
    - `values` 全 NaN → 輸出全 NaN
    - `values` 長度 < max(windows) → 部分 window 全 NaN
    - 含 1e30 和 1e-30 → 不 overflow/underflow（float64 累加器保護）
    - 單一常數值 → mean=val, std=0, skew=NaN, kurt=NaN, rank=0.5, slope=0
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/operators/numba_rolling.py` → `fused_rolling_stats_multi_window()`（新增）
- [ ] **不可做**:
  - 不可在 Numba JIT 內呼叫 Python 函式（包括 logger、print）
  - 不可刪除現有 `fused_rolling_stats()`（保留作為 fallback）
  - 不可使用 `parallel=True` 和 `prange` 在 column 維度（data race 風險）
- [ ] **風險緩解**: R4（數值穩定性 — float64 累加器 + T3.B2 全常數測試）, R5（Numba ARM64 相容性）
- [ ] **驗證**: T3.1, T3.3, T3.B1~T3.B7

### Task 3.2 — 整合到 `_compute_all_streaming_numba()`
- [x] **SPEC ref**: Task 3.2, §5.1
- [ ] **目標**: 修改 RollingAggregator 呼叫邏輯，改用 multi-window kernel
- [ ] **輸入**: 環境變數 `FFACT_L3_MULTI_WINDOW`（預設 `"1"` 啟用）
- [ ] **輸出**: 與現行相同的 rolling 結果（column name、NaN pattern 完全一致）
- [ ] **實作要點**:
  - 在 `_compute_all_streaming_numba()` 開頭檢查 feature flag：
    ```python
    use_multi_window = os.getenv("FFACT_L3_MULTI_WINDOW", "1").strip() != "0"
    ```
  - 啟用時改用 multi-window 呼叫：
    ```python
    # 現行（逐 window）：
    for window in self._windows:
        for col_idx, col_name in ...:
            fused = fused_rolling_stats(values, int(window))
    
    # 改為（multi-window）：
    windows_array = np.array(self._windows, dtype=np.int32)
    for col_idx, col_name in ...:
        fused_all = fused_rolling_stats_multi_window(values, windows_array)
        for wi, window in enumerate(self._windows):
            fused = fused_all[:, wi, :]  # slice 無額外計算
    ```
  - Edge case 處理：
    - `FFACT_L3_MULTI_WINDOW=0` → 回到逐 window 呼叫（現有路徑完全不變）
    - 單一 window 情境 → multi-window kernel 仍正確
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_compute_all_streaming_numba()`
- [ ] **不可做**:
  - 不可移除現有 per-window 路徑（保留作為 `FFACT_L3_MULTI_WINDOW=0` fallback）
  - 不可改變輸出 column name 的命名規則
- [ ] **驗證**: T3.2, T3.B8

### Task 3.3 — Batch Variance Filter — P2-B
- [x] **SPEC ref**: Task 3.3, §5.1
- [ ] **目標**: 每個 window 的所有 agg 計算完畢後，做一次 batch variance filter 再寫入（減少 memmap writes）
- [ ] **輸入**: `window_results: Dict[str, np.ndarray]`（某 window 的所有 agg 結果）
- [ ] **輸出**: 過濾後的 dict（只含非零方差 columns），與現行 filter 結果一致
- [ ] **實作要點**:
  - 新增 `_batch_variance_filter()` 方法：
    ```python
    def _batch_variance_filter(self, window_results: Dict[str, np.ndarray], var_threshold: float = 0.0) -> Dict[str, np.ndarray]:
        filtered = {}
        for agg_name, data in window_results.items():
            if np.nanvar(data) > var_threshold:
                filtered[agg_name] = data
        return filtered
    ```
  - 在 `_compute_all_streaming_numba()` 的 per-window 迴圈尾部整合：
    ```python
    for wi, window in enumerate(self._windows):
        window_results = {}
        for agg_name in agg_list:
            window_results[agg_name] = extract_stat(fused_all[:, wi, :], agg_name)
        filtered = self._batch_variance_filter(window_results)
        for agg_name, data in filtered.items():
            self._write_result(col_name, window, agg_name, data)
    ```
  - 效果：減少 memmap write 次數（80 → 8，按 window 分批）
  - Edge case 處理：
    - 空 batch（所有 aggs 被 filter 掉）→ 不寫入，不 crash
    - `var_threshold=0.0` → 只過濾完全零方差（常數列），與現有行為一致
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_batch_variance_filter()`（新增）, `_compute_all_streaming_numba()`（修改 write 時機）
- [ ] **不可做**:
  - 不可改變 variance filter 的判斷閾值或邏輯（只改批次化時機）
  - 不可在 filter 前改變 data 的值
- [ ] **驗證**: T3.4

### Phase 3 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T3.1 | `test_multi_window_matches_single_window` | multi-window 結果 == 逐 window 結果 | `np.allclose(atol=1e-4, equal_nan=True)` per stat | §5.2 |
| ☐ | T3.2 | `test_multi_window_golden_equivalence` | multi-window pipeline → V7 golden 比對 | C1 全量比對通過 | §5.2 |
| ☐ | T3.3 | `test_multi_window_nan_pattern_preserved` | NaN pattern 與 V7 完全一致 | C6: `np.array_equal(nan_mask_new, nan_mask_golden)` | §5.2 |
| ☐ | T3.4 | `test_batch_variance_filter_matches_per_step` | batch filter 結果 == per-step filter 結果 | 保留的 column set 一致 | §5.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T3.B1 | `test_multi_window_all_nan_input` | 輸入全 NaN | 輸出全 NaN | §5.2 |
| ☐ | T3.B2 | `test_multi_window_constant_values` | 輸入單一常數值 | mean=val, std=0, skew=NaN, kurt=NaN | §5.2 |
| ☐ | T3.B3 | `test_multi_window_single_window` | windows=[21] 單一 window | 結果與逐 window 一致 | §5.2 |
| ☐ | T3.B4 | `test_multi_window_short_series` | n_rows=10, max_window=21 | 前 20 行 NaN | §5.2 |
| ☐ | T3.B5 | `test_multi_window_extreme_values` | 含 1e30 和 1e-30 | 不 overflow/underflow | §5.2 |
| ☐ | T3.B6 | `test_multi_window_all_windows` | 所有 9 個 window 同時 (5,8,13,21,34,55,89,144,233) | 全部正確 | §5.2 |
| ☐ | T3.B7 | `test_multi_window_intermittent_nan` | [1, NaN, 3, NaN, 5, ...] intermittent NaN | 跳過 NaN，min_periods 行為一致 | §5.2 |
| ☐ | T3.B8 | `test_fallback_env_var` | `FFACT_L3_MULTI_WINDOW=0` | 走逐 window 舊路徑，結果不變 | §5.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☐ | T3.P1 | `test_multi_window_speedup` | multi-window 比逐 window 快 ≥ 1.3× | §5.2 |
| ☐ | T3.P2 | `test_multi_window_rss_stable` | RSS 增量 < 500 MB | §5.2 |

#### 測試檔案：`tests/test_multi_window_rolling.py` + `tests/performance/test_multi_window_perf.py`

### Phase 3 → Phase 4 Gate
- [ ] T3.1~T3.4 全部通過
- [ ] T3.B1~T3.B8 全部通過
- [ ] T3.P1 效能驗收通過（≥ 1.3× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L3_MULTI_WINDOW=0` fallback 正常

---

## Phase 4 — L7 Parallel Parquet Writes（P3）

### Phase 4 目標與驗收標準
> ThreadPool 平行寫入 Parquet parts。完成後 L7 從 467s → ~150s (8GB/4w) / ~100s (24GB/8w)。

### Task 4.1 — 實作 `_persist_parts_parallel()`
- [x] **SPEC ref**: Task 4.1, §6.1
- [ ] **目標**: ThreadPool 平行寫入已分割的 Parquet parts
- [ ] **輸入**: `parts_queue: List[Tuple[str, Any, Path, Path]]`（part_id, arrow_table, final_path, staging_path）, `n_workers: int`
- [ ] **輸出**: `List[str]`（成功寫入的檔案路徑）
- [ ] **實作要點**:
  - 新增方法於 `feature_storage.py`：
    ```python
    def _persist_parts_parallel(self, parts_queue, n_workers):
        import pyarrow.parquet as pq
        
        def _write_one(item):
            part_id, table, final_path, staging_path = item
            pq.write_table(table, str(staging_path), compression="zstd")
            os.replace(str(staging_path), str(final_path))  # atomic
            return str(final_path)
        
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            results = list(pool.map(_write_one, parts_queue))
        
        logger.info("[L7] Parallel persist: %d parts in %.2fs, %d workers",
                    len(results), elapsed, n_workers)
        return results
    ```
  - Thread-safety：每個 part 寫獨立檔案 + `os.replace` 原子替換 + staging_path 含 part_id 不衝突
  - Edge case 處理：
    - `parts_queue` 為空 → 回傳空 list
    - 某個 part 寫入失敗（磁碟滿）→ raise `OSError`，不 silent fail
    - `n_workers=1` → 串行寫入（fallback）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_storage.py` → `_persist_parts_parallel()`（新增）, `persist_registry_to_parquet()`（修改呼叫邏輯）
- [ ] **不可做**:
  - 不可修改 zstd compression level（維持 level=1 速度優先）
  - 不可用 ProcessPoolExecutor（I/O bound，ThreadPool 足夠）
- [ ] **風險緩解**: R6（磁碟空間不足 — atomic write + raise OSError）
- [ ] **驗證**: T4.1, T4.2, T4.B1, T4.B2, T4.B3

### Task 4.2 — 呼叫端整合 — 硬體自適應 workers
- [x] **SPEC ref**: Task 4.2, §6.1
- [ ] **目標**: 在 persist 呼叫端根據 tier 選擇 workers
- [ ] **輸入**: 無（讀取 tier + env var）
- [ ] **輸出**: 無（修改呼叫邏輯）
- [ ] **實作要點**:
  - 在 persist 呼叫點整合：
    ```python
    tier = get_memory_tier()
    tier_cfg = get_tier_config(tier)
    n_workers = int(os.getenv("FFACT_L7_WORKERS", str(tier_cfg["l7_workers"])))
    
    if n_workers > 1 and len(parts_queue) > 1:
        written = self._persist_parts_parallel(parts_queue, n_workers)
    else:
        written = [_write_one(item) for item in parts_queue]  # 串行
    ```
  - Edge case 處理：
    - 只有 1 個 part → 不啟動 ThreadPool（開銷不值得）
    - `FFACT_L7_WORKERS=1` → 強制串行
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_storage.py` → persist 呼叫點
- [ ] **不可做**:
  - 不可 hardcode workers 數
- [ ] **驗證**: T4.3, T4.B4

### Phase 4 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T4.1 | `test_parallel_persist_matches_serial` | 平行寫入的 Parquet == 串行寫入 | 檔案 binary 比對（排除 metadata timestamp） | §6.2 |
| ☐ | T4.2 | `test_parallel_persist_atomic_write` | staging 檔正確替換為 final 檔 | `final_path.exists() and not staging_path.exists()` | §6.2 |
| ☐ | T4.3 | `test_tier_auto_selects_l7_workers` | 8GB tier → 4 workers | `n_workers == 4` | §6.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T4.B1 | `test_parallel_persist_empty_queue` | 空 parts_queue | 回傳空 list | §6.2 |
| ☐ | T4.B2 | `test_parallel_persist_single_part` | 只有 1 個 part | 串行寫入（不啟動 ThreadPool） | §6.2 |
| ☐ | T4.B3 | `test_parallel_persist_disk_full` | mock disk full → OSError | raise OSError，不 silent fail | §6.2 |
| ☐ | T4.B4 | `test_l7_workers_env_override` | `FFACT_L7_WORKERS=2` | 使用 2 workers | §6.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☐ | T4.P1 | `test_l7_parallel_speedup` | 4 workers 比 1 worker 快 ≥ 2× | §6.2 |

#### 測試檔案：`tests/test_l7_parallel_persist.py` + `tests/performance/test_l7_persist_perf.py`

### Phase 4 → Phase 5 Gate
- [ ] T4.1~T4.3 全部通過
- [ ] T4.B1~T4.B4 全部通過
- [ ] T4.P1 效能驗收通過（≥ 2× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）

---

## Phase 5 — 硬體資訊 API + 前端顯示

### Phase 5 目標與驗收標準
> 提供 REST API endpoint 暴露硬體資訊和建議設定，前端顯示系統資源面板。完成後 V2 Chat / V3 Agent 可自動讀取 `memory_tier` 並配置最佳參數。

### Task 5.1 — 後端 `GET /config/hardware` endpoint
- [x] **SPEC ref**: Task 5.1, §7.1
- [ ] **目標**: 新增 API endpoint 回傳硬體資訊、memory tier、建議設定
- [ ] **輸入**: 無（讀取系統資訊）
- [ ] **輸出**: JSON response，結構：
  ```json
  {
    "memory_tier": "8gb",
    "cpu": {"logical_cores": 8, "physical_cores": 4, "usage_pct": 23.0},
    "memory": {"total_gb": 8.0, "available_gb": 4.2, "used_pct": 47.0},
    "disk": {"path": "/path/to/data_cache", "free_gb": 142.0, "total_gb": 228.0, "used_pct": 38.0},
    "recommended_settings": {"FFACT_L65_WORKERS": 4, "FFACT_CGSA_MEMORY_BUFFER": 0, "FFACT_L7_WORKERS": 4}
  }
  ```
- [ ] **實作要點**:
  - 在 `api/routes/config.py` 新增：
    ```python
    @router.get("/hardware")
    async def get_hardware_info() -> Dict[str, Any]:
        import shutil
        import psutil
        from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config
        
        vm = psutil.virtual_memory()
        data_cache_path = Path("data_cache").resolve()
        try:
            disk = shutil.disk_usage(data_cache_path)
            disk_free_gb = round(disk.free / 1024**3, 1)
            disk_total_gb = round(disk.total / 1024**3, 1)
            disk_used_pct = round(disk.used / disk.total * 100, 1)
        except OSError:
            disk_free_gb = disk_total_gb = disk_used_pct = 0.0
        
        tier = get_memory_tier()
        tier_config = get_tier_config(tier)
        
        return {
            "memory_tier": tier,
            "cpu": {
                "logical_cores": os.cpu_count() or 1,
                "physical_cores": psutil.cpu_count(logical=False) or 1,
                "usage_pct": psutil.cpu_percent(interval=0.1),
            },
            "memory": {
                "total_gb": round(vm.total / 1024**3, 1),
                "available_gb": round(vm.available / 1024**3, 1),
                "used_pct": round(vm.percent, 1),
            },
            "disk": {"path": str(data_cache_path), "free_gb": disk_free_gb, "total_gb": disk_total_gb, "used_pct": disk_used_pct},
            "recommended_settings": {
                "FFACT_L65_WORKERS": tier_config["l65_workers"],
                "FFACT_CGSA_MEMORY_BUFFER": tier_config["cgsa_memory_buffer"],
                "FFACT_L7_WORKERS": tier_config["l7_workers"],
            },
        }
    ```
  - Edge case 處理：
    - `data_cache/` 不存在 → disk info 全為 0
    - psutil 不可用 → 回傳 fallback 值
- [ ] **修改檔案**:
  - `api/routes/config.py` → `get_hardware_info()`（新增 endpoint）
- [ ] **不可做**:
  - 不可暴露敏感資訊（API keys, 完整檔案系統路徑 outside data_cache）
  - 不可使用 `cpu_percent(interval=1)` 以上（會阻塞 async event loop）
- [ ] **風險緩解**: R9（API 不可用 — 前端 error boundary）
- [ ] **驗證**: T5.1, T5.2, T5.B1

### Task 5.2 — 前端 `HardwareStatusPanel.tsx`
- [x] **SPEC ref**: Task 5.2, §7.1
- [ ] **目標**: 建立系統資源顯示面板
- [ ] **輸入**: `GET /api/v1/config/hardware` 回傳的 JSON
- [ ] **輸出**: React 元件
- [ ] **實作要點**:
  - 新建 `frontend/src/components/feature-factory/HardwareStatusPanel.tsx`
  - UI Layout：
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
  - 顏色邏輯（Tailwind CSS）：
    - RAM 可用 ≥ 2GB → `text-green-600`；1-2GB → `text-yellow-600`；< 1GB → `text-red-600`
    - 磁碟可用 < 10GB → `text-yellow-600`；< 5GB → `text-red-600`
  - API 呼叫：`const res = await fetch('/api/v1/config/hardware')`
  - State management：`useState` for data + loading + error（不需 Zustand — 局部狀態足夠）
  - 手動重新整理按鈕（不自動輪詢）
  - Edge case 處理：
    - API 無回應 / 500 → 顯示 "無法取得系統資訊" 錯誤狀態
    - Loading 狀態 → skeleton placeholder
  - 加入 TypeScript interface：
    ```typescript
    interface HardwareInfo {
      memory_tier: string;
      cpu: { logical_cores: number; physical_cores: number; usage_pct: number };
      memory: { total_gb: number; available_gb: number; used_pct: number };
      disk: { path: string; free_gb: number; total_gb: number; used_pct: number };
      recommended_settings: { FFACT_L65_WORKERS: number; FFACT_CGSA_MEMORY_BUFFER: number; FFACT_L7_WORKERS: number };
    }
    ```
- [ ] **修改檔案**:
  - `frontend/src/components/feature-factory/HardwareStatusPanel.tsx`（**新增**）
- [ ] **不可做**:
  - 不可自動輪詢（使用者手動觸發）
  - 不可在此元件引入 Zustand store（不需要跨頁面共享此狀態）
- [ ] **風險緩解**: R9（error boundary + fallback 錯誤訊息）
- [ ] **驗證**: T5.3, T5.B2

### Task 5.3 — 嵌入 Feature Factory 頁面
- [x] **SPEC ref**: Task 5.3, §7.1
- [ ] **目標**: 將 HardwareStatusPanel 嵌入 Feature Factory 頁面
- [ ] **輸入**: `HardwareStatusPanel` 元件
- [ ] **輸出**: Feature Factory 頁面頂部可見系統資源面板
- [ ] **實作要點**:
  - 在 `frontend/src/app/feature-factory/page.tsx` 引入：
    ```tsx
    import { HardwareStatusPanel } from '@/components/feature-factory/HardwareStatusPanel';
    
    // 放置位置：頁面頂部，主要功能區域之前
    <HardwareStatusPanel />
    ```
  - 可折疊（預設展開），使用 `<details>` 或 custom collapsible
  - Edge case 處理：
    - API 不可用 → 面板顯示最小化的錯誤狀態，不影響其他功能
- [ ] **修改檔案**:
  - `frontend/src/app/feature-factory/page.tsx` → 引入 HardwareStatusPanel
- [ ] **不可做**:
  - 不可遮擋或替換現有的主要功能元件
  - 不可在未登入/API 不可用時 crash 整個頁面
- [ ] **驗證**: T5.3（隱含）

### Phase 5 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T5.1 | `test_hardware_endpoint_returns_valid_json` | endpoint 回傳正確 JSON 結構 | 包含 memory_tier, cpu, memory, disk, recommended_settings | §7.2 |
| ☐ | T5.2 | `test_hardware_endpoint_tier_matches_util` | endpoint tier == `get_memory_tier()` | 一致 | §7.2 |
| ☐ | T5.3 | `test_hardware_panel_renders_without_crash` | React 元件正常渲染 | 無 console error | §7.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T5.B1 | `test_hardware_endpoint_missing_data_cache` | `data_cache/` 不存在 | disk info 全為 0，endpoint 不 crash | §7.2 |
| ☐ | T5.B2 | `test_hardware_panel_api_error` | API 回傳 500 | 前端顯示錯誤狀態，不白屏 | §7.2 |

#### 測試檔案：`tests/test_hardware_api.py`

### Phase 5 → Done Gate
- [ ] T5.1~T5.3 全部通過
- [ ] T5.B1~T5.B2 全部通過
- [ ] API 可正常存取 `GET /api/v1/config/hardware`

---

## DEFERRED Tasks（記錄但不執行）

### Task 2.5: Polars Wide Matrix — ⚠️ DEFERRED
- **延後理由**: 435K cols × 17,928 rows × float32 = ~30 GB，僅在 32GB tier 可行。目前開發機為 8GB，無法測試。Polars API 跨版本有 breaking changes（R8）
- **觸發條件**: 當開發機升級至 32GB，且 P0-A ThreadPool 效果不足時
- **若跳過的影響**: 32GB tier 使用 ThreadPool 8 workers（~303s），而非 Polars 預估的 ~200s。差距可接受。

### Task 3.4: TimeChunkIterator — ⚠️ DEFERRED
- **延後理由**: 目前資料集為 17,928 rows (1h)，不需要 time chunking。此功能針對 1min 大資料集（630K rows）
- **觸發條件**: 當需要處理 1min timeframe 的資料集時
- **若跳過的影響**: 1min 大資料集在 8GB 下可能 OOM。目前 use case 不涉及 1min。

---

## 明確排除項目（Out of Scope）

| 項目 | 排除理由 |
|------|---------|
| `FFACT_LAYER1_PARALLEL`（L1 平行化） | L1 耗時僅 3.3s（佔總時間 0.04%），ROI 極低 |
| `compression_level` 調整 | 目前 zstd level=1 已是速度優先設定 |
| L1 Kline Data Ingestion 優化 | L1 耗時 3.3s（0.04%），非瓶頸 |
| L4/L5/L6 優化 | L4(22s) + L5(0.6s) + L6(0s) 合計 < 0.3%，非瓶頸 |
