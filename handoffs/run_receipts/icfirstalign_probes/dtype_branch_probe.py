"""ICFIRSTALIGN 乙 SPEC v2 §A 收據：①`concat_with_memmap` 之 dtype 規模分支對縮尾後數值之影響；②macOS 行程內
resident／footprint 取樣 API。

①真實 BTCUSDT 12h 尾 800 根 close 與單棒 return 兩欄；只把 `threshold_bytes` 設 1 以觸發既有 float32 分支（不改生產門檻）；
比對「float32 分支後縮尾」vs「float64 逐欄縮尾」之有限值差異數與首個有限值列，縮尾開（預設 WinsorConfig）。
縮尾關之對照＝分支輸出本身之差異（float32 vs float64）。
②`proc_pid_rusage(getpid(), RUSAGE_INFO_V0)`：rusage_info_v0＝16 byte uuid＋12 個 uint64，resident 為第 7、phys_footprint 為第 8 個。
用法：env PYTHONPATH=. venv/bin/python <本檔>（峰值 < 300 MB，不跑工廠生成）。
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import time


def _rusage() -> dict:
    class RusageInfoV0(ctypes.Structure):
        _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(12)]

    lib = ctypes.CDLL("/usr/lib/libproc.dylib")
    info = RusageInfoV0()
    t0 = time.perf_counter()
    rc = lib.proc_pid_rusage(os.getpid(), 0, ctypes.byref(info))
    ms = (time.perf_counter() - t0) * 1000
    return {"rc": int(rc), "resident_bytes": int(info.f6), "phys_footprint_bytes": int(info.f7), "call_ms": round(ms, 4)}


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.feature_config import WinsorConfig
    from momentum.FeatureEngineering.memmap_utils import concat_with_memmap
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        rec = f["/BTCUSDT/12h/data"][-800:]
    idx = pd.DatetimeIndex(pd.to_datetime(rec["timestamp"], unit="s", utc=True))
    a = pd.DataFrame({"close": np.asarray(rec["close"], dtype=np.float64)}, index=idx)
    b = pd.DataFrame({"one_bar_return": a["close"].pct_change()}, index=idx)
    small = concat_with_memmap([a, b], threshold_bytes=10**9)
    large = concat_with_memmap([a, b], threshold_bytes=1)
    pp = FeaturePreprocessor({"winsorization": WinsorConfig().model_dump()})
    old = pp._apply_winsorization(large)
    new = pd.concat([pp._apply_winsorization(a), pp._apply_winsorization(b)], axis=1)

    def sha(df: pd.DataFrame) -> str:
        return hashlib.sha256(df.to_numpy(dtype=np.float64).tobytes()).hexdigest()

    def ndiff(x: pd.DataFrame, y: pd.DataFrame) -> int:
        xv, yv = x.to_numpy(dtype=np.float64), y.to_numpy(dtype=np.float64)
        return int((np.isfinite(xv) & np.isfinite(yv) & (xv != yv)).sum())

    def first_finite(df: pd.DataFrame) -> list:
        return [int(np.flatnonzero(np.isfinite(df[c].to_numpy(dtype=np.float64)))[0]) for c in df.columns]

    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/dtype_branch_probe.py",
        "platform": platform.platform(),
        "dtypes": {"small_branch": [str(t) for t in small.dtypes], "large_branch": [str(t) for t in large.dtypes]},
        "winsor_on": {"finite_value_diffs": ndiff(old, new), "sha256_large_then_winsor": sha(old),
                      "sha256_float64_per_column": sha(new), "first_finite_large": first_finite(old),
                      "first_finite_float64": first_finite(new),
                      "small_branch_equals_float64_per_column": sha(pp._apply_winsorization(small)) == sha(new)},
        "winsor_off": {"finite_value_diffs": ndiff(large, small)},
        "rusage": _rusage() if platform.system() == "Darwin" else None,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
