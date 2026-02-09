"""
Feature Engineering Module for Pattern Discovery

This module provides feature extraction functionality for machine learning-based
pattern discovery in trading strategies.
"""

from typing import Any

import pandas as pd
import h5py

from .feature_extractor import FeatureExtractor, StrategyParams
from .feature_validator import FeatureValidator
from .feature_storage import FeatureStorage
from .feature_factory import FeatureFactory, FeatureGenerationResult
from .config_manager import ConfigManager


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
