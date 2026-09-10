"""EVTLABEL Task 3.5：`mann_whitney_table` 之 oracle 與邊界。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.5　TODO：Task 3.5

## 這批測試在防什麼

分辨力統計算錯**不會拋例外**——它只會給出一個看起來很正常的數字，然後你拿它去篩特徵。
故本檔以**可獨立驗算的 oracle** 釘住：完全可分 ⇒ AUC 必須恰為 1；把標籤翻轉 ⇒
rank-biserial 必須恰好變號；向量化結果 ⇒ 必須與逐欄標量 scipy 逐值相同。

mutation（`--phase 3b`）：`M-P3-1`（AUC 方向翻轉）⇒ `test_planted_*` 紅。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.binary_discrimination import BINARY_STATUS_OK, mann_whitney_table


def _y(n_pos: int, n_neg: int) -> np.ndarray:
    return np.array([1] * n_pos + [0] * n_neg, dtype=int)


def _frame(cols: dict) -> pd.DataFrame:
    return pd.DataFrame(cols)


# ══════════════════════════════════════════════════════════════════════════
# ① oracle：完全可分 ⇒ AUC == 1（可獨立驗算，不依賴實作）
# ══════════════════════════════════════════════════════════════════════════


def test_planted_perfectly_separable_gives_auc_one():
    """🔴 `M-P3-1` 之標的：正例的值全部大於反例 ⇒ AUC 恰為 1、rank-biserial 恰為 1。"""
    y = _y(20, 20)
    x = np.where(y == 1, 10.0, 0.0) + np.arange(40) * 1e-6
    out = mann_whitney_table(_frame({"planted": x}), y, min_class_n=10)
    assert out.loc["planted", "auc"] == pytest.approx(1.0, abs=1e-12)
    assert out.loc["planted", "rank_biserial"] == pytest.approx(1.0, abs=1e-12)
    assert out.loc["planted", "status"] == BINARY_STATUS_OK
    assert out.loc["planted", "p_value"] < 1e-6


def test_mirror_flips_rank_biserial_sign_exactly():
    """把標籤翻轉 ⇒ rank-biserial 必須**恰好**變號（±1e-12）。

    這條同時證明「負值＝反向但一樣能分」——下游門檻因此必須看絕對值。
    """
    y = _y(20, 20)
    x = np.where(y == 1, 10.0, 0.0) + np.arange(40) * 1e-6
    a = mann_whitney_table(_frame({"f": x}), y, min_class_n=10)
    b = mann_whitney_table(_frame({"f": x}), 1 - y, min_class_n=10)
    assert a.loc["f", "rank_biserial"] + b.loc["f", "rank_biserial"] == pytest.approx(0.0, abs=1e-12)
    assert b.loc["f", "rank_biserial"] < 0
    assert a.loc["f", "p_value"] == pytest.approx(b.loc["f", "p_value"], rel=1e-12)


def test_no_signal_sits_near_zero():
    """完全無訊號（正反同分布）⇒ rank-biserial 接近 0、p 不顯著。"""
    rng = np.random.default_rng(20260910)
    y = _y(60, 60)
    x = rng.standard_normal(120)
    out = mann_whitney_table(_frame({"noise": x}), y, min_class_n=10)
    assert abs(out.loc["noise", "rank_biserial"]) < 0.35
    assert out.loc["noise", "p_value"] > 0.05


# ══════════════════════════════════════════════════════════════════════════
# ② 向量化必須與逐欄標量逐值相同
# ══════════════════════════════════════════════════════════════════════════


def test_vectorized_matches_scalar_scipy_per_column():
    """🔴 承重條：一次算 p 欄，必須與「一欄一欄呼叫 scipy」逐值相同。

    向量化最容易出的錯是軸搞錯——那不會拋例外，只會讓每一欄拿到別欄的數字。
    """
    rng = np.random.default_rng(7)
    y = _y(30, 25)
    cols = {f"f{i}": rng.standard_normal(55) for i in range(12)}
    out = mann_whitney_table(_frame(cols), y, min_class_n=5)
    for name, values in cols.items():
        want = stats.mannwhitneyu(values[y == 1], values[y == 0], alternative="two-sided")
        assert out.loc[name, "mw_u"] == pytest.approx(float(want.statistic), rel=1e-12)
        assert out.loc[name, "p_value"] == pytest.approx(float(want.pvalue), rel=1e-9)
        assert out.loc[name, "auc"] == pytest.approx(float(want.statistic) / (30 * 25), rel=1e-12)


def test_nan_is_dropped_per_column_not_per_row():
    """逐欄 pairwise 去列：A 欄的缺值不得影響 B 欄的 `n_used`。"""
    y = _y(10, 10)
    a = np.arange(20, dtype=float)
    a[:5] = np.nan
    b = np.arange(20, dtype=float)
    out = mann_whitney_table(_frame({"a": a, "b": b}), y, min_class_n=1)
    assert out.loc["a", "n_used"] == 15
    assert out.loc["b", "n_used"] == 20, "B 欄不該被 A 欄的缺值波及"


def test_inf_counts_as_missing():
    """`inf` 併入缺值（上游已閘，此處只防禦）。"""
    y = _y(10, 10)
    x = np.arange(20, dtype=float)
    x[0] = np.inf
    x[1] = -np.inf
    out = mann_whitney_table(_frame({"f": x}), y, min_class_n=1)
    assert out.loc["f", "n_used"] == 18


# ══════════════════════════════════════════════════════════════════════════
# ③ 三種不可用：回值＋status，不拋例外
# ══════════════════════════════════════════════════════════════════════════


def test_all_nan_column_is_marked_all_nan():
    y = _y(10, 10)
    out = mann_whitney_table(_frame({"dead": np.full(20, np.nan)}), y, min_class_n=1)
    assert out.loc["dead", "status"] == "unavailable:all_nan"
    assert out.loc["dead", "n_used"] == 0
    assert np.isnan(out.loc["dead", "auc"])


def test_constant_column_is_marked_constant_not_faked_as_half():
    """🔴 常數欄**不冒充 0.5／1.0**：scipy 對全並列之 p 定義依版本而異。

    給一個看似正常的數字，比誠實說「不知道」更糟——那個數字會被拿去篩特徵。
    """
    y = _y(10, 10)
    out = mann_whitney_table(_frame({"flat": np.full(20, 3.0)}), y, min_class_n=1)
    assert out.loc["flat", "status"] == "unavailable:constant"


def test_class_below_min_is_marked_but_still_computed():
    """某類太少 ⇒ 值仍算出來（供診斷），但 status 非 ok（算得出來 ≠ 可信）。"""
    y = _y(18, 2)
    x = np.arange(20, dtype=float)
    out = mann_whitney_table(_frame({"f": x}), y, min_class_n=10)
    assert out.loc["f", "status"] == "unavailable:class_below_min"
    assert np.isfinite(out.loc["f", "auc"]), "值仍要算，只是不標 ok"
    assert out.loc["f", "n_pos"] == 18 and out.loc["f", "n_neg"] == 2


# ══════════════════════════════════════════════════════════════════════════
# ④ 契約：欄集、加權預留、輸入不被改動
# ══════════════════════════════════════════════════════════════════════════


def test_weights_is_not_silently_ignored():
    """🔴 R-1 預留欄位：非 None ⇒ `NotImplementedError`。

    靜默忽略＝「呼叫端以為加權了、其實沒有」，那是最難查的一種錯。
    """
    y = _y(10, 10)
    with pytest.raises(NotImplementedError, match="加權"):
        mann_whitney_table(_frame({"f": np.arange(20, dtype=float)}), y,
                           min_class_n=1, weights=np.ones(20))


def test_column_set_is_the_documented_one():
    y = _y(10, 10)
    out = mann_whitney_table(_frame({"f": np.arange(20, dtype=float)}), y, min_class_n=1)
    assert list(out.columns) == [
        "auc", "rank_biserial", "mw_u", "p_value", "n_pos", "n_neg", "n_used", "status",
    ]
    assert out.index.name == "feature"


def test_input_frame_is_not_mutated():
    """純函式：呼叫後輸入必須逐值不變（含 inf 位置）。"""
    y = _y(10, 10)
    x = np.arange(20, dtype=float)
    x[0] = np.inf
    df = _frame({"f": x.copy()})
    before = df.to_numpy(copy=True)
    mann_whitney_table(df, y, min_class_n=1)
    after = df.to_numpy(copy=True)
    assert np.array_equal(before, after, equal_nan=True)


def test_rejects_non_binary_y():
    with pytest.raises(ValueError, match="0/1"):
        mann_whitney_table(_frame({"f": np.arange(6, dtype=float)}), np.array([0, 1, 2, 0, 1, 0]))


def test_rejects_length_mismatch():
    with pytest.raises(ValueError, match="不符"):
        mann_whitney_table(_frame({"f": np.arange(6, dtype=float)}), np.array([0, 1, 0]))
