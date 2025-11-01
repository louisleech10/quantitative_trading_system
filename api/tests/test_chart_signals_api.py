"""
test_chart_signals_api.py - Chart Signals API 整合測試

Phase 3.3+3.4 - Task D3: API 整合測試

測試範圍:
- POST /api/chart-signals/signals 端點
- POST /api/chart-signals/validate-strategy 端點
- 請求驗證邏輯
- 響應格式驗證
- 錯誤處理

Ultra Think 記錄:
- 步驟 1: 初版代碼 (當前)
- 步驟 2: 審查優化 (待執行)
- 步驟 3: 最終優化 (待執行)
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


# ========== 測試數據 ==========

VALID_STRATEGY_CONFIG = {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_time": int((datetime.now() - timedelta(days=30)).timestamp()),
    "end_time": int(datetime.now().timestamp()),
    "strategy_config": {
        "data_source": "close",
        "indicator_type": "ema",
        "strategy_logic": "three_line",
        "ema_parameters": {
            "ema_short": 7,
            "ema_mid": 18,
            "ema_long": 35,
        },
        "training_window": {
            "reference_point": "TO",
            "lookback_bars": 24,
            "lookforward_bars": 0,
            "mode": "relative",
        },
        "test_mode": "single",
    },
}

INVALID_STRATEGY_CONFIG_OVERLAP = {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_time": int((datetime.now() - timedelta(days=30)).timestamp()),
    "end_time": int(datetime.now().timestamp()),
    "strategy_config": {
        "data_source": "close",
        "indicator_type": "ema",
        "strategy_logic": "three_line",
        "ema_parameters": {
            "ema_short": 35,  # 錯誤: short > mid
            "ema_mid": 18,
            "ema_long": 7,  # 錯誤: long < mid
        },
        "training_window": {
            "reference_point": "TO",
            "lookback_bars": 24,
            "lookforward_bars": 0,
            "mode": "relative",
        },
        "test_mode": "single",
    },
}


# ========== API 測試 ==========

@pytest.mark.asyncio
class TestChartSignalsAPI:
    """Chart Signals API 測試"""

    def test_calculate_signals_valid_request(self, client: TestClient):
        """測試: 有效請求應該返回信號數據"""
        response = client.post(
            "/api/chart-signals/signals",
            json=VALID_STRATEGY_CONFIG,
        )

        # 驗證狀態碼
        assert response.status_code == 200

        # 驗證響應格式
        data = response.json()
        assert "success" in data
        assert "symbol" in data
        assert "timeframe" in data
        assert "signal_points" in data
        assert "total_signals" in data
        assert "sampled" in data
        assert "metadata" in data

        # 驗證數據類型
        assert isinstance(data["success"], bool)
        assert isinstance(data["signal_points"], list)
        assert isinstance(data["total_signals"], int)
        assert isinstance(data["sampled"], bool)
        assert isinstance(data["metadata"], dict)

        # 驗證 metadata 內容
        assert "total_klines" in data["metadata"]
        assert "calculation_time_ms" in data["metadata"]
        assert "strategy_config" in data["metadata"]

    def test_calculate_signals_invalid_ema_parameters(self, client: TestClient):
        """測試: 無效的 EMA 參數應該返回錯誤"""
        response = client.post(
            "/api/chart-signals/signals",
            json=INVALID_STRATEGY_CONFIG_OVERLAP,
        )

        # 應該返回 422 (驗證錯誤)
        assert response.status_code == 422

        # 驗證錯誤訊息
        data = response.json()
        assert "detail" in data

    def test_calculate_signals_missing_fields(self, client: TestClient):
        """測試: 缺少必填欄位應該返回錯誤"""
        incomplete_config = {
            "symbol": "BTCUSDT",
            # 缺少 timeframe, start_time, end_time, strategy_config
        }

        response = client.post(
            "/api/chart-signals/signals",
            json=incomplete_config,
        )

        # 應該返回 422 (驗證錯誤)
        assert response.status_code == 422

    def test_calculate_signals_invalid_symbol(self, client: TestClient):
        """測試: 無效的交易對應該返回錯誤"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["symbol"] = "INVALID_SYMBOL_XYZ"

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 可能返回 404 (數據不存在) 或 400 (無效請求)
        assert response.status_code in [400, 404]

    def test_calculate_signals_invalid_timeframe(self, client: TestClient):
        """測試: 無效的時間框架應該返回錯誤"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["timeframe"] = "invalid_timeframe"

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 應該返回 400 或 422
        assert response.status_code in [400, 422]

    def test_calculate_signals_invalid_time_range(self, client: TestClient):
        """測試: 無效的時間範圍應該返回錯誤"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["start_time"] = int(datetime.now().timestamp())
        invalid_config["end_time"] = int(
            (datetime.now() - timedelta(days=30)).timestamp()
        )  # end < start

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 應該返回 400 或 422
        assert response.status_code in [400, 422]

    def test_validate_strategy_valid_config(self, client: TestClient):
        """測試: 驗證有效的策略配置"""
        validation_request = {
            "strategy_config": VALID_STRATEGY_CONFIG["strategy_config"]
        }

        response = client.post(
            "/api/chart-signals/validate-strategy",
            json=validation_request,
        )

        # 驗證狀態碼
        assert response.status_code == 200

        # 驗證響應格式
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data

        # 應該是有效的
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_strategy_invalid_ema_overlap(self, client: TestClient):
        """測試: 驗證 EMA 參數重疊錯誤"""
        validation_request = {
            "strategy_config": INVALID_STRATEGY_CONFIG_OVERLAP["strategy_config"]
        }

        response = client.post(
            "/api/chart-signals/validate-strategy",
            json=validation_request,
        )

        # 驗證狀態碼
        assert response.status_code == 200

        # 驗證響應格式
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data

        # 應該是無效的
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_strategy_missing_required_fields(self, client: TestClient):
        """測試: 驗證缺少必填欄位"""
        incomplete_config = {
            "strategy_config": {
                "data_source": "close",
                "indicator_type": "ema",
                # 缺少其他必填欄位
            }
        }

        response = client.post(
            "/api/chart-signals/validate-strategy",
            json=incomplete_config,
        )

        # 應該返回 422 (驗證錯誤)
        assert response.status_code == 422

    def test_signal_points_structure(self, client: TestClient):
        """測試: 信號點數據結構"""
        response = client.post(
            "/api/chart-signals/signals",
            json=VALID_STRATEGY_CONFIG,
        )

        if response.status_code == 200:
            data = response.json()
            signal_points = data["signal_points"]

            if len(signal_points) > 0:
                # 驗證第一個信號點的結構
                first_signal = signal_points[0]
                assert "timestamp" in first_signal
                assert "indicator_values" in first_signal
                assert isinstance(first_signal["timestamp"], int)
                assert isinstance(first_signal["indicator_values"], dict)

                # 驗證指標數值
                indicator_values = first_signal["indicator_values"]
                assert "ema_short" in indicator_values
                assert "ema_mid" in indicator_values
                assert "ema_long" in indicator_values

                # 驗證數值類型
                assert isinstance(indicator_values["ema_short"], (int, float))
                assert isinstance(indicator_values["ema_mid"], (int, float))
                assert isinstance(indicator_values["ema_long"], (int, float))

    def test_signal_sampling_limit(self, client: TestClient):
        """測試: 信號採樣限制 (最多 500 個)"""
        # 使用較大的時間範圍以生成更多信號
        large_range_config = VALID_STRATEGY_CONFIG.copy()
        large_range_config["start_time"] = int(
            (datetime.now() - timedelta(days=365)).timestamp()
        )  # 1 年

        response = client.post(
            "/api/chart-signals/signals",
            json=large_range_config,
        )

        if response.status_code == 200:
            data = response.json()
            signal_points = data["signal_points"]

            # 驗證信號數量不超過 500
            assert len(signal_points) <= 500

            # 如果超過 500 個原始信號, sampled 應該為 True
            if data["total_signals"] > 500:
                assert data["sampled"] is True

    def test_calculation_time_performance(self, client: TestClient):
        """測試: 計算時間性能"""
        response = client.post(
            "/api/chart-signals/signals",
            json=VALID_STRATEGY_CONFIG,
        )

        if response.status_code == 200:
            data = response.json()
            calculation_time_ms = data["metadata"]["calculation_time_ms"]

            # 驗證計算時間在合理範圍內 (< 5000ms)
            assert calculation_time_ms < 5000

            # 記錄性能數據
            print(f"\n計算時間: {calculation_time_ms:.2f} ms")
            print(f"信號數量: {data['total_signals']}")
            print(f"K線數量: {data['metadata']['total_klines']}")


# ========== Fixtures ==========

@pytest.fixture
def client():
    """創建測試客戶端"""
    from api.main import app

    with TestClient(app) as client:
        yield client


# ========== 性能測試 ==========

@pytest.mark.performance
class TestChartSignalsPerformance:
    """性能測試套件"""

    def test_large_dataset_performance(self, client: TestClient):
        """測試: 大數據集性能 (1000 根 K 線)"""
        large_config = VALID_STRATEGY_CONFIG.copy()
        large_config["start_time"] = int(
            (datetime.now() - timedelta(days=42)).timestamp()
        )  # ~1000 hours

        response = client.post(
            "/api/chart-signals/signals",
            json=large_config,
        )

        if response.status_code == 200:
            data = response.json()
            calculation_time_ms = data["metadata"]["calculation_time_ms"]

            # 大數據集應該在 2 秒內完成
            assert calculation_time_ms < 2000

            print(f"\n大數據集測試:")
            print(f"  K線數量: {data['metadata']['total_klines']}")
            print(f"  信號數量: {data['total_signals']}")
            print(f"  計算時間: {calculation_time_ms:.2f} ms")
            print(
                f"  吞吐量: {data['metadata']['total_klines'] / (calculation_time_ms / 1000):.2f} klines/sec"
            )

    def test_concurrent_requests(self, client: TestClient):
        """測試: 並發請求處理"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def make_request():
            return client.post(
                "/api/chart-signals/signals",
                json=VALID_STRATEGY_CONFIG,
            )

        # 發送 5 個並發請求
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # 驗證所有請求都成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 5

        print(f"\n並發測試: {success_count}/5 請求成功")


# ========== 錯誤處理測試 ==========

@pytest.mark.error_handling
class TestChartSignalsErrorHandling:
    """錯誤處理測試套件"""

    def test_malformed_json(self, client: TestClient):
        """測試: 格式錯誤的 JSON"""
        response = client.post(
            "/api/chart-signals/signals",
            data="{ invalid json }",
            headers={"Content-Type": "application/json"},
        )

        # 應該返回 422
        assert response.status_code == 422

    def test_invalid_data_types(self, client: TestClient):
        """測試: 無效的數據類型"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["strategy_config"]["ema_parameters"]["ema_short"] = (
            "not_a_number"
        )

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 應該返回 422
        assert response.status_code == 422

    def test_negative_ema_values(self, client: TestClient):
        """測試: 負數 EMA 值"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["strategy_config"]["ema_parameters"]["ema_short"] = -5

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 應該返回 422
        assert response.status_code == 422

    def test_zero_lookback_bars(self, client: TestClient):
        """測試: lookback_bars 為 0"""
        invalid_config = VALID_STRATEGY_CONFIG.copy()
        invalid_config["strategy_config"]["training_window"]["lookback_bars"] = 0

        response = client.post(
            "/api/chart-signals/signals",
            json=invalid_config,
        )

        # 可能返回 400 或 422
        assert response.status_code in [400, 422]
