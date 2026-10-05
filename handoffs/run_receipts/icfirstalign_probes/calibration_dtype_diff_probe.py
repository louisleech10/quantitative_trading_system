"""ICFIRSTALIGN 乙 Task 4.1 收據：新實作 vs HEAD 乙之校準值差異（待確認⑤）與 P1 之 peak footprint 對照。

兩個子命令（皆真實 kline、精簡設定、寫入隔離於暫存目錄）：
- `diff <out.json>`：以本樹（新實作）跑 §G 之 P1、P2（探測）與 S3 縮尾開／關（校準封包），與 HEAD 乙之凍結基準
  （tests/_golden/icfirstalign/probe_baseline.json、calibration_baseline.json 之 "yi"）逐項比對：探測之末輪各週期首個
  有限值 sha 與晚到集合 sha；封包之逐欄值 sha、first／last 校準時間、empty_columns、column_set_digest。基準只存逐欄
  sha，故差異以「不等之欄數」計；全等時最大絕對差＝0（位元組相同），不等時記為不可由基準求得。
- `peak <PYTHONPATH 根> <out.json>`：於新 spawn 子行程以指定樹之碼跑 P1 正式生成，記行程生涯最大 phys_footprint
  （`proc_pid_rusage` RUSAGE_INFO_V4 第 28 欄）。HEAD 以 `git worktree` 之樹執行（data_cache 以 symlink 指回主樹）。
用法：env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/calibration_dtype_diff_probe.py diff <out>
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _diff(out_path: Path) -> int:
    sys.path.insert(0, os.getcwd())
    import pytest

    import scripts.freeze_icfirstalign_baseline as frz
    from momentum.FeatureEngineering import feature_factory as ff
    from tests.feature_engineering import icfirstalign_helpers as h

    probe_gold = json.loads((h.REPO / "tests/_golden/icfirstalign/probe_baseline.json").read_text(encoding="utf-8"))
    calib_gold = json.loads((h.REPO / "tests/_golden/icfirstalign/calibration_baseline.json").read_text(encoding="utf-8"))
    started = time.time()
    probes: Dict[str, Any] = {}
    for name, payload, window in (("P1", frz.p1_payload(), frz.P1_WINDOW), ("P2", frz.p2_payload(), h.S2_WINDOW)):
        mp = pytest.MonkeyPatch()
        try:
            root = h.isolated(mp, Path(tempfile.mkdtemp(prefix="icfa_dtypediff_")))
            factory = h.make_factory(root)
            factory.generate_features(h.SYMBOL, h.PRIMARY, config_override=payload, force_regenerate=True,
                                      start_date=window[0], end_date=window[1], persist=True)
            late = getattr(factory, "_public_warmup_late", None)
            got_late = _sha(sorted(late[1])) if late else None
            got_first = {tf: _sha(sorted(m.items())) for tf, m in factory._public_warmup_first_finite.items()}
        finally:
            mp.undo()
        yi_first: Dict[str, str] = {}
        for call in probe_gold["yi"][name]["domain_calls"]:
            yi_first[call["timeframe"]] = call["first_finite_sha256"]
        probes[name] = {"late_names_equal_yi": got_late == probe_gold["yi"][name]["late_names_sha256"],
                        "first_finite_timeframes_differing": sorted(tf for tf in set(yi_first) | set(got_first)
                                                                    if yi_first.get(tf) != got_first.get(tf))}
    packets: Dict[str, Any] = {}
    for winsor in (True, False):
        key = f"S3_winsor_{'on' if winsor else 'off'}"
        captured: Dict[str, Any] = {}
        mp = pytest.MonkeyPatch()
        try:
            real = ff.FeatureFactory.run_calibration_preflight

            def preflight(self: Any, *a: Any, **k: Any) -> Any:
                result = real(self, *a, **k)
                captured.update(result.get("packets", {}))
                return result

            mp.setattr(ff.FeatureFactory, "run_calibration_preflight", preflight)
            root = h.isolated(mp, Path(tempfile.mkdtemp(prefix="icfa_dtypediff_")))
            h.make_factory(root).generate_features(h.SYMBOL, h.PRIMARY, config_override=frz.s3_payload(winsor),
                                                   force_regenerate=True, start_date=h.S2_WINDOW[0],
                                                   end_date=h.S2_WINDOW[1], persist=True)
        finally:
            mp.undo()
        for tf, packet in captured.items():
            got = frz._packet_record(packet)
            yi = calib_gold["yi"][key][tf]
            cols = sorted(set(got["values"]) | set(yi["values"]))
            differing = [c for c in cols if got["values"].get(c) != yi["values"].get(c)]
            first_diff = [c for c in sorted(set(got["first_ts"]) | set(yi["first_ts"]))
                          if got["first_ts"].get(c) != yi["first_ts"].get(c)]
            packets[f"{key}/{tf}"] = {
                "columns": len(cols), "value_columns_differing": len(differing),
                "max_abs_diff": 0.0 if not differing else "unavailable（基準只存逐欄 sha）",
                "first_calibration_ts_differing": first_diff,
                "empty_columns_equal": got["empty_columns"] == yi["empty_columns"],
                "column_set_digest_equal": got["column_set_digest"] == yi["column_set_digest"],
            }
    receipt = {"schema_version": 1, "command": f"... calibration_dtype_diff_probe.py diff {out_path}",
               "baseline": "HEAD 乙（tests/_golden/icfirstalign/*_baseline.json 之 yi）", "probe": probes,
               "packets": packets, "elapsed_seconds": round(time.time() - started, 1)}
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0


class _V4(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(f"f{i}", ctypes.c_uint64) for i in range(40)]


def _p1_child() -> int:
    """子行程本體：以本行程 sys.path 之碼跑 P1，印生涯峰值。"""
    import pytest

    import scripts.freeze_icfirstalign_baseline as frz
    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        root = h.isolated(mp, Path(tempfile.mkdtemp(prefix="icfa_p1peak_")))
        h.make_factory(root).generate_features(h.SYMBOL, h.PRIMARY, config_override=frz.p1_payload(),
                                               force_regenerate=True, start_date=frz.P1_WINDOW[0],
                                               end_date=frz.P1_WINDOW[1], persist=True)
    finally:
        mp.undo()
    info = _V4()
    ctypes.CDLL("/usr/lib/libproc.dylib").proc_pid_rusage(os.getpid(), 4, ctypes.byref(info))
    print("PEAK", int(info.f28))
    return 0


def _peak(tree: Path, out_path: Path) -> int:
    env = {**os.environ, "PYTHONPATH": str(tree), "PYTHONHASHSEED": "0"}
    proc = subprocess.run([sys.executable, __file__, "_child"], cwd=str(tree), env=env, capture_output=True, text=True,
                          timeout=1800)
    peak = next((int(line.split()[1]) for line in proc.stdout.splitlines() if line.startswith("PEAK ")), None)
    receipt = {"tree": str(tree), "rc": proc.returncode, "lifetime_peak_footprint_bytes": peak,
               "lifetime_peak_footprint_gib": None if peak is None else round(peak / (1 << 30), 3),
               "stderr_tail": proc.stderr[-1500:] if proc.returncode else ""}
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "_child":
        sys.path.insert(0, os.getcwd())
        raise SystemExit(_p1_child())
    if mode == "diff":
        raise SystemExit(_diff(Path(sys.argv[2])))
    if mode == "peak":
        raise SystemExit(_peak(Path(sys.argv[2]).resolve(), Path(sys.argv[3])))
    raise SystemExit(f"unknown mode {mode}")
