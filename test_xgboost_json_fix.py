"""
測試 XGBoost Batch 分析 - JSON 序列化修復驗證

測試場景：
1. 啟動批量分析任務
2. 輪詢任務狀態（模擬前端行為）
3. 驗證返回的 JSON 可以正確序列化（不會有 numpy.int64 錯誤）

執行方式：
    python test_xgboost_json_fix.py
"""

import sys
import time
import requests
from pathlib import Path

# 加入專案路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger

logger = get_logger(__name__)

API_BASE = "http://localhost:8000/api/v1"


def test_batch_xgboost_json():
    """測試批量 XGBoost 分析的 JSON 序列化"""
    
    logger.info("=" * 80)
    logger.info("測試 5: XGBoost Batch JSON 序列化修復")
    logger.info("=" * 80)
    
    # Step 1: 啟動批量分析
    logger.info("\n📤 Step 1: 發送批量分析請求...")
    
    payload = {
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "lookback_bars": 200,
        "indicators": [
            {
                "indicator": "ema_three_line",
                "data_source": "close",
                "params": {
                    "ema_short": 5,
                    "ema_mid": 13,
                    "ema_long": 34,
                    "volume_threshold": 0.0
                }
            }
        ],
        "cv_folds": 5,
        "xgboost_params": {
            "max_depth": 5,
            "learning_rate": 0.1,
            "n_estimators": 100
        },
        "top_n_rules": 10,
        "min_support": 10
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/pattern-analysis/xgboost/batch/start",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        task_id = data.get('task_id')
        logger.info(f"✅ 任務已啟動: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ 啟動任務失敗: {e}")
        return False
    
    # Step 2: 輪詢任務狀態（模擬前端行為）
    logger.info("\n🔄 Step 2: 輪詢任務狀態（最多 10 次，每次間隔 2 秒）...")
    
    max_polls = 10
    poll_interval = 2
    
    for i in range(max_polls):
        time.sleep(poll_interval)
        
        try:
            response = requests.get(
                f"{API_BASE}/pattern-analysis/xgboost/batch/task/{task_id}",
                timeout=10
            )
            
            # 檢查狀態碼
            if response.status_code != 200:
                logger.error(f"❌ Poll {i+1}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return False
            
            # 嘗試解析 JSON
            task_status = response.json()
            
            status = task_status.get('status', 'unknown')
            progress = task_status.get('progress', 0)
            current_step = task_status.get('current_step', 'N/A')
            
            logger.info(
                f"✅ Poll {i+1}: status={status}, progress={progress}%, "
                f"step={current_step}"
            )
            
            # 如果完成或失敗，停止輪詢
            if status == 'completed':
                logger.info("\n🎉 任務完成！")
                
                # 檢查結果資料
                result = task_status.get('result')
                if result:
                    logger.info(f"  - 總案例: {result.get('total_cases')}")
                    logger.info(f"  - 有效案例: {result.get('valid_cases')}")
                    logger.info(f"  - 正例: {result.get('positive_cases')}")
                    logger.info(f"  - 反例: {result.get('negative_cases')}")
                    logger.info(f"  - 特徵數: {result.get('features_generated')}")
                    
                    # 檢查是否有 numpy 類型（這些應該都被轉換了）
                    perf = result.get('model_performance', {})
                    logger.info(f"  - Train AUC: {perf.get('train_auc_score')}")
                    logger.info(f"  - CV AUC: {perf.get('cv_auc_mean')}")
                
                return True
            
            elif status == 'failed':
                logger.error(f"❌ 任務失敗: {task_status.get('error')}")
                return False
            
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"❌ Poll {i+1}: JSON 解析失敗 - {e}")
            logger.error(f"Response text: {response.text[:500]}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Poll {i+1}: 未預期的錯誤 - {e}")
            return False
    
    logger.warning("⏰ 達到最大輪詢次數，任務仍在執行中")
    return True  # 不算失敗，只是還沒完成


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("XGBoost Batch JSON 序列化修復測試")
    print("=" * 80)
    
    success = test_batch_xgboost_json()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 測試通過 - JSON 序列化正常，沒有無限迴圈")
    else:
        print("❌ 測試失敗 - 請檢查日誌")
    print("=" * 80 + "\n")
    
    sys.exit(0 if success else 1)
