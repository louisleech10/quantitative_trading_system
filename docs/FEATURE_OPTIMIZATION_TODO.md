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

#### 規則 B: Logging 規範 — 影響 Task 2.1, 2.4, 3.1, 4.1, 4.3

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
- Task 4.3: Async compactor 只在 batch merge 完成後做摘要 log，不可對每個小檔逐筆 log

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

#### 規則 G: 向後相容 — 影響 Task 2.1, 2.2, 3.2, 4.2, 4.3

| Phase | Fallback 機制 | 環境變數 |
|-------|--------------|---------|
| Phase 2 | L6.5 串行路徑 | `FFACT_L65_WORKERS=1` |
| Phase 3 | 現有 per-window kernel | `FFACT_L3_MULTI_WINDOW=0` |
| Phase 4 | L7 串行 writes + 停用背景合併 | `FFACT_L7_WORKERS=1`, `FFACT_L7_COMPACTOR_ENABLED=0` |
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
□ Logging 符合規則 B（不在 hot loop 中 log）
□ 命名符合規則 D
□ 測試有中文 docstring
□ 測試可獨立執行（無需 run_api.py）
□ .npy / .parquet 不在 git track 中
□ 效能程式碼符合規則 F
□ Fallback env var 可切回舊行為（規則 G）
□ ruff check momentum/ → 0 error
```

### 0.5 全域前置條件

- [x] 專案虛擬環境已啟用（`source venv/bin/activate`）
- [x] `requirements.txt` 內相依套件已安裝，且 `psutil`、`numba` 可於目前 venv 匯入
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
  Task 4.1, 4.2, 4.3
    │
    ▼ Gate: T4.x 全通過，C1~C6，≥2× speedup，且小檔數受控
Batch 5: [Phase 5] ──── 依賴 Batch 4 Gate + Phase 0（hardware_utils）
  Task 5.1, 5.2, 5.3
    │
    ▼ Gate: T5.x 全通過，API + 前端可用
```

### 批次明細

| Batch | 包含項目 | 依賴前置 | 合併理由 | 預估規模 |
|-------|---------|---------|---------|----------|
| 1 | Phase 0 (Task 0.1, 0.2) + Phase 1 (Task 1.1, 1.2, 1.3) | — | 修改不同檔案（新增 hardware_utils vs 修改 feature_factory），無互依賴 | 中（5 Task，但邏輯簡單） |
| 2 | Phase 2 (Task 2.1, 2.2, 2.3, 2.4, 2.5) | Batch 1 | 依賴 hardware_utils (Task 0.1) + CGSA registry 修改 (Task 1.x)；同批處理 greedy scheduling、warmup 與 deferred 判定，可減少重複改動與遺漏 | 中（5 Task，4 個實作 + 1 個 deferred 決策） |
| 3 | Phase 3 (Task 3.1, 3.2, 3.3, 3.4) | Batch 2 | 依賴 Phase 2 Gate 通過（確認 L6.5 正確後才改 L3）；同批保留大資料集 chunking 的 deferred 判定，避免後續批次遺漏 | 中（4 Task，3 個實作 + 1 個 deferred 決策） |
| 4 | Phase 4 (Task 4.1, 4.2, 4.3) | Batch 3 | `_persist_parts_parallel()`、呼叫端整合與 Async compactor 共用同一資料流，分開做容易造成介面漂移 | 中（3 Task，I/O 路徑與背景佇列需一起驗證） |
| 5 | Phase 5 (Task 5.1, 5.2, 5.3) | Batch 4 | 依賴 hardware_utils + 所有核心 Phase 完成 | 中（3 Task，跨前後端） |

### 批次間 Gate 檢查

| 轉換 | 必須通過的驗證 | 驗證命令 |
|------|-------------|----------|
| Batch 1 → 2 | T0.1~T0.4, T0.B1~T0.B3, T1.1~T1.4, T1.B1~T1.B5 + `grep -r "from api\." momentum/` = 0 | `./venv/bin/pytest tests/test_hardware_utils.py tests/test_cgsa_resume.py -v && ! grep -r 'from api\.' momentum/` |
| Batch 2 → 3 | T2.1~T2.6, T2.B1~T2.B7, T2.P1~T2.P2 + C1~C6 全量比對 + `FFACT_L65_WORKERS=1` fallback + Task 2.5 deferred 觸發條件仍未達成 | `./venv/bin/pytest tests/test_l65_parallel.py tests/performance/test_l65_parallel_perf.py -v` |
| Batch 3 → 4 | T3.1~T3.4, T3.B1~T3.B8, T3.P1~T3.P2 + C1~C6 + `FFACT_L3_MULTI_WINDOW=0` fallback + Task 3.4 deferred 觸發條件仍未達成 | `./venv/bin/pytest tests/test_multi_window_rolling.py tests/performance/test_multi_window_perf.py -v` |
| Batch 4 → 5 | T4.1~T4.5, T4.B1~T4.B7, T4.P1~T4.P2 + C1~C6 + `FFACT_L7_COMPACTOR_ENABLED=0` fallback | `./venv/bin/pytest tests/test_l7_parallel_persist.py tests/performance/test_l7_persist_perf.py -v` |
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
請執行：Task 2.1 + Task 2.2 + Task 2.3 + Task 2.4，並完成 Task 2.5 的 deferred 條件確認（不實作程式碼）
完成後執行驗證：
  ./venv/bin/pytest tests/test_l65_parallel.py tests/performance/test_l65_parallel_perf.py -v
  FFACT_L65_WORKERS=1 ./venv/bin/pytest tests/test_l65_parallel.py -v  # fallback 驗證
  手動確認 Task 2.5 觸發條件未達成：開發機非 32GB，且 P0-A ThreadPool 路徑已作為主要方案
```

**Batch 3**:
```
前置已完成：Batch 1-2（Phase 0-2 全部 Task + Gate 通過）
請執行：Task 3.1 + Task 3.2 + Task 3.3，並完成 Task 3.4 的 deferred 條件確認（不實作程式碼）
完成後執行驗證：
  ./venv/bin/pytest tests/test_multi_window_rolling.py tests/performance/test_multi_window_perf.py -v
  FFACT_L3_MULTI_WINDOW=0 ./venv/bin/pytest tests/test_multi_window_rolling.py -v  # fallback
  手動確認 Task 3.4 觸發條件未達成：目前資料集非 1min 大時間序列，故維持 deferred
```

**Batch 4**:
```
前置已完成：Batch 1-3（Phase 0-3 全部 Task + Gate 通過）
請執行：Task 4.1 + Task 4.2 + Task 4.3
完成後執行驗證：
  ./venv/bin/pytest tests/test_l7_parallel_persist.py tests/performance/test_l7_persist_perf.py -v
  FFACT_L7_WORKERS=1 ./venv/bin/pytest tests/test_l7_parallel_persist.py -v  # fallback
  FFACT_L7_COMPACTOR_ENABLED=0 ./venv/bin/pytest tests/test_l7_parallel_persist.py -v  # compactor fallback
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
- [x] **目標**: 實作記憶體層級自動偵測函式，支援環境變數覆蓋
- [x] **輸入**: 無（讀取 `psutil.virtual_memory().total` 和 `os.getenv("FFACT_MEMORY_TIER")`）
- [x] **輸出**: `str`（`"8gb"` | `"16gb"` | `"24gb"` | `"32gb"`）
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/utils/__init__.py`（**新增**，空檔案）
  - `momentum/FeatureEngineering/utils/hardware_utils.py`（**新增**）→ `get_memory_tier()`, `TIER_THRESHOLDS`
- [x] **不可做**:
  - 不可 import `api/` 任何模組（R1）
  - 不可加入 logging（此為純工具函式，無副作用）
  - 不可在此函式內加入 config file 讀取邏輯（保持純函式）
- [x] **風險緩解**: R1（解耦）, R10（psutil 不可用）
- [x] **驗證**: T0.1, T0.2, T0.B1, T0.B2, T0.B3

### Task 0.2 — 建立各層級功能矩陣常數（get_tier_config）
- [x] **SPEC ref**: Task 0.2, §2.1
- [x] **目標**: 定義各 tier 對應的 workers、buffer 等參數常數，提供統一查表函式
- [x] **輸入**: `tier: str`（由 `get_memory_tier()` 回傳）
- [x] **輸出**: `Dict[str, Any]`，keys: `l65_workers`, `cgsa_memory_buffer`, `l7_workers`, `chunk_bars`
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/utils/hardware_utils.py` → `get_tier_config()`, `_WORKERS_BY_TIER`, `_CGSA_BUFFER_BY_TIER`, `_L7_WORKERS_BY_TIER`, `_CHUNK_BARS_BY_TIER`
- [x] **不可做**:
  - 不可有任何副作用（純查表函式）
  - 不可直接暴露 `_PRIVATE` dict 給外部（只透過 `get_tier_config` 存取）
- [x] **風險緩解**: R1（解耦）
- [x] **驗證**: T0.3, T0.4

### Phase 0 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☑ | T0.1 | `test_get_memory_tier_auto_detection` | psutil 回傳值對應正確 tier | 8GB M1 → `"8gb"` | §2.2 |
| ☑ | T0.2 | `test_get_memory_tier_env_override` | `FFACT_MEMORY_TIER=16gb` → `"16gb"` | 環境變數覆蓋生效 | §2.2 |
| ☑ | T0.3 | `test_get_tier_config_returns_valid_dict` | 所有 4 個 tier 回傳的 dict 包含必要 keys | keys = {l65_workers, cgsa_memory_buffer, l7_workers, chunk_bars} | §2.2 |
| ☑ | T0.4 | `test_get_tier_config_unknown_tier_fallback` | 未知 tier → 回傳 8gb 值 | `l65_workers == 4` | §2.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☑ | T0.B1 | `test_get_memory_tier_env_auto` | `FFACT_MEMORY_TIER=auto` | 走 psutil 偵測路徑 | §2.2 |
| ☑ | T0.B2 | `test_get_memory_tier_env_empty` | `FFACT_MEMORY_TIER=""` | 走 psutil 偵測路徑 | §2.2 |
| ☑ | T0.B3 | `test_get_memory_tier_psutil_unavailable` | mock psutil 失敗 | 回傳 `"8gb"` | §2.2 |

#### 測試檔案：`tests/test_hardware_utils.py`

### Phase 0 → Phase 1 Gate
- [x] T0.1~T0.4 全部通過
- [x] T0.B1~T0.B3 全部通過
- [x] `grep -r "from api\." momentum/FeatureEngineering/utils/` → 0 結果

---

## Phase 1 — Resume 啟用 + CGSA 修正

### Phase 1 目標與驗收標準
> 啟用已實作但未被 production 呼叫的 `resume_from_manifest()` 功能，修改 CGSA work_dir 為決定性路徑，增加 manifest 損壞容錯。完成後崩潰場景可 resume 剩餘部分（而非重跑全部 2,424s）；正常執行無效能影響。

### Task 1.1 — 修正 `_prepare_cgsa_registry()` 使用決定性路徑
- [x] **SPEC ref**: Task 1.1, §3.1
- [x] **目標**: 將 `tempfile.mkdtemp()` 隨機路徑改為基於 symbol/timeframe/config_hash 的決定性路徑
- [x] **輸入**: `symbol: str`, `timeframe: str`, `config_hash: str = ""`
- [x] **輸出**: `Optional[ColumnGroupRegistry]`
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`（修改簽名+路徑邏輯）
- [x] **不可做**:
  - 不可刪除 `FFACT_CGSA_WORK_DIR` 環境變數路徑（保留作為手動覆蓋）
  - 不可修改 `ColumnGroupRegistry` 的 `__init__` 或 `resume_from_manifest` 簽名
- [x] **風險緩解**: R2（manifest 損壞）
- [x] **驗證**: T1.1, T1.2, T1.B1, T1.B2, T1.B3

### Task 1.2 — 呼叫端補傳 `config_hash` 參數
- [x] **SPEC ref**: Task 1.2, §3.1
- [x] **目標**: 在 `feature_factory.py` 呼叫 `_prepare_cgsa_registry` 處補傳 `config_hash`
- [x] **輸入**: 當前 scope 中的 `config_hash` 值
- [x] **輸出**: 無（修改呼叫簽名）
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `generate_features()`（補傳 `_prepare_cgsa_registry(symbol, timeframe, config_hash)`）
- [x] **不可做**:
  - 不可在此步驟改動 `resume_from_manifest()` 的邏輯
  - 不可修改 config_hash 的計算方式
- [x] **驗證**: T1.3

### Task 1.3 — 處理損壞的 manifest.json
- [x] **SPEC ref**: Task 1.3, §3.1
- [x] **目標**: 增加 resume 時的容錯處理，manifest 損壞時 fallback 到新 Registry
- [x] **輸入**: 已存在的 manifest.json（可能損壞）
- [x] **輸出**: 容錯 fallback 到新 `ColumnGroupRegistry`
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`（增加 try/except）
- [x] **不可做**:
  - 不可自動刪除損壞的 manifest（保留供人工檢查）
  - 不可 catch bare `Exception`（只 catch 預期的 3 種）
- [x] **風險緩解**: R2（manifest 損壞不再導致 pipeline 失敗）
- [x] **驗證**: T1.4, T1.B4, T1.B5

### Phase 1 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☑ | T1.1 | `test_cgsa_deterministic_path` | 相同 symbol/tf/hash → 相同路徑 | 兩次呼叫回傳相同 work_dir | §3.2 |
| ☑ | T1.2 | `test_cgsa_resume_from_existing_manifest` | manifest 存在時 resume 而非新建 | `resume_from_manifest` 被呼叫（mock 驗證） | §3.2 |
| ☑ | T1.3 | `test_cgsa_config_hash_passed_correctly` | config_hash 從呼叫端正確傳入 | work_dir 路徑含 hash prefix（前 8 字元） | §3.2 |
| ☑ | T1.4 | `test_cgsa_corrupt_manifest_fallback` | 損壞 manifest → 建新 Registry | 不 raise exception，回傳有效 Registry | §3.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☑ | T1.B1 | `test_cgsa_empty_config_hash` | `config_hash=""` | work_dir 含 `"nohash"` | §3.2 |
| ☑ | T1.B2 | `test_cgsa_special_chars_in_symbol` | `symbol="BTC/USDT:PERP"` | 清理為 `BTC_USDT_PERP` | §3.2 |
| ☑ | T1.B3 | `test_cgsa_work_dir_env_override` | `FFACT_CGSA_WORK_DIR=/tmp/test` | 使用環境變數路徑（不走決定性路徑） | §3.2 |
| ☑ | T1.B4 | `test_cgsa_empty_manifest_json` | manifest.json 內容為 `""` | `JSONDecodeError` → 建新 Registry | §3.2 |
| ☑ | T1.B5 | `test_cgsa_missing_npy_files_in_manifest` | manifest 記錄的 .npy 不存在 | 跳過該 group（不 crash），或建新 Registry | §3.2 |

#### 測試檔案：`tests/test_cgsa_resume.py`

### Phase 1 → Phase 2 Gate
- [x] T1.1~T1.4 全部通過
- [x] T1.B1~T1.B5 全部通過
- [ ] 正常執行的 pipeline 輸出與 V7 Baseline 數值等價（C1）[延到後續驗證階段]
- [ ] Resume 場景：手動殺掉 L6.5 中間 → 重跑 → 從中斷點繼續[延到後續驗證階段]

---

## Phase 2 — L6.5 Preprocessing 平行化（P0）

### Phase 2 目標與驗收標準
> 將 L6.5 `transform_registry_groups()` 從串行改為 ThreadPool 平行，支援 CGSA In-Memory Buffer（24/32GB tier），並加入貪婪排程與 Numba 冷啟動保護。完成後 L6.5 從 2,424s → ~606s (8GB/4w) / ~404s (16GB/6w) / ~303s (24GB/8w)。**最高 ROI 項目**。

### Task 2.1 — 實作 `_transform_registry_parallel()` — P0-A ThreadPool
- [x] **SPEC ref**: Task 2.1, §4.1
- [x] **目標**: 新增 ThreadPoolExecutor 平行路徑，保留串行路徑作為 fallback，並以 group 欄位數做貪婪排程避免長尾
- [ ] **輸入**: `registry: ColumnGroupRegistry`, `n_workers: int`
- [x] **輸出**: `int`（成功 transform 的 group 數）
- [ ] **實作要點**:
  - 修改 `transform_registry_groups()` 簽名，新增 `n_workers: int = 1` 參數
  - `n_workers > 1` → 走 `_transform_registry_parallel()`；`n_workers <= 1` → 走現有串行路徑（重命名為 `_transform_registry_serial()`）
  - 平行路徑實作偽碼：
    ```python
    def _transform_registry_parallel(self, registry, n_workers):
        groups = registry.list_all_groups()
        groups = sorted(
            groups,
            key=lambda group: getattr(group, "n_columns", 0),
            reverse=True,
        )

        completed, failed = 0, 0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(self._transform_single_group, registry, group): group
                for group in groups
            }
            for future in as_completed(futures):
                try:
                    future.result()
                    completed += 1
                except Exception as error:
                    failed += 1
                    logger.error(
                        "[L6.5] Failed group %s: %s",
                        futures[future].group_id,
                        error,
                        exc_info=True,
                    )

        elapsed = time.perf_counter() - t0
        logger.info(
            "[L6.5] Parallel complete: %d/%d in %.2fs (%d failed), %d workers",
            completed,
            len(groups),
            elapsed,
            failed,
            n_workers,
        )
        return completed
    ```
  - **【新增】Greedy scheduling 原因**：L65 每個 group 耗時差異極大，若沿用原始順序提交，容易出現「多個 worker 已空閒，但超大型 group 才剛開始」的長尾；以 `n_columns` 降序可讓大任務先進池，提升整體平衡度
  - Thread-safety 保證：
    - `overwrite_data()` 使用原子寫入（temp + `os.replace`）→ thread-safe
    - `load_data(mmap_mode="r")` → 多執行緒讀取安全
    - 各 group 完全獨立，無共享可變狀態
    - 若 CGSA buffer > 0（24/32GB），`save_data()` 經由 `_buffer_lock` 保護（見 Task 2.4）
  - Edge case 處理：
    - `n_workers=0` → 等同 `n_workers=1`，串行執行
    - groups 為空列表 → 直接回傳 0
    - 某個 group transform 失敗 → log error，繼續其他 groups，最終回傳 `completed < total`
    - `n_columns` 屬性不存在或全為 0 → 排序退化但不影響正確性
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `transform_registry_groups()`（修改簽名）, `_transform_registry_parallel()`（新增）, `_transform_registry_serial()`（重命名現有邏輯）
- [ ] **不可做**:
  - 不可使用 `ProcessPoolExecutor`（L6.5 現階段 ThreadPool 足夠且開銷較低）
  - 不可移除串行路徑（`n_workers=1` 必須走串行）
  - 不可在 `_transform_single_group` 內逐 group log 成功訊息（hot loop）
- [ ] **風險緩解**: R3（並發 race condition）, R12（group 成本不均造成長尾）
- [x] **驗證**: T2.1, T2.2, T2.6, T2.B1, T2.B2, T2.B3, T2.B4

### Task 2.2 — 呼叫端整合 — 硬體自適應 workers
- [x] **SPEC ref**: Task 2.2, §4.1
- [x] **目標**: 在呼叫端根據 `get_memory_tier()` 自動選擇 workers 數，並同步帶入 CGSA buffer 設定
- [ ] **輸入**: 無（讀取 tier + env var）
- [ ] **輸出**: 無（修改呼叫邏輯）
- [ ] **實作要點**:
  - 在 L6.5 呼叫端整合：
    ```python
    from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

    tier = get_memory_tier()
    tier_cfg = get_tier_config(tier)
    n_workers = int(os.getenv("FFACT_L65_WORKERS", str(tier_cfg["l65_workers"])))
    buffer_groups = int(os.getenv("FFACT_CGSA_MEMORY_BUFFER", str(tier_cfg["cgsa_memory_buffer"])))

    registry = ColumnGroupRegistry(
        work_dir=work_dir,
        memory_buffer_groups=buffer_groups,
    )
    preprocessor.transform_registry_groups(registry, n_workers=n_workers)
    ```
  - Edge case 處理：
    - `FFACT_L65_WORKERS=1` → 強制串行（完整 fallback）
    - `FFACT_L65_WORKERS=0` → 等同 1（串行）
    - `FFACT_CGSA_MEMORY_BUFFER` 缺值或非法 → 回退到 tier 預設值
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/feature_factory.py` → `_prepare_cgsa_registry()`（依 tier 建立 `memory_buffer_groups`）
  - `momentum/FeatureEngineering/feature_factory.py` → `_layer6_5_preprocessing()`（讀取 tier config 並傳入 `n_workers`）
- [ ] **不可做**:
  - 不可 hardcode workers 數
  - 不可跳過 `get_tier_config()` 直接散落常數到 pipeline 主流程
- [ ] **風險緩解**: R3（workers=1 為完整 fallback）, R7（buffer 只於高記憶體 tier 啟用）
- [x] **驗證**: T2.3

### Task 2.3 — Numba warmup 確保 JIT 完成
- [x] **SPEC ref**: Task 2.3, §4.1
- [x] **目標**: 主執行緒先 warmup Numba JIT，再啟動 ThreadPool，並明確防範未來多進程冷啟動 storm
- [ ] **輸入**: 無
- [ ] **輸出**: 無（副作用：Numba functions 已完成或略過 warmup）
- [ ] **實作要點**:
  - 新增 `_warmup_numba_if_needed(self) -> None`：
    ```python
    def _warmup_numba_if_needed(self) -> None:
        if getattr(self, "_numba_warmed_up", False):
            return

        try:
            from momentum.FeatureEngineering.operators.numba_rolling import warmup_numba

            warmup_numba()
        except ImportError:
            pass

        self._numba_warmed_up = True
    ```
  - 在 `_transform_registry_parallel()` 開頭呼叫此函式
  - 所有相關 `@numba.njit` 必須使用 `cache=True`，讓主進程 warmup 後能將機器碼寫入磁碟快取
  - **【新增】ProcessPool 安全性說明**：
    - 目前 Task 2.1 使用 ThreadPool，warmup 後同進程 worker 可直接共享 JIT 結果
    - 若未來引入 `ProcessPoolExecutor`，主進程必須先 warmup 並確認 `.nbi` / `.nbc` 快取存在，避免每個子進程各自編譯造成 CPU/RAM 暴衝
  - Edge case 處理：
    - Numba 未安裝 → `ImportError` → skip warmup，但流程不中斷
    - 多次呼叫 → 只 warmup 一次
    - 快取目錄不可寫 → `cache=True` 退化，需記錄 warning 並接受首次重新編譯
    - `warmup_numba()` 尚不存在 → 先在 `numba_rolling.py` 補最小 warmup 函式
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `_warmup_numba_if_needed()`（新增）
  - `momentum/FeatureEngineering/operators/numba_rolling.py` → 若缺少 `warmup_numba()` 則補上
- [ ] **不可做**:
  - 不可在 warmup 中執行大型資料集計算
  - 不可移除 `cache=True` 或以註解代替實際 warmup
- [ ] **風險緩解**: R13（Numba 多進程冷啟動 storm）
- [x] **驗證**: T2.B7（顯式驗證）, T2.1（隱式驗證）

### Task 2.4 — CGSA In-Memory Buffer — P0-B（24/32GB tier）
- [x] **SPEC ref**: Task 2.4, §4.1
- [x] **目標**: 24/32GB tier 緩衝多個 group 的 `.npy` 陣列，批次寫入減少 disk I/O
- [ ] **輸入**: `memory_buffer_groups: int`（0=立即 flush, N=緩衝 N 個 group）
- [ ] **輸出**: 減少 disk writes（708 次 → 約 22 次 at buffer=32）
- [ ] **實作要點**:
  - 修改 `ColumnGroupRegistry.__init__()` 新增 `memory_buffer_groups: int = 0` 參數
  - 新增 instance 變數：
    ```python
    self._memory_buffer: Dict[str, np.ndarray] = {}
    self._memory_buffer_limit = memory_buffer_groups
    self._buffer_lock = threading.Lock()
    ```
  - **【補充】實際簽名差異**：SPEC 偽碼以 `group_id: str` 示意，但現有 `save_data()` 實際簽名為 `save_data(self, group: ColumnGroup, data: np.ndarray) -> ColumnGroup`；實作時以 `group.group_id` 做 buffer key，不可改變既有公共介面
  - 修改 `save_data()` 邏輯：
    ```python
    if self._memory_buffer_limit > 0:
        with self._buffer_lock:
            self._memory_buffer[group.group_id] = data
            if len(self._memory_buffer) >= self._memory_buffer_limit:
                self._flush_buffer()
    else:
        np.save(path, data_fp32, allow_pickle=False)
    ```
  - 新增 `_flush_buffer()` 與 `finalize()`；在 `feature_factory.py` 的 L6.5 完成後呼叫 `registry.finalize()`
  - Edge case 處理：
    - buffer=0（8/16GB）→ 完全向後相容，現有行為不變
    - Pipeline 中途崩潰 → buffer 中未 flush data 遺失（可接受，resume 會重算）
    - `finalize()` 必須在 pipeline 結束時呼叫
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/core/column_group_registry.py` → `__init__()`、`save_data()`、`_flush_buffer()`、`finalize()`
  - `momentum/FeatureEngineering/feature_factory.py` → L6.5 完成後呼叫 `registry.finalize()`
- [ ] **不可做**:
  - 不可在 8/16GB tier 啟用 buffer
  - 不可改變 `save_data()` 的外部簽名
  - 不可在 `_flush_buffer()` 外部直接操作 `_memory_buffer`
- [ ] **風險緩解**: R7（buffer 崩潰遺失）
- [x] **驗證**: T2.4, T2.5, T2.B5, T2.B6

### Task 2.5 — Polars Wide Matrix — ⚠️ DEFERRED
- [x] **SPEC ref**: Task 2.5, §4.1
- [x] **目標**: 保留 32GB tier 的 Polars wide-matrix 升級入口，但本輪只完成 deferred 判定，不實作程式碼
- [ ] **輸入**: `tier: str = "32gb"`、超寬矩陣資料（約 435K columns × 17,928 rows）與 P0-A ThreadPool 的實測結果
- [ ] **輸出**: 本輪輸出為 deferred 決策紀錄；未來啟用時輸出為 Polars-based wide matrix transform 路徑
- [ ] **實作要點**:
  - 本輪不修改執行路徑，只在 TODO 中保留精確啟用條件與未來落點，避免誤被視為遺漏
  - 未來啟用時優先落在 `FeaturePreprocessor._transform_single_polars()`，並由 `transform_registry_groups()` 或 `transform()` 增加 `32gb` 專用分支
  - 未來啟用時的最小偽碼：
    ```python
    if tier != "32gb":
        return existing_threadpool_path()
    if estimated_matrix_gb > 30:
        raise SkipPolarsPath()
    return self._transform_single_polars(features_df)
    ```
  - Edge case 處理：
    - 32GB 以外 tier → 必須維持 Task 2.1 ThreadPool 路徑
    - Polars 版本與既有 API 不相容 → 保持 deferred，不可半實作
    - fracdiff 開啟時 → 不可直接切 Polars 路徑（目前 `_transform_single_polars()` 已有限制）
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `transform()`、`transform_registry_groups()`、`_transform_single_polars()`（未來啟用時）
  - `momentum/FeatureEngineering/polars_adapter.py` → Polars 能力檢查與版本相容層（未來啟用時）
- [ ] **不可做**:
  - 本輪不可提前加入未驗證的 Polars 生產路徑
  - 不可在 8/16/24GB tier 嘗試 materialize 435K 欄寬矩陣
  - 不可在未補齊 numeric equivalence 測試前移除 ThreadPool 主路徑
- [ ] **風險緩解**: R8（Polars API breaking change）
- [x] **驗證**: 本輪僅驗證 deferred 狀態仍合理：開發機非 32GB，且 Task 2.1~2.4 已提供主路徑；未來啟用前需另補充專用測試

### Phase 2 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☑ | T2.1 | `test_parallel_transform_matches_serial` | 4 workers 結果 == 1 worker 結果 | `np.allclose(atol=1e-4, equal_nan=True)` | §4.2 |
| ☑ | T2.2 | `test_parallel_transform_all_groups_complete` | 所有 groups 均被處理 | `completed == len(groups)` | §4.2 |
| ☑ | T2.3 | `test_tier_auto_selects_workers` | 8GB tier → 4 workers | `n_workers == 4` | §4.2 |
| ☑ | T2.4 | `test_cgsa_buffer_batch_write` | buffer=4 時每 4 groups 才 flush | mock `np.save` 呼叫次數（若已抽出 helper，則 mock helper） | §4.2 |
| ☑ | T2.5 | `test_cgsa_buffer_finalize_flushes_remaining` | finalize 清空剩餘 buffer | `len(registry._memory_buffer) == 0` | §4.2 |
| ☑ | T2.6 | `test_parallel_greedy_scheduling_largest_groups_first` | 平行提交順序按 `n_columns` 降序 | 最大 group 最先進入 pool | §4.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☑ | T2.B1 | `test_parallel_zero_groups` | 空 groups 列表 | 回傳 0，不 crash | §4.2 |
| ☑ | T2.B2 | `test_parallel_single_group` | 只有 1 個 group | 正常處理 | §4.2 |
| ☑ | T2.B3 | `test_parallel_one_group_fails` | 1 個 group raise Exception | 其他 groups 不受影響，`completed < total` | §4.2 |
| ☑ | T2.B4 | `test_parallel_workers_1_is_serial` | `n_workers=1` | 走串行路徑 `_transform_registry_serial` | §4.2 |
| ☑ | T2.B5 | `test_cgsa_buffer_zero_is_immediate_flush` | buffer=0 | 每次 save 立即 write（現有行為） | §4.2 |
| ☑ | T2.B6 | `test_cgsa_buffer_crash_loses_unflushed` | buffer=4, 存 2 個後模擬 crash | 只有已 flush 內容落盤；未 flush 內容遺失 | §4.2 |
| ☑ | T2.B7 | `test_numba_warmup_runs_before_process_pool_fanout` | 模擬未來 ProcessPool 路徑 | 主進程 warmup 先於 worker 啟動 | §4.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☑ | T2.P1 | `test_l65_parallel_4workers_speedup` | 4 workers 比 1 worker 快 ≥ 2× | §4.2 |
| ☑ | T2.P2 | `test_l65_parallel_rss_under_limit` | RSS 增量 < 1 GB（vs serial baseline） | §4.2 |

#### 測試檔案：`tests/test_l65_parallel.py` + `tests/performance/test_l65_parallel_perf.py`

### Phase 2 → Phase 3 Gate
- [x] T2.1~T2.6 全部通過
- [x] T2.B1~T2.B7 全部通過
- [x] T2.P1 效能驗收通過（≥ 2× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）[延到後續驗證階段]
- [x] `FFACT_L65_WORKERS=1` fallback 正常

---

## Phase 3 — L3 Rolling Aggregation 優化（P2）

### Phase 3 目標與驗收標準
> 擴展 Numba kernel 為多 window 版本，每個 column 讀取 1 次（vs 現行 8 次），加上 batch variance filter 減少 memmap writes。完成後 L3 從 2,051s → ~1,400s (8GB)。

### Task 3.1 — 實作 `fused_rolling_stats_multi_window()` — P2-A Multi-Window Fused Kernel
- [x] **SPEC ref**: Task 3.1, §5.1
- [x] **目標**: 每個 column 只讀取 1 次，同時計算所有 windows 的 rolling stats
- [x] **輸入**: `values: np.ndarray` shape (n_rows,), `windows: np.ndarray` shape (n_windows,) int32
- [x] **輸出**: `np.ndarray` shape (n_rows, n_windows, N_STATS)，internal float64
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/operators/numba_rolling.py` → `fused_rolling_stats_multi_window()`（新增）
- [x] **不可做**:
  - 不可在 Numba JIT 內呼叫 Python 函式（包括 logger、print）
  - 不可刪除現有 `fused_rolling_stats()`（保留作為 fallback）
  - 不可使用 `parallel=True` 和 `prange` 在 column 維度（data race 風險）
- [x] **風險緩解**: R4（數值穩定性 — float64 累加器 + T3.B2 全常數測試）, R5（Numba ARM64 相容性）
- [x] **驗證**: T3.1, T3.3, T3.B1~T3.B7

### Task 3.2 — 整合到 `_compute_all_streaming_numba()`
- [x] **SPEC ref**: Task 3.2, §5.1
- [x] **目標**: 修改 RollingAggregator 呼叫邏輯，改用 multi-window kernel
- [x] **輸入**: 環境變數 `FFACT_L3_MULTI_WINDOW`（預設 `"1"` 啟用）
- [x] **輸出**: 與現行相同的 rolling 結果（column name、NaN pattern 完全一致）
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_compute_all_streaming_numba()`
- [x] **不可做**:
  - 不可移除現有 per-window 路徑（保留作為 `FFACT_L3_MULTI_WINDOW=0` fallback）
  - 不可改變輸出 column name 的命名規則
- [x] **驗證**: T3.2, T3.B8

### Task 3.3 — Batch Variance Filter — P2-B
- [x] **SPEC ref**: Task 3.3, §5.1
- [x] **目標**: 每個 window 的所有 agg 計算完畢後，做一次 batch variance filter 再寫入（減少 memmap writes）
- [x] **輸入**: `window_results: Dict[str, np.ndarray]`（某 window 的所有 agg 結果）
- [x] **輸出**: 過濾後的 dict（只含非零方差 columns），與現行 filter 結果一致
- [x] **實作要點**:
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
- [x] **修改檔案**:
  - `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_batch_variance_filter()`（新增）, `_compute_all_streaming_numba()`（修改 write 時機）
- [x] **不可做**:
  - 不可改變 variance filter 的判斷閾值或邏輯（只改批次化時機）
  - 不可在 filter 前改變 data 的值
- [x] **驗證**: T3.4

### Task 3.4 — TimeChunkIterator — ⚠️ DEFERRED
- [x] **SPEC ref**: Task 3.4, §5.1
- [x] **目標**: 保留大資料集的 time-chunking 設計入口，但本輪只完成 deferred 判定，不引入額外 chunk orchestration
- [x] **輸入**: `n_rows`、`max_window`、目標 timeframe（特別是 1min）
- [x] **輸出**: 本輪輸出為 deferred 決策紀錄；未來啟用時輸出為可逐時間塊串流的 rolling aggregation 路徑
- [x] **實作要點**:
  - 本輪不修改 `_compute_all_streaming_numba()` 執行流程，只保留未來在大資料集啟用 chunking 的落點
  - 未來啟用時優先在 `rolling_aggregator.py` 新增 `TimeChunkIterator`，並由 `_compute_all_streaming_numba()` 增加 chunked branch
  - 未來啟用時的最小偽碼：
    ```python
    if n_rows < chunk_threshold:
        return self._compute_all_streaming_numba(features_df, columns, valid_aggs)
    for chunk in TimeChunkIterator(features_df, overlap=max_window - 1):
        yield self._compute_chunk(chunk)
    ```
  - Edge case 處理：
    - `n_rows` 小於 chunk 門檻 → 必須維持現有 non-chunk 路徑
    - chunk overlap 不足 → 會破壞 rolling window NaN pattern，故不可上線
    - 1min 大資料集 + 8GB → 若未啟用 chunking 需明確標示 OOM 風險
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/operators/rolling_aggregator.py` → `_compute_all_streaming_numba()`（未來 chunked branch）, `TimeChunkIterator`（新增）
- [ ] **不可做**:
  - 本輪不可加入半成品 chunk 路徑破壞 C1~C6
  - 不可在未定義 overlap 與邊界拼接規則前切入 chunk 處理
  - 不可將 1h 目前資料集強行改成 chunked 路徑以增加複雜度
- [x] **風險緩解**: 未來主要對應大資料集 OOM 風險；本輪以明確 deferred 決策避免過早複雜化
- [x] **驗證**: 本輪僅驗證 deferred 狀態仍合理：目前資料集為 17,928 rows（1h），不需 chunking；未來 1min 專案啟動前再補專用測試

### Phase 3 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☑ | T3.1 | `test_multi_window_matches_single_window` | multi-window 結果 == 逐 window 結果 | `np.allclose(atol=1e-4, equal_nan=True)` per stat | §5.2 |
| ☑ | T3.2 | `test_multi_window_golden_equivalence` | multi-window pipeline → V7 golden 比對 | C1 全量比對通過 | §5.2 |
| ☑ | T3.3 | `test_multi_window_nan_pattern_preserved` | NaN pattern 與 V7 完全一致 | C6: `np.array_equal(nan_mask_new, nan_mask_golden)` | §5.2 |
| ☑ | T3.4 | `test_batch_variance_filter_matches_per_step` | batch filter 結果 == per-step filter 結果 | 保留的 column set 一致 | §5.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☑ | T3.B1 | `test_multi_window_all_nan_input` | 輸入全 NaN | 輸出全 NaN | §5.2 |
| ☑ | T3.B2 | `test_multi_window_constant_values` | 輸入單一常數值 | mean=val, std=0, skew=NaN, kurt=NaN | §5.2 |
| ☑ | T3.B3 | `test_multi_window_single_window` | windows=[21] 單一 window | 結果與逐 window 一致 | §5.2 |
| ☑ | T3.B4 | `test_multi_window_short_series` | n_rows=10, max_window=21 | 前 20 行 NaN | §5.2 |
| ☑ | T3.B5 | `test_multi_window_extreme_values` | 含 1e30 和 1e-30 | 不 overflow/underflow | §5.2 |
| ☑ | T3.B6 | `test_multi_window_all_windows` | 所有 9 個 window 同時 (5,8,13,21,34,55,89,144,233) | 全部正確 | §5.2 |
| ☑ | T3.B7 | `test_multi_window_intermittent_nan` | [1, NaN, 3, NaN, 5, ...] intermittent NaN | 跳過 NaN，min_periods 行為一致 | §5.2 |
| ☑ | T3.B8 | `test_fallback_env_var` | `FFACT_L3_MULTI_WINDOW=0` | 走逐 window 舊路徑，結果不變 | §5.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☑ | T3.P1 | `test_multi_window_speedup` | multi-window 比逐 window 快 ≥ 1.3× | §5.2 |
| ☑ | T3.P2 | `test_multi_window_rss_stable` | RSS 增量 < 500 MB | §5.2 |

#### 測試檔案：`tests/test_multi_window_rolling.py` + `tests/performance/test_multi_window_perf.py`

### Phase 3 → Phase 4 Gate
- [x] T3.1~T3.4 全部通過
- [x] T3.B1~T3.B8 全部通過
- [x] T3.P1 效能驗收通過（≥ 1.3× speedup）
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [x] `FFACT_L3_MULTI_WINDOW=0` fallback 正常

---

## Phase 4 — L7 Parallel Parquet Writes + Async Compactor（P3）

### Phase 4 目標與驗收標準
> ThreadPool 平行寫入 Parquet parts，並加入背景 Async compactor 避免小檔案數爆炸反噬 SSD IOPS。完成後 L7 從 467s → ~150s (8GB/4w) / ~100s (24GB/8w)，同時確保輸出檔案數受控。

### Task 4.1 — 實作 `_persist_parts_parallel()`
- [x] **SPEC ref**: Task 4.1, §6.1
- [ ] **目標**: ThreadPool 平行寫入已分割的 Parquet parts，並支援選配的 compactor 佇列
- [ ] **輸入**: `parts_queue: List[Tuple[str, Any, Path, Path]]`（part_id, arrow_table, final_path, staging_path）, `n_workers: int`, `compactor: Optional[AsyncParquetCompactor] = None`
- [ ] **輸出**: `List[str]`（已接受的 part 目標路徑；若啟用 compactor，實際 merged 檔案由 `finalize()` 回傳）
- [ ] **實作要點**:
  - 新增方法於 `feature_storage.py`：
    ```python
    def _persist_parts_parallel(self, parts_queue, n_workers, compactor=None):
        import pyarrow.parquet as pq

        def _write_one(item):
            part_id, table, final_path, staging_path = item
            pq.write_table(table, str(staging_path), compression="zstd")
            if compactor is not None:
                compactor.enqueue((part_id, staging_path))
            else:
                os.replace(str(staging_path), str(final_path))
            return str(final_path)

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            results = list(pool.map(_write_one, parts_queue))

        logger.info(
            "[L7] Parallel persist: %d parts in %.2fs, %d workers",
            len(results),
            elapsed,
            n_workers,
        )
        return results
    ```
  - Thread-safety：每個 part 寫獨立檔案；未啟用 compactor 時使用 `os.replace` 原子替換；啟用 compactor 時只負責 staging write 與 enqueue
  - Edge case 處理：
    - `parts_queue` 為空 → 回傳空 list
    - 某個 part 寫入失敗（磁碟滿）→ raise `OSError`，不 silent fail
    - `n_workers=1` → 串行寫入（fallback）
    - 啟用 compactor 時，回傳值表示 part 已被接收，不代表最終 merged 檔已生成
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_storage.py` → `_persist_parts_parallel()`（新增或擴充）, `persist_registry_to_parquet()`（修改呼叫邏輯）
- [ ] **不可做**:
  - 不可修改 zstd compression level（維持 level=1 速度優先）
  - 不可用 `ProcessPoolExecutor`（I/O bound，ThreadPool 足夠）
- [ ] **風險緩解**: R6（磁碟空間不足）, R11（小檔案爆炸）
- [ ] **驗證**: T4.1, T4.2, T4.B1, T4.B2, T4.B3

### Task 4.2 — 呼叫端整合 — 硬體自適應 workers + compactor 開關
- [x] **SPEC ref**: Task 4.2, §6.1
- [ ] **目標**: 在 persist 呼叫端根據 tier 選擇 workers，並依條件啟用 Async compactor
- [ ] **輸入**: 無（讀取 tier + env var）
- [ ] **輸出**: 無（修改呼叫邏輯）
- [ ] **實作要點**:
  - 在 persist 呼叫點整合：
    ```python
    tier = get_memory_tier()
    tier_cfg = get_tier_config(tier)
    n_workers = int(os.getenv("FFACT_L7_WORKERS", str(tier_cfg["l7_workers"])))
    compactor_enabled = os.getenv("FFACT_L7_COMPACTOR_ENABLED", "1").strip() != "0"
    target_rows = int(os.getenv("FFACT_L7_COMPACTOR_TARGET_ROWS", "100000"))

    if compactor_enabled and chunk_bars is not None and max_group_columns <= 5_000:
        compactor = AsyncParquetCompactor(staging_dir, final_dir, target_rows=target_rows)
        compactor.start()
        written = self._persist_parts_parallel(parts_queue, n_workers, compactor=compactor)
        merged_files = compactor.finalize()
    elif n_workers > 1 and len(parts_queue) > 1:
        written = self._persist_parts_parallel(parts_queue, n_workers)
    else:
        written = [_write_one(item) for item in parts_queue]
    ```
  - Edge case 處理：
    - 只有 1 個 part → 不啟動 ThreadPool
    - `FFACT_L7_WORKERS=1` → 強制串行
    - `FFACT_L7_COMPACTOR_ENABLED=0` → 完整回退到直接輸出模式
    - 啟用 compactor 時，worker 只保證 staging 寫入成功；最終檔案 promotion 由背景合併程序負責
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_storage.py` → `persist_registry_to_parquet()`（注入 tier-based workers / compactor 選擇）
  - `momentum/FeatureEngineering/feature_factory.py` → `generate_features()`（persist branch 傳遞最終寫出策略）
- [ ] **不可做**:
  - 不可 hardcode workers 或 `target_rows`
  - 不可讓 compactor 在主 worker thread 同步執行 merge
- [ ] **風險緩解**: R11（IOPS bottleneck）
- [ ] **驗證**: T4.3, T4.B4, T4.B5

### Task 4.3 — 實作 `AsyncParquetCompactor`
- [x] **SPEC ref**: Task 4.3, §6.1
- [ ] **目標**: 將 L7 worker 先輸出到 staging 目錄，由背景執行緒批次合併小型 Parquet parts，抑制碎片化檔案數暴增
- [ ] **輸入**: `staging_dir: Path`, `final_dir: Path`, `target_rows: int = 100_000`, `min_files_to_compact: int = 8`
- [ ] **輸出**: 較少的大型 Parquet 檔案 + manifest 對應資訊
- [ ] **實作要點**:
  - 在 `feature_storage.py` 新增：
    ```python
    class AsyncParquetCompactor:
        def __init__(self, staging_dir, final_dir, target_rows=100_000, min_files_to_compact=8):
            ...

        def start(self) -> None:
            ...

        def enqueue(self, item: Tuple[str, Path]) -> None:
            ...

        def finalize(self) -> List[Path]:
            ...
    ```
  - 背景流程：
    1. L7 worker 將 part 寫到 `staging_dir/part_*.parquet`
    2. worker 完成後呼叫 `compactor.enqueue((part_id, staging_path))`
    3. compactor 累積到 `min_files_to_compact` 或 `target_rows` 門檻後觸發 merge
    4. merge 後產出 `final_dir/merged_{index}.parquet`，刪除已吸收的小檔
    5. pipeline 結束時呼叫 `compactor.finalize()`，排空佇列與剩餘 staging 檔
  - **【新增】設計動機**：8GB tier 為避免 OOM 會使用較小 `chunk_bars` 與較小 group 上限，雖然能降低記憶體壓力，但會產生更多小型 part 檔；若不做背景合併，L7 與後續 ML 讀取都會退化
  - Edge case 處理：
    - `parts_queue` 很小（低於 `min_files_to_compact`）→ 直到 `finalize()` 才做最後合併
    - merge 過程 crash → staging 目錄保留，final 目錄不可部分覆寫
    - 單一 part 已超過 `target_rows` → 直接 promote，不做二次合併
    - 若後續 ML 仍需 part-aware 讀取 → 保留 manifest 記錄 merged 檔與來源檔對應
- [ ] **修改檔案**:
  - `momentum/FeatureEngineering/feature_storage.py` → `AsyncParquetCompactor`（新增）與 manifest 整合點
- [ ] **不可做**:
  - 不可在主執行緒同步合併
  - 不可在 merge 失敗時刪除尚未成功吸收的 staging 檔
- [ ] **風險緩解**: R11（小檔案/IOPS）, R6（crash 時保留 staging 供復原）
- [ ] **驗證**: T4.4, T4.5, T4.B6, T4.B7, T4.P2

### Phase 4 測試清單

#### 單元測試
| ☐ | Test ID | 測試名稱 | 驗證內容 | 通過條件 | SPEC ref |
|---|---------|---------|---------|---------|---------|
| ☐ | T4.1 | `test_parallel_persist_matches_serial` | 平行寫入的 Parquet == 串行寫入 | 檔案 binary 比對（排除 metadata timestamp） | §6.2 |
| ☐ | T4.2 | `test_parallel_persist_atomic_write` | 寫入過程中 staging 檔存在，完成後只有 final 檔 | `final_path.exists() and not staging_path.exists()` | §6.2 |
| ☐ | T4.3 | `test_tier_auto_selects_l7_workers` | 8GB tier → 4 workers | `n_workers == 4` | §6.2 |
| ☐ | T4.4 | `test_async_compactor_merges_small_files_into_large_parts` | 多個 staging 小檔被合併 | final 檔案數 < staging 檔案數 | §6.2 |
| ☐ | T4.5 | `test_async_compactor_manifest_tracks_sources` | merge 後 manifest 記錄來源檔案 | manifest 含 merged→source 對應 | §6.2 |

#### 邊界條件測試
| ☐ | Test ID | 測試名稱 | 邊界條件 | 預期行為 | SPEC ref |
|---|---------|---------|---------|---------|----------|
| ☐ | T4.B1 | `test_parallel_persist_empty_queue` | 空 parts_queue | 回傳空 list | §6.2 |
| ☐ | T4.B2 | `test_parallel_persist_single_part` | 只有 1 個 part | 串行寫入（不啟動 ThreadPool） | §6.2 |
| ☐ | T4.B3 | `test_parallel_persist_disk_full` | mock disk full → OSError | raise OSError，不 silent fail | §6.2 |
| ☐ | T4.B4 | `test_l7_workers_env_override` | `FFACT_L7_WORKERS=2` | 使用 2 workers | §6.2 |
| ☐ | T4.B5 | `test_async_compactor_disabled_bypasses_merge` | `FFACT_L7_COMPACTOR_ENABLED=0` | 不建立 compactor，直接輸出小檔 | §6.2 |
| ☐ | T4.B6 | `test_async_compactor_finalize_flushes_remaining_files` | 未達 batch 門檻即結束 | `finalize()` 後 staging 為空 | §6.2 |
| ☐ | T4.B7 | `test_async_compactor_crash_preserves_staging_files` | merge 中途 raise OSError | staging 檔仍存在，final 不部分覆蓋 | §6.2 |

#### 效能驗收
| ☐ | Test ID | 測試名稱 | 驗收標準 | SPEC ref |
|---|---------|---------|---------|----------|
| ☐ | T4.P1 | `test_l7_parallel_speedup` | 4 workers 比 1 worker 快 ≥ 2× | §6.2 |
| ☐ | T4.P2 | `test_async_compactor_controls_file_explosion` | 8GB tier 小檔數壓到原始 staging 檔數的 ≤ 25% | §6.2 |

#### 測試檔案：`tests/test_l7_parallel_persist.py` + `tests/performance/test_l7_persist_perf.py`

### Phase 4 → Phase 5 Gate
- [ ] T4.1~T4.5 全部通過
- [ ] T4.B1~T4.B7 全部通過
- [ ] T4.P1~T4.P2 效能驗收通過
- [ ] Pipeline 完整輸出與 V7 Baseline 數值等價（C1~C6）
- [ ] `FFACT_L7_COMPACTOR_ENABLED=0` fallback 正常

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
    "recommended_settings": {"FFACT_L65_WORKERS": 4, "FFACT_CGSA_MEMORY_BUFFER": 0, "FFACT_L7_WORKERS": 4, "FFACT_L7_COMPACTOR_ENABLED": 1}
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
                "FFACT_L7_COMPACTOR_ENABLED": 1,
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
    │            L7_COMPACTOR_ENABLED=1                    │
    └─────────────────────────────────────────────────────┘
    ```
  - 顏色邏輯（Tailwind CSS）：
    - RAM 可用 ≥ 2GB → `text-green-600`；1-2GB → `text-yellow-600`；< 1GB → `text-red-600`
    - 磁碟可用 < 10GB → `text-yellow-600`；< 5GB → `text-red-600`
  - API 呼叫：`const res = await fetch('/api/v1/config/hardware')`
  - State management：`useState` for data + loading + error（不需 Zustand — 局部狀態足夠）
  - 手動重新整理按鈕（不自動輪詢）
  - 建議設定顯示需包含 compactor 狀態，例如 `Compactor=ON` 或第二列顯示 `L7_COMPACTOR_ENABLED=1`
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
      recommended_settings: {
        FFACT_L65_WORKERS: number;
        FFACT_CGSA_MEMORY_BUFFER: number;
        FFACT_L7_WORKERS: number;
        FFACT_L7_COMPACTOR_ENABLED: number;
      };
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
  - `frontend/src/app/feature-factory/page.tsx` → `FeatureFactoryPage()`（引入並嵌入 `HardwareStatusPanel`）
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

## 全局測試與 Gate 索引

### 測試層級

| 層級 | 範圍 | 執行頻率 | 工具 |
|------|------|---------|------|
| 單元測試 | 單一函式或單一 Task | 每個 Task 完成後 | pytest |
| 整合測試 | 跨模組或跨 Task | 每個 Phase | pytest |
| 效能測試 | 端到端速度/RSS 驗收 | 每個 Phase Gate | 自定義 benchmark / pytest |
| 回歸測試 | Golden output / NaN pattern / future leak | 每個 Phase | pytest + golden files |

### 測試檔案結構

```text
tests/
├── test_hardware_utils.py                # Phase 0 — T0.1~T0.4, T0.B1~T0.B3
├── test_cgsa_resume.py                   # Phase 1 — T1.1~T1.4, T1.B1~T1.B5
├── test_l65_parallel.py                  # Phase 2 — T2.1~T2.6, T2.B1~T2.B7
├── test_multi_window_rolling.py          # Phase 3 — T3.1~T3.4, T3.B1~T3.B8
├── test_l7_parallel_persist.py           # Phase 4 — T4.1~T4.5, T4.B1~T4.B7
├── test_hardware_api.py                  # Phase 5 — T5.1~T5.3, T5.B1~T5.B2
├── performance/
│   ├── test_l65_parallel_perf.py         # T2.P1~T2.P2
│   ├── test_multi_window_perf.py         # T3.P1~T3.P2
│   └── test_l7_persist_perf.py           # T4.P1~T4.P2
```

### 測試數量統計

| Phase | 核心 | 邊界 | 效能 | 小計 |
|-------|------|------|------|------|
| Phase 0 | 4 | 3 | 0 | **7** |
| Phase 1 | 4 | 5 | 0 | **9** |
| Phase 2 | 6 | 7 | 2 | **15** |
| Phase 3 | 4 | 8 | 2 | **14** |
| Phase 4 | 5 | 7 | 2 | **14** |
| Phase 5 | 3 | 2 | 0 | **5** |
| **總計** | **26** | **32** | **6** | **64** |

### 共用 Fixture / 合成資料要求

```python
# conftest.py
import numpy as np
import pytest

@pytest.fixture
def sample_feature_array():
  """產生合成 feature 陣列 (1000 rows × 50 cols) for testing."""
  rng = np.random.RandomState(42)
  data = rng.randn(1000, 50).astype(np.float32)
  for column_index in range(50):
    nan_len = rng.randint(0, 200)
    data[:nan_len, column_index] = np.nan
  return data
```

- Phase 2 與 Phase 3 的數值等價測試優先重用共用 fixture，避免每個測試各自生成不同隨機資料
- 需要模擬 registry 時，使用 `tmp_path` 建立臨時 work_dir，確保符合 Rule 6 測試隔離

### Phase Gate 矩陣

| Gate | 條件 | 通過 → | 失敗 → |
|------|------|--------|--------|
| Phase 0 → 1 | T0.x 全通過 + 無 api import | Phase 1 | 修正 Phase 0 |
| Phase 1 → 2 | T1.x 全通過 + Resume 場景驗證 | Phase 2 | 修正 Phase 1 |
| Phase 2 → 3 | T2.x 全通過 + C1~C6 + ≥2× speedup | Phase 3 | 修正 Phase 2 |
| Phase 3 → 4 | T3.x 全通過 + C1~C6 + ≥1.3× speedup | Phase 4 | 修正 Phase 3 |
| Phase 4 → 5 | T4.x 全通過 + C1~C6 + 小檔數受控 | Phase 5 | 修正 Phase 4 |
| Phase 5 → Done | T5.x 全通過 + API 可用 | ✅ 完成 | 修正 Phase 5 |

---

## 風險索引（對應 SPEC §10）

| 風險 ID | 摘要 | 對應 Task |
|---------|------|-----------|
| R1 | `hardware_utils.py` 誤 import `api/` | Task 0.1 |
| R2 | manifest 損壞導致 resume 失敗 | Task 1.3 |
| R3 | L6.5 ThreadPool race condition | Task 2.1, 2.2 |
| R4 | multi-window kernel 數值不穩定 | Task 3.1 |
| R5 | Numba ARM64 / macOS 相容性 | Task 3.1 |
| R6 | L7 平行寫入時磁碟空間不足 | Task 4.1, 4.3 |
| R7 | CGSA buffer 崩潰遺失未 flush 資料 | Task 2.4 |
| R8 | Polars API breaking change（Deferred） | Task 2.5 |
| R9 | 硬體 API 不可用導致前端白屏 | Task 5.1, 5.2 |
| R10 | `psutil` 不可用 | Task 0.1 |
| R11 | 小 chunk / 小 group 導致 Parquet 檔案碎片化與 IOPS 瓶頸 | Task 4.2, 4.3 |
| R12 | L6.5 group 成本差異大造成長尾效應 | Task 2.1 |
| R13 | Numba 多進程冷啟動 storm 導致 CPU/RAM 暴衝 | Task 2.3 |

---

## 環境變數 / Feature Flag 索引

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
| `FFACT_L65_POLARS` | `auto` | 啟用 Polars wide matrix（32GB only） | Deferred |

### 關鍵常數索引

```python
MAX_GROUP_COLUMNS    = 5_000
MAX_L65_GROUP_COLS   = 16_110
L65_GROUP_COUNT      = 708
L65_AVG_S_PER_GROUP  = 3.42
L65_TOTAL_SECONDS    = 2_424
L7_TOTAL_SECONDS     = 467
CGSA_WORK_DIR_BASE   = "data_cache/cgsa_work"

_WORKERS_BY_TIER     = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
_CGSA_BUFFER_BY_TIER = {"8gb": 0, "16gb": 0, "24gb": 32, "32gb": 64}
_L7_WORKERS_BY_TIER  = {"8gb": 4, "16gb": 6, "24gb": 8, "32gb": 8}
_CHUNK_BARS_BY_TIER  = {"8gb": 50_000, "16gb": 100_000, "24gb": 250_000, "32gb": None}
```

---

## 效能預估對照

| 項目 | V7 現況 (8GB) | 8GB 目標 | 24GB 目標 | 32GB 目標 |
|------|-------------|---------|---------|---------|
| Resume fix（崩潰場景） | 重跑 2,424s | resume 剩餘 | resume 剩餘 | resume 剩餘 |
| P0-A L6.5 parallel | 2,424s | ~606s | ~303s | ~303s |
| P0-B CGSA buffer | 2,055s（L2 I/O） | 不變 | ~1,300s | ~1,000s |
| P2-A multi-window kernel | 2,051s（L3） | ~1,400s | ~800s | ~400s |
| P3 L7 parallel | 467s | ~150s | ~100s | ~80s |
| P3-B Async compactor | 724 files | ~150-250 files | ~80-160 files | ~40-120 files |

### 主要瓶頸提醒

- L2、L3、L6.5 仍是總耗時主體，Phase 2 與 Phase 3 的數值等價驗證必須優先於 Phase 4 的 I/O 優化。
- Async compactor 的成功標準不只看時間，也要看最終小檔數是否受控，否則只是把瓶頸往後移。

---

## 參考文件

| 文件 | 用途 |
|------|------|
| `docs/OPTIMIZATION_TODO_PLANNING.md` | 本 TODO / SPEC 的規劃來源 |
| `Pre-opt_vs_V7_Comparison.md` | V7 baseline 效能數據與瓶頸分析 |
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | Phase 2 主要修改檔 |
| `momentum/FeatureEngineering/operators/numba_rolling.py` | Phase 3 Numba kernel |
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | Phase 3 orchestrator |
| `momentum/FeatureEngineering/feature_storage.py` | Phase 4 persist / compactor |
| `momentum/FeatureEngineering/feature_factory.py` | Pipeline 主檔與 CGSA 整合 |
| `api/routes/config.py` | Phase 5 硬體資訊 API |

---

## Agent 執行檢查點

- Phase 2 執行時，確認 `n_columns` 降序提交與 `cache=True`/warmup 已同時落地，不可只做其中一半。
- Phase 4 執行時，`_persist_parts_parallel()`、呼叫端切換與 `AsyncParquetCompactor` 必須一起驗證，避免介面漂移。
- 每個 Phase 完成後都要回到 C1~C6 基礎驗收，不可只跑新增測試編號。
- 若使用 fallback 驗證，需分別驗證 `FFACT_L65_WORKERS=1`、`FFACT_L3_MULTI_WINDOW=0`、`FFACT_L7_COMPACTOR_ENABLED=0` 的舊行為仍可運作。

---

## DEFERRED Tasks（記錄但不執行）

- Deferred 索引：Task 2.5 — Polars Wide Matrix
  詳細說明見 Phase 2 的 Task 2.5；此處僅保留 deferred 索引，方便在 Phase 外快速追蹤。

- Deferred 索引：Task 3.4 — TimeChunkIterator
  詳細說明見 Phase 3 的 Task 3.4；此處僅保留 deferred 索引，方便在 Phase 外快速追蹤。

---

## 明確排除項目（Out of Scope）

| 項目 | 排除理由 |
|------|---------|
| `FFACT_LAYER1_PARALLEL`（L1 平行化） | L1 耗時僅 3.3s（佔總時間 0.04%），ROI 極低 |
| `compression_level` 調整 | 目前 zstd level=1 已是速度優先設定 |
| L1 Kline Data Ingestion 優化 | L1 耗時 3.3s（0.04%），非瓶頸 |
| L4/L5/L6 優化 | L4(22s) + L5(0.6s) + L6(0s) 合計 < 0.3%，非瓶頸 |
