# Feature Factory 效能優化規劃書

> **基於**: FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md  
> **目標**: 方案 M（Hybrid — CGSA + Polars + Numba + searchsorted）  
> **約束**: 不減特徵、不降品質、數值完全等價  
> **執行者**: AI Agent（全自動，含測試）  
> **建立日期**: 2026-04-12  
> **V2 修訂日期**: 2026-04-15  
> **版本**: V2（整合 Review1 + Review2 + Codebase 交叉驗證）  
> **硬體**: MacBook M1 8GB RAM  
> **狀態**: 🔒 FROZEN（2026-04-16 — 完整交叉驗證通過，無新增架構盲點/矛盾/風險）
>
> ### V2 變更摘要
>
> 本版整合以下來源的審查結論：
> - `FEATURE_FACTORY_REVIEW1.md`（架構盲點 / 數據矛盾 / 潛在風險，共 10 節 + A1~C5 修正項）
> - `FEATURE_FACTORY_REVIEW2.md`（交叉驗證 / 信心分級，共 P0×5 + P1×5 + P2×3 優先項）
> - **Codebase 交叉驗證**（對照實際程式碼發現的額外盲點）
>
> **主要變更**：
> 1. §1.1 C1 改為 per-layer atol map（取代單一 atol=1e-6）
> 2. §1.3 Golden 策略強化（三層 baseline + 大記憶體環境完整基準）
> 3. §3.5 Task 1.5 從 OPTIONAL 升級為 **DEFERRED to Phase 5**
> 4. §4 新增 L2 RAM 斷路器、L4/L5/L6 依賴域定義、欄位排序規格、Group 粒度調整、Registry 持久化、config_hash 規範化、A/B 驗證改為逐層比對、downstream contract 定義
> 5. §5 新增 float64 累加器要求、rolling rank 數學語義凍結、現有 L3 streaming 模式說明
> 6. §6 Phase 4 明確 skip 條件與 no-Phase-4 效能預估
> 7. §7 新增 Numba JIT 預熱、ProcessPoolExecutor spawn context
> 8. §10 新增 R15~R25 風險項
> 9. 新增附錄 D: Review 整合追溯表

---

## 目錄

0. [AI Agent 生成規範](#0-ai-agent-生成規範)
1. [全局約束與驗收標準](#1-全局約束與驗收標準)
   - [1.3.1 三層 Baseline 策略](#131-三層-baseline-策略v2-新增)
   - [1.3.2 Golden Output 循環依賴的打破策略](#132-golden-output-循環依賴的打破策略v2-新增)
2. [Phase 0 — 可觀測性基礎建設](#2-phase-0--可觀測性基礎建設)
3. [Phase 1 — searchsorted + Multi-TF 快修](#3-phase-1--searchsorted--multi-tf-快修)
   - [3.5 Task 1.5 — DEFERRED to Phase 5](#35-task-15-multi-tf-平行化--deferred-to-phase-5v2-修訂)
4. [Phase 2 — CGSA 架構規格與實作](#4-phase-2--cgsa-架構規格與實作)
   - [4.2.1 L2 RAM 預算修正與斷路器](#421-l2-ram-預算修正與斷路器v2-新增)
   - [4.2.2 L4 LagProcessor 依賴域定義](#422-l4-lagprocessor-依賴域定義v2-新增--codebase-交叉驗證發現)
   - [4.2.3 L5 Cross-Sectional 依賴域定義](#423-l5-cross-sectional-依賴域定義v2-新增)
   - [4.2.4 L6 Meta Features 跨 Group 依賴解決方案](#424-l6-meta-features-跨-group-依賴解決方案v2-新增)
   - [4.8 Column Ordering 規格](#48-column-ordering-規格v2-新增)
   - [4.9 ColumnGroup 粒度調整](#49-columngroup-粒度調整v2-新增)
   - [4.10 Registry 持久化與斷點續跑](#410-registry-持久化與斷點續跑v2-新增)
   - [4.11 config_hash 正規化](#411-config_hash-正規化v2-新增)
   - [4.12 A/B 驗證修訂](#412-ab-驗證修訂v2-修訂)
   - [4.13 Downstream Contract](#413-downstream-contract-與-materialize_wide_df-處置v2-新增)
   - [4.14 現有優化措施確認](#414-現有優化措施確認v2-新增--codebase-交叉驗證)
5. [Phase 3 — Numba L3 融合 Rolling](#5-phase-3--numba-l3-融合-rolling)
   - [5.0 現有 L3 Streaming 模式說明](#50-現有-l3-streaming-模式說明v2-新增)
6. [Phase 4 — Polars L2 / L6.5（條件性）](#6-phase-4--polars-l2--l65條件性)
   - [6.0 Phase 4 Skip 條件](#60-phase-4-skip-條件v2-新增)
7. [Phase 5 — 生產化](#7-phase-5--生產化)
   - [7.0 Phase 5 前置要求](#70-phase-5-前置要求v2-新增)
8. [Phase Gate 決策矩陣](#8-phase-gate-決策矩陣)
9. [全局測試策略](#9-全局測試策略)
10. [風險登記簿](#10-風險登記簿)（R1~R25）
- [附錄 A: 效能預估對照表](#附錄-a-效能預估對照表)
- [附錄 B: 參考文件](#附錄-b-參考文件)
- [附錄 C: AI Agent 執行清單](#附錄-c-ai-agent-執行清單)
- [附錄 D: Review 整合追溯表](#附錄-d-review-整合追溯表v2-新增)（V2 新增）

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
| C1 | **數值等價**：優化後的 feature 矩陣與 golden output 欄位名稱完全相同、數值等價（per-layer atol，見下表） | Golden output test suite |
| C2 | **不減特徵**：feature_count 不變（453,953 cols for ETHUSDT 2TF） | `assert new_count == golden_count` |
| C3 | **不改 column name**：包含 TF prefix、indicator name、window size 等；**欄位順序須由顯式排序規格決定**（見 §4.8），不依賴 runtime 註冊順序 | `assert sorted(new_cols) == sorted(golden_cols)` + order test |
| C4 | **RAM 峰值 ≤ 6 GB**（8GB 機器留 2GB 給 OS） | `psutil.Process().memory_info().rss` 監控 |
| C5 | **無 future leakage**：align 後 12h 特徵不超前 primary 1h | `TimeframeAligner.validate_no_future_leak()` |
| C6 | **NaN 語義一致**：rolling window 開頭的 NaN pattern 完全相同 | per-column NaN mask comparison |

#### C1 Per-Layer Tolerance Map（V2 新增）

> **動機**（Review1 §6.2, Review2 B7）：不同層的數值穩定性不同，L3 skew/kurt 使用 Pebay online 演算法與 pandas Cython batch 演算法存在 ~1e-4 差異，若統一用 atol=1e-6 會導致全量 golden 比對在 skew/kurt 欄位系統性 FAIL。

| Layer / Operation | atol | rtol | 說明 |
|---|---|---|---|
| L1（TA-Lib） | 1e-7 | 0 | C 函式庫精確計算，不應有差異 |
| L2（四則運算） | 1e-6 | 0 | 浮點四則運算 |
| L3 mean / std / min / max / range | 1e-6 | 0 | Welford / monotonic deque 精度 |
| L3 zscore | 1e-6 | 0 | 由 mean + std 推導 |
| L3 skew / kurt | **1e-4** | 0 | Pebay online 演算法 + float64 累加器 |
| L3 slope | 1e-5 | 0 | cumsum 公式精度 |
| L3 rank | 1e-6 | 0 | sorted buffer pct 精度 |
| L6.5 winsorization | 1e-6 | 0 | clip 操作 |
| L6.5 rank_transform | 1e-6 | 0 | rolling rank pct |
| L6.5 adaptive_zscore | 1e-6 | 0 | (x - mean) / std |
| L6.5 gaussian | 1e-5 | 0 | erfinv 精度 |
| **全量 golden 比對**（C1 預設） | **1e-4** | 0 | 取最寬鬆 layer 的上限，確保不誤報 |

**驗證方式**：golden 比對時，先按 column name 解析 layer + operation，再套用對應 atol。若無法解析，使用預設 atol=1e-4。

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

#### 1.3.1 三層 Baseline 策略（V2 新增）

> **動機**（Review2 A1）：Review1/Review2 一致認為 Golden 驗證策略不足以支撐「全量等價」承諾。Reduced config golden 只覆蓋局部正確性，無法保證 453,953 欄位在重構後不偏移。

**三層 baseline 定義**：

| Tier | 名稱 | 內容 | 建立環境 | 用途 |
|---|---|---|---|---|
| **Tier 1** | Full-Config Structural Baseline | 欄位數、欄位名列表、欄位排序、各層輸出 shape 摘要、NaN 比率摘要 | **大記憶體環境（≥32 GB RAM）** 或雲端機器完整跑出一次 | Phase 2+ 的結構等價驗證 |
| **Tier 2** | Reduced-Config Numeric Baseline | 全數值比對（per-layer atol）、NaN mask 完全比對、邊界條件比對 | 開發機（8 GB）使用 reduced config | Phase 1~3 逐層正確性驗證 |
| **Tier 3** | Per-Layer Golden | L1 / L2 / L3 / L6.5 個別層輸出，逐層比對 | 開發機 + 大記憶體環境互補 | 精確定位哪一層引入偏差 |

**強制要求**：
- **Tier 1 必須在 Phase 0 完成前取得**。若開發機 OOM，必須在大記憶體環境（雲端 VM、同事機器、或 CI 大型 runner）執行一次 full pipeline，取得並存檔 `golden_structural.json`（欄位名列表 + 各層 shape + NaN 率）。此檔案為 **immutable baseline**，不可被後續 Phase 覆蓋。
- Tier 1 不要求全量數值比對（因為 full config 的 parquet 可能超過 20 GB），但**必須取得欄位名稱的完整列表**。
- Phase 2 完成後，CGSA 可在開發機上完整跑出 full config → 此輸出即成為 **new full baseline**，用於驗證 Phase 3/4 的改動。

#### 1.3.2 Golden Output 循環依賴的打破策略（V2 新增）

> **動機**（Review1 §6.1）：要建立 golden 需要現行 pipeline 跑完，但現行 pipeline 的 F 段卡住。

**打破循環的步驟**：
1. **L1 golden 可直接建立**：L1 計算很快（~1s），不涉及 concat/memmap → 用現行 pipeline 在開發機建立
2. **L2/L3 golden 用 reduced config**：減少 data_sources 到 `["close"]`，限制 indicator 數量，使 concat 規模可控（< 6 GB）
3. **Full structural baseline 在大記憶體環境取得**（Tier 1）
4. **Phase 2 完成後**：用 CGSA 跑 full config 產出新的完整 golden → 此後所有 Phase 3/4/5 的驗證都以此為基準
5. **Phase 2 本身的正確性**只能用 per-layer golden + reduced-config numeric golden 驗證（有盲區，但這是可接受的 trade-off）

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

### 3.5 Task 1.5: Multi-TF 平行化 — ⚠️ DEFERRED to Phase 5（V2 修訂）

> **V2 變更**（Review2 A3, Review1 §4.7）：從 OPTIONAL ThreadPoolExecutor 改為 **DEFERRED to Phase 5**，且僅允許 `ProcessPoolExecutor + spawn`。

**原始設計問題**：
1. TA-Lib 為 C 語言擴充套件，**非 thread-safe**（R11）。使用 ThreadPoolExecutor 可能導致 segfault
2. 效益僅 C=37s（佔 ABCDE 的 2.0%），**成本效益完全不合理**
3. macOS 預設 `fork()` 與 TA-Lib C 全域狀態衝突（fork-safety 問題）
4. 併發註冊可能導致欄位順序非決定性

**⚠️ 注意：codebase 中 L1 已有平行模式**（`FFACT_LAYER1_PARALLEL=1` + `FFACT_LAYER1_MAX_WORKERS=4`），使用 ThreadPoolExecutor 平行執行 7+ 個 TA-Lib category engine。此模式同樣有 thread-safety 風險，預設為關閉（`FFACT_LAYER1_PARALLEL=0`）。若啟用，與 Task 1.5 的風險完全相同。

**Phase 5 實作指引**（若屆時需要平行化）：

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# 必須使用 spawn context（避免 fork + TA-Lib 衝突）
mp_ctx = multiprocessing.get_context('spawn')

with ProcessPoolExecutor(
    max_workers=min(len(training_tfs), 4),
    mp_context=mp_ctx,
) as pool:
    futures = {
        pool.submit(_process_single_tf, symbol, tf, config_dict): tf
        for tf in training_tfs
    }
```

**Phase 1 中不可實作任何 Multi-TF 平行化**。
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

#### 4.2.1 L2 RAM 預算修正與斷路器（V2 新增）

> **動機**（Review1 §3.3 + §3.3.1, Review2 B1）：上述 RAM 預算只計入 L1 **輸入**，未計入 L2 **輸出**。L2 產出 48,591 columns（Research §4.4），48,591 cols × 12,888 rows × 4 bytes = **2.5 GB**。若 Stage A 一次性計算所有 cross/ratio，輸出會在 RAM 中直到 `save_data()` 完成。

**修正後的 RAM 預算**：

| 組件 | 大小 | 說明 |
|---|---|---|
| L1 全量（Stage A 輸入） | 87 MB | 保留在 RAM 供跨 indicator 計算 |
| L2 單 category 輸出（最大） | ~500 MB | Distance 類別最多（~12,000 cols） |
| L2 中間結果 + save buffer | ~100 MB | per-group save 後即釋放 |
| **峰值** | **~700 MB** | 使用 per-category 分批模式 |

**關鍵變更：L2 Stage A 改為 per-category 分批計算**：

```python
# ❌ V1 原始設計：一次性計算全部 L2
l2_result = engine.compute_all(l1_df, raw_data, specs)  # → 2.5 GB 峰值

# ✅ V2 修正：per-category 分批 + 逐批 save
for category in ['Distance', 'Cross', 'Ratio', 'Momentum', 'BinarySignal', 'SignedStrength', 'WorldQuant']:
    cat_result = engine.compute_category(l1_df, raw_data, specs, category)
    for group in split_into_groups(cat_result):
        registry.save_data(group, group_data)
    del cat_result  # 立即釋放
```

**斷路器（Circuit Breaker）**：

> **動機**（Review1 §3.3.1）：若 config 設定全排列 Cross/Ratio 組合（1,683 個 L1 指標兩兩配對 → ~7M columns），會遠超 RAM 容量。需要預估保護。

```python
MAX_L2_ESTIMATED_COLS = 100_000  # 斷路器閾值

def _estimate_l2_output_cols(self, l1_col_count: int, config: Dict) -> int:
    """預估 L2 輸出欄位數，用於斷路器判斷。"""
    # ... 根據 config 中的 operator 設定計算預估值 ...

estimated = self._estimate_l2_output_cols(l1_df.shape[1], config)
if estimated > MAX_L2_ESTIMATED_COLS:
    logger.warning("[L2] Estimated output %d cols > threshold %d, forcing per-category chunked mode",
                   estimated, MAX_L2_ESTIMATED_COLS)
    # 強制使用 per-category 分批 + per-group save，避免 OOM
```

#### 4.2.2 L4 LagProcessor 依賴域定義（V2 新增 — Codebase 交叉驗證發現）

> **動機**：Review1/Review2 均未討論 L4 在 CGSA 下的依賴範圍。Codebase 分析發現 `_layer4_lag_features` 有兩條路徑：

```python
# 現行程式碼（feature_factory.py）
if apply_to == "layer1_and_raw":
    base = self._combine_layers([data, layer1], context="layer4_input")  # 快速路徑
else:
    base = self._combine_layers([data, layer1, layer2, layer3], context="layer4_input")  # 完整路徑
```

**CGSA 下的處理方式**：
- **快速路徑（`layer1_and_raw`）**：L4 需要 raw_data + L1 全量 → L1 全量已在 Stage A 保留（87 MB），raw_data 來自 L0（~1 MB）→ 合計 ~88 MB，可接受
- **完整路徑（`all`）**：L4 需要 raw_data + L1 + L2 + L3 全量 → 在 CGSA 下需要從 Registry 讀回所有 L1/L2/L3 group → **等同於 wide-table materialization**
- **建議**：CGSA 下強制 L4 使用 `apply_to="layer1_and_raw"` 快速路徑，避免觸發 wide materialization

**在 Task 2.5 中需加入**：若 config 的 `lag_features.apply_to` 不是 `"layer1_and_raw"`，在 CGSA 模式下發出警告並自動降級為快速路徑。

#### 4.2.3 L5 Cross-Sectional 依賴域定義（V2 新增）

> **動機**（Review2 A2, Review1 §2.1）：L5 需要**跨 symbol** 資料（BTCUSDT reference），與 per-symbol CGSA 架構存在衝突。兩份 Review 一致認為這是系統分層與 orchestration 邊界問題，必須在 Phase 2 前定義。

**Codebase 現狀**（`feature_factory.py` L5 實作）：
- `_layer5_cross_sectional()` 呼叫 `self._layer0_data_ingestion(reference_symbol, timeframe, config)` 取得 BTCUSDT 資料
- 只產出 3 個特徵：`cs_relative_price`, `cs_beta`, `cs_idiosyncratic_momentum`
- 使用 `_reference_data_cache` 快取 reference 資料（instance-level）

**L5 依賴分類（凍結）**：

| 類型 | 定義 | L5 屬於 |
|---|---|---|
| intra-symbol / cross-feature | 同 symbol 不同 feature 計算 | ❌ |
| **inter-symbol / same timestamp** | **同時間戳跨 symbol 計算** | **✅** |
| market-relative / universe-wide | 全市場排名/正規化 | ❌（目前） |

**CGSA 處理方式**：
- L5 的 registry scope 維持 **per-symbol**（L5 輸出歸屬於目標 symbol）
- Reference symbol 資料透過獨立 adapter 讀取，**不需要 reference symbol 的完整 pipeline 結果**（只需 raw close price）
- Phase 5 multi-symbol 時，BTCUSDT raw data 可用 **shared read-only cache**（Arrow IPC 或 Parquet），避免 8 個 worker 各自讀取一次
- L5 在 CGSA per-group streaming 中作為 **獨立 stage**（不在 per-group 迴圈內），在 L1/L2 完成後、L7 persist 前執行
- L5 的 3 個輸出 column 組成一個獨立 ColumnGroup（`{tf}_cross_sectional_relative_strength_close`）

#### 4.2.4 L6 Meta Features 跨 Group 依賴解決方案（V2 新增）

> **動機**（Review1 §2.2, Review2 B2）：L6 的 consensus/interaction 引擎使用 `_find_column()` 模糊匹配 L1 欄位名（如 EMA_8, RSI_14, ATR_14），需要同時存取來自不同 indicator engine 的 columns。

**Codebase 現狀**（`consensus_features.py`, `interaction_features.py`）：
- `ConsensusFeatureEngine.compute_trend_consensus()` 需要：EMA_8 (trend), EMA_21 (trend), MACD_Hist (trend), ADX_14 (trend) — 全部來自 trend 類別
- `InteractionFeatureEngine.compute_all()` 需要：EMA_8 (trend) × RSI_14 (momentum) × ATR_14 (volatility) — **跨類別**
- `_find_column()` 做 fuzzy matching：先精確匹配，後子字串匹配 → **需要全 L1 DataFrame 的欄位列表**

**CGSA 處理方式（仿 L2 Stage A/B）**：

```
L6 Stage A: 從 Registry 讀取 L6 需要的 L1 columns（~10 個已知 columns，非全量）
  → 使用 manifest 中的 column name 做精確匹配
  → 只讀取包含目標 column 的 group（通常 3~5 個 group）
  → 合計 RAM: ~5 MB
  → 計算 consensus / interaction / time features → 產出 L6 group

L6 Stage B: L6 group save_data() 到 disk
  → 釋放 Stage A 讀取的 L1 subset
```

**⚠️ `_find_column` 的 fuzzy matching 風險**：在 CGSA 下，若 column 命名格式改變（如加入 group_id prefix），fuzzy matching 可能失敗。建議 L6 改為**顯式 column 引用**（從 Registry 按 indicator name + category 查詢），而非全 DataFrame 模糊搜尋。

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

**⚠️ L6.5 操作完整列表與 per-group 相容性確認（V2 補充）**：

> **動機**（Review1 §4.6）：Plan V1 未窮盡列舉 L6.5 所有操作的 per-group 相容性。

| 操作 | Scope | Per-Group 相容 | 說明 |
|---|---|---|---|
| winsorization（sigma/quantile） | per-column（需整列 mean/std/percentile） | ✅ | per-group 每列仍有完整 12,888 rows |
| rank_transform | per-column（rolling rank on same column） | ✅ | 同上 |
| adaptive_zscore | per-column（(x - mean) / std） | ✅ | 同上 |
| gaussian_normalize | per-column（erfinv 轉換） | ✅ | 同上 |
| adf_differencing | per-column（ADF 檢定 + diff） | ✅ | 同上 |
| fractional_differencing | per-column（FFD 權重） | ✅ | 同上 |
| **cross-feature rank**（假設性） | per-row（同 row 所有 features 排名） | **❌** | 目前 L6.5 **未實作** cross-feature rank。若未來新增，需跳出 per-group 模式 |

**結論**：現行 L6.5 的 6 種操作均為 per-column，per-group 完全相容。在新增 L6.5 操作前，須先檢查是否為 per-column scope。

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

### 4.8 Column Ordering 規格（V2 新增）

> **動機**（Review2 B3, Review1 §2.4）：V1 SPEC 用 `set(new_cols) == set(golden_cols)` 做欄位名比對，但未定義欄位**順序**。若順序不一致，後續 IC Analysis / ML Training 的特徵 index 可能不穩定，導致 XGBoost 的 feature_importances_ 映射錯誤。

**定義：Canonical Column Order**

```
排序鍵（優先序，由高到低）：
  1. timeframe（primary first, then training TFs by period ascending: 1h → 4h → 12h → 1d）
  2. layer（L1 → L2 → L3 → L4 → L5 → L6 → L6.5）
  3. category（alphabetical: entropy → microstructure → momentum → tail_risk → trend → volatility → volume）
  4. indicator（alphabetical within category: ADX → ATR → BBANDS → ...）
  5. source（alphabetical: close → high → low → open → volume）
  6. window（ascending: 5 → 8 → 13 → 21 → ...）
  7. aggregator（alphabetical: kurt → max → mean → min → range → rank → skew → slope → std → zscore）
```

**實作方式**：
- Registry 的 `all_column_names()` 方法須按上述排序鍵排序
- persist 階段的 manifest.json `groups` 陣列按 group_id 排序（group_id 本身由排序鍵組成）
- `materialize_wide_df()` 的 column 順序 = canonical order
- Label columns（以 `label_` prefix 開頭）固定排在最後

**Golden 比對時**：
```python
# V1: assert set(new_cols) == set(golden_cols)  # 順序不敏感
# V2: 雙重比對
assert set(new_cols) == set(golden_cols)  # 先確認名稱集合相同
assert list(new_cols) == list(golden_cols)  # 再確認順序完全一致
```

### 4.9 ColumnGroup 粒度調整（V2 新增）

> **動機**（Review1 §7.1, Review2 B5）：V1 設計中 group_id 為 `{tf}_{category}_{indicator}_{source}_{agg}_{window}`，預估 ~33,600 groups（L3 以上）。過細粒度導致：
> 1. .npy 中介檔案數量爆炸（~36,000+ 檔案，含 I/O overhead）
> 2. DuckDB 讀取時 Parquet footer scan 累計開銷（R19）
> 3. Manifest JSON 體積過大

**調整：提升粒度為 indicator level**

| Layer | Group 粒度 | Group 命名 | 預估 Group 數 |
|---|---|---|---|
| L1 | per-indicator (all sources) | `{tf}_L1_{category}_{indicator}` | ~200 |
| L2 | per-category | `{tf}_L2_{operator}` | ~14 |
| L3 | per-L1-indicator (all windows × all aggs) | `{tf}_L3_{category}_{indicator}_{source}` | ~800 |
| L4 | per-L1-indicator (all lags) | `{tf}_L4_{category}_{indicator}_{source}` | ~200 |
| L5 | single group | `{tf}_L5_cross_sectional` | 2（1h + 12h）|
| L6 | per-engine | `{tf}_L6_{engine}` | ~6 |
| **合計** | | | **~1,200** |

**效果**：
- .npy 檔案數：~33,600 → ~1,200（降低 28×）
- 單 group columns 數：10 cols → ~30~100 cols（仍在 per-group 記憶體預算內）
- Parquet 檔案數：~1,200（DuckDB 可高效處理）
- Manifest JSON：從 ~50 MB 降到 ~5 MB

**替代中介格式**：若 .npy 的 I/O 開銷仍顯著，考慮 Arrow IPC（`.arrow`）作為中介格式：
- Arrow IPC 支援 columnar + metadata + 零複製讀取
- 可直接被 DuckDB 和 Polars 讀取
- 權衡：多一個依賴（pyarrow），但通常已安裝

### 4.10 Registry 持久化與斷點續跑（V2 新增）

> **動機**（Review1 §7.2）：若 pipeline 在 L3 第 500 個 group 崩潰，需要從頭重跑所有 L1/L2/L3。Registry 應支援 incremental checkpoint。

**方案**：

```python
class ColumnGroupRegistry:
    def save_data(self, group: ColumnGroup, data: np.ndarray):
        """Save group data to disk and update manifest incrementally."""
        # 1. Write .npy / .arrow
        path = self._work_dir / f"{group.group_id}.npy"
        np.save(path, data)
        
        # 2. Update in-memory registry
        self._groups[group.group_id] = group
        
        # 3. Incremental manifest write（每次 save 都更新）
        self._write_manifest()  # atomic write via temp + rename
    
    def _write_manifest(self):
        """Atomic manifest write using temp file + os.rename."""
        tmp = self._work_dir / "manifest.json.tmp"
        with open(tmp, 'w') as f:
            json.dump(self._to_manifest_dict(), f, indent=2)
        os.replace(tmp, self._work_dir / "manifest.json")  # atomic on POSIX
    
    @classmethod
    def resume_from_manifest(cls, work_dir: Path) -> 'ColumnGroupRegistry':
        """Resume from existing manifest.json — load all registered groups."""
        manifest = json.load(open(work_dir / "manifest.json"))
        registry = cls(work_dir=work_dir)
        for g in manifest['groups']:
            # 驗證 .npy 檔案存在
            if (work_dir / g['npy_path']).exists():
                registry._register_from_manifest(g)
            else:
                logger.warning("[Registry] Missing file for group %s, will recompute", g['group_id'])
        return registry
```

**斷點續跑邏輯**：
- pipeline 開始前，檢查 `manifest.json` 是否存在
- 若存在 → `resume_from_manifest()` → 跳過已完成的 groups
- 若不存在 → 全新開始
- 每個 layer 開始前，比對 manifest 已有的 groups vs 需要計算的 groups → 差集即為需計算的

### 4.11 config_hash 正規化（V2 新增）

> **動機**（Review1 §2.3）：config_hash 用於儲存路徑和 manifest 識別，但 Python dict 的 key 順序可能不一致（Python 3.7+ 保證插入順序，但不保證跨版本或不同建構方式的順序一致性）。

**規範**：

```python
import hashlib
import json

def compute_config_hash(config: dict) -> str:
    """Canonical config hash: sorted keys + deterministic JSON + SHA256."""
    canonical_json = json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()[:12]
```

**額外要求**：
- manifest.json 中**同時存放 config_hash 和完整 config snapshot**（便於事後驗證）
- config 變更 → config_hash 變更 → 產出到新目錄（不覆蓋舊結果）
- config 中排除非影響結果的欄位（如 `log_level`, `n_jobs`）→ 在計算 hash 前 strip 這些 keys

### 4.12 A/B 驗證修訂（V2 修訂）

> **動機**（Review1 §3.5, Review2 A1）：V1 的 A/B 驗證要求「新舊 pipeline 都跑一次 ETHUSDT full config」，但現行 pipeline 的 F 段 OOM 無法完成。驗證陷入死鎖。

**修訂方案：逐層 Golden 比對（取代全量 A/B）**

| 比對層級 | 方法 | 基準來源 |
|---|---|---|
| L1 output | `np.allclose(cgsa_l1, legacy_l1, atol=1e-7, equal_nan=True)` | 現行 pipeline L1 golden（可在 8 GB 機器建立） |
| L2 output | `np.allclose(..., atol=1e-6)` per-category | Reduced-config 下現行 pipeline L2 output |
| L3 output | per-aggregator atol（見 C1 tolerance map） | Reduced-config golden |
| Full structure | column names list + count + NaN 率 | **Tier 1 Structural Baseline**（大記憶體環境） |
| Final numeric | 全量 atol（C1 預設 1e-4） | Phase 2 完成後用 CGSA 跑出的 full-config baseline |

**Phase 2 A/B 驗證不再要求現行 pipeline 完成 full-config run。**

### 4.13 Downstream Contract 與 materialize_wide_df 處置（V2 新增）

> **動機**（Review2 A5）：CGSA 的核心價值是消除 wide-table，但現行所有下游消費者（IC Analysis, ML Training, SHAP, Export）都假設接收 wide DataFrame。必須定義過渡策略。

**新 Downstream Interface**：

```python
class IFeatureProvider(Protocol):
    """V2.0 feature access protocol — per-group or streaming."""
    
    def get_group(self, group_id: str) -> pd.DataFrame:
        """讀取單一 ColumnGroup。"""
        ...
    
    def iter_groups(self, layer: Optional[str] = None) -> Iterator[Tuple[str, pd.DataFrame]]:
        """迭代所有 ColumnGroups（可按 layer 過濾）。"""
        ...
    
    def get_column_names(self) -> List[str]:
        """取得 canonical ordered column names。"""
        ...
    
    def materialize_wide_df(self) -> pd.DataFrame:
        """
        ⚠️ DEPRECATED — 僅用於向後相容和 debug。
        會在 RAM 中建構完整 wide DataFrame。
        Production 使用者應遷移到 get_group() / iter_groups()。
        """
        ...
```

**遷移計畫**：
1. Phase 2 期間：所有下游模組**繼續使用** `materialize_wide_df()`（確保功能不中斷）
2. Phase 2 完成後：逐步重構下游為 per-group 消費（IC Analysis, ML Training 優先）
3. `materialize_wide_df()` 加上 `@deprecated` decorator + RAM 估算 warning log
4. 最終 Phase 5 時刪除 wide materialization（或僅在 debug 模式保留）

### 4.14 現有優化措施確認（V2 新增 — Codebase 交叉驗證）

> **動機**：Codebase 中已存在多項 streaming / chunking 優化，SPEC 不應忽略這些既有能力。CGSA 應與這些機制整合而非重複建構。

| 既有機制 | 所在程式碼 | 與 CGSA 的關係 |
|---|---|---|
| **L1 平行**（`FFACT_LAYER1_PARALLEL`） | `feature_factory.py` | ThreadPoolExecutor — 有 TA-Lib 安全性風險（R21），CGSA 下保持預設關閉 |
| **L3 Streaming**（`FFACT_L3_STREAMING`） | `rolling_aggregator.py` | Per-column streaming + variance_filter + memmap 輸出 — CGSA 的 per-group 模式可直接復用此路徑 |
| **L4 快速路徑**（`apply_to == "layer1_and_raw"`） | `feature_factory.py` | 避免 2 分鐘 memmap copy — CGSA 下強制使用此路徑（§4.2.2） |
| **L6.5 Chunking**（`FFACT_L65_CHUNK_SIZE`） | `feature_preprocessor.py` | Per-chunk + memmap — CGSA per-group 模式取代 chunking（per-group 即為天然 chunk） |
| **concat_with_memmap** | `memmap_utils.py` | 大量 concat 時改用 memmap — CGSA 消除 global concat 後，此函式僅在 `materialize_wide_df()` 中使用 |
| **MultiTFGenerator._combine_layers** | `multi_tf_generator.py` | 靜態方法，呼叫 `concat_with_memmap` — **需要同步修改為 CGSA Registry-based 整合** |

**⚠️ 重要**：`MultiTFGenerator._combine_layers()` 是 `FeatureFactory._combine_layers()` 之外的**獨立程式碼路徑**。CGSA Task 2.5 修改 `_combine_layers` 時，必須同時處理 `multi_tf_generator.py` 中的 `_combine_layers` 靜態方法。

---

## 5. Phase 3 — Numba L3 融合 Rolling

**目標**: L3 掃描次數 100N → 1N  
**預計效果**: A4 385s → ~60s  
**風險**: 中等（數值穩定性）

### 5.0 現有 L3 Streaming 模式說明（V2 新增）

> **動機**（Codebase 交叉驗證）：`RollingAggregator` 已實作 streaming 模式（`FFACT_L3_STREAMING=1`），包含 variance_filter、base_cache per window、vectorized slope、memmap 輸出。Phase 3 Numba 方案是在此基礎上的**進一步優化**，不是從零開始。

**現有 streaming 模式特性**：
- Per-column 迴圈（避免全量 expand）
- `variance_filter`：移除低 variance 特徵（減少無效計算）
- 每個 window 的 base stats（mean/std）有 cache
- Slope 使用 vectorized cumsum 公式
- 大量結果使用 memmap 輸出

**Phase 3 在此基礎上的增量改進**：
1. 將 per-column pandas rolling 替換為 Numba single-pass fused rolling（10 aggs 一次掃描）
2. 用 float64 累加器 + Welford/Pebay 演算法取代 pandas 內部的 Cython 計算
3. 維持 streaming 模式的 variance_filter + memmap 輸出

**⚠️ variance_filter 與 Golden 的互動**（V2 新增）：
- variance_filter 移除的特徵可能因 float32/float64 差異或 CGSA 計算順序不同而有微小變化
- **決定性保證**：variance 閾值必須為固定值（不使用百分位或動態閾值），確保同一輸入資料的過濾結果相同
- Golden 比對時，先比較 variance_filter 保留的 column set → 若不同，須 log 差異並使用交集做數值比對

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

> **V2 強調**（Review1 §4.3.1）：float64 累加器是 **硬性要求**，不可使用 float32。Numba `@njit` 函式的所有 internal state（count, mean, M2, S3, S4）必須宣告為 `float64`。最終輸出時再 `astype(np.float32)` 寫入 ColumnGroup。
>
> 若使用 float32 累加器，Welford 在 W=233 時的 catastrophic cancellation 可能使 std 誤差達 ~1e-2 級別（Research §15.1）。

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

> **V2 數學語義凍結**（Review2 A4）：rolling rank 的精確定義必須在 Phase 3 開始前凍結，因為 `bisect_left` 和 `pandas rank(pct=True, method='average')` 對 ties 的處理不同。

**凍結的數學定義**：
```
rolling_rank(x, window=W) at position i:
  buf = sorted([x[j] for j in range(i-W+1, i+1) if not isnan(x[j])])
  count = len(buf)
  if count < min_periods:
    return NaN
  
  # Tie handling: average method（等同 pandas default）
  # 若 x[i] 出現 k 次，rank = (first_pos + last_pos) / 2 + 1
  lo = bisect_left(buf, x[i])   # first position of x[i]
  hi = bisect_right(buf, x[i])  # position after last x[i]
  rank = (lo + hi - 1) / 2 + 1  # 1-based average rank
  
  pct = rank / count  # percentile rank
  return pct
```

**邊界情況（凍結）**：
| 情況 | 結果 | 說明 |
|---|---|---|
| Window 全 NaN | NaN | count=0 < min_periods |
| Window 全同值 | 0.5 | average of [1, 1, ..., 1] / count |
| Window=1, 唯一非 NaN | 1.0 | rank 1 / count 1 |
| 極大值出現在 sorted 最後 | ~1.0 | (count-1+count)/2/count |

**atol 驗證**: `np.allclose(numba_rank, pd.rolling(W).apply(lambda x: x.rank(pct=True).iloc[-1]), atol=1e-6)`

```python
# 維護一個 sorted array of size W
# 新值加入：bisect_insort → O(W) shift
# 舊值移除：bisect_left → O(W) shift
# Rank = (bisect_left + bisect_right - 1) / 2 / count  # average tie method
# 總複雜度：O(N·W) — 比 pandas rolling.rank O(N·W·log(W)) 快
```

#### 5.2.4 Pebay Online Skew/Kurt（float64 累加器 + 定期校正）

> **V2 強化**（Review1 §4.3.1）：Pebay online 的 S3/S4 累加器在長序列（N >> W）中因 catastrophic cancellation 可能累積誤差。定期校正是**必要的**，不是 nice-to-have。

```
定期校正策略：
  recalc_interval = min(W, 50)  # 每 min(W, 50) 步從 ring buffer 重新計算
  
  for i in range(N):
    # Online update
    _pebay_update(...)
    
    if (i + 1) % recalc_interval == 0:
      # 從 ring buffer 的原始值重新計算 S2, S3, S4
      buf = ring_buffer[valid_start:valid_end]
      count, mean, M2, M3, M4 = _batch_compute(buf)  # Exact batch computation
      # 覆蓋 online state
```

**校正成本**：O(W) per `recalc_interval` steps = amortized O(W / recalc_interval) = O(1~5) per step。
**精度保證**：校正後 skew/kurt 與 batch 計算的差異必須 < 1e-6（若不滿足，說明 ring buffer 有 bug）。

**⚠️ Numba ARM64/macOS 相容性**（R16）：
- Numba 在 Apple Silicon（M1/M2）的 ARM64 backend 可能有 JIT 編譯差異
- 必須在開發機上跑完全量測試（T3.1~T3.B13）後才視為 Phase 3 完成
- 版本釘選：`numba>=0.57,<0.60`（已知穩定版本範圍）

**⚠️ Numba skew/kurt zero-variance guard**（R17）：
```python
@numba.njit
def _compute_skew(M2, M3, count):
    if count < 3 or M2 < 1e-30:  # epsilon guard for zero-variance
        return np.nan
    return (count * np.sqrt(count - 1) / (count - 2)) * (M3 / M2 ** 1.5)
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

#### 6.0 Phase 4 Skip 條件（V2 新增）

> **動機**（Review1 §3.2）：Research §16.2 將 Phase 4 設為「條件性」，但未定義明確的 skip 條件。若 Phase 3 完成後整體已達目標（< 7 min/sym），Phase 4 的 Polars 遷移**成本效益不合理**（引入 Polars 依賴、NaN/null 語義差異、版本鎖定風險）。

**明確 Skip 條件**：
```
IF (Phase 3 完成後 profile 結果)
   L2_time + L6.5_time < 0.30 × total_pipeline_time
THEN
   SKIP Phase 4 → 直接進入 Phase 5
```

**No-Phase-4 效能預估**：
- Phase 1 (searchsorted): B2+D 454s → ~50s（省 ~400s）
- Phase 2 (CGSA): F 8,365s → ~0s（消除 memmap page thrashing）
- Phase 3 (Numba): A4 385s → ~60s（省 ~325s）
- **Total without Phase 4**: ~7 min/sym（可接受的 research platform 效能）
- 若仍需更快 → 推進 Phase 4 或 Phase 5 multi-symbol parallelism

**Polars 版本鎖定風險**（R25）：Polars API 在 major 版本間有重大 breaking changes（如 `pl.Expr` API 變更）。若推進 Phase 4，須釘選版本：`polars>=0.20,<0.21`。

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

### 7.0 Phase 5 前置要求（V2 新增）

> **動機**（Review1 §4.3, §4.7）：Phase 5 引入多進程平行，有多項 Numba + TA-Lib 相關風險需事先處理。

#### 7.0.1 Numba JIT 預熱

**問題**：Numba `@njit` 函式的首次呼叫會觸發 JIT 編譯（~3-10s per function）。若 8 個 worker 同時啟動，各自編譯相同函式，會導致：
1. CPU spike（8 × compilation）
2. 可能的快取競爭（Numba cache dir 寫入衝突）

**解法**：
```python
def warmup_numba_cache():
    """在啟動 worker pool 前，main process 先呼叫一次所有 @njit 函式。"""
    dummy = np.random.randn(100).astype(np.float32)
    fused_rolling_stats(dummy, window=5)  # 觸發 JIT 編譯 → 寫入 __pycache__
    # ... 其他 @njit 函式 ...

# main process 中：
warmup_numba_cache()  # 先預熱

mp_ctx = multiprocessing.get_context('spawn')
with ProcessPoolExecutor(max_workers=8, mp_context=mp_ctx) as pool:
    # Workers 從 __pycache__ 載入已編譯的函式（不重複編譯）
    futures = [pool.submit(process_symbol, sym) for sym in symbols]
```

#### 7.0.2 ProcessPoolExecutor 強制 spawn context

**問題**：macOS 預設 `fork()` + TA-Lib C 全域狀態 → segfault。
**要求**：**所有 Phase 5 多進程必須使用 `multiprocessing.get_context('spawn')`**。

```python
# ❌ 禁止
with ProcessPoolExecutor(max_workers=8) as pool:  # macOS 預設 fork

# ✅ 必須
mp_ctx = multiprocessing.get_context('spawn')
with ProcessPoolExecutor(max_workers=8, mp_context=mp_ctx) as pool:
```

#### 7.0.3 Reference Data 共享快取（V2 新增 — Codebase 交叉驗證）

> **動機**：L5 的 `_reference_data_cache` 是 instance-level（per-FeatureFactory）。Phase 5 多進程中，8 個 worker 各自建立 FeatureFactory 實例，各自讀取 BTCUSDT reference data → 8 次重複 I/O。

**解法**：
- 在 main process 中預先讀取 BTCUSDT reference data
- 序列化為 Arrow IPC 或 Parquet 到 shared temp path
- Workers 透過 read-only mmap 或 Arrow IPC 讀取（零複製）

```python
# Main process
btcusdt_ref = load_reference_data("BTCUSDT", timeframe, config)
ref_path = work_dir / "shared_ref_BTCUSDT.arrow"
btcusdt_ref.to_feather(ref_path)  # Arrow IPC format

# Worker process（process_symbol 內）
ref_data = pd.read_feather(ref_path)  # OS page cache → 實質零複製
```

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
| re-profile 完成 | **僅當 L2_time + L6.5_time > 0.30 × total_pipeline_time 時才推進 Phase 4** |
| No-Phase-4 效能是否可接受 | 若 total < 7 min/sym → SKIP Phase 4 → 直接到 Phase 5 |
| 否則 → 跳到 Phase 5 | Phase 4 為條件性，不跳過需要明確 profiling 數據支撐 |

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
| **R15** | **.npy 中介檔案爆炸**：33,600+ groups → 33,600+ .npy 檔（V1 粒度） | I/O overhead、inode 耗盡 | 中 | §4.9 粒度調整 → ~1,200 groups；persist 後立即刪除 .npy |
| **R16** | **Numba ARM64/macOS JIT 相容性**：Apple Silicon 的 LLVM backend 可能有 JIT 差異 | Phase 3 數值不穩定或 compile error | 低 | 版本釘選 `numba>=0.57,<0.60`；CI/CD 加入 ARM64 runner；Phase 3 完成前必須在開發機全量測試通過 |
| **R17** | **Numba skew/kurt zero-variance divide-by-zero**：全常數序列的 M2≈0 → skew/kurt 除零 | NaN 或 inf 汙染 | 中 | float64 累加器 + epsilon guard（M2 < 1e-30 → NaN）；T3.B2 全常數邊界測試 |
| **R18** | **L2 O(N²) 組合爆炸**：若 config 開啟全排列 Cross/Ratio → 1,683² ≈ 2.8M columns | RAM 爆炸、pipeline 卡死 | 低 | §4.2.1 斷路器 MAX_L2_ESTIMATED_COLS=100,000；超過閾值自動降級為 per-category 分批 |
| **R19** | **DuckDB Parquet footer scan overhead**：V1 粒度 33,600 Parquet files 的 footer scan | 下游讀取慢 | 中 | §4.9 粒度調整 → ~1,200 files；或合併為 category-level Parquet |
| **R20** | **Phase 5 磁碟 I/O 未建模**：100 symbol × per-group I/O，磁碟可能成為新瓶頸 | 實際效能遠差於預估 | 中 | Phase 5 啟動前做 2-symbol pilot benchmark，量測磁碟吞吐；若 I/O bound → 考慮 SSD RAID 或 Arrow IPC |
| **R21** | **現有 L1 ThreadPool + TA-Lib 安全風險**：`FFACT_LAYER1_PARALLEL=1` 使用 ThreadPoolExecutor | segfault 或結果錯誤（與 R11 同類） | 中 | 預設關閉（`FFACT_LAYER1_PARALLEL=0`）；Phase 5 才啟用，且改用 ProcessPoolExecutor + spawn |
| **R22** | **L6 `_find_column` fuzzy matching 在 CGSA 下失敗**：欄位重命名或 group_id prefix 改變 column name pattern | L6 meta features 產出 0 個特徵 | 中 | §4.2.4 建議改為顯式 column 引用（從 manifest 查詢）；增加 L6 output column count 的 sanity check |
| **R23** | **L3 variance_filter 非決定性**：float32/64 精度差異可能導致不同特徵被過濾 | Golden 比對 column count 不一致（C2 fail） | 低 | 固定 variance 閾值（不用百分位）；Golden 比對先比 column set，再用交集做數值比對 |
| **R24** | **MultiTFGenerator._combine_layers 獨立程式碼路徑未被 CGSA 覆蓋** | Phase 2 遺漏此路徑 → 仍觸發 wide concat | 中 | §4.14 明確標記；Task 2.5 必須同時修改兩處 _combine_layers |
| **R25** | **Polars 版本鎖定風險（Phase 4）**：Polars API 跨 major 版本有 breaking changes | Phase 4 程式碼在 Polars 升級後失效 | 低 | 版本釘選 `polars>=0.20,<0.21`；Phase 4 為條件性，可能 skip |

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
  □ 1.5  ~~(OPTIONAL) Multi-TF 平行化~~ → **DEFERRED to Phase 5**（V2 修訂）

Phase 2:
  □ 2.1  建立 ColumnGroup dataclass
  □ 2.2  建立 ColumnGroupRegistry（含 incremental manifest + resume）
  □ 2.3  L1 per-indicator output
  □ 2.4  L2 兩階段計算（per-category 分批 + 斷路器）
  □ 2.5  _combine_layers registry-based（**含 MultiTFGenerator._combine_layers**）
  □ 2.6  Multi-TF column tagging via group_id
  □ 2.7  L6.5 per-group
  □ 2.8  Persist per-group Parquet
  □ 2.9  manifest.json（含 config_hash 正規化 + 完整 config snapshot）
  □ 2.10 L7 per-group validate
  □ 2.11 materialize_wide_df() 向後相容（@deprecated + RAM warning）
  □ 2.12 逐層 Golden 比對（V2 修訂：取代全量 A/B）
  □      L4 快速路徑強制（§4.2.2）
  □      L5 依賴域定義驗證（§4.2.3）
  □      L6 Stage A/B 驗證（§4.2.4）
  □      Column Ordering 驗證（§4.8）
  □      跑 T2.1~T2.17 + T2.B1~T2.B9
  □      Phase Gate 2→3 檢查

Phase 3:
  □ 3.1  fused_rolling_stats (mean/std/min/max/range/zscore) — **float64 累加器**
  □ 3.2  online skew/kurt (Pebay) — **定期校正 + epsilon guard**
  □ 3.3  rolling rank (sorted buffer) — **average tie method 凍結**
  □ 3.4  slope (running sums)
  □ 3.5  整合到 RollingAggregator（維持現有 streaming 模式架構）
  □ 3.6  跑 T3.1~T3.12 + T3.B1~T3.B13 + T3.P1~T3.P2
  □      Phase Gate 3→4 檢查（re-profile：L2+L6.5 > 30% total → Phase 4，否則 skip）

Phase 4 (條件性 — 可 skip):
  □ 4.1~4.4  Polars L2/L6.5 改寫（版本釘選 polars>=0.20,<0.21）
  □          跑 T4.1~T4.4 + T4.B1~T4.B3

Phase 5:
  □ 5.0  Numba JIT 預熱 + ProcessPoolExecutor spawn context
  □ 5.0  Reference data 共享快取（BTCUSDT → Arrow IPC）
  □ 5.1~5.3  生產化（multi-symbol, Arrow IPC, DuckDB）
  □          跑 T5.1~T5.3 + T5.B1~T5.B3
  □          最終全量 golden 驗證
```

---

## 附錄 D: Review 整合追溯表（V2 新增）

> 本表追溯 Review1 + Review2 的每一個發現項在 SPEC V2 中的處理方式。

### D.1 Review2 P0 項（實作前必須解決）

| Review2 項 | 原始描述 | SPEC V2 處置 | 對應 SPEC 章節 |
|---|---|---|---|
| **A1** | Golden 驗證策略不足 | 三層 Baseline 策略 + 大記憶體環境 Tier 1 + 循環依賴打破 | §1.3.1, §1.3.2 |
| **A2** | L5 cross-sectional 與 per-symbol CGSA 衝突 | L5 依賴域凍結定義 + 獨立 stage + Phase 5 共享快取 | §4.2.3 |
| **A3** | Task 1.5 ThreadPool + TA-Lib 不安全 | DEFERRED to Phase 5 + ProcessPoolExecutor + spawn | §3.5 |
| **A4** | Rolling rank 數學語義未凍結 | Frozen 定義（average tie method + bisect_left/right + 邊界表） | §5.2.3 |
| **A5** | Downstream contract 未重寫（materialize_wide_df 仍存在） | IFeatureProvider Protocol + 遷移計畫 + @deprecated | §4.13 |

### D.2 Review2 P1 項（Phase 2 前必須解決）

| Review2 項 | 原始描述 | SPEC V2 處置 | 對應 SPEC 章節 |
|---|---|---|---|
| **B1** | L2 output RAM 低估（未計 2.5GB 輸出） | Per-category 分批 + 斷路器 | §4.2.1 |
| **B2** | L6 meta cross-group 依賴未定義 | L6 Stage A/B + _find_column 風險說明 | §4.2.4 |
| **B3** | Column ordering 不穩定 | Canonical Column Order 定義（7-key 排序） | §4.8 |
| **B4** | searchsorted 為過渡方案（Phase 2 CGSA 後可能不需要） | 維持 Phase 1 實作；Phase 2 後 searchsorted 用於 non-primary TF → 仍有價值 | §3 無修改（已標記 transitional） |
| **B5** | 小檔案治理（Group 粒度過細） | Group 粒度從 ~33,600 提升到 ~1,200 | §4.9 |
| **B7** | Per-layer atol 需要分層定義 | C1 Tolerance Map（12 個操作各有 atol） | §1.1 C1 |

### D.3 Review1 獨有發現（Review2 未覆蓋）

| Review1 項 | 原始描述 | SPEC V2 處置 | 對應 SPEC 章節 |
|---|---|---|---|
| **§2.3** | config_hash 正規化不足 | Canonical JSON + SHA256 + 完整 config snapshot | §4.11 |
| **§4.6** | L6.5 操作的 per-group 相容性未窮盡列舉 | 6 種操作完整列表 + cross-feature rank 不相容注記 | §4.3 |
| **§7.1** | Group 粒度過細（~33,600 groups） | 同 Review2 B5 | §4.9 |
| **§7.2** | Registry 不支援斷點續跑 | Incremental manifest + resume_from_manifest() | §4.10 |
| **§4.3** | Numba JIT cold start 在 Phase 5 多 worker 場景 | JIT 預熱方案 + spawn context | §7.0.1, §7.0.2 |
| **§4.3.1** | float64 累加器硬性要求 | 加強語氣 + epsilon guard + 定期校正策略 | §5.2.1, §5.2.4 |
| **§3.2** | Phase 4 skip 條件未定義 | 30% 閾值 + No-Phase-4 效能預估 | §6.0 |
| **§3.5** | A/B 驗證死鎖（現行 pipeline OOM 無法完成） | 逐層 Golden 比對 + Tier 1 structural baseline | §4.12 |

### D.4 Codebase 交叉驗證獨有發現（兩份 Review 均未覆蓋）

| 發現 | 描述 | SPEC V2 處置 | 對應 SPEC 章節 |
|---|---|---|---|
| **CB-1** | L4 有兩條路徑（快速 / 完整），完整路徑在 CGSA 下等同 wide materialization | CGSA 下強制 L4 快速路徑 | §4.2.2 |
| **CB-2** | L3 已有 streaming 模式（`FFACT_L3_STREAMING`） | Phase 3 定位為增量改進（非從零開始） | §5.0 |
| **CB-3** | L1 已有 ThreadPool 平行（`FFACT_LAYER1_PARALLEL`），與 Task 1.5 同類風險 | 加入 R21 風險；預設關閉直到 Phase 5 | §3.5 注意, R21 |
| **CB-4** | L4 已有快速路徑優化（`apply_to == "layer1_and_raw"` 避免 2min memmap copy） | 確認既有優化，CGSA 整合 | §4.14 |
| **CB-5** | `MultiTFGenerator._combine_layers()` 是獨立程式碼路徑（static method） | Task 2.5 必須同時修改；加入 R24 風險 | §4.14, R24 |
| **CB-6** | L5 使用 instance-level `_reference_data_cache`，Phase 5 多 worker 重複讀取 | 共享 read-only reference data cache | §7.0.3 |
| **CB-7** | L6.5 已有 chunking 模式（`FFACT_L65_CHUNK_SIZE=2000`） | CGSA per-group 取代 chunking | §4.14 |
| **CB-8** | variance_filter 可能導致 Golden column count 不一致 | 固定閾值 + column set 先比 → 交集數值比對 | §5.0, R23 |
| **CB-9** | `_find_column()` fuzzy matching 在 CGSA 重命名後可能失效 | 建議改為顯式 column 引用 | §4.2.4, R22 |
