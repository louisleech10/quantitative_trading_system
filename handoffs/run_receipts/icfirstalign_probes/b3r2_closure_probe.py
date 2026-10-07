#!/usr/bin/env python3
"""b3 review-r2: re-run r1 four counterexamples against 3e605c00 (+ nesting/st_dev)."""
from __future__ import annotations

import json
import os
import pickle
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE = Path(os.environ.get("PROBE_BASE", "/tmp/icfa_b3r2_w1/probe_state"))
BASE.mkdir(parents=True, exist_ok=True)
ROOT = Path(os.environ.get("PROBE_ROOT", "/tmp/icfa_b3r2_w1"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from momentum.FeatureEngineering import memory_budget as mb
from momentum.FeatureEngineering import memory_guard as mg
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from tests.feature_engineering import icfirstalign_helpers as h
import scripts.freeze_icfirstalign_baseline as frz


def scheduler_exit() -> dict:
    release = threading.Event()
    started = threading.Event()
    executors = []
    shutdowns = []

    class Executor(ThreadPoolExecutor):
        def shutdown(self, *a, **kw):
            shutdowns.append(True)
            return super().shutdown(*a, **kw)

    def factory(n):
        if executors:
            assert started.wait(2)
            raise OSError("injected second executor creation failure")
        obj = Executor(n)
        executors.append(obj)
        return obj

    def worker(desc, payload):
        started.set()
        release.wait(5)
        return payload

    def identity():
        return (threading.get_ident(), 0.0)

    sched = mb.MemoryBudgetScheduler(
        1000,
        domain_dir=BASE / "sched",
        max_workers=2,
        executor_factory=factory,
        read_system=lambda: (1000, 1, False, 10, ()),
        read_task_footprint=lambda task: 10,
        aux_startup_envelope=1,
        task_identity=identity,
    )
    timer = threading.Timer(0.5, release.set)
    timer.start()
    try:
        try:
            sched.run(
                [mb.Task("A", 100, 1), mb.Task("B", 100, 2)],
                worker,
                lambda p: p,
                lambda w: None,
            )
            err = None
        except OSError as exc:
            err = str(exc)
        return {
            "error": err,
            "started": started.is_set(),
            "shutdowns_at_exit": len(shutdowns),
            "worker_alive_at_exit": any(t.is_alive() for ex in executors for t in ex._threads),
            "A_status": sched._tasks["A"].status,
        }
    finally:
        release.set()
        timer.cancel()
        for ex in executors:
            ex.shutdown(wait=True)


def preflight_scope() -> dict:
    fac = h.make_factory(BASE / "features")
    observed: dict = {}
    calls: list = []

    class StopProbe(Exception):
        pass

    class Handle:
        pid = 424241
        extra = {"checkpoint_file": None, "process": None}

        def stop(self):
            return None

    def fake_start(run_dir, run_id, **k):
        calls.append(str(run_dir))
        return Handle()

    def gate(*a, **kw):
        observed.update(
            active=mb.active_context() is not None,
            mapping_root=str(mb.current_mapping_root()),
            run_dir=str(mb.current_run_dir()),
            stop_dir=str(mb.active_context().stop_dir) if mb.active_context() else None,
        )
        raise StopProbe()

    with patch.object(fac, "_assert_generation_memory_preconditions", lambda *a, **k: None), patch.object(
        fac, "_run_calibration_gate", gate
    ), patch.object(mb, "start_guard", fake_start):
        try:
            fac.generate_features(
                h.SYMBOL,
                h.PRIMARY,
                config_override=frz.s3_payload(True),
                start_date=h.S2_WINDOW[0],
                end_date=h.S2_WINDOW[1],
                persist=True,
            )
        except StopProbe:
            pass
        observed["guard_start_calls"] = len(calls)
        if calls:
            observed["guard_run_dir"] = calls[0]
    return observed


def serial_budget() -> list:
    fac = h.make_factory(BASE / "serial")
    raw = h.kline_close().iloc[-800:].to_frame()
    out = []
    for partial in [False, True]:
        cfg = fac._resolve_config(h.s2_payload(["12h", "4h"], allow_partial_timeframes=partial))
        gen = MultiTFGenerator(fac, cfg)
        err = mb.GenerationMemoryBudgetExceeded("Layer 3", 100, 200, 250, "本程式超上限")
        registry = MagicMock()
        registry._groups = {}
        skipped = []
        with patch.object(fac, "_layer0_data_ingestion", return_value=raw), patch.object(
            gen, "_run_tf_l1_l6_results", side_effect=err
        ):
            try:
                gen._process_timeframe_inroot(
                    h.SYMBOL,
                    "4h",
                    raw,
                    raw.index,
                    None,
                    None,
                    registry,
                    skipped,
                    {},
                    {},
                    {"dual_tf_l1_l6": 0, "alignment": 0},
                )
                serial = "returned normally"
            except Exception as exc:
                serial = type(exc).__name__
                same = exc is err
            else:
                same = False
        try:
            gen._accept_worker_result(err, registry, raw.index, [], {}, {}, {"alignment": 0})
            parallel = "returned normally"
        except Exception as exc:
            parallel = type(exc).__name__
        out.append(
            {
                "allow_partial": partial,
                "serial": serial,
                "serial_same_object": same,
                "parallel": parallel,
                "skipped": list(skipped),
            }
        )
    return out


def guard_alternating() -> dict:
    seq = [
        {"pressure_level": 4, "swap_volume_free_bytes": 10**20, "swap_volume_capacity_bytes": 0, "footprint": 0, "failed": []},
        {"pressure_level": 1, "swap_volume_free_bytes": 10**9, "swap_volume_capacity_bytes": 0, "footprint": 0, "failed": []},
        {"pressure_level": 1, "swap_volume_free_bytes": 10**20, "swap_volume_capacity_bytes": 0, "footprint": 101, "failed": []},
    ]

    class Readings:
        def __init__(self, *a):
            self.pos = 0

        def sample(self):
            if self.pos >= len(seq):
                mg._STOP = True
                return {"pressure_level": 1, "swap_volume_free_bytes": 10**20, "swap_volume_capacity_bytes": 0,
                        "footprint": 0, "failed": []}
            v = seq[self.pos]
            self.pos += 1
            return v

    killed = []

    def abort(args, system, reason, history):
        killed.append(reason)

    with patch.object(mg, "_System", lambda: object()), patch.object(mg, "_Readings", Readings), patch.object(
        mg, "_alive", lambda p: True
    ), patch.object(mg, "_write_atomic", lambda *a, **k: None), patch.object(mg, "_abort", abort):
        mg._STOP = False
        mg.main(
            ["--pid", "123456", "--run-dir", str(BASE), "--run-id", "probe", "--budget", "100", "--interval", "0.05"]
        )
    reasons = [mg._conditions(v, 100) for v in seq]
    return {
        "sample_condition_lists": reasons,
        "abort": killed,
        "closed_as_no_kill": killed == [],
    }


def nest_and_st_dev() -> dict:
    """After lease nest: one guard; prelease and run_dir same st_dev; abort copy name retained."""
    import subprocess

    base = BASE / "nest"
    base.mkdir(exist_ok=True)
    key = "BTCUSDT/1h/deadbeef"
    # mock guard so this probe never spawns a real memory_guard
    class Handle:
        pid = 424242
        extra = {"checkpoint_file": None, "process": None}

        def stop(self):
            return None

    import shutil

    live = None
    with patch.object(mb, "start_guard", lambda *a, **k: Handle()):
        scope = mb.begin_pre_lease_scope(base, key)
        try:
            pre_dev = scope.run_dir.stat().st_dev
            outer_stop = mb.active_context().stop_dir
            guard_pid = mb.active_context().guard_pid
            run_dir = base / "SYM" / "1h" / "hash"
            run_dir.mkdir(parents=True)
            proc = subprocess.Popen([sys.executable, "-c", "pass"])
            proc.wait()
            dead = base / f"{mb.PRE_LEASE_SCOPE_PREFIX}{mb._scope_key(key)}_dead"
            dead.mkdir()
            (dead / mb.SCOPE_OWNER_NAME).write_text(
                json.dumps({"pid": proc.pid, "start_time": 1.0}), encoding="utf-8"
            )
            (dead / mb.ABORT_RECEIPT_NAME).write_text(
                json.dumps({"trigger": "footprint_over_budget"}), encoding="utf-8"
            )
            live = base / f"{mb.PRE_LEASE_SCOPE_PREFIX}{mb._scope_key(key)}_live"
            live.mkdir()
            (live / mb.SCOPE_OWNER_NAME).write_text(
                json.dumps({"pid": os.getpid(), "start_time": mb.process_start_time(os.getpid())}),
                encoding="utf-8",
            )
            removed = mb.recover_orphan_pre_lease_scopes(base, key, run_dir, keep=scope.run_dir)
            nested = mb.begin_protected_run(run_dir, key)
            try:
                ctx = mb.active_context()
                result = {
                    "guard_pid_stable": ctx.guard_pid == guard_pid,
                    "nested_true": nested.nested is True,
                    "stop_dir_still_prelease": Path(ctx.stop_dir) == Path(outer_stop) == scope.run_dir,
                    "mapping_is_run": Path(ctx.mapping_root) == mb.mapping_root(run_dir),
                    "st_dev_equal": pre_dev == run_dir.stat().st_dev,
                    "orphan_removed": removed == [str(dead)],
                    "live_kept": live.exists(),
                    "abort_copy_exists": (run_dir / f"memory_guard_abort.prelease-{dead.name}.json").exists(),
                }
            finally:
                nested.close()
            return result
        finally:
            scope.close()
            if live is not None and live.exists():
                shutil.rmtree(live, ignore_errors=True)


def main() -> int:
    out = {
        "p1_01_preflight": preflight_scope(),
        "p1_02_scheduler": scheduler_exit(),
        "p1_03_serial": serial_budget(),
        "p2_04_guard": guard_alternating(),
        "nest_st_dev": nest_and_st_dev(),
    }
    # closure expectations
    p1 = out["p1_01_preflight"]
    out["p1_01_closed"] = (
        p1.get("active") is True
        and "icfa_prelease_" in (p1.get("mapping_root") or "")
        and p1.get("guard_start_calls") == 1
    )
    p2 = out["p1_02_scheduler"]
    out["p1_02_closed"] = (
        p2.get("shutdowns_at_exit") == 1
        and p2.get("worker_alive_at_exit") is False
        and p2.get("A_status") == "joined"
    )
    p3 = out["p1_03_serial"]
    out["p1_03_closed"] = all(
        row["serial"] == "GenerationMemoryBudgetExceeded"
        and row["parallel"] == "GenerationMemoryBudgetExceeded"
        and row["skipped"] == []
        and row["serial_same_object"]
        for row in p3
    )
    out["p2_04_closed"] = out["p2_04_guard"]["closed_as_no_kill"] is True
    out["all_four_closed"] = all(
        out[k] for k in ("p1_01_closed", "p1_02_closed", "p1_03_closed", "p2_04_closed")
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["all_four_closed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
