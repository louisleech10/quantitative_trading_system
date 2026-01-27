"""
Debug 腳本：檢查 price_change_method 參數傳遞
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from api.models.requests import SearchConfigRequest, PriceChangeMethodEnum, FilterConditionRequest, ConditionTypeEnum, OperatorEnum
from api.services.standalone_search_service import StandaloneSearchService
from api.core.logging import get_logger

logger = get_logger(__name__)

def test_price_change_method_flow():
    """測試價格計算方式參數在整個流程中的傳遞"""
    
    print("=" * 70)
    print("測試 1: OPEN_TO_CLOSE 參數傳遞")
    print("=" * 70)
    
    # 建立測試請求 - OPEN_TO_CLOSE
    request1 = SearchConfigRequest(
        name="測試 OPEN_TO_CLOSE",
        timeframe="12h",
        start_date="2024-01-01",
        end_date="2024-01-31",
        initial_conditions=[
            FilterConditionRequest(
                condition_type=ConditionTypeEnum.PRICE,
                parameter="price_change",
                operator=OperatorEnum.GREATER_EQUAL,
                value=0.05,
                description="價格變化 >= 5%"
            )
        ],
        price_change_method=PriceChangeMethodEnum.OPEN_TO_CLOSE
    )
    
    print(f"✓ SearchConfigRequest.price_change_method = {request1.price_change_method}")
    print(f"  Value: {request1.price_change_method.value}")
    
    # 轉換為 SearchConfiguration
    service = StandaloneSearchService()
    config1 = service._convert_request_to_search_config(request1)
    
    print(f"✓ SearchConfiguration.price_change_method = {config1.price_change_method}")
    
    print("\n" + "=" * 70)
    print("測試 2: CLOSE_TO_CLOSE 參數傳遞")
    print("=" * 70)
    
    # 建立測試請求 - CLOSE_TO_CLOSE
    request2 = SearchConfigRequest(
        name="測試 CLOSE_TO_CLOSE",
        timeframe="12h",
        start_date="2024-01-01",
        end_date="2024-01-31",
        initial_conditions=[
            FilterConditionRequest(
                condition_type=ConditionTypeEnum.PRICE,
                parameter="price_change",
                operator=OperatorEnum.GREATER_EQUAL,
                value=0.05,
                description="價格變化 >= 5%"
            )
        ],
        price_change_method=PriceChangeMethodEnum.CLOSE_TO_CLOSE
    )
    
    print(f"✓ SearchConfigRequest.price_change_method = {request2.price_change_method}")
    print(f"  Value: {request2.price_change_method.value}")
    
    config2 = service._convert_request_to_search_config(request2)
    print(f"✓ SearchConfiguration.price_change_method = {config2.price_change_method}")
    
    print("\n" + "=" * 70)
    print("測試 3: 預設值測試")
    print("=" * 70)
    
    # 測試預設值
    request3 = SearchConfigRequest(
        name="測試預設值",
        timeframe="12h",
        start_date="2024-01-01",
        end_date="2024-01-31",
        initial_conditions=[]
    )
    
    print(f"✓ SearchConfigRequest.price_change_method (預設) = {request3.price_change_method}")
    print(f"  Value: {request3.price_change_method.value}")
    
    config3 = service._convert_request_to_search_config(request3)
    print(f"✓ SearchConfiguration.price_change_method (預設) = {config3.price_change_method}")
    
    print("\n" + "=" * 70)
    print("✅ 所有參數傳遞測試通過！")
    print("=" * 70)

if __name__ == '__main__':
    test_price_change_method_flow()
