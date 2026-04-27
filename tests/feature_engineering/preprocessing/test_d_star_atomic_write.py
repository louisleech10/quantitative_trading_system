from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext


def _context() -> PreprocessingContext:
    return PreprocessingContext(
        symbol="ETHUSDT",
        timeframe="1h",
        config_hash="b" * 32,
        data_fingerprint="fingerprint-atomic",
        feature_schema_hash="schema-atomic",
        time_range=(1, 100),
        row_count=100,
        source_data_version="test",
    )


def _cache(cache_dir: Path) -> DStarCache:
    return DStarCache(
        _context(),
        cache_dir,
        adf_threshold=0.1,
        precision=0.02,
        max_lag=64,
        weight_threshold=1e-5,
        sample_size=500,
        nan_policy="dropna",
    )


def _write_once(cache_dir: Path, index: int) -> Dict[str, object]:
    cache = _cache(cache_dir)
    cache.set(f"L1_close_{index}", float(index) / 100.0)
    cache.flush_atomic()
    return json.loads(cache.path.read_text(encoding="utf-8"))


def test_d_star_atomic_write_parallel_valid_json(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        payloads = list(executor.map(lambda idx: _write_once(tmp_path, idx), range(100)))

    assert len(payloads) == 100
    for payload in payloads:
        assert payload["cache_version"] == "v2"
        assert payload["symbol"] == "ETHUSDT"
        assert isinstance(payload["entries"], dict)

    final_payload = json.loads(_cache(tmp_path).path.read_text(encoding="utf-8"))
    assert final_payload["cache_version"] == "v2"
    assert isinstance(final_payload["entries"], dict)
