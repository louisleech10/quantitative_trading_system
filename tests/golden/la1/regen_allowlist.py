#!/usr/bin/env python3
"""LA-1 歸因 allowlist 產生器（ICPERF SPEC v5.43 Task 0.5 (d)）。

以測試同一組 builder 產生 live diffs，列＝(path, index, old, new, class)：
  - BTC／ETH 各自：五路徑 recursive diff（`test_b4_golden_rebaseline._build_live_five_path_artifact` ＋
    `_five_path_recursive_diffs`）＋P1-3-obs（`_build_p13_obs_diffs`；樣本外請求須 `ok_oos`）——同
    `test_b4_modified_path_attribution_unexpected_zero`、`test_b4_cross_symbol_eth_independent`；
  - kmeans PIT（`tests/momentum/test_la1_lookahead.py` `_assert_kmeans_pit`）：BTC 全長 `RegimeDetector.detect` 之
    xgboost_phases 標籤（`_build_phase_attribution_diffs`）與 kmeans grouped IC（`_build_regime_kmeans_attribution_diffs`，
    取 BTC 五路徑同一次 kmeans 分析之報告）。
五路徑與 kmeans PIT 之列，其 old 須等於該 symbol B0 baseline 之葉值（`attribution_validator.values_equal`），否則 fail
（B0 legacy 基準不重產）；P1-3-obs 之 old／new 為同次 fallback 與樣本外報告之 report-root 值，不對 B0。
輸出：依 class 之列數增減、(path, index) 集合之新增／消失（重錄審查面）；`--write` 寫回 allowlist（rows 以外之鍵原樣保留），
並印新 rows 指紋與列數，供同步 `test_attribution_validator.py` 之 `FROZEN_ALLOWLIST_*`。

用法（真實資料，重型；經共用監看背景執行）：
  venv/bin/python -m tests.golden.la1.regen_allowlist [--write] [--summary-out handoffs/run_receipts/<日期>-la1-allowlist-regen.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

B0_CHECKED_PREFIXES = ("regime_rule.", "regime_kmeans.", "xgboost_phases.", "long_short.", "fallback.")
ROW_KEYS = ("path", "index", "old", "new", "class")


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False, allow_nan=True, separators=(",", ":"))


def _row(d: Dict[str, Any]) -> Dict[str, Any]:
    missing = [k for k in ROW_KEYS if k not in d]
    if missing:
        raise RuntimeError(f"diff 列缺鍵 {missing}：{d}")
    return {k: d[k] for k in ROW_KEYS}


def _check_old_is_b0(rows: Iterable[Dict[str, Any]], baseline: Dict[str, Any], label: str) -> None:
    from tests.golden.la1 import test_b4_golden_rebaseline as rb
    from tests.golden.la1.attribution_validator import baseline_parent_has_skipped, values_equal

    bad: List[str] = []
    for r in rows:
        if not str(r["path"]).startswith(B0_CHECKED_PREFIXES):
            continue
        found, leaf = rb._resolve_baseline_leaf(baseline, str(r["path"]))
        if not found and r["old"] is None and baseline_parent_has_skipped(baseline, str(r["path"])):
            # B0 該特徵 skipped、live 轉為結果 ⇒ 驗證器之 added_key 列（雙錨：B0 parent skipped＋live path；
            # attribution_validator.validate_allowlist_paths_against_baseline）
            r["added_key"] = True
            continue
        if not found or not values_equal(leaf, r["old"]):
            bad.append(f"{r['path']}（index {r['index']}）old={r['old']!r} B0={'缺' if not found else repr(leaf)}")
    if bad:
        raise RuntimeError(f"{label}：{len(bad)} 列 old 不等於 B0 葉值（B0 不重產，不得以 live 值充 old）：{bad[:5]}")


def collect_live_rows() -> List[Dict[str, Any]]:
    """BTC／ETH 五路徑＋P1-3-obs、BTC kmeans PIT 之全部 live diff 列（去重前）。"""
    from momentum.factories import create_regime_detector
    from tests.golden.la1 import test_b4_golden_rebaseline as rb
    from tests.momentum import test_la1_lookahead as la

    rows: List[Dict[str, Any]] = []
    btc_live: Dict[str, Any] = {}
    for symbol, base_path in (("BTCUSDT", rb.BTC_BASELINE_PATH), ("ETHUSDT", rb.ETH_BASELINE_PATH)):
        baseline = rb._load_baseline(base_path)
        run, h5, meta = rb._run_for_symbol(symbol)
        symbol_tf = f"{run['symbol']}/{run['timeframe']}"
        raw = rb._read_kline(run["symbol"], run["timeframe"])
        live = rb._build_live_five_path_artifact(run["symbol"], run["timeframe"], h5, meta, raw)
        five = [_row(d) for d in rb._five_path_recursive_diffs(baseline, live, symbol_tf=symbol_tf)]
        _check_old_is_b0(five, baseline, f"{symbol_tf} 五路徑")
        _orch_ok, report_ok = rb._run_analyze(h5, meta, rb._regime_off_config())
        if report_ok.get("analysis_status") != "ok_oos":
            raise RuntimeError(f"{symbol_tf}：樣本外請求 analysis_status={report_ok.get('analysis_status')!r} != ok_oos")
        rows += five + [_row(d) for d in rb._build_p13_obs_diffs(live["report_fb"], report_ok)]
        if symbol == "BTCUSDT":
            btc_live = {"baseline": baseline, "raw": raw, "live": live}

    baseline, raw, live = btc_live["baseline"], btc_live["raw"], btc_live["live"]
    det = create_regime_detector(n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=50)
    full = det.detect(raw["close"].astype(float), raw["volume"].astype(float))
    xgb = la._build_phase_attribution_diffs([str(x) for x in full.labels], baseline.get("xgboost_phases") or {},
                                            path_prefix="xgboost_phases")
    by_regime_km = (live["report_km"].get("grouped_ic") or {}).get("by_regime") or {}
    km = la._build_regime_kmeans_attribution_diffs(baseline.get("regime_kmeans") or {},
                                                   rb._summarize_by_regime(by_regime_km))
    pit = [_row(d) for d in xgb + km]
    _check_old_is_b0(pit, baseline, "BTCUSDT/1h kmeans PIT")
    return rows + pit


def dedupe(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """以 (path, index, old, new, class) 之正準 JSON 去重；依 (class, path, index) 排序。"""
    seen: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for r in rows:
        seen.setdefault(tuple(_canon(r[k]) for k in ROW_KEYS), r)
    return sorted(seen.values(), key=lambda r: (str(r["class"]), str(r["path"]), _canon(r["index"])))


def summarize(old_rows: List[Dict[str, Any]], new_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """重錄審查面：依 class 之列數（前→後）、(path, index) 集合之新增／消失、同 (path, index) 而 new 值改變之列數。"""
    def pi(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
        return {(str(r["path"]), _canon(r["index"])): r for r in rows}

    a, b = pi(old_rows), pi(new_rows)
    ca, cb = Counter(str(r["class"]) for r in old_rows), Counter(str(r["class"]) for r in new_rows)
    return {
        "by_class": {c: {"before": ca.get(c, 0), "after": cb.get(c, 0)} for c in sorted(set(ca) | set(cb))},
        "added": sorted(f"{p} [{i}]" for p, i in set(b) - set(a)),
        "removed": sorted(f"{p} [{i}]" for p, i in set(a) - set(b)),
        "new_value_changed": sum(1 for k in set(a) & set(b) if _canon(a[k]["new"]) != _canon(b[k]["new"])),
        "rows_before": len(old_rows), "rows_after": len(new_rows),
    }


def main(argv: List[str]) -> int:
    from tests.golden.la1.attribution_validator import allowlist_rows_fingerprint, load_allowlist
    from tests.golden.la1.test_b4_golden_rebaseline import ALLOWLIST_PATH

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="寫回 attribution_allowlist.json（預設只印審查摘要）")
    ap.add_argument("--summary-out", type=Path, default=None, help="審查摘要 JSON 輸出路徑")
    args = ap.parse_args(argv)

    current = load_allowlist(ALLOWLIST_PATH)
    new_rows = dedupe(collect_live_rows())
    out = {**current, "rows": new_rows}
    summary = {**summarize(list(current.get("rows") or []), new_rows),
               "rows_sha256": allowlist_rows_fingerprint(out), "row_count": len(new_rows)}
    text = json.dumps(summary, ensure_ascii=False, indent=1)
    print(text)
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(text + "\n", encoding="utf-8")
    if args.write:
        ALLOWLIST_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
