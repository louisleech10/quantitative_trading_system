"""PROBEWINSOR 偵察：完整生成（真實 kline、persist=True），現行碼 vs 模擬修正，記公開輸出逐欄指紋與品質中繼資料。

用法：python gen_compare.py <case> <mode current|fixed> <out.json> <work_dir>
case 取自 probe_depth.SHORT_CASES／CASES；work_dir 須為空目錄（輸出落於其下，跑完由呼叫端刪）。
"""
from __future__ import annotations

import json
import resource
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import probe_depth as pd_mod  # noqa: E402
from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.feature_factory import FeatureFactory  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
from tests.feature_engineering.ffstat_helpers import public_fingerprints  # noqa: E402


def main() -> int:
    case, mode, out, work = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
    primary, training, pp_enabled, build = pd_mod.resolve_case(case)
    payload = build(primary, training, pp_enabled)
    if mode == "fixed":
        original = FeatureFactory._calibration_winsorizer

        def patched(self, config, timeframe):
            if not config.preprocessing.enabled:
                return None
            return original(self, config, timeframe)

        FeatureFactory._calibration_winsorizer = patched
    elif mode != "current":
        raise SystemExit(f"unknown mode {mode}")
    work.mkdir(parents=True, exist_ok=True)
    sys_tmp = work / "sys_tmp"
    sys_tmp.mkdir(exist_ok=True)
    tempfile.tempdir = str(sys_tmp)
    root = work / "features"
    factory = create_feature_factory(cache_dir=pd_mod.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    t0 = time.time()
    result = factory.generate_features(pd_mod.SYMBOL, primary, config_override=payload, force_regenerate=True,
                                       start_date=pd_mod.WINDOW[0], end_date=pd_mod.WINDOW[1])
    elapsed = time.time() - t0
    md = result.metadata if isinstance(getattr(result, "metadata", None), dict) else {}
    import hashlib as _h

    late_bound = getattr(factory, "_public_warmup_late", None)
    late_list = sorted(late_bound[1]) if late_bound else None
    probe_state = {
        "rounds": list(getattr(factory, "_public_warmup_probe", []) or []),
        "late_count": None if late_list is None else len(late_list),
        "late_sha256": None if late_list is None else _h.sha256("\n".join(late_list).encode()).hexdigest(),
        "first_finite_sha256": _h.sha256(json.dumps(getattr(factory, "_public_warmup_first_finite", {}),
                                                    sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "config_hash": md.get("config_hash"),
    }

    def pick(d, *keys):
        for k in keys:
            if isinstance(d, dict) and k in d:
                return d[k]
        return None

    fps = public_fingerprints(root)
    found: dict = {}
    wanted = ("warmup_insufficient_columns", "stable_start", "quality_status", "warmup_probe",
              "warmup_doublings", "start_dependent_columns", "column_failure_reasons", "failure_reasons")
    key_paths: dict = {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in wanted and k not in found:
                    found[k] = v
                    key_paths[k] = path + "/" + k
                walk(v, path + "/" + str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node[:50]):
                walk(v, path + f"[{i}]")

    walk(md, "result.metadata")
    for p in sorted(root.rglob("*.json")):
        try:
            walk(json.loads(p.read_text(encoding="utf-8")), str(p.relative_to(root)))
        except Exception:
            continue
    warmup_cols = found.get("warmup_insufficient_columns")
    stable = found.get("stable_start")
    quality = found.get("quality_status")
    probe_rounds = found.get("warmup_probe")
    record = {
        "case": case,
        "mode": mode,
        "output_window": md.get("output_window"),
        "quality_status": quality if quality is not None else pick(md, "quality_status"),
        "warmup_insufficient_columns": warmup_cols,
        "stable_start_count": None if stable is None else len(stable),
        "stable_start": stable,
        "warmup_probe": probe_rounds,
        "probe_state": probe_state,
        "found_keys": {k: key_paths[k] for k in sorted(key_paths)},
        "other_found": {k: v for k, v in found.items() if k not in ("stable_start",)},
        "public_column_count": len(fps),
        "public_fingerprints": fps,
        "elapsed_seconds": round(elapsed, 2),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 1),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("case", "mode", "output_window", "quality_status",
                                             "public_column_count", "elapsed_seconds", "peak_rss_mb")},
                     ensure_ascii=False))
    print("warmup_insufficient:", None if warmup_cols is None else len(warmup_cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
