"""
Optuna參數優化引擎 - Ultra Think 最終優化版本

核心功能:
1. 自動搜索最佳EMA策略參數組合
2. 優化目標: 最大化正反例信號密度差異(separation)
3. 支援多種優化器(TPE/CmaEs/Random/GP/NSGA-II)
4. 多目標優化(separation + stability,Pareto前沿)
5. 斷點續跑機制(SQLite持久化)
6. 並行多進程優化

Ultra Think 記錄:
- Day 1 步驟1: 初版代碼 - 核心優化邏輯和目標函數(TPE/CmaEs/Random)
- Day 1 步驟2: 審查優化 - 發現6個優化點(async/event loop、數據驗證、錯誤處理等)
- Day 1 步驟3: 最終優化 - 修復所有P0/P1問題,添加參數範圍配置和詳細日誌
- Day 2 步驟1: 進階優化器 - 新增GP/NSGA-II兩種Sampler
- Day 2 步驟2: 多目標優化 - 實作multi_objective_function(separation + stability)
- Day 2 步驟3: Pareto分析 - 整合ParetoAnalyzer,提供get_pareto_analysis()方法

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

Author: Claude (Phase 3.5)
Date: 2025-11-02
"""

import logging
import optuna
from optuna import Trial, Study
from optuna.samplers import TPESampler, CmaEsSampler, RandomSampler, GPSampler, NSGAIISampler
from optuna.pruners import MedianPruner, PercentilePruner, NopPruner
from typing import Dict, Any, Optional, List, Callable, Tuple
import asyncio
from dataclasses import dataclass, field
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from api.models.training_window_config import (
    SignalDensityRequest,
    SignalDensityResponse,
    TrainingWindowConfig,
    StrategyConfig
)
from api.models.strategy_test_models import ParameterRange
from api.services.signal_analysis_service import SignalAnalysisService
from api.services.case_storage import CaseStorage


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
        use_multi_objective: bool = False
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

        # 依賴服務
        self.signal_service = SignalAnalysisService()
        self.case_storage = CaseStorage()

        # 日誌
        self.logger = logging.getLogger(__name__)

        # Study對象(延遲初始化)
        self.study: Optional[Study] = None

        # 優化配置(在optimize()時設置)
        self.positive_cases: List[str] = []
        self.negative_cases: List[str] = []
        self.training_window: Optional[TrainingWindowConfig] = None

        # ThreadPoolExecutor for async compatibility
        self._executor = ThreadPoolExecutor(max_workers=1)

        self.logger.info(
            f"OptunaOptimizer initialized: study_name={study_name}, "
            f"sampler={sampler_type}, n_trials={n_trials}, "
            f"param_ranges={self.parameter_ranges}"
        )

    def _create_sampler(self) -> optuna.samplers.BaseSampler:
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

    def _create_pruner(self) -> optuna.pruners.BasePruner:
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

    def create_study(self) -> Study:
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

    async def _objective_function(self, trial: Trial) -> float:
        """
        Optuna目標函數

        核心算法:
        1. 參數採樣: 從搜索空間採樣參數組合
        2. 參數驗證: 確保參數約束(如short < mid < long)
        3. 調用信號密度分析: 計算正反例的平均信號密度
        4. 計算目標值: separation = positive_avg - negative_avg
        5. 返回目標值: Optuna將最大化此值

        Args:
            trial: Optuna Trial對象

        Returns:
            separation(密度差異)

        Raises:
            optuna.TrialPruned: 參數不合法時剪枝

        Design Note:
        - 優化目標: 最大化正反例信號密度差異(而非Win Rate)
        - 參數約束: 三線排列必須 short < mid < long
        - 數據源: 從DataSourceEnum中選擇,無硬編碼
        """
        try:
            # 步驟1: 參數採樣(使用配置的範圍,無硬編碼)
            data_source = trial.suggest_categorical(
                'data_source',
                self.parameter_ranges.data_sources
            )

            strategy_logic = trial.suggest_categorical(
                'strategy_logic',
                self.parameter_ranges.strategy_logics
            )

            ema_short = trial.suggest_int(
                'ema_short',
                self.parameter_ranges.ema_short_range[0],
                self.parameter_ranges.ema_short_range[1]
            )
            ema_long = trial.suggest_int(
                'ema_long',
                self.parameter_ranges.ema_long_range[0],
                self.parameter_ranges.ema_long_range[1]
            )

            # 三線排列需要額外採樣ema_mid
            if strategy_logic == 'three_line':
                ema_mid = trial.suggest_int(
                    'ema_mid',
                    self.parameter_ranges.ema_mid_range[0],
                    self.parameter_ranges.ema_mid_range[1]
                )
            else:
                ema_mid = None

            # 步驟2: 參數驗證
            if strategy_logic == 'three_line':
                if not (ema_short < ema_mid < ema_long):
                    self.logger.debug(
                        f"Trial {trial.number} pruned: "
                        f"Invalid EMA order: {ema_short} < {ema_mid} < {ema_long}"
                    )
                    raise optuna.TrialPruned()
            else:
                if not (ema_short < ema_long):
                    self.logger.debug(
                        f"Trial {trial.number} pruned: "
                        f"Invalid EMA order: {ema_short} < {ema_long}"
                    )
                    raise optuna.TrialPruned()

            # 步驟3: 組裝策略配置
            strategy_config = StrategyConfig(
                data_source=data_source,
                indicator_type="ema",
                strategy_logic=strategy_logic,
                params={
                    "ema_short": ema_short,
                    "ema_mid": ema_mid,
                    "ema_long": ema_long
                }
            )

            # 步驟4: 調用信號密度分析
            request = SignalDensityRequest(
                strategy_config=strategy_config,
                training_window=self.training_window,
                positive_cases=self.positive_cases,
                negative_cases=self.negative_cases
            )

            response: SignalDensityResponse = await self.signal_service.analyze_signal_density(request)

            # 步驟5: 計算目標值
            separation = response.positive_avg_density - response.negative_avg_density

            # 日誌記錄
            self.logger.info(
                f"Trial {trial.number}: separation={separation:.4f}, "
                f"params={trial.params}"
            )

            return separation

        except optuna.TrialPruned:
            # 參數不合法,重新拋出
            raise
        except (ConnectionError, TimeoutError) as e:
            # 可重試錯誤: 網絡相關錯誤
            self.logger.warning(
                f"Trial {trial.number} encountered retryable error: {e}. "
                f"Returning poor value (-500.0)"
            )
            return -500.0  # 較差值,但允許後續試驗繼續
        except (ValueError, KeyError, TypeError) as e:
            # 不可重試錯誤: 數據/參數問題
            self.logger.error(
                f"Trial {trial.number} encountered non-retryable error: {e}",
                exc_info=True
            )
            raise optuna.TrialPruned()  # 剪枝此試驗
        except Exception as e:
            # 未知錯誤: 記錄詳細日誌
            self.logger.error(
                f"Trial {trial.number} failed with unknown error: {e}",
                exc_info=True
            )
            return -999.0  # 極差值,確保不會被選為最佳

    async def _multi_objective_function(self, trial: Trial) -> Tuple[float, float]:
        """
        多目標優化函數

        同時優化兩個目標:
        1. separation: 最大化正反例信號密度差異
        2. stability_score: 最大化穩定性(最小化變異係數)

        Args:
            trial: Optuna Trial對象

        Returns:
            (separation, stability_score) 元組

        Raises:
            optuna.TrialPruned: 參數不合法時剪枝

        Design Note:
        - 穩定性計算: stability_score = 1.0 - min(cv, 1.0)
        - cv = std_separation / mean_separation (變異係數)
        - Pareto前沿: NSGA-II會返回多個非支配解
        """
        try:
            # 步驟1-4: 與單目標相同,獲取separation
            # (復用參數採樣、驗證、調用分析邏輯)
            data_source = trial.suggest_categorical(
                'data_source',
                self.parameter_ranges.data_sources
            )

            strategy_logic = trial.suggest_categorical(
                'strategy_logic',
                self.parameter_ranges.strategy_logics
            )

            ema_short = trial.suggest_int(
                'ema_short',
                self.parameter_ranges.ema_short_range[0],
                self.parameter_ranges.ema_short_range[1]
            )
            ema_long = trial.suggest_int(
                'ema_long',
                self.parameter_ranges.ema_long_range[0],
                self.parameter_ranges.ema_long_range[1]
            )

            if strategy_logic == 'three_line':
                ema_mid = trial.suggest_int(
                    'ema_mid',
                    self.parameter_ranges.ema_mid_range[0],
                    self.parameter_ranges.ema_mid_range[1]
                )
            else:
                ema_mid = None

            # 參數驗證
            if strategy_logic == 'three_line':
                if not (ema_short < ema_mid < ema_long):
                    self.logger.debug(
                        f"Trial {trial.number} pruned: "
                        f"Invalid EMA order: {ema_short} < {ema_mid} < {ema_long}"
                    )
                    raise optuna.TrialPruned()
            else:
                if not (ema_short < ema_long):
                    self.logger.debug(
                        f"Trial {trial.number} pruned: "
                        f"Invalid EMA order: {ema_short} < {ema_long}"
                    )
                    raise optuna.TrialPruned()

            # 組裝策略配置
            strategy_config = StrategyConfig(
                data_source=data_source,
                indicator_type="ema",
                strategy_logic=strategy_logic,
                params={
                    "ema_short": ema_short,
                    "ema_mid": ema_mid,
                    "ema_long": ema_long
                }
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

            return (separation, stability_score)

        except optuna.TrialPruned:
            raise
        except (ConnectionError, TimeoutError) as e:
            self.logger.warning(
                f"Trial {trial.number} encountered retryable error: {e}. "
                f"Returning poor values (-500.0, 0.0)"
            )
            return (-500.0, 0.0)
        except (ValueError, KeyError, TypeError) as e:
            self.logger.error(
                f"Trial {trial.number} encountered non-retryable error: {e}",
                exc_info=True
            )
            raise optuna.TrialPruned()
        except Exception as e:
            self.logger.error(
                f"Trial {trial.number} failed with unknown error: {e}",
                exc_info=True
            )
            return (-999.0, 0.0)

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
        except AttributeError:
            # case_storage未實作case_exists,跳過驗證
            self.logger.warning(
                "Case validation skipped: CaseStorage.case_exists() not implemented"
            )

        # 步驟2: 設置優化配置
        self.positive_cases = positive_cases
        self.negative_cases = negative_cases
        self.training_window = training_window

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

        # 步驟5: 定義callback追蹤進度
        last_log_trial = [0]  # 使用列表保持可變性

        def callback(study: Study, trial: optuna.trial.FrozenTrial):
            """每完成一次試驗的回調,用於階段性日誌"""
            completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])

            # 每100次試驗記錄一次
            if completed_trials % 100 == 0 and completed_trials > last_log_trial[0]:
                self.logger.info(
                    f"Progress: {completed_trials} trials completed, "
                    f"current best: {study.best_value:.4f}"
                )
                last_log_trial[0] = completed_trials

        try:
            # 步驟6: 執行優化
            # 修復async event loop問題: 使用run_in_executor在獨立線程中運行
            loop = asyncio.get_event_loop()

            # 根據use_multi_objective選擇目標函數
            if self.use_multi_objective:
                def sync_objective(trial: Trial) -> Tuple[float, float]:
                    """
                    多目標同步包裝器

                    Returns:
                        (separation, stability_score) 元組
                    """
                    future = asyncio.run_coroutine_threadsafe(
                        self._multi_objective_function(trial),
                        loop
                    )
                    return future.result()
            else:
                def sync_objective(trial: Trial) -> float:
                    """
                    單目標同步包裝器

                    Returns:
                        separation值
                    """
                    future = asyncio.run_coroutine_threadsafe(
                        self._objective_function(trial),
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
