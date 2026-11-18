"""L3 skew／kurt 存檔值之數學可達界檢查（TESTSEL I1b；docs/TESTSEL_I1_REDS_SPEC.md Task 2.4 先查）——
現存／新生成 run 之 L3 skew／kurt 存檔值必要條件檢查。

界（樣本統計量，bias=False；n＝窗長）：
- |skew| ≤ n−1 等值＋1 離群之 skew（可達最大）；
- （最平均兩點分佈之 kurt）≤ kurt ≤（n−1 等值＋1 離群之 kurt）。
界值以精確 oracle（tests/references/exact_moments.py）於該二極端窗型算出，放寬相對 1e-5 後**依欄位實際存檔型別量化**
（產品 `feature_storage._select_parquet_storage_array` 於往返安全時存 float16；IEEE 捨入單調 ⇒ 合法存檔值必在量化後端點內）。
越界＝數學上不可能且非存檔量化可解釋之值。I1b 實測：BTCUSDT/12h 0729db3a 未量化比對時 61,242 值「越界」，全部等於精確界值之
float16 量化（審查 r1 CODEX-R1-P1-01 指出）⇒ 量化後 0 越界。
用法：venv/bin/python scripts/l3_moment_bound_check.py <features_root 或 run_dir>... ；任一越界 ⇒ rc 1。
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

REL_TOL = 1e-5


@lru_cache(maxsize=None)
def bounds(n: int) -> Tuple[float, float, float]:
    """回 (|skew| 上界, kurt 下界, kurt 上界)。"""
    from tests.references.exact_moments import exact_rolling_skew_kurt

    spike = np.zeros(n); spike[-1] = 1.0
    sk_hi, ku_hi = exact_rolling_skew_kurt(spike, n)[-1]
    two = np.array(([0.0, 1.0] * n)[:n])
    ku_lo = exact_rolling_skew_kurt(two, n)[-1, 1]
    return float(abs(sk_hi)), float(ku_lo), float(ku_hi)


def _quantize(x: float, dtype: np.dtype) -> float:
    """端點依存檔型別最近捨入（單調）；非浮點型別按 float64。"""
    dt = np.dtype(dtype) if np.issubdtype(np.dtype(dtype), np.floating) else np.dtype(np.float64)
    return float(np.asarray(x, dtype=np.float64).astype(dt))


def violations(name: str, values: np.ndarray) -> int:
    """欄名須以 `_Skew-W<n>` 或 `_Kurt-W<n>` 結尾；`values` 須保留存檔型別（float16／float32／float64）。
    回越界值個數（非有限值不計）。"""
    stat = "Kurt" if "_Kurt-W" in name else ("Skew" if "_Skew-W" in name else None)
    if stat is None:
        return 0
    n = int(name.rsplit("W", 1)[1])
    sk, lo, hi = bounds(n)
    arr = np.asarray(values)
    dt = arr.dtype
    v = arr.astype(np.float64)
    v = v[np.isfinite(v)]
    if stat == "Kurt":
        hi_q = _quantize(hi * (1 + REL_TOL), dt)
        lo_q = _quantize(lo - REL_TOL * abs(lo), dt)
        return int(((v > hi_q) | (v < lo_q)).sum())
    sk_q = _quantize(sk * (1 + REL_TOL), dt)
    return int((np.abs(v) > sk_q).sum())


def scan_run(run_dir: Path) -> Dict[str, int]:
    import pyarrow.parquet as pq

    from scripts._manifest_listing import declared_group_files, load_manifest

    bad: Dict[str, int] = {}
    if "raw" not in (load_manifest(run_dir).get("artifacts") or {}):
        return bad  # manifest 無 raw artifact（非 V2 run 或 raw 未宣告）⇒ 無可檢之特徵檔
    # 特徵檔只自 manifest 宣告導出（PRE-PROV：不得以檔名掃描 run 目錄取特徵）
    for f in declared_group_files(run_dir, "raw"):
        if "_Skew" not in f.name and "_Kurt" not in f.name:
            continue
        table = pq.read_table(f)
        for name in table.column_names:
            n_bad = violations(name, table.column(name).to_numpy(zero_copy_only=False))
            if n_bad:
                bad[name] = n_bad
    return bad


def _runs(paths: Iterable[str]) -> List[Path]:
    from scripts._manifest_listing import feature_run_dirs

    out: List[Path] = []
    for p in map(Path, paths):
        out.extend(feature_run_dirs(p))  # 以 manifest 定位 run 目錄（不列舉特徵檔）
    return out


def main(argv: List[str]) -> int:
    rc = 0
    for run in _runs(argv):
        bad = scan_run(run)
        print(f"{run} bad_cols={len(bad)} bad_values={sum(bad.values())}")
        if bad:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
