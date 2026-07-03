#!/usr/bin/env python3
"""Freeze pre-fix fracdiff max_lag G1/G2 golden receipts."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import tempfile
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing import _d_star_cache
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory, create_kline_storage_manager
from tests.feature_engineering.ff_maxlag_golden_helpers import (
    canonical_raw_dir_digests,
    compare_golden_digests,
    digest_frame_sha256,
)
from tests.feature_engineering.ff_truncation_mr_helpers import (
    KLINE_CACHE_DIR,
    _bar_window_dates,
    _fracdiff_mr_config_payload,
    _fracdiff_window_bars,
    _ensure_module_env,
)


SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAME = "1h"
RECEIPT_DIR = PROJECT_ROOT / "handoffs" / "run_receipts"
ARTIFACT_DIR = RECEIPT_DIR / "fracdiff_maxlag_golden_artifacts"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _setup_logging(log_path: Path) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(formatter)
    root.addHandler(handler)


@contextmanager
def _capture_dstar_stats() -> Iterator[Dict[str, Dict[str, int]]]:
    original_stats = _d_star_cache.DStarCache.stats
    captured: Dict[str, Dict[str, int]] = {}

    def _stats_wrapper(self: _d_star_cache.DStarCache) -> tuple[int, int]:
        hits, misses = original_stats(self)
        captured[str(self.path)] = {"hits": int(hits), "misses": int(misses)}
        return hits, misses

    _d_star_cache.DStarCache.stats = _stats_wrapper  # type: ignore[method-assign]
    try:
        yield captured
    finally:
        _d_star_cache.DStarCache.stats = original_stats  # type: ignore[method-assign]


def _read_kline(symbol: str) -> pd.DataFrame:
    manager = create_kline_storage_manager(cache_dir=str(PROJECT_ROOT / KLINE_CACHE_DIR))
    frame = manager.read_klines(symbol, TIMEFRAME, validate_continuity=False)
    if frame is None or frame.empty:
        raise RuntimeError(f"missing real kline data for {symbol}/{TIMEFRAME}")
    return frame


def _config_for(label: str) -> Dict[str, Any]:
    # G2 不走 config override：現行 HEAD nested pydantic 會丟棄未知 max_lag 鍵
    # （委員會實證 handoffs/20260703-FRACDIFF-MAXLAG-G2PIN-CODEX.md §1），
    # 改用 _pin_fracdiff_max_lag() 實例注入（calculation-path pin）。
    return copy.deepcopy(_fracdiff_mr_config_payload())


G2_PIN_MAX_LAG = 50


@contextmanager
def _pin_fracdiff_max_lag(value: int) -> Iterator[None]:
    """G2-only：patch FeaturePreprocessor.__init__，於實例 fracdiff_config 注入 max_lag。

    等價論證閉合在 production 唯一讀值點 feature_preprocessor.py:3198
    `self.fracdiff_config.get("max_lag", 0)`；wrapper 內 fail-fast 斷言防打錯層。
    """
    original_init = FeaturePreprocessor.__init__

    def _patched_init(self: FeaturePreprocessor, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        # rebind 實例自己的 copy，不 mutate 共享 config dict（防跨實例污染）
        pinned = dict(self.fracdiff_config)
        pinned["max_lag"] = int(value)
        self.fracdiff_config = pinned
        if self.fracdiff_config.get("max_lag") != int(value):
            raise AssertionError("G2 pin injection failed at instance fracdiff_config")

    FeaturePreprocessor.__init__ = _patched_init  # type: ignore[method-assign]
    try:
        yield
    finally:
        FeaturePreprocessor.__init__ = original_init  # type: ignore[method-assign]
        if FeaturePreprocessor.__init__ is not original_init:
            raise AssertionError("G2 pin patch not restored; would pollute later runs")


def _make_factory(features_root: Path, d_star_dir: Path):
    _ensure_module_env()
    factory = create_feature_factory(
        cache_dir=str(PROJECT_ROOT / KLINE_CACHE_DIR),
        validate_continuity=False,
    )
    factory._storage = FeatureStorage(str(features_root))
    FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: d_star_dir)  # type: ignore[method-assign]
    return factory


@contextmanager
def _isolated_cgsa_work(work_dir: Path) -> Iterator[None]:
    previous = os.environ.get("FFACT_CGSA_WORK_DIR")
    os.environ["FFACT_CGSA_WORK_DIR"] = str(work_dir)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FFACT_CGSA_WORK_DIR", None)
        else:
            os.environ["FFACT_CGSA_WORK_DIR"] = previous


def _cache_payload(d_star_dir: Path, symbol: str) -> Dict[str, Any]:
    candidates = sorted(d_star_dir.glob(f"d_star_{symbol}_{TIMEFRAME}_*.json"))
    if not candidates:
        raise RuntimeError(f"no DStarCache payload found in {d_star_dir} for {symbol}/{TIMEFRAME}")
    if len(candidates) != 1:
        raise RuntimeError(f"expected one DStarCache payload in {d_star_dir}, got {len(candidates)}")
    path = candidates[0]
    # read_d_star_json 只回欄位→d_star 值；meta 欄位須直接讀原始 payload
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "fracdiff_hash": str(payload.get("fracdiff_hash")),
        "resolved_max_lag": int(payload.get("max_lag")),
        "row_count": int(payload.get("row_count")),
        "time_range": payload.get("time_range"),
        "entry_count": len(payload.get("entries", {})),
    }


def _run_symbol(
    *,
    label: str,
    run_id: str,
    symbol: str,
    config: Mapping[str, Any],
    window_bars: int,
    capture_stats: Dict[str, Dict[str, int]],
) -> Dict[str, Any]:
    kline = _read_kline(symbol)
    start_date, end_date, _ = _bar_window_dates(kline, window_bars=window_bars, trunc_k=10)
    run_root = ARTIFACT_DIR / run_id / symbol
    features_root = run_root / "features"
    cgsa_work_dir = run_root / "cgsa_work"
    d_star_dir = run_root / "d_star_cache"
    d_star_dir.mkdir(parents=True, exist_ok=True)
    if any(d_star_dir.iterdir()):
        raise RuntimeError(f"d_star_cache dir must be empty before run: {d_star_dir}")

    logging.info(
        "START label=%s run_id=%s symbol=%s timeframe=%s start=%s end=%s d_star_dir=%s",
        label,
        run_id,
        symbol,
        TIMEFRAME,
        start_date,
        end_date,
        d_star_dir,
    )
    with _isolated_cgsa_work(cgsa_work_dir):
        factory = _make_factory(features_root, d_star_dir)
        result = factory.generate_features(
            symbol,
            TIMEFRAME,
            config_override=dict(config),
            force_regenerate=True,
            start_date=start_date,
            end_date=end_date,
            persist=True,
        )
    # persist=True streaming 模式不回傳 features_df；真實產物在 L7 raw parquet
    # （與 ff_truncation_mr_helpers._run_generation 讀法一致）。
    config_hash = str(result.metadata["config_hash"])
    raw_dir = features_root / symbol / TIMEFRAME / config_hash / "raw"
    if not raw_dir.is_dir():
        raise RuntimeError(f"L7 raw dir missing after persist=True: {raw_dir}")
    digest = canonical_raw_dir_digests(raw_dir)
    if digest["row_count"] <= 0 or digest["column_count"] <= 0:
        raise RuntimeError(f"empty raw digest for {label}/{symbol}")
    frame_hash = digest_frame_sha256(digest)
    cache = _cache_payload(d_star_dir, symbol)
    stats = capture_stats.get(str(PROJECT_ROOT / cache["path"]), {"hits": 0, "misses": 0})
    fracdiff_cols = [
        column for column in digest["columns"] if "fracdiff" in str(column).lower()
    ]
    if not fracdiff_cols:
        raise RuntimeError(f"no fracdiff columns detected for {label}/{symbol}")

    logging.info(
        "DONE label=%s run_id=%s symbol=%s rows=%s cols=%s fracdiff_cols=%s max_lag=%s hits=%s misses=%s cache=%s",
        label,
        run_id,
        symbol,
        digest["row_count"],
        digest["column_count"],
        len(fracdiff_cols),
        cache["resolved_max_lag"],
        stats["hits"],
        stats["misses"],
        cache["path"],
    )
    return {
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        "start_date": start_date,
        "end_date": end_date,
        "raw_dir": str(raw_dir.relative_to(PROJECT_ROOT)),
        "config_hash": config_hash,
        "features_run_dir": str((features_root / symbol / TIMEFRAME).relative_to(PROJECT_ROOT)),
        "cgsa_work_dir": str(cgsa_work_dir.relative_to(PROJECT_ROOT)),
        "digest": digest,
        "frame_digest_sha256": frame_hash,
        "fracdiff_column_count": len(fracdiff_cols),
        "d_star_cache": cache,
        "cache_stats": stats,
        "feature_count": int(result.feature_count),
        "metadata": dict(result.metadata),
    }


def _run_label(label: str, sequence: int, *, stamp: str) -> Dict[str, Any]:
    run_id = f"{stamp}-fracdiff-maxlag-golden-{label}-run{sequence}"
    config = _config_for(label)
    window_bars = _fracdiff_window_bars(config)
    pin_context = _pin_fracdiff_max_lag(G2_PIN_MAX_LAG) if label == "G2" else None
    with _capture_dstar_stats() as captured:
        if pin_context is not None:
            with pin_context:
                symbols = {
                    symbol: _run_symbol(
                        label=label,
                        run_id=run_id,
                        symbol=symbol,
                        config=config,
                        window_bars=window_bars,
                        capture_stats=captured,
                    )
                    for symbol in SYMBOLS
                }
        else:
            symbols = {
                symbol: _run_symbol(
                    label=label,
                    run_id=run_id,
                    symbol=symbol,
                    config=config,
                    window_bars=window_bars,
                    capture_stats=captured,
                )
                for symbol in SYMBOLS
            }
    if label == "G2":
        for symbol, info in symbols.items():
            resolved = int(info["d_star_cache"]["resolved_max_lag"])
            if resolved != G2_PIN_MAX_LAG:
                raise RuntimeError(
                    f"G2 pin ineffective for {symbol}: d_star payload max_lag={resolved} != {G2_PIN_MAX_LAG}"
                )
    return {
        "label": label,
        "run_id": run_id,
        "window_bars": int(window_bars),
        "config_source": "tests/feature_engineering/ff_truncation_mr_helpers._fracdiff_mr_config_payload()",
        "pin_method": (
            "preprocessor_instance_fracdiff_config_injection" if label == "G2" else "none"
        ),
        "symbols": symbols,
    }


def _assert_stable_g1(g1_first: Mapping[str, Any], g1_second: Mapping[str, Any]) -> Dict[str, Any]:
    per_symbol: Dict[str, Any] = {}
    stable = True
    for symbol in SYMBOLS:
        left = g1_first["symbols"][symbol]
        right = g1_second["symbols"][symbol]
        same = left["frame_digest_sha256"] == right["frame_digest_sha256"]
        per_symbol[symbol] = {
            "stable": same,
            "first": left["frame_digest_sha256"],
            "second": right["frame_digest_sha256"],
        }
        stable = stable and same
    if not stable:
        raise RuntimeError(f"G1 stability precheck failed: {per_symbol}")
    return {"passed": True, "symbols": per_symbol}


def _compare_g1_g2(g1: Mapping[str, Any], g2: Mapping[str, Any]) -> Dict[str, Any]:
    per_symbol = {
        symbol: compare_golden_digests(
            g1["symbols"][symbol]["digest"],
            g2["symbols"][symbol]["digest"],
        )
        for symbol in SYMBOLS
    }
    passed = all(item["passed"] for item in per_symbol.values())
    if not passed:
        raise RuntimeError(f"G1/G2 digest validation failed: {per_symbol}")
    return {"passed": True, "symbols": per_symbol}


def _write_receipt(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    log_path = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-golden-G1.log"
    _setup_logging(log_path)
    logging.info("Freeze fracdiff max_lag golden start stamp=%s", stamp)

    with tempfile.TemporaryDirectory(prefix="fracdiff-maxlag-golden-") as tmp:
        logging.info("temporary workspace=%s", tmp)
        g1_first = _run_label("G1", 1, stamp=stamp)
        g1_second = _run_label("G1", 2, stamp=stamp)
        g2 = _run_label("G2", 1, stamp=stamp)

    stability = _assert_stable_g1(g1_first, g1_second)
    comparison = _compare_g1_g2(g1_first, g2)
    for symbol in SYMBOLS:
        g1_hash = g1_first["symbols"][symbol]["d_star_cache"]["fracdiff_hash"]
        g2_hash = g2["symbols"][symbol]["d_star_cache"]["fracdiff_hash"]
        if g1_hash == g2_hash:
            raise RuntimeError(
                f"G2 pin ineffective for {symbol}: fracdiff_hash identical to G1 ({g1_hash})"
            )

    common = {
        "created_at_utc": stamp,
        "task_id": "fracdiff-maxlag-b0-codex-20260703",
        "kline_cache": "data_cache/feature_klines/kline_cache.h5",
        "symbols": list(SYMBOLS),
        "timeframe": TIMEFRAME,
        "window_contract": "_fracdiff_window_bars(_fracdiff_mr_config_payload())",
        "stability_precheck": stability,
        "g1_vs_g2_validation": comparison,
    }
    g1_receipt = dict(common)
    g1_receipt.update({"golden": "G1", "runs": [g1_first, g1_second]})
    g2_receipt = dict(common)
    g2_receipt.update({"golden": "G2", "runs": [g2]})

    g1_json = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-golden-G1.json"
    g2_json = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-golden-G2.json"
    _write_receipt(g1_json, g1_receipt)
    _write_receipt(g2_json, g2_receipt)
    g2_log = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-golden-G2.log"
    g2_log.write_text(
        f"G2 receipt shares execution log with {log_path.name}\n"
        f"Validation passed: {comparison['passed']}\n",
        encoding="utf-8",
    )

    logging.info("WROTE %s", g1_json)
    logging.info("WROTE %s", g2_json)
    logging.info("WROTE %s", g2_log)
    logging.info("STATUS: DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
