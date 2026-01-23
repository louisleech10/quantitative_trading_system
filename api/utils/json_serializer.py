"""
JSON 序列化工具
用於將 numpy 類型轉換為 Python 原生類型，解決 FastAPI 序列化問題
"""

import numpy as np
import math
from typing import Any, Dict, List
from decimal import Decimal


def convert_numpy_types(obj: Any) -> Any:
    """
    遞迴轉換物件中的 numpy 類型為 Python 原生類型
    
    Args:
        obj: 需要轉換的物件（dict, list, numpy types 等）
        
    Returns:
        轉換後的物件，保證可被 JSON 序列化
    """
    # numpy 數值類型
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    
    if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    
    # numpy 陣列
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    
    # Decimal 類型（如果有使用）
    if isinstance(obj, Decimal):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    
    # Python float 類型（也需要檢查 NaN/Inf）
    if isinstance(obj, float):
        if math.isnan(obj):
            return None  # NaN 轉為 null
        elif math.isinf(obj):
            return None  # Infinity 轉為 null
        return obj
    
    # 字典：遞迴轉換每個值
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    
    # 列表、元組：遞迴轉換每個元素
    if isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    
    # 其他類型保持原樣
    return obj


def sanitize_for_json(data: Dict) -> Dict:
    """
    清理資料以供 JSON 序列化
    
    這是 convert_numpy_types 的便捷包裝，專門用於字典類型
    
    Args:
        data: 需要清理的字典資料
        
    Returns:
        清理後可被 JSON 序列化的字典
    """
    return convert_numpy_types(data)
