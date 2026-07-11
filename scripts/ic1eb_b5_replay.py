"""IC 1e+1b B5 共用重放：baseline inputs → 新路徑 service/analyzer。

G-1/G-2 共用；B5 重放必須施加 capture 同款 ``patch_persist_outputs``。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.capture_ic1eb_baseline import (  # noqa: E402
    FINAL_DIR,
    G1_COLUMNS,
    SERIES_KEYS,
    SIG_COLUMNS,
    SYMBOLS,
    _sha_bytes,
    _sha_json,
    five_hash,
    patch_persist_outputs,
    reconstruct_passed,
    summary_to_g1_frame,
)

BASELINE_DIR = FINAL_DIR
MANIFEST_PATH = BASELINE_DIR / "baseline_manifest.json"
INPUTS_DIR = BASELINE_DIR / "inputs"
FAST_RUN = "long_BTCUSDT_12h_f754aad4"
SLOW_RUNS = {
    "long_BTCUSDT_1h_4a8a0b37",
    "long_ETHUSDT_1h_4a8a0b37",
    "long_BCHUSDT_1h_4a8a0b37",
    "long_ETHUSDT_12h_e53e2290",
    "long_BCHUSDT_12h_e53e2290",
    "long_BTCUSDT_12h_e53e2290",
    "long_ETHUSDT_12h_f754aad4",
    "long_BCHUSDT_12h_f754aad4",
    "full_BTCUSDT_12h_e53e2290",
    "event_BTCUSDT_12h_e53e2290",
    "event_lowconf_BTCUSDT_12h_e53e2290",
    "xsec_3sym_12h_e53e2290",
}


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"baseline manifest absent: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def verify_inputs_integrity(manifest: dict[str, Any]) -> None:
    integrity = manifest.get("inputs_integrity") or {}
    for name, meta in integrity.items():
        path = INPUTS_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"baseline input missing: {path}")
        actual = _sha_bytes(path.read_bytes())
        expected = meta["sha256"] if isinstance(meta, dict) else meta
        if actual != expected:
            raise AssertionError(
                f"inputs integrity fail {name}: actual={actual} expected={expected}"
            )


def input_paths_for_longitudinal(req: dict[str, Any]) -> tuple[Path, Path]:
    """縱向 run → 預物化 h5/meta（sha500 命名）。"""
    symbol = req["symbol"]
    timeframe = req["timeframe"]
    config_hash = req["config_hash"]
    tag = f"{symbol}_{timeframe}_{config_hash}_sha500"
    h5 = INPUTS_DIR / f"{tag}.h5"
    meta = INPUTS_DIR / f"{tag}_meta.json"
    if not h5.is_file() or not meta.is_file():
        raise FileNotFoundError(f"longitudinal inputs missing for {tag}")
    return h5, meta


async def run_longitudinal(
    req: dict[str, Any],
    *,
    timeout_seconds: float = 1800.0,
) -> dict[str, Any]:
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService

    h5, meta = input_paths_for_longitudinal(req)
    request = ICAnalyzeRequest(
        features_path=str(h5.resolve()),
        meta_path=str(meta.resolve()),
        symbol=req["symbol"],
        timeframe=req["timeframe"],
        config_hash=req["config_hash"],
        mode="longitudinal",
        config_override=req.get("config_override"),
        event_query=req.get("event_query"),
    )
    service = ICAnalysisService()
    started = await service.start_analysis(request)
    task_id = started["task_id"]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = service.get_task_status(task_id)
        if status and status.get("status") == "completed":
            result = service.get_result(task_id)
            if result is None:
                raise AssertionError(f"completed but no result: {req}")
            return result
        if status and status.get("status") == "failed":
            raise AssertionError(f"IC failed: {status.get('error')}")
        await asyncio.sleep(0.5)
    raise TimeoutError(f"longitudinal timeout: {req}")


def _load_h5_features(path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    import h5py

    with h5py.File(path, "r") as file:
        group = file[f"{symbol}/{timeframe}"]
        matrix = group["features"][:]
        names = [
            n.decode("utf-8") if isinstance(n, (bytes, bytearray)) else str(n)
            for n in group["feature_names"][:]
        ]
        ts = group["timestamps"][:]
        index = pd.to_datetime(ts, unit="s", utc=True).tz_localize(None)
        return pd.DataFrame(matrix, columns=names, index=index)


# data_cache 前置條件缺失才允許 premat fallback；其他例外直接 raise（F1 / review）。
_XSEC_READER_PRECONDITION_ERRORS = (FileNotFoundError, OSError)


def _assert_xsec_selected_columns(
    frame: pd.DataFrame,
    selected: list[str],
    symbol: str,
) -> pd.DataFrame:
    """與 capture.build_xsec_frame 同構：欄集合相等後重排為 selected 順序。"""
    if set(frame.columns) != set(selected):
        raise AssertionError(
            f"xsec column set mismatch for {symbol}: "
            f"have={sorted(frame.columns)[:5]}… need={len(selected)} cols"
        )
    ordered = frame[selected].copy()
    if list(ordered.columns) != list(selected):
        raise AssertionError(f"xsec column order mismatch for {symbol}")
    return ordered


def _xsec_frames_from_reader(
    reader: Any,
    symbols: list[str],
    timeframe: str,
    config_hash: str,
    selected: list[str],
) -> list[pd.DataFrame]:
    """data_cache 路徑；欄集合/順序同 capture.build_xsec_frame。"""
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        frame = reader.load_columns_v2(symbol, timeframe, config_hash, selected)
        row_index = reader.load_row_index_v2(symbol, timeframe, config_hash)
        if row_index is not None:
            frame.index = row_index
        # 缺欄視為 data_cache 前置不足（可 fallback），非邏輯 bug
        if set(frame.columns) != set(selected):
            raise FileNotFoundError(
                f"xsec reader columns incomplete for {symbol}: "
                f"have={len(frame.columns)} need={len(selected)}"
            )
        frame = _assert_xsec_selected_columns(frame, selected, symbol)
        frame["_symbol"] = symbol
        frames.append(frame)
    return frames


def _xsec_frames_from_premat(
    symbols: list[str],
    timeframe: str,
    config_hash: str,
    selected: list[str],
) -> list[pd.DataFrame]:
    """premat long h5 路徑；投影後欄集合+順序與 capture 同構斷言。"""
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        h5, _ = input_paths_for_longitudinal(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "config_hash": config_hash,
            }
        )
        frame = _load_h5_features(h5, symbol, timeframe)
        missing = [c for c in selected if c not in frame.columns]
        if missing:
            raise RuntimeError(
                f"xsec replay cannot materialize columns for {symbol}: "
                f"missing {len(missing)} (e.g. {missing[:3]})"
            )
        # 投影到 selected 後與 capture 同構（集合 + 順序）
        frame = _assert_xsec_selected_columns(frame[selected], selected, symbol)
        frame["_symbol"] = symbol
        frames.append(frame)
    return frames


def run_xsec(
    manifest: dict[str, Any],
    req: dict[str, Any],
) -> dict[str, Any]:
    """xsec：優先用各 symbol 預物化 h5 交集欄 + kline labels（與 capture 同前置）。

    各 long 子集為 per-symbol sha500 排序，與 xsec 交集 sha500 排序可能不同；
    因此以 manifest.subsets['xsec_...'].selected_names 為準，從 data_cache 精準載入
    （與 capture.build_xsec_frame 同欄集合）。若 data_cache 不可用
    （僅 FileNotFoundError/OSError 等前置缺失）則退化為三份 inputs h5
    的欄投影（並斷言欄集合+順序與 capture 同構）。
    """
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_feature_reader, create_ic_analyzer

    symbols = list(req.get("symbols") or SYMBOLS)
    timeframe = req["timeframe"]
    config_hash = req["config_hash"]
    subset_key = f"xsec_3sym_{timeframe}_{config_hash[:8]}"
    selected = list((manifest.get("subsets") or {}).get(subset_key, {}).get("selected_names") or [])
    if not selected:
        raise RuntimeError(f"xsec selected_names missing in manifest subset {subset_key}")

    service = ICAnalysisService()
    reader = create_feature_reader()
    try:
        frames = _xsec_frames_from_reader(
            reader, symbols, timeframe, config_hash, selected
        )
    except _XSEC_READER_PRECONDITION_ERRORS:
        # 僅 data_cache 前置缺失 → premat；其他例外不攔截
        frames = _xsec_frames_from_premat(symbols, timeframe, config_hash, selected)

    cross_df = pd.concat(frames, axis=0).set_index("_symbol", append=True)
    cross_df = service._append_cross_sectional_labels(cross_df, symbols, timeframe)
    analyzer = create_ic_analyzer(None)
    return analyzer.analyze_cross_sectional(
        features=cross_df,
        labels_path=None,
        config_override=None,
        progress_callback=None,
        timeframe=timeframe,
    )


def run_xsec_labels_raise(manifest: dict[str, Any]) -> Exception:
    """F14：單軸 labels_path 仍應 raise；回傳 exception 供 G-3 比對。"""
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_feature_reader, create_ic_analyzer

    raise_meta = (manifest.get("expected_raise_runs") or {}).get("xsec_labels_return5_12h")
    if not raise_meta:
        raise RuntimeError("expected_raise_runs.xsec_labels_return5_12h missing")
    labels_path = INPUTS_DIR / raise_meta["labels_file"]
    if not labels_path.is_file():
        raise FileNotFoundError(labels_path)

    config_hash = "e53e22906c35363757f4cd49d27f973e"
    service = ICAnalysisService()
    reader = create_feature_reader()
    subset_key = "xsec_3sym_12h_e53e2290"
    selected = list((manifest.get("subsets") or {}).get(subset_key, {}).get("selected_names") or [])
    if not selected:
        raise RuntimeError(f"xsec selected_names missing: {subset_key}")
    frames: list[pd.DataFrame] = []
    for symbol in SYMBOLS:
        frame = reader.load_columns_v2(symbol, "12h", config_hash, selected)
        row_index = reader.load_row_index_v2(symbol, "12h", config_hash)
        if row_index is not None:
            frame.index = row_index
        frame = frame[selected].copy()
        frame["_symbol"] = symbol
        frames.append(frame)
    cross_df = pd.concat(frames, axis=0).set_index("_symbol", append=True)
    cross_df = service._append_cross_sectional_labels(cross_df, SYMBOLS, "12h")
    analyzer = create_ic_analyzer(None)
    try:
        analyzer.analyze_cross_sectional(
            features=cross_df,
            labels_path=str(labels_path),
            config_override=None,
            progress_callback=None,
            timeframe="12h",
        )
    except Exception as exc:  # noqa: BLE001 — G-3 預期 raise
        return exc
    raise AssertionError("xsec labels_path single-axis unexpectedly succeeded")


def replay_run(manifest: dict[str, Any], run_name: str) -> dict[str, Any]:
    entry = (manifest.get("runs") or {})[run_name]
    req = entry["request"]
    mode = req.get("mode", "longitudinal")
    if mode == "cross_sectional":
        return run_xsec(manifest, req)
    return asyncio.run(run_longitudinal(req))


def g1_hashes_from_result(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary_table") or []
    g1 = summary_to_g1_frame(summary)
    return {
        "g1_five_hash": five_hash(g1),
        "summary_feature_order_sha256": _sha_json(
            [row.get("feature_name") for row in summary]
        ),
        "series_sha256": {k: _sha_json(result.get(k)) for k in SERIES_KEYS},
    }


def assert_g1_invariant(baseline_entry: dict[str, Any], result: dict[str, Any]) -> None:
    actual = g1_hashes_from_result(result)
    for key in ("index_sha256", "columns_sha256", "dtypes_sha256", "nanmask_sha256", "values_sha256"):
        exp = baseline_entry["g1_five_hash"][key]
        got = actual["g1_five_hash"][key]
        if exp != got:
            raise AssertionError(f"G-1 five_hash.{key} mismatch: {got} != {exp}")
    if actual["summary_feature_order_sha256"] != baseline_entry["summary_feature_order_sha256"]:
        raise AssertionError("G-1 summary_feature_order_sha256 mismatch")
    for sk in SERIES_KEYS:
        exp = baseline_entry["series_sha256"][sk]
        got = actual["series_sha256"][sk]
        if exp != got:
            raise AssertionError(f"G-1 series_sha256.{sk} mismatch")


def removal_reason_for(
    feature: str,
    removed_features: dict[str, list[str]],
    *,
    passed: bool,
) -> str:
    if passed:
        return "passed"
    # 穩定順序：與 stage5 常見門檻序對齊
    order = [
        "ic_mean",
        "icir",
        "p_value",
        "ic_hit_rate",
        "monotonicity",
        "coverage",
        "long_short_spread",
    ]
    for key in order:
        names = removed_features.get(key) or []
        if feature in names:
            return f"removed:{key}"
    for key, names in sorted(removed_features.items()):
        if feature in (names or []):
            return f"removed:{key}"
    return "removed:unknown"


def build_pass_set(result: dict[str, Any]) -> list[str]:
    return reconstruct_passed(result.get("summary_table") or [], result.get("filter_log") or {})


def nan_p_fraction(summary: list[dict[str, Any]], p_field: str = "p_value") -> float:
    if not summary:
        return float("nan")
    n_nan = 0
    for row in summary:
        v = row.get(p_field)
        if v is None:
            n_nan += 1
            continue
        try:
            if not np.isfinite(float(v)):
                n_nan += 1
        except (TypeError, ValueError):
            n_nan += 1
    return n_nan / len(summary)


__all__ = [
    "BASELINE_DIR",
    "FAST_RUN",
    "G1_COLUMNS",
    "INPUTS_DIR",
    "MANIFEST_PATH",
    "SERIES_KEYS",
    "SIG_COLUMNS",
    "SLOW_RUNS",
    "assert_g1_invariant",
    "build_pass_set",
    "five_hash",
    "g1_hashes_from_result",
    "load_manifest",
    "nan_p_fraction",
    "patch_persist_outputs",
    "removal_reason_for",
    "replay_run",
    "reconstruct_passed",
    "run_xsec_labels_raise",
    "summary_to_g1_frame",
    "verify_inputs_integrity",
    "_sha_json",
    "_sha_bytes",
]
