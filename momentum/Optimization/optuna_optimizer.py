"""
Optuna參數優化引擎 - Ultra Think 最終優化版本

核心功能:
1. 自動搜索最佳EMA策略參數組合
2. 優化目標: 最大化正反例信號密度差異(separation)或加權雙密度得分(weighted dual-density)
3. 支援多種優化器(TPE/CmaEs/Random/GP/NSGA-II)
4. 多目標優化(separation + stability,Pareto前沿)
5. 斷點續跑機制(SQLite持久化)
6. 並行多進程優化
7. 雙密度模式: 加權優化信號聚集(clustering)和正反例區分(discrimination)

Ultra Think 記錄:
- Day 1 步驟1: 初版代碼 - 核心優化邏輯和目標函數(TPE/CmaEs/Random)
- Day 1 步驟2: 審查優化 - 發現6個優化點(async/event loop、數據驗證、錯誤處理等)
- Day 1 步驟3: 最終優化 - 修復所有P0/P1問題,添加參數範圍配置和詳細日誌
- Day 2 步驟1: 進階優化器 - 新增GP/NSGA-II兩種Sampler
- Day 2 步驟2: 多目標優化 - 實作multi_objective_function(separation + stability)
- Day 2 步驟3: Pareto分析 - 整合ParetoAnalyzer,提供get_pareto_analysis()方法
- Day 3 步驟1: CheckpointManager - 手動檢查點保存機制(每50次試驗,pickle格式)
- Day 3 步驟2: ErrorHandler - 錯誤分類與重試機制(exponential backoff)
- Day 3 步驟3: 整合 - 包裝器模式整合重試邏輯,callback整合檢查點保存
- Day 4 步驟1: ProgressMonitor - 進度追蹤與實時通知(里程碑、ETA、試驗速度)
- Day 4 步驟2: 整合 - callback整合進度監控,檢查點包含progress_statistics
- Day 5 步驟1: 雙密度模式 - 檢測far_lookback_bars,自動切換優化目標為ratio_separation

優化內容:
Day 1:
- ✅ 修復async/event loop衝突(使用run_in_executor)
- ✅ 添加數據驗證(確保案例ID真實存在)
- ✅ 細化錯誤處理(區分可重試/不可重試/致命錯誤)
- ✅ 支援參數範圍配置(從外部傳入,無硬編碼)
- ✅ 增強日誌記錄(階段性進度日誌)
- ✅ 完善類型提示(pandas.DataFrame等)

Day 2:
- ✅ 新增GPSampler(貝葉斯優化,適合昂貴目標函數)
- ✅ 新增NSGAIISampler(遺傳算法,多目標優化)
- ✅ 實作multi_objective_function(同時優化separation和stability)
- ✅ 支援多目標Study創建(directions=["maximize", "maximize"])
- ✅ 整合ParetoAnalyzer(識別Pareto前沿,推薦膝點)
- ✅ 新增get_pareto_analysis()方法(便捷獲取Pareto分析結果)

Day 3:
- ✅ CheckpointManager整合(__init__添加checkpoint_manager實例)
- ✅ ErrorHandler整合(__init__添加error_handler實例)
- ✅ 重試包裝器(_objective_function_with_retry,_multi_objective_function_with_retry)
- ✅ 檢查點保存(optimize()的callback每50次試驗自動保存)
- ✅ 錯誤統計(檢查點包含error_statistics數據)
- ✅ 參數配置(checkpoint_dir,checkpoint_interval,max_retries,retry_base_delay)

Day 4:
- ✅ ProgressMonitor整合(__init__添加enable_progress_monitor,progress_notification_callback)
- ✅ optimize()創建ProgressMonitor實例(total_trials,notification_callback)
- ✅ callback整合進度監控(on_trial_complete自動調用)
- ✅ 檢查點包含progress_statistics(completion_percentage,ETA,trials_per_hour等)
- ✅ 優化完成調用finish()(發送optimization_finished通知)
- ✅ 里程碑通知(25%/50%/75%),新最佳值通知,實時進度更新

Day 5:
- ✅ 雙密度模式檢測(檢查training_window.far_lookback_bars是否存在)
- ✅ 目標函數切換(雙密度模式使用ratio_separation,單密度使用separation)
- ✅ 日誌記錄增強(顯示當前優化模式和目標)
- ✅ 步驟2: 加權雙密度優化(方案D) - 同時優化信號聚集和正反例區分
  - clustering_weight參數控制權重(預設0.5)
  - clustering_score = positive_near_far_ratio - 1.0 (聚集程度)
  - discrimination_score = ratio_separation (區分度)
  - objective = clustering_weight * clustering_score + (1-clustering_weight) * discrimination_score

Author: Claude (Phase 3.5)
Date: 2025-11-02 (Updated: 2025-11-12)
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Tuple, TYPE_CHECKING
import asyncio
from dataclasses import dataclass, field
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# 延遲導入 optuna 以避免 sklearn 在模塊加載時初始化
if TYPE_CHECKING:
    import optuna
    from optuna import Trial, Study
    from optuna.samplers import BaseSampler
    from optuna.pruners import BasePruner

from api.models.training_window_config import (
    SignalDensityRequest,
    SignalDensityResponse,
    TrainingWindowConfig,
    StrategyConfig
)
from api.models.strategy_test_models import ParameterRange
from api.services.signal_analysis_service import SignalAnalysisService
from api.utils.case_storage import get_case_storage_manager

# 導入新增的容錯機制
from momentum.Optimization.checkpoint_manager import CheckpointManager
from momentum.Optimization.error_handler import OptimizationErrorHandler, ErrorType
from momentum.Optimization.progress_monitor import ProgressMonitor, ProgressStats

# 導入動態策略系統 (Phase 2 Refactoring)
# Note: strategy_registry 使用 lazy import 避免循環依賴
from momentum.Optimization.strategy_metadata import ParameterType


# ==================== 錯誤分類定義 ====================

class RetryableError(Exception):
    """可重試錯誤(網絡、暫時性記憶體不足等)"""
    pass


class NonRetryableError(Exception):
    """不可重試錯誤(參數驗證失敗、數據損壞等)"""
    pass


class FatalError(Exception):
    """致命錯誤(系統級錯誤,需終止優化)"""
    pass


# ==================== 數據類定義 ====================

@dataclass
class ParameterRanges:
    """
    參數搜索範圍配置

    定義Optuna優化時的參數搜索空間。
    支援從外部配置傳入,避免硬編碼。

    Attributes:
        ema_short_range: 短期EMA範圍(min, max)
        ema_mid_range: 中期EMA範圍(min, max,僅三線排列)
        ema_long_range: 長期EMA範圍(min, max)
        data_sources: 可選數據源列表
        strategy_logics: 可選策略邏輯列表
        indicator_types: 可選指標類型列表（尊重用戶選擇）
    """
    ema_short_range: Tuple[int, int] = (5, 200)
    ema_mid_range: Tuple[int, int] = (10, 200)
    ema_long_range: Tuple[int, int] = (20, 200)
    data_sources: List[str] = field(
        default_factory=lambda: [
            'close', 'open', 'high', 'low',
            'volume', 'taker_buy_volume', 'taker_ratio'
        ]
    )
    strategy_logics: List[str] = field(
        default_factory=lambda: [
            'three_line', 'short_long_cross', 'mid_long_cross'
        ]
    )
    indicator_types: List[str] = field(
        default_factory=lambda: ['ema']  # 默認只使用已實現的 EMA
    )

    def __post_init__(self):
        """
        Ultra Think Step 3 優化: 驗證參數範圍配置的合法性

        確保:
        1. short_max < mid_min (短期EMA最大值必須小於中期EMA最小值)
        2. mid_max < long_min (中期EMA最大值必須小於長期EMA最小值)
        3. 範圍值必須為正整數

        Raises:
            ValueError: 參數範圍配置不合法
        """
        # 驗證範圍值為正整數
        for range_name, range_value in [
            ('ema_short_range', self.ema_short_range),
            ('ema_mid_range', self.ema_mid_range),
            ('ema_long_range', self.ema_long_range)
        ]:
            if len(range_value) != 2:
                raise ValueError(
                    f"{range_name} must be a tuple of (min, max), got {range_value}"
                )
            min_val, max_val = range_value
            if not (isinstance(min_val, int) and isinstance(max_val, int)):
                raise ValueError(
                    f"{range_name} must contain integers, got ({type(min_val)}, {type(max_val)})"
                )
            if min_val <= 0 or max_val <= 0:
                raise ValueError(
                    f"{range_name} must be positive, got ({min_val}, {max_val})"
                )
            if min_val >= max_val:
                raise ValueError(
                    f"{range_name} min must be less than max, got ({min_val}, {max_val})"
                )

        # 驗證三線排列約束: short < mid < long
        short_min, short_max = self.ema_short_range
        mid_min, mid_max = self.ema_mid_range
        long_min, long_max = self.ema_long_range

        if short_max >= mid_min:
            raise ValueError(
                f"EMA parameter ranges overlap: short_max ({short_max}) >= mid_min ({mid_min}). "
                f"三線排列要求 short < mid < long，請調整參數範圍。"
            )

        if mid_max >= long_min:
            raise ValueError(
                f"EMA parameter ranges overlap: mid_max ({mid_max}) >= long_min ({long_min}). "
                f"三線排列要求 short < mid < long，請調整參數範圍。"
            )


@dataclass
class OptimizationResult:
    """
    優化結果數據類

    封裝Optuna優化完成後的結果信息。

    Attributes:
        best_value: 最佳目標值(separation)
        best_params: 最佳參數字典
        best_trial_number: 最佳試驗編號
        total_trials: 總試驗次數
        optimization_time: 優化總耗時(秒)
        convergence_history: 收斂曲線(每次試驗的最佳值)
        study_name: Study名稱
    """
    best_value: float
    best_params: Dict[str, Any]
    best_trial_number: int
    total_trials: int
    optimization_time: float
    convergence_history: List[float]
    study_name: str


class OptunaOptimizer:
    """
    Optuna參數優化器

    核心功能:
    1. 創建/載入Optuna Study(支援斷點續跑)
    2. 定義目標函數(整合信號密度分析)
    3. 執行優化搜索(支援並行)
    4. 獲取優化結果

    設計原則:
    - First Principle: 優化目標是"最大化正反例密度差異",而非Win Rate
    - 數據真實性: 所有數據來自真實案例和實際計算
    - 容錯穩健: SQLite持久化,支援電腦當機後恢復

    Example:
        >>> optimizer = OptunaOptimizer(
        ...     study_name="ema_optimization_1",
        ...     storage="sqlite:///data/optuna_study.db",
        ...     sampler_type="TPE",
        ...     n_trials=100
        ... )
        >>> result = await optimizer.optimize(
        ...     positive_cases=["case1", "case2"],
        ...     negative_cases=["case3", "case4"],
        ...     training_window=training_window_config
        ... )
        >>> print(f"Best separation: {result.best_value}")
        >>> print(f"Best params: {result.best_params}")
    """

    def __init__(
        self,
        study_name: str,
        storage: str = "sqlite:///data/optuna_study.db",
        sampler_type: str = "TPE",
        pruner_type: Optional[str] = "Median",
        n_trials: int = 100,
        n_jobs: int = 1,
        timeout: Optional[int] = None,
        random_seed: Optional[int] = 42,
        parameter_ranges: Optional[ParameterRanges] = None,
        use_multi_objective: bool = False,
        checkpoint_dir: str = "data/checkpoints",
        checkpoint_interval: int = 50,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        enable_progress_monitor: bool = True,
        progress_notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        clustering_weight: float = 0.5
    ):
        """
        初始化Optuna優化器

        Args:
            study_name: Study名稱(用於SQLite存儲和續跑)
            storage: SQLite數據庫路徑
            sampler_type: 優化器類型(TPE/CmaEs/Random/GP/NSGA-II)
            pruner_type: 剪枝器類型(Median/Percentile/None)
            n_trials: 試驗次數
            n_jobs: 並行核心數(1=串行,>1=並行)
            timeout: 總優化超時(秒,None=無限制)
            random_seed: 隨機種子(可重現性)
            parameter_ranges: 參數搜索範圍(None使用預設)
            use_multi_objective: 是否使用多目標優化(separation + stability)
            checkpoint_dir: 檢查點保存目錄(default: data/checkpoints)
            checkpoint_interval: 檢查點保存間隔(每N次試驗,default: 50)
            max_retries: 錯誤最大重試次數(default: 3)
            retry_base_delay: 重試基礎延遲(秒,default: 1.0)
            enable_progress_monitor: 是否啟用進度監控(default: True)
            progress_notification_callback: 進度通知回調函數(event_type, data)
            clustering_weight: 雙密度模式中聚集得分的權重(0.0-1.0, default: 0.5)
                              - 聚集得分: 測量正例信號在近期窗口的聚集程度
                              - 區分得分: 測量正反例的near/far ratio差異
                              - 加權公式: clustering_weight * 聚集得分 + (1-clustering_weight) * 區分得分
        """
        self.study_name = study_name
        self.storage = storage
        self.sampler_type = sampler_type
        self.pruner_type = pruner_type
        self.n_trials = n_trials
        self.n_jobs = n_jobs
        self.timeout = timeout
        self.random_seed = random_seed
        self.parameter_ranges = parameter_ranges or ParameterRanges()
        self.use_multi_objective = use_multi_objective
        self.enable_progress_monitor = enable_progress_monitor
        self.progress_notification_callback = progress_notification_callback
        self.clustering_weight = clustering_weight

        # 依賴服務
        self.signal_service = SignalAnalysisService()
        self.case_storage = get_case_storage_manager()

        # 日誌
        self.logger = logging.getLogger(__name__)

        # Study對象(延遲初始化)
        self.study: Optional["Study"] = None

        # 優化配置(在optimize()時設置)
        self.positive_cases: List[str] = []
        self.negative_cases: List[str] = []
        self.training_window: Optional[TrainingWindowConfig] = None

        # ThreadPoolExecutor for async compatibility
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Day 3: 新增容錯機制
        # CheckpointManager: 手動檢查點保存(每50次試驗)
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=checkpoint_dir,
            save_interval=checkpoint_interval,
            max_checkpoints=10
        )

        # OptimizationErrorHandler: 錯誤分類與重試機制
        self.error_handler = OptimizationErrorHandler(
            max_retries=max_retries,
            base_delay=retry_base_delay
        )

        # Day 4: ProgressMonitor (在optimize()時初始化,因為需要n_trials)
        self.progress_monitor: Optional[ProgressMonitor] = None

        self.logger.info(
            f"OptunaOptimizer initialized: study_name={study_name}, "
            f"sampler={sampler_type}, n_trials={n_trials}, "
            f"param_ranges={self.parameter_ranges}, "
            f"checkpoint_interval={checkpoint_interval}, max_retries={max_retries}"
        )

    def _create_sampler(self) -> "BaseSampler":
        """
        創建Sampler(優化器)

        支援的Sampler:
        - TPE: Tree-structured Parzen Estimator(預設,推薦)
        - CmaEs: 協方差矩陣自適應演化策略
        - Random: 隨機搜索(基準對比)
        - GP: Gaussian Process(貝葉斯優化,適合昂貴目標函數)
        - NSGA-II: 遺傳算法(多目標優化,返回Pareto前沿)

        Returns:
            Sampler對象

        Raises:
            ValueError: 不支援的sampler類型
        """
        # 延遲導入
        from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler, GPSampler, NSGAIISampler

        if self.sampler_type == 'TPE':
            return TPESampler(
                seed=self.random_seed,
                n_startup_trials=25,  # 前25次隨機試驗
                n_ei_candidates=24     # 期望改善候選數
            )
        elif self.sampler_type == 'CmaEs':
            return CmaEsSampler(
                seed=self.random_seed,
                n_startup_trials=25
            )
        elif self.sampler_type == 'Random':
            return RandomSampler(seed=self.random_seed)
        elif self.sampler_type == 'GP':
            # Gaussian Process Sampler
            # 適用場景: 單次試驗耗時長(>10秒),試驗次數少(<100)
            return GPSampler(
                seed=self.random_seed,
                n_startup_trials=10,  # GP前期使用Random採樣
                independent_sampler=RandomSampler(seed=self.random_seed)
            )
        elif self.sampler_type == 'NSGA-II':
            # 多目標優化遺傳算法
            # 返回Pareto前沿解集(多個非支配解)
            return NSGAIISampler(
                population_size=50,     # 種群大小
                mutation_prob=0.1,      # 變異概率
                crossover_prob=0.9,     # 交叉概率
                seed=self.random_seed
            )
        else:
            raise ValueError(
                f"Unknown sampler type: {self.sampler_type}. "
                f"Supported: TPE, CmaEs, Random, GP, NSGA-II"
            )

    def _create_pruner(self) -> "BasePruner":
        """
        創建Pruner(剪枝器)

        支援的Pruner:
        - Median: 低於中位數時剪枝(預設)
        - Percentile: 低於百分位時剪枝
        - None: 不剪枝

        Returns:
            Pruner對象

        Raises:
            ValueError: 不支援的pruner類型
        """
        # 延遲導入
        from optuna.pruners import MedianPruner, PercentilePruner, NopPruner

        if self.pruner_type == 'Median':
            return MedianPruner(
                n_startup_trials=5,  # 前5次不剪枝
                n_warmup_steps=0,
                interval_steps=1
            )
        elif self.pruner_type == 'Percentile':
            return PercentilePruner(
                percentile=25.0,     # 低於25%時剪枝
                n_startup_trials=5
            )
        elif self.pruner_type is None or self.pruner_type == 'None':
            return NopPruner()
        else:
            raise ValueError(
                f"Unknown pruner type: {self.pruner_type}. "
                f"Supported: Median, Percentile, None"
            )

    def create_study(self) -> "Study":
        """
        創建或載入Optuna Study

        功能:
        1. 檢查SQLite數據庫是否存在該Study
        2. 存在則載入(斷點續跑)
        3. 不存在則創建新Study

        Returns:
            Optuna Study對象

        Design Note:
        - direction="maximize"(單目標): 最大化separation(正例密度 - 反例密度)
        - directions=["maximize", "maximize"](多目標): separation和stability
        - load_if_exists=True: 支援斷點續跑
        """
        # 延遲導入
        import optuna

        sampler = self._create_sampler()
        pruner = self._create_pruner()

        # 多目標優化: separation + stability
        if self.use_multi_objective:
            study = optuna.create_study(
                study_name=self.study_name,
                storage=self.storage,
                sampler=sampler,
                pruner=pruner,
                directions=["maximize", "maximize"],  # [separation, stability]
                load_if_exists=True
            )
            self.logger.info(
                f"Multi-objective study created/loaded: {self.study_name}, "
                f"previous trials: {len(study.trials)}"
            )
        # 單目標優化: separation only
        else:
            study = optuna.create_study(
                study_name=self.study_name,
                storage=self.storage,
                sampler=sampler,
                pruner=pruner,
                direction="maximize",  # 最大化separation
                load_if_exists=True
            )
            self.logger.info(
                f"Study created/loaded: {self.study_name}, "
                f"previous trials: {len(study.trials)}"
            )

        self.study = study
        return study

    async def _objective_function_with_retry(self, trial: "Trial") -> float:
        """
        帶重試機制的目標函數包裝器

        功能:
        1. 調用_objective_function_core執行實際計算
        2. 捕獲異常並使用ErrorHandler分類錯誤
        3. 根據錯誤類型決定是否重試(exponential backoff)
        4. 記錄錯誤統計

        Args:
            trial: Optuna Trial對象

        Returns:
            separation(密度差異)
        """
        # 延遲導入
        import optuna

        attempt = 1

        while attempt <= self.error_handler.max_retries + 1:  # +1 for initial attempt
            try:
                return await self._objective_function_core(trial)

            except optuna.TrialPruned:
                # 參數不合法,直接剪枝(不重試)
                raise

            except Exception as e:
                # 使用ErrorHandler處理錯誤
                should_retry, delay = self.error_handler.handle_trial_error(
                    trial_number=trial.number,
                    exception=e,
                    attempt=attempt
                )

                if should_retry and delay is not None:
                    # 等待後重試
                    await asyncio.sleep(delay)
                    attempt += 1
                else:
                    # 不重試,返回極差值或剪枝
                    error_type = self.error_handler.classify_error(e)
                    if error_type == ErrorType.FATAL:
                        # 致命錯誤: 返回極差值並警告
                        self.logger.critical(
                            f"Trial {trial.number} encountered FATAL error, "
                            f"returning worst value (-999.0)"
                        )
                        return -999.0
                    elif error_type == ErrorType.NON_RETRYABLE:
                        # 不可重試錯誤: 剪枝此試驗
                        raise optuna.TrialPruned()
                    else:
                        # 其他情況: 返回較差值
                        return -500.0

        # 超過最大重試次數
        self.logger.error(f"Trial {trial.number} exceeded max retries ({self.error_handler.max_retries})")
        return -999.0

    async def _objective_function_core(self, trial: "Trial") -> float:
        """
        Optuna目標函數核心實作(不含重試邏輯)

        核心算法:
        1. 參數採樣: 從搜索空間採樣參數組合
        2. 參數驗證: 確保參數約束(如short < mid < long)
        3. 調用信號密度分析: 計算正反例的平均信號密度
        4. 檢測雙密度模式: 若training_window有far_lookback_bars,使用ratio_separation
        5. 計算目標值:
           - 單密度模式: separation = positive_avg - negative_avg
           - 雙密度模式: ratio_separation = positive_near_far_ratio - negative_near_far_ratio
        6. 返回目標值: Optuna將最大化此值

        Args:
            trial: Optuna Trial對象

        Returns:
            目標值(單密度:separation / 雙密度:ratio_separation)

        Raises:
            optuna.TrialPruned: 參數不合法時剪枝
            Exception: 其他錯誤由_objective_function_with_retry處理

        Design Note:
        - 優化目標:
          - 單密度: 最大化正反例信號密度差異(而非Win Rate)
          - 雙密度: 最大化正反例near/far ratio差異(檢測信號聚集)
        - 參數約束: 三線排列必須 short < mid < long
        - 數據源: 從DataSourceEnum中選擇,無硬編碼
        """
        # 延遲導入
        import optuna

        try:
            # ==================== Phase 2 重構：動態參數採樣 ====================
            # 步驟1: 採樣固定參數（data_source, strategy_logic, indicator_type）
            data_source = trial.suggest_categorical(
                'data_source',
                self.parameter_ranges.data_sources
            )

            strategy_logic = trial.suggest_categorical(
                'strategy_logic',
                self.parameter_ranges.strategy_logics
            )

            # 指標類型：尊重用戶在前端的選擇
            # 如果用戶選擇了特定指標類型，則只使用該類型；否則使用所有可用類型
            indicator_type = trial.suggest_categorical(
                'indicator_type',
                self.parameter_ranges.indicator_types
            )

            # 步驟2: 根據策略元數據動態採樣參數
            # Lazy import to avoid circular dependency
            from momentum.Analysis.strategy_registry import strategy_registry

            try:
                metadata = strategy_registry.get_strategy(strategy_logic)
            except ValueError as e:
                self.logger.error(f"Strategy '{strategy_logic}' not found: {e}")
                raise optuna.TrialPruned()

            # 動態採樣策略參數
            params = {}

            # 參數範圍覆蓋邏輯: 優先使用前端傳遞的 parameter_ranges，否則使用 YAML 默認值
            range_overrides = {}
            if self.parameter_ranges:
                # 構建參數名到範圍的映射
                if hasattr(self.parameter_ranges, 'ema_short_range') and self.parameter_ranges.ema_short_range:
                    range_overrides['short_period'] = self.parameter_ranges.ema_short_range
                if hasattr(self.parameter_ranges, 'ema_mid_range') and self.parameter_ranges.ema_mid_range:
                    range_overrides['mid_period'] = self.parameter_ranges.ema_mid_range
                if hasattr(self.parameter_ranges, 'ema_long_range') and self.parameter_ranges.ema_long_range:
                    range_overrides['long_period'] = self.parameter_ranges.ema_long_range

            self.logger.debug(f"Parameter range overrides: {range_overrides}")

            for param_def in metadata.parameters:
                param_name = param_def.name

                if param_def.type == ParameterType.INT:
                    # 使用覆蓋範圍（如果有）
                    if param_name in range_overrides:
                        min_val, max_val = range_overrides[param_name]
                        self.logger.debug(
                            f"Using frontend range for {param_name}: [{min_val}, {max_val}] "
                            f"(YAML default: [{param_def.min_value}, {param_def.max_value}])"
                        )
                    else:
                        min_val = int(param_def.min_value)
                        max_val = int(param_def.max_value)

                    params[param_name] = trial.suggest_int(
                        param_name,
                        min_val,
                        max_val,
                        step=int(param_def.step) if param_def.step else 1
                    )
                elif param_def.type == ParameterType.FLOAT:
                    params[param_name] = trial.suggest_float(
                        param_name,
                        param_def.min_value,
                        param_def.max_value,
                        step=param_def.step
                    )
                elif param_def.type == ParameterType.CATEGORICAL:
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_def.choices
                    )

            # 添加 indicator_type 和 data_source 到 params（策略函數需要）
            params['indicator_type'] = indicator_type
            params['data_source'] = data_source

            # 步驟3: 參數驗證（使用策略註冊系統）
            validation_result = strategy_registry.validate_parameters(
                strategy_logic,
                params
            )

            if not validation_result.is_valid:
                error_msg = f"Parameter validation failed: {', '.join(validation_result.errors)}"
                self.logger.error(
                    f"Trial {trial.number} failed: {error_msg}"
                )
                raise ValueError(error_msg)

            # 步驟4: 組裝策略配置
            strategy_config = StrategyConfig(
                data_source=data_source,
                indicator_type=indicator_type,
                strategy_logic=strategy_logic,
                params=params
            )

            # 步驟4: 調用信號密度分析
            request = SignalDensityRequest(
                strategy_config=strategy_config,
                training_window=self.training_window,
                positive_cases=self.positive_cases,
                negative_cases=self.negative_cases
            )

            response: SignalDensityResponse = await self.signal_service.analyze_signal_density(request)

            # 步驟5: 檢測雙密度模式並計算目標值
            is_dual_density = (
                self.training_window.far_lookback_bars is not None
                and response.ratio_separation is not None
            )

            if is_dual_density:
                # 雙密度模式: 加權優化 (方案D)
                # Ultra Think Step 3 優化: 添加邊界條件檢查
                # 檢查 near/far ratio 是否有效 (必須 > 0)
                if (response.positive_near_far_ratio is None or
                    response.negative_near_far_ratio is None or
                    response.positive_near_far_ratio <= 0 or
                    response.negative_near_far_ratio <= 0):
                    self.logger.warning(
                        f"Trial {trial.number}: Invalid near/far ratio detected "
                        f"(pos={response.positive_near_far_ratio}, "
                        f"neg={response.negative_near_far_ratio}). "
                        f"數據異常，剪枝此 trial。"
                    )
                    raise optuna.TrialPruned()

                # 條件1得分: 正例信號聚集程度 (positive_near_far_ratio - 1.0)
                # - 若 ratio=1.5, score=0.5 (信號在近期聚集50%)
                # - 若 ratio=1.0, score=0.0 (無聚集效應)
                # - 若 ratio<1.0, score<0 (近期反而更少,懲罰)
                clustering_score = response.positive_near_far_ratio - 1.0

                # 條件2得分: 正反例區分度 (ratio_separation)
                discrimination_score = response.ratio_separation

                # 加權綜合得分
                clustering_weight = self.clustering_weight
                discrimination_weight = 1.0 - clustering_weight

                objective_value = (
                    clustering_weight * clustering_score +
                    discrimination_weight * discrimination_score
                )

                self.logger.info(
                    f"Trial {trial.number} [DUAL-DENSITY-WEIGHTED]: "
                    f"objective={objective_value:.4f} "
                    f"(clustering={clustering_score:.4f} [w={clustering_weight:.2f}], "
                    f"discrimination={discrimination_score:.4f} [w={discrimination_weight:.2f}]), "
                    f"pos_ratio={response.positive_near_far_ratio:.4f}, "
                    f"neg_ratio={response.negative_near_far_ratio:.4f}, "
                    f"params={trial.params}"
                )
            else:
                # 單密度模式: 優化separation
                objective_value = response.separation
                self.logger.info(
                    f"Trial {trial.number} [SINGLE-DENSITY]: "
                    f"separation={objective_value:.4f} "
                    f"(pos={response.positive_avg_density:.4f}, "
                    f"neg={response.negative_avg_density:.4f}), "
                    f"params={trial.params}"
                )

            # 步驟6: 存儲統計數據到 Trial user_attrs（供前端顯示和CSV匯出）
            # 核心統計指標
            trial.set_user_attr("p_value", response.p_value)
            trial.set_user_attr("cohens_d", response.cohens_d)
            trial.set_user_attr("stability_cv", response.stability_cv)
            trial.set_user_attr("positive_avg_density", response.positive_avg_density)
            trial.set_user_attr("negative_avg_density", response.negative_avg_density)
            trial.set_user_attr("separation", response.separation)

            # 雙密度模式額外存儲
            if is_dual_density:
                trial.set_user_attr("positive_near_far_ratio", response.positive_near_far_ratio)
                trial.set_user_attr("negative_near_far_ratio", response.negative_near_far_ratio)
                trial.set_user_attr("ratio_separation", response.ratio_separation)
                if response.positive_ratio_cv is not None:
                    trial.set_user_attr("positive_ratio_cv", response.positive_ratio_cv)
                if response.separation_cv is not None:
                    trial.set_user_attr("separation_cv", response.separation_cv)

            return objective_value

        except optuna.TrialPruned:
            # 參數不合法,重新拋出(由包裝器處理)
            raise
        except Exception:
            # 所有其他錯誤由_objective_function_with_retry的重試邏輯處理
            raise

    async def _multi_objective_function_with_retry(self, trial: "Trial") -> Tuple[float, float]:
        """
        帶重試機制的多目標函數包裝器

        功能:
        1. 調用_multi_objective_function_core執行實際計算
        2. 捕獲異常並使用ErrorHandler分類錯誤
        3. 根據錯誤類型決定是否重試(exponential backoff)
        4. 記錄錯誤統計

        Args:
            trial: Optuna Trial對象

        Returns:
            (separation, stability_score) 元組
        """
        # 延遲導入
        import optuna

        attempt = 1

        while attempt <= self.error_handler.max_retries + 1:
            try:
                return await self._multi_objective_function_core(trial)

            except optuna.TrialPruned:
                raise

            except Exception as e:
                should_retry, delay = self.error_handler.handle_trial_error(
                    trial_number=trial.number,
                    exception=e,
                    attempt=attempt
                )

                if should_retry and delay is not None:
                    await asyncio.sleep(delay)
                    attempt += 1
                else:
                    error_type = self.error_handler.classify_error(e)
                    if error_type == ErrorType.FATAL:
                        self.logger.critical(
                            f"Trial {trial.number} encountered FATAL error, "
                            f"returning worst values (-999.0, 0.0)"
                        )
                        return (-999.0, 0.0)
                    elif error_type == ErrorType.NON_RETRYABLE:
                        raise optuna.TrialPruned()
                    else:
                        return (-500.0, 0.0)

        self.logger.error(f"Trial {trial.number} exceeded max retries ({self.error_handler.max_retries})")
        return (-999.0, 0.0)

    async def _multi_objective_function_core(self, trial: "Trial") -> Tuple[float, float]:
        """
        多目標優化函數核心實作(不含重試邏輯)

        同時優化兩個目標:
        1. separation: 最大化正反例信號密度差異
        2. stability_score: 最大化穩定性(最小化變異係數)

        Args:
            trial: Optuna Trial對象

        Returns:
            (separation, stability_score) 元組

        Raises:
            optuna.TrialPruned: 參數不合法時剪枝
            Exception: 其他錯誤由_multi_objective_function_with_retry處理

        Design Note:
        - 穩定性計算: stability_score = 1.0 - min(cv, 1.0)
        - cv = std_separation / mean_separation (變異係數)
        - Pareto前沿: NSGA-II會返回多個非支配解
        """
        # 延遲導入
        import optuna

        try:
            # ==================== Phase 2 重構：動態參數採樣（多目標）====================
            # 步驟1: 採樣固定參數
            data_source = trial.suggest_categorical(
                'data_source',
                self.parameter_ranges.data_sources
            )

            strategy_logic = trial.suggest_categorical(
                'strategy_logic',
                self.parameter_ranges.strategy_logics
            )

            # 指標類型：尊重用戶在前端的選擇
            # 如果用戶選擇了特定指標類型，則只使用該類型；否則使用所有可用類型
            indicator_type = trial.suggest_categorical(
                'indicator_type',
                self.parameter_ranges.indicator_types
            )

            # 步驟2: 根據策略元數據動態採樣參數
            # Lazy import to avoid circular dependency
            from momentum.Analysis.strategy_registry import strategy_registry

            try:
                metadata = strategy_registry.get_strategy(strategy_logic)
            except ValueError as e:
                self.logger.error(f"Strategy '{strategy_logic}' not found: {e}")
                raise optuna.TrialPruned()

            # 動態採樣策略參數
            params = {}

            # 參數範圍覆蓋邏輯: 優先使用前端傳遞的 parameter_ranges，否則使用 YAML 默認值
            range_overrides = {}
            if self.parameter_ranges:
                # 構建參數名到範圍的映射
                if hasattr(self.parameter_ranges, 'ema_short_range') and self.parameter_ranges.ema_short_range:
                    range_overrides['short_period'] = self.parameter_ranges.ema_short_range
                if hasattr(self.parameter_ranges, 'ema_mid_range') and self.parameter_ranges.ema_mid_range:
                    range_overrides['mid_period'] = self.parameter_ranges.ema_mid_range
                if hasattr(self.parameter_ranges, 'ema_long_range') and self.parameter_ranges.ema_long_range:
                    range_overrides['long_period'] = self.parameter_ranges.ema_long_range

            self.logger.debug(f"Parameter range overrides: {range_overrides}")

            for param_def in metadata.parameters:
                param_name = param_def.name

                if param_def.type == ParameterType.INT:
                    # 使用覆蓋範圍（如果有）
                    if param_name in range_overrides:
                        min_val, max_val = range_overrides[param_name]
                        self.logger.debug(
                            f"Using frontend range for {param_name}: [{min_val}, {max_val}] "
                            f"(YAML default: [{param_def.min_value}, {param_def.max_value}])"
                        )
                    else:
                        min_val = int(param_def.min_value)
                        max_val = int(param_def.max_value)

                    params[param_name] = trial.suggest_int(
                        param_name,
                        min_val,
                        max_val,
                        step=int(param_def.step) if param_def.step else 1
                    )
                elif param_def.type == ParameterType.FLOAT:
                    params[param_name] = trial.suggest_float(
                        param_name,
                        param_def.min_value,
                        param_def.max_value,
                        step=param_def.step
                    )
                elif param_def.type == ParameterType.CATEGORICAL:
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_def.choices
                    )

            # 添加 indicator_type 和 data_source 到 params
            params['indicator_type'] = indicator_type
            params['data_source'] = data_source

            # 步驟3: 參數驗證
            validation_result = strategy_registry.validate_parameters(
                strategy_logic,
                params
            )

            if not validation_result.is_valid:
                error_msg = f"Parameter validation failed: {', '.join(validation_result.errors)}"
                self.logger.error(
                    f"Trial {trial.number} failed: {error_msg}"
                )
                raise ValueError(error_msg)

            # 步驟4: 組裝策略配置
            strategy_config = StrategyConfig(
                data_source=data_source,
                indicator_type=indicator_type,
                strategy_logic=strategy_logic,
                params=params
            )

            # 調用信號密度分析
            request = SignalDensityRequest(
                strategy_config=strategy_config,
                training_window=self.training_window,
                positive_cases=self.positive_cases,
                negative_cases=self.negative_cases
            )

            response: SignalDensityResponse = await self.signal_service.analyze_signal_density(request)

            # 目標1: separation
            separation = response.positive_avg_density - response.negative_avg_density

            # 目標2: stability_score
            # 計算變異係數(Coefficient of Variation): cv = std / mean
            # 變異係數越小,穩定性越高
            # 轉換為最大化問題: stability_score = 1.0 - min(cv, 1.0)

            # 從正例和反例的密度列表計算標準差
            # (假設response中有per_case_densities,若無則使用近似計算)
            # 近似方法: 使用positive_std和negative_std的平均作為整體穩定性指標

            if hasattr(response, 'positive_std_density') and hasattr(response, 'negative_std_density'):
                # 使用標準差的平均值作為穩定性指標
                avg_std = (response.positive_std_density + response.negative_std_density) / 2.0
                mean_density = (response.positive_avg_density + response.negative_avg_density) / 2.0

                if mean_density > 0:
                    cv = avg_std / mean_density
                else:
                    cv = 1.0  # 密度為0時,視為不穩定
            else:
                # 若無標準差數據,使用density差異作為穩定性近似
                cv = abs(response.positive_avg_density - response.negative_avg_density) / max(response.positive_avg_density, 0.01)

            stability_score = 1.0 - min(cv, 1.0)  # 限制在[0, 1]

            # 日誌記錄
            self.logger.info(
                f"Trial {trial.number}: separation={separation:.4f}, "
                f"stability={stability_score:.4f}, params={trial.params}"
            )

            # 存儲統計數據到 Trial user_attrs（供前端顯示和CSV匯出）
            trial.set_user_attr("p_value", response.p_value)
            trial.set_user_attr("cohens_d", response.cohens_d)
            trial.set_user_attr("stability_cv", response.stability_cv)
            trial.set_user_attr("positive_avg_density", response.positive_avg_density)
            trial.set_user_attr("negative_avg_density", response.negative_avg_density)
            trial.set_user_attr("separation", separation)
            trial.set_user_attr("stability_score", stability_score)

            return (separation, stability_score)

        except optuna.TrialPruned:
            # 參數不合法,重新拋出(由包裝器處理)
            raise
        except Exception:
            # 所有其他錯誤由_multi_objective_function_with_retry的重試邏輯處理
            raise

    async def optimize(
        self,
        positive_cases: List[str],
        negative_cases: List[str],
        training_window: TrainingWindowConfig
    ) -> OptimizationResult:
        """
        執行Optuna優化

        主要流程:
        1. 設置優化配置(案例列表、訓練窗口)
        2. 創建/載入Study
        3. 執行優化搜索(調用目標函數n_trials次)
        4. 收集優化結果
        5. 返回OptimizationResult

        Args:
            positive_cases: 正例案例ID列表
            negative_cases: 反例案例ID列表
            training_window: 訓練窗口配置

        Returns:
            OptimizationResult對象

        Design Note:
        - 支援並行: n_jobs > 1時多進程並行
        - 支援中斷: KeyboardInterrupt時保存當前進度
        - 斷點續跑: Study自動持久化到SQLite
        - 數據驗證: 確保案例ID真實存在(數據真實性原則)

        Raises:
            ValueError: 案例ID無效或不存在
        """
        # 步驟1: 數據驗證(數據真實性原則)
        self.logger.info("Validating case IDs...")
        try:
            # 驗證正例案例
            for case_id in positive_cases:
                if not self.case_storage.case_exists(case_id):
                    raise ValueError(f"Positive case not found: {case_id}")

            # 驗證反例案例
            for case_id in negative_cases:
                if not self.case_storage.case_exists(case_id):
                    raise ValueError(f"Negative case not found: {case_id}")

            self.logger.info(
                f"Case validation passed: {len(positive_cases)} positive, "
                f"{len(negative_cases)} negative"
            )
        except AttributeError as e:
            # Ultra Think Step 3 優化: case_storage 未實作 case_exists 應該拋出異常
            # 數據真實性原則: 必須確保案例 ID 存在，不能跳過驗證
            self.logger.error(
                f"CaseStorage.case_exists() method not implemented: {e}"
            )
            raise ValueError(
                "CaseStorage.case_exists() method not implemented. "
                "Cannot validate case IDs - this violates data authenticity principle."
            ) from e

        # 步驟2: 設置優化配置
        self.positive_cases = positive_cases
        self.negative_cases = negative_cases
        self.training_window = training_window

        # [DEBUG] 詳細日誌：記錄 Optuna 任務使用的配置，用於與單參數測試比對
        self.logger.info(
            f"[DEBUG] Optuna 優化配置:\n"
            f"  - positive_cases: {sorted(positive_cases)[:5]}... (共{len(positive_cases)}個)\n"
            f"  - negative_cases: {sorted(negative_cases)[:5]}... (共{len(negative_cases)}個)\n"
            f"  - training_window: near={training_window.lookback_bars}, "
            f"far={training_window.far_lookback_bars}, "
            f"ref={training_window.reference_point}, "
            f"mode={training_window.mode}"
        )

        # 檢測雙密度模式
        is_dual_density_mode = training_window.far_lookback_bars is not None
        if is_dual_density_mode:
            self.logger.info(
                f"DUAL-DENSITY MODE detected: "
                f"near window={training_window.lookback_bars}, "
                f"far window={training_window.far_lookback_bars}. "
                f"Optimization target: ratio_separation (near/far ratio difference)"
            )
        else:
            self.logger.info(
                f"SINGLE-DENSITY MODE: "
                f"window={training_window.lookback_bars}. "
                f"Optimization target: separation (density difference)"
            )

        # 步驟3: 創建/載入Study
        if self.study is None:
            self.create_study()

        # 步驟4: 記錄優化開始
        start_time = time.time()
        initial_trials = len(self.study.trials)

        self.logger.info(
            f"Starting optimization: {self.n_trials} new trials, "
            f"n_jobs={self.n_jobs}, existing trials={initial_trials}"
        )

        # Day 4: 初始化ProgressMonitor
        if self.enable_progress_monitor:
            self.progress_monitor = ProgressMonitor(
                total_trials=self.n_trials,
                notification_callback=self.progress_notification_callback,
                milestone_percentages=[25, 50, 75],
                log_interval=100
            )
            self.progress_monitor.start()
            self.logger.info("ProgressMonitor started")

        # 步驟5: 定義callback追蹤進度
        last_log_trial = [0]  # 使用列表保持可變性

        # 延遲導入
        import optuna

        def callback(study: "Study", trial: "optuna.trial.FrozenTrial"):
            """
            每完成一次試驗的回調

            功能:
            1. ProgressMonitor進度追蹤(Day 4)
            2. 階段性日誌記錄(每100次試驗)
            3. 手動檢查點保存(每50次試驗,通過CheckpointManager)
            4. 錯誤統計(通過ErrorHandler)
            """
            # Day 4: ProgressMonitor更新
            if self.progress_monitor:
                self.progress_monitor.on_trial_complete(study, trial)

            completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])

            # 每100次試驗記錄一次進度日誌(ProgressMonitor已處理,此處可簡化或移除)
            # ProgressMonitor會自動記錄,這裡保留作為備援
            if completed_trials % 100 == 0 and completed_trials > last_log_trial[0]:
                last_log_trial[0] = completed_trials

            # Day 3: 檢查點保存(每checkpoint_interval次試驗)
            if self.checkpoint_manager.should_save_checkpoint(completed_trials):
                try:
                    # 收集額外統計數據
                    error_stats = self.error_handler.get_error_statistics()

                    # Day 4: 添加進度統計到檢查點
                    progress_stats = None
                    if self.progress_monitor:
                        stats = self.progress_monitor.get_progress_stats(study)
                        progress_stats = {
                            'completion_percentage': stats.completion_percentage,
                            'elapsed_time': stats.elapsed_time,
                            'estimated_remaining_time': stats.estimated_remaining_time,
                            'trials_per_hour': stats.trials_per_hour,
                            'avg_trial_duration': stats.avg_trial_duration
                        }

                    additional_data = {
                        'error_statistics': error_stats,
                        'progress_statistics': progress_stats,
                        'optimization_config': {
                            'positive_cases': self.positive_cases,
                            'negative_cases': self.negative_cases,
                            'sampler_type': self.sampler_type,
                            'n_trials': self.n_trials
                        }
                    }

                    checkpoint_path = self.checkpoint_manager.save_checkpoint(
                        study=study,
                        trial_number=completed_trials,
                        additional_data=additional_data
                    )
                    self.logger.info(f"Checkpoint saved at trial {completed_trials}: {checkpoint_path}")

                except Exception as e:
                    self.logger.error(f"Failed to save checkpoint at trial {completed_trials}: {e}")

        try:
            # 步驟6: 執行優化
            # 修復async event loop問題: 使用run_in_executor在獨立線程中運行
            loop = asyncio.get_event_loop()

            # 根據use_multi_objective選擇目標函數(使用帶重試版本)
            if self.use_multi_objective:
                def sync_objective(trial: "Trial") -> Tuple[float, float]:
                    """
                    多目標同步包裝器(帶重試機制)

                    Returns:
                        (separation, stability_score) 元組
                    """
                    future = asyncio.run_coroutine_threadsafe(
                        self._multi_objective_function_with_retry(trial),
                        loop
                    )
                    return future.result()
            else:
                def sync_objective(trial: "Trial") -> float:
                    """
                    單目標同步包裝器(帶重試機制)

                    Returns:
                        separation值
                    """
                    future = asyncio.run_coroutine_threadsafe(
                        self._objective_function_with_retry(trial),
                        loop
                    )
                    return future.result()

            # 在ThreadPoolExecutor中運行Optuna優化(避免阻塞event loop)
            await loop.run_in_executor(
                self._executor,
                lambda: self.study.optimize(
                    sync_objective,
                    n_trials=self.n_trials,
                    n_jobs=self.n_jobs,
                    timeout=self.timeout,
                    callbacks=[callback],
                    show_progress_bar=True
                )
            )

        except KeyboardInterrupt:
            self.logger.warning("Optimization interrupted by user")

        # Day 4: 完成ProgressMonitor
        if self.progress_monitor:
            self.progress_monitor.finish(self.study)

        # 收集結果
        end_time = time.time()
        optimization_time = end_time - start_time

        best_trial = self.study.best_trial
        best_value = self.study.best_value
        best_params = self.study.best_params

        # 構建收斂曲線
        convergence_history = []
        current_best = float('-inf')
        for trial in self.study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                if trial.value > current_best:
                    current_best = trial.value
            convergence_history.append(current_best)

        # 日誌記錄
        self.logger.info(
            f"Optimization completed: best_value={best_value:.4f}, "
            f"best_params={best_params}, total_time={optimization_time:.1f}s"
        )

        return OptimizationResult(
            best_value=best_value,
            best_params=best_params,
            best_trial_number=best_trial.number,
            total_trials=len(self.study.trials),
            optimization_time=optimization_time,
            convergence_history=convergence_history,
            study_name=self.study_name
        )

    def get_best_trial(self) -> Dict[str, Any]:
        """
        獲取最佳試驗

        Returns:
            包含best_params, best_value, best_trial_number的字典

        Raises:
            ValueError: Study尚未創建或無完成試驗
        """
        if self.study is None:
            raise ValueError("Study not created yet. Call create_study() first.")

        if len(self.study.trials) == 0:
            raise ValueError("No trials completed yet.")

        best_trial = self.study.best_trial

        return {
            'best_params': self.study.best_params,
            'best_value': self.study.best_value,
            'best_trial_number': best_trial.number
        }

    def get_trials_dataframe(self) -> pd.DataFrame:
        """
        獲取試驗歷史DataFrame

        Returns:
            pandas.DataFrame with columns:
                - number: 試驗編號
                - value: 目標值
                - params_*: 參數列
                - state: 試驗狀態(COMPLETE/PRUNED/FAIL)
                - datetime_start: 開始時間

        Raises:
            ValueError: Study尚未創建
        """
        if self.study is None:
            raise ValueError("Study not created yet. Call create_study() first.")

        return self.study.trials_dataframe()

    def get_pareto_analysis(self, n_recommendations: int = 3) -> Dict[str, Any]:
        """
        獲取Pareto前沿分析結果(僅適用於多目標優化)

        Args:
            n_recommendations: 推薦膝點數量(default: 3)

        Returns:
            Pareto分析結果字典:
            {
                'pareto_solutions': List[ParetoSolution],
                'recommended_solutions': List[ParetoSolution],
                'summary': Dict[str, Any],
                'visualization_data': Dict[str, Any]
            }

        Raises:
            ValueError: Study尚未創建或非多目標優化
        """
        if self.study is None:
            raise ValueError("Study not created yet. Call create_study() first.")

        if not self.use_multi_objective:
            raise ValueError(
                "Pareto analysis is only available for multi-objective optimization. "
                "Set use_multi_objective=True when initializing OptunaOptimizer."
            )

        # 延遲導入避免循環依賴
        from momentum.Analysis.pareto_analyzer import ParetoAnalyzer

        analyzer = ParetoAnalyzer()
        trials_df = self.get_trials_dataframe()

        return analyzer.analyze_pareto_front(trials_df, n_recommendations)

    def __del__(self):
        """清理資源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
