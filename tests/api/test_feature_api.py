"""
Feature Engineering API Tests - API 端點測試

測試特徵工程 REST API 功能

Author: AI Agent
Date: 2026-01-10
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_feature_extraction_api():
    """測試特徵提取 API 端點"""
    request_data = {
        "case_id": "ETHUSDT_1735905600_1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "strategy_type": "ema_three_line",
        "strategy_params": {
            "ema_short": 5,
            "ema_mid": 20,
            "ema_long": 60,
            "volume_threshold": 0.6
        },
        "include_basic_features": True,
        "validate": True
    }
    
    response = client.post("/api/v1/features/extract", json=request_data)
    
    assert response.status_code == 202
    data = response.json()
    assert 'task_id' in data
    assert data['status'] == 'running'
    assert 'estimated_time' in data
    
    print(f"✅ 特徵提取 API 測試通過 - task_id: {data['task_id']}")
    
    # 等待任務完成 (最多等待 60 秒)
    task_id = data['task_id']
    for _ in range(60):
        status_response = client.get(f"/api/v1/features/task/{task_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        if status_data['status'] == 'completed':
            print(f"✅ 任務完成 - 特徵數: {status_data['result']['n_features']}")
            assert status_data['result']['n_features'] >= 20
            break
        elif status_data['status'] == 'failed':
            pytest.fail(f"任務失敗: {status_data['error']}")
        
        asyncio.sleep(1)


def test_feature_task_status_api():
    """測試任務狀態查詢 API"""
    # 先啟動一個任務
    request_data = {
        "case_id": "ETHUSDT_1736942400_1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "strategy_type": "ema_three_line",
        "strategy_params": {
            "ema_short": 5,
            "ema_mid": 20,
            "ema_long": 60,
            "volume_threshold": 0.6
        }
    }
    
    response = client.post("/api/v1/features/extract", json=request_data)
    task_id = response.json()['task_id']
    
    # 查詢任務狀態
    status_response = client.get(f"/api/v1/features/task/{task_id}")
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert 'task_id' in data
    assert 'status' in data
    assert 'progress' in data
    assert data['status'] in ['running', 'completed', 'failed']
    
    print(f"✅ 任務狀態查詢 API 測試通過 - 狀態: {data['status']}")


def test_feature_task_not_found():
    """測試查詢不存在的任務"""
    response = client.get("/api/v1/features/task/nonexistent_task")
    
    assert response.status_code == 404
    
    print("✅ 不存在任務處理測試通過")


def test_feature_extraction_invalid_params():
    """測試無效參數處理"""
    request_data = {
        "case_id": "INVALID_CASE",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "strategy_type": "invalid_strategy",  # 無效策略類型
        "strategy_params": {}
    }
    
    response = client.post("/api/v1/features/extract", json=request_data)
    
    assert response.status_code == 400  # Bad Request
    
    print("✅ 無效參數處理測試通過")


def test_health_check():
    """測試健康檢查端點"""
    response = client.get("/api/v1/features/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'feature_engineering'
    
    print("✅ 健康檢查測試通過")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
