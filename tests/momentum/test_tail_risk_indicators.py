from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine


def _make_data(n: int = 300) -> pd.DataFrame:
    np.random.seed(7)
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 1, n)))
    return pd.DataFrame({"close": close})


def _engine(**override) -> TailRiskIndicatorEngine:
    cfg = {
        "windows": [21, 55, 100],
        "cvar_alphas": [0.01, 0.05],
        "rv_windows": [13, 21, 55],
        "mdd_windows": [21, 55, 100],
    }
    cfg.update(override)
    return TailRiskIndicatorEngine(cfg, ["close"])


def test_tail_risk_compute_all_feature_count_and_prefix() -> None:
    out = _engine().compute_all(_make_data())
    assert out.shape[1] == 26
    assert all(col.startswith("tr_") for col in out.columns)


def test_tail_risk_metadata_complete() -> None:
    metadata = _engine().get_feature_metadata()
    assert len(metadata) == 26
    assert "tr_mdd_100" in metadata


def test_tail_risk_insufficient_data() -> None:
    out = _engine().compute_all(_make_data(15))
    assert out["tr_cvar_1pct_100"].isna().all()


def test_tail_risk_zero_returns() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    assert (out.filter(like="tr_cvar_").fillna(0.0) == 0.0).all().all()
    assert (out.filter(like="tr_mdd_").fillna(0.0) == 0.0).all().all()


def test_tail_risk_one_sided() -> None:
    data = _make_data()
    data["close"] = np.arange(len(data), dtype=float) + 100.0
    out = _engine().compute_all(data)
    gpr = out.filter(like="tr_gpr_")
    assert (gpr.dropna() <= 100.0).all().all()


def test_tail_risk_rare_negative() -> None:
    data = _make_data()
    close = np.linspace(100, 120, len(data))
    close[150] = close[149] * 0.95
    data["close"] = close
    out = _engine().compute_all(data)
    assert out.filter(like="tr_cvar_5pct_").notna().any().any()


def test_udvr_zero_downside() -> None:
    data = _make_data()
    data["close"] = np.linspace(100, 130, len(data))
    out = _engine().compute_all(data)
    assert out.filter(like="tr_ud_vol_ratio_").isna().any().any()


def test_tail_risk_extreme() -> None:
    data = _make_data()
    data.loc[50:80, "close"] *= 1.5
    data.loc[120:150, "close"] *= 0.5
    out = _engine().compute_all(data)
    assert out.shape[1] == 26


def test_cvar_invalid_alpha() -> None:
    with pytest.raises(ValueError):
        _engine(cvar_alphas=[0.0, 0.05])


def test_tail_risk_many_nans() -> None:
    data = _make_data()
    data.loc[:220, "close"] = np.nan
    out = _engine().compute_all(data)
    assert out.shape[1] == 26


def test_mdd_monotonic_up() -> None:
    data = _make_data()
    data["close"] = np.linspace(100, 150, len(data))
    out = _engine().compute_all(data)
    assert (out.filter(like="tr_mdd_").fillna(0.0) == 0.0).all().all()


def test_mdd_monotonic_down() -> None:
    data = _make_data()
    data["close"] = np.linspace(150, 100, len(data))
    out = _engine().compute_all(data)
    assert out.filter(like="tr_mdd_").iloc[-1].max() > 0.0


def test_mdd_invalid_price() -> None:
    data = _make_data()
    data.loc[30, "close"] = 0.0
    out = _engine().compute_all(data)
    assert out.filter(like="tr_mdd_").isna().any().any()


def test_tail_risk_one_sided_gpr_is_nan_not_capped() -> None:
    """嚴格遞增 ⇒ 每窗 loss_sum＝0 ⇒ GPR 無定義：須全列 NaN（不得變成 inf 或被 clip 成上限 100）；
    同時 rv_up 暖機後全為正有限值（證明 NaN 來自零虧損而非缺資料）。"""
    data = _make_data()
    data["close"] = np.arange(len(data), dtype=float) + 100.0
    out = _engine().compute_all(data)
    gpr = out.filter(like="tr_gpr_").to_numpy()
    rv_up = out.filter(like="tr_rv_up_").iloc[60:].to_numpy()
    assert np.isnan(gpr).all() and np.isfinite(rv_up).all() and (rv_up > 0).all(), \
        (np.nanmax(gpr) if np.isfinite(gpr).any() else "all-nan", rv_up.min())


def test_udvr_zero_downside_is_nan_after_warmup() -> None:
    """零下行（線性遞增）⇒ rv_down 暖機後恆 0 ⇒ 上下行波動比無定義：暖機**之後**亦須全 NaN；
    rv_up 暖機後為正有限值（排除「只是暖機 NaN」之恆真）。"""
    data = _make_data()
    data["close"] = np.linspace(100, 130, len(data))
    out = _engine().compute_all(data)
    udvr_after = out.filter(like="tr_ud_vol_ratio_").iloc[60:].to_numpy()
    rv_down_after = out.filter(like="tr_rv_down_").iloc[60:].to_numpy()
    rv_up_after = out.filter(like="tr_rv_up_").iloc[60:].to_numpy()
    assert np.isnan(udvr_after).all() and (rv_down_after == 0.0).all() and (rv_up_after > 0).all(), \
        np.nanmax(np.abs(udvr_after)) if np.isfinite(udvr_after).any() else "all-nan"


def test_mdd_invalid_price_masks_that_row_only_and_keeps_prior_rows() -> None:
    """第 250 列 close＝0（各窗暖機皆已過）：該列每個 tr_mdd_* 須為 NaN；
    第 249 列（窗未含壞價，因果上不受影響）須非 NaN 且與未改動資料逐值相同。"""
    base = _engine().compute_all(_make_data()).filter(like="tr_mdd_")
    data = _make_data()
    data.loc[250, "close"] = 0.0
    out = _engine().compute_all(data).filter(like="tr_mdd_")
    assert out.iloc[250].isna().all() and out.iloc[249].notna().all() \
        and np.allclose(out.iloc[249].to_numpy(), base.iloc[249].to_numpy(), rtol=0, atol=1e-15), \
        (out.iloc[249:252].to_dict(), base.iloc[249].to_dict())


def test_tail_risk_extreme_matches_independent_numpy_oracle() -> None:
    """同 test_tail_risk_extreme 之劇烈跳變資料；CVaR／RV／MDD 以逐窗 numpy 迴圈獨立重算，
    有效列遮罩須完全一致、數值逐列相符（現有測試無任何數值期望值）。"""
    data = _make_data()
    data.loc[50:80, "close"] *= 1.5
    data.loc[120:150, "close"] *= 0.5
    out = _engine().compute_all(data)
    c = data["close"].to_numpy(dtype=float)
    n = len(c)
    r = np.full(n, np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0

    def _roll(w, fn):
        res = np.full(n, np.nan)
        for i in range(w - 1, n):
            win = r[i - w + 1:i + 1]
            if np.isfinite(win).all():
                res[i] = fn(win)
        return res

    cvar_cols, cvar_exp = [], []
    for alpha, tag in ((0.01, 1), (0.05, 5)):
        for w in (21, 55, 100):
            cvar_cols.append(f"tr_cvar_{tag}pct_{w}")
            cvar_exp.append(_roll(w, lambda x, a=alpha: x[x <= np.quantile(x, a)].mean()))
    cvar_got = out[cvar_cols].to_numpy()
    assert np.allclose(cvar_got, np.column_stack(cvar_exp), rtol=1e-12, atol=1e-14, equal_nan=True), "CVaR 不符"

    rv_cols, rv_exp = [], []
    for w in (13, 21, 55):
        rv_cols += [f"tr_rv_up_{w}", f"tr_rv_down_{w}"]
        rv_exp += [_roll(w, lambda x: np.sqrt((x[x > 0] ** 2).sum())),
                   _roll(w, lambda x: np.sqrt((x[x < 0] ** 2).sum()))]
    rv_got = out[rv_cols].to_numpy()
    assert np.allclose(rv_got, np.column_stack(rv_exp), rtol=1e-9, atol=1e-7, equal_nan=True), "RV 上下行不符"

    mdd_exp = []
    for w in (21, 55, 100):
        dd = np.full(n, np.nan)
        for j in range(w - 1, n):
            peak = c[j - w + 1:j + 1].max()
            dd[j] = (c[j] - peak) / peak
        mdd = np.full(n, np.nan)
        for i in range(2 * w - 2, n):
            mdd[i] = abs(dd[i - w + 1:i + 1].min())
        mdd_exp.append(mdd)
    mdd_got = out[["tr_mdd_21", "tr_mdd_55", "tr_mdd_100"]].to_numpy()
    mdd_ref = np.column_stack(mdd_exp)
    got_ok = ~np.isnan(mdd_got)  # 穩定遮罩（warmup 表）可比自然暖機多遮數列；只驗「有值處必相符、不得無中生有」
    assert not (got_ok & np.isnan(mdd_ref)).any() and got_ok.sum(axis=0).min() >= 98 \
        and np.allclose(mdd_got[got_ok], mdd_ref[got_ok], rtol=1e-12, atol=1e-14), "MDD 不符"


def test_tail_risk_many_nans_never_emits_values_from_missing_prefix() -> None:
    """close 前 221 列為 NaN（第 221 列起有值、報酬自第 222 列起）：
    ① 第 0..221 列所有輸出須為 NaN（缺值不得被補成數值）② rv_*_13 首個有效列恰為 222+12＝234，
    且其後與只用有效尾段獨立重算之 RV 逐列相符。"""
    data = _make_data()
    data.loc[:220, "close"] = np.nan
    out = _engine().compute_all(data)
    c = data["close"].to_numpy(dtype=float)
    r = np.full(len(c), np.nan)
    r[1:] = c[1:] / c[:-1] - 1.0
    exp_down = np.full(len(c), np.nan)
    for i in range(234, len(c)):
        win = r[i - 12:i + 1]
        exp_down[i] = np.sqrt((win[win < 0] ** 2).sum())
    got_down = out["tr_rv_down_13"].to_numpy()
    assert out.iloc[:222].isna().all().all() and out["tr_rv_up_13"].first_valid_index() == 234 \
        and np.allclose(got_down, exp_down, rtol=1e-9, atol=1e-7, equal_nan=True), \
        (out.iloc[:222].notna().sum().loc[lambda s: s > 0].to_dict(), out["tr_rv_up_13"].first_valid_index())
