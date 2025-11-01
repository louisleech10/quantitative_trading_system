"""
配置載入器

從 YAML 文件載入指標配置，提供驗證和訪問功能。

功能：
- 載入 YAML 配置文件
- 驗證配置完整性和正確性
- 提供便捷的配置訪問方法
- 獲取指標元信息
- 獲取預設的批量計算配置

設計原則：
- 明確的錯誤處理（配置缺失、格式錯誤）
- 完整的驗證（必填欄位、類型檢查）
- 便捷的訪問接口
- 緩存機制（避免重複載入）
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required. Install it with: pip install pyyaml")

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    指標配置載入器

    從 YAML 文件載入和驗證指標配置。

    Example:
        >>> loader = ConfigLoader()
        >>> loader.load_config()
        >>>
        >>> # 獲取指標信息
        >>> ema_info = loader.get_indicator_info("ema")
        >>> print(ema_info['default_params'])
        {'period': 20}
        >>>
        >>> # 獲取預設批量計算配置
        >>> configs = loader.get_calculation_preset("ema_multi_period")
        >>> print(len(configs))
        3
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置載入器

        Args:
            config_path: 配置文件路徑（可選，默認使用項目根目錄下的 config/indicators.yaml）
        """
        if config_path is None:
            # 默認路徑：項目根目錄/config/indicators.yaml
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            config_path = project_root / "config" / "indicators.yaml"

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._is_loaded = False

        logger.info(f"ConfigLoader initialized with path: {self.config_path}")

    # ==================== 載入配置 ====================

    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        載入 YAML 配置文件

        Args:
            force_reload: 是否強制重新載入（默認使用緩存）

        Returns:
            Dict[str, Any]: 完整配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 格式錯誤
            ValueError: 配置驗證失敗

        Example:
            >>> loader = ConfigLoader()
            >>> config = loader.load_config()
            >>> print(config['version'])
            '1.0.0'
        """
        # 使用緩存
        if self._is_loaded and not force_reload:
            logger.debug("Using cached config")
            return self._config

        # 檢查文件是否存在
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\n"
                f"Please create the config file or specify a valid path."
            )

        # 載入 YAML
        logger.info(f"Loading config from: {self.config_path}")
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML config: {e}")

        # 驗證配置
        self._validate_config(config)

        # 緩存配置
        self._config = config
        self._is_loaded = True

        logger.info(
            f"Config loaded successfully: "
            f"{len(config.get('indicators', {}))} indicators, "
            f"{len(config.get('calculation_presets', {}))} presets"
        )

        return config

    def _validate_config(self, config: Dict[str, Any]):
        """
        驗證配置完整性

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置不完整或格式錯誤
        """
        # 檢查必填欄位
        required_fields = ['version', 'indicators']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field in config: {field}")

        # 檢查版本格式
        version = config['version']
        if not isinstance(version, str):
            raise ValueError(f"Invalid version format: {version}")

        # 檢查每個指標的配置
        indicators = config['indicators']
        if not isinstance(indicators, dict):
            raise ValueError("'indicators' must be a dictionary")

        for indicator_name, indicator_config in indicators.items():
            self._validate_indicator_config(indicator_name, indicator_config)

        logger.debug(f"Config validation passed: {len(indicators)} indicators")

    def _validate_indicator_config(self, name: str, config: Dict[str, Any]):
        """
        驗證單個指標配置

        Args:
            name: 指標名稱
            config: 指標配置

        Raises:
            ValueError: 配置不完整或格式錯誤
        """
        required_fields = ['class_name', 'module', 'default_params']
        for field in required_fields:
            if field not in config:
                raise ValueError(
                    f"Indicator '{name}' missing required field: {field}"
                )

        # 檢查 default_params 是字典
        if not isinstance(config['default_params'], dict):
            raise ValueError(
                f"Indicator '{name}': default_params must be a dictionary"
            )

    # ==================== 訪問配置 ====================

    def get_indicator_info(self, indicator_name: str) -> Dict[str, Any]:
        """
        獲取指標完整信息

        Args:
            indicator_name: 指標名稱

        Returns:
            Dict[str, Any]: 指標配置信息

        Raises:
            ValueError: 指標不存在

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> info = loader.get_indicator_info("ema")
            >>> print(info['default_params']['period'])
            20
        """
        # 確保配置已載入
        if not self._is_loaded:
            self.load_config()

        indicators = self._config.get('indicators', {})
        if indicator_name not in indicators:
            available = ", ".join(indicators.keys())
            raise ValueError(
                f"Indicator '{indicator_name}' not found in config. "
                f"Available: {available}"
            )

        return indicators[indicator_name]

    def get_default_params(self, indicator_name: str) -> Dict[str, Any]:
        """
        獲取指標默認參數

        Args:
            indicator_name: 指標名稱

        Returns:
            Dict[str, Any]: 默認參數

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> params = loader.get_default_params("ema")
            >>> print(params)
            {'period': 20}
        """
        info = self.get_indicator_info(indicator_name)
        return info['default_params']

    def get_param_ranges(self, indicator_name: str) -> Dict[str, Any]:
        """
        獲取指標參數範圍（用於 Optuna 優化）

        Args:
            indicator_name: 指標名稱

        Returns:
            Dict[str, Any]: 參數範圍定義

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> ranges = loader.get_param_ranges("ema")
            >>> print(ranges['period'])
            {'type': 'int', 'min': 2, 'max': 200, 'step': 1}
        """
        info = self.get_indicator_info(indicator_name)
        return info.get('param_ranges', {})

    def list_indicators(self) -> List[str]:
        """
        列出所有可用指標

        Returns:
            List[str]: 指標名稱列表

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> indicators = loader.list_indicators()
            >>> print(indicators)
            ['ema']
        """
        if not self._is_loaded:
            self.load_config()

        return list(self._config.get('indicators', {}).keys())

    # ==================== 批量計算預設 ====================

    def get_calculation_preset(self, preset_name: str) -> List[Dict[str, Any]]:
        """
        獲取預設的批量計算配置

        Args:
            preset_name: 預設名稱（如 "ema_multi_period"）

        Returns:
            List[Dict[str, Any]]: 計算配置列表

        Raises:
            ValueError: 預設不存在

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> configs = loader.get_calculation_preset("ema_multi_period")
            >>> print(len(configs))
            3
            >>> print(configs[0]['params']['period'])
            20
        """
        if not self._is_loaded:
            self.load_config()

        presets = self._config.get('calculation_presets', {})
        if preset_name not in presets:
            available = ", ".join(presets.keys())
            raise ValueError(
                f"Calculation preset '{preset_name}' not found. "
                f"Available: {available}"
            )

        preset = presets[preset_name]
        return preset['configs']

    def list_calculation_presets(self) -> List[str]:
        """
        列出所有預設的批量計算配置

        Returns:
            List[str]: 預設名稱列表

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> presets = loader.list_calculation_presets()
            >>> print(presets)
            ['ema_multi_period', 'ema_multi_source', 'full_indicator_set']
        """
        if not self._is_loaded:
            self.load_config()

        return list(self._config.get('calculation_presets', {}).keys())

    # ==================== 全局配置 ====================

    def get_global_config(self) -> Dict[str, Any]:
        """
        獲取全局配置

        Returns:
            Dict[str, Any]: 全局配置

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> global_config = loader.get_global_config()
            >>> print(global_config['cache']['enabled'])
            True
        """
        if not self._is_loaded:
            self.load_config()

        return self._config.get('global', {})

    def get_version(self) -> str:
        """
        獲取配置版本

        Returns:
            str: 版本號

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_config()
            >>> print(loader.get_version())
            '1.0.0'
        """
        if not self._is_loaded:
            self.load_config()

        return self._config.get('version', 'unknown')


# ==================== 模塊級便捷函數 ====================

# 單例模式：全局配置載入器
_global_loader: Optional[ConfigLoader] = None


def get_global_loader() -> ConfigLoader:
    """
    獲取全局配置載入器（單例模式）

    Returns:
        ConfigLoader: 全局配置載入器實例

    Example:
        >>> loader = get_global_loader()
        >>> indicators = loader.list_indicators()
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
        _global_loader.load_config()
    return _global_loader


def load_indicator_config(indicator_name: str) -> Dict[str, Any]:
    """
    便捷函數：載入指標配置

    Args:
        indicator_name: 指標名稱

    Returns:
        Dict[str, Any]: 指標配置

    Example:
        >>> config = load_indicator_config("ema")
        >>> print(config['default_params'])
        {'period': 20}
    """
    loader = get_global_loader()
    return loader.get_indicator_info(indicator_name)
