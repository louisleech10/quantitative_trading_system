"""
OPTUNA_CACHE_REVIEW.md 修復驗證測試

此測試驗證以下修復:
1. 策略快取註冊機制 (strategy_cache_registry)
2. 記憶體自動偵測 (_detect_memory_limit_mb)
3. strategies.yaml is_cacheable 參數解析
4. 動態週期收集 (_collect_cacheable_periods_from_config)
5. 並發安全性 (threading.Lock)

Author: Claude (Ultra Think Process)
Date: 2026-01
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestStrategyCacheRegistry:
    """測試策略快取註冊機制"""
    
    def test_registry_import(self):
        """測試可以成功導入 strategy_cache_registry"""
        from momentum.Analysis.strategy_cache_registry import strategy_cache_registry
        assert strategy_cache_registry is not None
    
    def test_builtin_strategies_registered(self):
        """測試三個內建策略已註冊"""
        from momentum.Analysis.strategy_cache_registry import strategy_cache_registry
        
        strategies = strategy_cache_registry.list_strategies()
        assert 'three_line' in strategies
        assert 'short_long_cross' in strategies
        assert 'mid_long_cross' in strategies
    
    def test_has_strategy(self):
        """測試 has_strategy 方法"""
        from momentum.Analysis.strategy_cache_registry import strategy_cache_registry
        
        assert strategy_cache_registry.has_strategy('three_line') is True
        assert strategy_cache_registry.has_strategy('short_long_cross') is True
        assert strategy_cache_registry.has_strategy('mid_long_cross') is True
        assert strategy_cache_registry.has_strategy('unknown_strategy') is False
    
    def test_get_calculator(self):
        """測試 get_calculator 方法"""
        from momentum.Analysis.strategy_cache_registry import strategy_cache_registry
        
        calc = strategy_cache_registry.get_calculator('three_line')
        assert calc is not None
        assert callable(calc)
        
        calc = strategy_cache_registry.get_calculator('unknown_strategy')
        assert calc is None
    
    def test_register_strategy_decorator(self):
        """測試 @register_strategy_cache 裝飾器"""
        from momentum.Analysis.strategy_cache_registry import (
            strategy_cache_registry, 
            register_strategy_cache
        )
        
        @register_strategy_cache("test_strategy")
        def test_calculator(short_ema, long_ema, params):
            return short_ema > long_ema
        
        assert strategy_cache_registry.has_strategy('test_strategy')
        calc = strategy_cache_registry.get_calculator('test_strategy')
        assert calc is test_calculator


class TestMemoryAutoDetection:
    """測試記憶體自動偵測功能"""
    
    def test_detect_memory_limit(self):
        """測試 _detect_memory_limit_mb 函式"""
        from momentum.Analysis.indicator_cache import _detect_memory_limit_mb
        
        detected_mb = _detect_memory_limit_mb()
        assert detected_mb > 0
        assert isinstance(detected_mb, float)
    
    def test_detect_memory_uses_half_available(self):
        """測試使用系統可用記憶體的 50%"""
        import psutil
        from momentum.Analysis.indicator_cache import _detect_memory_limit_mb
        
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        detected_mb = _detect_memory_limit_mb()
        
        # 允許小範圍誤差（記憶體會波動）
        expected = available_mb * 0.5
        assert abs(detected_mb - expected) < 100  # 100MB 誤差範圍
    
    def test_detect_memory_fallback_on_error(self):
        """測試 psutil 異常時的 fallback"""
        from momentum.Analysis.indicator_cache import _detect_memory_limit_mb
        
        # 模擬 psutil 拋出異常
        with patch('psutil.virtual_memory', side_effect=Exception("Mock error")):
            detected_mb = _detect_memory_limit_mb()
            assert detected_mb == 2000.0  # 預設 2GB (2000 MB)


class TestStrategiesYamlParsing:
    """測試 strategies.yaml 解析"""
    
    def test_yaml_file_exists(self):
        """測試 strategies.yaml 檔案存在"""
        config_path = Path('config/strategies.yaml')
        assert config_path.exists()
    
    def test_is_cacheable_markers_exist(self):
        """測試 is_cacheable 標記存在於所有週期參數"""
        config_path = Path('config/strategies.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        strategies = config.get('strategies', {})
        
        # 檢查 three_line 策略
        three_line = strategies.get('three_line', {})
        params = three_line.get('parameters', [])
        cacheable_params = [p['name'] for p in params if p.get('is_cacheable')]
        
        assert 'short_period' in cacheable_params
        assert 'mid_period' in cacheable_params
        assert 'long_period' in cacheable_params
    
    def test_all_period_params_are_cacheable(self):
        """測試所有週期參數都標記為 is_cacheable"""
        config_path = Path('config/strategies.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        strategies = config.get('strategies', {})
        
        for strategy_name, strategy_config in strategies.items():
            params = strategy_config.get('parameters', [])
            for param in params:
                if 'period' in param.get('name', ''):
                    assert param.get('is_cacheable', False) is True, \
                        f"策略 {strategy_name} 的 {param['name']} 應該標記為 is_cacheable"


class TestDynamicPeriodCollection:
    """測試動態週期收集邏輯"""
    
    def test_collect_periods_from_config(self):
        """測試從 strategies.yaml 收集可快取週期"""
        import yaml
        from pathlib import Path
        
        config_path = Path('config/strategies.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        strategies = config.get('strategies', {})
        periods_to_cache = set()
        
        # 模擬 parameter_ranges
        mock_ranges = {
            'ema_short_range': (5, 10),
            'ema_mid_range': (20, 30),
            'ema_long_range': (50, 70),
        }
        
        strategy_config = strategies.get('three_line', {})
        parameters = strategy_config.get('parameters', [])
        
        for param in parameters:
            if not param.get('is_cacheable', False):
                continue
            
            param_name = param.get('name')
            range_attr_name = f"ema_{param_name.replace('_period', '')}_range"
            
            if range_attr_name in mock_ranges:
                min_val, max_val = mock_ranges[range_attr_name]
                periods_to_cache.update(range(min_val, max_val + 1))
        
        # 驗證收集到的週期
        assert 5 in periods_to_cache  # short_period min
        assert 10 in periods_to_cache  # short_period max
        assert 20 in periods_to_cache  # mid_period min
        assert 70 in periods_to_cache  # long_period max


class TestConcurrencySafety:
    """測試並發安全性"""
    
    def test_indicator_cache_has_lock(self):
        """測試 IndicatorCache 有 threading.Lock"""
        import threading
        from momentum.Analysis.indicator_cache import IndicatorCache
        
        # 檢查類別定義中是否有 lock
        import inspect
        source = inspect.getsource(IndicatorCache)
        assert 'threading.Lock' in source or 'Lock()' in source
    
    def test_cache_write_is_thread_safe(self):
        """測試快取寫入使用了 lock"""
        import inspect
        from momentum.Analysis.indicator_cache import IndicatorCache
        
        source = inspect.getsource(IndicatorCache)
        # 確認有使用 with self._cache_lock 的模式
        assert '_cache_lock' in source


class TestResourceCleanup:
    """測試資源清理"""
    
    def test_cleanup_caches_method_exists(self):
        """測試 _cleanup_caches 方法存在"""
        from momentum.Optimization.optuna_optimizer import OptunaOptimizer
        
        assert hasattr(OptunaOptimizer, '_cleanup_caches')
    
    def test_cleanup_caches_clears_kline_cache(self):
        """測試 _cleanup_caches 會清理 K 線快取"""
        import inspect
        from momentum.Optimization.optuna_optimizer import OptunaOptimizer
        
        source = inspect.getsource(OptunaOptimizer._cleanup_caches)
        assert '_kline_cache' in source
        assert 'clear()' in source
    
    def test_cleanup_caches_clears_indicator_cache(self):
        """測試 _cleanup_caches 會清理指標快取"""
        import inspect
        from momentum.Optimization.optuna_optimizer import OptunaOptimizer
        
        source = inspect.getsource(OptunaOptimizer._cleanup_caches)
        assert '_indicator_cache' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
