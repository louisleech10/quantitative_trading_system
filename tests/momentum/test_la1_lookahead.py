"""LA-1 M-lookahead 測試骨架（B0 Task 0.3；B1–B4 填實）。

SPEC: docs/IC_LA1_SPEC.md
TODO: docs/IC_LA1_TODO.md Task 0.3

collect == 9:
  - test_regime_pit[rule]
  - test_regime_pit[kmeans]
  - test_regime_pit[mid_segment]
  - test_regime_pit_empty_vol
  - test_regime_fallback_truth_table
  - test_long_short_pit
  - test_long_short_fixed_q
  - test_return_nan_mask_invariance
  - test_fallback_loud_and_status

B0 全 skip；各批去 skip 填實測邏輯。collect 不觸 data_cache 副作用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

LA1_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden" / "la1"
ATTR_ALLOWLIST = LA1_GOLDEN_DIR / "attribution_allowlist.json"
BASELINE_BTC = LA1_GOLDEN_DIR / "BTCUSDT_1h_baseline.json"
BASELINE_ETH = LA1_GOLDEN_DIR / "ETHUSDT_12h_baseline.json"
GEN_BASELINE = LA1_GOLDEN_DIR / "gen_baseline.py"

SKIP_B1 = pytest.mark.skip(reason="LA1-B1 pending")
SKIP_B2 = pytest.mark.skip(reason="LA1-B2 pending")
SKIP_B3 = pytest.mark.skip(reason="LA1-B3 pending")


@pytest.fixture(scope="module")
def la1_baseline_paths() -> Dict[str, Path]:
    """Task 0.1 inputs / baseline 路徑（collect 期不讀 data_cache）。"""
    return {
        "golden_dir": LA1_GOLDEN_DIR,
        "allowlist": ATTR_ALLOWLIST,
        "baseline_btc": BASELINE_BTC,
        "baseline_eth": BASELINE_ETH,
        "gen_baseline": GEN_BASELINE,
    }


@pytest.fixture(scope="module")
def la1_inputs_dir(la1_baseline_paths: Dict[str, Path]) -> Path:
    return la1_baseline_paths["golden_dir"] / "inputs"


# ---------------------------------------------------------------------------
# B1 — regime PIT
# ---------------------------------------------------------------------------
@SKIP_B1
@pytest.mark.parametrize("case", ["rule", "kmeans", "mid_segment"])
def test_regime_pit(case: str, la1_baseline_paths: Dict[str, Path]) -> None:
    """P1-1 / P1-1c：rule / kmeans / mid_segment M-trunc early flip。"""
    raise NotImplementedError(f"LA1-B1 fill-in: test_regime_pit[{case}]")


@SKIP_B1
def test_regime_pit_empty_vol(la1_baseline_paths: Dict[str, Path]) -> None:
    """空 vol → by_regime == {}（Opt-A legacy guard）。"""
    raise NotImplementedError("LA1-B1 fill-in: test_regime_pit_empty_vol")


@SKIP_B1
def test_regime_fallback_truth_table(la1_baseline_paths: Dict[str, Path]) -> None:
    """P1-1b `_fallback_rule_based` 真值表三列。"""
    raise NotImplementedError("LA1-B1 fill-in: test_regime_fallback_truth_table")


# ---------------------------------------------------------------------------
# B2 — long_short PIT
# ---------------------------------------------------------------------------
@SKIP_B2
def test_long_short_pit(la1_baseline_paths: Dict[str, Path]) -> None:
    """P1-2：feature 原時序分箱 + M-trunc early bin flip + reduced-bin。"""
    raise NotImplementedError("LA1-B2 fill-in: test_long_short_pit")


@SKIP_B2
def test_long_short_fixed_q(la1_baseline_paths: Dict[str, Path]) -> None:
    """n≥200 → num_quantiles_used==5（固定 q）。"""
    raise NotImplementedError("LA1-B2 fill-in: test_long_short_fixed_q")


@SKIP_B2
def test_return_nan_mask_invariance(la1_baseline_paths: Dict[str, Path]) -> None:
    """竄改未來報酬 NaN 分布 → bins 逐元素不變。"""
    raise NotImplementedError("LA1-B2 fill-in: test_return_nan_mask_invariance")


# ---------------------------------------------------------------------------
# B3 — fallback loud
# ---------------------------------------------------------------------------
@SKIP_B3
def test_fallback_loud_and_status(
    la1_baseline_paths: Dict[str, Path],
    caplog: Any,
) -> None:
    """P1-3：root analysis_status / oos_guarantees / caplog warning / 禁內層 persist。"""
    raise NotImplementedError("LA1-B3 fill-in: test_fallback_loud_and_status")
