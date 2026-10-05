"""ICFIRSTALIGN 乙 Task 4.2 收據：子行程之 runtime／import／JIT 上界與 resource tracker 啟動峰值（v25 任務峰值 E 之常數項）。

量測（macOS，`proc_pid_rusage` RUSAGE_INFO_V4 之行程生涯最大 phys_footprint＝第 28 個 uint64 欄，見
handoffs/run_receipts/20261004-icfirstalign-interval-peak.json）：
- 「空 worker」：spawn 子行程只 import Feature Factory 套件並做 numba warmup 後之生涯峰值（runtime／import／JIT）；
- 「真 worker」：spawn 子行程執行 `_tf_worker_entry`（S2m 之 4h，精簡 L1）與 `_worker_entry`（S2 BTCUSDT 全史）之生涯峰值，
  另記該任務資料部分之估算（`estimate_generation_envelope` 扣除常數項）以核「常數項＋資料估算 ≥ 實測峰值」；
- resource tracker：spawn pool 建立後 tracker 行程之生涯峰值。
常數＝實測峰值 × 1.5（安全係數）後上取整至 MiB，寫入 `memory_budget.WORKER_RUNTIME_ENVELOPE_BYTES`／
`AUX_TRACKER_STARTUP_ENVELOPE_BYTES`（本收據為其出處）。真實 kline、精簡設定（峰值遠低於 1 GB）。
用法：env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/runtime_envelope_probe.py <out.json>
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
import time
from pathlib import Path

MIB = 1 << 20


class _V4(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]


def lifetime_peak(pid: int) -> int:
    info = _V4()
    rc = ctypes.CDLL("/usr/lib/libproc.dylib").proc_pid_rusage(int(pid), 4, ctypes.byref(info))
    if rc != 0:
        raise OSError(f"proc_pid_rusage v4 rc={rc}")
    return int(info.f28)


def _empty_worker() -> dict:
    import momentum.FeatureEngineering.feature_factory as ff  # noqa: F401 — 套件 import 成本

    ff._warmup_numba_functions()
    return {"pid": os.getpid(), "lifetime_peak": lifetime_peak(os.getpid())}


def _tf_worker(root: str, kline_dir: str) -> dict:
    sys.path.insert(0, os.getcwd())
    import pytest

    from momentum.FeatureEngineering.timeframe.multi_tf_generator import _tf_worker_entry
    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        h.isolated(mp, Path(root))
        payload = h.make_factory(Path(root) / "features")._resolve_config(h.s2_payload(["12h", "4h"])).model_dump(by_alias=True)
        result = _tf_worker_entry(h.SYMBOL, "4h", payload, h.S2_WINDOW[0], h.S2_WINDOW[1], cache_dir=kline_dir)
        return {"pid": os.getpid(), "lifetime_peak": lifetime_peak(os.getpid()), "error": result.get("error")}
    finally:
        mp.undo()


def _symbol_worker(root: str, kline_dir: str) -> dict:
    sys.path.insert(0, os.getcwd())
    import pytest

    from momentum.FeatureEngineering.feature_factory import _worker_entry
    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        h.isolated(mp, Path(root))
        mp.delenv("FFACT_CGSA_WORK_DIR", raising=False)
        meta = _worker_entry(h.SYMBOL, h.s2_payload(), kline_dir, None)
        return {"pid": os.getpid(), "lifetime_peak": lifetime_peak(os.getpid()), "config_hash": meta.get("config_hash")}
    finally:
        mp.undo()


def _run_in_spawn(fn, *args) -> dict:
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn")) as pool:
        return pool.submit(fn, *args).result()


def _tracker_peak() -> dict:
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import resource_tracker

    with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn")) as pool:
        pool.submit(os.getpid).result()
        pid = getattr(resource_tracker._resource_tracker, "_pid", None)
        peak = 0
        for _ in range(20):
            peak = max(peak, lifetime_peak(int(pid)))
            time.sleep(0.05)
    return {"pid": pid, "lifetime_peak": peak}


def main() -> int:
    sys.path.insert(0, os.getcwd())
    out_path = Path(sys.argv[1])
    from momentum.FeatureEngineering import memory_budget as mb
    from tests.feature_engineering import icfirstalign_helpers as h

    started = time.time()
    tracker = _tracker_peak()
    empty = _run_in_spawn(_empty_worker)
    with tempfile.TemporaryDirectory(prefix="icfa_envelope_") as tmp:
        tf_worker = _run_in_spawn(_tf_worker, str(Path(tmp) / "tf"), str(h.KLINE_DIR))
        sym_worker = _run_in_spawn(_symbol_worker, str(Path(tmp) / "sym"), str(h.KLINE_DIR))
        factory = h.make_factory(Path(tmp) / "est")
        cfg_m = factory._resolve_config(h.s2_payload(["12h", "4h"]))
        cfg_s = factory._resolve_config(h.s2_payload())
        tf_rows = len(factory._layer0_data_ingestion(h.SYMBOL, "4h", cfg_m, start_date=None, end_date=h.S2_WINDOW[1]))
        sym_env = factory._estimate_symbol_envelope(h.SYMBOL, cfg_s)
        tf_env = factory.estimate_generation_envelope(cfg_m, tf_rows, 6)
    runtime_peak = max(empty["lifetime_peak"], tf_worker["lifetime_peak"], sym_worker["lifetime_peak"])
    runtime_const = -(-int(runtime_peak * 1.5) // MIB) * MIB
    tracker_const = -(-int(tracker["lifetime_peak"] * 1.5) // MIB) * MIB
    data_tf = tf_env - mb.WORKER_RUNTIME_ENVELOPE_BYTES
    data_sym = (sym_env or 0) - mb.WORKER_RUNTIME_ENVELOPE_BYTES
    receipt = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/runtime_envelope_probe.py "
                   + str(out_path),
        "platform": sys.platform, "physical_bytes": mb.physical_memory_bytes(),
        "measurements": {"empty_worker": empty, "tf_worker_S2m_4h": tf_worker, "symbol_worker_S2": sym_worker,
                         "resource_tracker": tracker},
        "runtime_peak_bytes": runtime_peak, "worker_runtime_envelope_bytes": runtime_const,
        "aux_tracker_startup_envelope_bytes": tracker_const,
        "code_constants_at_run": {"WORKER_RUNTIME_ENVELOPE_BYTES": mb.WORKER_RUNTIME_ENVELOPE_BYTES,
                                  "AUX_TRACKER_STARTUP_ENVELOPE_BYTES": mb.AUX_TRACKER_STARTUP_ENVELOPE_BYTES},
        "envelope_check": {
            "tf_worker": {"data_estimate_bytes": data_tf, "estimate_with_new_const": runtime_const + data_tf,
                          "measured_peak": tf_worker["lifetime_peak"],
                          "covers": runtime_const + data_tf >= tf_worker["lifetime_peak"]},
            "symbol_worker": {"data_estimate_bytes": data_sym, "estimate_with_new_const": runtime_const + data_sym,
                              "measured_peak": sym_worker["lifetime_peak"],
                              "covers": runtime_const + data_sym >= sym_worker["lifetime_peak"]},
        },
        "honest_bounds": "精簡 L1（EMA8／SMA13）；runtime 常數以三種 spawn worker 之生涯峰值最大者 × 1.5；完整 L1 之資料項由分支表估算，"
                         "其不低估另由 Task 4.2 (ii) 逐分支收據與 Task 4.3 序列核對",
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("runtime_peak_bytes", "worker_runtime_envelope_bytes",
                                              "aux_tracker_startup_envelope_bytes", "envelope_check")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
