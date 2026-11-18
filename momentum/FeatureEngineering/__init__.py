"""
Feature Engineering Module for Pattern Discovery

This module provides feature extraction functionality for machine learning-based
pattern discovery in trading strategies.
"""

from typing import Any

import pandas as pd
import h5py

import importlib as _importlib

# 套件層級匯出改為首次取用才載入（PEP 562 模組層 __getattr__／__dir__，https://peps.python.org/pep-0562/；
# TESTSEL I4g，docs/TESTSEL_I4G_SPEC.md）：原急切匯入使任何 `momentum.FeatureEngineering.*` 子模組匯入皆帶入
# feature_factory／feature_validator（statsmodels、numba 預編鏈，約 2.3 秒）。取得之物件與子模組中同名物件為同一物件；
# 下方 pd.read_hdf 相容補丁仍於本檔執行時生效（時點不變）。
_LAZY_EXPORTS = {
	'FeatureExtractor': '.feature_extractor',
	'StrategyParams': '.feature_extractor',
	'FeatureValidator': '.feature_validator',
	'FeatureStorage': '.feature_storage',
	'FeatureFactory': '.feature_factory',
	'FeatureGenerationResult': '.feature_factory',
	'ConfigManager': '.config_manager',
}


def __getattr__(name: str) -> Any:
	module_name = _LAZY_EXPORTS.get(name)
	if module_name is None:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	value = getattr(_importlib.import_module(module_name, __name__), name)
	globals()[name] = value
	return value


def __dir__() -> list:
	return sorted(set(globals()) | set(_LAZY_EXPORTS))


# pandas.read_hdf 相容性補丁：支援讀取既有 HDF5 結構 (h5py 格式)
_orig_read_hdf = pd.read_hdf


def _read_hdf_compat(path_or_buf: Any, key: str = None, *args, **kwargs):
	try:
		return _orig_read_hdf(path_or_buf, key=key, *args, **kwargs)
	except Exception:
		if not key:
			raise

		path_str = str(path_or_buf)
		if path_str.endswith("kline_cache.h5"):
			with h5py.File(path_str, "r") as f:
				if key not in f:
					raise

				node = f[key]
				if hasattr(node, "keys") and "data" in node:
					data = node["data"][:]
				else:
					data = node[:]

			return pd.DataFrame(data)

		raise


# 保留此相容補丁：既有模組仍可能以 pd.read_hdf(..., key='SYMBOL/TF') 讀取 kline_cache.h5。
if pd.read_hdf is not _read_hdf_compat:
	pd.read_hdf = _read_hdf_compat

__all__ = [
	'FeatureExtractor',
	'StrategyParams',
	'FeatureValidator',
	'FeatureStorage',
	'FeatureFactory',
	'FeatureGenerationResult',
	'ConfigManager',
]
