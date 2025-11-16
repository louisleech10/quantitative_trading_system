"""
信號分析服務層 - Ultra Think 最終優化版本

提供信號密度分析的FastAPI服務層封裝,整合核心分析引擎。
本模塊經過 Ultra Think 三步驟優化,確保服務穩定可靠。

Ultra Think 優化記錄:
- 步驟 1: 初版代碼 - 基本服務層架構和依賴注入
- 步驟 2: 審查優化 - 完善驗證、錯誤處理、性能監控
- 步驟 3: 最終版本 - 實作所有優化項

Author: Claude (Phase 3.2)
Date: 2025-11-01
"""

import logging
import time
from typing import List, Optional, Dict, Any
from fastapi import HTTPException

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators import IndicatorEngine
from momentum.Analysis import SignalDensityAnalyzer
from api.utils.case_storage import get_case_storage_manager
from api.core.config import settings
from api.models.training_window_config import (
    SignalDensityRequest,
    SignalDensityResponse,
    TrainingWindowConfig
)


class SignalAnalysisService:
    """
    信號分析服務 (全局單例)

    提供信號密度分析的服務層接口,整合:
    - KlineStorageManager (讀取K線數據)
    - IndicatorEngine (計算指標)
    - CaseStorage (讀取案例數據)
    - SignalDensityAnalyzer (核心分析引擎)
    """

    _instance = None

    def __new__(cls):
        """單例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化服務(僅執行一次)"""
        if self._initialized:
            return

        # 依賴注入
        self.kline_storage = KlineStorageManager(cache_dir=str(settings.kline_cache_dir))
        self.indicator_engine = IndicatorEngine()
        self.case_storage = get_case_storage_manager()
        self.analyzer = SignalDensityAnalyzer(
            kline_storage=self.kline_storage,
            indicator_engine=self.indicator_engine
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("SignalAnalysisService initialized")

        self._initialized = True

    async def analyze_signal_density(
        self,
        request: SignalDensityRequest
    ) -> SignalDensityResponse:
        """
        計算信號密度分析

        主服務方法,執行完整的信號密度分析流程。

        Args:
            request: 信號密度分析請求

        Returns:
            SignalDensityResponse

        Raises:
            HTTPException:
                - 400: 參數驗證失敗
                - 404: 案例數據不存在
                - 500: 內部服務錯誤

        Example:
            >>> service = SignalAnalysisService()
            >>> request = SignalDensityRequest(
            ...     strategy_config=StrategyConfig(...),
            ...     training_window=TrainingWindowConfig(...),
            ...     positive_cases=["case1", "case2"],
            ...     negative_cases=["case3", "case4"]
            ... )
            >>> result = await service.analyze_signal_density(request)
            >>> print(result.separation)
            0.35
        """
        start_time = time.time()

        try:
            # 1. 驗證請求
            self._validate_request(request)

            # 2. 載入案例數據
            positive_cases = []
            negative_cases = []
            missing_cases = []

            for case_id in request.positive_cases:
                case = self.case_storage.get_case(case_id)
                if case is None:
                    self.logger.warning(f"正例案例不存在: {case_id}")
                    missing_cases.append(case_id)
                    continue
                positive_cases.append(case)

            for case_id in request.negative_cases:
                case = self.case_storage.get_case(case_id)
                if case is None:
                    self.logger.warning(f"反例案例不存在: {case_id}")
                    missing_cases.append(case_id)
                    continue
                negative_cases.append(case)

            # 驗證載入後的案例數量
            if len(positive_cases) < 5:
                raise ValueError(
                    f"正例案例載入不足: 需要至少5個,實際載入{len(positive_cases)}個。"
                    f"請求{len(request.positive_cases)}個,缺失{len(missing_cases)}個"
                )

            if len(negative_cases) < 5:
                raise ValueError(
                    f"反例案例載入不足: 需要至少5個,實際載入{len(negative_cases)}個"
                )

            if missing_cases:
                self.logger.warning(
                    f"共有{len(missing_cases)}個案例不存在,已跳過: {missing_cases[:5]}"
                )

            # 3. 調用分析引擎
            self.logger.info(
                f"開始信號密度分析: positive={len(positive_cases)}, "
                f"negative={len(negative_cases)}, "
                f"strategy={request.strategy_config.strategy_logic}"
            )

            result = self.analyzer.analyze_signal_density(
                positive_cases=positive_cases,
                negative_cases=negative_cases,
                strategy_config=request.strategy_config,
                window_config=request.training_window
            )

            # 記錄性能
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"信號密度分析完成: "
                f"separation={result.separation:.4f}, "
                f"p_value={result.p_value:.4f}, "
                f"耗時={elapsed_time:.2f}秒"
            )

            return result

        except ValueError as e:
            # 參數驗證失敗(400 Bad Request)
            self.logger.error(f"參數驗證失敗: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        except FileNotFoundError as e:
            # 數據不存在(404 Not Found)
            self.logger.error(f"數據不存在: {e}")
            raise HTTPException(status_code=404, detail=str(e))

        except Exception as e:
            # 內部錯誤(500 Internal Server Error)
            elapsed_time = time.time() - start_time
            self.logger.error(
                f"信號密度分析失敗: {e}, 耗時={elapsed_time:.2f}秒",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail=f"內部服務錯誤: {str(e)}"
            )

    async def preview_training_window(
        self,
        case_id: str,
        window_config: TrainingWindowConfig
    ) -> Dict[str, Any]:
        """
        預覽訓練窗口 (Debug用)

        返回訓練窗口的K線數據範圍和數量,不執行實際分析。

        Args:
            case_id: 案例ID
            window_config: 訓練窗口配置

        Returns:
            包含窗口信息的字典

        Raises:
            HTTPException: 當案例不存在或K線讀取失敗時
        """
        try:
            # 載入案例
            case = self.case_storage.get_case(case_id)
            if case is None:
                raise ValueError(f"案例不存在: {case_id}")

            # 提取訓練窗口
            klines = self.analyzer.extract_training_window(case, window_config)

            # 返回窗口信息
            return {
                "case_id": case_id,
                "symbol": case.symbol,
                "timeframe": case.timeframe,
                "reference_point": window_config.reference_point,
                "lookback_bars": window_config.lookback_bars,
                "lookforward_bars": window_config.lookforward_bars,
                "actual_bars": len(klines),
                "timestamp_range": {
                    "start": int(klines.iloc[0]["timestamp"]) if len(klines) > 0 else None,
                    "end": int(klines.iloc[-1]["timestamp"]) if len(klines) > 0 else None
                }
            }

        except ValueError as e:
            self.logger.error(f"預覽訓練窗口失敗: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        except Exception as e:
            self.logger.error(f"預覽訓練窗口失敗: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    def _validate_request(self, request: SignalDensityRequest):
        """
        驗證請求參數

        Args:
            request: 信號密度分析請求

        Raises:
            ValueError: 當參數驗證失敗時

        Note:
            驗證規則:
            - 正例數量 ≥ 10
            - 反例數量 ≥ 10
            - 案例ID格式有效
            - lookback_bars ≥ 1
            - indicator已在IndicatorEngine中註冊
        """
        # 檢查案例數量
        if len(request.positive_cases) < 10:
            raise ValueError(
                f"正例數量不足: 需要至少10個,實際{len(request.positive_cases)}個"
            )

        if len(request.negative_cases) < 10:
            raise ValueError(
                f"反例數量不足: 需要至少10個,實際{len(request.negative_cases)}個"
            )

        # 檢查案例ID格式
        for case_id in request.positive_cases + request.negative_cases:
            if not case_id or not isinstance(case_id, str):
                raise ValueError(f"無效的案例ID: {case_id}")

        # 檢查訓練窗口配置
        if request.training_window.lookback_bars < 1:
            raise ValueError("lookback_bars必須大於0")

        if request.training_window.lookforward_bars < 0:
            raise ValueError("lookforward_bars不能為負數")

        # 檢查指標是否已註冊
        available_indicators = self.indicator_engine.list_indicators()
        if request.strategy_config.indicator_type not in available_indicators:
            raise ValueError(
                f"未知的指標類型: {request.strategy_config.indicator_type}. "
                f"可用指標: {', '.join(available_indicators)}"
            )

        # 檢查策略邏輯類型
        supported_logics = ["three_line"]  # 目前只支持這一種
        if request.strategy_config.strategy_logic not in supported_logics:
            raise ValueError(
                f"不支持的策略邏輯: {request.strategy_config.strategy_logic}. "
                f"支持的邏輯: {', '.join(supported_logics)}"
            )

        self.logger.debug("請求驗證通過")
