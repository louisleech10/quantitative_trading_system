"""V8 Golden Baseline Lite Registration.

從現有 data_cache/features/ETHUSDT/{config_hash}/ 的 892 parquet 直接生成
golden baseline，避免重跑 1800s benchmark。

策略:
- feature_names: 逐 group parquet 讀取 columns，集合化 + 排序
- column_sha256: 逐 group 計算每欄 sha256（streaming, 無 OOM 風險）
- overall_sha256: 對 sorted(column_sha256.values()) 串接後 sha256（次序無關）
- manifest: 紀錄 v8fix6 已知 metrics
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = REPO_ROOT / "data_cache" / "features" / "ETHUSDT" / "9e5c8a65c9cbd773a778e8c99ca634ec"
BASELINE_REGISTRY_DIR = REPO_ROOT / "results" / "full_golden_baseline"

# v8fix6 已知 runtime metrics（來自 results/benchmark_run_v8fix6.log）
V8FIX6_METRICS = {
    "elapsed_seconds": 1794.51,
    "peak_rss_mb": 1956.0,
    "feature_count": 434720,
    "groups": 858,
    "dtype": "float16",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register baseline from existing parquet outputs")
    parser.add_argument("--label-suffix", default="v8fix6", help="baseline_id suffix, e.g. v8fix7c")
    parser.add_argument("--elapsed-seconds", type=float, default=V8FIX6_METRICS["elapsed_seconds"])
    parser.add_argument("--peak-rss-mb", type=float, default=V8FIX6_METRICS["peak_rss_mb"])
    parser.add_argument("--label", default="V8 Golden (v8fix6 - Plan A streaming persist + hardware auto-tier)")
    parser.add_argument("--v7-speedup", type=float, default=4.12)
    parser.add_argument("--peak-rss-reduction", type=float, default=0.51)
    return parser.parse_args()


def column_sha256(series: pd.Series) -> str:
    arr = series.to_numpy()
    if arr.dtype != np.float16:
        arr = arr.astype(np.float16, copy=False)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def main() -> int:
    args = _parse_args()
    if not FEATURES_DIR.is_dir():
        print(f"[FAIL] features dir not found: {FEATURES_DIR}")
        return 1

    parquet_files = sorted(FEATURES_DIR.glob("*.parquet"))
    if not parquet_files:
        print(f"[FAIL] no parquet files in {FEATURES_DIR}")
        return 1

    print(f"[Info] 共 {len(parquet_files)} 個 parquet groups，開始計算 column-level sha256...")

    feature_names: list[str] = []
    col_checksums: dict[str, str] = {}
    rows_seen: set[int] = set()

    for idx, pq in enumerate(parquet_files, 1):
        df = pd.read_parquet(pq)
        rows_seen.add(int(df.shape[0]))
        # group_key = parquet stem（含 TF prefix），避免跨 TF 同欄名衝突
        group_key = pq.stem
        for col in df.columns:
            full_name = f"{group_key}::{col}"
            feature_names.append(full_name)
            col_checksums[full_name] = column_sha256(df[col])
        if idx % 100 == 0:
            print(f"  ... {idx}/{len(parquet_files)} groups processed, total cols={len(feature_names):,}")
        del df

    feature_names_unique = sorted(set(feature_names))
    if len(feature_names_unique) != len(feature_names):
        print(f"[WARN] 重複 (group::col): total={len(feature_names)}, unique={len(feature_names_unique)}")

    # overall_sha256：對 sorted(col_sha) 串接後 hash（次序無關 - 適合 streaming baseline）
    overall_h = hashlib.sha256()
    for col_name in feature_names_unique:
        overall_h.update(col_checksums[col_name].encode("ascii"))
    overall_sha = overall_h.hexdigest()

    rows = max(rows_seen) if rows_seen else 0
    print(f"[Info] feature_count={len(feature_names_unique):,}, max_rows={rows:,}, overall_sha={overall_sha[:16]}...")

    # 建立 baseline 目錄
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    baseline_id = f"{ts}_ETHUSDT_1h_full_multitf_{args.label_suffix}"
    baseline_dir = BASELINE_REGISTRY_DIR / baseline_id
    artifacts_dir = baseline_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    def write_json(path: Path, payload) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    write_json(artifacts_dir / "feature_names.json", feature_names_unique)
    write_json(
        artifacts_dir / "checksums.json",
        {
            "overall_dataframe_sha256": overall_sha,
            "overall_sha256_method": "order_invariant_concat_of_sorted_col_sha256",
            "column_sha256": col_checksums,
            "config_hash": "9e5c8a65c9cbd773a778e8c99ca634ec",
        },
    )
    write_json(
        artifacts_dir / "metadata_runtime.json",
        {
            "config_hash": "9e5c8a65c9cbd773a778e8c99ca634ec",
            "source": "lite_registration_from_parquet",
            "note": "Generated from existing v8fix6 parquet output, NOT from full benchmark re-run",
        },
    )

    perf_metrics = {
        "elapsed_seconds": args.elapsed_seconds,
        "peak_rss_mb": args.peak_rss_mb,
        "feature_count": len(feature_names_unique),
        "groups": len(parquet_files),
        "dtype": "float16",
    }
    manifest = {
        "baseline_id": baseline_id,
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "preset": "full",
        "training_tfs": ["1h", "12h"],
        "force_regenerate": True,
        "shape": {"rows": rows, "columns": len(feature_names_unique)},
        "layer_counts": {},
        "performance": perf_metrics,
        "checksums": {
            "overall_dataframe_sha256": overall_sha,
            "overall_sha256_method": "order_invariant_concat_of_sorted_col_sha256",
            "feature_name_count": len(feature_names_unique),
            "config_hash": "9e5c8a65c9cbd773a778e8c99ca634ec",
        },
        "label": args.label,
        "v7_speedup": args.v7_speedup,
        "peak_rss_reduction_vs_v7": args.peak_rss_reduction,
        "status": "official",
        "lite_baseline": True,
    }
    write_json(baseline_dir / "manifest.json", manifest)
    print(f"[Baseline] 已儲存至 {baseline_dir}")

    # 更新 registry.json
    registry_path = BASELINE_REGISTRY_DIR / "registry.json"
    registry: list = []
    if registry_path.is_file():
        try:
            existing = json.loads(registry_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                registry = existing
        except json.JSONDecodeError:
            print(f"[WARN] registry.json 解析失敗，將覆寫")

    registry.append(
        {
            "baseline_id": baseline_id,
            "label": manifest["label"],
            "created_at": manifest["created_at_utc"],
            "v7_baseline_speedup": args.v7_speedup,
            "peak_rss_reduction": args.peak_rss_reduction,
            "feature_count": len(feature_names_unique),
            "elapsed_seconds": args.elapsed_seconds,
            "peak_rss_mb": args.peak_rss_mb,
            "status": "official",
            "lite_baseline": True,
        }
    )
    write_json(registry_path, registry)
    print(f"[Registry] 已更新 {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
