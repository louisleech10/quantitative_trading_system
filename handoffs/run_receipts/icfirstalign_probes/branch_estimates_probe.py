"""ICFIRSTALIGN Task 4.2 (ii)：逐分支不低估之一次性收據（docs/ICFIRSTALIGN_SPEC.md v40 Task 4.2「估算不低估之機械核對」(ii)）。

母體＝實際可達組合（非分支 ID）：L1 parallel 2 值；L2 `FFACT_USE_POLARS` × polars 可否 import × workers 等價類；
L3 numba × 串流 × 多窗 × persist mode（callback 有／無）× chunked 與否＋numba 例外後備；多週期 dense／compact（並行
根對齊）與串列根內；IC-first（IC 群組讀回、選欄讀回、post-IC）。L1／L2 之組合併入 L3 組合之各次生成（各層之
選擇子互相獨立）。每一組合以真實 kline（BTCUSDT 1h、trend 預設指標）於兩規模（列數相差 2 倍以上）各實跑一次，
各在獨立子行程（區間峰值與配置器狀態互不污染）。

逐 check 段（`segment_tracker.SegmentTracker`）核對「區間峰值 − check 當下值 ≤ 該 check 之 planned_bytes」；
量＝`ri_phys_footprint` 之區間最大值（與預算量同一量）。另記「空段」（reset 後立即讀）之實測增量。

用法：
  env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/branch_estimates_probe.py \
      [--out handoffs/run_receipts/<日期>-icfirstalign-branch-estimates.json] [--only <組合名,...>] [--scales A,B]
子行程模式（由主程式呼叫）：--one <組合名> --scale <A|B> --segments <jsonl> --workdir <dir>
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

# 兩規模（列數相差 2 倍以上；工作集 100 MB–1 GB）：BTCUSDT 1h、trend 類預設指標
SCALES: Dict[str, Dict[str, str]] = {
    "A": {"start": "2025-10-01", "end": "2026-03-31"},
    "B": {"start": "2025-03-15", "end": "2026-03-31"},
}
TIMEFRAME = "1h"
MTF_SECOND = "12h"

_L3 = [(n, s, m, cb) for n in ("0", "1") for s in ("0", "1") for m in ("0", "1") for cb in (True, False)]
_L2 = [("1", True, "1"), ("0", True, "1"), ("0", True, "4"), ("1", False, "1")]  # (USE_POLARS, polars 可 import, workers)


def _combos() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for i, (numba, streaming, multi, callback) in enumerate(_L3):
        polars_env, polars_ok, workers = _L2[i % len(_L2)]
        env = {"FFACT_USE_NUMBA_ROLLING": numba, "FFACT_L3_STREAMING": streaming, "FFACT_L3_MULTI_WINDOW": multi,
               "FFACT_L3_PERSIST_MODE": "streaming" if callback else "in_memory",
               "FFACT_LAYER1_PARALLEL": "1" if i % 2 else "0",
               "FFACT_USE_POLARS": polars_env, "FFACT_L2_CATEGORY_WORKERS": workers,
               "FFACT_MULTI_TF_PARALLEL": "0"}
        name = f"l3_n{numba}s{streaming}m{multi}{'cb' if callback else 'nocb'}"
        out[name] = {"env": env, "polars_available": polars_ok, "preprocessing": i == 0}
    base = {"FFACT_MULTI_TF_PARALLEL": "0"}
    out["l3_vectorized_chunked"] = {"env": {**base, "FFACT_L3_STREAMING": "0"}, "chunk": 1}
    out["l3_numba_fallback"] = {"env": dict(base), "inject_numba_error": True}
    out["mtf_parallel_dense"] = {"env": {"FFACT_MULTI_TF_PARALLEL": "1", "FFACT_MULTI_TF_MAX_WORKERS": "1",
                                         "FFACT_MULTI_TF_COMPACT_ALIGNMENT": "0"}, "training": [TIMEFRAME, MTF_SECOND]}
    out["mtf_parallel_compact"] = {"env": {"FFACT_MULTI_TF_PARALLEL": "1", "FFACT_MULTI_TF_MAX_WORKERS": "1",
                                           "FFACT_MULTI_TF_COMPACT_ALIGNMENT": "1"}, "training": [TIMEFRAME, MTF_SECOND]}
    out["mtf_serial_dense"] = {"env": {"FFACT_MULTI_TF_PARALLEL": "0", "FFACT_MULTI_TF_COMPACT_ALIGNMENT": "0"},
                               "training": [TIMEFRAME, MTF_SECOND]}
    out["ic_first"] = {"env": dict(base), "ic_first": True, "preprocessing": True}
    return out


def _payload(h: Any, spec: Dict[str, Any]) -> Dict[str, Any]:
    payload = h.s2_payload()
    payload["timeframes"] = {"primary": TIMEFRAME, "training": list(spec.get("training") or [TIMEFRAME]),
                             "alignment_mode": "open_minus"}
    payload["atomic_indicators"] = {c: ({"enabled": True} if c == "trend" else {"enabled": False}) for c in h._ATOMIC}
    if spec.get("chunk"):
        payload["rolling_aggregation"] = {"enabled": True, "windows": [5, 13], "column_chunk_size": int(spec["chunk"])}
    if not spec.get("preprocessing"):
        payload["preprocessing"] = {"enabled": False}
    return payload


def run_one(name: str, scale: str, segments_path: Path, workdir: Path) -> int:
    """子行程：跑一個組合、逐段寫 JSONL。"""
    import pytest

    sys.path.insert(0, str(HERE))
    from segment_tracker import SegmentTracker, empty_segment_increase  # noqa: PLC0415

    from momentum.FeatureEngineering import memory_budget as mb  # noqa: PLC0415
    from tests.feature_engineering import icfirstalign_helpers as h  # noqa: PLC0415

    logging.getLogger("momentum").setLevel(logging.WARNING)
    spec = _combos()[name]
    window = SCALES[scale]
    handle = open(segments_path, "a", encoding="utf-8")

    def emit(seg: Any) -> None:
        handle.write(json.dumps({"combo": name, "scale": scale, **seg.as_dict()}, ensure_ascii=False) + "\n")
        handle.flush()

    handle.write(json.dumps({"combo": name, "scale": scale, "empty_segment": empty_segment_increase(mb)}) + "\n")
    t0 = time.monotonic()
    with pytest.MonkeyPatch.context() as mp:
        root = h.isolated(mp, workdir, **spec["env"])
        if not spec.get("polars_available", True):
            import momentum.FeatureEngineering.polars_adapter as pa_mod  # noqa: PLC0415

            mp.setattr(pa_mod, "_check_polars_available", lambda: False)
        if spec.get("inject_numba_error"):
            from momentum.FeatureEngineering.operators import numba_rolling  # noqa: PLC0415

            mp.setattr(numba_rolling, "fused_rolling_stats_multi_window",
                       lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
        tracker = SegmentTracker(mb, on_segment=emit).install(mp)
        factory = h.make_factory(root)
        payload = _payload(h, spec)
        if spec.get("ic_first"):
            from momentum.Analysis.ic_engine import ICEngine  # noqa: PLC0415

            factory.run_ic_first(h.SYMBOL, TIMEFRAME, factory._resolve_config(payload), start_date=window["start"],
                                 end_date=window["end"], ic_engine=ICEngine({"methods": ["spearman"]}),
                                 ic_threshold=0.0, label_horizon="1",
                                 selection_window={"start": window["start"], "end": window["end"]})
        else:
            factory.generate_features(h.SYMBOL, TIMEFRAME, config_override=payload, force_regenerate=True,
                                      start_date=window["start"], end_date=window["end"], persist=True)
        tracker.finish()
    handle.write(json.dumps({"combo": name, "scale": scale, "elapsed_s": round(time.monotonic() - t0, 2)}) + "\n")
    handle.close()
    return 0


def _summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    segments = [r for r in rows if "branch" in r]
    violations = [r for r in segments if r.get("increase") is not None and r["increase"] > r["planned"]]
    by_branch: Dict[str, Dict[str, Any]] = {}
    for r in segments:
        b = by_branch.setdefault(r["branch"], {"segments": 0, "scales": set(), "combos": set(), "max_increase": 0,
                                               "max_ratio": 0.0, "violations": 0})
        b["segments"] += 1
        b["scales"].add(r["scale"])
        b["combos"].add(r["combo"])
        b["max_increase"] = max(b["max_increase"], int(r["increase"] or 0))
        if r["planned"] > 0:
            b["max_ratio"] = max(b["max_ratio"], (r["increase"] or 0) / r["planned"])
        if r in violations:
            b["violations"] += 1
    for b in by_branch.values():
        b["scales"] = sorted(b["scales"])
        b["combos"] = sorted(b["combos"])
        b["max_ratio"] = round(b["max_ratio"], 4)
    empties = [r["empty_segment"] for r in rows if "empty_segment" in r]
    return {"segments": len(segments), "violations": violations, "violation_count": len(violations),
            "by_branch": by_branch, "empty_segment_max": max((e["max"] for e in empties), default=None),
            "elapsed": {f'{r["combo"]}/{r["scale"]}': r["elapsed_s"] for r in rows if "elapsed_s" in r}}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one")
    parser.add_argument("--scale")
    parser.add_argument("--segments")
    parser.add_argument("--workdir")
    parser.add_argument("--out")
    parser.add_argument("--only")
    parser.add_argument("--scales", default="A,B")
    parser.add_argument("--rebuild", action="store_true", help="只由既有 .segments.jsonl 重寫收據（不重跑生成）")
    args = parser.parse_args(argv)
    if args.one:
        return run_one(args.one, args.scale, Path(args.segments), Path(args.workdir))
    if sys.platform != "darwin":
        print(f"(ii) 只於 macOS 執行（SPEC §N）：platform={sys.platform}", file=sys.stderr)
        return 2
    combos = _combos()
    names = [n for n in combos if not args.only or n in args.only.split(",")]
    stamp = time.strftime("%Y%m%d")
    out = Path(args.out or REPO / f"handoffs/run_receipts/{stamp}-icfirstalign-branch-estimates.json")
    segments_path = out.with_suffix(".segments.jsonl")
    failures: List[Dict[str, Any]] = []
    if args.rebuild:
        # 只由既有逐段原始讀數（.segments.jsonl）重算摘要與判定，不重跑生成；failures 沿用既有收據
        if out.exists():
            failures = list(json.loads(out.read_text(encoding="utf-8")).get("failures") or [])
        return _write(out, segments_path, names, combos, failures, args)
    segments_path.unlink(missing_ok=True)
    for scale in args.scales.split(","):
        for name in names:
            workdir = Path(tempfile.mkdtemp(prefix=f"icfa_be_{name}_{scale}_"))
            cmd = [sys.executable, str(Path(__file__).resolve()), "--one", name, "--scale", scale,
                   "--segments", str(segments_path), "--workdir", str(workdir)]
            env = {**os.environ, "PYTHONPATH": str(REPO), "PYTHONHASHSEED": "0"}
            proc = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True)
            print(f"{name}/{scale} rc={proc.returncode}", flush=True)
            if proc.returncode != 0:
                failures.append({"combo": name, "scale": scale, "rc": proc.returncode, "stderr": proc.stderr[-3000:]})
            shutil.rmtree(workdir, ignore_errors=True)
    return _write(out, segments_path, names, combos, failures, args)


def _write(out: Path, segments_path: Path, names: List[str], combos: Dict[str, Any], failures: List[Dict[str, Any]],
           args: argparse.Namespace) -> int:
    rows = [json.loads(line) for line in segments_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = _summarize(rows)
    from momentum.FeatureEngineering import memory_budget as mb  # noqa: PLC0415

    declared = set(summary["by_branch"])
    verdict = "pass" if not summary["violations"] and not failures else "fail"
    receipt = {
        "schema_version": 1,
        "command": ("env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python "
                    "handoffs/run_receipts/icfirstalign_probes/branch_estimates_probe.py "
                    f"--out {out.relative_to(REPO) if out.is_relative_to(REPO) else out}"
                    + (f" --only {args.only}" if args.only else "") + f" --scales {args.scales}"),
        "exit_code": 0 if verdict == "pass" else 1,
        "rebuilt_from_segments": bool(args.rebuild),
        "probe": "handoffs/run_receipts/icfirstalign_probes/branch_estimates_probe.py",
        "spec": "docs/ICFIRSTALIGN_SPEC.md v40 Task 4.2 (ii)",
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
                     "physical_bytes": mb.physical_memory_bytes()},
        "kline": "data_cache/feature_klines/kline_cache.h5", "symbol": "BTCUSDT", "timeframe": TIMEFRAME,
        "scales": SCALES, "combos": {n: combos[n] for n in names},
        "metric": "ri_interval_max_phys_footprint − ri_phys_footprint@check（逐 check 段，至下一 check／layer_end）",
        "branches_not_hit": sorted(set(mb.BRANCH_TABLE) - declared),
        "segment_constants": {"segment_constant": getattr(mb, "SEGMENT_CONSTANT_BYTES", None),
                              "polars_runtime": getattr(mb, "POLARS_RUNTIME_BYTES", None)},
        "failures": failures,
        **summary,
        "verdict": verdict,
        "segments_file": str(segments_path.relative_to(REPO)) if segments_path.is_relative_to(REPO) else str(segments_path),
    }
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "violations": summary["violation_count"],
                      "branches_not_hit": receipt["branches_not_hit"], "failures": len(failures)}, ensure_ascii=False))
    return 0 if receipt["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
