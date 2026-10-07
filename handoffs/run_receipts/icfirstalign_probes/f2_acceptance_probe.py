"""ICFIRSTALIGN Task 4.4：F-2 原設定之記憶體驗收收據（docs/ICFIRSTALIGN_SPEC.md v40 §G「記憶體驗收」、Task 4.4）。

原設定（PRE-RED F-2，`handoffs/run_receipts/prered_probes/v7_seed_manifest.py`）：BTCUSDT 12h 主週期、training
[12h, 1h]、14 天公開窗、全史預熱、完整預設 L1、L6.5 關、dead-drop 關；環境同 `scripts/freeze_failopen_baseline.py`
之 FIXED_ENV（多週期串列）。以正式生成（含 Task 4.2 守護）於子行程執行，本行程為外部看門狗：
- 開跑前置（§G）：磁碟剩餘 ≥ 各週期同容器檔案寫入上界 D 之和（`FeatureFactory.estimate_generation_disk`，含暫存
  校準 registry／L2 memmap／正式 registry 之共存，全史列數）＋ 4 GiB；不足即不開跑並回報（rc=2）。
- 每 0.5 秒記子行程樹 footprint 合計、壓力等級、換頁用量、換頁卷剩餘、工作目錄實占（每 5 秒）；換頁卷剩餘 < 4 GiB
  ⇒ 終止受測行程樹（停止原因＝disk_watchdog，不算完成）。
- 子行程以 `/usr/bin/time -l` 包覆（peak memory footprint、maximum resident set size）；`ICFA_CHECK_LOG` 記每次
  `check`／准入之判定（逐檢查點之預算判定摘要入收據）。
結果分類：completed（生成跑完）／fail_closed（具名 `GenerationMemoryBudgetExceeded` 等預算錯誤）／killed（被系統、
守護或看門狗終止）／error（其他例外）。

用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/f2_acceptance_probe.py \
        [--receipt handoffs/run_receipts/<日期>-icfirstalign-f2-acceptance.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
DISK_FLOOR = 4 << 30
WALK_EVERY_S = 5.0
SYMBOL = "BTCUSDT"
PRIMARY = "12h"
TRAINING = ["12h", "1h"]
DAYS = 14
COMMAND = ("env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/f2_acceptance_probe.py "
           "--receipt handoffs/run_receipts/<日期>-icfirstalign-f2-acceptance.json；之後 … --annotate --receipt <同>")


# 成品品質 partial 之可接受原因（封閉集合）：FF-STAT §C 公開域預熱——預熱已延至資料起點、首個有效值仍晚於起始日之欄
# （資料真相，非記憶體；SPEC v41 §G）。其餘 partial 原因一律不算 Task 4.4 完成。
ALLOWED_PARTIAL_REASONS = ("warmup_insufficient_history",)


def classify(rc: int, *, disk_watchdog: bool, guard_abort: bool, child: Dict[str, Any],
             failure_reasons: Optional[List[str]] = None) -> Dict[str, Any]:
    """Task 4.4 完成判定（純函式；審碼 b4 r1 codex P1-01／P1-02）。

    行程結局先於子行程自述：磁碟看門狗、守護 abort、rc ≠ 0（含被訊號終止之負值）任一成立 ⇒ 非完成，不論子行程是否已
    寫 `completed`。行程完成後另判成品品質：run_status 與 quality_status 皆 complete ⇒ `completed`；partial 且全部
    failure_reasons 之原因名屬 `ALLOWED_PARTIAL_REASONS` ⇒ `completed_partial_allowed`；其餘 ⇒ `completed_partial_other`
    （不算完成）。回傳 process_outcome、artifact_quality、outcome、accepted。"""
    child_outcome = child.get("outcome")
    if disk_watchdog:
        process = "killed_disk_watchdog"
    elif guard_abort:
        process = "killed_by_guard"
    elif rc < 0:
        process = f"killed_signal_{-rc}"
    elif child_outcome in ("fail_closed", "error"):
        process = child_outcome
    elif rc != 0 or child_outcome != "completed":
        process = f"inconsistent_rc_{rc}_child_{child_outcome}"
    else:
        process = "completed"
    run_status, quality_status = child.get("run_status"), child.get("quality_status")
    reasons = [str(r) for r in (failure_reasons or [])]
    if run_status == "complete" and quality_status == "complete":
        quality = "complete"
    elif reasons and all(r.split(":", 1)[0] in ALLOWED_PARTIAL_REASONS for r in reasons):
        quality = "partial_allowed"
    else:
        quality = "partial_other"
    if process != "completed":
        outcome = process
    else:
        outcome = {"complete": "completed", "partial_allowed": "completed_partial_allowed"}.get(
            quality, "completed_partial_other")
    return {"process_outcome": process, "artifact_quality": quality, "run_status": run_status,
            "quality_status": quality_status, "failure_reasons": reasons, "outcome": outcome,
            "accepted": outcome in ("completed", "completed_partial_allowed")}


def _freeze_module() -> Any:
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", REPO / "scripts/freeze_failopen_baseline.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _guard_module() -> Any:
    spec = importlib.util.spec_from_file_location("icfa_guard", REPO / "momentum/FeatureEngineering/memory_guard.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _payload() -> Dict[str, Any]:
    return {
        "timeframes": {"primary": PRIMARY, "training": list(TRAINING), "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {"enabled": False},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }


def _window() -> Dict[str, str]:
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(REPO / "data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f[f"/{SYMBOL}/{PRIMARY}/data"]["timestamp"]).max()), unit="s", tz="UTC")
    return {"start": (end - pd.Timedelta(days=DAYS)).strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}


def _child(work: Path, result_path: Path) -> int:
    """子行程：正式生成（原設定）；結果分類寫 JSON。"""
    sys.path.insert(0, str(REPO))
    from momentum.FeatureEngineering import memory_budget as mb
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    window = _window()
    out: Dict[str, Any] = {"window": window, "payload": _payload()}
    t0 = time.monotonic()
    try:
        factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines"), validate_continuity=False)
        factory._storage = FeatureStorage(str(work / "features"))
        res = factory.generate_features(SYMBOL, PRIMARY, config_override=_payload(), force_regenerate=True,
                                        start_date=window["start"], end_date=window["end"], persist=True)
        meta = dict(getattr(res, "metadata", {}) or {})
        out.update({"outcome": "completed", "feature_count": int(res.feature_count),
                    "config_hash": str(meta.get("config_hash")),
                    "run_status": meta.get("run_status"), "quality_status": meta.get("quality_status"),
                    "failure_reasons": meta.get("failure_reasons"),
                    "memory_route": meta.get("memory_route"), "memory_budget": meta.get("memory_budget")})
    except (mb.GenerationMemoryBudgetExceeded, mb.MemoryMeasurementUnavailable) as exc:
        out.update({"outcome": "fail_closed", "error_type": type(exc).__name__, "error": str(exc)[:4000]})
    except Exception as exc:  # noqa: BLE001 — 其他例外照記，不當作完成
        out.update({"outcome": "error", "error_type": type(exc).__name__, "error": str(exc)[:4000]})
    out["elapsed_s"] = round(time.monotonic() - t0, 2)
    result_path.write_text(json.dumps(out, ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    return 0 if out["outcome"] == "completed" else 1


def _dir_bytes(root: Path) -> int:
    total = 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            try:
                total += os.lstat(os.path.join(base, name)).st_blocks * 512
            except OSError:
                pass
    return total


def _disk_precheck(work: Path) -> Dict[str, Any]:
    """§G 開跑前置：Σ 週期 D（全史列數）＋4 GiB ≤ 磁碟剩餘。"""
    import h5py

    sys.path.insert(0, str(REPO))
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines"), validate_continuity=False)
    config = factory._resolve_config(_payload())
    per_tf: Dict[str, int] = {}
    with h5py.File(REPO / "data_cache/feature_klines/kline_cache.h5", "r") as f:
        for tf in TRAINING:
            rows = int(f[f"/{SYMBOL}/{tf}/data"].shape[0])
            per_tf[tf] = int(factory.estimate_generation_disk(config, rows, 5))
    st = os.statvfs(work)
    free = int(st.f_bavail) * int(st.f_frsize)
    need = sum(per_tf.values()) + DISK_FLOOR
    return {"per_tf_D_bytes": per_tf, "required_bytes": need, "free_bytes": free, "ok": free >= need}


def _summarize_checks(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"events": 0}
    by: Dict[str, Dict[str, Any]] = {}
    routes: List[Dict[str, Any]] = []
    refusals: List[Dict[str, Any]] = []
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        total += 1
        if event.get("event") == "memory_route" or "point" in event:
            routes.append(event)
        if event.get("event") != "check":
            continue
        branch = str(event.get("branch"))
        entry = by.setdefault(branch, {"checks": 0, "max_planned": 0, "min_A": None, "results": {}})
        entry["checks"] += 1
        entry["max_planned"] = max(entry["max_planned"], int(event.get("planned") or 0))
        if event.get("A") is not None:
            entry["min_A"] = int(event["A"]) if entry["min_A"] is None else min(entry["min_A"], int(event["A"]))
        result = str(event.get("result"))
        entry["results"][result] = entry["results"].get(result, 0) + 1
        if result != "ok":
            refusals.append(event)
    return {"events": total, "by_branch": by, "refusals": refusals[:50], "routes": routes[:50]}


def annotate(receipt_path: Path) -> int:
    """以工作目錄內成品 manifest 補收據之品質狀態（run_status／quality_status／failure_reasons；讀檔、不重跑）。"""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.update({"schema_version": 1, "command": COMMAND, "exit_code": receipt.get("rc")})
    manifests = sorted(Path(receipt["work_dir"]).rglob("feature_manifest.json"))
    receipt["manifests"] = []
    for path in manifests:
        data = json.loads(path.read_text(encoding="utf-8"))
        receipt["manifests"].append({"path": str(path.relative_to(receipt["work_dir"])),
                                     "run_status": data.get("run_status"), "quality_status": data.get("quality_status"),
                                     "failure_reasons": data.get("failure_reasons")})
    # 完成判定一律經 classify（記錄之行程結局＋成品 manifest 之品質原因；不重跑）
    reasons = receipt["child"].get("failure_reasons")
    if reasons is None and receipt["manifests"]:
        reasons = receipt["manifests"][0].get("failure_reasons")
    verdict = classify(int(receipt.get("rc") if receipt.get("rc") is not None else -1),
                       disk_watchdog=receipt.get("stop_reason") == "disk_watchdog",
                       guard_abort=bool(receipt.get("guard_abort_receipts")), child=receipt.get("child") or {},
                       failure_reasons=reasons)
    receipt.update({"outcome": verdict["outcome"], "classification": verdict,
                    "exit_code": 0 if verdict["accepted"] else 1})
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt["manifests"], ensure_ascii=False))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotate", action="store_true", help="以工作目錄內成品 manifest 補收據品質狀態")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--work")
    parser.add_argument("--result")
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    if args.annotate:
        return annotate(Path(args.receipt))
    if args.child:
        return _child(Path(args.work), Path(args.result))

    stamp = time.strftime("%Y%m%d")
    receipt_path = Path(args.receipt or REPO / f"handoffs/run_receipts/{stamp}-icfirstalign-f2-acceptance.json")
    work = Path(tempfile.mkdtemp(prefix="icfa_f2_"))
    precheck = _disk_precheck(work)
    receipt: Dict[str, Any] = {
        "schema_version": 1, "command": COMMAND, "exit_code": None,
        "probe": "handoffs/run_receipts/icfirstalign_probes/f2_acceptance_probe.py",
        "spec": "docs/ICFIRSTALIGN_SPEC.md v40 §G 記憶體驗收／Task 4.4",
        "setting": {"symbol": SYMBOL, "primary": PRIMARY, "training": TRAINING, "public_window_days": DAYS,
                    "warmup": "全史（預設）", "l1": "完整預設", "payload": _payload()},
        "disk_precheck": precheck, "time_start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if not precheck["ok"]:
        receipt["outcome"] = "not_started_disk_precheck"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"outcome": receipt["outcome"], **precheck}, ensure_ascii=False))
        return 2

    freeze = _freeze_module()
    env = {**os.environ, **freeze.FIXED_ENV, "FFACT_LAYER1_PARALLEL": "0", "FFACT_MULTI_TF_PARALLEL": "0",
           "PYTHONPATH": str(REPO), "PYTHONHASHSEED": "0", "FFACT_CGSA_WORK_DIR": str(work / "cgsa"),
           "FFACT_FEATURE_REGISTRY_PATH": str(work / "features" / "registry.json"),
           "ICFA_CHECK_LOG": str(work / "check_log.jsonl")}
    result_path = work / "child_result.json"
    timeline_path = receipt_path.with_suffix(".timeline.jsonl")
    time_log = work / "time.log"
    cmd = ["/usr/bin/time", "-l", "-o", str(time_log), sys.executable, str(Path(__file__).resolve()), "--child",
           "--work", str(work), "--result", str(result_path)]
    guard = _guard_module()
    system = guard._System()
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=str(REPO), env=env, stdout=open(work / "child.log", "w"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    stop_reason: Optional[str] = None
    peaks = {"tree_footprint": 0, "swap_used": 0, "work_dir_bytes": 0, "min_swap_volume_free": None}
    pressure_hist: Dict[str, int] = {}
    last_walk = 0.0
    with open(timeline_path, "w", encoding="utf-8") as timeline:
        while proc.poll() is None:
            members = system.tree(proc.pid)
            footprint = sum((system.rusage(p) or (0, 0))[0] for p in members)
            free, _cap = system.swap_volume()
            try:
                pressure = system.pressure()
            except OSError:
                pressure = -1
            parts = {}
            try:
                parts = system.available_parts()
            except OSError:
                pass
            row = {"t": round(time.monotonic() - t0, 2), "tree_footprint": footprint, "pressure": pressure,
                   "swap_volume_free": free, "swap_avail": parts.get("swap_avail_bytes")}
            if time.monotonic() - last_walk >= WALK_EVERY_S:
                row["work_dir_bytes"] = _dir_bytes(work)
                peaks["work_dir_bytes"] = max(peaks["work_dir_bytes"], row["work_dir_bytes"])
                last_walk = time.monotonic()
            peaks["tree_footprint"] = max(peaks["tree_footprint"], footprint)
            peaks["min_swap_volume_free"] = free if peaks["min_swap_volume_free"] is None else min(
                peaks["min_swap_volume_free"], free)
            pressure_hist[str(pressure)] = pressure_hist.get(str(pressure), 0) + 1
            timeline.write(json.dumps(row) + "\n")
            timeline.flush()
            if free < DISK_FLOOR:
                stop_reason = "disk_watchdog"
                os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(0.5)
    rc = proc.wait()
    wall = time.monotonic() - t0
    child = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
    time_text = time_log.read_text(encoding="utf-8") if time_log.exists() else ""

    def _time_field(label: str) -> Optional[int]:
        for line in time_text.splitlines():
            if line.strip().endswith(label):
                return int(line.split()[0])
        return None

    guard_abort = sorted(str(p) for p in work.rglob("memory_guard_abort.json"))
    verdict = classify(rc, disk_watchdog=stop_reason == "disk_watchdog", guard_abort=bool(guard_abort), child=child,
                       failure_reasons=child.get("failure_reasons"))
    stop_reason = stop_reason or verdict["process_outcome"]
    receipt.update({
        "outcome": verdict["outcome"], "classification": verdict,
        "stop_reason": stop_reason, "rc": rc, "exit_code": 0 if verdict["accepted"] else 1,
        "wall_seconds": round(wall, 2), "child": child,
        "peak_footprint_bytes_time_l": _time_field("peak memory footprint"),
        "max_resident_bytes_time_l": _time_field("maximum resident set size"),
        "sampled_peaks": peaks, "pressure_histogram": pressure_hist,
        "guard_abort_receipts": [json.loads(Path(p).read_text(encoding="utf-8")) for p in guard_abort],
        "checks": _summarize_checks(work / "check_log.jsonl"),
        "timeline_file": str(timeline_path.relative_to(REPO)) if timeline_path.is_relative_to(REPO) else str(timeline_path),
        "work_dir": str(work), "time_end": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": receipt["outcome"], "stop_reason": stop_reason, "wall_s": receipt["wall_seconds"],
                      "peak_footprint": receipt["peak_footprint_bytes_time_l"]}, ensure_ascii=False))
    return 0 if verdict["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
