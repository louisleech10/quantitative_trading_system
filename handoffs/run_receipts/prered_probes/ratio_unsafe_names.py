"""RATIOUNSAFE 預查（唯讀）：列真實 run 之落盤 parquet 中含 pattern 之欄名，並以現行判定逐一判。

用法：venv/bin/python <本檔> <run 目錄>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(run_dir: str) -> None:
    import pyarrow.parquet as pq

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import _is_ratio_unsafe_column

    names = set()
    for p in Path(run_dir).rglob("*.parquet"):
        if p.name == "timestamps.parquet":
            continue
        names.update(n for n in pq.read_schema(p).names if "pattern" in n)
    flagged = sorted(n for n in names if _is_ratio_unsafe_column(n))
    missed = sorted(n for n in names if not _is_ratio_unsafe_column(n))
    print("pattern_cols", len(names), "flagged", len(flagged), "missed", len(missed))
    print("missed_sample", missed[:8])
    print("flagged_sample", flagged[:4])


if __name__ == "__main__":
    main(sys.argv[1])
