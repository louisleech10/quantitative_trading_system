"""Cleanup script for pre-fix Feature Factory artifacts (Step 6 of NAN_POISONING_INVESTIGATION.md).

Identifies Feature Factory output files (parquet / .npy / quality dashboards) generated
before the 2026-05-21 NaN poisoning fix and offers safe deletion.

A file is flagged as "stale" if ANY of:
  - It contains columns matching `<source>_pattern_*_<L2_op>` (e.g. *_Momentum_L*, *_Distance_*,
    *_SignedStrength_*, *_WorldQuant_*) — these can only come from the unguarded L2 path.
  - It contains columns matching `*_pattern_*_<agg>_w<window>` (e.g. _mean_w20, _rank_w60) —
    these can only come from the unguarded L3 path.
  - Its file mtime is older than the configured cutoff (default: 2026-05-21 00:00 local)
    AND it lives under a Feature Factory output directory.

Default mode is `--dry-run` — no files are deleted. Pass `--confirm` to actually delete.

Usage:
  PYTHONPATH="$PWD" venv/bin/python scripts/cleanup_pattern_nan_artifacts.py
  PYTHONPATH="$PWD" venv/bin/python scripts/cleanup_pattern_nan_artifacts.py --confirm
  PYTHONPATH="$PWD" venv/bin/python scripts/cleanup_pattern_nan_artifacts.py --cutoff 2026-05-21 --root data_cache
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None  # type: ignore[assignment]

# Directories under data_cache/ that hold Feature Factory output.
DEFAULT_SCAN_DIRS = (
    "features",
    "feature_preprocessing",
    "ml_pipelines",
    "cgsa_work",
)

L2_PATTERN_LEAK = re.compile(
    r"_pattern_[^_]+_(?:Momentum|Distance|SignedStrength|WorldQuant|Cross|Ratio)(?:_|$)"
)
L3_PATTERN_LEAK = re.compile(r"_pattern_.+?_(?:mean|std|min|max|skew|kurt|rank|zscore)_w\d+")


@dataclass
class ScanResult:
    path: Path
    size_bytes: int
    mtime: datetime
    leak_reason: Optional[str] = None  # "L2", "L3", or "mtime_only"
    leak_columns: List[str] = field(default_factory=list)


def _iter_candidate_files(root: Path) -> Iterable[Path]:
    suffixes = {".parquet", ".npy", ".json", ".h5"}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in suffixes:
            yield path


def _scan_parquet_columns(path: Path) -> List[str]:
    if pq is None:
        return []
    try:
        return list(pq.read_metadata(path).schema.names)
    except Exception:
        return []


def _classify(path: Path, cutoff: datetime) -> ScanResult:
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime)
    result = ScanResult(path=path, size_bytes=stat.st_size, mtime=mtime)

    if path.suffix == ".parquet":
        cols = _scan_parquet_columns(path)
        l2_hits = [c for c in cols if L2_PATTERN_LEAK.search(c)]
        l3_hits = [c for c in cols if L3_PATTERN_LEAK.search(c)]
        if l2_hits:
            result.leak_reason = "L2"
            result.leak_columns = l2_hits[:5]
            return result
        if l3_hits:
            result.leak_reason = "L3"
            result.leak_columns = l3_hits[:5]
            return result

    if mtime < cutoff:
        result.leak_reason = "mtime_only"

    return result


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data_cache", help="Base directory to scan")
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        default=list(DEFAULT_SCAN_DIRS),
        help="Subdirectories under root to scan",
    )
    parser.add_argument(
        "--cutoff",
        default="2026-05-21",
        help="Files modified strictly before this date (YYYY-MM-DD) are flagged",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete flagged files (default: dry-run, no deletion)",
    )
    parser.add_argument(
        "--skip-mtime-only",
        action="store_true",
        help="Only delete files with confirmed column-level leaks; ignore mtime-only matches",
    )
    args = parser.parse_args(argv)

    cutoff = datetime.strptime(args.cutoff, "%Y-%m-%d")
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2

    if pq is None:
        print("WARNING: pyarrow not installed — column-level leak detection disabled; "
              "only mtime heuristic will run.", file=sys.stderr)

    print(f"Scanning {root} (cutoff < {cutoff.date()}, mode={'DELETE' if args.confirm else 'DRY-RUN'})")
    print("=" * 80)

    flagged: List[ScanResult] = []
    scanned = 0
    for sub in args.scan_dirs:
        scan_root = root / sub
        if not scan_root.exists():
            continue
        for path in _iter_candidate_files(scan_root):
            scanned += 1
            res = _classify(path, cutoff)
            if res.leak_reason is None:
                continue
            if args.skip_mtime_only and res.leak_reason == "mtime_only":
                continue
            flagged.append(res)

    if not flagged:
        print(f"No stale artifacts found ({scanned} files scanned).")
        return 0

    print(f"Found {len(flagged)} stale file(s) (of {scanned} scanned):\n")
    by_reason: dict[str, int] = {}
    total_bytes = 0
    for res in flagged:
        by_reason[res.leak_reason or "?"] = by_reason.get(res.leak_reason or "?", 0) + 1
        total_bytes += res.size_bytes
        rel = res.path.relative_to(root)
        suffix = ""
        if res.leak_columns:
            suffix = f"  e.g. {res.leak_columns[0]}"
        print(f"  [{res.leak_reason:<10}] {_human_size(res.size_bytes):>8}  {rel}{suffix}")

    print(f"\nSummary: total {_human_size(total_bytes)} across {len(flagged)} files")
    for reason, n in sorted(by_reason.items()):
        print(f"  {reason}: {n}")

    if not args.confirm:
        print("\nDRY-RUN: no files deleted. Re-run with --confirm to actually delete.")
        return 0

    print("\nDeleting flagged files...")
    deleted = 0
    freed = 0
    for res in flagged:
        try:
            res.path.unlink()
            deleted += 1
            freed += res.size_bytes
        except OSError as exc:
            print(f"  FAILED to delete {res.path}: {exc}", file=sys.stderr)
    print(f"Deleted {deleted} files, freed {_human_size(freed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
