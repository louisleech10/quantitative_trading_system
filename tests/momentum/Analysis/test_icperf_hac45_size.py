"""ICPERF Task 0.4 ㊺：虛無拒絕率與檢定力研究（SPEC v5.78 ㊺ 列驗證 A⑤、B⑥、B⑦；BUDGET-12）。

重型（背景、共用監看、估時收據）；b2d 施工前標 xfail(strict=True)。
通過判準（A⑤、B⑥）：每格未觸發 `data_warning` 者 N_u 次中拒絕次數 ≤ Binomial(N_u, 0.05) 於 1−0.05／格數之單尾上界。
"""

from __future__ import annotations

import pytest
from scipy import stats

_PENDING = pytest.mark.xfail(strict=True, reason="ICPERF ㊺ b2d 施工前（SPEC v5.78 ㊺ 列 A⑤、B⑥、B⑦）")


def bonferroni_upper_bound(n_unwarned: int, n_cells: int, alpha: float = 0.05) -> int:
    """單尾上界：Binomial(N_u, α) 於水準 1−0.05／格數之分位（格點數由測試計算，不寫死）。"""
    return int(stats.binom.ppf(1.0 - 0.05 / n_cells, n_unwarned, alpha))


def test_bonferroni_upper_bound_definition() -> None:
    # 純定義測試（非研究本體）：上界隨 N_u 遞增、隨格數遞增
    assert bonferroni_upper_bound(2000, 13) >= bonferroni_upper_bound(1000, 13)
    assert bonferroni_upper_bound(1000, 26) >= bonferroni_upper_bound(1000, 13)


@_PENDING
@pytest.mark.slow
def test_a5_xsec_null_rejection_conditional_on_no_warning() -> None:
    raise NotImplementedError("b2d：A⑤ 12＋1 格，每格 2,000 次")


@_PENDING
@pytest.mark.slow
def test_b6_trend_null_rejection_conditional_on_no_warning() -> None:
    raise NotImplementedError("b2d：B⑥ 9＋2＋1＋1 格，每格 1,000 次")


@_PENDING
@pytest.mark.slow
def test_b7_size_adjusted_power_report() -> None:
    raise NotImplementedError("b2d：B⑦ 研究輸出（不設門檻）")
