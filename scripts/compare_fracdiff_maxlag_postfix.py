#!/usr/bin/env python3
"""修後對照：§G 條件 1/2 + G2' 交叉驗證（D 增強）。

R   = 修後 code 預設（auto→calibration-derived=50），fresh 空 d* cache
G2' = 修後 code 真 config 路徑顯式 max_lag=50（Task 1.2 schema 落地後才可能）
對照 G1/G2 = handoffs/run_receipts/20260703T042407Z-fracdiff-maxlag-golden-{G1,G2}.json

通過條件（SPEC §G，缺一即 exit 1）：
  1. R vs G2：全部欄（fracdiff+非fracdiff）per-column digest 全同 → 變更純由窗寬造成
  2. R vs G1：非 fracdiff 欄全同 + row/index 同；fracdiff 欄有差（報告列 G1 實際 max_lag 與樣本）
  3. G2' vs R：digest 全同 → 注入等價 + config 路徑修通（D 增強）
  4. R 的 d* payload resolved max_lag == 50（auto 推導正確）
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "freeze_mod", PROJECT_ROOT / "scripts" / "freeze_fracdiff_maxlag_golden.py"
)
freeze_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and freeze_mod)  # type: ignore[arg-type]

from tests.feature_engineering.ff_truncation_mr_helpers import (  # noqa: E402
    _fracdiff_mr_config_payload,
    _fracdiff_window_bars,
)

GOLDEN_STAMP = "20260703T042407Z"
RECEIPT_DIR = PROJECT_ROOT / "handoffs" / "run_receipts"
SYMBOLS = freeze_mod.SYMBOLS


def _load_golden(label: str) -> Dict[str, Any]:
    path = RECEIPT_DIR / f"{GOLDEN_STAMP}-fracdiff-maxlag-golden-{label}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _digest_columns_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """回傳兩 digest 的逐欄比較摘要。"""
    a_cols, b_cols = a["columns"], b["columns"]
    common = sorted(set(a_cols) & set(b_cols))
    only_a = sorted(set(a_cols) - set(b_cols))
    only_b = sorted(set(b_cols) - set(a_cols))
    diff = [
        c
        for c in common
        if a_cols[c]["value_sha256"] != b_cols[c]["value_sha256"]
        or a_cols[c]["nan_mask_sha256"] != b_cols[c]["nan_mask_sha256"]
        or a_cols[c]["dtype"] != b_cols[c]["dtype"]
    ]
    fd_diff = [c for c in diff if "fracdiff" in c.lower()]
    nonfd_diff = [c for c in diff if "fracdiff" not in c.lower()]
    return {
        "common": len(common),
        "only_a": only_a[:10],
        "only_b": only_b[:10],
        "only_count": len(only_a) + len(only_b),
        "row_count_equal": int(a["row_count"]) == int(b["row_count"]),
        "index_hash_equal": a["index_hash"] == b["index_hash"],
        "fracdiff_diff_count": len(fd_diff),
        "non_fracdiff_diff_count": len(nonfd_diff),
        "fracdiff_diff_examples": fd_diff[:20],
        "non_fracdiff_diff_examples": nonfd_diff[:20],
    }


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-postfix-compare.log"
    freeze_mod._setup_logging(log_path)
    logging.info("postfix compare start stamp=%s golden=%s", stamp, GOLDEN_STAMP)

    g1 = _load_golden("G1")
    g2 = _load_golden("G2")

    base_config = copy.deepcopy(_fracdiff_mr_config_payload())
    window_bars = _fracdiff_window_bars(base_config)

    explicit_config = copy.deepcopy(base_config)
    explicit_config["preprocessing"]["fractional_differencing"]["max_lag"] = 50

    with freeze_mod._capture_dstar_stats() as captured:
        r_run = {
            symbol: freeze_mod._run_symbol(
                label="R",
                run_id=f"{stamp}-fracdiff-maxlag-postfix-R",
                symbol=symbol,
                config=base_config,
                window_bars=window_bars,
                capture_stats=captured,
            )
            for symbol in SYMBOLS
        }
    with freeze_mod._capture_dstar_stats() as captured2:
        g2p_run = {
            symbol: freeze_mod._run_symbol(
                label="G2P",
                run_id=f"{stamp}-fracdiff-maxlag-postfix-G2P",
                symbol=symbol,
                config=explicit_config,
                window_bars=window_bars,
                capture_stats=captured2,
            )
            for symbol in SYMBOLS
        }

    failures: list[str] = []
    report: Dict[str, Any] = {
        "created_at_utc": stamp,
        "golden_stamp": GOLDEN_STAMP,
        "window_bars": int(window_bars),
        "symbols": {},
    }
    for symbol in SYMBOLS:
        r = r_run[symbol]
        g2p = g2p_run[symbol]
        g1_sym = g1["runs"][0]["symbols"][symbol]
        g2_sym = g2["runs"][0]["symbols"][symbol]

        # 條件 4：R auto 推導 == 50
        r_max_lag = int(r["d_star_cache"]["resolved_max_lag"])
        if r_max_lag != 50:
            failures.append(f"{symbol}: R resolved_max_lag={r_max_lag} != 50")

        # 條件 1：R vs G2 全欄一致
        c1 = _digest_columns_equal(r["digest"], g2_sym["digest"])
        if (
            c1["only_count"]
            or c1["fracdiff_diff_count"]
            or c1["non_fracdiff_diff_count"]
            or not c1["row_count_equal"]
            or not c1["index_hash_equal"]
        ):
            failures.append(f"{symbol}: 條件1 R vs G2 不一致: {c1}")

        # 條件 2：R vs G1 非 fracdiff 全同、fracdiff 有差
        c2 = _digest_columns_equal(r["digest"], g1_sym["digest"])
        if (
            c2["only_count"]
            or c2["non_fracdiff_diff_count"]
            or not c2["row_count_equal"]
            or not c2["index_hash_equal"]
            or c2["fracdiff_diff_count"] == 0
        ):
            failures.append(f"{symbol}: 條件2 R vs G1 異常: {c2}")

        # 條件 3：G2' vs R 全欄一致（D 增強）
        c3 = _digest_columns_equal(g2p["digest"], r["digest"])
        if c3["only_count"] or c3["fracdiff_diff_count"] or c3["non_fracdiff_diff_count"]:
            failures.append(f"{symbol}: 條件3 G2' vs R 不一致: {c3}")
        g2p_max_lag = int(g2p["d_star_cache"]["resolved_max_lag"])
        if g2p_max_lag != 50:
            failures.append(f"{symbol}: G2' resolved_max_lag={g2p_max_lag} != 50（config 路徑仍不通）")

        report["symbols"][symbol] = {
            "R": {k: r[k] for k in ("d_star_cache", "cache_stats", "frame_digest_sha256")},
            "G2P": {k: g2p[k] for k in ("d_star_cache", "cache_stats", "frame_digest_sha256")},
            "g1_actual_max_lag": g1_sym["d_star_cache"]["resolved_max_lag"],
            "cond1_R_vs_G2": c1,
            "cond2_R_vs_G1": c2,
            "cond3_G2P_vs_R": c3,
        }

    report["failures"] = failures
    report["passed"] = not failures
    out = RECEIPT_DIR / f"{stamp}-fracdiff-maxlag-postfix-compare.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    logging.info("WROTE %s passed=%s failures=%s", out, report["passed"], failures)
    print(f"RECEIPT={out}")
    print(f"PASSED={report['passed']}")
    for f in failures:
        print(f"FAIL: {f}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
