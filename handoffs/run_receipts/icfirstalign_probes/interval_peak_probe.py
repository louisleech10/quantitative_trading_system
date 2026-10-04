"""ICFIRSTALIGN 乙 SPEC §A 收據：macOS 是否有核心追蹤之「區間最大 phys_footprint」可重設並逐段讀取（無取樣盲區）。

`proc_pid_rusage(pid, RUSAGE_INFO_V4)`：rusage_info_v4 之欄位序依 SDK `sys/resource.h`；以實測辨認欄位——
重設區間（`proc_reset_footprint_interval`）後配置並觸頁 400 MB、立即釋放，再讀；區間最大值應含該 400 MB 短峰，
而當前 phys_footprint 已回落。再重設一次，不配置，區間最大值應回到當前值附近。
用法：env PYTHONPATH=. venv/bin/python <本檔>（峰值約 0.5 GB）。
"""

from __future__ import annotations

import ctypes
import json
import os

N_FIELDS = 40  # v4 之 uint64 欄數上界（多讀之尾端為 0，不影響辨認）


class RusageInfo(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(N_FIELDS)]


def read(lib) -> list:
    info = RusageInfo()
    rc = lib.proc_pid_rusage(os.getpid(), 4, ctypes.byref(info))
    if rc != 0:
        raise OSError(f"proc_pid_rusage v4 rc={rc}")
    return [int(getattr(info, f"f{i}")) for i in range(N_FIELDS)]


def main() -> int:
    import numpy as np

    lib = ctypes.CDLL("/usr/lib/libproc.dylib")
    has_reset = hasattr(lib, "proc_reset_footprint_interval")
    reset_rc = lib.proc_reset_footprint_interval(os.getpid()) if has_reset else None
    base = read(lib)
    import mmap

    region = mmap.mmap(-1, 400 * 1024 * 1024)  # 匿名映射，close 即歸還（不經 malloc 快取）
    view = np.frombuffer(region, dtype=np.uint8)
    view[::4096] = 1  # 觸每一頁
    del view
    region.close()
    after_spike = read(lib)
    reset_rc2 = lib.proc_reset_footprint_interval(os.getpid()) if has_reset else None
    after_reset = read(lib)
    mb = 1024 * 1024
    candidates = []
    for i in range(N_FIELDS):
        delta = after_spike[i] - base[i]
        if 300 * mb < delta < 600 * mb and abs(after_reset[i] - base[i]) < 100 * mb:
            candidates.append({"field_index": i, "base_mb": round(base[i] / mb, 1),
                               "after_spike_mb": round(after_spike[i] / mb, 1),
                               "after_reset_mb": round(after_reset[i] / mb, 1)})
    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/interval_peak_probe.py",
        "has_proc_reset_footprint_interval": has_reset, "reset_rc": [reset_rc, reset_rc2],
        "phys_footprint_now_mb": {"base": round(base[7] / mb, 1), "after_spike": round(after_spike[7] / mb, 1)},
        "interval_peak_candidates": candidates,
        "all_fields_mb": [[i, round(base[i] / mb, 1), round(after_spike[i] / mb, 1), round(after_reset[i] / mb, 1)]
                          for i in range(N_FIELDS) if 1 * mb < max(base[i], after_spike[i], after_reset[i]) < 10**6 * mb],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
