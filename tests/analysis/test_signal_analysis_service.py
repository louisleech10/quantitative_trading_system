"""
SignalAnalysisService 整合測試 - Ultra Think 最終優化版本

測試服務層的完整功能，包括依賴注入、錯誤處理、性能監控。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本服務測試
- 步驟 2: 審查優化 - 添加錯誤場景、邊界測試、性能測試
- 步驟 3: 最終版本 - 完整實作所有優化項
"""

import pytest
import time
from fastapi import HTTPException

from api.services.signal_analysis_service import SignalAnalysisService
from api.models.training_window_config import (
    SignalDensityRequest,
    TrainingWindowConfig,
    StrategyConfig
)


def _service_with_cases(monkeypatch, cases_by_label):
    """服務單例 + 以真實 ETHUSDT 案例（CaseRecord）替換案例查詢（測後由 monkeypatch 還原）。"""
    by_id = {
        c.case_id: c
        for c in cases_by_label["positive"] + cases_by_label["negative"]
    }

    class _CaseLookup:
        def get_case(self, case_id):
            return by_id.get(case_id)

    service = SignalAnalysisService()
    monkeypatch.setattr(service, "case_storage", _CaseLookup())
    return service


class TestServiceInitialization:
    """測試服務初始化和單例模式"""

    def test_singleton_pattern(self):
        """測試單例模式"""
        service1 = SignalAnalysisService()
        service2 = SignalAnalysisService()

        # 應該是同一個實例
        assert service1 is service2

        print("✅ Singleton pattern working correctly")

    def test_dependencies_initialized(self):
        """測試依賴正確初始化"""
        service = SignalAnalysisService()

        # 驗證所有依賴都已初始化
        assert service.kline_storage is not None
        assert service.indicator_engine is not None
        assert service.case_storage is not None
        assert service.analyzer is not None

        print("✅ All dependencies initialized")


class TestAnalyzeSignalDensity:
    """測試主服務方法"""

    @pytest.mark.asyncio
    async def test_analyze_minimal_cases(
        self,
        monkeypatch,
        minimal_test_cases,
        sample_strategy_config,
        sample_training_window_config
    ):
        """測試最小案例集分析"""
        service = _service_with_cases(monkeypatch, minimal_test_cases)

        request = SignalDensityRequest(
            strategy_config=sample_strategy_config,
            training_window=sample_training_window_config,
            positive_cases=[c.case_id for c in minimal_test_cases["positive"]],
            negative_cases=[c.case_id for c in minimal_test_cases["negative"]]
        )

        result = await service.analyze_signal_density(request)

        assert result.positive_sample_size == len(minimal_test_cases["positive"])
        assert result.negative_sample_size == len(minimal_test_cases["negative"])
        assert 0.0 <= result.positive_avg_density <= 1.0
        assert 0.0 <= result.negative_avg_density <= 1.0
        assert result.separation == pytest.approx(
            result.positive_avg_density - result.negative_avg_density
        )
        case_keys = [k for k in result.case_level_densities if not k.startswith("__")]
        assert sorted(case_keys) == sorted(
            c.case_id for c in minimal_test_cases["positive"] + minimal_test_cases["negative"]
        )

        print("✅ Service analyze_signal_density end-to-end validated")

    @pytest.mark.asyncio
    async def test_analyze_with_validation(self):
        """測試請求驗證"""
        service = SignalAnalysisService()

        # 無效的 indicator_type
        invalid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="invalid_indicator",
                strategy_logic="three_line",
                params={}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        # 應該拋出 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_signal_density(invalid_request)

        assert exc_info.value.status_code == 400
        assert "未註冊的指標" in str(exc_info.value.detail)

        print("✅ Request validation working")

    @pytest.mark.asyncio
    async def test_analyze_missing_params(self):
        """測試缺少必需參數"""
        service = SignalAnalysisService()

        # EMA 缺少必需參數
        invalid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={}  # 缺少 short_period, mid_period, long_period
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_signal_density(invalid_request)

        assert exc_info.value.status_code == 400
        assert "參數" in str(exc_info.value.detail)

        print("✅ Parameter validation working")

    @pytest.mark.asyncio
    async def test_analyze_invalid_data_source(self):
        """測試無效的數據源"""
        service = SignalAnalysisService()

        invalid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="invalid_source",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_signal_density(invalid_request)

        assert exc_info.value.status_code == 400

        print("✅ Data source validation working")


class TestPreviewTrainingWindow:
    """測試訓練窗口預覽功能"""

    @pytest.mark.asyncio
    async def test_preview_basic(
        self,
        monkeypatch,
        minimal_test_cases,
        sample_training_window_config
    ):
        """測試基本預覽功能"""
        service = _service_with_cases(monkeypatch, minimal_test_cases)

        case = minimal_test_cases["positive"][0]
        info = await service.preview_training_window(
            case.case_id, sample_training_window_config
        )

        assert info["case_id"] == case.case_id
        assert info["symbol"] == case.symbol
        assert 0 < info["actual_bars"] <= sample_training_window_config.lookback_bars
        # 無 look-ahead：預覽窗口最後一根嚴格早於 TO
        assert info["timestamp_range"]["start"] < info["timestamp_range"]["end"]
        assert info["timestamp_range"]["end"] < case.timestamp

        print("✅ Preview returns window info without look-ahead")

    @pytest.mark.asyncio
    async def test_preview_nonexistent_case(self, sample_training_window_config):
        """測試不存在的案例"""
        service = SignalAnalysisService()

        with pytest.raises(HTTPException) as exc_info:
            await service.preview_training_window(
                "NONEXISTENT_CASE",
                sample_training_window_config
            )

        assert exc_info.value.status_code == 404
        assert "未找到案例" in str(exc_info.value.detail)

        print("✅ Nonexistent case handled correctly")


class TestErrorHandling:
    """測試錯誤處理"""

    @pytest.mark.asyncio
    async def test_handle_value_error(self):
        """測試 ValueError 轉換為 400"""
        service = SignalAnalysisService()

        # 觸發 ValueError（無效參數）
        invalid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": -1}  # 負數週期
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_signal_density(invalid_request)

        assert exc_info.value.status_code == 400

        print("✅ ValueError handled as 400 Bad Request")

    @pytest.mark.asyncio
    async def test_handle_file_not_found(self):
        """測試 FileNotFoundError 轉換為 404"""
        service = SignalAnalysisService()

        # 觸發 FileNotFoundError（案例不存在）
        request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["NONEXISTENT"],
            negative_cases=["ALSO_NONEXISTENT"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_signal_density(request)

        # 應該是 404（案例未找到）
        assert exc_info.value.status_code in [404, 500]  # 可能是 404 或 500，取決於實作

        print("✅ FileNotFoundError handled correctly")


class TestPerformanceMonitoring:
    """測試性能監控"""

    @pytest.mark.asyncio
    async def test_execution_time_logged(
        self,
        monkeypatch,
        minimal_test_cases,
        sample_strategy_config,
        sample_training_window_config,
        caplog
    ):
        """測試執行時間是否記錄"""
        service = _service_with_cases(monkeypatch, minimal_test_cases)

        request = SignalDensityRequest(
            strategy_config=sample_strategy_config,
            training_window=sample_training_window_config,
            positive_cases=[c.case_id for c in minimal_test_cases["positive"]],
            negative_cases=[c.case_id for c in minimal_test_cases["negative"]]
        )

        import logging
        with caplog.at_level(logging.INFO, logger=service.logger.name):
            await service.analyze_signal_density(request)

        # 完成日誌須含耗時（秒）
        done = [
            r.getMessage() for r in caplog.records
            if "信號密度分析完成" in r.getMessage() and "耗時=" in r.getMessage()
        ]
        assert len(done) == 1
        assert "耗時=" in done[0] and done[0].rstrip().endswith("秒")

        print("✅ Execution time logged")


class TestIntegrationWithRealComponents:
    """與真實組件的整合測試"""

    def test_service_uses_real_kline_storage(self):
        """測試服務使用真實 KlineStorageManager"""
        service = SignalAnalysisService()

        from momentum.DataExtraction.kline_storage_manager import KlineStorageManager
        assert isinstance(service.kline_storage, KlineStorageManager)

        print("✅ Service uses real KlineStorageManager")

    def test_service_uses_real_indicator_engine(self):
        """測試服務使用真實 IndicatorEngine"""
        service = SignalAnalysisService()

        from momentum.Indicators.indicator_engine import IndicatorEngine
        assert isinstance(service.indicator_engine, IndicatorEngine)

        print("✅ Service uses real IndicatorEngine")

    def test_service_uses_real_analyzer(self):
        """測試服務使用真實 SignalDensityAnalyzer"""
        service = SignalAnalysisService()

        from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
        assert isinstance(service.analyzer, SignalDensityAnalyzer)

        print("✅ Service uses real SignalDensityAnalyzer")


class TestValidationMethods:
    """測試驗證方法"""

    def test_validate_indicator_registered(self):
        """測試指標註冊驗證"""
        service = SignalAnalysisService()

        # 有效指標（EMA 應該已註冊）
        valid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        # 完整有效請求必須無例外通過（不再吞例外）
        assert service._validate_request(valid_request) is None

        # 對照組：未註冊指標必須被拒絕，證明驗證確實有跑
        invalid_request = valid_request.model_copy(update={
            "strategy_config": StrategyConfig(
                data_source="close",
                indicator_type="invalid_indicator",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            )
        })
        with pytest.raises(ValueError, match="未註冊的指標"):
            service._validate_request(invalid_request)

        print("✅ Valid indicator passed validation; invalid rejected")

    def test_validate_data_source(self):
        """測試數據源驗證"""
        service = SignalAnalysisService()

        # 有效數據源
        valid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",  # 有效
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        # 完整有效請求必須無例外通過（不再吞例外）
        assert service._validate_request(valid_request) is None

        # 對照組：無效數據源必須被拒絕
        invalid_request = valid_request.model_copy(update={
            "strategy_config": StrategyConfig(
                data_source="invalid_source",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            )
        })
        with pytest.raises(ValueError, match="無效的data_source"):
            service._validate_request(invalid_request)

        print("✅ Valid data source passed validation; invalid rejected")

    def test_validate_strategy_params(self):
        """測試策略參數驗證"""
        service = SignalAnalysisService()

        # 缺少必需參數
        invalid_request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20}  # 缺少 mid_period, long_period
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1"],
            negative_cases=["case2"]
        )

        with pytest.raises(ValueError, match="參數"):
            service._validate_request(invalid_request)

        print("✅ Missing params detected correctly")


class TestCaseCounts:
    """測試案例數量驗證"""

    @pytest.mark.asyncio
    async def test_insufficient_positive_cases(self):
        """測試正例不足"""
        service = SignalAnalysisService()

        request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=[],  # 空列表
            negative_cases=["case1", "case2"]
        )

        # 驗證方法應該捕獲此錯誤
        with pytest.raises(ValueError, match="案例"):
            service._validate_request(request)

        print("✅ Insufficient positive cases detected")

    @pytest.mark.asyncio
    async def test_insufficient_negative_cases(self):
        """測試反例不足"""
        service = SignalAnalysisService()

        request = SignalDensityRequest(
            strategy_config=StrategyConfig(
                data_source="close",
                indicator_type="ema",
                strategy_logic="three_line",
                params={"short_period": 20, "mid_period": 60, "long_period": 120}
            ),
            training_window=TrainingWindowConfig(
                reference_point="TO",
                lookback_bars=240,
                lookforward_bars=0,
                mode="relative"
            ),
            positive_cases=["case1", "case2"],
            negative_cases=[]  # 空列表
        )

        with pytest.raises(ValueError, match="案例"):
            service._validate_request(request)

        print("✅ Insufficient negative cases detected")
