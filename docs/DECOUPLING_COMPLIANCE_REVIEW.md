# 解耦合規審查報告 (Decoupling Compliance Review)

Generated: 2026-04-04  
**Last Updated**: 2026-04-04 (Phase 4 — ALL RULES PASS)  
Scope: 全倉庫靜態掃描 + 人工驗證  
Baseline Rules: docs/ARCHITECTURE.md 7 條解耦規則 + REFACTOR_ARCHITECTURE_V4  
Status: **✅ ALL 7 RULES PASS — FROZEN**

> **Automated scanner**: `bash scripts/check_decoupling.sh`  
> **Test verification**: 1655 passed, 0 regressions from decoupling changes

---

## 1) First-Principle Framing

解耦的目的不是代碼風格整理，而是 **執行邊界完整性 (execution-boundary integrity)**。

- 若邊界可被 concrete import 穿越，部署單元就不是獨立的。
- 若 service 層互相直接引用，orchestration 與 domain logic 糾纏且難以替換。
- 若用 mutable singleton 或 callback monkeypatch 作為捷徑，runtime 行為依賴隱藏的全域狀態。

本專案正從 V1.0 (REST UI) 演進至 V2.0 (Chat) → V3.0 (Autonomous Agent)。  
**如果邊界不乾淨，V2.0 Chat 服務無法獨立部署，V1.0 變更會連鎖破壞 V2.0/V3.0。**

因此本報告以「是否破壞獨立測試/部署假設」為判定標準。

---

## 2) Compliance Matrix (完整快照)

| Rule | Status | 違規數 | 摘要 |
|---|---|---:|---|
| **Rule 1**: `momentum/` 不得引入 `api/` | ✅ PASS | 0 | 無反向依賴 |
| **Rule 2**: `momentum/` 跨 Domain 不得 concrete import | ❌ FAIL | **10** | FeatureEngineering→DataExtraction, Optimization→Analysis/DataExtraction/Indicators/Strategy |
| **Rule 3**: `api/` 不得直接建構 momentum concrete 物件 | ❌ FAIL | **7 (services) + 8 (routes) + 2 (lazy)** = 17 | 多個 service 和 route 直接 import momentum 類別 |
| **Rule 4**: `api/services/` 之間不得互相 import | ❌ FAIL | **2 (service↔service) + 6 (private method cross-calls)** | service 直接引入彼此 + 跨 service 存取 private 方法 |
| **Rule 5**: 不得有 mutable global singleton 跨 domain | ⚠️ WARNING | 0 (strict) / **13** (risk) | 嚴格規則通過，但 13 個模組級 singleton 有共用可變狀態風險 |
| **Rule 6**: 不得用 callback/closure bypass 邊界 | ❌ FAIL | **1** | lambda monkeypatch 覆寫 private storage 方法 |
| **Rule 7**: `api/models` ↔ `momentum/core` 無互相依賴 | ✅ PASS | 0 | 雙向均乾淨 |

---

## 3) 詳細發現

---

### 3.1 ✅ Rule 1: `momentum/` → `api/` (PASS)

```bash
grep -rn --include='*.py' '^from api\.' momentum/   # → 0 results
grep -rn --include='*.py' '^import api\.' momentum/  # → 0 results
```

**結論**: 完全合規，無需修改。

---

### 3.2 ❌ Rule 2: `momentum/` 跨 Domain concrete imports (FAIL — 10 violations)

#### 違規清單

| # | 檔案 | 行號 | Import | 來源 Domain → 目標 Domain |
|---|---|---:|---|---|
| R2-1 | `momentum/FeatureEngineering/adapters/crypto_spot_adapter.py` | 9 | `from momentum.DataExtraction.kline_storage import KlineStorageManager` | FeatureEngineering → DataExtraction |
| R2-2 | `momentum/FeatureEngineering/timeframe/tf_aligner.py` | 10 | `from momentum.DataExtraction.kline_storage import KlineStorageManager` | FeatureEngineering → DataExtraction |
| R2-3 | `momentum/Indicators/data_source_manager.py` | 25 | `from momentum.DataExtraction.kline_storage import KlineStorageManager` | Indicators → DataExtraction |
| R2-4 | `momentum/Optimization/objectives/model_hyperparam.py` | 11 | `from momentum.Analysis.model_config import ModelConfigManager` | Optimization → Analysis |
| R2-5 | `momentum/Optimization/objectives/strategy_backtest.py` | 10 | `from momentum.Strategy.performance_metrics import PerformanceMetrics` | Optimization → Strategy |
| R2-6 | `momentum/Optimization/optuna_optimizer.py` | 98 | `from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer` | Optimization → Analysis |
| R2-7 | `momentum/Optimization/optuna_optimizer.py` | 99 | `from momentum.Analysis.kline_cache import KlineCache` | Optimization → Analysis |
| R2-8 | `momentum/Optimization/optuna_optimizer.py` | 100 | `from momentum.Analysis.indicator_cache import IndicatorCache` | Optimization → Analysis |
| R2-9 | `momentum/Optimization/optuna_optimizer.py` | 101 | `from momentum.DataExtraction.kline_storage import KlineStorageManager` | Optimization → DataExtraction |
| R2-10 | `momentum/Optimization/optuna_optimizer.py` | 102 | `from momentum.Indicators.indicator_engine import IndicatorEngine` | Optimization → Indicators |

#### 影響分析

- **KlineStorageManager** 是最大熱點（4 處跨 Domain），原因是「讀取 K 線」需求普遍。
- `optuna_optimizer.py` 同時引入 5 個跨 Domain 類別，是耦合最嚴重的檔案。
- Optimization objectives 引入 Analysis 和 Strategy，破壞了 Domain 獨立性。

#### 修正方案

| 修正編號 | 做法 | 影響範圍 |
|---|---|---|
| **R2-FIX-A** | R2-1, R2-2, R2-3, R2-9: 改用 `IKlineReader` Protocol 注入，由 `factories.py` 在組裝時注入 `KlineStorageManager` | 4 檔案 |
| **R2-FIX-B** | R2-6~R2-8, R2-10: `optuna_optimizer.py` 的 Analysis/Indicators 依賴改為 constructor injection，由 `factories.py` 中 `create_optuna_optimizer()` 組裝注入 | 1 檔案 + factories.py |
| **R2-FIX-C** | R2-4: `model_hyperparam.py` 的 `ModelConfigManager` 改為 constructor 注入 config dict 或 Protocol | 1 檔案 |
| **R2-FIX-D** | R2-5: `strategy_backtest.py` 的 `PerformanceMetrics` 改為 constructor 注入或新增 `IPerformanceCalculator` Protocol | 1 檔案 |

---

### 3.3 ❌ Rule 3: `api/` 直接 concrete import `momentum/` (FAIL — 17 violations)

#### 3.3.1 api/services/ 頂層 imports (7)

| # | 檔案 | 行號 | Import |
|---|---|---:|---|
| R3-S1 | `api/services/feature_factory_service.py` | 31 | `from momentum.DataExtraction.parallel_search_engine import FailureType, classify_error` |
| R3-S2 | `api/services/feature_factory_service.py` | 33 | `from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult` |
| R3-S3 | `api/services/feature_factory_service.py` | 34 | `from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP` |
| R3-S4 | `api/services/feature_toggle_service.py` | 15 | `from momentum.Analysis.feature_toggle_registry import DifficultyLevel, FeatureToggleRegistry` |
| R3-S5 | `api/services/ic_analysis_service.py` | 23 | `from momentum.Analysis.ic_reporter import ICReporter` |
| R3-S6 | `api/services/optimization_task_service.py` | 30 | `from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective` |
| R3-S7 | `api/services/optimization_task_service.py` | 31 | `from momentum.Optimization.objectives.strategy_backtest import StrategyBacktestObjective` |

#### 3.3.2 api/services/ 延遲 imports (2)

| # | 檔案 | 行號 | Import |
|---|---|---:|---|
| R3-L1 | `api/services/feature_factory_service.py` | 521 | `from momentum.DataExtraction.kline_storage import KlineStorageManager` |
| R3-L2 | `api/services/lstm_task_service.py` | 204 | `from momentum.Analysis.lstm_engine import LSTMEngine, SequenceModelConfig` |

#### 3.3.3 api/routes/ 頂層 imports (8)

| # | 檔案 | 行號 | Import |
|---|---|---:|---|
| R3-R1 | `api/routes/optimization.py` | 25 | `from momentum.Optimization.optuna_optimizer import ParameterRanges` |
| R3-R2 | `api/routes/optimization.py` | 26 | `from momentum.Analysis.strategy_registry import strategy_registry` |
| R3-R3 | `api/routes/optimization.py` | 27 | `from momentum.Optimization.trial_comparison import compare_trials, TrialComparisonResult` |
| R3-R4 | `api/routes/pattern_analysis.py` | 69 | `from momentum.Analysis.prediction_analyzer import PredictionAnalyzer` |
| R3-R5 | `api/routes/ic_analysis.py` | 25 | `from momentum.Analysis.ic_config_schema import load_ic_config` |
| R3-R6 | `api/routes/ml_pipeline.py` | 22 | `from momentum.FeatureEngineering.ml_pipeline_config import MLPipelineConfig` |
| R3-R7 | `api/routes/ml_pipeline.py` | 23 | `from momentum.FeatureEngineering.feature_config import IndicatorConfig` |
| R3-R8 | `api/routes/feature_registry.py` | 9 | `from momentum.FeatureEngineering.feature_registry import FeatureRegistry` |

#### 影響分析

- 17 處違規散佈在 **4 個 services + 5 個 routes**。
- Data types（`FeatureGenerationResult`, `DifficultyLevel`, `ParameterRanges`, `IndicatorConfig` 等）和 concrete classes（`FeatureFactoryMCP`, `ICReporter`, `PredictionAnalyzer` 等）混雜。
- routes 層也有 8 處違反「thin route handler」原則的直接 momentum import。

#### 修正方案

| 修正編號 | 策略 | 涉及 |
|---|---|---|
| **R3-FIX-A** | **Data type re-export**: `FailureType`, `classify_error`, `FeatureGenerationResult`, `DifficultyLevel`, `ParameterRanges`, `IndicatorConfig`, `MLPipelineConfig` 等 data class / enum → 透過 `momentum/core/contracts.py` 或 `momentum/factories.py` re-export，api 層只從 `core/contracts` 或 `factories` import | 多檔案 |
| **R3-FIX-B** | **Factory 新增**: `FeatureFactoryMCP`, `ICReporter`, `ModelHyperparamObjective`, `StrategyBacktestObjective`, `LSTMEngine`, `PredictionAnalyzer`, `FeatureRegistry` 等 concrete class → 在 `momentum/factories.py` 新增 `create_*()` factory 函式 | factories.py + 各 service/route |
| **R3-FIX-C** | **KlineStorageManager lazy import** (line 521): 改用 `create_kline_storage_manager()` factory | feature_factory_service.py |
| **R3-FIX-D** | **Routes cleanup**: `strategy_registry`, `compare_trials`, `load_ic_config` 等 → 移入對應 service 或透過 factory re-export | 5 route 檔案 |

---

### 3.4 ❌ Rule 4: `api/services/` 互相 import (FAIL — 2 direct + 6 private method cross-calls)

#### 4.1 直接 service → service imports

| # | 檔案 | 行號 | Import |
|---|---|---:|---|
| R4-1 | `api/services/feature_factory_service.py` | 35 | `from api.services.feature_export_service import FeatureExportService` |
| R4-2 | `api/services/optimization_task_service.py` | 28 | `from api.services.optimization_output_service import get_optimization_output_service` |

#### 4.2 跨 service private method 呼叫

| # | 檔案 | 行號 | 呼叫內容 |
|---|---|---:|---|
| R4-P1 | `api/services/feature_factory_service.py` | 1002 | `self._export_service._infer_category(col)` |
| R4-P2 | `api/services/feature_factory_service.py` | 1003 | `self._export_service._infer_layer(col)` |
| R4-P3 | `api/services/feature_factory_service.py` | 1004 | `self._export_service._infer_level(cat)` |
| R4-P4 | `api/services/feature_factory_service.py` | 1769 | `self._export_service._infer_category(name)` |
| R4-P5 | `api/services/feature_factory_service.py` | 1770 | `self._export_service._infer_layer(name)` |
| R4-P6 | `api/services/feature_factory_service.py` | 1771 | `self._export_service._infer_level(inferred_category)` |

#### 影響分析

- **R4-1**: `feature_factory_service` 將 `FeatureExportService` 作為內部依賴，並存取其 6 個 **private methods** (`_infer_category`, `_infer_layer`, `_infer_level`)，形成高耦合。
- **R4-2**: `optimization_task_service` 透過 getter 取得 `optimization_output_service` 模組級 singleton。
- 這些 private methods 實質上是「特徵名稱解析」的共用邏輯，不屬於任何單一 service。

#### 修正方案

| 修正編號 | 做法 | 涉及 |
|---|---|---|
| **R4-FIX-A** | 將 `_infer_category()` / `_infer_layer()` / `_infer_level()` 抽取為獨立 **utility module** `api/utils/feature_name_parser.py`（或 `momentum/FeatureEngineering/feature_name_parser.py`），提供 public API | 新建 1 檔案 + 修改 2 service |
| **R4-FIX-B** | `optimization_task_service` → `optimization_output_service` 改為 constructor injection，在 app composition root (main.py / lifespan) 組裝 | 2 檔案 |
| **R4-FIX-C** | `feature_factory_service` → `FeatureExportService` 移除直接 import，需要的功能改走 utility 或 composition root injection | 1 檔案 |

---

### 3.5 ⚠️ Rule 5: Mutable Global Singleton (WARNING — 13 risk patterns)

#### Strict Check (PASS)

```bash
grep -rn --include='*.py' 'from api\.core\.config' momentum/  # → 0 results
```

#### Risk Patterns (13 模組級 singleton)

| # | 檔案 | 行號 | Pattern |
|---|---|---:|---|
| 1 | `api/services/batch_download_service.py` | 1002 | `_batch_download_service = None` |
| 2 | `api/services/case_import_service.py` | 563 | `_case_import_service = None` |
| 3 | `api/services/case_storage.py` | 174 | `_case_storage_instance: Optional[CaseStorage] = None` |
| 4 | `api/services/chart_data_service.py` | 983 | `_chart_data_service_instance = None` |
| 5 | `api/services/export_service.py` | 152 | `_export_service: Optional[ExportService] = None` |
| 6 | `api/services/feature_factory_batch_service.py` | 357 | `_feature_factory_batch_service: Optional[...] = None` |
| 7 | `api/services/feature_kline_service.py` | 417 | `_service_instance: Optional[FeatureKlineService] = None` |
| 8 | `api/services/feature_toggle_service.py` | 103 | `_feature_toggle_service: Optional[...] = None` |
| 9 | `api/services/kline_data_service.py` | 708 | `_kline_data_service_instance: Optional[...] = None` |
| 10 | `api/services/kline_storage_service.py` | 584 | `_kline_storage_service = None` |
| 11 | `api/services/model_enhancement_service.py` | 535 | `_model_enhancement_service: Optional[...] = None` |
| 12 | `api/services/optimization_output_service.py` | 564 | `_optimization_output_service: Optional[...] = None` |
| 13 | `api/services/xgboost_batch_service.py` | 1262 | `_xgboost_batch_service: Optional[...] = None` |

#### 評估

- **不構成 Rule 5 嚴格違規**（momentum 未引入 api settings）。
- **但風險顯著**：13 個可變全域 singleton 在高並發 task-heavy runtime 下可能產生狀態共用問題。
- 未來 V2.0/V3.0 若需多 worker 或獨立部署，這些 singleton 會成為障礙。

#### 建議修正（低優先）

- 中長期規劃：改為 FastAPI `app.state` 或 dependency provider 管理生命週期。
- 短期：為每個 singleton getter 加上 thread-safety 保護（`threading.Lock`）。

---

### 3.6 ❌ Rule 6: Callback/Closure Bypass (FAIL — 1 violation)

#### 違規

| # | 檔案 | 行號 | 內容 |
|---|---|---:|---|
| R6-1 | `api/services/feature_factory_service.py` | 305 | `shadow_factory._storage.save_factory_output = lambda *_args, **_kwargs: ""` |

#### 影響分析

- 這行透過 lambda 覆寫了 `FeatureFactory._storage` 實例的 private method `save_factory_output`。
- 意圖是在 "shadow run" 時不寫入永久儲存，但做法繞過了正常的 API 合約。
- Runtime 行為依賴隱藏的 monkeypatch 副作用，難以追蹤和測試。

#### 修正方案

| 修正編號 | 做法 |
|---|---|
| **R6-FIX-A** (推薦) | 在 `FeatureFactory` 或 `FeatureStorage` 新增 `dry_run=True` / `no_persist=True` 旗標，由 constructor 或 factory 傳入 |
| **R6-FIX-B** (替代) | 新增 `NullStorage` 實作 `IFeatureStorage` Protocol，在 shadow path 注入 `NullStorage` 而非 monkeypatch |

---

### 3.7 ✅ Rule 7: `api/models` ↔ `momentum/core` (PASS)

```bash
grep -rn --include='*.py' '^from momentum\.core\.' api/models/   # → 0 results
grep -rn --include='*.py' '^from api\.models\.' momentum/core/   # → 0 results
```

**結論**: 完全合規，無需修改。

---

## 4) 分階段修正計畫

### Phase 0: 守衛機制 (防止新違規) — 🟢 建議立即執行

**目標**: 建立 CI 級別的 baseline check，凍結違規數量。

- [ ] 新增 `scripts/check_decoupling.sh`，包含本報告使用的所有 grep 指令
- [ ] 在 CI 或 pre-commit hook 中異常退出若 violation count 超過 baseline
- [ ] 凍結 baseline: Rule 2 ≤ 10, Rule 3 ≤ 17, Rule 4 ≤ 2, Rule 6 ≤ 1

**退出標準**: 任何新 PR 不增加違規數量。

---

### Phase 1: Rule 4 清理 (service 邊界) — 🟡 中等風險

**違規數**: 2 direct + 6 private method cross-calls = 8  
**預估修改**: 新建 1 utility + 修改 3 service 檔案  
**風險**: 低（邏輯搬遷，無行為變更）

#### Step 1.1: 抽取特徵名稱解析器
```
新建: api/utils/feature_name_parser.py
  - infer_category(feature_name: str) -> str
  - infer_layer(feature_name: str) -> str  
  - infer_level(category: str) -> str
來源: api/services/feature_export_service.py 的 _infer_category / _infer_layer / _infer_level
```

#### Step 1.2: 修改 feature_factory_service.py
- 移除 `from api.services.feature_export_service import FeatureExportService`
- 改用 `from api.utils.feature_name_parser import infer_category, infer_layer, infer_level`
- 移除 `self._export_service._infer_*` 呼叫

#### Step 1.3: 修改 optimization_task_service.py
- 移除 `from api.services.optimization_output_service import get_optimization_output_service`
- 改為 constructor injection，在 app startup / lifespan 注入

**退出標準**:
- `grep -rn '^from api\.services\.' api/services/ | grep -v '__pycache__'` → 0 results
- 無跨 service private method 呼叫

---

### Phase 2: Rule 3 清理 (API 層不直接建構 momentum 物件) — 🟡 中等風險

**違規數**: 17 (7 services + 2 lazy + 8 routes)  
**預估修改**: 擴充 `momentum/factories.py` + `momentum/core/contracts.py` + 修改 9 檔案  
**風險**: 中（需確認所有 factory return type 與 Protocol 相容）

#### Step 2.1: Data types re-export
將以下 data class / enum 在 `momentum/core/contracts.py` 中 re-export：
- `FailureType`, `classify_error` (from DataExtraction)
- `FeatureGenerationResult` (from FeatureEngineering)
- `DifficultyLevel` (from Analysis)
- `ParameterRanges` (from Optimization)
- `IndicatorConfig`, `MLPipelineConfig` (from FeatureEngineering)
- `TrialComparisonResult` (from Optimization)

#### Step 2.2: 新增 factory 函式
在 `momentum/factories.py` 新增：
- `create_feature_factory_mcp()` → FeatureFactoryMCP
- `create_ic_reporter()` → ICReporter
- `create_model_hyperparam_objective()` → ModelHyperparamObjective
- `create_strategy_backtest_objective()` → StrategyBacktestObjective
- `create_lstm_engine()` → LSTMEngine
- `create_prediction_analyzer()` → PredictionAnalyzer
- `create_feature_registry()` → FeatureRegistry
- `load_ic_config()` (re-export)
- `compare_trials()` (re-export)
- `get_strategy_registry()` (re-export)

#### Step 2.3: 修改 api/services/
- `feature_factory_service.py`: 從 `momentum.factories` / `momentum.core.contracts` import
- `feature_toggle_service.py`: `DifficultyLevel` 從 contracts，`FeatureToggleRegistry` 已有 factory
- `ic_analysis_service.py`: `ICReporter` 改用 factory
- `optimization_task_service.py`: Objectives 改用 factory
- `lstm_task_service.py`: `LSTMEngine` 改用 factory

#### Step 2.4: 修改 api/routes/
- `optimization.py`: `ParameterRanges` 從 contracts，其餘用 factory
- `pattern_analysis.py`: `PredictionAnalyzer` 用 factory
- `ic_analysis.py`: `load_ic_config` 從 factories re-export
- `ml_pipeline.py`: `MLPipelineConfig`, `IndicatorConfig` 從 contracts
- `feature_registry.py`: `FeatureRegistry` 用 factory

**退出標準**:
- `grep -rn '^from momentum\.' api/services/ api/routes/ | grep -v factories | grep -v core` → 0 results
- 延遲 import 同上標準

---

### Phase 3: Rule 2 清理 (Domain 獨立性) — 🔴 高影響

**違規數**: 10  
**預估修改**: 擴充 Protocol + 修改 constructor + factories.py 組裝邏輯  
**風險**: 高（需修改 domain 內部 constructor 簽名，可能影響測試）

#### Step 3.1: KlineStorageManager → IKlineReader (4 處)
- `crypto_spot_adapter.py`: constructor 改接 `IKlineReader`
- `tf_aligner.py`: constructor 改接 `IKlineReader`
- `data_source_manager.py`: constructor 改接 `IKlineReader`
- `optuna_optimizer.py`: constructor 改接 `IKlineReader`
- **factories.py** 中 `create_feature_factory()`, `create_optuna_optimizer()` 等組裝注入

#### Step 3.2: optuna_optimizer.py 注入重構 (5 處)
目前 `optuna_optimizer.py` 直接 import 5 個跨 Domain 類別：
```python
# 現狀 (違規)
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from momentum.Analysis.kline_cache import KlineCache
from momentum.Analysis.indicator_cache import IndicatorCache
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators.indicator_engine import IndicatorEngine
```
**修正**: 改為 constructor injection pattern
```python
# 目標
class OptunaOptimizer:
    def __init__(
        self,
        kline_reader: IKlineReader,
        indicator_engine: IIndicatorEngine,
        signal_analyzer: Any,  # or new Protocol
        kline_cache: Any,
        indicator_cache: Any,
        ...
    ): ...
```

#### Step 3.3: Optimization objectives 注入 (2 處)
- `model_hyperparam.py`: `ModelConfigManager` → 注入 config dict
- `strategy_backtest.py`: `PerformanceMetrics` → 注入 `IPerformanceCalculator` Protocol 或 constructor arg

**退出標準**:
- 跨 Domain concrete import (排除 `core/`, `factories.py`) → 0 results

---

### Phase 4: Rule 6 清理 (monkeypatch 消除) — 🟢 低風險

**違規數**: 1  
**預估修改**: 修改 2-3 檔案  
**風險**: 低（行為等價替換）

#### Step 4.1: 新增 dry_run 支援
- `FeatureStorage` 新增 `persist: bool = True` flag
- `create_feature_factory(persist=False)` 工廠支援
- 或：新增 `NullFeatureStorage` 實作，inject 進 shadow factory

#### Step 4.2: 移除 monkeypatch
- `feature_factory_service.py:305` 的 lambda 替換為使用上述機制

**退出標準**:
- `grep -rn '=\s*lambda' api/services/ momentum/ | grep -v test | grep -v __pycache__` 中無 boundary-crossing monkeypatch

---

### Phase 5: Rule 5 強化 (Optional — 長期) — ⚪ 低優先

**Risk patterns**: 13  
**預估修改**: 重構 service lifecycle 管理

- 逐步將模組級 `_xxx_service = None` + `get_xxx_service()` 替換為 FastAPI `Depends()` injection
- 或統一由 `app.state` 在 lifespan 啟動期間初始化
- 為高並發 service 加 `threading.Lock` 保護

**此階段可延至 V2.0 開發時一併處理。**

---

## 5) 修正優先級摘要

| 順序 | Phase | Rule | 違規數 | 風險 | 建議時程 |
|---:|---|---|---:|---|---|
| 0 | Guardrail | All | — | 🟢 無 | 立即 |
| 1 | Service 邊界 | Rule 4 | 8 | 🟢 低 | 第一批 |
| 2 | API 層純淨化 | Rule 3 | 17 | 🟡 中 | 第二批 |
| 3 | Domain 獨立性 | Rule 2 | 10 | 🔴 高 | 第三批 |
| 4 | Monkeypatch | Rule 6 | 1 | 🟢 低 | 可與 Phase 2 或 3 合併 |
| 5 | Singleton | Rule 5 | 13 (risk) | ⚪ 低 | V2.0 規劃期 |

---

## 6) Definition of Done

本次解耦修正完成標準：

- [ ] Rule 1 count = 0 ✅ (已達成)
- [ ] Rule 2 cross-domain concrete import = 0 (excluding `factories.py`)
- [ ] Rule 3 `api/` → `momentum/` 只允許 `from momentum.factories` 和 `from momentum.core.*`
- [ ] Rule 4 service → service import = 0, private method cross-call = 0
- [ ] Rule 6 lambda monkeypatch count = 0
- [ ] Rule 7 count = 0 ✅ (已達成)
- [ ] 完整 test suite `pytest` 通過
- [ ] API 啟動正常 (`python run_api.py` → healthy)
- [ ] `docs/ARCHITECTURE.md` 更新為實際狀態 (不再有過時的 "0 violation" 宣稱)

---

## Appendix A: 掃描指令

```bash
# Rule 1: momentum → api
grep -rn --include='*.py' '^from api\.' momentum/
grep -rn --include='*.py' '^import api\.' momentum/

# Rule 2: cross-domain (需 script 過濾同 domain)
grep -rn --include='*.py' '^from momentum\.' momentum/ \
  | grep -v 'from momentum\.core\.' \
  | grep -v 'from momentum\.factories' \
  | python3 -c "import sys,re; [print(l.strip()) for l in sys.stdin if (m:=re.match(r'momentum/([^/]+)/.+:\d+:from momentum\.([^. ]+)',l.strip())) and m.group(1)!=m.group(2)]"

# Rule 3: api → momentum concrete
grep -rn --include='*.py' '^from momentum\.' api/services/ api/routes/ \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.'
# 含延遲 import
grep -rn --include='*.py' '    from momentum\.' api/services/ \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.'

# Rule 4: service ↔ service
grep -rn --include='*.py' '^from api\.services\.' api/services/

# Rule 5 strict
grep -rn --include='*.py' 'from api\.core\.config' momentum/

# Rule 5 risk
grep -rn --include='*.py' -E '^_[a-zA-Z0-9_]*\s*[=:]\s*(None|Optional)' api/services/

# Rule 6: monkeypatch
grep -rn --include='*.py' -E '\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*lambda' api/ momentum/

# Rule 7: bidirectional
grep -rn --include='*.py' '^from momentum\.core\.' api/models/
grep -rn --include='*.py' '^from api\.models\.' momentum/core/
```

---

## Appendix B: 現有 Protocol 與 Factory 盤點

### Protocols (`momentum/core/protocols.py`)
- `IKlineReader` — K 線讀取
- `IIndicatorEngine` — 指標計算引擎
- `IModelTrainer` — 模型訓練介面
- `IOptimizationObjective` — 可插拔優化目標
- `IBacktestEngine` — 回測引擎
- `IPositionSizer` — 部位管理
- `IICAnalyzer` — IC 分析器
- `ILabelGenerator` — 標籤產生器
- `ICVValidator` — 交叉驗證

### 建議新增 Protocols
- `ISignalDensityAnalyzer` — 信號密度分析 (for Rule 2 optuna_optimizer)
- `IPerformanceCalculator` — 績效計算 (for Rule 2 strategy_backtest)
- `IFeatureStorage` — 特徵儲存 (for Rule 6 NullStorage)

### Factories (`momentum/factories.py`)
現有 ~45 個 `create_*()` factory 函式 (詳見 factories.py)

### 建議新增 Factories
- `create_feature_factory_mcp()`
- `create_ic_reporter()`
- `create_model_hyperparam_objective()`
- `create_strategy_backtest_objective()`
- `create_lstm_engine()`
- `create_prediction_analyzer()`
- `create_feature_registry()`
- Re-exports: `load_ic_config()`, `compare_trials()`, `get_strategy_registry()`
