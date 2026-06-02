"""Step 6 效能基準腳本（4-6）。

執行方式：
  ./venv/bin/python tests/performance/step6_multitf_batch_benchmark.py
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_adapters import (
    FeatureFactoryBrowseAdapter,
    FeatureFactoryQualityAdapter,
)
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from momentum.factories import create_feature_factory, create_kline_storage_manager


def _pick_symbols(required_tfs: List[str], count: int) -> List[str]:
    storage = create_kline_storage_manager()
    cache_index = storage.get_cache_index()
    if not cache_index:
        storage.rebuild_cache_index()
        cache_index = storage.get_cache_index()
    symbols: List[str] = []

    for symbol, tfs in cache_index.items():
        if all(tf in tfs for tf in required_tfs):
            symbols.append(symbol)
        if len(symbols) >= count:
            break

    # Fallback for 12h benchmarks: discover symbols from legacy files when cache index is incomplete.
    if len(symbols) < count and required_tfs == ["12h"]:
        data_cache_dir = Path("data_cache")
        for file_path in sorted(data_cache_dir.glob("*_12h.h5")):
            symbol = file_path.stem[: -len("_12h")]
            if symbol not in symbols:
                symbols.append(symbol)
            if len(symbols) >= count:
                break

    return symbols


def _single_tf_override() -> Dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": "12h",
            "training": ["12h"],
            "alignment_mode": "open_minus",
        },
    }


def _multi_tf_override() -> Dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": "12h",
            "training": ["1h", "4h", "12h"],
            "alignment_mode": "open_minus",
        },
    }


def _benchmark_single_symbol(factory, symbol: str) -> Dict[str, float]:
    t0 = time.perf_counter()
    factory.generate_features(
        symbol=symbol,
        timeframe="12h",
        config_override=_single_tf_override(),
        force_regenerate=True,
    )
    baseline_sec = time.perf_counter() - t0

    t1 = time.perf_counter()
    factory.generate_features(
        symbol=symbol,
        timeframe="12h",
        config_override=_multi_tf_override(),
        force_regenerate=True,
    )
    multi_tf_sec = time.perf_counter() - t1

    return {
        "single_symbol_1tf_sec": baseline_sec,
        "single_symbol_3tf_sec": multi_tf_sec,
        "ratio_3tf_over_1tf": multi_tf_sec / max(baseline_sec, 1e-9),
    }


async def _wait_batch_done(service: FeatureFactoryBatchService, task_id: str, timeout_sec: float = 1800.0) -> Dict[str, Any]:
    start = time.perf_counter()
    while True:
        status = service.get_status(task_id)
        if status and status["status"] in {"completed", "partial", "failed"}:
            return status
        if (time.perf_counter() - start) > timeout_sec:
            raise TimeoutError(f"batch timeout: {task_id}")
        await asyncio.sleep(1.0)


async def _benchmark_batch(service: FeatureFactoryBatchService, symbols: List[str], override: Dict[str, Any]) -> Dict[str, Any]:
    request = BatchGenerateRequest(
        symbols=symbols,
        timeframe="12h",
        config_override=override,
        force_regenerate=True,
        max_workers=4,
    )

    t0 = time.perf_counter()
    task_id = await service.start_batch(request)
    status = await _wait_batch_done(service, task_id)
    elapsed = time.perf_counter() - t0

    return {
        "task_id": task_id,
        "status": status["status"],
        "elapsed_sec": elapsed,
        "completed": status["completed"],
        "failed": status["failed"],
        "total": status["total"],
    }


async def main() -> None:
    factory = create_feature_factory()

    symbols_1tf = _pick_symbols(["12h"], count=5)
    symbols_3tf = _pick_symbols(["1h", "4h", "12h"], count=5)

    if not symbols_1tf:
        raise RuntimeError("No symbols with 12h data available for benchmark")

    single_symbol = symbols_3tf[0] if symbols_3tf else symbols_1tf[0]

    single_stats = _benchmark_single_symbol(factory, single_symbol)

    service = FeatureFactoryBatchService(
        browse_registrar=FeatureFactoryBrowseAdapter(),
        quality_computer=FeatureFactoryQualityAdapter(),
    )
    batch_1tf: Optional[Dict[str, Any]] = None
    batch_3tf: Optional[Dict[str, Any]] = None
    single_batch_1tf: Optional[Dict[str, Any]] = None
    single_batch_3tf: Optional[Dict[str, Any]] = None

    # Batch baseline: include ProcessPool spawn overhead for fair comparison.
    single_batch_1tf = await _benchmark_batch(service, [symbols_1tf[0]], _single_tf_override())

    if symbols_3tf:
        single_batch_3tf = await _benchmark_batch(service, [symbols_3tf[0]], _multi_tf_override())

    if len(symbols_1tf) >= 5:
        batch_1tf = await _benchmark_batch(service, symbols_1tf, _single_tf_override())
    else:
        batch_1tf = {
            "status": "skipped",
            "reason": f"insufficient symbols for 1TF batch benchmark: {len(symbols_1tf)}/5",
        }

    if len(symbols_3tf) >= 5:
        batch_3tf = await _benchmark_batch(service, symbols_3tf, _multi_tf_override())
    else:
        batch_3tf = {
            "status": "skipped",
            "reason": f"insufficient symbols for 3TF batch benchmark: {len(symbols_3tf)}/5",
        }

    report: Dict[str, Any] = {
        "single_symbol": {
            "symbol": single_symbol,
            **single_stats,
            "target_ratio_3tf_over_1tf_lt": 3.0,
            "pass": single_stats["ratio_3tf_over_1tf"] < 3.0,
        },
        "single_batch_baseline_1tf": single_batch_1tf,
        "single_batch_baseline_3tf": single_batch_3tf,
        "batch_1tf": batch_1tf,
        "batch_3tf": batch_3tf,
    }

    if batch_1tf is not None and batch_1tf.get("status") != "skipped":
        baseline_1tf = single_batch_1tf["elapsed_sec"] if single_batch_1tf else single_stats["single_symbol_1tf_sec"]
        report["batch_1tf"]["target_elapsed_lt_sec"] = baseline_1tf * 2.0
        report["batch_1tf"]["pass"] = (
            batch_1tf["status"] == "completed"
            and batch_1tf["elapsed_sec"] < (baseline_1tf * 2.0)
        )

    if batch_3tf is not None and batch_3tf.get("status") != "skipped":
        baseline_3tf = (
            single_batch_3tf["elapsed_sec"]
            if single_batch_3tf and single_batch_3tf.get("status") != "skipped"
            else single_stats["single_symbol_1tf_sec"]
        )
        report["batch_3tf"]["target_elapsed_lt_sec"] = baseline_3tf * 6.0
        report["batch_3tf"]["pass"] = (
            batch_3tf["status"] == "completed"
            and batch_3tf["elapsed_sec"] < (baseline_3tf * 6.0)
        )

    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
