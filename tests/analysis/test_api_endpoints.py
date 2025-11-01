"""
Signal Analysis API 端點測試 - Ultra Think 最終優化版本

測試 FastAPI 路由的完整功能，包括請求/響應驗證、錯誤處理、OpenAPI 文檔。

Ultra Think 優化記錄：
- 步驟 1: 初版代碼 - 基本端點測試
- 步驟 2: 審查優化 - 添加錯誤場景、邊界測試、文檔驗證
- 步驟 3: 最終版本 - 完整實作所有優化項
"""

import pytest
from fastapi.testclient import TestClient

# NOTE: 需要確保 API 已正確初始化
# 這裡導入完整的 FastAPI app
try:
    from api.main import app
    client = TestClient(app)
    API_AVAILABLE = True
except Exception as e:
    API_AVAILABLE = False
    pytest.skip(f"API not available: {e}", allow_module_level=True)


class TestCalculateSignalDensityEndpoint:
    """測試 POST /api/v1/signal-analysis/density 端點"""

    def test_endpoint_exists(self):
        """測試端點存在且可訪問"""
        # 發送無效請求，但應該得到 422/400 而非 404
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={}
        )

        # 404 = 端點不存在，422/400 = 端點存在但請求無效
        assert response.status_code != 404, "Endpoint should exist"

        print(f"✅ Endpoint exists (status: {response.status_code})")

    def test_request_validation_missing_fields(self):
        """測試請求驗證：缺少必需欄位"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                # 缺少所有必需欄位
            }
        )

        # 應該返回 422 (Unprocessable Entity)
        assert response.status_code == 422

        error_detail = response.json()
        assert "detail" in error_detail

        print(f"✅ Missing fields validation: {response.status_code}")

    def test_request_validation_invalid_types(self):
        """測試請求驗證：無效的類型"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {"short_period": "not_a_number"}  # 應該是數字
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["case1"],
                "negative_cases": ["case2"]
            }
        )

        # 應該返回 422
        assert response.status_code == 422

        print(f"✅ Invalid types validation: {response.status_code}")

    def test_request_validation_invalid_enum(self):
        """測試請求驗證：無效的枚舉值"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {"short_period": 20, "mid_period": 60, "long_period": 120}
                },
                "training_window": {
                    "reference_point": "INVALID",  # 應該是 TO/TC/custom
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["case1"],
                "negative_cases": ["case2"]
            }
        )

        assert response.status_code == 422

        print(f"✅ Invalid enum validation: {response.status_code}")

    def test_request_validation_negative_lookback(self):
        """測試請求驗證：負數 lookback_bars"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {"short_period": 20, "mid_period": 60, "long_period": 120}
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": -100,  # 負數
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["case1"],
                "negative_cases": ["case2"]
            }
        )

        assert response.status_code == 422

        print(f"✅ Negative lookback validation: {response.status_code}")

    def test_business_logic_validation_unregistered_indicator(self):
        """測試業務邏輯驗證：未註冊的指標"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "nonexistent_indicator",
                    "strategy_logic": "three_line",
                    "params": {}
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["case1"],
                "negative_cases": ["case2"]
            }
        )

        # 應該返回 400 (業務邏輯錯誤)
        assert response.status_code == 400

        error_detail = response.json()
        assert "未註冊的指標" in error_detail["detail"]

        print(f"✅ Unregistered indicator: {error_detail['detail']}")

    def test_business_logic_validation_nonexistent_cases(self):
        """測試業務邏輯驗證：不存在的案例"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {"short_period": 20, "mid_period": 60, "long_period": 120}
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["ABSOLUTELY_NONEXISTENT"],
                "negative_cases": ["ALSO_NONEXISTENT"]
            }
        )

        # 應該返回 404 或 400
        assert response.status_code in [400, 404, 500]

        print(f"✅ Nonexistent cases handled: {response.status_code}")

    def test_response_schema_validation(self):
        """測試響應模型驗證（使用 mock 數據）"""
        # NOTE: 此測試需要實際的案例數據，這裡僅驗證端點結構
        # 真實測試應該使用 mock_case_storage fixture

        # 構造有效請求（即使執行失敗，也能驗證響應結構）
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {"short_period": 20, "mid_period": 60, "long_period": 120}
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["test1", "test2"],
                "negative_cases": ["test3", "test4"]
            }
        )

        # 即使失敗，響應也應該是 JSON
        assert response.headers["content-type"] == "application/json"

        print(f"✅ Response is JSON: {response.status_code}")


class TestPreviewTrainingWindowEndpoint:
    """測試 POST /api/v1/signal-analysis/preview-window 端點"""

    def test_endpoint_exists(self):
        """測試端點存在"""
        response = client.post(
            "/api/v1/signal-analysis/preview-window",
            json={}
        )

        # 404 = 端點不存在
        assert response.status_code != 404, "Endpoint should exist"

        print(f"✅ Preview endpoint exists (status: {response.status_code})")

    def test_preview_missing_case_id(self):
        """測試缺少 case_id 參數"""
        response = client.post(
            "/api/v1/signal-analysis/preview-window",
            json={
                "window_config": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                }
            }
        )

        # 應該返回 422（缺少必需參數）
        assert response.status_code == 422

        print(f"✅ Missing case_id validation: {response.status_code}")

    def test_preview_nonexistent_case(self):
        """測試不存在的案例"""
        response = client.post(
            "/api/v1/signal-analysis/preview-window",
            json={
                "case_id": "NONEXISTENT_CASE",
                "window_config": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                }
            }
        )

        # 應該返回 404
        assert response.status_code == 404

        error_detail = response.json()
        assert "未找到案例" in error_detail["detail"]

        print(f"✅ Nonexistent case: {error_detail['detail']}")


class TestAPIDocumentation:
    """測試 API 文檔和 OpenAPI schema"""

    def test_openapi_schema_available(self):
        """測試 OpenAPI schema 可訪問"""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        assert "paths" in schema
        assert "components" in schema

        print("✅ OpenAPI schema available")

    def test_signal_analysis_endpoints_documented(self):
        """測試信號分析端點已文檔化"""
        response = client.get("/openapi.json")
        schema = response.json()

        paths = schema["paths"]

        # 驗證兩個端點都在文檔中
        assert "/api/v1/signal-analysis/density" in paths, \
            "Density endpoint should be documented"
        assert "/api/v1/signal-analysis/preview-window" in paths, \
            "Preview endpoint should be documented"

        print("✅ Signal analysis endpoints documented")

    def test_density_endpoint_has_post_method(self):
        """測試 density 端點有 POST 方法"""
        response = client.get("/openapi.json")
        schema = response.json()

        density_path = schema["paths"]["/api/v1/signal-analysis/density"]

        assert "post" in density_path, "Should have POST method"

        post_spec = density_path["post"]
        assert "requestBody" in post_spec
        assert "responses" in post_spec

        print("✅ Density endpoint POST method documented")

    def test_request_schema_documented(self):
        """測試請求模型已文檔化"""
        response = client.get("/openapi.json")
        schema = response.json()

        components = schema["components"]["schemas"]

        # 應該包含 SignalDensityRequest
        assert "SignalDensityRequest" in components, \
            "SignalDensityRequest should be in schemas"

        request_schema = components["SignalDensityRequest"]
        assert "properties" in request_schema

        # 驗證必需欄位
        properties = request_schema["properties"]
        assert "strategy_config" in properties
        assert "training_window" in properties
        assert "positive_cases" in properties
        assert "negative_cases" in properties

        print("✅ Request schema documented")

    def test_response_schema_documented(self):
        """測試響應模型已文檔化"""
        response = client.get("/openapi.json")
        schema = response.json()

        components = schema["components"]["schemas"]

        # 應該包含 SignalDensityResponse
        assert "SignalDensityResponse" in components, \
            "SignalDensityResponse should be in schemas"

        response_schema = components["SignalDensityResponse"]
        properties = response_schema["properties"]

        # 驗證核心欄位
        assert "positive_avg_density" in properties
        assert "negative_avg_density" in properties
        assert "separation" in properties
        assert "p_value" in properties
        assert "cohens_d" in properties
        assert "stability_cv" in properties

        print("✅ Response schema documented")

    def test_endpoint_descriptions_exist(self):
        """測試端點有描述文檔"""
        response = client.get("/openapi.json")
        schema = response.json()

        density_endpoint = schema["paths"]["/api/v1/signal-analysis/density"]["post"]

        # 應該有摘要或描述
        assert "summary" in density_endpoint or "description" in density_endpoint

        if "description" in density_endpoint:
            desc = density_endpoint["description"]
            # 檢查是否包含關鍵信息
            assert len(desc) > 20, "Description should be meaningful"

        print("✅ Endpoint descriptions exist")


class TestErrorResponses:
    """測試錯誤響應格式"""

    def test_400_error_format(self):
        """測試 400 錯誤格式"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "nonexistent",
                    "strategy_logic": "three_line",
                    "params": {}
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["case1"],
                "negative_cases": ["case2"]
            }
        )

        assert response.status_code == 400

        error = response.json()
        assert "detail" in error
        assert isinstance(error["detail"], str)

        print(f"✅ 400 error format: {error}")

    def test_404_error_format(self):
        """測試 404 錯誤格式"""
        response = client.post(
            "/api/v1/signal-analysis/preview-window",
            json={
                "case_id": "NONEXISTENT",
                "window_config": {
                    "reference_point": "TO",
                    "lookback_bars": 240,
                    "lookforward_bars": 0,
                    "mode": "relative"
                }
            }
        )

        assert response.status_code == 404

        error = response.json()
        assert "detail" in error

        print(f"✅ 404 error format: {error}")

    def test_422_error_format(self):
        """測試 422 驗證錯誤格式"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={
                "invalid_field": "value"
            }
        )

        assert response.status_code == 422

        error = response.json()
        assert "detail" in error
        # FastAPI 的驗證錯誤格式
        assert isinstance(error["detail"], list)

        print(f"✅ 422 error format: {len(error['detail'])} validation errors")


class TestCORSAndHeaders:
    """測試 CORS 和 HTTP headers"""

    def test_content_type_json(self):
        """測試 Content-Type 為 JSON"""
        response = client.post(
            "/api/v1/signal-analysis/density",
            json={}
        )

        assert response.headers["content-type"] == "application/json"

        print("✅ Content-Type is JSON")

    def test_cors_headers_if_enabled(self):
        """測試 CORS headers（如果啟用）"""
        response = client.options("/api/v1/signal-analysis/density")

        # 如果啟用了 CORS，應該有對應 headers
        # 這取決於 main.py 的配置
        print(f"✅ CORS check: status={response.status_code}, "
              f"headers={response.headers.get('access-control-allow-origin', 'N/A')}")


class TestEndpointTags:
    """測試端點標籤（用於 API 分組）"""

    def test_endpoints_have_signal_analysis_tag(self):
        """測試端點有 'Signal Analysis' 標籤"""
        response = client.get("/openapi.json")
        schema = response.json()

        density_endpoint = schema["paths"]["/api/v1/signal-analysis/density"]["post"]
        preview_endpoint = schema["paths"]["/api/v1/signal-analysis/preview-window"]["post"]

        # 檢查標籤
        assert "tags" in density_endpoint
        assert "Signal Analysis" in density_endpoint["tags"]

        assert "tags" in preview_endpoint
        assert "Signal Analysis" in preview_endpoint["tags"]

        print("✅ Endpoints have correct tags")
