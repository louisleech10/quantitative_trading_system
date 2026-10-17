"""Momentum tests use the redirect plugin registered by tests/conftest.py."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def tmp_feature_runs(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """於 tmp 物化 FeatureLibrary 測試所需之小型真實特徵 run（真實 kline、短窗、輕量設定）。

    以 `data_cache/feature_klines/kline_cache.h5` 真實 K 線生成（禁合成資料），一切寫入隔離於 tmp：
    run 落 `<root>/data_cache/features`、registry 落 `<root>/data_cache/features/registry.json`
    （`fftfmeta_golden_helpers.prepare_env` 之 tmp 隔離＋cwd 移入 tmp；不碰專案 data_cache）。
    依序物化：BTCUSDT 12h 設定 A（L3 rolling 5／13）→ BTCUSDT 12h 設定 B（L3 rolling 5）→ ETHUSDT 12h 設定 A，
    故 BTCUSDT 12h 有兩個不同 config 之 run，且最新者為 B。

    回傳：`root`（測試須 chdir 至此，使 `create_feature_library()` 之相對 `data_cache/features` 解析到 tmp）、
    `registry`、`symbol`/`timeframe`、`hash_a`/`hash_b`/`hash_eth`、`index_a`/`index_b`/`index_eth`
    （生成當下之主時間軸，epoch 秒 int64 陣列，供載入端獨立比對）。
    """
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering.fftfmeta_golden_helpers import HEALTHY, KLINE_DIR, fast_payload, prepare_env

    timeframe = "12h"
    start_date, end_date = "2025-10-01", "2026-01-31"
    root = tmp_path_factory.mktemp("feature_library_runs")
    features_root = root / "data_cache" / "features"
    registry_path = features_root / "registry.json"

    def payload(windows: list) -> Dict[str, Any]:
        cfg = fast_payload([timeframe], **copy.deepcopy(HEALTHY))
        cfg["timeframes"] = {"primary": timeframe, "training": [timeframe], "alignment_mode": "open_minus"}
        cfg["rolling_aggregation"] = {"enabled": True, "windows": list(windows)}
        return cfg

    mp = pytest.MonkeyPatch()
    try:
        prepare_env(mp, root)
        mp.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_path))

        def generate(symbol: str, cfg: Dict[str, Any]):
            factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
            factory._storage = FeatureStorage(str(features_root))
            result = factory.generate_features(
                symbol, timeframe, config_override=cfg, force_regenerate=True,
                start_date=start_date, end_date=end_date, persist=True,
            )
            index = result.features_df.index
            if isinstance(index, pd.DatetimeIndex):
                seconds = index.view("int64") // 10**9
            else:  # 生成結果之主時間軸為 epoch 秒之整數 index
                seconds = np.asarray(index, dtype="int64")
            return str(result.metadata["config_hash"]), np.array(seconds, dtype="int64", copy=True)

        hash_a, index_a = generate("BTCUSDT", payload([5, 13]))
        hash_b, index_b = generate("BTCUSDT", payload([5]))
        hash_eth, index_eth = generate("ETHUSDT", payload([5, 13]))
    finally:
        mp.undo()

    # 物化前提不符 ⇒ fixture 錯誤（fail-closed；以 raise 而非 assert，免 fixture 斷言混入各測試之斷言序號化）
    if hash_a == hash_b:
        raise RuntimeError("兩個設定須產生不同 config_hash（否則消歧測試無意義）")
    if not registry_path.is_file():
        raise RuntimeError(f"tmp registry 未產生: {registry_path}")
    return {
        "root": root,
        "registry": registry_path,
        "symbol": "BTCUSDT",
        "timeframe": timeframe,
        "hash_a": hash_a,
        "hash_b": hash_b,
        "hash_eth": hash_eth,
        "index_a": index_a,
        "index_b": index_b,
        "index_eth": index_eth,
    }
