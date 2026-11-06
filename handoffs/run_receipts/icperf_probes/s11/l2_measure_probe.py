"""ICPERF SPEC v5.82 S11 診斷：雙起點預設設定（與 ffstat_helpers.dual_start_report 同 body：單一原生週期、
fracdiff／ADF 關）於真實 kline 刪前段列使 L2 計畫落於本機預算內，照常通過預算檢查而實跑；以 ICFIRSTALIGN 之
SegmentTracker 記逐 check 段之「區間峰值 − check 當下值」（phys_footprint，與預算量同一量）對計畫。
每次呼叫跑一個 (週期, 刪列數)，於獨立行程中執行（區間峰值與配置器狀態互不污染）。不改產品碼。
用法：venv/bin/python handoffs/run_receipts/icperf_probes/s11/l2_measure_probe.py <週期> <刪前段列數> <segments.jsonl>"""
import json
import logging
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]  # handoffs/run_receipts/icperf_probes/s11/ 之上四層＝repo 根
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "handoffs" / "run_receipts" / "icfirstalign_probes"))

import h5py  # noqa: E402
import pytest  # noqa: E402

from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering import memory_budget as mb  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
from segment_tracker import SegmentTracker  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

SYMBOL = "BTCUSDT"


def main() -> int:
    tf, drop, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    logging.getLogger("momentum").setLevel(logging.WARNING)
    source = REPO / h.CONTRACT["dual_start"]["timeframes"][tf]
    handle = open(out, "a", encoding="utf-8")

    def emit(seg):
        handle.write(json.dumps({"tf": tf, "drop": drop, **seg.as_dict()}, ensure_ascii=False) + "\n")
        handle.flush()

    body = {"timeframes": {"primary": tf, "training": [tf]},
            "preprocessing": {"fractional_differencing": {"enabled": False}, "adf_differencing": {"enabled": False}}}
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(dir=str(REPO / "runs" / "icperf" / "s11")) as tmp, \
            pytest.MonkeyPatch.context() as mp:
        tmp = Path(tmp)
        h.prepare_stat_env(mp, tmp)
        kdir = tmp / "k"
        kdir.mkdir()
        shutil.copy2(source / "kline_cache.h5", kdir / "kline_cache.h5")
        with h5py.File(kdir / "kline_cache.h5", "r+") as f:
            group = f[SYMBOL][tf]
            arr = group["data"][()]
            attrs = dict(group["data"].attrs)
            rows = int(arr.shape[0]) - drop
            if drop:
                del group["data"]
                ds = group.create_dataset("data", data=arr[drop:], maxshape=(None,), chunks=True)
                for key, value in attrs.items():
                    ds.attrs[key] = value
        handle.write(json.dumps({"tf": tf, "drop": drop, "kline_rows": rows}) + "\n")
        tracker = SegmentTracker(mb, on_segment=emit).install(mp)
        factory = create_feature_factory(cache_dir=str(kdir), validate_continuity=False)
        factory._storage = FeatureStorage(str(tmp / "features"))
        status = "ok"
        try:
            factory.generate_features(SYMBOL, tf, config_override=body, force_regenerate=True)
        except Exception as exc:  # noqa: BLE001 —— 診斷探針：記錄失敗原因（含預算拒絕），不吞為成功
            status = f"{type(exc).__name__}:{str(exc)[:300]}"
        tracker.finish()
    handle.write(json.dumps({"tf": tf, "drop": drop, "status": status, "elapsed_s": round(time.monotonic() - t0, 1)},
                            ensure_ascii=False) + "\n")
    handle.close()
    print(tf, drop, status, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
