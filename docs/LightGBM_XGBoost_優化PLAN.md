# LightGBM/XGBoost 優化 PLAN

> **版本**: V8  
> **建立日期**: 2026-02-16  
> **最後更新**: 2026-02-17  
> **依據 SPEC**: `docs/LightGBM_XGBoost_優化SPEC.md` V2 (Frozen)  
> **PLAN 範本**: `docs/Feature_Factory_PLAN.md` V7 (Frozen)  
> **前置依賴**: Phase 3 LightGBM/XGBoost 雙引擎系統（已完成）、REFACTOR_ARCHITECTURE_V4（已完成）  
> **對應 Phase**: Phase 3.5（模型訓練增強）  
> **狀態**: ✅ V8 (Converged / Ready to Freeze)  
> **預估工作量**: 14-20 天（M1-M6: 5-7 天 + M7-M9: 9-13 天）  
> **新建檔案**: 53 個（M1-M6: 24 + M7-M9: 29）  
> **修改檔案**: 10 個（M1-M6: 5 + M7-M9: 5）  
> **測試總數**: ~204 個（77 邊界條件 + ~55 功能 + ~30 整合 + ~29 API + ~13 效能）  
> **V8 變更**: 補齊 Phase 6-8 階段級驗證檢查點，明確成功/失敗與邊界 PASS 條件（不擴展原責任範圍）  
> Changelog: V7 → V8：補齊 Phase 6-8 的階段驗證覆蓋，並完成收斂檢查

---

## 目錄

1. [架構原則與解耦合規](#1-架構原則與解耦合規)
2. [全域常數與共用定義](#2-全域常數與共用定義)
3. [Phase 0：前置條件](#3-phase-0前置條件)
4. [Phase 1：基礎設施](#4-phase-1基礎設施)
5. [Phase 2：核心模組 M1-M6](#5-phase-2核心模組-m1-m6)
6. [Phase 3：API 層](#6-phase-3api-層)
7. [Phase 4：前端層](#7-phase-4前端層)
8. [Phase 5：測試與驗收](#8-phase-5測試與驗收)
9. [__init__.py 匯出清單](#9-__init__py-匯出清單)
10. [執行順序總覽](#10-執行順序總覽)
11. [關鍵依賴圖](#11-關鍵依賴圖)
12. [風險對照表](#12-風險對照表)
13. [測試共用 Fixtures](#13-測試共用-fixtures)
14. [快取策略](#14-快取策略)
15. [Logging 標準](#15-logging-標準)
16. [MCP Tool Interface](#16-mcp-tool-interface)
17. [AI Agent 每 Task 完成後驗證命令](#17-ai-agent-每-task-完成後驗證命令)

---

## 1. 架構原則與解耦合規

### 1.1 核心原則（SPEC §1.3）

1. **非侵入式**：所有模組為獨立新建檔案，不修改 Phase 3 已凍結核心檔案
2. **引擎無關**：所有模組接收 `IModelTrainer` Protocol 或 `Callable[[], IModelTrainer]`
3. **可選啟用**：每個模組 `enabled: bool` 控制，不啟用 = 零開銷
4. **向後相容**：現有 API 端點、前端圖表、測試套件完全不受影響
5. **解耦合規**：遵循 REFACTOR_ARCHITECTURE_V4 七條規則
6. **First Principle**：每個方法有學術來源或業界實務支撐

### 1.2 解耦規則 Checklist

| 規則 | 驗證方式 | 本 PLAN 合規策略 |
|------|---------|-----------------|
| **Rule 1** — `momentum/` 不 import `api/` | `grep -r "from api\." momentum/` → 0 | 所有新模組使用 `momentum.core.logging` |
| **Rule 2** — 跨 Domain 使用 Protocol | 確認無 concrete class 直接 import | 新模組位於同 Domain（`momentum/Analysis/`），無跨 Domain 依賴 |
| **Rule 3** — `api/services/` 使用 Factory | 確認無直接 import concrete class | `ModelEnhancementService` 通過 `momentum/factories.py` 取得物件 |
| **Rule 4** — Service 不互相 import | 確認 service 間無直接依賴 | `model_enhancement_service.py` 不 import 其他 service |
| **Rule 5** — Config 單一來源 | 確認無 `from api.core.config import settings` | 使用 `config/model_config.yaml` + Pydantic Config |
| **Rule 6** — 測試可不依賴 `run_api.py` | `pytest tests/momentum/Analysis/` 獨立通過 | 用 factory + fixture 注入 |
| **Rule 7** — DTO 不跨域依賴 | `api/models/` → `momentum/core/contracts.py` 單向 | `api/models/model_enhancement.py` 獨立定義 Request/Response |

### 1.3 Protocol 策略決策（SPEC §9.2）

**不新增 Protocol** — 理由：
1. 所有新模組位於 `momentum/Analysis/` 同一 Domain
2. 模組接收已有的 `IModelTrainer` Protocol 或 `Callable[[], IModelTrainer]`
3. `momentum/core/protocols.py` 中的 `IModelTrainer` **不修改**

### 1.4 不動的檔案清單（SPEC §13.3）

| 檔案 | 理由 |
|------|------|
| `momentum/core/protocols.py` | `IModelTrainer` 已足夠，不新增 Protocol |
| `momentum/Analysis/model_validation/cv_validator.py` | M5 獨立平行，不修改現有 CV |
| `momentum/Analysis/calibration_analyzer.py` | M1 引用其 ECE/Brier 計算（只讀），不改動 |
| `momentum/Analysis/drift_analyzer.py` | M4 引用 PSI 邏輯（只讀），不改動 |
| `momentum/Analysis/time_splitter.py` | M2/M5 復用 purge/embargo 邏輯（只讀），不改動 |

---

## 2. 全域常數與共用定義

### 2.1 SkippedResult 結構（SPEC §1.5.3）

> **⚠️ 尚未存在於程式碼中**：`momentum/core/contracts.py` 目前無 `SkippedResult`，需在 **Task 0.1** 中新增。

```python
@dataclass
class SkippedResult:
    module_name: str            # e.g., "probability_calibrator"
    reason: str                 # 人類可讀描述
    error_type: str             # INSUFFICIENT_DATA | SINGLE_CLASS | TIMEOUT | NUMERICAL_ERROR | ...
    details: Optional[Dict] = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

**SPEC §14.2 欄位差異說明**：SPEC §1.5.3 和 §14.2 定義了兩組略不同的欄位名。本 PLAN 以 §1.5.3 為正式定義（更完整），§14.2 的 `module` / `error_code` / `severity` 是簡化範例。

### 2.2 全域最低資料要求（SPEC §1.5.1）

| 模組 | 最低樣本數 | 最低特徵數 | 常數名稱 |
|------|:----------:|:----------:|---------|
| M1 ProbabilityCalibrator | 50 | 1 | `MIN_SAMPLES_CALIBRATION = 50` |
| M2 WalkForwardValidator | `train_window + test_window × 2` | 1 | 動態計算 |
| M3 SampleWeightCalculator | 10 | 0 | `MIN_SAMPLES_WEIGHT = 10` |
| M4 AdversarialValidator | 40（train+test 各 20） | 1 | `MIN_SAMPLES_ADVERSARIAL = 40` |
| M5 CombinatorialPurgedCV | `n_groups × 20` | 1 | 動態計算 |
| M6 LearningCurveAnalyzer | 200 | 5 | `MIN_SAMPLES_LEARNING_CURVE = 200` |

### 2.3 錯誤分類常數（SPEC §14.1）

| 等級 | 處理策略 |
|------|---------|
| **CRITICAL** | 中止 + 全額報告（如校準導致 ECE 惡化 50%+） |
| **ERROR** | skip + `SkippedResult`（如資料不足、模型訓練失敗） |
| **WARNING** | 繼續 + 附帶警告（如樣本數邊界、AUC 不穩定） |
| **INFO** | 僅記錄（模組開始/完成） |

### 2.4 Per-Module Timeout（SPEC §14.3）

| 模組 | 預設 Timeout | 常數名稱 |
|------|:-----------:|---------|
| M1 | 120s | `TIMEOUT_CALIBRATOR = 120` |
| M2 | 300s | `TIMEOUT_WALK_FORWARD = 300` |
| M3 | 30s | `TIMEOUT_SAMPLE_WEIGHT = 30` |
| M4 | 120s | `TIMEOUT_ADVERSARIAL = 120` |
| M5 | 600s | `TIMEOUT_CPCV = 600` |
| M6 | 300s | `TIMEOUT_LEARNING_CURVE = 300` |

### 2.5 Config 載入流程（YAML → Factory → Module → Pydantic）

```
config/model_config.yaml            ← 使用者可修改的 runtime 設定
        │
        ▼
momentum/factories.py              ← Factory 讀取 YAML（config=None 時）
  create_probability_calibrator(config=None)
        │  config = yaml_config.get('probability_calibration', {})
        ▼
momentum/Analysis/probability_calibrator.py
  ProbabilityCalibrator(config=dict)
        │  self.config = ProbabilityCalibratorConfig(**(config or {}))
        ▼
  ProbabilityCalibratorConfig(BaseModel)   ← Pydantic 驗證 + 預設值
```

**規則**：
- `config=None` → Factory 自動載入 `model_config.yaml` 中對應 section
- `config=dict` → 用傳入 dict 覆蓋 Pydantic 預設值
- Pydantic 預設值 = SPEC 定義的預設值
- YAML 值 = 使用者 runtime 自訂值（可能與 Pydantic 預設不同）

**Module `__init__` 標準模式**：

```python
class ProbabilityCalibrator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = ProbabilityCalibratorConfig(**(config or {}))
        self.logger = get_logger(__name__)
        self._fitted = False
```

---

## 3. Phase 0：前置條件

### 驗證檢查點

- PASS: Task 0.1-0.3 全部完成後，可成功 import `SkippedResult` 並確認測試目錄存在。
- PASS: 若 `SkippedResult` 未建立或 `betacal` 未安裝，Phase 0 驗證應明確失敗並停止進入 Phase 1。

### Task 0.1：SkippedResult dataclass 新增

**說明**：`SkippedResult` 在 SPEC 中被定義但尚未存在於程式碼中。需在 `momentum/core/contracts.py` 中新增。

**檔案**（修改）：`momentum/core/contracts.py`

**新增內容**（註：`contracts.py` 已有 `from dataclasses import dataclass, field` 和 `from typing import Optional, Dict`，僅需新增 `datetime` import）：

```python
from datetime import datetime  # 新增

@dataclass
class SkippedResult:
    """模組執行跳過或失敗時的結構化結果（SPEC §1.5.3）"""
    module_name: str
    reason: str
    error_type: str   # INSUFFICIENT_DATA | SINGLE_CLASS | TIMEOUT | NUMERICAL_ERROR | ZERO_VARIANCE | UNEXPECTED
    details: Optional[Dict] = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

**依賴**：無

**驗收條件**：
- [ ] `SkippedResult` 可從 `momentum.core.contracts` import
- [ ] 不影響現有 contracts.py 中的 `TrainingWindowConfig`, `StrategyConfig` 等

**驗證檢查點**：
- PASS: `python -c "from momentum.core.contracts import SkippedResult; print(SkippedResult('m1','test','TIMEOUT'))"` 輸出正常
- PASS: `pytest tests/momentum/ -x --tb=short` 無回歸

**驗證命令**：
```bash
python -c "from momentum.core.contracts import SkippedResult; sr = SkippedResult(module_name='test', reason='test', error_type='TIMEOUT'); print(sr); print('SkippedResult OK')"
```

---

### Task 0.2：requirements.txt 更新

**說明**：新增 `betacal` 依賴（Beta Calibration，M1 使用）

**檔案**（修改）：`requirements.txt`

**新增行**：

```
betacal>=0.2.7
```

**依賴**：無

**驗收條件**：
- [ ] `pip install betacal` 成功
- [ ] import 不報錯

**驗證檢查點**：
- PASS: `pip install betacal` 成功且 `python -c "import betacal"` 無錯誤
- FAIL: import error → 確認 Python 版本相容性

**驗證命令**：
```bash
pip install betacal && python -c "import betacal; print('betacal OK')"
```

---

### Task 0.3：測試目錄結構確認

**說明**：確保 `tests/momentum/Analysis/model_validation/` 目錄存在且有 `__init__.py`

**目錄建立**：

```bash
mkdir -p tests/momentum/Analysis/model_validation
touch tests/momentum/Analysis/model_validation/__init__.py
```

**驗收條件**：
- [ ] `tests/momentum/Analysis/model_validation/__init__.py` 存在

**驗證檢查點**：
- PASS: `ls tests/momentum/Analysis/model_validation/__init__.py` 存在
- PASS: `pytest tests/momentum/ --collect-only` 不因目錄缺失而報錯

---

## 4. Phase 1：基礎設施

### 驗證檢查點

- PASS: Task 1.1.1-1.1.4 完成後，YAML/Factory/API Models 可獨立被匯入與驗證。
- PASS: 任一 Config 驗證規則不符（如 `n_test_groups >= n_groups`）時，應在 Phase 1 即被攔截。

### Task 1.1.1：Pydantic Config Models

**說明**：定義 Phase 3.5 所有模組的 Pydantic 配置模型（SPEC §3.9, §4.8, §5.8, §6.7, §7.6, §8.7, §9.4）。各模組 Config 定義在各自模組檔案內（同 Phase 3 慣例）。

**各模組 Config 定義**（分佈在 Phase 2 各模組檔案中）：

```python
# === 位於 momentum/Analysis/probability_calibrator.py ===
class ProbabilityCalibratorConfig(BaseModel):
    enabled: bool = True
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=10)
    min_samples_isotonic: int = Field(default=1000, ge=100)
    fallback_on_degradation: bool = True
    venn_abers_max_samples: int = Field(default=5000, ge=100)

# === 位於 momentum/Analysis/model_validation/walk_forward_validator.py ===
class WalkForwardConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=50)
    test_size: int = Field(default=100, ge=20)
    step_size: Optional[int] = None
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    auc_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    min_periods: int = Field(default=3, ge=1)

# === 位於 momentum/Analysis/sample_weight_calculator.py ===
class SampleWeightConfig(BaseModel):
    enabled: bool = True
    strategies: List[str] = ["time_decay", "class_balance"]
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=3650)
    time_decay_type: str = Field(default="exponential", pattern="^(exponential|linear)$")
    class_balance_method: str = Field(default="balanced", pattern="^(balanced|sqrt|custom)$")
    min_weight: float = Field(default=0.01, ge=0.0, lt=1.0)

# === 位於 momentum/Analysis/adversarial_validator.py ===
class AdversarialValidationConfig(BaseModel):
    enabled: bool = True
    n_estimators: int = Field(default=100, ge=10, le=1000)
    cv: int = Field(default=5, ge=2, le=10)
    auc_warning_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    auc_severe_threshold: float = Field(default=0.70, ge=0.5, le=1.0)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True

# === 位於 momentum/Analysis/model_validation/combinatorial_purged_cv.py ===
class CPCVConfig(BaseModel):
    enabled: bool = True
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)
    compute_backtest_paths: bool = True

    @model_validator(mode='after')
    def check_groups(self) -> 'CPCVConfig':
        if self.n_test_groups >= self.n_groups:
            raise ValueError(f"n_test_groups ({self.n_test_groups}) must be < n_groups ({self.n_groups})")
        return self

# === 位於 momentum/Analysis/learning_curve_analyzer.py ===
class LearningCurveConfig(BaseModel):
    enabled: bool = True
    cv: int = Field(default=5, ge=2, le=10)
    metric: str = Field(default="auc", pattern="^(auc|brier|precision_at_k)$")
    train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")
```

**驗收條件**：
- [ ] 所有 Config 使用 `pydantic.Field` 含 `ge`/`le`/`pattern` 驗證
- [ ] `CPCVConfig` 含 `model_validator` 確保 `n_test_groups < n_groups`
- [ ] 所有 Config 有 `enabled: bool = True` 開關

**驗證檢查點**：
- PASS: `CPCVConfig(n_groups=6, n_test_groups=2)` 成功建立
- FAIL: `CPCVConfig(n_groups=6, n_test_groups=6)` → 拋出 `ValidationError`

**驗證命令**：
```bash
# Phase 2 各模組完成後執行
python -c "
from momentum.Analysis.probability_calibrator import ProbabilityCalibratorConfig
from momentum.Analysis.model_validation.combinatorial_purged_cv import CPCVConfig
c = CPCVConfig(n_groups=6, n_test_groups=2); print(f'CPCV Config OK: {c}')
try:
    CPCVConfig(n_groups=6, n_test_groups=6)
    print('FAIL: should have raised')
except Exception as e:
    print(f'PASS: {e}')
"
```

---

### Task 1.1.2：YAML Config 擴展

**說明**：在 `config/model_config.yaml` 新增 Phase 3.5 configuration section（SPEC §9.4）

**檔案**（修改）：`config/model_config.yaml`

**新增內容**：

```yaml
# === Phase 3.5 新增：模型訓練增強 ===

probability_calibration:
  enabled: true
  method: auto
  cv: 5
  min_samples_isotonic: 1000
  fallback_on_degradation: true

walk_forward:
  enabled: true
  mode: rolling
  train_size: 500
  test_size: 100
  step_size: null
  purge_gap: 5
  embargo_pct: 0.01
  auc_threshold: 0.55
  min_periods: 3

sample_weight:
  enabled: true
  strategies:
    - time_decay
    - class_balance
  combination: multiply
  time_decay_half_life: 180
  time_decay_type: exponential
  class_balance_method: balanced
  min_weight: 0.01

adversarial_validation:
  enabled: true
  n_estimators: 100
  cv: 5
  auc_warning_threshold: 0.55
  auc_severe_threshold: 0.70
  include_feature_tests: true
  include_leakage_detection: true

cpcv:
  enabled: true
  n_groups: 6
  n_test_groups: 2
  purge_gap: 5
  embargo_pct: 0.01
  max_paths: 50
  compute_backtest_paths: true

learning_curve:
  enabled: true
  cv: 5
  metric: auc
  train_fractions: [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
  ranking_method: gain
```

**驗收條件**：
- [ ] 不修改現有 `lightgbm`/`xgboost`/`validation` section
- [ ] 所有預設值與 SPEC 一致
- [ ] YAML 格式可被 `yaml.safe_load()` 正常解析

**驗證檢查點**：
- PASS: `yaml.safe_load()` 後同時存在 `probability_calibration` 與 `learning_curve` key。
- PASS: 當 YAML 缺少任一新 section 時，檢查流程可明確失敗（assert 失敗）且指出缺漏 key。

**驗證命令**：
```bash
python -c "import yaml; d=yaml.safe_load(open('config/model_config.yaml')); assert 'probability_calibration' in d; assert 'cpcv' in d; print('YAML OK')"
```

---

### Task 1.1.3：Factory 函式擴展

**說明**：在 `momentum/factories.py` 新增 6 個 factory 函式（SPEC §9.3, Rule 3）

**檔案**（修改）：`momentum/factories.py`

**新增函式簽名**：

```python
def create_probability_calibrator(
    config: Optional[Dict] = None,
) -> "ProbabilityCalibrator":
    """Factory — M1 機率校準器"""
    from momentum.Analysis.probability_calibrator import ProbabilityCalibrator
    return ProbabilityCalibrator(config=config)

def create_walk_forward_validator(
    config: Optional[Dict] = None,
) -> "WalkForwardValidator":
    """Factory — M2 Walk-Forward 驗證器"""
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator
    return WalkForwardValidator(config=config)

def create_sample_weight_calculator(
    config: Optional[Dict] = None,
) -> "SampleWeightCalculator":
    """Factory — M3 樣本加權計算器"""
    from momentum.Analysis.sample_weight_calculator import SampleWeightCalculator
    return SampleWeightCalculator(config=config)

def create_adversarial_validator(
    config: Optional[Dict] = None,
) -> "AdversarialValidator":
    """Factory — M4 Adversarial 驗證器"""
    from momentum.Analysis.adversarial_validator import AdversarialValidator
    return AdversarialValidator(config=config)

def create_combinatorial_purged_cv(
    config: Optional[Dict] = None,
) -> "CombinatorialPurgedCV":
    """Factory — M5 CPCV"""
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    return CombinatorialPurgedCV(config=config)

def create_learning_curve_analyzer(
    config: Optional[Dict] = None,
) -> "LearningCurveAnalyzer":
    """Factory — M6 Learning Curve 分析器"""
    from momentum.Analysis.learning_curve_analyzer import LearningCurveAnalyzer
    return LearningCurveAnalyzer(config=config)
```

**依賴**：Task 2.1-2.6（所有 M1-M6 模組必須先存在才能 import）

**驗收條件**：
- [ ] 使用 lazy import（`from ... import` 在函式內部）
- [ ] 不直接 import `api.*`
- [ ] 參數統一為 `config: Optional[Dict] = None`

**驗證檢查點**：
- PASS: `from momentum.factories import create_*` 可成功 import 並建立 6 個模組實例。
- PASS: 若任一目標模組尚未建立，factory import 立即失敗且錯誤可定位到對應模組。

**驗證命令**：
```bash
python -c "
from momentum.factories import (
    create_probability_calibrator,
    create_walk_forward_validator,
    create_sample_weight_calculator,
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
)
print('All 6 factories imported successfully')
# 實例化測試（需 Phase 2 完成）
cal = create_probability_calibrator()
print(f'ProbabilityCalibrator created: {type(cal).__name__}')
wf = create_walk_forward_validator()
print(f'WalkForwardValidator created: {type(wf).__name__}')
sw = create_sample_weight_calculator()
print(f'SampleWeightCalculator created: {type(sw).__name__}')
av = create_adversarial_validator()
print(f'AdversarialValidator created: {type(av).__name__}')
cpcv = create_combinatorial_purged_cv()
print(f'CombinatorialPurgedCV created: {type(cpcv).__name__}')
lc = create_learning_curve_analyzer()
print(f'LearningCurveAnalyzer created: {type(lc).__name__}')
"
```

---

### Task 1.1.4：API Models（Request/Response）

**說明**：定義所有 API 端點的 Request/Response Pydantic 模型（SPEC §11.2, §11.3）

**檔案**（新建）：`api/models/model_enhancement.py`

**Request Models**：

```python
class ModelEnhancementBaseRequest(BaseModel):
    """所有 M1-M6 Request 共用欄位"""
    model_task_id: str = Field(..., description="已訓練模型的 task_id")
    symbol: Optional[str] = None
    timeframe: Optional[str] = None

class CalibrateRequest(ModelEnhancementBaseRequest):
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=10)

class WalkForwardRequest(ModelEnhancementBaseRequest):
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=100, le=50000)
    test_size: int = Field(default=100, ge=20, le=10000)
    step_size: Optional[int] = None
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)

class SampleWeightRequest(ModelEnhancementBaseRequest):
    strategies: List[str] = Field(default=["time_decay", "class_balance"])
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=3650)

class AdversarialValidateRequest(ModelEnhancementBaseRequest):
    n_estimators: int = Field(default=100, ge=10, le=1000)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True

class CPCVRequest(ModelEnhancementBaseRequest):
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)

class LearningCurveRequest(ModelEnhancementBaseRequest):
    train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    feature_counts: Optional[List[int]] = None
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")

class FullEnhancementRequest(ModelEnhancementBaseRequest):
    modules: List[str] = Field(
        default=["calibration", "walk_forward", "sample_weight", "adversarial", "cpcv", "learning_curve"]
    )
    config_overrides: Optional[Dict[str, Any]] = None
```

**Response Models**：

```python
class ModelEnhancementResponse(BaseModel):
    task_id: str
    status: str = Field(pattern="^(running|completed|failed|skipped)$")
    module: str
    result: Optional[Dict[str, Any]] = None
    skipped_reason: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    created_at: str

class FullEnhancementResponse(BaseModel):
    task_id: str
    status: str
    modules: Dict[str, ModelEnhancementResponse]
    total_execution_time_seconds: float
```

**驗收條件**：
- [ ] 不 import `momentum.*`（Rule 7）
- [ ] 所有 Field 含驗證約束
- [ ] `FullEnhancementRequest.modules` 有預設值

**驗證檢查點**：
- PASS: 以最小 payload 建立 `CalibrateRequest(model_task_id='test-123')` 成功且預設值正確。
- PASS: 給定非法值（如 `cv=1` 或不合法 `method`）時，Pydantic 會拋出 `ValidationError`。

**驗證命令**：
```bash
python -c "
from api.models.model_enhancement import (
    CalibrateRequest, WalkForwardRequest, SampleWeightRequest,
    AdversarialValidateRequest, CPCVRequest, LearningCurveRequest,
    FullEnhancementRequest, ModelEnhancementResponse, FullEnhancementResponse,
)
# Validation test
r = CalibrateRequest(model_task_id='test-123')
assert r.method == 'auto'
print('API models OK')
"
```

---

## 5. Phase 2：核心模組 M1-M6

### 驗證檢查點

- PASS: M1-M6 單元測試全綠，且 C/W/S/A/P/L 邊界條件總數與 PLAN 宣告一致。
- PASS: 任一模組回傳 `SkippedResult` 或 timeout 時，其餘模組仍可獨立驗證，不發生連鎖中斷。

### Task 2.1：M1 ProbabilityCalibrator（P1 優先）

**說明**：機率校準修正引擎（SPEC §3）。擴展 `CalibrationAnalyzer` 的診斷能力為可執行的校準修正。支援 Platt/Isotonic/Beta/Venn-ABERS 四種方法 + auto 自動選擇。

**依賴**：Task 0.1（SkippedResult）、Task 0.2（betacal）

**檔案**（新建）：`momentum/Analysis/probability_calibrator.py`

**類別設計**：

```python
class ProbabilityCalibrator:
    """
    機率校準修正引擎
    
    業界依據:
    - Platt (1999): Sigmoid Calibration
    - Zadrozny & Elkan (2002): Isotonic Regression
    - Kull et al. (2017): Beta Calibration
    - Vovk et al. (2005): Venn-ABERS
    """

    def __init__(self, config: Optional[Dict] = None): ...

    # --- 核心介面 ---
    def fit(
        self, model: Any, X_cal: Union[pd.DataFrame, np.ndarray],
        y_cal: np.ndarray, method: str = 'auto', cv: Optional[int] = None,
    ) -> Dict[str, Any]: ...

    def fit_from_predictions(
        self, y_true: np.ndarray, y_pred_proba: np.ndarray, method: str = 'auto',
    ) -> Dict[str, Any]: ...

    def predict_calibrated(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray: ...

    def transform_proba(self, y_pred_proba: np.ndarray) -> np.ndarray: ...

    def get_calibration_comparison(self) -> Dict[str, Any]: ...

    def get_venn_abers_intervals(
        self, X: Union[pd.DataFrame, np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]: ...
```

**內部依賴**：
- `sklearn.calibration.CalibratedClassifierCV`（Platt, Isotonic）
- `betacal.BetaCalibration`（Beta — 若不可用 fallback 至 Platt）
- `momentum.Analysis.calibration_analyzer`（只讀引用 ECE/Brier 計算邏輯）

**邊界條件**（11 個 — SPEC §3.10）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| C1 | y_cal 全為同類別 | skip + `SkippedResult(SINGLE_CLASS)` | `test_C1_single_class` |
| C2 | y_pred_proba 全為 0 或 1 | skip + `SkippedResult(ZERO_VARIANCE)` | `test_C2_zero_variance_proba` |
| C3 | len(y_cal) < 50 | 警告 + auto 切換 Platt | `test_C3_small_sample_auto_fallback` |
| C4 | method='isotonic' 且 n < 1000 | 警告 + fallback Platt | `test_C4_isotonic_small_sample_fallback` |
| C5 | method='venn_abers' 且 n > 5000 | 穩定降採樣至 max_samples | `test_C5_venn_abers_downsampling` |
| C6 | cv > len(y_cal) / 2 | auto 降低 cv | `test_C6_cv_exceeds_half_samples` |
| C7 | 校準後 ECE 上升 | fallback 返回原始機率 + `calibration_failed=True` | `test_C7_calibration_degradation_fallback` |
| C8 | 未 fit 即 predict | raise `ValueError` | `test_C8_predict_before_fit` |
| C9 | y_pred_proba 含 NaN | dropna 後校準，剩餘 < 50 則 skip | `test_C9_nan_in_predictions` |
| C10 | betacal 不可用 | fallback Platt + warning | `test_C10_beta_package_missing_fallback` |
| C11 | X_cal 特徵數不匹配 | raise `ValueError` | `test_C11_feature_mismatch` |

**輸出 Schema**（SPEC §3.8）：

```json
{
  "probability_calibration": {
    "method": "platt",
    "comparison": {
      "original": {"ece": 0.082, "brier": 0.205},
      "platt": {"ece": 0.031, "brier": 0.178},
      "isotonic": {"ece": 0.025, "brier": 0.172},
      "beta": {"ece": 0.028, "brier": 0.175}
    },
    "best_method": "isotonic",
    "improvement_pct": 69.5,
    "calibration_failed": false,
    "reliability_curve": { "bin_midpoints": [...], "original_freq": [...], "calibrated_freq": [...] },
    "sample_size": 1500,
    "cv_folds": 5
  }
}
```

**驗收條件**：
- [ ] `fit()` 和 `fit_from_predictions()` 兩種入口皆可使用
- [ ] `method='auto'` 時自動比較所有合格方法，選 ECE 最低
- [ ] 校準後 ECE ≤ 校準前 ECE（合成資料驗證）
- [ ] 11 個邊界條件全部有對應測試
- [ ] 不 import `api.*`

**驗證檢查點**：
- PASS: `fit_from_predictions()` 合成資料 → `ECE_after < ECE_before`
- PASS: 11 個邊界條件測試全部綠燈
- FAIL: `fit()` 後 `calibration_failed=True` 時原始機率被正確保留

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_probability_calibrator.py -v --tb=short
```

---

### Task 2.2：M2 WalkForwardValidator（P1 優先）

**說明**：Walk-Forward 滾動驗證引擎（SPEC §4）。支援 Rolling/Expanding 兩種模式，內建 Purge + Embargo。

**依賴**：Task 0.1（SkippedResult）

**檔案**（新建）：`momentum/Analysis/model_validation/walk_forward_validator.py`

**類別設計**：

```python
class WalkForwardValidator:
    """
    Walk-Forward 滾動驗證引擎
    
    業界依據:
    - Pardo (2008): Trading Strategy Evaluation
    - Bailey & López de Prado (2014): Deflated Sharpe Ratio
    """

    def __init__(self, config: Optional[Dict] = None): ...

    def validate_rolling(
        self, model_factory: Callable[[], Any], X: pd.DataFrame, y: np.ndarray,
        feature_names: List[str], train_size: int, test_size: int,
        step_size: Optional[int] = None,
    ) -> WalkForwardReport: ...

    def validate_expanding(
        self, model_factory: Callable[[], Any], X: pd.DataFrame, y: np.ndarray,
        feature_names: List[str], initial_train_size: int, test_size: int,
        step_size: Optional[int] = None,
    ) -> WalkForwardReport: ...

    def _run_single_period(
        self, model_factory: Callable, X_train, y_train, X_test, y_test,
        feature_names: List[str], period_index: int,
        train_range: Tuple[int, int], test_range: Tuple[int, int],
    ) -> WalkForwardPeriodResult: ...

    def _generate_rolling_splits(
        self, n_samples: int, train_size: int, test_size: int, step_size: int,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]: ...

    def _assess_stability(self, report: WalkForwardReport) -> str: ...
```

**Dataclass 定義**（同檔案內）：

```python
@dataclass
class WalkForwardPeriodResult:
    period_index: int
    train_start_idx: int; train_end_idx: int
    test_start_idx: int; test_end_idx: int
    train_samples: int; test_samples: int
    test_auc: Optional[float]
    test_precision_at_k: Optional[float]
    test_brier_score: Optional[float]
    is_auc: Optional[float]
    is_oos_gap: Optional[float]
    top_features: List[str]

@dataclass
class WalkForwardReport:
    mode: str; n_periods: int
    period_results: List[WalkForwardPeriodResult]
    mean_oos_auc: float; std_oos_auc: float
    min_oos_auc: float; max_oos_auc: float
    oos_hit_rate: float; mean_is_oos_gap: float
    auc_trend: str; degradation_periods: List[int]
    feature_stability: Dict[str, float]
    assessment: str
```

**內部依賴**：
- `momentum.Analysis.time_splitter`（只讀引用 purge/embargo 邏輯）

**邊界條件**（10 個 — SPEC §4.9）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| W1 | train_size + test_size + purge > len(X) | skip + `SkippedResult(INSUFFICIENT_DATA)` | `test_W1_data_too_short` |
| W2 | train_size < 50 | 警告 | `test_W2_small_train_window` |
| W3 | 只能產出 1-2 期 | 警告 + 依然回傳 | `test_W3_minimal_periods` |
| W4 | 某期 y 全同類別 | 該期 `test_auc=None`，不計入統計 | `test_W4_single_class_test_period` |
| W5 | step_size > test_size | 允許 + 警告 | `test_W5_step_larger_than_test` |
| W6 | purge_gap >= test_size | raise `ValueError` | `test_W6_purge_exceeds_test` |
| W7 | 某期模型訓練失敗 | skip 該期，繼續下期 | `test_W7_training_failure_single_period` |
| W8 | mode='both' | 同時回傳 rolling + expanding | `test_W8_both_modes` |
| W9 | 所有期 AUC < 0.5 | `assessment='unstable'` + 警告 | `test_W9_all_periods_below_random` |
| W10 | expanding train OOM | 不在本模組處理 | `test_W10_expanding_memory_warning` |

**驗收條件**：
- [ ] Rolling / Expanding 兩種模式均可正常運作
- [ ] Purge gap + embargo 與 `PurgedTimeSeriesSplit` 邏輯一致
- [ ] `_assess_stability()` 按 SPEC 標準判定 robust/moderate/unstable
- [ ] 10 個邊界條件全部有對應測試
- [ ] feature_stability 統計頻率正確

**輸出 Schema**（SPEC §4.7）：

```json
{
  "walk_forward": {
    "mode": "rolling",
    "config": { "train_size": 500, "test_size": 100, "step_size": 100, "purge_gap": 5, "embargo_pct": 0.01 },
    "n_periods": 8,
    "summary": {
      "mean_oos_auc": 0.628, "std_oos_auc": 0.042,
      "min_oos_auc": 0.562, "max_oos_auc": 0.695,
      "oos_hit_rate": 1.0, "mean_is_oos_gap": 0.035,
      "auc_trend": "stable", "assessment": "robust"
    },
    "period_results": [
      { "period_index": 0, "train_samples": 500, "test_samples": 100,
        "is_auc": 0.682, "test_auc": 0.645, "is_oos_gap": 0.037,
        "test_brier_score": 0.195, "top_features": ["close_RSI_14", "taker_ratio_EMA_21"] }
    ],
    "feature_stability": { "close_RSI_14": 1.0, "taker_ratio_EMA_21": 0.875 },
    "degradation_periods": []
  }
}
```

**穩定性評估規則**（SPEC §4.6）：
- `robust`：`oos_hit_rate >= 0.7` AND `mean_is_oos_gap < 0.05`
- `moderate`：`oos_hit_rate >= 0.5` AND `mean_is_oos_gap < 0.10`
- `unstable`：其他

**驗證檢查點**：
- PASS: 合成 1200 筆資料 → rolling(train=500, test=100) → 至少 3 periods
- PASS: `_assess_stability()` 對 all-AUC > 0.6 data → `'robust'`
- PASS: purge_gap=5 的 split 中 train_end + 5 <= test_start

**驗證命令**：
```bash
pytest tests/momentum/Analysis/model_validation/test_walk_forward_validator.py -v --tb=short
```

---

### Task 2.3：M3 SampleWeightCalculator（P2 優先）

**說明**：樣本加權計算器（SPEC §5）。提供 time_decay / class_balance / return_based / uniqueness 四種策略，可組合。

**依賴**：Task 0.1（SkippedResult）

**檔案**（新建）：`momentum/Analysis/sample_weight_calculator.py`

**類別設計**：

```python
class SampleWeightCalculator:
    """
    樣本加權計算器
    
    業界依據:
    - López de Prado (2018) Ch.4: Sample Uniqueness
    - Two Sigma / Citadel: Time Decay Weighting
    """

    def __init__(self, config: Optional[Dict] = None): ...

    def compute_time_decay(
        self, timestamps: np.ndarray, half_life: Optional[int] = None,
        decay_type: str = 'exponential',
    ) -> np.ndarray: ...

    def compute_class_balance(
        self, y: np.ndarray, method: str = 'balanced',
        custom_ratio: Optional[float] = None,
    ) -> np.ndarray: ...

    def compute_return_based(
        self, returns: np.ndarray, method: str = 'abs_return',
    ) -> np.ndarray: ...

    def compute_uniqueness(
        self, label_spans: List[Tuple[int, int]], n_samples: int,
    ) -> np.ndarray: ...

    def compute_combined_weights(
        self, timestamps=None, y=None, returns=None, label_spans=None,
        strategies: List[str] = ['time_decay', 'class_balance'],
        combination: str = 'multiply', **kwargs,
    ) -> np.ndarray: ...

    def get_weight_summary(self, weights: np.ndarray) -> Dict[str, float]: ...
```

**數學公式**：
- Time Decay: $w_i = \max(\exp(-\lambda \cdot (t_{\max} - t_i)),\; w_{\min})$，$\lambda = \frac{\ln 2}{\text{half\_life}}$
- Uniqueness: $u_t = \frac{1}{\sum_s \mathbb{1}[t \in \text{span}(s)]}$，$w_i = \bar{u}_i$

**邊界條件**（10 個 — SPEC §5.9）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| S1 | half_life ≤ 0 | raise `ValueError` | `test_S1_invalid_half_life` |
| S2 | timestamps 非單調遞增 | 自動排序 + 警告 | `test_S2_unsorted_timestamps` |
| S3 | 全部 returns = 0 | 等權重 + 警告 | `test_S3_zero_returns` |
| S4 | y 全為同類別 | class_balance 等權重 + 警告 | `test_S4_single_class_weight` |
| S5 | min_weight > 1.0 | raise `ValueError` | `test_S5_invalid_min_weight` |
| S6 | n_samples < 10 | 警告 | `test_S6_tiny_sample` |
| S7 | strategies 為空 | 回傳等權重 | `test_S7_no_strategies` |
| S8 | label_spans 重疊 > 99% | 切換 time_decay | `test_S8_extreme_label_overlap` |
| S9 | combination='additive' 無係數 | 等權重 | `test_S9_additive_default_coeffs` |
| S10 | timestamps 含 NaN | drop NaN + 重算 | `test_S10_nan_timestamps` |

**驗收條件**：
- [ ] 所有權重歸一化至均值 1.0
- [ ] `compute_combined_weights()` 支援 multiply / additive 兩種組合
- [ ] uniqueness 無 label_spans 時自動 fallback 至 time_decay
- [ ] `get_weight_summary()` 含 effective_n 和 efficiency_ratio

**輸出 Schema**（SPEC §5.7）：

```json
{
  "sample_weights": {
    "strategies_applied": ["time_decay", "class_balance"],
    "combination": "multiply",
    "summary": {
      "n_samples": 2000,
      "effective_n": 1234.5,
      "efficiency_ratio": 0.617,
      "weight_mean": 1.0,
      "weight_std": 0.342,
      "weight_min": 0.01,
      "weight_max": 3.45
    },
    "per_strategy": {
      "time_decay": { "half_life": 180, "type": "exponential" },
      "class_balance": { "method": "balanced", "pos_weight": 2.33, "neg_weight": 0.70 }
    }
  }
}
```

**驗證檢查點**：
- PASS: `compute_time_decay()` 最新樣本權重 > 最舊樣本權重
- PASS: `compute_class_balance()` 少數類權重 > 多數類權重
- PASS: `get_weight_summary()` 含 `effective_n` 且 0 < effective_n <= n_samples

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_sample_weight_calculator.py -v --tb=short
```

---

### Task 2.4：M4 AdversarialValidator（P2 優先）

**說明**：Adversarial Validation + Feature-Level Tests + Temporal Leakage Detection（SPEC §6）。

**依賴**：Task 0.1（SkippedResult）

**檔案**（新建）：`momentum/Analysis/adversarial_validator.py`

**類別設計**：

```python
class AdversarialValidator:
    """
    Adversarial Validation + Feature-Level Tests + Temporal Leakage Detection
    
    業界依據:
    - ZFTurbo (2015): Kaggle Adversarial Validation
    - Pan et al. (2020): Domain Adaptation for Financial Data
    """

    def __init__(self, config: Optional[Dict] = None): ...

    def validate_distribution(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame,
    ) -> Dict[str, Any]: ...

    def feature_level_tests(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame, method: str = 'ks',
    ) -> Dict[str, Dict]: ...

    def detect_leakage(
        self, X: pd.DataFrame, y: np.ndarray, timestamps: np.ndarray,
        future_window: int = 5,
    ) -> Dict[str, Any]: ...

    def full_validation(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame,
        y_train: Optional[np.ndarray] = None, timestamps: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]: ...
```

**AUC 判斷閾值**：
- AUC ≈ 0.50 → `status='good'`
- AUC ∈ [0.55, 0.70) → `status='warning'`
- AUC ≥ 0.70 → `status='severe'`

**邊界條件**（8 個 — SPEC §6.8）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| A1 | X_train 和 X_test 欄位不一致 | raise `ValueError` | `test_A1_feature_name_mismatch` |
| A2 | X_test 樣本數 < 20 | 警告 + AUC 不可靠 | `test_A2_tiny_test_set` |
| A3 | X_train == X_test | AUC ≈ 0.5, `status='good'` | `test_A3_identical_distributions` |
| A4 | timestamps=None | 跳過 leakage detection | `test_A4_no_timestamps_skip_leakage` |
| A5 | future_window > len(X)/2 | raise `ValueError` | `test_A5_extreme_future_window` |
| A6 | 所有特徵 KS p-value < 0.01 | 所有 `status='severe'` | `test_A6_all_features_drifted` |
| A7 | 特徵含全 NaN | 跳過該特徵 KS/PSI | `test_A7_all_nan_feature` |
| A8 | X_train 或 X_test 為空 | skip + `SkippedResult` | `test_A8_empty_dataset` |

**驗收條件**：
- [ ] 內建輕量 LightGBM 做分佈辨識（`n_estimators=100`）
- [ ] 同時支援 KS test 和 PSI 兩種 feature-level 測試
- [ ] temporal leakage detection 檢查 autocorrelation
- [ ] 不依賴外部訓練模型

**輸出 Schema**（SPEC §6.6）：

```json
{
  "adversarial_validation": {
    "distribution_test": {
      "auc": 0.58, "std": 0.03,
      "status": "warning",
      "top_discriminating_features": ["feature_3", "feature_7"]
    },
    "feature_level_tests": {
      "feature_3": { "ks_statistic": 0.15, "ks_pvalue": 0.002, "psi": 0.12, "status": "warning" },
      "feature_7": { "ks_statistic": 0.22, "ks_pvalue": 0.0001, "psi": 0.18, "status": "severe" }
    },
    "leakage_detection": {
      "suspicious_features": ["feature_5"],
      "autocorrelation_flags": { "feature_5": { "lag_1_corr": 0.92, "is_suspicious": true } }
    },
    "overall_status": "warning",
    "recommendations": ["考慮移除 feature_7", "檢查 feature_5 時間洩漏"]
  }
}
```

**驗證檢查點**：
- PASS: 合成同分佈 X_train/X_test → AUC ≈ 0.5 (±0.05)
- PASS: 合成 drift data (X_test += 2.0) → AUC > 0.7, `status='severe'`
- PASS: KS test p-value < 0.01 的特徵 → `status='severe'`

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_adversarial_validator.py -v --tb=short
```

---

### Task 2.5：M5 CombinatorialPurgedCV（P2 優先）

**說明**：Combinatorial Purged Cross-Validation + Backtest Path Generation（SPEC §7）。

**依賴**：Task 0.1（SkippedResult）

**檔案**（新建）：`momentum/Analysis/model_validation/combinatorial_purged_cv.py`

**類別設計**：

```python
class CombinatorialPurgedCV:
    """
    Combinatorial Purged Cross-Validation (CPCV)
    
    López de Prado (2018): AFML Chapter 12
    """

    def __init__(self, config: Optional[Dict] = None): ...

    def split(
        self, X: pd.DataFrame, y: Optional[np.ndarray] = None,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]: ...

    def validate(
        self, model_factory: Callable[[], Any], X: pd.DataFrame,
        y: np.ndarray, feature_names: List[str],
    ) -> Dict[str, Any]: ...

    def generate_backtest_paths(
        self, n_groups: int, n_test_groups: int,
    ) -> List[List[Tuple[int, ...]]]: ...

    def _compute_group_boundaries(self, n_samples: int) -> List[Tuple[int, int]]: ...

    def _apply_purge_embargo(
        self, train_indices: np.ndarray, test_groups: List[Tuple[int, int]], n_samples: int,
    ) -> np.ndarray: ...
```

**數學**：$\text{CPCV}(N, k) = \binom{N}{k}$ paths。例如 $N=6, k=2 \Rightarrow 15$ paths。

**邊界條件**（9 個 — SPEC §7.7）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| P1 | n_groups < 3 | raise `ValueError` | `test_P1_too_few_groups` |
| P2 | n_test_groups >= n_groups | raise `ValueError`（Pydantic） | `test_P2_test_groups_exceed` |
| P3 | C(N,k) > max_paths | 隨機取樣 | `test_P3_path_sampling_coverage` |
| P4 | group 樣本數 < 20 | 警告 | `test_P4_small_group` |
| P5 | purge_gap > group_size | raise `ValueError` | `test_P5_purge_exceeds_group` |
| P6 | 某 path 訓練失敗 | skip 該 path | `test_P6_single_path_failure` |
| P7 | 所有 path AUC = NaN | skip 整個模組 | `test_P7_all_paths_nan` |
| P8 | N=6, k=2（標準） | 驗證 15 paths | `test_P8_standard_6_2_cpcv` |
| P9 | embargo 導致 train 為空 | auto 降低 embargo_pct | `test_P9_embargo_empties_train` |

**驗收條件**：
- [ ] `split()` 產出 Iterator 可用於 sklearn 風格 CV
- [ ] `validate()` 回傳含 `path_aucs`, `backtest_paths`, `feature_stability`
- [ ] C(6,2) = 15 paths 驗證數量正確
- [ ] purge/embargo 邏輯復用 `time_splitter.py`

**輸出 Schema**（SPEC §7.5）：

```json
{
  "cpcv": {
    "config": { "n_groups": 6, "n_test_groups": 2, "purge_gap": 5 },
    "n_paths": 15,
    "summary": {
      "mean_auc": 0.612, "std_auc": 0.038,
      "min_auc": 0.548, "max_auc": 0.678,
      "hit_rate": 0.933
    },
    "path_results": [
      { "path_index": 0, "test_groups": [0, 1], "auc": 0.645, "n_train": 1600, "n_test": 400 }
    ],
    "backtest_paths": [[0, 1], [0, 2], [0, 3], [0, 4], [0, 5]],
    "feature_stability": { "close_RSI_14": 0.93, "volume_MA_34": 0.80 }
  }
}
```

**驗證檢查點**：
- PASS: `generate_backtest_paths(6, 2)` → 回傳 15 paths
- PASS: `split()` 產出的 train/test indices 不重疊（purge 後）
- PASS: 每個 path 的 test 組合不重複

**驗證命令**：
```bash
pytest tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py -v --tb=short
```

---

### Task 2.6：M6 LearningCurveAnalyzer（P3 優先）

**說明**：Learning Curve 分析器（SPEC §8）。含資料量/特徵量 vs 效能曲線 + Bias-Variance 診斷。

**依賴**：Task 0.1（SkippedResult）

**檔案**（新建）：`momentum/Analysis/learning_curve_analyzer.py`

**類別設計**：

```python
class LearningCurveAnalyzer:
    """
    Learning Curve 分析器
    
    幫助研究者判斷：
    1. 需要更多資料還是更好的特徵？
    2. 最佳特徵數量是多少？
    3. 模型是否過擬合/欠擬合？
    """

    def __init__(self, config: Optional[Dict] = None): ...

    def analyze_data_curve(
        self, model_factory: Callable[[], Any], X: pd.DataFrame, y: np.ndarray,
        feature_names: List[str], train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
    ) -> Dict[str, Any]: ...

    def analyze_feature_curve(
        self, model_factory: Callable[[], Any], X: pd.DataFrame, y: np.ndarray,
        feature_names: List[str], feature_counts: Optional[List[int]] = None,
        ranking_method: str = 'gain',
    ) -> Dict[str, Any]: ...

    def diagnose_bias_variance(
        self, train_scores: List[float], cv_scores: List[float], fractions: List[float],
    ) -> Dict[str, Any]: ...

    def full_analysis(
        self, model_factory: Callable[[], Any], X: pd.DataFrame, y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]: ...
```

**Bias-Variance 診斷規則**：
- **high_bias**：train_score 低 + cv_score 低 + gap 小 → 需更好特徵
- **high_variance**：train_score 高 + cv_score 低 + gap 大 → 需更多資料/正則化
- **good_fit**：train_score 適中 + cv_score 適中 + gap 合理

**邊界條件**（8 個 — SPEC §8.8）：

| # | 條件 | 處理 | 測試函式 |
|---|------|------|---------|
| L1 | train_fractions 含 0 或負數 | raise `ValueError` | `test_L1_invalid_fraction` |
| L2 | 最小比例 × n < 20 | 跳過該比例 | `test_L2_fraction_too_small` |
| L3 | feature_counts 超過實際特徵數 | 自動裁剪 | `test_L3_feature_count_exceeds` |
| L4 | 所有比例 CV AUC < 0.52 | `diagnosis="模型無預測力"` | `test_L4_no_predictive_power` |
| L5 | 某比例 fold AUC = NaN | 跳過該比例 | `test_L5_nan_fold` |
| L6 | ranking='shap' 但 SHAP 不可用 | fallback 'gain' | `test_L6_shap_unavailable` |
| L7 | 單一特徵 | feature_curve 只 1 點 | `test_L7_single_feature` |
| L8 | n_samples < 200 | 警告 | `test_L8_small_dataset` |

**驗收條件**：
- [ ] `analyze_data_curve()` 在多比例上訓練，回傳 train/cv scores
- [ ] `analyze_feature_curve()` 按 importance 排名逐步增加特徵
- [ ] `diagnose_bias_variance()` 正確判定 high_bias / high_variance / good_fit
- [ ] `full_analysis()` 同時執行資料量 + 特徵量 + Bias-Variance

**輸出 Schema**（SPEC §8.6）：

```json
{
  "learning_curve": {
    "data_curve": {
      "fractions": [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
      "train_scores": [0.85, 0.78, 0.72, 0.69, 0.67, 0.66],
      "cv_scores": [0.52, 0.56, 0.59, 0.61, 0.62, 0.63],
      "cv_stds": [0.08, 0.06, 0.04, 0.03, 0.03, 0.02]
    },
    "feature_curve": {
      "feature_counts": [5, 10, 20, 30, 50],
      "cv_scores": [0.58, 0.61, 0.63, 0.62, 0.61],
      "optimal_n_features": 20,
      "feature_ranking": ["close_RSI_14", "volume_MA_34", "taker_ratio_EMA_21"]
    },
    "diagnosis": {
      "type": "high_variance",
      "description": "模型過擬合：train_score 高但 cv_score 低，gap 大。建議增加資料或正則化。",
      "train_cv_gap": 0.03,
      "convergence": false,
      "recommendation": "增加訓練資料 or 增加正則化"
    }
  }
}
```

**驗證檢查點**：
- PASS: 合成資料 → `diagnose_bias_variance()` 對 high gap → `'high_variance'`
- PASS: `analyze_feature_curve()` 的 `optimal_n_features` 落在合理範圍
- PASS: 8 個邊界條件測試全部綠燈

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_learning_curve_analyzer.py -v --tb=short
```

---

## 6. Phase 3：API 層

### 驗證檢查點

- PASS: 8 個 API 端點可於 OpenAPI 顯示並通過 request schema 驗證。
- PASS: 非法 request 觸發 4xx 驗證錯誤，且不誤執行對應 Service 任務。

### Task 3.1：ModelEnhancementService

**說明**：Service 層負責任務管理、Factory 呼叫、錯誤處理（SPEC §11.5）。

**依賴**：Task 1.1.3（Factory）、Task 1.1.4（API Models）、Phase 2 全部

**檔案**（新建）：`api/services/model_enhancement_service.py`

**類別設計**：

```python
class ModelEnhancementService:
    """
    Model Enhancement 服務層
    
    職責：
    1. 管理非同步任務
    2. 透過 momentum/factories.py 建立模組（Rule 3）
    3. 執行模組並收集結果
    4. 處理 SkippedResult 和錯誤分類
    """

    def __init__(
        self,
        calibrator_factory: Callable = None,
        walk_forward_factory: Callable = None,
        sample_weight_factory: Callable = None,
        adversarial_factory: Callable = None,
        cpcv_factory: Callable = None,
        learning_curve_factory: Callable = None,
    ): ...

    async def execute_calibration(self, request: CalibrateRequest) -> ModelEnhancementResponse: ...
    async def execute_walk_forward(self, request: WalkForwardRequest) -> ModelEnhancementResponse: ...
    async def execute_sample_weights(self, request: SampleWeightRequest) -> ModelEnhancementResponse: ...
    async def execute_adversarial(self, request: AdversarialValidateRequest) -> ModelEnhancementResponse: ...
    async def execute_cpcv(self, request: CPCVRequest) -> ModelEnhancementResponse: ...
    async def execute_learning_curve(self, request: LearningCurveRequest) -> ModelEnhancementResponse: ...
    async def execute_full_enhancement(self, request: FullEnhancementRequest) -> FullEnhancementResponse: ...
    def get_task_status(self, task_id: str) -> Optional[ModelEnhancementResponse]: ...
```

**非同步任務狀態管理**（復用現有 `SearchTaskService` 模式）：

```python
class ModelEnhancementService:
    def __init__(self, ...):
        ...
        self._task_results: Dict[str, ModelEnhancementResponse] = {}
    
    async def execute_calibration(self, request) -> ModelEnhancementResponse:
        task_id = str(uuid.uuid4())
        self._task_results[task_id] = ModelEnhancementResponse(
            task_id=task_id, status='running', module='calibration', ...
        )
        # Background task updates self._task_results[task_id] on completion
        asyncio.create_task(self._run_and_store(task_id, ...))
        return self._task_results[task_id]
    
    def get_task_status(self, task_id: str) -> Optional[ModelEnhancementResponse]:
        return self._task_results.get(task_id)
```

**依賴注入**：
- 所有 `_factory` 預設使用 `momentum.factories` 的 `create_*` 函式
- `execute_full_enhancement()` 使用 `asyncio.gather` 並行無依賴模組

**Error Chain（SPEC §14.2, §14.4）**：

```
Module 層 (momentum/Analysis/*.py)
├─ try: 執行核心邏輯
├─ except → return SkippedResult(...)
└─ Module 不 raise，只回傳 SkippedResult 或正常結果

Service 層 (api/services/model_enhancement_service.py)
├─ 收到 SkippedResult → 轉換為 ModelEnhancementResponse(status='skipped')
├─ 收到正常結果 → 轉換為 ModelEnhancementResponse(status='completed')
├─ 意外 Exception → log ERROR + ModelEnhancementResponse(status='failed')
└─ Timeout → log ERROR + ModelEnhancementResponse(status='failed', reason='timeout')

Route 層 (api/routes/model_enhancement.py)
├─ 收到 Response → 直接回傳（FastAPI 自動序列化）
└─ 意外 Exception → FastAPI 全域 exception handler
```

**Service Lifespan 初始化**（`api/main.py` 修改）：

```python
# api/main.py — lifespan context 或 module-level singleton
from momentum.factories import (
    create_probability_calibrator,
    create_walk_forward_validator,
    create_sample_weight_calculator,
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
)

_model_enhancement_service: Optional[ModelEnhancementService] = None

def get_model_enhancement_service() -> ModelEnhancementService:
    global _model_enhancement_service
    if _model_enhancement_service is None:
        _model_enhancement_service = ModelEnhancementService(
            calibrator_factory=create_probability_calibrator,
            walk_forward_factory=create_walk_forward_validator,
            sample_weight_factory=create_sample_weight_calculator,
            adversarial_factory=create_adversarial_validator,
            cpcv_factory=create_combinatorial_purged_cv,
            learning_curve_factory=create_learning_curve_analyzer,
        )
    return _model_enhancement_service
```

**Full Enhancement 併行策略**：

```python
async def execute_full_enhancement(self, request):
    # M1/M3 互相無依賴 → 可平行
    # M2/M5/M6 互相無依賴 → 可平行
    # M4 無依賴 → 可與任何模組平行
    results = await asyncio.gather(
        self.execute_calibration(...),
        self.execute_walk_forward(...),
        self.execute_sample_weights(...),
        self.execute_adversarial(...),
        self.execute_cpcv(...),
        self.execute_learning_curve(...),
        return_exceptions=True,
    )
```

**Per-Module Timeout 實作模式**（§2.4）：

```python
async def execute_calibration(self, request: CalibrateRequest) -> ModelEnhancementResponse:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(self._run_calibration, request),
            timeout=TIMEOUT_CALIBRATOR,
        )
        if isinstance(result, SkippedResult):
            return ModelEnhancementResponse(status='skipped', skipped_reason=result.reason, ...)
        return ModelEnhancementResponse(status='completed', result=result, ...)
    except asyncio.TimeoutError:
        logger.error(f"Calibration timeout after {TIMEOUT_CALIBRATOR}s")
        return ModelEnhancementResponse(status='failed', skipped_reason='timeout', ...)
```

**Request → Config Dict 轉換橋接**：

```python
def _request_to_config(self, request: CalibrateRequest) -> Dict:
    """將 API Request 轉換為 Module Config dict"""
    return request.model_dump(exclude={'model_task_id', 'symbol', 'timeframe'})
```

**驗收條件**：
- [ ] 全部透過 Factory 建立模組（Rule 3）
- [ ] 不直接 import `momentum.Analysis.*` 的 concrete class
- [ ] 不 import 其他 `api/services/*`（Rule 4）
- [ ] `execute_full_enhancement()` 併行化無依賴模組
- [ ] 每個模組有 per-module timeout 保護
- [ ] `SkippedResult` 轉換為 `ModelEnhancementResponse(status='skipped')`

**驗證檢查點**：
- PASS: `execute_full_enhancement()` 回傳 6 個模組結果，且成功模組狀態為 `completed`。
- PASS: 任一模組 timeout 或回傳 `SkippedResult` 時，不中斷其餘模組並分別標記 `failed` 或 `skipped`。

**驗證命令**：
```bash
# 確認 Rule 3
grep "from momentum\." api/services/model_enhancement_service.py | grep -v "from momentum.factories" | grep -v "from momentum.core"
# 期望：無結果

# 確認 Rule 4
grep "from api.services" api/services/model_enhancement_service.py
# 期望：無結果

pytest tests/api/test_model_enhancement_service.py -v --tb=short
```

---

### Task 3.2：Route Handlers

**說明**：8 個 API 端點的 Route Handlers（SPEC §11.1, §11.4）。

**檔案**（新建）：`api/routes/model_enhancement.py`

**端點清單**：

| # | 方法 | 路徑 | 說明 |
|---|------|------|------|
| 1 | POST | `/api/v1/model-enhancement/calibrate` | M1 機率校準 |
| 2 | POST | `/api/v1/model-enhancement/walk-forward` | M2 Walk-Forward |
| 3 | POST | `/api/v1/model-enhancement/sample-weights` | M3 樣本權重 |
| 4 | POST | `/api/v1/model-enhancement/adversarial-validate` | M4 Adversarial |
| 5 | POST | `/api/v1/model-enhancement/cpcv` | M5 CPCV |
| 6 | POST | `/api/v1/model-enhancement/learning-curve` | M6 Learning Curve |
| 7 | GET | `/api/v1/model-enhancement/task/{task_id}` | 查詢任務狀態 |
| 8 | POST | `/api/v1/model-enhancement/full-enhancement` | 一鍵全執行 |

**Route Handler 結構**（薄層，所有邏輯在 Service）：

```python
router = APIRouter(prefix="/api/v1/model-enhancement", tags=["Model Enhancement"])

@router.post("/calibrate", response_model=ModelEnhancementResponse)
async def calibrate(request: CalibrateRequest):
    service = get_model_enhancement_service()
    return await service.execute_calibration(request)

# ... 其他端點相同模式
```

**Router 註冊**：在 `api/main.py` 的 router 註冊區塊新增：
```python
from api.routes.model_enhancement import router as model_enhancement_router
app.include_router(model_enhancement_router)
```

**驗收條件**：
- [ ] Route handler 為薄層（≤ 5 行），業務邏輯在 Service
- [ ] 8 個端點均回應 2xx（功能驗收 F7）
- [ ] router prefix = `/api/v1/model-enhancement`
- [ ] 在 `api/main.py` 中正確註冊

**驗證檢查點**：
- PASS: 8 個端點在 OpenAPI 文件可見且對應 request/response model 正常註冊。
- PASS: 請求 body 不合法時回傳 4xx 驗證錯誤，且不觸發 service 執行邏輯。

**驗證命令**：
```bash
# 啟動 API 後
curl -s http://localhost:8000/docs | grep "model-enhancement" | head -5
pytest tests/api/test_model_enhancement_routes.py -v --tb=short
```

---

## 7. Phase 4：前端層

### 驗證檢查點

- PASS: TypeScript 型別、Store、C23-C27 元件可在建構流程通過且正常渲染資料。
- PASS: 任一圖表收到空資料或缺欄位資料時，應顯示空狀態或降級畫面且不崩潰。

### Task 4.1：TypeScript 型別 + Zustand Store

**說明**：新增前端型別定義和狀態管理（SPEC §12.3, §12.4）。

**依賴**：Task 1.1.4（API Models — TypeScript 型別需與 API Response 對齊）

**檔案**（修改）：`frontend/src/lib/types.ts`

**新增型別**：
- `CalibrationResult` — M1 校準結果
- `WalkForwardResult` / `WalkForwardPeriod` — M2 Walk-Forward
- `AdversarialResult` — M4 Adversarial
- `CPCVResult` — M5 CPCV
- `LearningCurveResult` — M6 Learning Curve
- `ModelEnhancementResult` — 全域結果

**檔案**（新建）：`frontend/src/store/modelEnhancementStore.ts`

```typescript
import { create } from 'zustand';
import type { ModelEnhancementResult } from '@/lib/types';

interface ModelEnhancementState {
  currentResult: ModelEnhancementResult | null;
  isRunning: boolean;
  activeModules: string[];
  setResult: (result: ModelEnhancementResult) => void;
  setRunning: (running: boolean) => void;
  setActiveModules: (modules: string[]) => void;
  reset: () => void;
}

export const useModelEnhancementStore = create<ModelEnhancementState>((set) => ({
  currentResult: null,
  isRunning: false,
  activeModules: ['calibration', 'walk_forward', 'sample_weight', 'adversarial', 'cpcv', 'learning_curve'],
  setResult: (result) => set({ currentResult: result }),
  setRunning: (running) => set({ isRunning: running }),
  setActiveModules: (modules) => set({ activeModules: modules }),
  reset: () => set({ currentResult: null, isRunning: false }),
}));
```

**驗收條件**：
- [ ] 所有 TypeScript interface 與 SPEC §12.3 一致
- [ ] Zustand store pattern 與現有 `searchStore.ts` / `optimizationStore.ts` 一致
- [ ] TypeScript 編譯無錯誤

**驗證檢查點**：
- PASS: `npx tsc --noEmit` 通過，型別可正確約束 `ModelEnhancementResult`。
- PASS: 當 API 欄位型別不一致時，TypeScript 編譯會失敗並指出不相容欄位。

**驗證命令**：
```bash
cd frontend && npx tsc --noEmit
```

---

### Task 4.2：CalibrationPlot (C23)

**說明**：校準曲線圖表元件（SPEC §12.2 — C23）。顯示 diagonal 基準線 + 校準前後的 reliability curve。

**依賴**：Task 4.1（CalibrationResult 型別）

**檔案**（新建）：`frontend/src/components/optimization/CalibrationPlot.tsx`

**Props**：
```typescript
interface CalibrationPlotProps {
  data: CalibrationResult;
  onExportPNG?: () => void;
}
```

**驗收條件**：
- [ ] Line Chart 顯示 diagonal + original + calibrated 三條線
- [ ] 空資料顯示 EmptyState
- [ ] 支援 PNG 匯出
- [ ] 自適應容器寬度（`ResponsiveContainer`）

**驗證檢查點**：
- PASS: `data` 完整時可渲染三條曲線且 tooltip 顯示對應點資訊。
- PASS: `data` 缺少曲線資料或為空時只顯示 EmptyState，不拋出 runtime error。

---

### Task 4.3：WalkForwardTimeline (C24)

**說明**：Walk-Forward 各 period AUC 時間線（SPEC §12.2 — C24）。

**依賴**：Task 4.1（WalkForwardResult 型別）

**檔案**（新建）：`frontend/src/components/optimization/WalkForwardTimeline.tsx`

**Props**：
```typescript
interface WalkForwardTimelineProps {
  data: WalkForwardResult;
  onExportPNG?: () => void;
}
```

**驗收條件**：
- [ ] Bar 顯示各 period AUC + Line 顯示 moving average
- [ ] 紅/黃/綠色標依 AUC 值
- [ ] Tooltip 顯示 period 詳情（train/test 範圍、IS-OOS gap）

**驗證檢查點**：
- PASS: 多 period 資料時可同時渲染 bar 與 moving average。
- PASS: 當某 period `test_auc=None`（單類別）時，圖表可安全略過該點且 tooltip 不報錯。

---

### Task 4.4：AdversarialFeatureChart (C25)

**說明**：Feature-level KS/PSI 分佈圖（SPEC §12.2 — C25）。

**依賴**：Task 4.1（AdversarialResult 型別）

**檔案**（新建）：`frontend/src/components/optimization/AdversarialFeatureChart.tsx`

**驗收條件**：
- [ ] Bar Chart 顯示各特徵 KS statistic
- [ ] 顏色依 status（stable=green, warning=yellow, severe=red）
- [ ] 支援排序（by KS statistic / by name）

**驗證檢查點**：
- PASS: 提供 feature-level 資料時可依 KS 值與名稱切換排序。
- PASS: 某特徵缺少 KS/PSI 數值時，元件可跳過該列並顯示可讀警示，不造成崩潰。

---

### Task 4.5：CPCVPathChart (C26)

**說明**：CPCV path-wise AUC 分佈圖（SPEC §12.2 — C26）。

**依賴**：Task 4.1（CPCVResult 型別）

**檔案**（新建）：`frontend/src/components/optimization/CPCVPathChart.tsx`

**驗收條件**：
- [ ] Box/Violin Plot 顯示 path AUC 分佈
- [ ] 顯示 mean/std/min/max 統計
- [ ] 支援 PNG 匯出

**驗證檢查點**：
- PASS: path AUC 陣列存在時可渲染分佈圖與四項摘要統計。
- PASS: path AUC 為空時顯示空狀態提示，且匯出按鈕不觸發無效下載。

---

### Task 4.6：LearningCurveChart (C27)

**說明**：Data/Feature Learning Curve 圖表（SPEC §12.2 — C27）。

**依賴**：Task 4.1（LearningCurveResult 型別）

**檔案**（新建）：`frontend/src/components/optimization/LearningCurveChart.tsx`

**驗收條件**：
- [ ] Dual Line Chart：train score + CV score
- [ ] Shaded area 顯示 CV std
- [ ] 支援切換 data curve / feature curve

**驗證檢查點**：
- PASS: 可在 data curve / feature curve 間切換且保持軸與圖例一致。
- PASS: 缺少 `cv_stds` 或只有單點資料時，圖表降級顯示不崩潰並保留基本曲線。

---

## 8. Phase 5：測試與驗收

### 驗證檢查點

- PASS: 單元、整合、效能、驗收四類檢查皆有對應命令，且結果可重現。
- PASS: 任一驗收條件未達標時，可明確對應到 F/A/P/B 分類並阻擋 freeze 決策。

### Task 5.1：單元測試（56 邊界條件 + 功能測試）

**說明**：實作所有 56 邊界條件測試 + ~40 功能測試（SPEC §17）。

**測試檔案**（6 個新建）：

| 檔案 | 模組 | 邊界條件數 |
|------|------|:---------:|
| `tests/momentum/Analysis/test_probability_calibrator.py` | M1 | 11 (C1-C11) |
| `tests/momentum/Analysis/model_validation/test_walk_forward_validator.py` | M2 | 10 (W1-W10) |
| `tests/momentum/Analysis/test_sample_weight_calculator.py` | M3 | 10 (S1-S10) |
| `tests/momentum/Analysis/test_adversarial_validator.py` | M4 | 8 (A1-A8) |
| `tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py` | M5 | 9 (P1-P9) |
| `tests/momentum/Analysis/test_learning_curve_analyzer.py` | M6 | 8 (L1-L8) |

**測試命名規則**：
```python
def test_C1_single_class():
    """C1: y_cal 全為同類別 → SkippedResult(SINGLE_CLASS)"""

def test_W3_minimal_periods():
    """W3: 只能產出 1-2 期 → 警告 + 依然回傳"""
```

**功能測試範例**（M1）：
```python
class TestProbabilityCalibrator:
    def test_platt_scaling(self, calibrator, sample_predictions): ...
    def test_auto_selects_best(self, calibrator, sample_predictions): ...
    def test_transform_proba(self, calibrator, sample_predictions): ...
    def test_fit_from_predictions(self, calibrator, sample_predictions): ...
    def test_venn_abers_intervals(self, calibrator, sample_predictions): ...
```

**驗收條件**：
- [ ] 56 個邊界條件 100% 覆蓋
- [ ] 每個模組至少 5 個功能測試
- [ ] fixture 使用合成資料（`np.random.seed(42)` 確保可重現）
- [ ] 所有測試獨立於 `run_api.py`（Rule 6）

**驗證檢查點**：
- PASS: 指定 6 個測試檔可全部通過，且 C/W/S/A/P/L 邊界條件命名一一對應。
- PASS: 任一邊界案例失敗時，pytest 報告可直接定位到對應條件代號（例如 C7、W4）。

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_probability_calibrator.py tests/momentum/Analysis/test_sample_weight_calculator.py tests/momentum/Analysis/test_adversarial_validator.py tests/momentum/Analysis/test_learning_curve_analyzer.py tests/momentum/Analysis/model_validation/test_walk_forward_validator.py tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py -v --tb=short
```

---

### Task 5.2：整合測試

**說明**：Service 層 + Factory + 跨模組整合測試（SPEC §17.4）。

**測試檔案**（2 個新建）：

| 檔案 | 測試內容 |
|------|---------|
| `tests/api/test_model_enhancement_service.py` | Service 層功能 + SkippedResult 處理 |
| `tests/api/test_model_enhancement_routes.py` | API 端點 + Request Validation |

**驗收條件**：
- [ ] `full_enhancement` 全模組執行回傳 6 個結果
- [ ] 資料不足時部分模組正確跳過
- [ ] API 端點 8 個全回應 2xx

**驗證檢查點**：
- PASS: service 測試中 `full_enhancement` 結果包含 6 個模組鍵值且任務狀態可查詢。
- PASS: 整合測試中資料不足案例可同時出現 `completed` 與 `skipped`，不影響整體 API 回應結構。

**驗證命令**：
```bash
pytest tests/api/test_model_enhancement_service.py tests/api/test_model_enhancement_routes.py -v --tb=short
```

---

### Task 5.3：效能測試

**說明**：驗證各模組在目標時間內完成（SPEC §17.5）。

**效能目標**：

| 模組 | n_samples | n_features | 目標時間 | 平台 |
|------|:---------:|:----------:|:--------:|:----:|
| M1 ProbabilityCalibrator | 10,000 | - | < 30s | M1 8-core |
| M2 WalkForwardValidator | 5,000 | 50 | < 120s | M1 8-core |
| M3 SampleWeightCalculator | 50,000 | 50 | < 10s | M1 8-core |
| M4 AdversarialValidator | 10,000 | 50 | < 60s | M1 8-core |
| M5 CombinatorialPurgedCV (N=6,k=2) | 5,000 | 50 | < 180s | M1 8-core |
| M6 LearningCurveAnalyzer | 10,000 | 50 | < 120s | M1 8-core |
| **Full Enhancement** | — | — | < 15 分鐘 | M1 8-core |

**記憶體限制**：單模組 peak < 2GB

**驗證檢查點**：
- PASS: M1-M6 在對應樣本規模下達成表列目標時間。
- PASS: 任一模組超時或記憶體超限時，測試輸出可明確標示超標模組與實測值。

---

### Task 5.4：驗收 Checklist

**功能驗收**（SPEC §18.1）：

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| F1 | M1 校準後 ECE 改善 | `ECE_after <= ECE_before`（合成資料） |
| F2 | M2 Walk-Forward 完成滾動驗證 | ≥ 3 periods 無異常 |
| F3 | M3 權重分佈合理 | `mean(weights) ∈ [0.5, 2.0]`，無 NaN |
| F4 | M4 檢測已知分佈差異 | 合成 drifted data → AUC > 0.7 |
| F5 | M5 CPCV 組合數正確 | `C(6,2) = 15` paths |
| F6 | M6 過擬合診斷正確 | 合成 high variance data → `diagnosis="high_variance"` |
| F7 | API 全端點可用 | 8 個端點回應 2xx |
| F8 | Frontend 圖表渲染 | C23-C27 渲染無錯誤 |

**架構驗收**（SPEC §18.2）：

| # | 驗收項目 | 通過標準 | 驗證命令 |
|---|---------|---------|---------|
| A1 | Rule 1 | `grep -r "from api\." momentum/` → 0 | `grep -rn "from api\." momentum/ \| wc -l` |
| A2 | Rule 3 | Service 通過 Factory 注入 | 人工審查 |
| A3 | Rule 7 | api/models 和 momentum/core 無互相引用 | `grep -rn "from momentum\.core" api/models/ \| wc -l` |
| A4 | IModelTrainer 不變 | protocols.py 無修改 | `git diff momentum/core/protocols.py` |
| A5 | 56 邊界條件 100% | pytest 全通過 | `pytest tests/ -v` |

**效能驗收**（SPEC §18.3）：

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| P1 | M1-M6 單模組時間 | §17.5 各模組目標時間內 |
| P2 | Full Enhancement | 全執行 < 15 分鐘 |
| P3 | 記憶體使用 | 單模組 peak < 2GB |

**相容性驗收**（SPEC §18.4）：

| # | 驗收項目 | 通過標準 | 驗證命令 |
|---|---------|---------|---------|
| B1 | Phase 3 測試通過 | 無回歸 | `pytest tests/momentum/ -v --tb=short` |
| B2 | API backward compatible | 現有端點無 breaking change | `curl http://localhost:8000/docs` |
| B3 | Frontend backward compatible | 現有頁面功能正常 | `cd frontend && npm run build` |

**驗證檢查點**：
- PASS: F1-F8、A1-A5、P1-P3、B1-B3 各項皆有對應命令或可重現檢查步驟。
- PASS: 任一驗收項未達標時，能在對應分類（功能/架構/效能/相容性）被明確歸類並追蹤。

---

## 9. `__init__.py` 匯出清單

### `momentum/Analysis/__init__.py`（修改）

新增匯出：
```python
from .probability_calibrator import ProbabilityCalibrator
from .sample_weight_calculator import SampleWeightCalculator
from .adversarial_validator import AdversarialValidator
from .learning_curve_analyzer import LearningCurveAnalyzer
```

### `momentum/Analysis/model_validation/__init__.py`（修改）

新增匯出：
```python
from .walk_forward_validator import WalkForwardValidator, WalkForwardReport, WalkForwardPeriodResult
from .combinatorial_purged_cv import CombinatorialPurgedCV
```

### `api/models/__init__.py`（修改）

新增匯出：
```python
from .model_enhancement import (
    CalibrateRequest, WalkForwardRequest, SampleWeightRequest,
    AdversarialValidateRequest, CPCVRequest, LearningCurveRequest,
    FullEnhancementRequest, ModelEnhancementResponse, FullEnhancementResponse,
)
```

---

## 10. 執行順序總覽

```
Phase 0 (前置條件)
  0.1 建立 SkippedResult（momentum/core/contracts.py）
  0.2 requirements.txt 新增 betacal
  0.3 建立測試目錄 tests/momentum/Analysis/model_validation/

  ✅ CHECKPOINT: python -c "from momentum.core.contracts import SkippedResult; print('Phase 0 OK')"

Phase 1 (基礎設施)
  1.1.1 Pydantic Config Models（各模組內定義）
  1.1.2 YAML Config 擴展（config/model_config.yaml）
  1.1.3 Factory 函式擴展（momentum/factories.py）← 依賴 Phase 2
  1.1.4 API Models（api/models/model_enhancement.py）

  ✅ CHECKPOINT: python -c "import yaml; d=yaml.safe_load(open('config/model_config.yaml')); assert 'probability_calibration' in d; print('Phase 1 OK')"

Phase 2 (核心模組) — P1 優先
  2.1 M1 ProbabilityCalibrator [P1]
  2.2 M2 WalkForwardValidator [P1]
  2.3 M3 SampleWeightCalculator [P2]
  2.4 M4 AdversarialValidator [P2]
  2.5 M5 CombinatorialPurgedCV [P2]
  2.6 M6 LearningCurveAnalyzer [P3]

  ✅ CHECKPOINT: pytest tests/momentum/Analysis/ -v --tb=short (ALL PASSED)

Phase 3 (API 層)
  3.1 ModelEnhancementService ← 依賴 Phase 2 + Task 1.1.3 + Task 1.1.4
  3.2 Route Handlers ← 依賴 Task 3.1

  ✅ CHECKPOINT: curl -s http://localhost:8000/docs | grep "model-enhancement" && pytest tests/api/test_model_enhancement_routes.py -v --tb=short

Phase 4 (前端層)
  4.1 TypeScript 型別 + Store
  4.2 CalibrationPlot (C23)
  4.3 WalkForwardTimeline (C24)
  4.4 AdversarialFeatureChart (C25)
  4.5 CPCVPathChart (C26)
  4.6 LearningCurveChart (C27)

  ✅ CHECKPOINT: cd frontend && npx tsc --noEmit && npm run build

Phase 5 (測試與驗收)
  5.1 單元測試 ← 依賴 Phase 2
  5.2 整合測試 ← 依賴 Phase 3
  5.3 效能測試 ← 依賴 Phase 2
  5.4 驗收 Checklist ← ALL

  ✅ FINAL: grep -rn "from api\." momentum/ | wc -l → expect 0
```

**建議開發日程**：

| 日 | 任務 | 預計產出 |
|---|------|---------|
| Day 0 | Task 0.1-0.3 (Phase 0 前置條件) | SkippedResult + betacal + 測試目錄 |
| Day 1 | Task 1.1.1-1.1.4 + Task 2.1 (M1) + M1 測試 | 基礎設施 + M1 完成 |
| Day 2 | Task 2.2 (M2) + M2 測試 | M2 完成 |
| Day 3 | Task 2.3 (M3) + Task 2.4 (M4) + 測試 | M3 + M4 完成 |
| Day 4 | Task 2.5 (M5) + M5 測試 | M5 完成 |
| Day 5 | Task 2.6 (M6) + Task 1.1.3 (Factory) + M6 測試 | M6 + Factory 完成 |
| Day 6 | Task 3.1-3.2 (API) + Task 5.2 (整合測試) | API 完成 |
| Day 7 | Task 4.1-4.6 (前端) + Task 5.3-5.4 (效能+驗收) | 前端 + 全部驗收 |

---

## 11. 關鍵依賴圖

```
0.1 (SkippedResult) ─────→ 2.1-2.6 (所有 M1-M6 使用 SkippedResult)
0.2 (betacal) ───────────→ 2.1 (M1 Beta Calibration)
0.3 (test dir) ──────────→ 5.1 (M2/M5 測試需要 model_validation/)

1.1.1 (Config) ──────────→ 2.1-2.6 (M1-M6，各自使用 Config)
1.1.2 (YAML) ────────────→ 3.1 (Service 讀取 YAML)
1.1.4 (API Models) ──────→ 3.1 (Service), 3.2 (Routes)

2.1-2.6 (M1-M6) ─────────→ 1.1.3 (Factory: lazy import 模組)
2.1-2.6 (M1-M6) ─────────→ 5.1 (單元測試)

1.1.3 (Factory) + 1.1.4 (API Models) ──→ 3.1 (Service)
3.1 (Service) ────────────→ 3.2 (Routes)
3.2 (Routes) ─────────────→ 5.2 (整合測試)

3.2 (Routes) + 1.1.4 (API Models) ───→ 4.1 (TypeScript 型別)
4.1 (TypeScript) ─────────→ 4.2-4.6 (圖表元件)

ALL ──────────────────────→ 5.4 (驗收)
```

**不動的 Protocol**：
```
IModelTrainer (momentum/core/protocols.py) ← 已存在，不修改
    ↑
    │ model_factory: Callable[[], IModelTrainer]
    │
M2 WalkForwardValidator
M5 CombinatorialPurgedCV
M6 LearningCurveAnalyzer
```

---

## 12. 風險對照表

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| betacal 安裝失敗 | Beta Calibration 需額外套件 | C10 fallback 至 Platt + 警告 | 2.1 |
| CPCV 組合爆炸 | C(20,5) = 15504 paths | `max_paths` 限制 + 隨機取樣 | 2.5 |
| Walk-Forward OOM | Expanding mode 訓練資料持續增長 | 不在模組內處理，文件標記為上游責任 | 2.2 |
| 現有測試回歸 | 新增模組可能影響 import 順序 | 每個 Phase 完成後跑 `pytest tests/momentum/` | 5.4 |
| Frontend 型別不一致 | API Response 與 TypeScript 不同步 | TypeScript strict mode + 型別同步審查 | 4.1 |
| Venn-ABERS O(n²) | n > 5000 時計算極慢 | auto downsampling 至 `venn_abers_max_samples` | 2.1 |
| M4 輕量 LightGBM 版本衝突 | Adversarial 使用 LightGBM | 使用系統已安裝的 lightgbm，不引入新版本 | 2.4 |
| YAML 與 Pydantic 不一致 | YAML 預設值與 Pydantic 預設值不同 | YAML 為 runtime 覆蓋，Pydantic 為程式預設 | 1.1.1, 1.1.2 |

---

## 13. 測試共用 Fixtures

**檔案**：`tests/momentum/Analysis/conftest.py`（新建 — 模組專屬 fixtures）

```python
import pytest
import numpy as np
import pandas as pd
from momentum.factories import (
    create_probability_calibrator,
    create_walk_forward_validator,
    create_sample_weight_calculator,
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
)


@pytest.fixture
def synthetic_binary_data():
    """合成二分類資料（可重現）"""
    np.random.seed(42)
    n = 2000
    n_features = 50
    X = pd.DataFrame(
        np.random.randn(n, n_features),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    y = np.random.binomial(1, 0.3, n)
    return X, y


@pytest.fixture
def synthetic_predictions():
    """合成預測機率和標籤"""
    np.random.seed(42)
    n = 2000
    y_true = np.random.binomial(1, 0.3, n)
    y_pred = np.clip(y_true * 0.7 + np.random.normal(0, 0.2, n), 0.01, 0.99)
    return y_pred, y_true


@pytest.fixture
def synthetic_timestamps():
    """合成時間戳（12h 間隔）"""
    np.random.seed(42)
    n = 2000
    start = pd.Timestamp("2022-01-01")
    return np.array([start + pd.Timedelta(hours=12 * i) for i in range(n)])


@pytest.fixture
def probability_calibrator():
    return create_probability_calibrator()


@pytest.fixture
def walk_forward_validator():
    return create_walk_forward_validator()


@pytest.fixture
def sample_weight_calculator():
    return create_sample_weight_calculator()


@pytest.fixture
def adversarial_validator():
    return create_adversarial_validator()


@pytest.fixture
def combinatorial_purged_cv():
    return create_combinatorial_purged_cv()


@pytest.fixture
def learning_curve_analyzer():
    return create_learning_curve_analyzer()


@pytest.fixture
def mock_model_factory():
    """模擬 model_factory: Callable[[], IModelTrainer]"""
    from unittest.mock import MagicMock
    def factory():
        model = MagicMock()
        model.get_model_type.return_value = "lightgbm"
        return model
    return factory
```

---

## 14. 快取策略

> 對應 SPEC §15

### 14.1 快取粒度

| 模組 | 快取 Key | 快取時間 |
|------|---------|---------|
| M1 | `cal:{model_id}:{method}` | 直到模型重訓 |
| M2 | `wf:{model_id}:{mode}:{hash(config)}` | 直到資料更新 |
| M3 | `sw:{data_hash}:{strategy_combo}` | 直到資料更新 |
| M4 | `av:{data_hash_train}:{data_hash_test}` | 直到資料更新 |
| M5 | `cpcv:{model_id}:{n_groups}:{n_test}` | 直到資料更新 |
| M6 | `lc:{model_id}:{hash(fractions)}` | 直到模型重訓 |

### 14.2 快取檔案結構

```
data_cache/model_enhancement/
├── calibration/
│   └── {model_id}_{method}.json
├── walk_forward/
│   └── {model_id}_{mode}_{config_hash}.json
├── sample_weights/
│   └── {data_hash}_{strategies}.npy
├── adversarial/
│   └── {data_hash_pair}.json
├── cpcv/
│   └── {model_id}_{n_groups}_{n_test}.json
└── learning_curve/
    └── {model_id}_{fractions_hash}.json
```

### 14.3 快取失效規則

```python
def is_cache_valid(cache_file: Path, model_metadata: Dict) -> bool:
    """
    快取有效條件（全部滿足）：
    1. 快取檔案存在
    2. 快取建立時間 > model_metadata['last_trained']
    3. 快取 config_hash == 當前 config_hash
    4. 快取資料 hash == 當前資料 hash（僅 M3, M4）
    """
```

---

## 15. Logging 標準

> 對應 SPEC §16

### 15.1 模組 Logging（momentum/ 層）

```python
from momentum.core.logging import get_logger
logger = get_logger(__name__)

# INFO（關鍵事件）
logger.info(f"ProbabilityCalibrator: 開始校準 method={method}, n_samples={len(y_pred)}")
logger.info(f"ProbabilityCalibrator: 校準完成 ECE {ece_before:.4f} → {ece_after:.4f}")

# WARNING（降級場景）
logger.warning(f"SampleWeightCalculator: uniqueness 權重需要 meta_labels，降級使用 class_balance")

# ERROR（含 traceback）
logger.error(f"AdversarialValidator: 特徵測試失敗 feature={feat}", exc_info=True)

# 禁止
# ❌ logger.info(f"Processing sample {i}")  # 熱迴圈內
# ❌ print("debug")
```

### 15.2 Service 層 Logging（api/ 層）

```python
from api.core.logging import get_logger
logger = get_logger(__name__)

logger.info(f"ModelEnhancement task={task_id} started, modules={modules}")
logger.info(f"ModelEnhancement task={task_id} completed in {elapsed:.1f}s")
logger.error(f"ModelEnhancement task={task_id} failed: {error}", exc_info=True)
```

### 15.3 結構化日誌欄位

所有模組在關鍵路徑標記以下欄位（為 V2.0/V3.0 預留）：

```python
logger.info("calibration_complete", extra={
    "module": "ProbabilityCalibrator",
    "method": "isotonic",
    "ece_before": 0.085,
    "ece_after": 0.031,
    "execution_time_s": 12.3,
})
```

---

## 16. MCP Tool Interface

> 對應 SPEC §19。為 V2.0 Chat / V3.0 Agent 預留。所有 MCP Tools 均為**唯讀**查詢。

### 16.1 Tool 清單

| Tool 名稱 | 說明 | 參數 |
|-----------|------|------|
| `get_calibration_summary` | 校準結果摘要 | `model_task_id` |
| `get_walk_forward_summary` | Walk-Forward 摘要 | `model_task_id` |
| `get_adversarial_summary` | Adversarial 摘要 | `model_task_id` |
| `get_model_enhancement_report` | 完整報告 | `model_task_id`, `format` |
| `compare_model_enhancements` | 比較兩模型 | `model_task_id_a`, `model_task_id_b` |

### 16.2 實作時機

MCP Tools 為 **Phase 5+ 或 V2.0** 的實作項目，本 PLAN Phase 2-4 僅確保輸出的 JSON schema 結構化、可被 MCP 直接消費。**不在本次新建 MCP 檔案**。

---

## 17. AI Agent 每 Task 完成後驗證命令

| Task | 驗證命令 |
|------|---------|
| 0.1 | `python -c "from momentum.core.contracts import SkippedResult; print('SkippedResult OK')"` |
| 0.2 | `grep betacal requirements.txt` |
| 0.3 | `ls tests/momentum/Analysis/model_validation/` |
| 1.1.1 | `python -c "from pydantic import BaseModel; print('Pydantic OK')"` |
| 1.1.2 | `python -c "import yaml; d=yaml.safe_load(open('config/model_config.yaml')); assert 'probability_calibration' in d; print('YAML OK')"` |
| 1.1.3 | `python -c "from momentum.factories import create_probability_calibrator, create_walk_forward_validator, create_sample_weight_calculator, create_adversarial_validator, create_combinatorial_purged_cv, create_learning_curve_analyzer; print('6 factories OK')"` |
| 1.1.4 | `python -c "from api.models.model_enhancement import CalibrateRequest, FullEnhancementRequest; print('API models OK')"` |
| 2.1 | `pytest tests/momentum/Analysis/test_probability_calibrator.py -v --tb=short` |
| 2.2 | `pytest tests/momentum/Analysis/model_validation/test_walk_forward_validator.py -v --tb=short` |
| 2.3 | `pytest tests/momentum/Analysis/test_sample_weight_calculator.py -v --tb=short` |
| 2.4 | `pytest tests/momentum/Analysis/test_adversarial_validator.py -v --tb=short` |
| 2.5 | `pytest tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py -v --tb=short` |
| 2.6 | `pytest tests/momentum/Analysis/test_learning_curve_analyzer.py -v --tb=short` |
| 3.1 | `grep "from momentum\." api/services/model_enhancement_service.py \| grep -v "from momentum.factories" \| grep -v "from momentum.core"` → 應為空 |
| 3.2 | `pytest tests/api/test_model_enhancement_routes.py -v --tb=short` |
| 4.1 | `cd frontend && npx tsc --noEmit` |
| 4.2-4.6 | `cd frontend && npm run build` |
| 5.1 | `pytest tests/momentum/Analysis/test_probability_calibrator.py tests/momentum/Analysis/test_sample_weight_calculator.py tests/momentum/Analysis/test_adversarial_validator.py tests/momentum/Analysis/test_learning_curve_analyzer.py tests/momentum/Analysis/model_validation/ -v --tb=short` |
| 5.2 | `pytest tests/api/test_model_enhancement_service.py tests/api/test_model_enhancement_routes.py -v --tb=short` |
| 5.4 | `grep -rn "from api\." momentum/ \| wc -l` → 期望 0 |

---

## 檔案結構總覽

### 新建檔案（24 個）

```
# ── 核心模組（momentum/）──
momentum/Analysis/probability_calibrator.py          # M1
momentum/Analysis/sample_weight_calculator.py        # M3
momentum/Analysis/adversarial_validator.py           # M4
momentum/Analysis/learning_curve_analyzer.py         # M6
momentum/Analysis/model_validation/walk_forward_validator.py   # M2
momentum/Analysis/model_validation/combinatorial_purged_cv.py  # M5

# ── API 層 ──
api/routes/model_enhancement.py                     # Route handlers
api/services/model_enhancement_service.py           # Service 層
api/models/model_enhancement.py                     # Pydantic Request/Response

# ── 前端 ──
frontend/src/components/optimization/CalibrationPlot.tsx      # C23
frontend/src/components/optimization/WalkForwardTimeline.tsx   # C24
frontend/src/components/optimization/AdversarialFeatureChart.tsx  # C25
frontend/src/components/optimization/CPCVPathChart.tsx         # C26
frontend/src/components/optimization/LearningCurveChart.tsx    # C27
frontend/src/store/modelEnhancementStore.ts                    # Zustand store

# ── 測試 ──
tests/momentum/Analysis/test_probability_calibrator.py
tests/momentum/Analysis/test_sample_weight_calculator.py
tests/momentum/Analysis/test_adversarial_validator.py
tests/momentum/Analysis/test_learning_curve_analyzer.py
tests/momentum/Analysis/model_validation/test_walk_forward_validator.py
tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py
tests/momentum/Analysis/conftest.py                            # 模組專屬 fixtures
tests/api/test_model_enhancement_routes.py
tests/api/test_model_enhancement_service.py
```

### 修改檔案（5 個）

```
momentum/core/contracts.py           # 新增 SkippedResult dataclass (Task 0.1)
momentum/factories.py                # 新增 6 個 factory 函式
config/model_config.yaml             # 新增 Phase 3.5 config section
frontend/src/lib/types.ts            # 新增 TypeScript 型別
requirements.txt                     # 新增 betacal (Task 0.2)
```

### 額外修改（`__init__.py` 匯出）

```
momentum/Analysis/__init__.py
momentum/Analysis/model_validation/__init__.py
api/models/__init__.py
api/main.py                          # 新增 router 註冊（1 行）
```

---

## 下游整合相容性備註

### 對現有 Phase 3 模組的影響（SPEC §10.1）

| 現有模組 | 影響方式 | 程度 |
|---------|---------|:----:|
| LightGBMAnalyzer | M3 提供 sample_weight 透過 **kwargs 傳入 | 低 |
| XGBoostAnalyzer | 同上 | 低 |
| ModelComparison | M1 校準後統一兩引擎機率尺度 | 低 |
| CalibrationAnalyzer | M1 復用其 ECE/Brier 邏輯（只讀） | 無 |
| PurgedTimeSeriesSplit | M2/M5 復用 purge/embargo（只讀） | 無 |
| DriftAnalyzer | M4 的 PSI 可復用其實作（只讀） | 無 |

### 對 Phase 4+ 的準備（SPEC §10.2）

| Phase 4 需求 | Phase 3.5 支撐 |
|-------------|---------------|
| 策略回測信賴區間 | M5 CPCV backtest paths |
| Position Sizing | M1 校準後機率 → Kelly Criterion |
| 模型自動更新 | M2 Walk-Forward 驗證框架 |
| 因子容量評估 | M3 有效樣本數 efficiency_ratio |

### V2.0/V3.0 演進準備（SPEC §10.3）

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/model-enhancement/*` | ✅ 本 PLAN 實作 |
| **V2.0** | Chat: "幫我校準 BTCUSDT 12h 模型機率" | ✅ 直接呼叫 `create_probability_calibrator()` |
| **V3.0** | Agent: 自主判斷需要哪些增強模組 | ✅ 透過 MCP `get_model_enhancement_report` 查詢 |

**關鍵設計選擇**：
- ✅ **不綁定 FastAPI**：core 模組可被任何 Python 程式呼叫
- ✅ **結構化 JSON 輸出**：所有模組 output schema 為 MCP-ready
- ✅ **Factory 注入**：V2/V3 可用不同 Factory 配置建立模組

---

## Phase 6: 全功能開關系統 (M7)

> 對應 SPEC §21 | 預估工作量: 2-3 天 | 前置條件: Phase 2 (M1-M6 核心模組完成)

### 驗證檢查點

- PASS: 完成 Task 6.1-6.5 後，23 個功能開關可被查詢、更新與套用 preset，且 L1 鎖定規則與依賴關係 enforcement 生效。
- PASS: 當出現失敗/邊界情境（重複 feature_id、依賴未滿足、YAML 格式錯誤）時，系統回傳可辨識失敗結果並維持 registry 可繼續使用，不產生連鎖崩潰。

### Task 6.1: FeatureToggleRegistry 核心實作

**檔案**: `momentum/Analysis/feature_toggle_registry.py`（🆕 新建）

**類別**:
- `DifficultyLevel` (Enum): L1/L2/L3
- `FeatureToggle` (dataclass): feature_id, name, description, difficulty, is_enabled, is_locked, engine_types, dependencies, phase, module, estimated_time, tags
- `FeatureToggleRegistry`: 完整 Registry 類別

**方法清單**:
| 方法 | 說明 | 邊界條件 |
|------|------|---------|
| `register(toggle)` | 註冊功能開關 | 重複 ID → ValueError |
| `set_enabled(feature_id, enabled)` | 設定 ON/OFF | T1: L1 鎖定拒絕；T2: 連帶停用下游；T3: 依賴不滿足拒絕 |
| `get_by_difficulty(level)` | 按級別查詢 | — |
| `get_enabled_features()` | 取得已啟用功能 | — |
| `validate_dependencies()` | 驗證依賴關係 | — |
| `apply_preset(preset)` | 套用預設方案 | T4/T5: essential-only/full |
| `to_config_dict()` | 匯出 YAML dict | — |
| `load_from_yaml(yaml_path)` | 從 YAML 載入 | T7: 格式錯誤降級 |
| `get_summary()` | 摘要統計 | — |

**依賴管理邏輯**:
```python
def set_enabled(self, feature_id: str, enabled: bool) -> List[str]:
    toggle = self._toggles.get(feature_id)
    if toggle is None:
        raise ValueError(f"未知功能 ID: {feature_id}")
    
    if not enabled and toggle.is_locked:
        raise ValueError(f"L1 基礎功能 {toggle.name} 不可關閉")
    
    affected = []
    if not enabled:
        # 關閉 → 連帶關閉所有依賴此功能的下游
        for fid, ft in self._toggles.items():
            if feature_id in ft.dependencies and ft.is_enabled:
                ft.is_enabled = False
                affected.append(fid)
    else:
        # 啟用 → 檢查所有依賴是否已啟用
        for dep_id in toggle.dependencies:
            dep = self._toggles.get(dep_id)
            if dep and not dep.is_enabled:
                raise ValueError(f"需先啟用 {dep_id} ({dep.name})")
    
    toggle.is_enabled = enabled
    return affected
```

**預設功能註冊** (23 個功能):
- Phase 3: F-001 ~ F-013 (13 個)
- Phase 3.5: F-101 ~ F-110 (10 個)
- 全部見 SPEC §21.3

**驗收**:
```bash
python -c "
from momentum.Analysis.feature_toggle_registry import FeatureToggleRegistry, DifficultyLevel
reg = FeatureToggleRegistry()
# 預設載入驗證
assert len(reg.get_by_difficulty(DifficultyLevel.ESSENTIAL)) == 4
assert len(reg.get_by_difficulty(DifficultyLevel.INTERMEDIATE)) >= 8
assert len(reg.get_by_difficulty(DifficultyLevel.ADVANCED)) >= 8
print('FeatureToggleRegistry OK')
"
```

### Task 6.2: YAML 配置 + Preset 系統

**檔案**: `config/feature_toggles.yaml`（🆕 新建）

**內容**: 見 SPEC §21.5 — 包含 3 個 Presets (essential-only, recommended, full) + 23 個功能開關預設值

**驗收**:
```bash
python -c "
import yaml
d = yaml.safe_load(open('config/feature_toggles.yaml'))
assert 'presets' in d
assert 'feature_toggles' in d
assert len(d['presets']) == 3
print('feature_toggles.yaml OK')
"
```

### Task 6.3: Feature Toggle API + Service

**新建檔案**:
- `api/services/feature_toggle_service.py`（🆕）— 調用 FeatureToggleRegistry
- `api/routes/feature_toggles.py`（🆕）— 4 個端點
- `api/models/feature_toggle_models.py`（🆕）— Pydantic Request/Response

**端點清單**:
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/feature-toggles` | 列出全部（可篩選 difficulty） |
| PUT | `/api/v1/feature-toggles/{feature_id}` | 更新單一開關 |
| PUT | `/api/v1/feature-toggles/batch` | 批次更新 |
| POST | `/api/v1/feature-toggles/presets/{preset_name}` | 套用預設方案 |

**修改檔案**:
- `api/main.py`（🔄）— 新增 `feature_toggles` router 註冊
- `momentum/factories.py`（🔄）— 新增 `create_feature_toggle_registry()`

**驗收**:
```bash
pytest tests/api/test_feature_toggle_routes.py -v --tb=short
```

### Task 6.4: Frontend FeatureTogglePanel

**新建檔案**:
- `frontend/src/components/settings/FeatureTogglePanel.tsx`（🆕）— 三級分類開關面板
- `frontend/src/store/featureToggleStore.ts`（🆕）— Zustand Store

**UI 規格**: 見 SPEC §21.7 — 三級顏色分區（🟢/🟡/🔴）、鎖定圖標、預估時間提示、預設方案切換按鈕、摘要統計

**修改檔案**:
- `frontend/src/lib/types.ts`（🔄）— 新增 FeatureToggle 相關型別

**驗收**:
```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Task 6.5: M7 測試

**新建 2 個測試檔案**（~19 測試）:

| 測試檔案 | 測試數量 | 涵蓋 |
|---------|:-------:|------|
| `tests/momentum/Analysis/test_feature_toggle_registry.py` | ~12 | T1-T7 邊界 + CRUD + Preset + YAML |
| `tests/api/test_feature_toggle_routes.py` | ~7 | 4 端點 + validation + error |

**驗收**:
```bash
pytest tests/momentum/Analysis/test_feature_toggle_registry.py tests/api/test_feature_toggle_routes.py -v --tb=short
```

---

## Phase 7: 多格式匯出系統 (M8)

> 對應 SPEC §22 | 預估工作量: 2-3 天 | 前置條件: Phase 2 (M1-M6 結果結構) + Phase 3 (API 層 Service/Route)

### 驗證檢查點

- PASS: 完成 Task 7.1-7.4 後，既有匯出責任範圍（CSV/JSON/Markdown + download/preview）均可輸出且格式符合既定 schema。
- PASS: 當出現失敗/邊界情境（不支援 format/scope、NaN 或 numpy 類型、skipped 模組結果）時，匯出流程可降級為可序列化輸出或明確錯誤，不影響其他匯出目標。

### Task 7.1: AnalysisExporter 核心實作

**檔案**: `momentum/Analysis/analysis_exporter.py`（🆕 新建）

**類別**:
- `ExportFormat` (Enum): CSV, JSON, MARKDOWN
- `AnalysisExporter`: 多格式匯出器

**方法清單**:
| 方法 | 說明 | CSV | JSON | MD |
|------|------|:---:|:----:|:--:|
| `export_model_performance()` | 效能報告 | ✅ | ✅ | ✅ |
| `export_feature_importance()` | 特徵重要性 | ✅ | ✅ | ✅ |
| `export_enhancement_results()` | M1-M6 結果 | ✅ | ✅ | ✅ |
| `export_full_research_report()` | 完整報告 | — | ✅ | ✅ |

**JSON 信封格式** (AI Agent/LLM 友善):
```python
def _create_json_envelope(self, data: Dict, model_id: str) -> Dict:
    return {
        "schema_version": self.SCHEMA_VERSION,
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "engine": data.get("engine", "unknown"),
        "data_source": data.get("data_source", {}),
        **data,
    }
```

**Markdown 報告模板**: 見 SPEC §22.5 — 包含效能摘要表、Top-20 特徵、校準分析、Walk-Forward、建議

**邊界處理**:
- NaN → CSV 空字串、JSON null
- numpy 類型 → Python 原生類型
- 表格欄位超長 → 截斷 50 字元 + "..."
- SkippedResult → `"status": "skipped"` + reason

**驗收**:
```bash
python -c "
from momentum.Analysis.analysis_exporter import AnalysisExporter, ExportFormat
exporter = AnalysisExporter()
print('AnalysisExporter OK')
"
```

### Task 7.2: Export API + Service

**新建檔案**:
- `api/services/export_service.py`（🆕）— 調用 AnalysisExporter + 讀取 task cache
- `api/routes/export.py`（🆕）— 2 個端點
- `api/models/export_models.py`（🆕）— Pydantic Models

**端點清單**:
| 方法 | 路徑 | 說明 | 回傳 |
|------|------|------|------|
| GET | `/api/v1/export/{model_task_id}` | 匯出下載 | FileResponse |
| GET | `/api/v1/export/{model_task_id}/preview` | 匯出預覽 | JSON (text content) |

**Query Parameters**:
- `format`: csv \| json \| markdown（必填）
- `scope`: performance \| features \| calibration \| walk_forward \| adversarial \| cpcv \| learning_curve \| optimization \| comparison \| full（預設 full）

**修改檔案**:
- `api/main.py`（🔄）— 新增 `export` router 註冊
- `momentum/factories.py`（🔄）— 新增 `create_analysis_exporter()`

**驗收**:
```bash
pytest tests/api/test_export_routes.py -v --tb=short
```

### Task 7.3: Frontend ExportButton 整合

**新建檔案**:
- `frontend/src/components/common/ExportButton.tsx`（🆕）— 通用匯出下拉按鈕

**元件設計**:
```typescript
interface ExportButtonProps {
  modelTaskId: string;
  scope: string;
  availableFormats: ('csv' | 'json' | 'markdown')[];
}
// 外觀: [📥 匯出 ▾] → 下拉選單: CSV / JSON / Markdown
```

**整合點**: 在以下現有頁面加入 ExportButton:
- 模型結果頁 (scope="performance")
- 特徵重要性面板 (scope="features")
- 模型增強結果頁 (scope="calibration" 等)
- 完整報告 (scope="full")

**驗收**:
```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Task 7.4: M8 測試

**新建 2 個測試檔案**（~22 測試）:

| 測試檔案 | 測試數量 | 涵蓋 |
|---------|:-------:|------|
| `tests/momentum/Analysis/test_analysis_exporter.py` | ~15 | 3 格式 × 4 匯出方法 + E3-E7 邊界 |
| `tests/api/test_export_routes.py` | ~7 | 2 端點 + format/scope 組合 + E1-E2 |

**驗收**:
```bash
pytest tests/momentum/Analysis/test_analysis_exporter.py tests/api/test_export_routes.py -v --tb=short
```

---

## Phase 8: 特徵工程數據瀏覽器 (M9)

> 對應 SPEC §23 | 預估工作量: 5-7 天 | 前置條件: 外部 Phase 1 (Feature Factory) + 本 PLAN Phase 2-3 (M1-M6 + API 層)

### 驗證檢查點

- PASS: 完成 Task 8.1-8.5 後，10 個 Browser API 與 6 個前端 Tab 可在既有宣告範圍內提供與渲染資料（含空資料引導/空狀態）。
- PASS: 當出現失敗/邊界情境（IC/SHAP 資料不可用、特徵量過大需縮減、相關矩陣成本過高）時，系統提供明確降級結果或提示，不造成頁面/服務中斷。

### Task 8.1: FeatureBrowserService + Backend API

**新建檔案**:
- `api/services/feature_browser_service.py`（🆕）— 聚合多 domain 資料
- `api/routes/feature_browser.py`（🆕）— 10 個端點
- `api/models/feature_browser_models.py`（🆕）— Pydantic Response Models

**Service 設計**: 依賴注入模式，聚合 Feature Factory / Model Training / Model Enhancement 三個 domain 的資料。

**端點清單**:
| # | 方法 | 路徑 | Tab | 說明 |
|---|------|------|:---:|------|
| 1 | GET | `/api/v1/feature-browser/overview` | 1 | 特徵統計摘要 |
| 2 | GET | `/api/v1/feature-browser/distribution/{feature_name}` | 1 | 單一特徵分佈 |
| 3 | GET | `/api/v1/feature-browser/ic-dashboard` | 2 | IC 摘要 + 排名 |
| 4 | GET | `/api/v1/feature-browser/rolling-ic/{feature_name}` | 2 | 滾動 IC 時序 |
| 5 | GET | `/api/v1/feature-browser/quality-scorecard` | 3 | 品質多維評分 |
| 6 | GET | `/api/v1/feature-browser/correlation-matrix` | 4 | 相關性矩陣 |
| 7 | GET | `/api/v1/feature-browser/vif` | 4 | VIF 表 |
| 8 | GET | `/api/v1/feature-browser/drift-monitor` | 5 | PSI + KS 飄移 |
| 9 | GET | `/api/v1/feature-browser/shap-summary` | 6 | SHAP Beeswarm |
| 10 | GET | `/api/v1/feature-browser/importance-comparison` | 6 | 跨引擎對比 |

**修改檔案**:
- `api/main.py`（🔄）— 新增 `feature_browser` router 註冊

**驗收**:
```bash
pytest tests/api/test_feature_browser_routes.py -v --tb=short
```

### Task 8.2: Frontend Tab 1-2 (Overview + IC Dashboard)

**新建檔案**:
- `frontend/src/app/feature-browser/page.tsx`（🆕）— 頂層頁面 + 6 Tab 切換
- `frontend/src/components/feature-browser/FeatureSummaryTable.tsx`（🆕）— C30: 統計摘要表
- `frontend/src/components/feature-browser/ICDashboard.tsx`（🆕）— C33+C34+C35: IC 分析

**Tab 1 面板**:
- C30 FeatureSummaryTable: N, Mean, Std, Min, Max, NaN%, 型態
- C31 FeatureDistributionChart: 可選擇特徵的直方圖（內嵌於 C30 展開行）
- C32 NaNHeatmap: 時間 × 特徵的缺值熱力圖

**Tab 2 面板** (Alphalens 對標):
- C33 ICDashboardTable: IC Mean, IC Std, IR, t-stat, 顯著性星號 + Sparkline
- C34 RollingICChart: 選定特徵的滾動 IC/IR Line Chart
- C35 ICDecayChart: 不同 lag 的 IC 衰減

**驗收**:
```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Task 8.3: Frontend Tab 3-4 (Quality + Correlation)

**新建檔案**:
- `frontend/src/components/feature-browser/QualityScorecard.tsx`（🆕）— C36+C37+C38
- `frontend/src/components/feature-browser/CorrelationHeatmap.tsx`（🆕）— C39+C40

**Tab 3 面板** (QuantConnect 對標):
- C36 QualityScorecardTable: 多維品質評分 + A/B/C/D/F 徽章
- C37 FeatureFunnelChart: 篩選漏斗（原始 → IC → VIF → 最終）
- C38 QualityRadarChart: 選定特徵的雷達圖

**Tab 4 面板** (Bloomberg 對標):
- C39 CorrelationHeatmap: 帶 Clustering 的相關性矩陣
- C40 VIFTable: 方差膨脹因子排序表

**驗收**:
```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Task 8.4: Frontend Tab 5-6 (Drift + Attribution)

**新建檔案**:
- `frontend/src/components/feature-browser/DriftMonitor.tsx`（🆕）— C41+C42
- `frontend/src/components/feature-browser/ModelAttribution.tsx`（🆕）— C43+C44+C45

**Tab 5 面板** (Evidently 對標):
- C41 PSITimelineChart: PSI 隨時間變化 + 警告閾值線
- C42 DistributionComparisonChart: Train vs Test 密度曲線疊加

**Tab 6 面板** (Bloomberg PORT 對標):
- C43 SHAPBeeswarmPlot: SHAP Summary (dot/swarm)
- C44 SHAPDependencePlot: 選定特徵 × SHAP 值散點圖
- C45 ImportanceComparisonChart: LightGBM vs XGBoost Grouped Bar

**驗收**:
```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Task 8.5: Zustand Store + TypeScript + 整合測試

**新建檔案**:
- `frontend/src/store/featureBrowserStore.ts`（🆕）— 見 SPEC §23.7

**修改檔案**:
- `frontend/src/lib/types.ts`（🔄）— 新增 11 個 TypeScript 介面（FeatureOverview, ICDashboardEntry, RollingIC, FeatureQualityScore, CorrelationMatrix, DriftMonitorEntry, SHAPSummary, ImportanceComparison 等）
- `frontend/src/app/layout.tsx`（🔄）— 新增 /feature-browser 導航連結

**新建測試**:
- `tests/api/test_feature_browser_routes.py`（🆕）— 10 端點測試 + B1-B7 邊界
- `tests/api/test_feature_browser_service.py`（🆕）— Service 整合測試

**測試數量估算**（~29 測試）:
| 測試檔案 | 測試數 | 涵蓋 |
|---------|:-------:|------|
| `test_feature_browser_routes.py` | ~12 | 10 端點 + B3/B4 空狀態 |
| `test_feature_browser_service.py` | ~10 | 聚合邏輯 + 分頁 + 縮減 |
| B1-B7 邊界條件 | ~7 | 見 SPEC §23.8 |

**驗收**:
```bash
# Backend
pytest tests/api/test_feature_browser_routes.py tests/api/test_feature_browser_service.py -v --tb=short

# Frontend
cd frontend && npx tsc --noEmit && npm run build

# 架構合規
grep -rn "from api\." momentum/ | wc -l  # 期望 0
```

---

## Phase 6-8 依賴關係圖

```
Phase 0-5 (M1-M6 既有)
    │
    ├──→ Phase 6 (M7 Feature Toggle)
    │       ├── Task 6.1: Registry 核心
    │       ├── Task 6.2: YAML + Preset
    │       ├── Task 6.3: API + Service
    │       ├── Task 6.4: Frontend Panel
    │       └── Task 6.5: Tests
    │
    ├──→ Phase 7 (M8 Multi-Format Export)
    │       ├── Task 7.1: Exporter 核心
    │       ├── Task 7.2: API + Service
    │       ├── Task 7.3: Frontend Button
    │       └── Task 7.4: Tests
    │
    └──→ Phase 8 (M9 Feature Browser)  ← 依賴 Phase 1 (Feature Factory)
            ├── Task 8.1: Service + API
            ├── Task 8.2: Tab 1-2
            ├── Task 8.3: Tab 3-4
            ├── Task 8.4: Tab 5-6
            └── Task 8.5: Store + Tests

Phase 6, 7, 8 彼此獨立，可平行開發。
Phase 8 額外依賴 Phase 1 (Feature Factory) 的 IC 資料。
```

---

## Phase 6-8 風險對照表

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| YAML 設定遺失 | feature_toggles.yaml 不存在 | 降級至硬編碼預設值 + 警告 | 6.1 |
| 依賴循環 | 功能 A 依賴 B、B 依賴 A | 註冊時 DAG 拓撲排序 + 循環偵測 | 6.1 |
| JSON 序列化失敗 | numpy/pandas 類型無法 json.dumps | 自訂 JSONEncoder + _sanitize | 7.1 |
| 大量特徵渲染卡頓 | > 1000 特徵一次載入 | 分頁 + 虛擬捲動 + 延遲載入 | 8.2 |
| 相關性矩陣 OOM | 6514 × 6514 矩陣 | 限制 Top-200 + 警告 | 8.3 |
| IC 數據不可用 | Feature Factory 尚未執行 | Tab 顯示引導提示 + disable 狀態 | 8.2 |
| SHAP 數據不可用 | 模型尚未訓練 | Tab 6 顯示引導提示 | 8.4 |

---

## Phase 6-8 驗收標準

### 功能驗收

| # | 驗收項目 | 通過標準 | 對應 Phase |
|---|---------|---------|:--------:|
| F9 | 功能開關 CRUD | 23 功能 ON/OFF 正確 + 依賴關係強制 | 6 |
| F10 | L1 鎖定 | L1 功能無法關閉 | 6 |
| F11 | Preset 切換 | 3 種 Preset 正確切換全部開關 | 6 |
| F12 | CSV 匯出 | 11 匯出項正確輸出 CSV | 7 |
| F13 | JSON 匯出 | schema_version + metadata 正確 | 7 |
| F14 | Markdown 匯出 | 報告格式正確、表格對齊 | 7 |
| F15 | 數據瀏覽器 6 Tab | 全部 Tab 可渲染 + 無 JS 錯誤 | 8 |
| F16 | 16 個圖表元件 | C30-C45 渲染無錯誤 | 8 |
| F17 | 10 個 Browser API | 全部回應 2xx | 8 |

### 架構驗收

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| A6 | Rule 1 | `grep -r "from api\." momentum/` → 0 結果 |
| A7 | Rule 3 | export_service / feature_browser_service 透過 Factory 注入 |
| A8 | Rule 7 | api/models 和 momentum/core 無互相引用 |

### 效能驗收

| # | 驗收項目 | 通過標準 | 平台 |
|---|---------|---------|:----:|
| P4 | Feature Toggle 切換 | < 100ms | M1 Mac |
| P5 | JSON 匯出 (full report) | < 5s | M1 Mac |
| P6 | Feature Browser overview | < 3s (1000 features) | M1 Mac |
| P7 | Correlation Matrix | < 10s (200 × 200) | M1 Mac |

---

## Phase 6-8 AI Agent 驗證命令

| Task | 驗證命令 |
|------|---------|
| 6.1 | `python -c "from momentum.Analysis.feature_toggle_registry import FeatureToggleRegistry; print('Registry OK')"` |
| 6.2 | `python -c "import yaml; d=yaml.safe_load(open('config/feature_toggles.yaml')); assert 'presets' in d; print('YAML OK')"` |
| 6.3 | `pytest tests/api/test_feature_toggle_routes.py -v --tb=short` |
| 6.4 | `cd frontend && npx tsc --noEmit` |
| 6.5 | `pytest tests/momentum/Analysis/test_feature_toggle_registry.py -v --tb=short` |
| 7.1 | `python -c "from momentum.Analysis.analysis_exporter import AnalysisExporter; print('Exporter OK')"` |
| 7.2 | `pytest tests/api/test_export_routes.py -v --tb=short` |
| 7.3 | `cd frontend && npx tsc --noEmit` |
| 7.4 | `pytest tests/momentum/Analysis/test_analysis_exporter.py -v --tb=short` |
| 8.1 | `pytest tests/api/test_feature_browser_routes.py -v --tb=short` |
| 8.2-8.4 | `cd frontend && npm run build` |
| 8.5 | `grep -rn "from api\." momentum/ \| wc -l` → 期望 0 |

---

## Phase 6-8 新增檔案清單

### 新增檔案（29 個）

```
# ── M7 全功能開關 ──
momentum/Analysis/feature_toggle_registry.py
config/feature_toggles.yaml
api/routes/feature_toggles.py
api/services/feature_toggle_service.py
api/models/feature_toggle_models.py
frontend/src/components/settings/FeatureTogglePanel.tsx
frontend/src/store/featureToggleStore.ts
tests/momentum/Analysis/test_feature_toggle_registry.py
tests/api/test_feature_toggle_routes.py

# ── M8 多格式匯出 ──
momentum/Analysis/analysis_exporter.py
api/routes/export.py
api/services/export_service.py
api/models/export_models.py
frontend/src/components/common/ExportButton.tsx
tests/momentum/Analysis/test_analysis_exporter.py
tests/api/test_export_routes.py

# ── M9 數據瀏覽器 ──
api/routes/feature_browser.py
api/services/feature_browser_service.py
api/models/feature_browser_models.py
frontend/src/app/feature-browser/page.tsx
frontend/src/components/feature-browser/FeatureSummaryTable.tsx
frontend/src/components/feature-browser/ICDashboard.tsx
frontend/src/components/feature-browser/QualityScorecard.tsx
frontend/src/components/feature-browser/CorrelationHeatmap.tsx
frontend/src/components/feature-browser/DriftMonitor.tsx
frontend/src/components/feature-browser/ModelAttribution.tsx
frontend/src/store/featureBrowserStore.ts
tests/api/test_feature_browser_routes.py
tests/api/test_feature_browser_service.py
```

### 修改檔案（5 個）

```
momentum/factories.py               # 新增 create_feature_toggle_registry(), create_analysis_exporter(), create_feature_browser_dependencies()
api/main.py                          # 新增 3 個 router 註冊
frontend/src/lib/types.ts            # 新增 M7/M8/M9 TypeScript 型別
frontend/src/app/layout.tsx          # 新增 /feature-browser 導航連結
```

---

> **文件結束** — LightGBM/XGBoost 優化 PLAN V7
>
> 總計 9 模組 (M1-M9) | 78 邊界條件 | ~204 測試 | 53 新建檔案 + 10 修改檔案 | 16 API 端點（M7-M9 新增） | 21 圖表元件（C23-C27 + C30-C45）

<!-- STATUS: CONVERGED / READY TO FREEZE -->
