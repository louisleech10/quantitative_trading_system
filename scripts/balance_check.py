"""NOCAP Task 0.4（docs/NOCAP_SPEC.md）：記憶體／精確度／計算時間／檔案大小四項平衡之比較——改動後重量之四項與
`tests/_golden/balance/<模組>.json` 基準比，任一項明顯變差即 rc≠0；門檻寫於基準檔可審。

用法：`python3 scripts/balance_check.py <基準檔> <本次量測檔>`（rc 0＝四項皆在門檻內；1＝有變差；2＝輸入無效）。
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

#: 預設門檻（基準檔可覆寫）：耗時或峰值 RSS 增逾 20%、精度差非零、檔案大小增逾 10% ⇒ 變差。
DEFAULT_THRESHOLDS = {"seconds_increase": 0.20, "peak_rss_increase": 0.20, "precision_max_abs_diff": 0.0,
                      "output_bytes_increase": 0.10}


def compare(baseline: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """逐規模點比四項；回變差之描述（空串列＝通過）。兩者 `identity.match` 之 entrypoint／hardware 不同 ⇒ ValueError。"""
    raise NotImplementedError("NOCAP Task 0.4")


def main(argv: Optional[Sequence[str]] = None) -> int:
    raise NotImplementedError("NOCAP Task 0.4")


if __name__ == "__main__":
    raise SystemExit(main())
