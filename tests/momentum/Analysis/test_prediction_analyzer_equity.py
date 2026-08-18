"""PA-CUMSUM（2026-08-18 使用者定：單利／複利兩條都算、都標清楚）——`PredictionAnalyzer.calculate_strategy_equity_curve`。

手算 oracle：報酬 [+0.5, −0.5] ⇒ 單利累計 0.0（相加）、複利累計 −0.25（1.5×0.5−1）；兩者皆為對應部位假設下之正確值。
"""

import math

import numpy as np
import pytest

from momentum.Analysis.prediction_analyzer import EquityCurveData, PredictionAnalyzer


def _run(returns, proba=None, threshold=0.75, ts=None):
    returns = np.asarray(returns, dtype=float)
    proba = np.ones_like(returns) if proba is None else np.asarray(proba, dtype=float)
    ts = list(range(len(returns))) if ts is None else ts
    return PredictionAnalyzer().calculate_strategy_equity_curve(
        timestamps=ts, y_pred_proba=proba, actual_returns=returns, threshold=threshold
    )


def test_hand_case_plus50_minus50_simple_zero_compound_minus25():
    """+50%／−50%：單利 0%、複利 −25%（帳戶真實淨值）；兩條同時輸出且標籤明確。"""
    got = _run([0.5, -0.5])
    assert isinstance(got, EquityCurveData)
    assert got.strategy_returns_simple == pytest.approx([0.5, 0.0], abs=1e-12)
    assert got.strategy_returns_compound == pytest.approx([0.5, -0.25], abs=1e-12)
    assert got.benchmark_returns_simple == got.strategy_returns_simple  # 全程持倉 ⇒ 策略＝基準
    assert got.final_return_pct == pytest.approx(
        {"strategy_simple": 0.0, "benchmark_simple": 0.0, "strategy_compound": -25.0, "benchmark_compound": -25.0}, abs=1e-9
    )


def test_compound_equals_cumprod_and_simple_equals_cumsum_generic():
    rng = np.random.default_rng(3)
    r = rng.standard_normal(200) * 0.02
    got = _run(r)
    assert np.allclose(got.strategy_returns_simple, np.cumsum(r), atol=1e-12)
    assert np.allclose(got.strategy_returns_compound, np.cumprod(1 + r) - 1, atol=1e-12)
    # 對數關係：ln(1+複利終值) == Σ ln(1+r)
    assert math.log(1 + got.strategy_returns_compound[-1]) == pytest.approx(float(np.sum(np.log1p(r))), abs=1e-9)


def test_threshold_gates_positions_and_benchmark_ignores_it():
    """proba <= threshold 之期空手（策略報酬 0）；基準永遠全持倉。"""
    got = _run([0.1, 0.1, 0.1], proba=[0.9, 0.5, 0.9], threshold=0.75)
    assert got.strategy_returns_simple == pytest.approx([0.1, 0.1, 0.2], abs=1e-12)
    assert got.strategy_returns_compound == pytest.approx([0.1, 0.1, 0.21], abs=1e-12)
    assert got.benchmark_returns_simple == pytest.approx([0.1, 0.2, 0.3], abs=1e-12)
    assert got.benchmark_returns_compound == pytest.approx([0.1, 0.21, 0.331], abs=1e-12)
    assert got.threshold == 0.75 and got.timestamps == [0, 1, 2]


def test_length_mismatch_and_non_finite_raise():
    with pytest.raises(ValueError):
        _run([0.1, 0.2], proba=[0.9])
    with pytest.raises(ValueError):
        _run([0.1, 0.2], ts=[0])
    with pytest.raises(ValueError, match="NaN"):
        _run([0.1, float("nan")])


def test_to_dict_matches_api_model_and_has_no_unlabeled_keys():
    """to_dict 可直接餵 API pydantic 模型；不再有無標籤之 strategy_returns／benchmark_returns／final_return_pct.strategy。"""
    from api.models.pattern_analysis_models import EquityCurveData as ApiEquityCurveData

    d = _run([0.01, -0.02, 0.03]).to_dict()
    model = ApiEquityCurveData(**d)
    assert set(d) == {
        "timestamps", "strategy_returns_simple", "benchmark_returns_simple",
        "strategy_returns_compound", "benchmark_returns_compound", "threshold", "final_return_pct", "n_symbols", "aggregation",
    }
    assert set(d["final_return_pct"]) == {"strategy_simple", "benchmark_simple", "strategy_compound", "benchmark_compound"}
    assert model.final_return_pct.strategy_compound == pytest.approx(((1.01 * 0.98 * 1.03) - 1) * 100, abs=1e-9)


def test_proba_nan_or_inf_raises_not_silent_flat():
    """R23（CODEX-P1-02／COMPOSER-P2-01／GROK-P3-01）：缺失預測禁靜默當空手 ⇒ ValueError（與 actual_returns 對稱）。"""
    with pytest.raises(ValueError, match="y_pred_proba"):
        _run([0.1, 0.2], proba=[0.9, float("nan")])
    with pytest.raises(ValueError, match="y_pred_proba"):
        _run([0.1, 0.2], proba=[0.9, float("inf")])


def test_multi_symbol_uses_equal_weight_by_timestamp_not_single_account_compounding():
    """R23（CODEX-P1-01）：兩 symbol 同一 timestamp [+10%, −10%] ⇒ 等權組合報酬 0%（單利／複利皆 0），
    **不是**把兩列當同一帳戶連乘得 −1%；timestamps 去重；n_symbols=2、aggregation 標記。"""
    got = PredictionAnalyzer().calculate_strategy_equity_curve(
        timestamps=[100, 100, 200, 200],
        y_pred_proba=np.array([0.9, 0.9, 0.9, 0.9]),
        actual_returns=np.array([0.10, -0.10, 0.20, 0.00]),
        threshold=0.75,
        symbols=["BTC", "ETH", "BTC", "ETH"],
    )
    assert got.n_symbols == 2 and got.aggregation == "equal_weight_by_timestamp"
    assert got.timestamps == [100, 200]
    assert got.strategy_returns_simple == pytest.approx([0.0, 0.10], abs=1e-12)
    assert got.strategy_returns_compound == pytest.approx([0.0, 0.10], abs=1e-12)  # (1+0)(1+0.1)-1
    assert got.benchmark_returns_compound == pytest.approx([0.0, 0.10], abs=1e-12)
    # 對照：若當同一帳戶連乘會是 (1.1*0.9)-1 = -0.01（錯誤）
    assert abs(got.strategy_returns_compound[0] - (-0.01)) > 1e-6


def test_multi_symbol_positions_are_per_row_before_aggregation():
    """多標的：持倉判定逐列（各 symbol 各自 proba），再等權平均。BTC 持倉 +10%、ETH 空手 ⇒ 組合 +5%。"""
    got = PredictionAnalyzer().calculate_strategy_equity_curve(
        timestamps=[1, 1], y_pred_proba=np.array([0.9, 0.1]), actual_returns=np.array([0.10, -0.50]),
        threshold=0.75, symbols=["BTC", "ETH"],
    )
    assert got.strategy_returns_simple == pytest.approx([0.05], abs=1e-12)
    assert got.benchmark_returns_simple == pytest.approx([-0.20], abs=1e-12)  # (0.10−0.50)/2
    assert got.n_symbols == 2


def test_single_symbol_column_keeps_row_series():
    got = _run([0.1, 0.2], ts=[5, 6])
    assert got.aggregation == "single_series" and got.n_symbols == 1 and got.timestamps == [5, 6]
    got2 = PredictionAnalyzer().calculate_strategy_equity_curve(
        timestamps=[5, 6], y_pred_proba=np.array([0.9, 0.9]), actual_returns=np.array([0.1, 0.2]), symbols=["BTC", "BTC"]
    )
    assert got2.aggregation == "single_series" and got2.strategy_returns_simple == got.strategy_returns_simple


def test_api_model_final_return_pct_is_closed_four_keys():
    """R23（GROK-P2-01）：API model 之 final_return_pct 為四必填鍵之子模型；缺鍵／舊鍵 ⇒ 驗證錯。"""
    from pydantic import ValidationError

    from api.models.pattern_analysis_models import EquityCurveData as ApiEquityCurveData

    d = _run([0.01, -0.02]).to_dict()
    ApiEquityCurveData(**d)  # 產出端可入模
    bad = dict(d)
    bad["final_return_pct"] = {"strategy": 1.0, "benchmark": 2.0}
    with pytest.raises(ValidationError):
        ApiEquityCurveData(**bad)
    bad2 = dict(d)
    bad2["aggregation"] = "portfolio_magic"
    with pytest.raises(ValidationError):
        ApiEquityCurveData(**bad2)
    schema = ApiEquityCurveData.model_json_schema()
    assert all(v.get("description") for k, v in schema["properties"].items()), "每欄位須有 Field(description)"
