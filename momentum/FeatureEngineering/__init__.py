"""
Feature Engineering Module for Pattern Discovery

This module provides feature extraction functionality for machine learning-based
pattern discovery in trading strategies.
"""

from .feature_extractor import FeatureExtractor, StrategyParams
from .feature_validator import FeatureValidator
from .feature_storage import FeatureStorage

__all__ = ['FeatureExtractor', 'StrategyParams', 'FeatureValidator', 'FeatureStorage']
