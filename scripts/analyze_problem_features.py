"""Full per-feature problem-classification report for a Feature Factory task.

Scans every L7_raw parquet, computes IEEE-754 NaN counts (parquet null_count is
unreliable for CGSA tasks — see api/services/feature_factory_service.py
_build_data_quality_cgsa), then classifies all problem features into
mutually-exclusive buckets:

  - HIGH_NAN     nan_ratio > 0.05 (matches backend _DATA_QUALITY_HIGH_NAN_THRESHOLD)
  - MID_HOLE     NaN inside [first_valid, last_valid] (data corruption / missing block)
  - TRAILING     last_valid < T-1 (no high_nan & no mid_hole)
  - WARMUP_ONLY  first_valid > 0 (no other defect — design-driven)
  - CLEAN        no NaN at all

A single feature can fall into multiple problem buckets (e.g. high_nan AND
mid_hole). Set `problem_class` is the strongest defect in this order:
HIGH_NAN > MID_HOLE > TRAILING > WARMUP_ONLY > CLEAN.

Outputs three artifacts under <task_dir>/problem_analysis_<timestamp>/:
  - all_features.parquet        — every feature with full per-feature stats
  - problem_features.csv        — only problem features (HIGH_NAN/MID_HOLE/TRAILING)
  - summary.md                  — human-readable cross-tab report
  - summary.json                — machine-readable cross-tab report

Usage:
    PYTHONPATH=. venv/bin/python scripts/analyze_problem_features.py \\
        --task-dir data_cache/features/ETHUSDT/1h/c4403c2493edaf57e33d058336ace686

FF-NAME Task 3.1／3.4：欄名語意一律 `parse_feature_name`；`--task-dir` 須為 canonical run（特徵根下
`<symbol>/<timeframe>/<config_hash>/` 且 registry 有條目），群組只經 FeatureReader 讀取（含命名世代閘）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from momentum.factories import create_feature_library, create_feature_reader
from momentum.FeatureEngineering.feature_naming import FeatureNameParseError, parse_feature_name


HIGH_NAN_THRESHOLD = 0.05  # matches _DATA_QUALITY_HIGH_NAN_THRESHOLD


def parse_group_id(group_id: str) -> tuple[str, str, str]:
    """群組 id `{timeframe}_{layer}_{family}`（manifest 之群組鍵，非特徵欄名）→ (tf, layer, family)。"""
    parts = str(group_id).split("_", 2)
    if len(parts) < 3:
        return ("?", "?", str(group_id))
    return (parts[0], parts[1], parts[2])


def parse_source(col_name: str) -> str:
    """欄之 source 段（`parse_feature_name`）；不合文法 ⇒ '?'。"""
    try:
        return parse_feature_name(col_name).source
    except FeatureNameParseError:
        return "?"


def parse_base_indicator(col_name: str) -> str:
    """欄之 `<category>/<indicator>`（`parse_feature_name`）；不合文法 ⇒ 原欄名。"""
    try:
        identity = parse_feature_name(col_name)
    except FeatureNameParseError:
        return col_name
    return f"{identity.category}/{identity.indicator}"


def scan_frame(frame: pd.DataFrame) -> list[dict]:
    """Scan one feature group (DataFrame read via FeatureReader). Returns one dict per column.

    Per-column dict:
      name, total_rows, nan_count, nan_ratio,
      first_valid, last_valid, mid_hole_count, trailing_length, leading_length,
      all_nan
    """
    T = len(frame)
    out: list[dict] = []
    if T == 0:
        return out

    for col_name in frame.columns:
        # IEEE-754 NaN + null detection（parquet metadata 之 null_count 不計 NaN 位元型樣）
        mask = frame[col_name].isna().to_numpy()

        nan_count = int(mask.sum())
        notna = ~mask
        has_any = bool(notna.any())

        if not has_any:
            first_valid = T
            last_valid = -1
            mid_hole = 0
            leading = T
            trailing = 0
        else:
            first_valid = int(notna.argmax())
            last_valid = T - 1 - int(notna[::-1].argmax())
            leading = first_valid
            trailing = T - 1 - last_valid
            # Mid-hole = NaNs strictly inside [first_valid, last_valid]
            mid_hole = nan_count - leading - trailing
            if mid_hole < 0:
                mid_hole = 0

        out.append({
            "name": col_name,
            "total_rows": T,
            "nan_count": nan_count,
            "nan_ratio": nan_count / T,
            "first_valid": first_valid,
            "last_valid": last_valid,
            "leading_nan": leading,
            "trailing_nan": trailing,
            "mid_hole_count": mid_hole,
            "all_nan": not has_any,
        })

    return out


def classify(row: dict) -> str:
    """Mutually-exclusive defect class (strongest defect wins)."""
    if row["nan_ratio"] > HIGH_NAN_THRESHOLD:
        return "HIGH_NAN"
    if row["mid_hole_count"] > 0:
        return "MID_HOLE"
    if row["trailing_nan"] > 0:
        return "TRAILING"
    if row["leading_nan"] > 0:
        return "WARMUP_ONLY"
    return "CLEAN"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, help="Path to task directory containing raw/ subfolder")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: <task_dir>/problem_analysis_<ts>)")
    args = parser.parse_args()

    task_dir = Path(args.task_dir).resolve()
    library = create_feature_library()
    try:
        run = library.resolve_canonical_run(task_dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    reader = create_feature_reader(str(run.feature_root))
    group_names = list(reader.load_run_manifest_v2(run.symbol, run.timeframe, run.config_hash)
                       .get("artifacts", {}).get("raw", {}).get("groups", {}))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else task_dir / f"problem_analysis_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[scan] task_dir={task_dir}")
    print(f"[scan] {len(group_names)} raw groups to scan")
    print(f"[scan] output: {out_dir}")

    # ---- pass 1: scan every column ----
    all_rows: list[dict] = []
    t0 = time.monotonic()
    last_log = t0

    def _warn_unreadable(group: str, path: Path, exc: Exception) -> None:
        print(f"[warn] failed to scan {group} ({path.name}): {exc}", file=sys.stderr)

    groups = reader.stream_groups_v2(run.symbol, run.timeframe, run.config_hash, artifact_kind="raw",
                                     sort_groups=True, on_read_error=_warn_unreadable)
    for i, (group_id, frame) in enumerate(groups, 1):
        tf, layer, family = parse_group_id(group_id)
        for row in scan_frame(frame):
            row["timeframe_file"] = tf
            row["layer_file"] = layer
            row["family_file"] = family
            all_rows.append(row)
        del frame

        now = time.monotonic()
        if i == 1 or i == len(group_names) or (now - last_log) > 10:
            elapsed = now - t0
            pct = i / max(len(group_names), 1) * 100
            print(f"[scan] {i}/{len(group_names)} ({pct:.1f}%), {len(all_rows):,} cols, {elapsed:.1f}s")
            last_log = now

    print(f"[scan] complete: {len(all_rows):,} columns in {time.monotonic()-t0:.1f}s")

    df = pd.DataFrame(all_rows)
    df["source"] = df["name"].map(parse_source)
    df["base_indicator"] = df["name"].map(parse_base_indicator)
    df["problem_class"] = df.apply(classify, axis=1)

    # ---- write artifacts ----
    df.to_parquet(out_dir / "all_features.parquet", index=False)
    problem_df = df[df["problem_class"] != "CLEAN"].copy()
    problem_df = problem_df.sort_values(["problem_class", "nan_ratio"], ascending=[True, False])
    problem_df.to_csv(out_dir / "problem_features.csv", index=False)

    # ---- summary ----
    summary: dict = {}
    summary["task_dir"] = str(task_dir)
    summary["scanned_files"] = len(group_names)
    summary["total_features"] = len(df)
    summary["total_rows"] = int(df["total_rows"].iloc[0]) if len(df) else 0

    class_counts = df["problem_class"].value_counts().to_dict()
    summary["problem_class_counts"] = {str(k): int(v) for k, v in class_counts.items()}
    summary["problem_total"] = int(sum(v for k, v in class_counts.items() if k != "CLEAN"))

    # cross-tabs for each problem class
    summary["by_class"] = {}
    for cls in ["HIGH_NAN", "MID_HOLE", "TRAILING", "WARMUP_ONLY"]:
        sub = df[df["problem_class"] == cls]
        if sub.empty:
            continue
        summary["by_class"][cls] = {
            "count": int(len(sub)),
            "by_source": {str(k): int(v) for k, v in sub["source"].value_counts().to_dict().items()},
            "by_layer_file": {str(k): int(v) for k, v in sub["layer_file"].value_counts().to_dict().items()},
            "by_timeframe": {str(k): int(v) for k, v in sub["timeframe_file"].value_counts().to_dict().items()},
            "top_base_indicators": [
                {"name": str(name), "count": int(cnt)}
                for name, cnt in sub["base_indicator"].value_counts().head(30).items()
            ],
            "top_families": [
                {"name": str(name), "count": int(cnt)}
                for name, cnt in sub["family_file"].value_counts().head(20).items()
            ],
        }

    # nan_ratio buckets for HIGH_NAN
    if "HIGH_NAN" in df["problem_class"].values:
        hn = df[df["problem_class"] == "HIGH_NAN"]
        buckets = pd.cut(
            hn["nan_ratio"],
            bins=[0, 0.10, 0.25, 0.50, 0.75, 0.95, 0.999, 1.0001],
            labels=["5-10%", "10-25%", "25-50%", "50-75%", "75-95%", "95-99.9%", "100%"],
            include_lowest=False,
        )
        summary["high_nan_ratio_buckets"] = {
            str(k): int(v) for k, v in buckets.value_counts().sort_index().to_dict().items()
        }

    # mid-hole stats
    if "MID_HOLE" in df["problem_class"].values:
        mh = df[df["problem_class"] == "MID_HOLE"]
        summary["mid_hole_stats"] = {
            "count": int(len(mh)),
            "total_holes": int(mh["mid_hole_count"].sum()),
            "max_holes_in_one_feature": int(mh["mid_hole_count"].max()),
            "mean_holes_per_feature": float(mh["mid_hole_count"].mean()),
        }

    # trailing stats
    if "TRAILING" in df["problem_class"].values:
        tr = df[df["problem_class"] == "TRAILING"]
        summary["trailing_stats"] = {
            "count": int(len(tr)),
            "max_trailing_len": int(tr["trailing_nan"].max()),
            "mean_trailing_len": float(tr["trailing_nan"].mean()),
        }

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ---- markdown report ----
    md_lines: list[str] = []
    md_lines.append(f"# Problem Features Report — {task_dir.name}")
    md_lines.append("")
    md_lines.append(f"Generated: {ts}  ")
    md_lines.append(f"Task dir: `{task_dir}`  ")
    md_lines.append(f"Scanned files: **{summary['scanned_files']}**  ")
    md_lines.append(f"Total features: **{summary['total_features']:,}**  ")
    md_lines.append(f"Total rows (T): **{summary['total_rows']:,}**  ")
    md_lines.append("")
    md_lines.append("## Defect class distribution (mutually exclusive — strongest wins)")
    md_lines.append("")
    md_lines.append("| Class | Count | % of all |")
    md_lines.append("|---|---:|---:|")
    total = summary["total_features"]
    for cls in ["HIGH_NAN", "MID_HOLE", "TRAILING", "WARMUP_ONLY", "CLEAN"]:
        cnt = summary["problem_class_counts"].get(cls, 0)
        pct = cnt / total * 100 if total else 0
        md_lines.append(f"| {cls} | {cnt:,} | {pct:.2f}% |")
    md_lines.append("")
    md_lines.append(f"**Total problem (non-CLEAN): {summary['problem_total']:,}**")
    md_lines.append("")

    if "high_nan_ratio_buckets" in summary:
        md_lines.append("## HIGH_NAN — nan_ratio buckets")
        md_lines.append("")
        md_lines.append("| Bucket | Count |")
        md_lines.append("|---|---:|")
        for k, v in summary["high_nan_ratio_buckets"].items():
            md_lines.append(f"| {k} | {v:,} |")
        md_lines.append("")

    for cls in ["HIGH_NAN", "MID_HOLE", "TRAILING", "WARMUP_ONLY"]:
        if cls not in summary["by_class"]:
            continue
        block = summary["by_class"][cls]
        md_lines.append(f"## {cls} — breakdown ({block['count']:,} features)")
        md_lines.append("")
        md_lines.append("### By source prefix")
        md_lines.append("")
        md_lines.append("| Source | Count |")
        md_lines.append("|---|---:|")
        for k, v in sorted(block["by_source"].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v:,} |")
        md_lines.append("")
        md_lines.append("### By layer (from filename)")
        md_lines.append("")
        md_lines.append("| Layer | Count |")
        md_lines.append("|---|---:|")
        for k, v in sorted(block["by_layer_file"].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v:,} |")
        md_lines.append("")
        md_lines.append("### By timeframe")
        md_lines.append("")
        md_lines.append("| TF | Count |")
        md_lines.append("|---|---:|")
        for k, v in sorted(block["by_timeframe"].items(), key=lambda x: -x[1]):
            md_lines.append(f"| {k} | {v:,} |")
        md_lines.append("")
        md_lines.append("### Top 30 base indicators")
        md_lines.append("")
        md_lines.append("| Base indicator | Count |")
        md_lines.append("|---|---:|")
        for item in block["top_base_indicators"]:
            md_lines.append(f"| `{item['name']}` | {item['count']:,} |")
        md_lines.append("")
        md_lines.append("### Top 20 files (one file ≈ one indicator family)")
        md_lines.append("")
        md_lines.append("| File family | Count |")
        md_lines.append("|---|---:|")
        for item in block["top_families"]:
            md_lines.append(f"| `{item['name']}` | {item['count']:,} |")
        md_lines.append("")

    if "mid_hole_stats" in summary:
        s = summary["mid_hole_stats"]
        md_lines.append("## MID_HOLE — depth stats")
        md_lines.append("")
        md_lines.append(f"- Total mid-hole NaNs across all features: **{s['total_holes']:,}**")
        md_lines.append(f"- Max holes in a single feature: **{s['max_holes_in_one_feature']:,}**")
        md_lines.append(f"- Mean holes per affected feature: **{s['mean_holes_per_feature']:.1f}**")
        md_lines.append("")

    if "trailing_stats" in summary:
        s = summary["trailing_stats"]
        md_lines.append("## TRAILING — depth stats")
        md_lines.append("")
        md_lines.append(f"- Max trailing length: **{s['max_trailing_len']:,}**")
        md_lines.append(f"- Mean trailing length: **{s['mean_trailing_len']:.1f}**")
        md_lines.append("")

    with open(out_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print()
    print(f"[done] all_features.parquet: {len(df):,} rows")
    print(f"[done] problem_features.csv: {len(problem_df):,} rows")
    print(f"[done] summary.md / summary.json written")
    print(f"[done] output: {out_dir}")


if __name__ == "__main__":
    main()
