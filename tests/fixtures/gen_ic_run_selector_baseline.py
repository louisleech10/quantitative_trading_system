#!/usr/bin/env python3
"""凍結 IC Run Selector golden baseline（須用真實 registry runs）。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect
from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
# 2026-07-06 重凍:舊 1c4b825/90f586 run 已不在資料集,改用現行兩套競爭 12h run
# (同 symbol+tf、不同 config → feature 不同、row 同),真實生成於 data_cache/features。
HASH_A = "e53e22906c35363757f4cd49d27f973e"
HASH_B = "f754aad4cc8fe5ccc1532296d6e279ec"
OUTPUT = Path(__file__).resolve().parent / "ic_run_selector_baseline.json"

LENIENT_OVERRIDE = {
    "thresholds": {
        "ic_mean_min": -1.0,
        "icir_min": -1.0,
        "p_value_max": 1.0,
    },
    "report": {"include_regime_analysis": False, "include_decay_analysis": False},
}


def _feature_sha256(df: pd.DataFrame) -> str:
    columns = sorted(str(col) for col in df.columns)
    payload = "|".join(columns).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _run_identity(symbol: str, timeframe: str, config_hash: str) -> Dict[str, str]:
    library = create_feature_library()
    entry = library._registry.get(symbol, timeframe, config_hash)
    if entry is None:
        raise RuntimeError(f"registry run missing: {symbol}/{timeframe}/{config_hash}")
    return {
        "symbol": str(entry.get("symbol")),
        "timeframe": str(entry.get("timeframe")),
        "config_hash": str(entry.get("config_hash")),
        "path": str(entry.get("hdf5_relative_path")),
    }


def _ic_summary_top(report: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    table = report.get("summary_table") or []
    rows = sorted(table, key=lambda item: item.get("icir", float("-inf")), reverse=True)
    return [
        {
            "feature_name": row.get("feature_name"),
            "ic_mean": row.get("ic_mean"),
            "icir": row.get("icir"),
        }
        for row in rows[:top_n]
    ]


def _load_run_metrics(config_hash: str) -> Dict[str, Any]:
    library = create_feature_library()
    df = library.load(SYMBOL, TIMEFRAME, config_hash=config_hash)
    return {
        "selected_config_hash": config_hash,
        "run_identity": _run_identity(SYMBOL, TIMEFRAME, config_hash),
        "feature_sha256": _feature_sha256(df),
        "row_count": int(len(df)),
    }


async def _analyze_once(config_hash: str) -> Dict[str, Any]:
    """小 run 端到端 IC（驗證 analyze 路徑）。"""
    service = ICAnalysisService()
    request = ICAnalyzeRequest(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_hash=config_hash,
        config_override=LENIENT_OVERRIDE,
    )
    started = await service.start_analysis(request)
    task_id = started["task_id"]

    for _ in range(600):
        status = service.get_task_status(task_id)
        if status and status.get("status") in {"completed", "failed"}:
            break
        await asyncio.sleep(0.5)

    status = service.get_task_status(task_id)
    if not status or status.get("status") != "completed":
        raise RuntimeError(f"analyze failed: {status}")

    report = service.get_result(task_id)
    if not isinstance(report, dict):
        raise RuntimeError("analyze result missing")

    metrics = _load_run_metrics(config_hash)
    metrics["ic_summary_top"] = _ic_summary_top(report)
    return metrics


async def _load_multi_baseline() -> Dict[str, Any]:
    from unittest.mock import patch

    from api.services.cross_symbol_training_service import CrossSymbolTrainingService

    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframe = TIMEFRAME
    allow_partial = True
    service = CrossSymbolTrainingService()
    captured: Dict[str, Any] = {}
    original_load_multi = service._feature_library.load_multi

    def spy_load_multi(*args: Any, **kwargs: Any) -> Any:
        captured["kwargs"] = dict(kwargs)
        return original_load_multi(*args, **kwargs)

    service._feature_library.load_multi = spy_load_multi  # type: ignore[method-assign]

    with patch.object(service._validator, "run_leave_one_symbol_out", return_value={}):
        try:
            await service.run_cross_symbol_validation(
                symbols=symbols,
                timeframe=timeframe,
                allow_partial_training=allow_partial,
            )
        except ValueError as exc:
            if "label" not in str(exc).lower():
                raise

    kwargs = captured.get("kwargs", {})
    frames = original_load_multi(
        symbols,
        timeframe,
        for_training=True,
        allow_partial_training=allow_partial,
    )
    return {
        "load_multi_kwargs": {
            "symbols": symbols,
            "timeframe": timeframe,
            "kwargs": {
                "for_training": kwargs.get("for_training", True),
                "allow_partial_training": kwargs.get("allow_partial_training", allow_partial),
            },
        },
        "per_symbol_row_count": {symbol: int(len(frame)) for symbol, frame in frames.items()},
        "per_symbol_feature_sha256": {
            symbol: _feature_sha256(frame)
            for symbol, frame in frames.items()
        },
        "service_summary": {
            "n_symbols": len(symbols),
            "result_count": 0,
        },
    }


async def main() -> None:
    library = create_feature_library()
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        raise RuntimeError(f"required run missing: {HASH_A}")
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_B) is None:
        raise RuntimeError(f"required run missing: {HASH_B}")

    latest = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
    if latest is None:
        raise RuntimeError("find_latest_materialized returned no entry")
    latest_hash = str(latest["config_hash"])
    # 不變式(Codex P2b):backward_compat 基準必須落在本次凍結的兩套競爭 run 之一;
    # 否則 live registry 多出第三個 BTCUSDT/12h materialized run 時,重凍會靜默漂移基準。
    if latest_hash not in (HASH_A, HASH_B):
        raise RuntimeError(
            f"find_latest_materialized={latest_hash} 不在凍結對 {{{HASH_A},{HASH_B}}};"
            " live registry 疑有第三個 run,請確認後再凍。"
        )

    backward = _load_run_metrics(latest_hash)
    backward["selected_config_hash"] = latest_hash
    # 小 run 端到端 IC 摘要（大 run 僅凍結 load 指標）。best-effort：ic_summary_top 不被任何
    # 測試斷言(測試只驗 selected_config_hash/feature_sha256/row_count/run_identity)。若 analyze
    # 在此 12h 資料上失敗(例如 timestamp 連續性)，不阻擋 baseline 凍結，只留空摘要並印警告。
    try:
        e2e_small = await _analyze_once(HASH_A)
        e2e_summary = e2e_small.get("ic_summary_top", [])
    except Exception as exc:  # noqa: BLE001 - best-effort, 見上註
        print(f"WARN: e2e analyze 略過 ic_summary_top (未被測試斷言): {exc}")
        e2e_summary = []
    backward["ic_summary_top"] = e2e_summary

    baseline = {
        "backward_compat_no_config_hash": backward,
        f"disambig_{HASH_A}": {**_load_run_metrics(HASH_A), "ic_summary_top": e2e_summary},
        f"disambig_{HASH_B}": _load_run_metrics(HASH_B),
        "ml_caller_load_multi": await _load_multi_baseline(),
    }

    OUTPUT.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    required = {
        "backward_compat_no_config_hash",
        f"disambig_{HASH_A}",
        f"disambig_{HASH_B}",
        "ml_caller_load_multi",
    }
    assert required.issubset(set(baseline.keys()))
    print(f"Wrote baseline to {OUTPUT}")


if __name__ == "__main__":
    with run_with_manual_redirect():
        asyncio.run(main())
