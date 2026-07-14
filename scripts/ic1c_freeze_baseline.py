#!/usr/bin/env python3
"""IC1C baseline 凍結腳本(Task 0.1 / G-OLD; Phase1 G-NEW; Phase2 G-NEW2)。

用法:
  python scripts/ic1c_freeze_baseline.py --baseline old
  python scripts/ic1c_freeze_baseline.py --baseline new   # Phase 1 實作
  python scripts/ic1c_freeze_baseline.py --baseline new2  # Phase 2 實作

B0 僅實作 --baseline old;new/new2 佔位 NotImplementedError。
產出固定路徑: handoffs/ic1c_baseline/g_{old,new,new2}.{json,sha256}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "handoffs" / "ic1c_baseline"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "ic_api_real_kline.py"
KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"

# 注入特徵名(TODO Task 0.1 ④ 真 fixture 名)
INJECT_TURNOVER_MISSING = "oc_return"
INJECT_GROSS_IC_MISSING = "hl_range"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _is_non_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return not math.isfinite(float(value))
    return False


def _sanitize_for_strict_json(
    obj: Any,
    path: str = "",
    non_finite_fields: list[str] | None = None,
) -> Any:
    """遞迴將非有限 number 轉 null,並記錄路徑(供 non_finite_fields)。"""
    if non_finite_fields is None:
        non_finite_fields = []

    if isinstance(obj, dict):
        return {
            str(k): _sanitize_for_strict_json(
                v,
                f"{path}.{k}" if path else str(k),
                non_finite_fields,
            )
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [
            _sanitize_for_strict_json(v, f"{path}[{i}]", non_finite_fields)
            for i, v in enumerate(obj)
        ]
    if _is_non_finite_number(obj):
        non_finite_fields.append(path if path else "<root>")
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        fv = float(obj)
        if not math.isfinite(fv):
            non_finite_fields.append(path if path else "<root>")
            return None
        return fv
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _load_fixture_frames() -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """依 tests/fixtures/ic_api_real_kline.py 衍生 features/labels(不跑 full deep pipeline)。"""
    from momentum.factories import create_kline_storage_manager
    from tests.fixtures.ic_api_real_kline import (
        FEATURE_NAMES,
        SYMBOL,
        TIMEFRAME,
        build_real_kline_frames,
    )

    if not KLINE_CACHE.is_file():
        raise FileNotFoundError(f"requires_kline: missing {KLINE_CACHE}")

    storage = create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent))
    kline = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    if kline is None or getattr(kline, "empty", True):
        raise RuntimeError(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME}")

    features, labels = build_real_kline_frames(kline)
    return features, labels, list(FEATURE_NAMES)


def _spearman_ic_mean(feature: pd.Series, labels: pd.Series) -> float:
    aligned = pd.concat(
        [feature.rename("f"), labels.rename("y")],
        axis=1,
    ).dropna()
    if len(aligned) < 2:
        return float("nan")
    corr = spearmanr(
        aligned["f"].to_numpy(dtype=np.float64),
        aligned["y"].to_numpy(dtype=np.float64),
    ).correlation
    if corr is None or not np.isfinite(corr):
        return float("nan")
    return float(corr)


def _build_summary_and_turnover(
    features: pd.DataFrame,
    labels: pd.Series,
    feature_names: list[str],
) -> tuple[dict[str, dict], dict[str, float]]:
    """排序後逐 feat 建 summary(ic_mean=spearman)+turnover_data(quantile_turnover)。"""
    from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer

    ta = TurnoverAnalyzer({})
    # 確定性:feature 名排序
    ordered = sorted(feature_names)
    summary: dict[str, dict] = {}
    turnover_data: dict[str, float] = {}
    for name in ordered:
        series = features[name]
        summary[name] = {"ic_mean": _spearman_ic_mean(series, labels)}
        turnover_data[name] = float(ta.compute_quantile_turnover(series))
    return summary, turnover_data


def _inject_skipped(
    summary: dict[str, dict],
    turnover_data: dict[str, float],
) -> None:
    """具名 skipped 注入(真 fixture 特徵名)。"""
    if INJECT_TURNOVER_MISSING not in summary:
        raise KeyError(
            f"inject target missing from summary: {INJECT_TURNOVER_MISSING!r}"
        )
    if INJECT_GROSS_IC_MISSING not in summary:
        raise KeyError(
            f"inject target missing from summary: {INJECT_GROSS_IC_MISSING!r}"
        )
    turnover_data.pop(INJECT_TURNOVER_MISSING, None)
    summary[INJECT_GROSS_IC_MISSING]["ic_mean"] = float("nan")


def _default_net_ic_config() -> dict[str, Any]:
    """現行 default config(對齊 NetICAnalysisConfig / ic_config.yaml 現值)。"""
    return {
        "enabled": True,
        "default_cost_bps": 5.0,
        "slippage_bps": 2.0,
        "cost_scenarios": [1, 3, 5, 10, 20],
        "participation_rate": 0.01,
    }


def freeze_old() -> Path:
    """Task 0.1 G-OLD:fixture 衍生 → batch_analyze → g_old.{json,sha256}。"""
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer

    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"fixture missing: {FIXTURE_PATH}")

    features, labels, feature_names = _load_fixture_frames()
    summary, turnover_data = _build_summary_and_turnover(
        features, labels, feature_names
    )
    _inject_skipped(summary, turnover_data)

    analyzer = NetICAnalyzer(_default_net_ic_config())
    raw_result = analyzer.batch_analyze(summary, turnover_data)

    non_finite_fields: list[str] = []
    sanitized = _sanitize_for_strict_json(
        raw_result, path="result", non_finite_fields=non_finite_fields
    )
    # 路徑記相對 result 內容更易讀
    cleaned_paths = [
        p[len("result.") :] if p.startswith("result.") else p
        for p in non_finite_fields
    ]

    payload: dict[str, Any] = {
        "fixture_sha256": _sha256_file(FIXTURE_PATH),
        "git_head": _git_head(),
        "generated_by": "ic1c_freeze_baseline --baseline old",
        "non_finite_fields": sorted(cleaned_paths),
        "feature_names_input": sorted(feature_names),
        "injected_skips": {
            "turnover_missing": INJECT_TURNOVER_MISSING,
            "gross_ic_missing": INJECT_GROSS_IC_MISSING,
        },
        "result": sanitized,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "g_old.json"
    out_sha = OUT_DIR / "g_old.sha256"

    text = json.dumps(payload, sort_keys=True, allow_nan=False, ensure_ascii=False)
    # 尾端換行固定,避免跨工具 hash 漂移
    if not text.endswith("\n"):
        text = text + "\n"
    out_json.write_text(text, encoding="utf-8")

    digest = hashlib.sha256(out_json.read_bytes()).hexdigest()
    # shasum -c 格式:相對 repo root 路徑(執行端於 root 驗)
    rel = out_json.relative_to(REPO_ROOT).as_posix()
    out_sha.write_text(f"{digest}  {rel}\n", encoding="utf-8")

    print(f"wrote {rel}")
    print(f"sha256={digest}")
    print(f"features={len((sanitized or {}).get('features') or {})}")
    print(f"non_finite_fields={len(cleaned_paths)}")
    return out_json


def freeze_new() -> None:
    raise NotImplementedError(
        "G-NEW freeze is Phase 1 (B1); implement after NetICAnalyzer B-strict rewrite"
    )


def freeze_new2() -> None:
    raise NotImplementedError(
        "G-NEW2 freeze is Phase 2 (B2); implement after API wiring"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IC1C baseline freeze")
    parser.add_argument(
        "--baseline",
        required=True,
        choices=("old", "new", "new2"),
        help="which baseline to freeze",
    )
    args = parser.parse_args(argv)

    if args.baseline == "old":
        freeze_old()
        return 0
    if args.baseline == "new":
        freeze_new()
        return 1
    if args.baseline == "new2":
        freeze_new2()
        return 1
    parser.error(f"unknown baseline: {args.baseline}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
