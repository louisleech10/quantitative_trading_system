"""TESTSEL I1b｜SPEC Task 2.4 先查：scripts/l3_moment_bound_check.py 之界與判定（依存檔型別量化端點）。

界值以精確 oracle 算出並與已知解析式對照：spike 窗 skew＝√n·…（n=3 ⇒ √3）、kurt 上界＝n；偶數 n kurt 下界＝−2(n−1)/(n−3)。
實作已存在（驗收工具），本檔為其驗收；現存 run（0729db3a）依存檔型別量化後 0 越界（I1b 實測③更正），不需重生。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scripts import l3_moment_bound_check as chk


@pytest.mark.parametrize("n", [4, 8, 144])
def test_accept_01_even_n_kurt_lower_bound_matches_closed_form(n: int) -> None:
    _sk, lo, hi = chk.bounds(n)
    assert lo == pytest.approx(-2 * (n - 1) / (n - 3), rel=1e-12)
    assert hi == pytest.approx(n, rel=1e-12)


def test_accept_02_spike_skew_bound_n3() -> None:
    sk, _lo, _hi = chk.bounds(3)
    assert sk == pytest.approx(math.sqrt(3), rel=1e-12)


def test_accept_03_flags_impossible_value_and_passes_attainable() -> None:
    sk, lo, hi = chk.bounds(21)
    name = "x_12h_trend_MIDPOINT_89_Kurt-W21"
    assert chk.violations(name, np.array([lo, hi, 0.0, np.nan], dtype=np.float32)) == 0
    assert chk.violations(name, np.array([lo * (1 + 2e-4)])) == 1  # I1b 實測之越界幅度級（2e-4）
    assert chk.violations("x_Skew-W3", np.array([chk.bounds(3)[0] * (1 + 2.14e-4)])) == 1


def test_accept_04_float16_quantized_bound_is_legal() -> None:
    """存檔 float16 量化（產品 feature_storage 往返安全時存 float16）：精確界值之 float16 捨入不算越界；
    再超一個 float16 間距才算（審查 r1 CODEX-R1-P1-01：√3→1.732421875 相對超界 2.14e-4、−10/3→−3.333984375 超 1.95e-4）。"""
    sk3 = chk.bounds(3)[0]
    q = np.array([sk3], dtype=np.float16)
    assert float(q[0]) == 1.732421875
    assert chk.violations("x_Skew-W3", q) == 0
    beyond = np.nextafter(q, np.float16(np.inf))
    assert chk.violations("x_Skew-W3", beyond) == 1
    lo5 = chk.bounds(5)[1]
    assert lo5 == pytest.approx(-10 / 3, rel=1e-12)
    assert chk.violations("x_Kurt-W5", np.array([lo5], dtype=np.float16)) == 0


def test_mutation_unquantized_bound_flags_legal_float16(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：端點不依存檔型別量化（一律 float64）⇒ 合法之 float16 存檔界值被誤判越界（即 I1b 原誤判 61,242 值）。"""
    monkeypatch.setattr(chk, "_quantize", lambda x, dtype: float(x))
    assert chk.violations("x_Skew-W3", np.array([chk.bounds(3)[0]], dtype=np.float16)) == 1


def test_mutation_loose_tolerance_misses_measured_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：容差放寬至 1e-3 ⇒ I1b 實測之 2e-4 越界漏抓（證容差須小於實測越界幅度）。"""
    _sk, lo, _hi = chk.bounds(21)
    monkeypatch.setattr(chk, "REL_TOL", 1e-3)
    assert chk.violations("x_Kurt-W21", np.array([lo * (1 + 2e-4)])) == 0
