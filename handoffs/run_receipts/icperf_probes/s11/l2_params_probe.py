"""ICPERF SPEC v5.82 S11 診斷探針（唯讀產品碼、不改產品碼）：雙起點預設設定四週期跑到 L2 記憶體計畫點即停，
記錄 L2 計畫之輸入參數（列、欄、最大類別等）與逐成分計畫位元組；L2 大量配置不發生（於 check 前中止）。
用法：venv/bin/python handoffs/run_receipts/icperf_probes/s11/l2_params_probe.py <輸出 JSON> [週期…]（預設 1h 4h 12h 1d）"""
import json
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]  # handoffs/run_receipts/icperf_probes/s11/ 之上四層＝repo 根
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from momentum.FeatureEngineering import memory_budget as mb  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402


class _Stop(Exception):
    pass


def _record(sink, label, candidates):
    rows = []
    for branch, params in candidates:
        comps = mb.estimate(branch, params)
        rows.append({"branch": branch, "params": dict(params),
                     "components": {c.name: c.nbytes * max(c.count, 0) for c in comps},
                     "planned_anon": sum(c.nbytes * max(c.count, 0) for c in comps if c.kind == "anon")})
    sink.append({"label": label, "candidates": rows, "limit_bytes_now": _limit()})
    raise _Stop()


def _limit():
    try:
        return int(mb.available_budget_bytes())  # 若無此函式則略
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    out = Path(sys.argv[1])
    tfs = sys.argv[2:] or ["1h", "4h", "12h", "1d"]
    result = {"schema": "icperf-s11-l2-params/1", "timeframes": {}}
    real_check, real_route = mb.check_estimate, mb.route
    for tf in tfs:
        sink = []

        def check(branch, params, **kw):
            if str(kw.get("label", "")).startswith("Layer 2"):
                _record(sink, kw.get("label"), [(branch, params)])
            return real_check(branch, params, **kw)

        def route(layer, candidates, **kw):
            if str(layer).startswith("Layer 2"):
                _record(sink, layer, candidates)
            return real_route(layer, candidates, **kw)

        t0 = time.time()
        with tempfile.TemporaryDirectory(dir=str(REPO / "runs" / "icperf" / "s11")) as tmp, \
                pytest.MonkeyPatch.context() as mp:
            mp.setattr(mb, "check_estimate", check)
            mp.setattr(mb, "route", route)
            h.prepare_stat_env(mp, Path(tmp))
            source = str(REPO / h.CONTRACT["dual_start"]["timeframes"][tf])
            try:
                h.dual_start_report(Path(tmp), tf, {}, source)
                status = "no_l2_check_reached"
            except _Stop:
                status = "stopped_at_l2_check"
            except Exception as exc:  # noqa: BLE001
                status = f"error:{type(exc).__name__}:{str(exc)[:300]}"
        result["timeframes"][tf] = {"status": status, "seconds": round(time.time() - t0, 1), "records": sink,
                                    "source": source}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(tf, status, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
