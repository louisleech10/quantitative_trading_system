"""NOCAP Task 0.4（docs/NOCAP_SPEC.md）：記憶體／精確度／計算時間／檔案大小四項平衡之比較——改動後重量之四項與
`tests/_golden/balance/<模組>.json` 基準比，任一項明顯變差即 rc≠0；門檻寫於基準檔可審。

用法：`python3 scripts/balance_check.py <基準檔> <本次量測檔>`（rc 0＝四項皆在門檻內；1＝有變差；2＝輸入無效）。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

#: 預設門檻（基準檔可覆寫）：耗時或峰值 RSS 增逾 20%、精度差非零、檔案大小增逾 10% ⇒ 變差。
DEFAULT_THRESHOLDS = {"seconds_increase": 0.20, "peak_rss_increase": 0.20, "precision_max_abs_diff": 0.0,
                      "output_bytes_increase": 0.10}
MIN_POINTS = 3
_RELATIVE = (("seconds", "seconds_increase", "耗時"), ("peak_rss_bytes", "peak_rss_increase", "峰值 RSS"),
             ("output_bytes", "output_bytes_increase", "檔案大小"))


def _finite_nonneg(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def _points(record: Mapping[str, Any], label: str) -> Dict[float, Mapping[str, Any]]:
    """每點須含四項：seconds、peak_rss_bytes、output_bytes（有限非負）與 precision.{max_abs_diff（有限非負）、
    bitwise_equal（bool）}；缺欄或型別不符 ⇒ ValueError（缺資料不得當作無變差）。"""
    pts = record.get("points") or []
    for i, p in enumerate(pts):
        prec = p.get("precision") if isinstance(p, Mapping) else None
        if not (isinstance(p, Mapping) and all(_finite_nonneg(p.get(k)) for k in ("scale", "seconds", "peak_rss_bytes",
                                                                                   "output_bytes"))
                and isinstance(prec, Mapping) and _finite_nonneg(prec.get("max_abs_diff"))
                and isinstance(prec.get("bitwise_equal"), bool)):
            raise ValueError(f"{label} points[{i}] 四項欄位不齊或型別不符（須 seconds、peak_rss_bytes、output_bytes、"
                             "precision.max_abs_diff、precision.bitwise_equal）")
    by_scale = {float(p["scale"]): p for p in pts}
    if len(by_scale) < MIN_POINTS:
        raise ValueError(f"{label} 規模點 {len(by_scale)} 個 < {MIN_POINTS}（無成長曲線不可比）")
    return by_scale


def compare(baseline: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """逐規模點比四項；回變差之描述（空串列＝通過）。兩者 `identity.match` 之 entrypoint／hardware 不同 ⇒ ValueError。"""
    bm = (baseline.get("identity") or {}).get("match") or {}
    cm = (current.get("identity") or {}).get("match") or {}
    for key in ("entrypoint", "hardware"):
        if bm.get(key) != cm.get(key):
            raise ValueError(f"基準與本次之 {key} 不同（{bm.get(key)!r} ≠ {cm.get(key)!r}）⇒ 不可比")
    base, cur = _points(baseline, "基準"), _points(current, "本次")
    if set(base) != set(cur):
        raise ValueError(f"規模點不一致：基準 {sorted(base)}、本次 {sorted(cur)}")
    thr = {**DEFAULT_THRESHOLDS, **(baseline.get("thresholds") or {})}
    worse: List[str] = []
    for scale in sorted(base):
        b, c = base[scale], cur[scale]
        for field, key, name in _RELATIVE:
            bv, cv = float(b[field]), float(c[field])
            if bv > 0 and (cv - bv) / bv > thr[key]:
                worse.append(f"規模 {scale:g}：{name} {bv:g} → {cv:g}（+{(cv - bv) / bv:.1%} > {thr[key]:.0%}）")
            elif bv == 0 and cv > 0:
                worse.append(f"規模 {scale:g}：{name} 0 → {cv:g}")
        diff = float(c["precision"]["max_abs_diff"])
        if diff > thr["precision_max_abs_diff"]:
            worse.append(f"規模 {scale:g}：精度差 max_abs_diff {diff:g} > {thr['precision_max_abs_diff']:g}")
        elif b["precision"]["bitwise_equal"] and not c["precision"]["bitwise_equal"]:
            worse.append(f"規模 {scale:g}：基準逐位元相等、本次不再逐位元相等（如 -0.0／NaN 型樣改變）")
    return worse


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        baseline, current = (json.loads(Path(a).read_text(encoding="utf-8")) for a in args)
        worse = compare(baseline, current)
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        print(f"balance_check：輸入無效：{exc}", file=sys.stderr)
        return 2
    if worse:
        print("balance_check：四項有變差——", file=sys.stderr)
        for w in worse:
            print(f"  · {w}", file=sys.stderr)
        return 1
    print("balance_check：四項皆在門檻內")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
