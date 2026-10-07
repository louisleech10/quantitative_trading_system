"""ICFIRSTALIGN Task 4.3：記憶體量測序列（安全漸增）探針（docs/ICFIRSTALIGN_SPEC.md v40 Task 4.3）。

以精簡 L1 起，逐步增加 L1 類別與列數（每步工作集估計不超過前一步 2 倍），於同一行程內逐步跑正式生成
（`generate_features`，CGSA），並：
- 行程內取樣執行緒每 0.2 秒以 `memory_budget._read_rusage`（`sample_memory_bytes` 之同一 API）記（時間、resident、
  footprint、目前檢查點），逐筆寫入並 flush＋fsync（被終止時已寫者不失）；第一列為平台與設定之表頭。
- 各檢查點另記 Task 4.2 (ii) 之區間峰值（`segment_tracker`；時序為觀測下界，區間峰值為該段硬上界之實測），
  逐段核「區間峰值 − check 當下值 ≤ planned_bytes」，違反者列入收據（回報並修該分支之計算式）。
- 每步完成後以 IC 分析頁同一入口（`create_ic_analyzer`／`create_feature_reader` → `compute_ic_from_l7_raw`）讀該步
  成品，記其區間峰值（Task 4.2「IC 分析頁路徑」之收據項）。
- footprint（本行程讀數與守護之域合計取大者）達實體記憶體 50% 即停止加步；第一步前即越過 ⇒ 停止並回報（非 0）。
- 停損由 Task 4.2 之獨立守護行程執行（探針專用參數：footprint 合計達實體 75%、壓力危急；另沿用正式條件換頁卷
  剩餘低於保留量），守護寫 abort 收據並終止探針（不依賴本行程取得 GIL；守護不代寫時序）。守護已立旗時探針不自行
  結束（避免先於守護退出而失去 abort 收據），等待守護確認；逾時未終止 ⇒ 具名結束（rc=4）。
外部看門狗（磁碟剩 < 4 GiB 終止）由呼叫端之 `watch_run.sh`／swap 探針承擔。

用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/memory_series_probe.py \
        [--max-steps N] [--receipt <json>]
環境：`ICFA_SERIES_OUT`（時序 JSONL；預設與收據同名 .series.jsonl）、`ICFA_DRY_RUN=1`（只寫表頭、不生成）、
`ICFA_PHYSICAL_BYTES`（實體記憶體模擬，同 memory_budget）、`ICFA_GUARD_READINGS_FILE`（守護讀數注入，測試用）、
`ICFA_SERIES_BUFFERED=1`（測試 mutant：時序改為結束時一次寫出）。
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SAMPLE_INTERVAL = 0.2
COMMAND = ("env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/memory_series_probe.py "
           "--receipt <收據> --run-root <暫存>；被守護終止後 … --finalize --receipt <收據> --run-root <暫存>")
HONEST_BOUNDS = (
    "單一 macOS 8 GB 本機、BTCUSDT 1h、同一行程逐步累積（前步配置器保留之量計入後步起點）；時序為 0.2 秒取樣之觀測"
    "下界，逐段區間峰值為硬上界之實測；探針自身停損（75%／壓力危急）由守護執行，達之即終止（被終止之步無逐步收據，"
    "其段讀數只見時序）；IC 分析頁峰值以同一入口讀各步成品（單行程模式）——窗延至資料起點之步預熱不足而 run_status"
    "＝partial，IC 頁依設計拒讀（TrainingReadError），該步無 IC 頁讀數；linux 未實跑。")
HALF = 0.5
PROBE_STOP_RATIO = 0.75
GUARD_CONFIRM_WAIT_SECONDS = 15.0
TIMEFRAME = "1h"
SYMBOL = "BTCUSDT"
END = "2026-03-31"
# L1 類別漸增（精簡＝trend EMA8／SMA13）；列數以月為單位漸增（細粒度使每步可控制於前一步 2 倍內）
CATEGORY_LADDER: List[Tuple[str, Optional[List[str]]]] = [
    ("reduced", None), ("trend", ["trend"]), ("trend+momentum", ["trend", "momentum"]),
    ("trend+momentum+volatility", ["trend", "momentum", "volatility"]),
    ("trend+momentum+volatility+volume", ["trend", "momentum", "volatility", "volume"]),
]
DAYS = [3, 5, 7, 10, 14, 21, 30, 45, 60, 90, 120, 180, 240, 365, 480, 600, 730, 850]


class Series:
    """時序寫出：預設逐筆 flush＋fsync；`ICFA_SERIES_BUFFERED=1`（mutant）改為結束時一次寫出。"""

    def __init__(self, path: Path, buffered: bool) -> None:
        self.path = path
        self.buffered = buffered
        self.rows: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = None if buffered else open(path, "w", encoding="utf-8")  # 每次執行一份新時序

    def write(self, row: Dict[str, Any]) -> None:
        with self.lock:
            if self.buffered:
                self.rows.append(row)
                return
            assert self.handle is not None
            self.handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            self.handle.flush()
            os.fsync(self.handle.fileno())

    def close(self) -> None:
        with self.lock:
            if self.buffered:
                with open(self.path, "a", encoding="utf-8") as handle:
                    for row in self.rows:
                        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                self.rows = []
            elif self.handle is not None:
                self.handle.close()
                self.handle = None


class Sampler(threading.Thread):
    """行程內取樣執行緒（每 0.2 秒；resident 與 footprint 同時取）。"""

    def __init__(self, mb: Any, series: Series) -> None:
        super().__init__(daemon=True)
        self.mb = mb
        self.series = series
        self.checkpoint = "start"
        self.step: Optional[int] = None
        self.stop_event = threading.Event()
        self.max_footprint = 0
        self.max_resident = 0
        self.discriminating = 0  # resident < footprint 之樣本數
        self.count = 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                values = self.mb._read_rusage()
            except Exception as exc:  # noqa: BLE001 — 量測失敗照記
                self.series.write({"time": time.time(), "error": str(exc), "checkpoint": self.checkpoint})
            else:
                resident, footprint = int(values["resident"]), int(values["phys_footprint"])
                self.max_footprint = max(self.max_footprint, footprint)
                self.max_resident = max(self.max_resident, resident)
                self.discriminating += int(resident < footprint)
                self.count += 1
                self.series.write({"time": time.time(), "resident": resident, "footprint": footprint,
                                   "checkpoint": self.checkpoint, "step": self.step})
            self.stop_event.wait(SAMPLE_INTERVAL)


def _reduced_atomic(h: Any) -> Dict[str, Any]:
    return {"trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in h._ATOMIC if c != "trend"}}


def _payload(h: Any, categories: Optional[List[str]]) -> Dict[str, Any]:
    payload = h.s2_payload()
    payload["timeframes"] = {"primary": TIMEFRAME, "training": [TIMEFRAME], "alignment_mode": "open_minus"}
    payload["atomic_indicators"] = (_reduced_atomic(h) if categories is None else
                                    {c: ({"enabled": True} if c in categories else {"enabled": False}) for c in h._ATOMIC})
    return payload


def _start_for(days: int) -> str:
    import pandas as pd

    return (pd.Timestamp(END) - pd.Timedelta(days=days)).strftime("%Y-%m-%d")


def _column_counts(h: Any, factory: Any, categories: Optional[List[str]]) -> Tuple[int, int]:
    """（L1 欄數, L2 估計欄數）：L1 欄數以 300 列真實切片之 L1 實算取得（欄集合不依列數）；L2 以正式估計式。"""
    config = factory._resolve_config(_payload(h, categories))
    sample = factory._layer0_data_ingestion(SYMBOL, TIMEFRAME, config, start_date=_start_for(30), end_date=END)
    l1_cols = int(factory._layer1_atomic_indicators(sample.iloc[-300:], config).data.shape[1])
    l2_cols = int(factory._estimate_l2_output_cols(l1_cols, factory._filter_operators_config(config.operators)))
    return l1_cols, l2_cols


def _plan(h: Any, factory: Any, max_steps: int) -> List[Dict[str, Any]]:
    """漸增計畫：自最小者起，每步取「工作集估計 ∈（前一步, 2 × 前一步]」之最大者；無候選即止。
    工作集估計（只依形狀）＝列數 ×（L1 欄數＋L2 估計欄數）× 8 B。"""
    import pandas as pd

    candidates = []
    for name, cats in CATEGORY_LADDER:
        l1_cols, l2_cols = _column_counts(h, factory, cats)
        for days in DAYS:
            rows = int((pd.Timestamp(END) - pd.Timestamp(_start_for(days))) / pd.Timedelta(TIMEFRAME))
            candidates.append({"name": f"{name}/{days}d", "categories": cats, "days": days, "rows": rows,
                               "l1_cols": l1_cols, "l2_cols": l2_cols, "work_bytes": rows * (l1_cols + l2_cols) * 8})
    steps = [min(candidates, key=lambda c: c["work_bytes"])]
    while len(steps) < max_steps:
        prev = steps[-1]["work_bytes"]
        within = [c for c in candidates if prev < c["work_bytes"] <= 2 * prev]
        if not within:
            break
        steps.append(max(within, key=lambda c: c["work_bytes"]))
    return steps


def _guard_latest(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _wait_for_guard(mb: Any, run_dir: Path, series: Series, reason: str) -> int:
    """守護已立旗：不自行先退出（避免守護見父行程消失而不寫 abort 收據），等其確認並終止；逾時 ⇒ 具名結束。"""
    flag = (run_dir / mb.STOP_FLAG_NAME).read_text(encoding="utf-8").strip() if (run_dir / mb.STOP_FLAG_NAME).exists() else ""
    series.write({"time": time.time(), "event": "guard_flag_seen", "flag": flag, "reason": reason})
    deadline = time.monotonic() + GUARD_CONFIRM_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(0.2)
    print(f"守護已立旗（{flag}）而 {GUARD_CONFIRM_WAIT_SECONDS:.0f} 秒內未終止：探針具名結束", file=sys.stderr)
    return 4


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ICFIRSTALIGN Task 4.3 記憶體量測序列探針")
    parser.add_argument("--max-steps", type=int, default=99)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--run-root", default=None, help="守護 run 目錄與生成暫存之上層（預設 cwd）")
    args = parser.parse_args(argv)

    stamp = time.strftime("%Y%m%d")
    receipt_path = Path(args.receipt).resolve() if args.receipt else None  # 生成隔離會 chdir
    series_env = os.environ.get("ICFA_SERIES_OUT", "").strip()
    series_path = Path(series_env) if series_env else (
        (receipt_path.with_suffix(".series.jsonl") if receipt_path else
         REPO / f"handoffs/run_receipts/{stamp}-icfirstalign-memory-series.series.jsonl")).resolve()
    series = Series(series_path.resolve(), buffered=os.environ.get("ICFA_SERIES_BUFFERED") == "1")
    header = {"time": time.time(), "event": "header",
              "platform": {"system": platform.system(), "release": platform.release(),
                           "machine": platform.machine(), "python": platform.python_version()},
              "argv": sys.argv[1:], "sample_interval_s": SAMPLE_INTERVAL}
    if os.environ.get("ICFA_DRY_RUN") == "1":
        series.write({**header, "dry_run": True})
        series.close()
        return 0

    from momentum.FeatureEngineering import memory_budget as mb  # noqa: PLC0415

    physical = int(mb.physical_memory_bytes())
    header.update({"physical_bytes": physical, "half_bytes": int(physical * HALF),
                   "probe_stop_bytes": int(physical * PROBE_STOP_RATIO)})
    series.write(header)
    run_dir = (Path(args.run_root or Path.cwd()) / "icfa_memory_series_run").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    latest_file = run_dir / "guard_latest.json"
    guard = mb.start_guard(run_dir, "memory-series", budget=mb.configured_budget_bytes(include_override=False),
                           probe={"footprint_ratio": PROBE_STOP_RATIO, "physical_bytes": physical,
                                  "pressure_stop": True, "latest_file": str(latest_file)})
    sampler = Sampler(mb, series)
    sampler.start()
    result: Dict[str, Any] = {"steps": [], "stop_reason": None}
    if receipt_path is not None:
        def _checkpoint() -> None:
            _write_receipt(receipt_path, series_path, physical, sampler,
                           {**result, "stop_reason": {"reason": "in_progress"}}, None)

        result["_checkpoint"] = _checkpoint
    rc = 0
    try:
        rc = _run_steps(mb, args, run_dir, latest_file, physical, sampler, series, result)
    except Exception as exc:  # noqa: BLE001 — 收據照寫並記原因（rc=5），不吞為成功
        rc = 5
        result["stop_reason"] = {"reason": "exception", "error": f"{type(exc).__name__}: {exc}"[:2000]}
        print(f"探針例外：{type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        sampler.stop_event.set()
        sampler.join(timeout=5)
        guard.stop()
        series.write({"time": time.time(), "event": "end", "rc": rc, "stop_reason": result["stop_reason"]})
        series.close()
    if receipt_path is not None:
        _write_receipt(receipt_path, series_path, physical, sampler, result, rc)
    return rc


def _over_half(mb: Any, latest_file: Path, physical: int) -> Optional[Dict[str, int]]:
    own = int(mb.sample_memory_bytes())
    domain = int(_guard_latest(latest_file).get("footprint") or 0)
    current = max(own, domain)
    if current >= HALF * physical:
        return {"own_footprint": own, "guard_footprint": domain, "physical": physical}
    return None


def _run_steps(mb: Any, args: argparse.Namespace, run_dir: Path, latest_file: Path, physical: int, sampler: Sampler,
               series: Series, result: Dict[str, Any]) -> int:
    import pytest

    from segment_tracker import SegmentTracker  # noqa: PLC0415

    from tests.feature_engineering import icfirstalign_helpers as h  # noqa: PLC0415

    import logging

    logging.getLogger("momentum").setLevel(logging.WARNING)
    over = _over_half(mb, latest_file, physical)
    if over is not None:
        result["stop_reason"] = {"reason": "first_step_over_half", **over}
        print(f"第一步前 footprint 已達實體記憶體 50%（{over}）：停止並回報", file=sys.stderr)
        return 3
    work = run_dir / "work"
    with pytest.MonkeyPatch.context() as mp:
        root = h.isolated(mp, work)
        planner = h.make_factory(root)
        plan = _plan(h, planner, args.max_steps)
        del planner
        result["plan"] = [{k: v for k, v in p.items() if k != "categories"} for p in plan]
        for index, step in enumerate(plan, start=1):
            if (run_dir / mb.STOP_FLAG_NAME).exists():
                result["stop_reason"] = {"reason": "guard_flag", "before_step": index}
                return _wait_for_guard(mb, run_dir, series, "before_step")
            over = _over_half(mb, latest_file, physical)
            if over is not None:
                result["stop_reason"] = {"reason": "footprint_half", "before_step": index, **over}
                print(f"footprint 達實體記憶體 50%（{over}）：停止加步", file=sys.stderr)
                return 3 if index == 1 else 0
            sampler.step = index
            sampler.checkpoint = f"step{index}:{step['name']}"
            step_record = _run_one_step(mb, h, mp, root / f"step{index}", step, sampler, SegmentTracker)
            result["steps"].append(step_record)
            series.write({"time": time.time(), "event": "step_done", "step": index, "name": step["name"],
                          "elapsed_s": step_record["elapsed_s"]})
            if result.get("_checkpoint") is not None:  # 逐步覆寫收據（被守護終止時已完成之步不失）
                result["_checkpoint"]()
            if (run_dir / mb.STOP_FLAG_NAME).exists():
                result["stop_reason"] = {"reason": "guard_flag", "after_step": index}
                return _wait_for_guard(mb, run_dir, series, "after_step")
        result["stop_reason"] = {"reason": "plan_exhausted" if len(plan) < args.max_steps else "max_steps"}
    return 0


def _run_one_step(mb: Any, h: Any, mp: Any, step_root: Path, step: Dict[str, Any], sampler: Sampler,
                  tracker_cls: Any) -> Dict[str, Any]:
    segments: List[Dict[str, Any]] = []

    def on_segment(seg: Any) -> None:
        sampler.checkpoint = f"step{sampler.step}:{seg.branch}"
        segments.append(seg.as_dict())

    step_root.mkdir(parents=True, exist_ok=True)
    tracker = tracker_cls(mb, on_segment=on_segment)
    with pytest_context() as inner:
        tracker.install(inner)
        factory = h.make_factory(step_root)
        start = _start_for(step["days"])
        t0 = time.monotonic()
        footprint_before = int(mb.sample_memory_bytes())
        result = factory.generate_features(SYMBOL, TIMEFRAME, config_override=_payload(h, step["categories"]),
                                           force_regenerate=True, start_date=start, end_date=END, persist=True)
        tracker.finish()
        elapsed = time.monotonic() - t0
    violations = [s for s in segments if s["increase"] is not None and s["increase"] > s["planned"]]
    ic_page = _ic_page_peak(mb, h, step_root, str(result.metadata["config_hash"]), sampler,
                            {"start": start, "end": END})
    record = {"name": step["name"], "days": step["days"], "rows_est": step["rows"], "l1_cols": step["l1_cols"],
              "l2_cols_est": step["l2_cols"], "work_bytes_est": step["work_bytes"], "start": start, "end": END,
              "elapsed_s": round(elapsed, 2), "footprint_before": footprint_before,
              "footprint_after": int(mb.sample_memory_bytes()), "feature_count": int(result.feature_count),
              "segments": len(segments), "max_segment_increase": max((s["increase"] or 0 for s in segments), default=0),
              "violations": violations, "ic_page": ic_page}
    del factory, result
    shutil.rmtree(step_root, ignore_errors=True)
    gc.collect()
    return record


class pytest_context:  # noqa: N801 — 小寫以示其為 MonkeyPatch.context 之薄包
    def __enter__(self) -> Any:
        import pytest

        self._ctx = pytest.MonkeyPatch.context()
        return self._ctx.__enter__()

    def __exit__(self, *exc: Any) -> None:
        self._ctx.__exit__(*exc)


def _ic_page_peak(mb: Any, h: Any, root: Path, config_hash: str, sampler: Sampler,
                  selection_window: Dict[str, str]) -> Dict[str, Any]:
    """IC 分析頁同一入口（`api/services/ic_analysis_service.py` 之 compute_ic_from_l7_raw：create_ic_analyzer＋
    create_feature_reader）讀本步成品之區間峰值；單行程模式（無域、無受保護 run）。"""
    from momentum.factories import create_feature_reader, create_ic_analyzer  # noqa: PLC0415

    sampler.checkpoint = f"step{sampler.step}:ic_page"
    analyzer = create_ic_analyzer(None)
    engine = getattr(analyzer, "_ic_engine")
    reader = create_feature_reader(str(root))
    label = h.forward_return_label(TIMEFRAME, end=END)
    at = int(mb.reset_interval_peak())
    t0 = time.monotonic()
    try:
        out = engine.compute_ic_from_l7_raw(symbol=SYMBOL, tf=TIMEFRAME, config_hash=config_hash, label=label,
                                            feature_reader=reader, ic_threshold=0.0, label_horizon="1",
                                            selection_window=selection_window)
        status, groups, features = "ok", int(out.group_count), len(out.ic_scores)
    except Exception as exc:  # noqa: BLE001 — 收據記錄原因，不吞為成功
        status, groups, features = f"error:{type(exc).__name__}:{exc}"[:500], 0, 0
    peak = int(mb.read_interval_peak())
    return {"status": status, "groups": groups, "features": features, "footprint_at_start": at,
            "interval_peak": peak, "increase": peak - at, "elapsed_s": round(time.monotonic() - t0, 2)}


def _write_receipt(path: Path, series_path: Path, physical: int, sampler: Sampler, result: Dict[str, Any],
                   rc: int) -> None:
    violations = [v for s in result["steps"] for v in s["violations"]]
    ic = [s["ic_page"] for s in result["steps"]]
    receipt = {
        "schema_version": 1, "command": COMMAND, "exit_code": rc,
        "probe": "handoffs/run_receipts/icfirstalign_probes/memory_series_probe.py",
        "spec": "docs/ICFIRSTALIGN_SPEC.md v40 Task 4.3",
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "rc": rc,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "physical_bytes": physical, "half_bytes": int(physical * HALF), "probe_stop_bytes": int(physical * PROBE_STOP_RATIO),
        "series_file": str(series_path), "samples": sampler.count, "max_footprint": sampler.max_footprint,
        "max_resident": sampler.max_resident, "discriminating_samples_resident_lt_footprint": sampler.discriminating,
        "plan": result.get("plan"), "steps": result["steps"], "stop_reason": result["stop_reason"],
        "estimate_violations": violations, "estimate_violation_count": len(violations),
        "ic_page_max_increase": max((i["increase"] for i in ic), default=None),
        "ic_page_max_peak": max((i["interval_peak"] for i in ic), default=None),
        "main_evidence": "handoffs/run_receipts/20261003-prered-f2-memory.json（主證據沿用 PRE-RED，不重跑）",
        "honest_bounds": HONEST_BOUNDS,
    }
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")


def finalize(receipt_path: Path, run_root: Path) -> int:
    """探針被守護終止後補完收據：停止原因取守護 abort 收據；時序統計（樣本數、footprint／resident 最大、歧視樣本、
    最後檢查點）取時序檔全部列（含逐步收據之後、終止之前之樣本）。"""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in Path(receipt["series_file"]).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    samples = [r for r in rows if "footprint" in r and "event" not in r]
    abort_path = run_root / "icfa_memory_series_run" / "memory_guard_abort.json"
    abort = json.loads(abort_path.read_text(encoding="utf-8")) if abort_path.exists() else None
    last = samples[-1] if samples else {}
    receipt.update({
        "schema_version": 1, "command": COMMAND, "exit_code": -9 if abort else receipt.get("rc"),
        "rc": -9 if abort else receipt.get("rc"),
        "stop_reason": ({"reason": "guard_abort", "trigger": abort.get("trigger"), "abort_time": abort.get("time"),
                         "killed_during": last.get("checkpoint"), "readings": abort.get("readings")}
                        if abort else receipt.get("stop_reason")),
        "samples": len(samples), "max_footprint": max((int(r["footprint"]) for r in samples), default=None),
        "max_resident": max((int(r["resident"]) for r in samples), default=None),
        "discriminating_samples_resident_lt_footprint": sum(int(r["resident"]) < int(r["footprint"]) for r in samples),
        "finalized_from_series": True, "honest_bounds": HONEST_BOUNDS,
    })
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"stop_reason": receipt["stop_reason"] and receipt["stop_reason"].get("reason"),
                      "steps": len(receipt["steps"]), "max_footprint": receipt["max_footprint"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--finalize" in sys.argv:
        _parser = argparse.ArgumentParser()
        _parser.add_argument("--finalize", action="store_true")
        _parser.add_argument("--receipt", required=True)
        _parser.add_argument("--run-root", required=True)
        _args = _parser.parse_args()
        sys.exit(finalize(Path(_args.receipt), Path(_args.run_root)))
    sys.exit(main())
