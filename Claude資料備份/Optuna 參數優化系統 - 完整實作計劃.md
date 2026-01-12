# Optuna 參數優化系統 - 完整實作計劃

## 文檔資訊

- **任務編號**: Phase 3.5
- **優先級**: 🔥🔥🔥 P0
- **預估時間**: 10.5 天
- **前置需求**: Phase 3.2 信號密度分析（已完成）
- **創建日期**: 2025-01-XX

---

## 一、系統現狀

### 1.1 已完成模組

| 模組 | 檔案路徑 | 狀態 |
|------|----------|------|
| 信號密度分析器 | `momentum/Analysis/signal_density_analyzer.py` | ✅ 完成 |
| 信號分析服務 | `api/services/signal_analysis_service.py` | ✅ 完成 |
| 信號分析 API | `api/routes/signal_analysis.py` | ✅ 完成 |
| 策略測試頁面 | `frontend/src/app/strategy-test/page.tsx` | ✅ 完成 |
| 策略配置 Hook | `frontend/src/hooks/useStrategyConfig.ts` | ✅ 完成 |
| 密度箱型圖 | `frontend/src/components/charts/CombinedDensityBoxplot.tsx` | ✅ 完成 |
| 統計指標卡片 | `frontend/src/components/ui/StatMetricCard.tsx` | ✅ 完成 |

### 1.2 現有頁面結構（不可變更）

```
/strategy-test 頁面現有佈局：
┌─────────────────────────────────────────────────────────────┐
│ 頂部工具列：策略名稱輸入 + 管理範本按鈕                       │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌────────────────────────────────┐ │
│ │                     │  │                                │ │
│ │   折疊面板區域       │  │   結果展示區域                  │ │
│ │   (30% 寬度)        │  │   (70% 寬度)                   │ │
│ │                     │  │                                │ │
│ │ • 基本配置          │  │ • 統計指標卡片                  │ │
│ │ • 指標配置          │  │ • 密度箱型圖                    │ │
│ │ • 窗口配置          │  │ • 數據品質摘要                  │ │
│ │ • 測試範圍          │  │                                │ │
│ │ • 優化參數          │  │                                │ │
│ │                     │  │                                │ │
│ └─────────────────────┘  └────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ 底部操作按鈕區：重置 / 保存範本 / 查看圖表 / 執行測試         │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 現有可復用組件

```typescript
// UI 組件
import { Accordion } from "@/components/ui/Accordion";
import { AccordionItem } from "@/components/ui/AccordionItem";
import { Select } from "@/components/ui/Select";
import { NumberInput } from "@/components/ui/NumberInput";
import { DateRangePicker } from "@/components/ui/DateRangePicker";
import StatMetricCard from "@/components/ui/StatMetricCard";

// 圖表組件
import CombinedDensityBoxplot from "@/components/charts/CombinedDensityBoxplot";
import WindowConfigPanel from "@/components/strategy/WindowConfigPanel";

// 狀態管理
import { useStrategyConfig } from "@/hooks/useStrategyConfig";
```

---

## 二、優化目標設計

### 2.1 核心優化目標

```python
# 唯一優化目標：最大化 ratio_separation
maximize: ratio_separation = mean(positive_ratios) - mean(negative_ratios)

# 其中：
# positive_ratios = [case.near_density / case.far_density for case in positive_cases]
# negative_ratios = [case.near_density / case.far_density for case in negative_cases]
```

### 2.2 統計指標計算（基於 ratio 列表）

| 指標 | 計算公式 | 判斷標準 | 用途 |
|------|----------|----------|------|
| `ratio_separation` | `mean(pos_ratios) - mean(neg_ratios)` | > 0.5 優秀 | **主優化目標** |
| `p_value` | `ttest_ind(pos_ratios, neg_ratios)` | < 0.05 顯著 | 統計可信度 |
| `cohens_d` | `(μ_pos - μ_neg) / pooled_std` | > 0.8 大效果 | 效果量大小 |
| `stability_cv` | `std(monthly_sep) / mean(monthly_sep)` | < 0.3 穩定 | 時間穩定性 |

### 2.3 目標函數實現

```python
async def objective(trial: optuna.Trial) -> float:
    """
    唯一目標：maximize ratio_separation
    所有統計指標記錄於 user_attrs，供後續分析
    """
    # 1. 採樣參數
    params = sample_params(trial)
    
    # 2. 計算信號密度
    result = await signal_service.analyze_signal_density(...)
    
    # 3. 記錄完整統計（用於後續分析，不影響優化）
    trial.set_user_attr("positive_avg_ratio", result.positive_near_far_ratio)
    trial.set_user_attr("negative_avg_ratio", result.negative_near_far_ratio)
    trial.set_user_attr("p_value", result.ratio_p_value)
    trial.set_user_attr("cohens_d", result.ratio_cohens_d)
    trial.set_user_attr("stability_cv", result.stability_cv)
    
    # 4. 返回唯一優化目標
    return result.ratio_separation
```

---

## 三、模組架構

### 3.1 後端新增/修改檔案

```
momentum/Optimization/
├── optuna_optimizer.py         # [修改] 主優化器，整合所有組件
├── optimization_config.py      # [新增] 優化配置 dataclass
├── checkpoint_manager.py       # [新增] 斷點續跑機制
├── error_handler.py            # [新增] 錯誤分類與處理
├── progress_monitor.py         # [新增] 進度監控與回調
└── result_analyzer.py          # [新增] 結果分析（重要性、收斂、穩定性）

momentum/Utils/
└── data_validator.py           # [新增] 數據完整性驗證

api/services/
└── optimization_service.py     # [新增] 優化任務 API 服務

api/routes/
└── optimization.py             # [新增] 優化 API 端點

api/models/
└── optimization_models.py      # [新增] 優化請求/響應模型
```

### 3.2 前端新增/修改檔案

```
frontend/src/components/strategy-test/
├── OptunaConfigPanel.tsx       # [新增] Optuna 參數設定面板
└── OptimizationResults/
    ├── index.tsx               # [新增] 結果展示容器
    ├── BestResultCard.tsx      # [新增] 最佳結果卡片
    ├── ParamImportanceChart.tsx# [新增] 參數重要性圖
    ├── ParamHeatmap.tsx        # [新增] 參數空間熱力圖
    ├── ConvergencePlot.tsx     # [新增] 收斂曲線
    ├── StabilityChart.tsx      # [新增] 穩定性分析圖
    └── TrialRankingTable.tsx   # [新增] 試驗排名表格

frontend/src/app/strategy-test/
└── page.tsx                    # [修改] 整合 Optuna 面板與結果

frontend/src/hooks/
└── useStrategyConfig.ts        # [修改] 新增 optuna 相關狀態

frontend/src/lib/
└── optimization-api.ts         # [新增] 優化 API 調用封裝
```

---

## 四、後端實作步驟

### STEP 1: 優化配置模型 (0.5 天)

**檔案**: `momentum/Optimization/optimization_config.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

class ObjectiveMode(str, Enum):
    RATIO_SEPARATION = "ratio_separation"  # 雙密度模式（預設）
    SEPARATION = "separation"              # 單密度模式（備用）

@dataclass
class SearchSpace:
    """搜索空間配置"""
    ema_short_range: Tuple[int, int] = (5, 20)
    ema_mid_range: Tuple[int, int] = (15, 40)
    ema_long_range: Tuple[int, int] = (30, 60)
    strategy_logics: List[str] = field(
        default_factory=lambda: ["three_line", "short_long_cross"]
    )

@dataclass
class OptimizationConfig:
    """優化任務配置"""
    # 基本設定
    study_name: str
    data_source: str                       # 單選：close/volume/taker_ratio
    n_trials: int = 200
    timeout_hours: Optional[float] = None
    random_seed: int = 42
    
    # 搜索空間
    search_space: SearchSpace = field(default_factory=SearchSpace)
    
    # 優化目標
    objective_mode: ObjectiveMode = ObjectiveMode.RATIO_SEPARATION
    
    # 容錯設定
    checkpoint_interval: int = 50
    max_retries_per_trial: int = 3
    enable_pruning: bool = True
    
    # 存儲路徑
    storage_dir: str = "./optuna_storage"
    
    def get_storage_url(self) -> str:
        return f"sqlite:///{self.storage_dir}/{self.study_name}.db"
    
    def get_checkpoint_dir(self) -> str:
        return f"{self.storage_dir}/checkpoints/{self.study_name}"
```

**驗收標準**:
- [ ] Pydantic/dataclass 驗證完整
- [ ] 支援從 dict/JSON 載入
- [ ] 路徑自動建立

---

### STEP 2: 檢查點管理器 (1 天)

**檔案**: `momentum/Optimization/checkpoint_manager.py`

```python
import pickle
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import optuna

class CheckpointManager:
    """
    斷點續跑管理器
    
    功能：
    1. 定期保存完整狀態（每 N 次試驗）
    2. 支援從檢查點恢復
    3. 自動清理舊檢查點
    """
    
    def __init__(
        self, 
        checkpoint_dir: str, 
        interval: int = 50,
        keep_last_n: int = 3
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.interval = interval
        self.keep_last_n = keep_last_n
        self.last_save_time = time.time()
    
    def should_save(self, trial_number: int) -> bool:
        """判斷是否需要保存檢查點"""
        return trial_number > 0 and trial_number % self.interval == 0
    
    def save_checkpoint(
        self, 
        study: optuna.Study, 
        trial_number: int,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存檢查點
        
        內容：
        - study_name
        - best_value, best_params
        - trials_dataframe
        - timestamp
        - extra_data（可選）
        """
        checkpoint = {
            "study_name": study.study_name,
            "trial_number": trial_number,
            "best_value": study.best_value if study.best_trial else None,
            "best_params": study.best_params if study.best_trial else None,
            "best_trial_number": study.best_trial.number if study.best_trial else None,
            "n_trials": len(study.trials),
            "timestamp": datetime.now().isoformat(),
            "trials_summary": self._summarize_trials(study),
            "extra_data": extra_data or {}
        }
        
        filename = f"checkpoint_trial_{trial_number:04d}.pkl"
        filepath = self.checkpoint_dir / filename
        
        with open(filepath, "wb") as f:
            pickle.dump(checkpoint, f)
        
        self.last_save_time = time.time()
        self._cleanup_old_checkpoints()
        
        return str(filepath)
    
    def load_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """載入最新檢查點"""
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.pkl"))
        if not checkpoints:
            return None
        
        with open(checkpoints[-1], "rb") as f:
            return pickle.load(f)
    
    def _summarize_trials(self, study: optuna.Study) -> Dict:
        """摘要試驗資訊"""
        completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        return {
            "completed": len(completed),
            "pruned": len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
            "failed": len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
        }
    
    def _cleanup_old_checkpoints(self):
        """清理舊檢查點，只保留最近 N 個"""
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.pkl"))
        if len(checkpoints) > self.keep_last_n:
            for old_ckpt in checkpoints[:-self.keep_last_n]:
                old_ckpt.unlink()
```

**驗收標準**:
- [ ] 中斷後重啟可從最後完成的試驗繼續
- [ ] 檢查點包含完整狀態信息
- [ ] 自動清理舊檢查點

---

### STEP 3: 錯誤處理器 (0.5 天)

**檔案**: `momentum/Optimization/error_handler.py`

```python
import gc
import time
import traceback
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import optuna

class ErrorCategory(str, Enum):
    RETRYABLE = "retryable"     # 記憶體不足、暫時性 IO 錯誤
    PRUNABLE = "prunable"       # 無效參數組合、計算異常
    FATAL = "fatal"             # 數據損壞、配置錯誤

class ErrorAction(str, Enum):
    RETRY = "retry"
    PRUNE = "prune"
    ABORT = "abort"

@dataclass
class ErrorRecord:
    trial_number: int
    error_type: str
    error_message: str
    category: ErrorCategory
    action_taken: ErrorAction
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    traceback: Optional[str] = None

class OptimizationErrorHandler:
    """
    優化錯誤處理器
    
    功能：
    1. 分類錯誤類型
    2. 決定處理動作（重試/剪枝/終止）
    3. 記錄錯誤日誌
    """
    
    RETRYABLE_ERRORS = (
        MemoryError,
        IOError,
        TimeoutError,
        ConnectionError,
    )
    
    def __init__(self, max_retries: int = 3, retry_delay_base: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.error_log: List[ErrorRecord] = []
    
    def handle_trial_error(
        self, 
        trial: optuna.Trial, 
        error: Exception, 
        attempt: int
    ) -> ErrorAction:
        """處理試驗錯誤，返回應採取的動作"""
        category = self._classify_error(error)
        
        if category == ErrorCategory.RETRYABLE and attempt < self.max_retries:
            self._prepare_retry(attempt)
            action = ErrorAction.RETRY
        elif category == ErrorCategory.PRUNABLE:
            trial.set_user_attr("error", str(error))
            action = ErrorAction.PRUNE
        else:
            action = ErrorAction.ABORT
        
        self._log_error(trial.number, error, category, action)
        return action
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分類錯誤類型"""
        if isinstance(error, self.RETRYABLE_ERRORS):
            return ErrorCategory.RETRYABLE
        elif isinstance(error, (ValueError, KeyError, optuna.TrialPruned)):
            return ErrorCategory.PRUNABLE
        else:
            return ErrorCategory.FATAL
    
    def _prepare_retry(self, attempt: int):
        """準備重試：清理記憶體、延遲等待"""
        gc.collect()
        delay = self.retry_delay_base ** attempt
        time.sleep(delay)
    
    def _log_error(
        self, 
        trial_number: int, 
        error: Exception, 
        category: ErrorCategory,
        action: ErrorAction
    ):
        """記錄錯誤"""
        record = ErrorRecord(
            trial_number=trial_number,
            error_type=type(error).__name__,
            error_message=str(error),
            category=category,
            action_taken=action,
            traceback=traceback.format_exc()
        )
        self.error_log.append(record)
    
    def generate_error_report(self) -> Dict:
        """生成錯誤報告摘要"""
        if not self.error_log:
            return {"total_errors": 0, "breakdown": {}}
        
        breakdown = {}
        for record in self.error_log:
            key = f"{record.category.value}_{record.action_taken.value}"
            breakdown[key] = breakdown.get(key, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "breakdown": breakdown,
            "recent_errors": [
                {
                    "trial": r.trial_number,
                    "type": r.error_type,
                    "message": r.error_message[:100]
                }
                for r in self.error_log[-5:]
            ]
        }
```

**驗收標準**:
- [ ] 可重試錯誤自動重試（最多 3 次）
- [ ] 單次試驗失敗不影響整體優化
- [ ] 錯誤報告完整記錄

---

### STEP 4: 進度監控器 (0.5 天)

**檔案**: `momentum/Optimization/progress_monitor.py`

```python
import time
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass, field
import optuna
from api.core.logging import get_logger

logger = get_logger("optuna.progress")

@dataclass
class ProgressState:
    """進度狀態"""
    n_completed: int = 0
    n_total: int = 0
    best_value: Optional[float] = None
    best_trial_number: Optional[int] = None
    elapsed_seconds: float = 0
    estimated_remaining_seconds: float = 0
    trials_per_hour: float = 0

class ProgressMonitor:
    """
    進度監控器
    
    功能：
    1. 追蹤完成進度
    2. 預估剩餘時間
    3. 記錄最佳值演進
    4. 支援外部回調通知
    """
    
    def __init__(
        self, 
        total_trials: int,
        on_progress: Optional[Callable[[ProgressState], None]] = None,
        on_new_best: Optional[Callable[[int, float, dict], None]] = None
    ):
        self.total_trials = total_trials
        self.start_time = time.time()
        self.best_history: List[Tuple[int, float]] = []
        self.on_progress = on_progress
        self.on_new_best = on_new_best
    
    def __call__(self, study: optuna.Study, trial: optuna.FrozenTrial):
        """Optuna callback - 每次試驗後調用"""
        state = self._calculate_state(study)
        
        # 檢查是否有新最佳值
        if study.best_trial and study.best_value is not None:
            if not self.best_history or study.best_value > self.best_history[-1][1]:
                self.best_history.append((trial.number, study.best_value))
                self._log_new_best(study)
                if self.on_new_best:
                    self.on_new_best(
                        trial.number, 
                        study.best_value, 
                        study.best_params
                    )
        
        # 記錄進度
        self._log_progress(state)
        
        # 外部回調
        if self.on_progress:
            self.on_progress(state)
    
    def _calculate_state(self, study: optuna.Study) -> ProgressState:
        """計算當前進度狀態"""
        n_completed = len([
            t for t in study.trials 
            if t.state == optuna.trial.TrialState.COMPLETE
        ])
        elapsed = time.time() - self.start_time
        
        if n_completed > 0:
            avg_time = elapsed / n_completed
            remaining = avg_time * (self.total_trials - n_completed)
            trials_per_hour = n_completed / (elapsed / 3600)
        else:
            remaining = 0
            trials_per_hour = 0
        
        return ProgressState(
            n_completed=n_completed,
            n_total=self.total_trials,
            best_value=study.best_value if study.best_trial else None,
            best_trial_number=study.best_trial.number if study.best_trial else None,
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=remaining,
            trials_per_hour=trials_per_hour
        )
    
    def _log_progress(self, state: ProgressState):
        """記錄進度日誌"""
        progress_pct = state.n_completed / state.n_total * 100
        remaining_str = self._format_time(state.estimated_remaining_seconds)
        
        logger.info(
            f"[Optuna] 進度: {state.n_completed}/{state.n_total} ({progress_pct:.1f}%) | "
            f"最佳值: {state.best_value:.4f if state.best_value else 'N/A'} | "
            f"預計剩餘: {remaining_str}"
        )
    
    def _log_new_best(self, study: optuna.Study):
        """記錄新最佳值"""
        params_str = ", ".join(
            f"{k}={v}" for k, v in study.best_params.items()
        )
        logger.info(
            f"[Optuna] ✨ 新最佳值! Trial #{study.best_trial.number}: "
            f"ratio_sep={study.best_value:.4f}, params={{{params_str}}}"
        )
    
    def _format_time(self, seconds: float) -> str:
        """格式化時間"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分鐘"
        else:
            return f"{seconds/3600:.1f}小時"
    
    def get_convergence_data(self) -> List[Tuple[int, float]]:
        """獲取收斂曲線數據"""
        return self.best_history.copy()
```

**驗收標準**:
- [ ] 實時顯示進度百分比
- [ ] 預估剩餘時間準確（±20%）
- [ ] 記錄最佳值收斂曲線

---

### STEP 5: 數據驗證器 (0.5 天)

**檔案**: `momentum/Utils/data_validator.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from pathlib import Path
import pandas as pd
from api.core.logging import get_logger

logger = get_logger("data_validator")

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class DataValidator:
    """
    數據驗證器
    
    功能：
    1. 優化前驗證案例完整性
    2. 運行中抽樣驗證結果
    """
    
    MIN_CASES_PER_GROUP = 10
    MAX_TIME_OVERLAP_PCT = 0.1
    
    def validate_before_optimization(
        self,
        positive_cases: List,
        negative_cases: List,
        required_timeframes: Optional[List[str]] = None
    ) -> ValidationResult:
        """優化前驗證"""
        errors = []
        warnings = []
        
        # 1. 檢查案例數量
        if len(positive_cases) < self.MIN_CASES_PER_GROUP:
            errors.append(
                f"正例數量不足: {len(positive_cases)} < {self.MIN_CASES_PER_GROUP}"
            )
        if len(negative_cases) < self.MIN_CASES_PER_GROUP:
            errors.append(
                f"反例數量不足: {len(negative_cases)} < {self.MIN_CASES_PER_GROUP}"
            )
        
        # 2. 檢查時間範圍重疊
        if positive_cases and negative_cases:
            overlap_pct = self._check_time_overlap(positive_cases, negative_cases)
            if overlap_pct > self.MAX_TIME_OVERLAP_PCT:
                warnings.append(
                    f"正反例時間重疊過高: {overlap_pct:.1%} > {self.MAX_TIME_OVERLAP_PCT:.1%}"
                )
        
        # 3. 檢查案例唯一性
        pos_ids = set(c.case_id for c in positive_cases)
        neg_ids = set(c.case_id for c in negative_cases)
        overlap_ids = pos_ids & neg_ids
        if overlap_ids:
            errors.append(f"發現 {len(overlap_ids)} 個案例同時出現在正反例中")
        
        # 4. 檢查必要欄位
        for i, case in enumerate(positive_cases[:3]):  # 抽樣檢查
            missing = self._check_required_fields(case)
            if missing:
                errors.append(f"正例 #{i} 缺少必要欄位: {missing}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_trial_result(
        self,
        trial_number: int,
        positive_avg_ratio: float,
        negative_avg_ratio: float,
        p_value: float
    ) -> bool:
        """運行中驗證單次試驗結果"""
        # 檢查 ratio 範圍（應為正數，通常 0.5-3.0）
        if positive_avg_ratio <= 0 or positive_avg_ratio > 10:
            logger.warning(
                f"Trial {trial_number}: 異常 positive_ratio={positive_avg_ratio}"
            )
            return False
        
        if negative_avg_ratio <= 0 or negative_avg_ratio > 10:
            logger.warning(
                f"Trial {trial_number}: 異常 negative_ratio={negative_avg_ratio}"
            )
            return False
        
        # 檢查 p_value 範圍
        if pd.isna(p_value) or p_value < 0 or p_value > 1:
            logger.warning(
                f"Trial {trial_number}: 異常 p_value={p_value}"
            )
            return False
        
        return True
    
    def _check_time_overlap(
        self, 
        positive_cases: List, 
        negative_cases: List
    ) -> float:
        """檢查正反例時間範圍重疊比例"""
        pos_timestamps = set(c.timestamp for c in positive_cases)
        neg_timestamps = set(c.timestamp for c in negative_cases)
        
        # 以正例為基準計算重疊比例
        if not pos_timestamps:
            return 0.0
        
        overlap = pos_timestamps & neg_timestamps
        return len(overlap) / len(pos_timestamps)
    
    def _check_required_fields(self, case) -> List[str]:
        """檢查案例必要欄位"""
        required = ["case_id", "symbol", "timestamp", "timeframe"]
        missing = []
        for field in required:
            if not hasattr(case, field) or getattr(case, field) is None:
                missing.append(field)
        return missing
```

**驗收標準**:
- [ ] 啟動前檢測數據問題
- [ ] 運行中定期抽樣驗證
- [ ] 問題清晰報告

---

### STEP 6: 主優化器整合 (1 天)

**檔案**: `momentum/Optimization/optuna_optimizer.py` (修改)

```python
import asyncio
from typing import List, Optional, Dict, Any
import optuna
from optuna.samplers import TPESampler

from .optimization_config import OptimizationConfig, SearchSpace
from .checkpoint_manager import CheckpointManager
from .error_handler import OptimizationErrorHandler, ErrorAction
from .progress_monitor import ProgressMonitor
from momentum.Utils.data_validator import DataValidator
from api.services.signal_analysis_service import SignalAnalysisService
from api.models.training_window_config import (
    SignalDensityRequest, 
    SignalDensityResponse,
    TrainingWindowConfig,
    StrategyConfig
)
from api.core.logging import get_logger

logger = get_logger("optuna.optimizer")

class OptunaOptimizer:
    """
    Optuna 參數優化器
    
    優化目標：maximize ratio_separation
    容錯機制：斷點續跑、錯誤重試、進度監控
    """
    
    def __init__(
        self,
        config: OptimizationConfig,
        signal_service: SignalAnalysisService
    ):
        self.config = config
        self.signal_service = signal_service
        
        # 初始化組件
        self.checkpoint_mgr = CheckpointManager(
            config.get_checkpoint_dir(),
            config.checkpoint_interval
        )
        self.error_handler = OptimizationErrorHandler(
            config.max_retries_per_trial
        )
        self.progress_monitor = ProgressMonitor(config.n_trials)
        self.data_validator = DataValidator()
        
        # 初始化 Optuna Study
        self.study = optuna.create_study(
            study_name=config.study_name,
            storage=config.get_storage_url(),
            load_if_exists=True,  # 斷點續跑關鍵
            direction="maximize",
            sampler=TPESampler(seed=config.random_seed)
        )
        
        # 狀態
        self.positive_cases: List = []
        self.negative_cases: List = []
        self.training_window: Optional[TrainingWindowConfig] = None
    
    async def optimize(
        self,
        positive_cases: List,
        negative_cases: List,
        training_window: TrainingWindowConfig
    ) -> "OptimizationResult":
        """執行完整優化流程"""
        
        # Step 1: 數據驗證
        validation = self.data_validator.validate_before_optimization(
            positive_cases, negative_cases
        )
        if not validation.is_valid:
            raise ValueError(f"數據驗證失敗: {validation.errors}")
        
        if validation.warnings:
            for warning in validation.warnings:
                logger.warning(f"數據警告: {warning}")
        
        # 保存案例引用
        self.positive_cases = positive_cases
        self.negative_cases = negative_cases
        self.training_window = training_window
        
        # Step 2: 計算剩餘試驗數
        completed_trials = len([
            t for t in self.study.trials 
            if t.state == optuna.trial.TrialState.COMPLETE
        ])
        remaining_trials = self.config.n_trials - completed_trials
        
        if remaining_trials <= 0:
            logger.info("優化已完成，無需繼續")
            return self._generate_result()
        
        logger.info(
            f"開始優化: 已完成 {completed_trials}/{self.config.n_trials}, "
            f"剩餘 {remaining_trials} 次試驗"
        )
        
        # Step 3: 執行優化
        self.study.optimize(
            lambda trial: asyncio.get_event_loop().run_until_complete(
                self._objective(trial)
            ),
            n_trials=remaining_trials,
            timeout=self.config.timeout_hours * 3600 if self.config.timeout_hours else None,
            callbacks=[
                self.progress_monitor,
                self._checkpoint_callback
            ],
            catch=(Exception,)
        )
        
        # Step 4: 生成結果
        return self._generate_result()
    
    async def _objective(self, trial: optuna.Trial) -> float:
        """目標函數（帶錯誤處理和重試）"""
        
        for attempt in range(self.config.max_retries_per_trial):
            try:
                # 1. 採樣參數
                params = self._sample_params(trial)
                
                # 2. 構建策略配置
                strategy_config = StrategyConfig(
                    data_source=self.config.data_source,
                    indicator_type="ema",
                    strategy_logic=params["strategy_logic"],
                    params={
                        "ema_short": params["ema_short"],
                        "ema_mid": params.get("ema_mid"),
                        "ema_long": params["ema_long"]
                    }
                )
                
                # 3. 計算信號密度
                request = SignalDensityRequest(
                    strategy_config=strategy_config,
                    training_window=self.training_window,
                    positive_cases=self.positive_cases,
                    negative_cases=self.negative_cases
                )
                
                result = await self.signal_service.analyze_signal_density(request)
                
                # 4. 驗證結果
                if not self.data_validator.validate_trial_result(
                    trial.number,
                    result.positive_near_far_ratio,
                    result.negative_near_far_ratio,
                    result.ratio_p_value
                ):
                    raise optuna.TrialPruned()
                
                # 5. 記錄完整統計
                trial.set_user_attr("positive_avg_ratio", result.positive_near_far_ratio)
                trial.set_user_attr("negative_avg_ratio", result.negative_near_far_ratio)
                trial.set_user_attr("p_value", result.ratio_p_value)
                trial.set_user_attr("cohens_d", result.ratio_cohens_d)
                trial.set_user_attr("stability_cv", result.stability_cv)
                trial.set_user_attr("positive_avg_density", result.positive_avg_density)
                trial.set_user_attr("negative_avg_density", result.negative_avg_density)
                
                # 6. 返回優化目標
                return result.ratio_separation
                
            except optuna.TrialPruned:
                raise  # 直接傳遞剪枝
            except Exception as e:
                action = self.error_handler.handle_trial_error(trial, e, attempt)
                if action == ErrorAction.RETRY:
                    continue
                elif action == ErrorAction.PRUNE:
                    raise optuna.TrialPruned()
                else:
                    raise
        
        # 所有重試失敗
        raise optuna.TrialPruned()
    
    def _sample_params(self, trial: optuna.Trial) -> Dict[str, Any]:
        """採樣參數"""
        space = self.config.search_space
        
        # 策略邏輯
        strategy_logic = trial.suggest_categorical(
            "strategy_logic", 
            space.strategy_logics
        )
        
        # EMA 參數
        ema_short = trial.suggest_int(
            "ema_short", 
            space.ema_short_range[0], 
            space.ema_short_range[1]
        )
        ema_long = trial.suggest_int(
            "ema_long", 
            space.ema_long_range[0], 
            space.ema_long_range[1]
        )
        
        # 中期 EMA（僅三線排列需要）
        ema_mid = None
        if strategy_logic == "three_line":
            mid_min = max(space.ema_mid_range[0], ema_short + 3)
            mid_max = min(space.ema_mid_range[1], ema_long - 3)
            
            if mid_min >= mid_max:
                raise optuna.TrialPruned()
            
            ema_mid = trial.suggest_int("ema_mid", mid_min, mid_max)
        
        # 參數有效性檢查
        if strategy_logic == "three_line":
            if not (ema_short < ema_mid < ema_long):
                raise optuna.TrialPruned()
        else:
            if not (ema_short < ema_long):
                raise optuna.TrialPruned()
        
        return {
            "strategy_logic": strategy_logic,
            "ema_short": ema_short,
            "ema_mid": ema_mid,
            "ema_long": ema_long
        }
    
    def _checkpoint_callback(
        self, 
        study: optuna.Study, 
        trial: optuna.FrozenTrial
    ):
        """檢查點回調"""
        if self.checkpoint_mgr.should_save(trial.number):
            filepath = self.checkpoint_mgr.save_checkpoint(study, trial.number)
            logger.info(f"已保存檢查點: {filepath}")
    
    def _generate_result(self) -> "OptimizationResult":
        """生成優化結果"""
        return OptimizationResult(
            study_name=self.config.study_name,
            best_value=self.study.best_value,
            best_params=self.study.best_params,
            best_trial_number=self.study.best_trial.number if self.study.best_trial else None,
            n_trials=len(self.study.trials),
            n_completed=len([
                t for t in self.study.trials 
                if t.state == optuna.trial.TrialState.COMPLETE
            ]),
            convergence_history=self.progress_monitor.get_convergence_data(),
            error_report=self.error_handler.generate_error_report(),
            trials_dataframe=self.study.trials_dataframe()
        )


@dataclass
class OptimizationResult:
    """優化結果"""
    study_name: str
    best_value: Optional[float]
    best_params: Optional[Dict[str, Any]]
    best_trial_number: Optional[int]
    n_trials: int
    n_completed: int
    convergence_history: List[Tuple[int, float]]
    error_report: Dict
    trials_dataframe: Any  # pd.DataFrame
```

**驗收標準**:
- [ ] 完整優化流程可執行
- [ ] 所有容錯機制正常運作
- [ ] 結果可重現（設定 random_seed）

---

### STEP 7: 結果分析器 (1 天)

**檔案**: `momentum/Optimization/result_analyzer.py`

```python
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
import optuna
from dataclasses import dataclass

@dataclass
class ParamImportance:
    """參數重要性"""
    param_name: str
    importance: float  # 0-1

@dataclass
class StabilityAnalysis:
    """穩定性分析"""
    monthly_separations: Dict[str, float]  # {month: ratio_sep}
    mean: float
    std: float
    cv: float
    worst_month: str
    worst_value: float

@dataclass
class AnalysisResult:
    """完整分析結果"""
    # 最佳結果
    best_trial_number: int
    best_params: Dict[str, Any]
    best_ratio_separation: float
    best_p_value: float
    best_cohens_d: float
    
    # 參數重要性
    param_importances: List[ParamImportance]
    
    # 參數空間熱力圖數據
    heatmap_data: Dict[str, Any]
    
    # 收斂分析
    convergence_data: List[Tuple[int, float]]
    convergence_trial: int  # 收斂點
    
    # 穩定性分析
    stability: StabilityAnalysis
    
    # Top N 試驗
    top_trials: pd.DataFrame


class ResultAnalyzer:
    """
    優化結果分析器
    
    功能：
    1. 參數重要性分析
    2. 參數空間熱力圖
    3. 收斂分析
    4. 穩定性分析
    5. 試驗排名
    """
    
    def __init__(self, study: optuna.Study):
        self.study = study
        self.df = study.trials_dataframe()
    
    def analyze(self, top_n: int = 20) -> AnalysisResult:
        """執行完整分析"""
        
        # 1. 最佳結果
        best = self.study.best_trial
        
        # 2. 參數重要性
        importances = self._calculate_param_importances()
        
        # 3. 參數空間熱力圖
        heatmap = self._generate_heatmap_data()
        
        # 4. 收斂分析
        convergence_data, convergence_trial = self._analyze_convergence()
        
        # 5. 穩定性分析（使用最佳參數）
        stability = self._analyze_stability(best.params)
        
        # 6. Top N 試驗
        top_trials = self._get_top_trials(top_n)
        
        return AnalysisResult(
            best_trial_number=best.number,
            best_params=best.params,
            best_ratio_separation=best.value,
            best_p_value=best.user_attrs.get("p_value", 1.0),
            best_cohens_d=best.user_attrs.get("cohens_d", 0.0),
            param_importances=importances,
            heatmap_data=heatmap,
            convergence_data=convergence_data,
            convergence_trial=convergence_trial,
            stability=stability,
            top_trials=top_trials
        )
    
    def _calculate_param_importances(self) -> List[ParamImportance]:
        """計算參數重要性"""
        try:
            importances = optuna.importance.get_param_importances(self.study)
            return [
                ParamImportance(name, value)
                for name, value in importances.items()
            ]
        except Exception:
            return []
    
    def _generate_heatmap_data(self) -> Dict[str, Any]:
        """生成參數空間熱力圖數據"""
        completed = self.df[self.df["state"] == "COMPLETE"].copy()
        
        if len(completed) < 10:
            return {"error": "數據不足"}
        
        # 提取 ema_short vs ema_long 的熱力圖數據
        if "params_ema_short" not in completed.columns:
            return {"error": "缺少參數欄位"}
        
        heatmap_points = []
        for _, row in completed.iterrows():
            heatmap_points.append({
                "ema_short": row.get("params_ema_short"),
                "ema_long": row.get("params_ema_long"),
                "value": row.get("value", 0)
            })
        
        return {
            "points": heatmap_points,
            "x_label": "ema_short",
            "y_label": "ema_long",
            "value_label": "ratio_separation"
        }
    
    def _analyze_convergence(self) -> Tuple[List[Tuple[int, float]], int]:
        """分析收斂情況"""
        completed = self.df[self.df["state"] == "COMPLETE"].copy()
        completed = completed.sort_values("number")
        
        # 計算累積最佳值
        best_so_far = []
        current_best = float("-inf")
        
        for _, row in completed.iterrows():
            if row["value"] > current_best:
                current_best = row["value"]
            best_so_far.append((int(row["number"]), current_best))
        
        # 找收斂點（後 20% 試驗改進 < 5%）
        if len(best_so_far) > 10:
            n_tail = max(1, len(best_so_far) // 5)
            tail_values = [v for _, v in best_so_far[-n_tail:]]
            
            if tail_values[-1] > 0:
                improvement = (tail_values[-1] - tail_values[0]) / tail_values[-1]
                if improvement < 0.05:
                    convergence_trial = best_so_far[-n_tail][0]
                else:
                    convergence_trial = len(best_so_far)
            else:
                convergence_trial = len(best_so_far)
        else:
            convergence_trial = len(best_so_far)
        
        return best_so_far, convergence_trial
    
    def _analyze_stability(self, best_params: Dict) -> StabilityAnalysis:
        """分析策略穩定性（按月份）"""
        # 此處需要實際計算每月的 ratio_separation
        # 暫時返回模擬數據，實際實現需要重新計算
        
        # TODO: 實現按月份重新計算
        monthly_sep = {
            "2021-01": 0.72,
            "2021-02": 0.68,
            "2021-03": 0.81,
        }
        
        values = list(monthly_sep.values())
        mean_val = np.mean(values)
        std_val = np.std(values)
        cv = std_val / mean_val if mean_val > 0 else 0
        
        worst_month = min(monthly_sep, key=monthly_sep.get)
        
        return StabilityAnalysis(
            monthly_separations=monthly_sep,
            mean=mean_val,
            std=std_val,
            cv=cv,
            worst_month=worst_month,
            worst_value=monthly_sep[worst_month]
        )
    
    def _get_top_trials(self, top_n: int) -> pd.DataFrame:
        """獲取 Top N 試驗"""
        completed = self.df[self.df["state"] == "COMPLETE"].copy()
        
        # 提取關鍵欄位
        result = completed[[
            "number", "value", 
            "params_strategy_logic",
            "params_ema_short", 
            "params_ema_mid",
            "params_ema_long",
            "user_attrs_p_value",
            "user_attrs_cohens_d",
            "user_attrs_stability_cv"
        ]].copy()
        
        result.columns = [
            "trial", "ratio_separation",
            "strategy", "ema_short", "ema_mid", "ema_long",
            "p_value", "cohens_d", "stability_cv"
        ]
        
        return result.nlargest(top_n, "ratio_separation")
```

**驗收標準**:
- [ ] 參數重要性計算正確
- [ ] 熱力圖數據格式正確
- [ ] 收斂點判斷合理

---

### STEP 8: API 服務封裝 (0.5 天)

**檔案**: `api/services/optimization_service.py`

```python
import asyncio
import uuid
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from momentum.Optimization.optuna_optimizer import OptunaOptimizer, OptimizationResult
from momentum.Optimization.optimization_config import OptimizationConfig
from momentum.Optimization.result_analyzer import ResultAnalyzer, AnalysisResult
from api.services.signal_analysis_service import SignalAnalysisService
from api.core.logging import get_logger

logger = get_logger("api.optimization")

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class OptimizationTask:
    task_id: str
    status: TaskStatus
    config: OptimizationConfig
    progress: float = 0.0
    best_value: Optional[float] = None
    best_params: Optional[Dict] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[OptimizationResult] = None
    analysis: Optional[AnalysisResult] = None


class OptimizationService:
    """優化任務服務"""
    
    def __init__(self):
        self.tasks: Dict[str, OptimizationTask] = {}
        self.signal_service = SignalAnalysisService()
    
    async def start_optimization(
        self,
        config: OptimizationConfig,
        positive_cases: list,
        negative_cases: list,
        training_window: dict
    ) -> OptimizationTask:
        """啟動優化任務（異步）"""
        task_id = str(uuid.uuid4())
        
        task = OptimizationTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            config=config
        )
        self.tasks[task_id] = task
        
        # 異步執行優化
        asyncio.create_task(
            self._run_optimization(task_id, positive_cases, negative_cases, training_window)
        )
        
        return task
    
    async def _run_optimization(
        self,
        task_id: str,
        positive_cases: list,
        negative_cases: list,
        training_window: dict
    ):
        """執行優化任務"""
        task = self.tasks[task_id]
        
        try:
            task.status = TaskStatus.RUNNING
            
            optimizer = OptunaOptimizer(
                config=task.config,
                signal_service=self.signal_service
            )
            
            # 設置進度回調
            def on_progress(state):
                task.progress = state.n_completed / state.n_total
                task.best_value = state.best_value
            
            optimizer.progress_monitor.on_progress = on_progress
            
            # 執行優化
            result = await optimizer.optimize(
                positive_cases=positive_cases,
                negative_cases=negative_cases,
                training_window=training_window
            )
            
            # 分析結果
            analyzer = ResultAnalyzer(optimizer.study)
            analysis = analyzer.analyze()
            
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = result
            task.analysis = analysis
            task.best_value = result.best_value
            task.best_params = result.best_params
            task.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"優化任務失敗: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
    
    def get_task_status(self, task_id: str) -> Optional[OptimizationTask]:
        """獲取任務狀態"""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            return True
        return False
```

**API 端點** (`api/routes/optimization.py`):

```python
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from api.services.optimization_service import OptimizationService, TaskStatus

router = APIRouter(prefix="/api/v1/optimization", tags=["Optimization"])
service = OptimizationService()

class StartOptimizationRequest(BaseModel):
    study_name: str
    data_source: str  # close/volume/taker_ratio
    n_trials: int = 200
    timeout_hours: Optional[float] = None
    ema_short_range: tuple = (5, 20)
    ema_mid_range: tuple = (15, 40)
    ema_long_range: tuple = (30, 60)
    strategy_logics: list = ["three_line", "short_long_cross"]
    positive_case_ids: list
    negative_case_ids: list
    training_window: dict

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    best_value: Optional[float]
    best_params: Optional[dict]
    error_message: Optional[str]

@router.post("/start")
async def start_optimization(request: StartOptimizationRequest):
    """啟動優化任務"""
    # 構建配置...
    task = await service.start_optimization(...)
    return {"task_id": task.task_id, "status": task.status.value}

@router.get("/{task_id}/status")
async def get_status(task_id: str) -> TaskStatusResponse:
    """獲取任務狀態"""
    task = service.get_task_status(task_id)
    if not task:
        raise HTTPException(404, "任務不存在")
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        best_value=task.best_value,
        best_params=task.best_params,
        error_message=task.error_message
    )

@router.get("/{task_id}/result")
async def get_result(task_id: str):
    """獲取優化結果"""
    task = service.get_task_status(task_id)
    if not task:
        raise HTTPException(404, "任務不存在")
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(400, f"任務狀態: {task.status.value}")
    return {
        "result": task.result,
        "analysis": task.analysis
    }

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任務"""
    success = service.cancel_task(task_id)
    return {"success": success}
```

**驗收標準**:
- [ ] 啟動優化返回 task_id
- [ ] 可查詢進度和狀態
- [ ] 完成後可獲取結果

---

## 五、前端實作步驟

### STEP 9: Optuna 參數設定面板 (1 天)

**檔案**: `frontend/src/components/strategy-test/OptunaConfigPanel.tsx`

```tsx
/**
 * OptunaConfigPanel - Optuna 優化參數設定
 * 
 * 整合至 /strategy-test 頁面的折疊面板區域
 * 復用現有 UI 組件：Select, NumberInput
 */

import React from "react";
import { Select, SelectOption } from "@/components/ui/Select";
import { NumberInput } from "@/components/ui/NumberInput";
import { Settings, Zap, Target } from "lucide-react";

interface SearchSpaceConfig {
  ema_short_min: number;
  ema_short_max: number;
  ema_mid_min: number;
  ema_mid_max: number;
  ema_long_min: number;
  ema_long_max: number;
  strategy_logics: string[];
}

interface OptunaConfig {
  enabled: boolean;
  n_trials: number;
  timeout_hours: number | null;
  random_seed: number;
  enable_pruning: boolean;
  enable_checkpoint: boolean;
  search_space: SearchSpaceConfig;
}

interface OptunaConfigPanelProps {
  config: OptunaConfig;
  onChange: (config: OptunaConfig) => void;
  disabled?: boolean;
}

const STRATEGY_OPTIONS: SelectOption[] = [
  { value: "three_line", label: "三線排列 (short < mid < long)" },
  { value: "short_long_cross", label: "短長交叉 (short < long)" },
  { value: "mid_long_cross", label: "中長交叉 (mid < long)" },
];

export default function OptunaConfigPanel({
  config,
  onChange,
  disabled = false,
}: OptunaConfigPanelProps) {
  
  const updateField = <K extends keyof OptunaConfig>(
    field: K,
    value: OptunaConfig[K]
  ) => {
    onChange({ ...config, [field]: value });
  };
  
  const updateSearchSpace = <K extends keyof SearchSpaceConfig>(
    field: K,
    value: SearchSpaceConfig[K]
  ) => {
    onChange({
      ...config,
      search_space: { ...config.search_space, [field]: value },
    });
  };

  return (
    <div className="space-y-6">
      {/* 啟用開關 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-500" />
          <span className="font-medium text-slate-900">Optuna 優化</span>
        </div>
        <label className="relative inline-flex cursor-pointer items-center">
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) => updateField("enabled", e.target.checked)}
            disabled={disabled}
            className="peer sr-only"
          />
          <div className="peer h-6 w-11 rounded-full bg-slate-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-indigo-600 peer-checked:after:translate-x-full" />
        </label>
      </div>

      {config.enabled && (
        <>
          {/* 基本設定 */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h4 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
              <Settings className="h-4 w-4" />
              基本設定
            </h4>
            
            <div className="grid grid-cols-2 gap-4">
              <NumberInput
                label="試驗次數"
                value={config.n_trials}
                onChange={(v) => updateField("n_trials", v)}
                min={50}
                max={1000}
                step={50}
                disabled={disabled}
              />
              
              <NumberInput
                label="超時限制 (小時)"
                value={config.timeout_hours || 0}
                onChange={(v) => updateField("timeout_hours", v || null)}
                min={0}
                max={24}
                step={0.5}
                disabled={disabled}
                placeholder="無限制"
              />
              
              <NumberInput
                label="隨機種子"
                value={config.random_seed}
                onChange={(v) => updateField("random_seed", v)}
                min={0}
                max={999999}
                disabled={disabled}
              />
            </div>
            
            <div className="mt-4 flex flex-wrap gap-4">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={config.enable_pruning}
                  onChange={(e) => updateField("enable_pruning", e.target.checked)}
                  disabled={disabled}
                  className="rounded border-slate-300"
                />
                啟用剪枝（提前終止差勁試驗）
              </label>
              
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={config.enable_checkpoint}
                  onChange={(e) => updateField("enable_checkpoint", e.target.checked)}
                  disabled={disabled}
                  className="rounded border-slate-300"
                />
                啟用斷點續跑
              </label>
            </div>
          </div>

          {/* 搜索空間 */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h4 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
              <Target className="h-4 w-4" />
              EMA 週期搜索範圍
            </h4>
            
            <div className="space-y-4">
              {/* 短期 EMA */}
              <div>
                <p className="mb-2 text-xs text-slate-500">短期 EMA</p>
                <div className="flex items-center gap-2">
                  <NumberInput
                    value={config.search_space.ema_short_min}
                    onChange={(v) => updateSearchSpace("ema_short_min", v)}
                    min={3}
                    max={30}
                    disabled={disabled}
                    className="w-20"
                  />
                  <span className="text-slate-400">~</span>
                  <NumberInput
                    value={config.search_space.ema_short_max}
                    onChange={(v) => updateSearchSpace("ema_short_max", v)}
                    min={5}
                    max={40}
                    disabled={disabled}
                    className="w-20"
                  />
                </div>
              </div>
              
              {/* 中期 EMA */}
              <div>
                <p className="mb-2 text-xs text-slate-500">中期 EMA</p>
                <div className="flex items-center gap-2">
                  <NumberInput
                    value={config.search_space.ema_mid_min}
                    onChange={(v) => updateSearchSpace("ema_mid_min", v)}
                    min={10}
                    max={50}
                    disabled={disabled}
                    className="w-20"
                  />
                  <span className="text-slate-400">~</span>
                  <NumberInput
                    value={config.search_space.ema_mid_max}
                    onChange={(v) => updateSearchSpace("ema_mid_max", v)}
                    min={15}
                    max={60}
                    disabled={disabled}
                    className="w-20"
                  />
                </div>
              </div>
              
              {/* 長期 EMA */}
              <div>
                <p className="mb-2 text-xs text-slate-500">長期 EMA</p>
                <div className="flex items-center gap-2">
                  <NumberInput
                    value={config.search_space.ema_long_min}
                    onChange={(v) => updateSearchSpace("ema_long_min", v)}
                    min={20}
                    max={80}
                    disabled={disabled}
                    className="w-20"
                  />
                  <span className="text-slate-400">~</span>
                  <NumberInput
                    value={config.search_space.ema_long_max}
                    onChange={(v) => updateSearchSpace("ema_long_max", v)}
                    min={30}
                    max={120}
                    disabled={disabled}
                    className="w-20"
                  />
                </div>
              </div>
            </div>
            
            {/* 策略邏輯選擇 */}
            <div className="mt-4">
              <p className="mb-2 text-xs text-slate-500">策略邏輯（多選）</p>
              <div className="flex flex-wrap gap-2">
                {STRATEGY_OPTIONS.map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
                      config.search_space.strategy_logics.includes(opt.value)
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={config.search_space.strategy_logics.includes(opt.value)}
                      onChange={(e) => {
                        const newLogics = e.target.checked
                          ? [...config.search_space.strategy_logics, opt.value]
                          : config.search_space.strategy_logics.filter((l) => l !== opt.value);
                        updateSearchSpace("strategy_logics", newLogics);
                      }}
                      disabled={disabled}
                      className="sr-only"
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* 預估資訊 */}
          <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            <p>
              📊 預估執行時間: ~{Math.ceil(config.n_trials * 0.5)} 分鐘
              （{config.n_trials} 次試驗）
            </p>
          </div>
        </>
      )}
    </div>
  );
}
```

**整合方式**: 作為新的 AccordionItem 加入 `/strategy-test` 頁面

**驗收標準**:
- [ ] 啟用/停用切換正常
- [ ] 參數範圍輸入合法
- [ ] 策略邏輯多選正常
- [ ] 預估時間顯示

---

### STEP 10-15: 結果展示組件 (3.5 天)

由於篇幅限制，以下提供組件清單和關鍵實現要點：

#### STEP 10: 最佳結果卡片 (0.5 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/BestResultCard.tsx`

- 復用現有 `StatMetricCard` 組件
- 顯示：ratio_separation、正例 ratio、反例 ratio、p-value、Cohen's d、穩定性 CV
- 最佳參數：data_source、strategy、EMA 參數
- 操作按鈕：複製參數、重新測試

#### STEP 11: 參數重要性圖 (0.5 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/ParamImportanceChart.tsx`

- 水平條狀圖
- 使用 Recharts BarChart
- 顯示每個參數的重要性百分比

#### STEP 12: 參數空間熱力圖 (1 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/ParamHeatmap.tsx`

- 二維熱力圖（ema_short vs ema_long）
- 使用 Recharts ScatterChart 或自訂 SVG
- 顏色深度表示 ratio_separation 大小
- 標記最佳區域

#### STEP 13: 收斂曲線 (0.5 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/ConvergencePlot.tsx`

- 折線圖顯示最佳值演進
- X 軸：試驗編號
- Y 軸：ratio_separation
- 標記收斂點

#### STEP 14: 穩定性分析圖 (0.5 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/StabilityChart.tsx`

- 按月份顯示 ratio_separation
- 標記最差月份
- 顯示統計指標（mean、std、CV）

#### STEP 15: 試驗排名表格 (0.5 天)

**檔案**: `frontend/src/components/strategy-test/OptimizationResults/TrialRankingTable.tsx`

- 表格顯示 Top 20 試驗
- 欄位：Rank、Strategy、EMA Params、Ratio Sep.、p-value、Cohen's d、CV
- 支援排序
- 支援匯出 CSV

---

## 六、頁面整合（不改變現有格式）

### 整合原則

1. **新增折疊面板**：在現有「優化參數」之後新增「Optuna 優化」面板
2. **切換顯示結果**：根據測試模式（單次/Optuna）切換結果區域內容
3. **復用現有組件**：StatMetricCard、CombinedDensityBoxplot 等
4. **保持佈局**：30%/70% 的左右分割不變

### 修改 `/strategy-test/page.tsx`

```tsx
// 新增狀態
const [optunaConfig, setOptunaConfig] = useState<OptunaConfig>(defaultOptunaConfig);
const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
const [isOptimizing, setIsOptimizing] = useState(false);

// 新增折疊面板（在「優化參數」之後）
<AccordionItem
  id="optuna"
  title="Optuna 優化"
  icon={<Zap className="h-5 w-5" />}
  badge={optunaConfig.enabled ? `${optunaConfig.n_trials} 次` : "關閉"}
>
  <OptunaConfigPanel
    config={optunaConfig}
    onChange={setOptunaConfig}
    disabled={isRunning || isOptimizing}
  />
</AccordionItem>

// 結果區域條件渲染
{optimizationResult ? (
  <OptimizationResultsContainer result={optimizationResult} />
) : (
  // 現有的單次測試結果顯示
  <SingleTestResults testResult={testResult} />
)}

// 執行按鈕邏輯
const handleExecute = async () => {
  if (optunaConfig.enabled) {
    await handleStartOptimization();
  } else {
    await handleSingleTest();
  }
};
```

---

## 七、時程規劃總表

| 階段 | 步驟 | 內容 | 時間 | 累計 |
|------|------|------|------|------|
| **後端** | STEP 1 | 優化配置模型 | 0.5天 | 0.5天 |
| | STEP 2 | 檢查點管理器 | 1天 | 1.5天 |
| | STEP 3 | 錯誤處理器 | 0.5天 | 2天 |
| | STEP 4 | 進度監控器 | 0.5天 | 2.5天 |
| | STEP 5 | 數據驗證器 | 0.5天 | 3天 |
| | STEP 6 | 主優化器整合 | 1天 | 4天 |
| | STEP 7 | 結果分析器 | 1天 | 5天 |
| | STEP 8 | API 服務封裝 | 0.5天 | 5.5天 |
| **前端** | STEP 9 | Optuna 參數設定 UI | 1天 | 6.5天 |
| | STEP 10 | 最佳結果卡片 | 0.5天 | 7天 |
| | STEP 11 | 參數重要性圖 | 0.5天 | 7.5天 |
| | STEP 12 | 參數空間熱力圖 | 1天 | 8.5天 |
| | STEP 13 | 收斂曲線 | 0.5天 | 9天 |
| | STEP 14 | 穩定性分析圖 | 0.5天 | 9.5天 |
| | STEP 15 | 試驗排名表格 | 0.5天 | 10天 |
| **整合** | STEP 16 | 前後端整合測試 | 0.5天 | 10.5天 |

---

## 八、驗收標準總表

| 類別 | 驗收項目 | 測試方法 |
|------|----------|----------|
| **功能** | 優化目標正確（ratio_separation 最大化） | 對照手動計算 |
| **功能** | 統計指標計算正確（p-value, Cohen's d） | 對照 scipy |
| **功能** | 參數採樣有效（符合約束條件） | 檢查 trial 參數 |
| **容錯** | 中斷後重啟可自動續跑 | 模擬斷電重啟 |
| **容錯** | 錯誤試驗不影響整體進度 | 注入異常測試 |
| **性能** | 長時間運行（4小時+）穩定 | 壓力測試 |
| **數據** | 結果可重現（設定 random_seed） | 重複執行比對 |
| **UI** | 現有頁面格式不變 | 視覺對比 |
| **UI** | 進度可視化清晰 | 手動測試 |
| **UI** | 結果圖表正確渲染 | 手動測試 |

---

## 九、風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 優化時間過長 | 用戶體驗差 | 提供進度條、預估時間、支援取消 |
| 記憶體不足 | 崩潰 | 定期 gc.collect()、錯誤重試機制 |
| 統計不顯著 | 結果無意義 | 明確顯示 p-value，警告用戶 |
| 過擬合 | 策略不可用 | 強調穩定性分析，按月檢驗 |

---

## 十、注意事項

1. **數據源單選**：每次優化只處理一個數據源（close/volume/taker_ratio），避免記憶體崩潰
2. **不改變現有格式**：所有新功能以附加方式整合，不修改現有 UI 結構
3. **復用現有組件**：優先使用 StatMetricCard、Select、NumberInput 等已有組件
4. **統計基於 ratio**：所有統計指標（p-value、Cohen's d）都是對 near_far_ratio 列表計算
5. **只優化一個目標**：maximize ratio_separation，其他指標僅記錄不參與優化

---

## 十一、參考資料

- 現有代碼：`frontend/src/app/strategy-test/page.tsx`
- 現有 Hook：`frontend/src/hooks/useStrategyConfig.ts`
- 信號密度分析：`momentum/Analysis/signal_density_analyzer.py`
- Optuna 文檔：https://optuna.readthedocs.io/

---

*文檔版本: 1.0*
*最後更新: 2025-11-28