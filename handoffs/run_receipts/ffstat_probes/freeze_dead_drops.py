"""FF-STAT Task 2.3 ⑦（v49）：改前原始碼之 L3 死欄剔除紀錄（欄集合差異 `warmup_restored` 原因之證據）。

必於 b4 動工前原始碼（5a148b8e）之獨立 git worktree 內執行（不動主工作區 tracked 檔）：
  git worktree add <tmp>/ffstat-prebase 5a148b8e
  cd <tmp>/ffstat-prebase && <主 repo>/venv/bin/python <主 repo>/handoffs/run_receipts/ffstat_probes/freeze_dead_drops.py \
      --kline-dir <主 repo>/data_cache/feature_klines --out <主 repo>/tests/_golden/ffstat/baseline_dead_drops.json
設定與窗：同 `tests/_golden/ffstat/baseline.json`（`ffstat_helpers.stat_payload()`、BTCUSDT 1h、`WINDOW`）。
攔截改前 `RollingAggregator._variance_filter`（L3 唯一死欄判定入口），逐欄記被剔之列數、NaN 率（改前分母＝全列數）、
開頭非有限值列數、有效樣本數、是否含 inf、是否常數（全無有限值者記為常數）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _drop_call_sites(source: Path) -> set:
    """改前 `rolling_aggregator.py` 內對 L3 剔除函式（`_variance_filter`、`_batch_variance_filter`、
    `_should_keep_output`）之呼叫點：{(所在函式名, 被呼叫函式名)}（AST 靜態列舉）。"""
    import ast

    tree = ast.parse(source.read_text(encoding="utf-8"))
    targets = {"_variance_filter", "_batch_variance_filter", "_should_keep_output"}
    sites = set()
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in targets:
                sites.add((func.name, node.func.attr))
    return sites


# 改前 5a148b8e 之已知剔除入口（攔截：兩處直接 `_variance_filter` 以完整欄名記錄、批次路徑經 `_batch_variance_filter`
# 以呼叫端 col_name／window 還原欄名、批次內委派之 `_variance_filter` 以彙總名呼叫而略過；`_should_keep_output` 無呼叫點）
EXPECTED_CALL_SITES = {
    ("_compute_all_streaming", "_variance_filter"),
    ("_compute_all_streaming_numba_single_window", "_variance_filter"),
    ("_compute_all_streaming_numba_multi_window", "_batch_variance_filter"),
    ("_batch_variance_filter", "_variance_filter"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kline-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, os.getcwd())
    import pytest

    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
    from tests.feature_engineering import ffstat_helpers as h

    assert Path(h.__file__).resolve().is_relative_to(Path(os.getcwd()).resolve()), "須於改前 worktree 內執行"
    import inspect

    call_sites = _drop_call_sites(Path(inspect.getsourcefile(RollingAggregator)))
    # 審查 r33 codex P2-06：攔截點（`_variance_filter`、`_batch_variance_filter`、低基數閘）須涵蓋改前 L3 全部剔除入口；
    # 呼叫點集合與下列已知集合不同 ⇒ 改前原始碼另有剔除入口未被攔截 ⇒ fail-closed
    assert call_sites == EXPECTED_CALL_SITES, sorted(set(call_sites) ^ set(EXPECTED_CALL_SITES))

    dropped = {}
    original = RollingAggregator._variance_filter
    original_batch = RollingAggregator._batch_variance_filter

    def record(name: str, values: np.ndarray, **extra: Any) -> None:
        values = np.asarray(values, dtype=np.float64)
        is_finite = np.isfinite(values)
        finite = values[is_finite]
        dropped[name] = {
            **extra,
            "rows": int(values.size),
            # 開頭連續非有限值之列數（全無有限值＝rows）：判「改前因開頭過長被剔」之依據
            "leading_nan": int(np.argmax(is_finite)) if is_finite.any() else int(values.size),
            "nan_rate": float(np.isnan(values).mean()) if values.size else 1.0,
            "valid": int(finite.size),
            "has_inf": bool(np.isinf(values).any()),
            "constant": bool(finite.size == 0 or np.nanstd(finite) == 0),
        }

    def spy(df, nan_threshold: float = 0.9):
        # 直接以完整欄名呼叫者（非批次路徑）；批次路徑之欄名為彙總名（無 `_W`），由 spy_batch 記
        out = original(df, nan_threshold=nan_threshold)
        for column in df.columns.difference(out.columns):
            if "_W" in str(column):
                record(str(column), df[column].to_numpy())
        return out

    def spy_batch(self, window_results, nan_threshold: float = 0.9):
        # 改前批次路徑（numba multi-window）：彙總名 → 完整欄名須取呼叫端迴圈變數 col_name／window
        out = original_batch(self, window_results, nan_threshold=nan_threshold)
        caller = inspect.currentframe().f_back.f_locals
        col_name, window = caller["col_name"], caller["window"]
        for agg_name in set(window_results) - set(out):
            record(f"{col_name}_{self._format_agg_label(agg_name)}_W{window}", window_results[agg_name])
        if caller.get("col_skip_higher_moment"):
            # 改前 Layer 4 低基數閘：skew／kurt 未計算即剔（不經過濾器）；記其輸入欄之統計並標記，
            # 收據只於輸入全無有限值時視為開頭過長所致
            for agg_name in sorted(set(caller["valid_aggs"]) & set(self._HIGHER_MOMENT_AGGS)):
                record(f"{col_name}_{self._format_agg_label(agg_name)}_W{window}", caller["values"],
                       low_cardinality_skip=True)
        return out

    mp = pytest.MonkeyPatch()
    work = Path(tempfile.mkdtemp(prefix="ffstat_deaddrops_"))
    try:
        mp.setattr(RollingAggregator, "_variance_filter", staticmethod(spy))
        mp.setattr(RollingAggregator, "_batch_variance_filter", spy_batch)
        h.prepare_stat_env(mp, work)
        _root, _factory, result = h.run_stat(work, h.stat_payload(), kline_dir=args.kline_dir)
        status = result.metadata.get("quality_status")
    finally:
        mp.undo()
    head = os.popen("git rev-parse HEAD").read().strip()
    doc = {"commit": head, "symbol": h.SYMBOL, "timeframe": h.PRIMARY_TF, "window": list(h.WINDOW),
           "payload": "tests/feature_engineering/ffstat_helpers.stat_payload()", "quality_status": status,
           "l3_dead_drops": dict(sorted(dropped.items()))}
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("dropped", len(dropped), "status", status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
