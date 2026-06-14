"""Feature run identity and canonical path helpers."""

from __future__ import annotations

import re
from pathlib import Path

from momentum.FeatureEngineering.feature_storage import FeatureStorage


_CONFIG_HASH_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def validate_config_hash(token: str) -> str:
    """驗證可安全作為 run identity 的 config hash。"""
    if not _CONFIG_HASH_PATTERN.fullmatch(token) or set(token) == {"."}:
        raise ValueError(f"Invalid config hash: {token!r}")
    return token


def safe_token(text: str) -> str:
    """依既有 CGSA 規則清理檔名 token。"""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def features_run_dir(root: Path, symbol: str, timeframe: str, config_hash: str) -> Path:
    """回傳 FeatureStorage canonical run 目錄，不執行 IO。"""
    validate_config_hash(config_hash)
    storage = FeatureStorage.__new__(FeatureStorage)
    storage.base_path = Path(root)
    return storage.feature_run_dir(symbol, timeframe, config_hash)


def cgsa_work_dir(root: Path, symbol: str, timeframe: str, config_hash: str) -> Path:
    """回傳既有 CGSA default work 目錄。"""
    validate_config_hash(config_hash)
    leaf = f"{safe_token(symbol)}_{safe_token(timeframe)}_{config_hash[:8]}"
    return (Path(root) / leaf).resolve()
