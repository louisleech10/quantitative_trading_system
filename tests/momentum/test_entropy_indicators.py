from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.feature_naming import build_identity, format_feature_name, parse_feature_name


def _name(indicator: str, window: int, source: str = "close") -> str:
    """FF-NAME 文法之 entropy 欄名（未標記形；`close_return` 之輸入為 close ⇒ source `close`）。"""
    return format_feature_name(build_identity(source, "entropy", indicator, (window,)))


def _by_indicator(out: pd.DataFrame, indicator: str) -> pd.DataFrame:
    """取 indicator 相符之欄（取代改前之欄名前綴 `ent_<indicator>_` 篩選）。"""
    return out[[c for c in out.columns if parse_feature_name(c, tagged=False).indicator == indicator]]


def _make_data(n: int = 300) -> pd.DataFrame:
    np.random.seed(123)
    close = pd.Series(100 + np.cumsum(np.random.normal(0, 1, n)))
    volume = pd.Series(np.random.randint(100, 2000, n)).astype(float)
    taker_ratio = pd.Series(np.random.uniform(0.35, 0.75, n)).astype(float)
    return pd.DataFrame({"close": close, "volume": volume, "taker_ratio": taker_ratio})


def _engine(**override) -> EntropyIndicatorEngine:
    cfg = {
        "windows": [55, 100],
        "n_bins": 10,
        "apen_m": 2,
        "apen_r_ratio": 0.2,
        "shannon_windows": [21, 55, 100],
        "hurst_windows": [55, 100, 200],
        "fractal_kmax": 10,
        "perm_m": 3,
        "perm_windows": [21, 55, 100],
        "apply_to": ["close_return"],
    }
    cfg.update(override)
    return EntropyIndicatorEngine(cfg, ["close"])


def test_entropy_compute_all_feature_count_and_prefix() -> None:
    out = _engine().compute_all(_make_data())
    assert out.shape[1] == 15
    assert all(parse_feature_name(col, tagged=False).category == "entropy" for col in out.columns)


def test_entropy_metadata_complete() -> None:
    metadata = _engine().get_feature_metadata()
    assert len(metadata) == 15
    assert _name("perm", 100) in metadata


def test_entropy_insufficient_data() -> None:
    out = _engine().compute_all(_make_data(30))
    assert out[_name("hurst", 200)].isna().all()


def test_entropy_constant_returns() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    shannon = _by_indicator(out, "shannon").dropna()
    assert not shannon.empty
    assert (shannon == 0.0).all().all()


def test_entropy_zero_variance() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    assert _by_indicator(out, "apen").notna().any().any()


def test_entropy_many_nans() -> None:
    data = _make_data()
    data.loc[:200, "close"] = np.nan
    out = _engine().compute_all(data)
    assert out.shape[1] == 15


def test_entropy_extreme_returns() -> None:
    data = _make_data()
    data.loc[20:40, "close"] *= 1.5
    data.loc[80:100, "close"] *= 0.5
    out = _engine().compute_all(data)
    assert out.shape[1] == 15


def test_hurst_low_r_squared() -> None:
    data = _make_data()
    data["close"] = np.random.uniform(99.9, 100.1, len(data))
    out = _engine().compute_all(data)
    assert out[_name("hurst", 55)].isna().any()


def test_entropy_missing_column() -> None:
    out = _engine(apply_to=["not_exist"]).compute_all(_make_data())
    assert out.empty


def test_perm_entropy_m_exceeds_window() -> None:
    out = _engine(perm_m=10, perm_windows=[5]).compute_all(_make_data())
    assert out[_name("perm", 5)].isna().all()


def test_perm_entropy_constant_values() -> None:
    data = _make_data()
    data["close"] = 100.0
    out = _engine().compute_all(data)
    perm = _by_indicator(out, "perm").dropna()
    assert not perm.empty
    assert (perm == 0.0).all().all()


def test_perm_entropy_invalid_m() -> None:
    with pytest.raises(ValueError):
        _engine(perm_m=1)


def test_hurst_low_r_squared_matches_independent_rs_oracle() -> None:
    """ent_hurst_55 逐列對獨立純 Python R/S 實作（不呼叫生產碼）：暖機後之 NaN 位置（R²<0.1 置 NaN 分支）
    與數值皆須一致，且暖機後同時存在 NaN 與有限值（分支真被鑑別，非只靠暖機 NaN）。"""
    import math as _m

    def _oracle(vals):
        v = [float(x) for x in vals if _m.isfinite(x)]
        n = len(v)
        if n < 20:
            return float("nan")
        hi = max(n // 2, 10)
        sizes = sorted({int(_m.floor(10 ** (1.0 + (_m.log10(hi) - 1.0) * j / 5))) for j in range(6)})
        xs, ys = [], []
        for size in sizes:
            if size < 10 or size >= n or n // size < 2:
                continue
            rs_list = []
            for c in range(n // size):
                chunk = v[c * size:(c + 1) * size]
                mu = sum(chunk) / size
                acc, cmax, cmin = 0.0, -float("inf"), float("inf")
                for x in chunk:
                    acc += x - mu
                    cmax, cmin = max(cmax, acc), min(cmin, acc)
                sd = _m.sqrt(sum((x - mu) ** 2 for x in chunk) / size)
                if sd != 0.0:
                    rs_list.append((cmax - cmin) / sd)
            if rs_list and sum(rs_list) > 0:
                xs.append(_m.log(size))
                ys.append(_m.log(sum(rs_list) / len(rs_list)))
        if len(xs) < 2:
            return float("nan")
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
        icp = my - slope * mx
        ss_res = sum((b - (slope * a + icp)) ** 2 for a, b in zip(xs, ys))
        ss_tot = sum((b - my) ** 2 for b in ys)
        r2 = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0
        return float("nan") if r2 < 0.1 else slope

    data = _make_data()
    data["close"] = np.random.uniform(99.9, 100.1, len(data))
    prod = _engine().compute_all(data)[_name("hurst", 55)].to_numpy()
    ret = data["close"].astype(float).pct_change().to_numpy()
    w = 55
    orc = np.full(len(ret), np.nan)
    for i in range(w, len(ret)):
        orc[i] = _oracle(ret[i - w + 1:i + 1])
    post = prod[w:]
    assert np.isnan(post).any() and np.isfinite(post).any() and np.array_equal(np.isnan(prod), np.isnan(orc)) and np.allclose(prod[np.isfinite(orc)], orc[np.isfinite(orc)], rtol=1e-9, atol=1e-12), (int(np.isnan(post).sum()), int(np.isnan(orc[w:]).sum()))
