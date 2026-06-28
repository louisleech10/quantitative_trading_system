"""Task 1.4 — BUG-2 手刻指標 vs 獨立 canonical reference + v0→v1 差異表。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import talib

from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine
from tests.references import volume_indicators_ref as ref

pytestmark = pytest.mark.requires_kline

DIFF_TABLE_PATH = Path("tests/_golden/ff_deepaudit/handcoded_variant_diff.json")
V0_V1_DIFF_PATH = Path("tests/_golden/ff_deepaudit/handcoded_v0_v1_diff.json")

_RTOL = 1e-5
_ATOL = 1e-3

# 8 根合成 bar（H,L,C,V）— Klinger VF 手推 golden（Stock.Indicators KVO 公式）
# vf = volume * abs(2*((dm/cm)-1)) * trend * 100；trend 比較 (H+L+C)；cm 同向累加/反轉重置
_KLINGER_WORKED_BARS = pd.DataFrame(
    {
        "high": [12.0, 14.0, 13.0, 15.0, 16.0, 14.0, 17.0, 18.0],
        "low": [10.0, 11.0, 10.0, 12.0, 13.0, 11.0, 14.0, 15.0],
        "close": [11.0, 13.0, 12.0, 14.0, 15.0, 13.0, 16.0, 17.0],
        "volume": [500.0, 600.0, 700.0, 800.0, 900.0, 750.0, 850.0, 950.0],
    }
)
# bar0: hlc=33 trend=1 dm=2 cm=2 → vf=500*|2*(1-1)|*1*100=0
# bar1: hlc=38 trend=1 dm=3 cm=5 → vf=600*|2*(3/5-1)|*1*100=48000
# bar2: hlc=35 trend=-1 dm=3 cm=6 → vf=700*|2*(0.5-1)|*(-1)*100=-70000
# bar3: hlc=41 trend=1 dm=3 cm=6 → vf=80000
# bar4: hlc=44 trend=1 dm=3 cm=9 → vf=900*|2*(1/3-1)|*100=120000
# bar5: hlc=38 trend=-1 dm=3 cm=6 → vf=-75000
# bar6: hlc=47 trend=1 dm=3 cm=6 → vf=85000
# bar7: hlc=50 trend=1 dm=3 cm=9 → vf=950*(4/3)*100=126666.666...
_KLINGER_EXPECTED_VF = np.array(
    [0.0, 48000.0, -70000.0, 80000.0, 120000.0, -75000.0, 85000.0, 126666.66666666667],
    dtype=float,
)


@pytest.fixture
def ohlcv_df(requires_kline_data):
    return requires_kline_data("BTCUSDT", "12h", min_rows=500)


def _engine_output(engine: VolumeIndicatorEngine, data, col_substr: str) -> np.ndarray:
    out = engine.compute_all(data)
    matches = [c for c in out.columns if col_substr in c]
    assert len(matches) == 1, f"expected one column matching {col_substr}, got {matches}"
    return out[matches[0]].to_numpy(dtype=float)


def _capture_klinger_vf(data: pd.DataFrame) -> np.ndarray:
    """執行 impl 並攔截 talib.EMA 輸入以取得 VF（非 KVO）。"""
    captured: dict[str, np.ndarray] = {}
    import momentum.FeatureEngineering.atomic.volume_indicators as vol_mod

    real_ema = vol_mod.talib.EMA

    def _ema_capture(values: np.ndarray, timeperiod: int) -> np.ndarray:
        captured["vf"] = np.asarray(values, dtype=float).copy()
        return real_ema(values, timeperiod=timeperiod)

    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    vol_mod.talib.EMA = _ema_capture
    try:
        engine._compute_klinger(data)
    finally:
        vol_mod.talib.EMA = real_ema

    assert "vf" in captured, "Klinger compute did not pass VF to talib.EMA"
    return captured["vf"]


def _summary(a: np.ndarray, b: np.ndarray) -> dict:
    mask = ~(np.isnan(a) | np.isnan(b))
    if not mask.any():
        return {"n": 0, "max_abs_diff": None, "corr": None}
    diff = a[mask] - b[mask]
    corr = float(np.corrcoef(a[mask], b[mask])[0, 1])
    return {
        "n": int(mask.sum()),
        "max_abs_diff": float(np.max(np.abs(diff))),
        "corr": corr,
    }


def test_force_index_matches_canonical_reference(ohlcv_df) -> None:
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    impl = _engine_output(engine, ohlcv_df, "ForceIndex")
    expected = ref.force_index_canonical_ema13(ohlcv_df).to_numpy(dtype=float)
    mask = ~(np.isnan(impl) | np.isnan(expected))
    np.testing.assert_allclose(impl[mask], expected[mask], rtol=_RTOL, atol=_ATOL)


def test_klinger_vf_worked_example_golden() -> None:
    """獨立 oracle：手推 VF literal vs impl（Stock.Indicators abs 公式）。"""
    impl_vf = _capture_klinger_vf(_KLINGER_WORKED_BARS)
    np.testing.assert_allclose(impl_vf, _KLINGER_EXPECTED_VF, rtol=1e-10, atol=1e-6)


def test_klinger_kvo_ema_from_golden_vf() -> None:
    """EMA34/55 部分用 talib 驗：手算 VF → KVO 應等於 impl 輸出。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    impl_kvo = _engine_output(engine, _KLINGER_WORKED_BARS, "Klinger")
    vf = _KLINGER_EXPECTED_VF.astype(float)
    expected_kvo = talib.EMA(vf, timeperiod=34) - talib.EMA(vf, timeperiod=55)
    mask = ~(np.isnan(impl_kvo) | np.isnan(expected_kvo))
    np.testing.assert_allclose(impl_kvo[mask], expected_kvo[mask], rtol=1e-10, atol=1e-6)


def test_eom_matches_simplified_reference(ohlcv_df) -> None:
    """EOM 維持 simplified（corr≈1 vs canonical，僅 scale 差）。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    impl = _engine_output(engine, ohlcv_df, "EOM")
    expected = ref.eom_simplified(ohlcv_df).to_numpy(dtype=float)
    mask = ~(np.isnan(impl) | np.isnan(expected))
    np.testing.assert_allclose(impl[mask], expected[mask], rtol=_RTOL, atol=_ATOL)


def test_handcoded_no_lookahead_invariant(ohlcv_df) -> None:
    """截斷尾段 → 前段 Klinger/ForceIndex 不變（無 look-ahead）。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    tail_cut = 25
    full = engine.compute_all(ohlcv_df)
    trunc = engine.compute_all(ohlcv_df.iloc[:-tail_cut])
    for substr in ("Klinger", "ForceIndex"):
        col = [c for c in full.columns if substr in c][0]
        full_prefix = full[col].iloc[: len(trunc)].to_numpy(dtype=float)
        trunc_vals = trunc[col].to_numpy(dtype=float)
        mask = ~(np.isnan(full_prefix) | np.isnan(trunc_vals))
        np.testing.assert_allclose(full_prefix[mask], trunc_vals[mask], rtol=1e-10, atol=1e-10)


def test_handcoded_v0_v1_diff_table_recorded(ohlcv_df) -> None:
    """§G：記錄 simplified v0 → canonical v1 數值差異（供三方簽核）。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    fi_v1 = _engine_output(engine, ohlcv_df, "ForceIndex")
    fi_v0 = ref.force_index_simplified(ohlcv_df).to_numpy(dtype=float)
    k_v1 = _engine_output(engine, ohlcv_df, "Klinger")
    k_v0 = ref.klinger_simplified_vf(ohlcv_df).to_numpy(dtype=float)
    eom_impl = _engine_output(engine, ohlcv_df, "EOM")
    eom_canon = ref.eom_canonical_scaled(ohlcv_df).to_numpy(dtype=float)

    table = {
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "migration": "simplified_v0_to_canonical_v1_round3",
        "indicators": {
            "ForceIndex": _summary(fi_v0, fi_v1),
            "Klinger": _summary(k_v0, k_v1),
            "EOM": _summary(eom_impl, eom_canon),
        },
        "note": (
            "ForceIndex/Klinger upgraded to Stock.Indicators canonical (round3: Klinger abs fix); "
            "EOM unchanged (scale-only vs 1e8 ref)"
        ),
    }
    V0_V1_DIFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    V0_V1_DIFF_PATH.write_text(json.dumps(table, indent=2), encoding="utf-8")

    assert table["indicators"]["Klinger"]["corr"] is not None
    assert table["indicators"]["Klinger"]["corr"] < 0.99
    assert table["indicators"]["ForceIndex"]["corr"] is not None
    assert table["indicators"]["ForceIndex"]["corr"] < 0.99


def test_literature_reference_diff_table_recorded(ohlcv_df) -> None:
    """§G：round2 錯 canonical → round3 真 canonical 差異 + ForceIndex 文獻對照。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])
    eom_impl = _engine_output(engine, ohlcv_df, "EOM")
    eom_canon = ref.eom_canonical_scaled(ohlcv_df).to_numpy(dtype=float)
    fi_impl = _engine_output(engine, ohlcv_df, "ForceIndex")
    fi_canon = ref.force_index_canonical_ema13(ohlcv_df).to_numpy(dtype=float)
    k_impl = _engine_output(engine, ohlcv_df, "Klinger")
    k_round2 = ref.klinger_round2_wrong_vf(ohlcv_df).to_numpy(dtype=float)

    table = {
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "variant": "canonical_v1_round3",
        "indicators": {
            "ForceIndex": _summary(fi_impl, fi_canon),
            "Klinger_round2_to_round3": _summary(k_round2, k_impl),
            "EOM": _summary(eom_impl, eom_canon),
        },
        "note": (
            "round2 Klinger lacked abs(wrong parens); round3 fixes to Stock.Indicators; "
            "corr round2 vs round3 ~ -0.82 on BTCUSDT/12h"
        ),
    }
    DIFF_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIFF_TABLE_PATH.write_text(json.dumps(table, indent=2), encoding="utf-8")

    assert table["indicators"]["ForceIndex"]["corr"] is not None
    assert table["indicators"]["ForceIndex"]["corr"] > 0.99
    k_r2_r3 = table["indicators"]["Klinger_round2_to_round3"]
    assert k_r2_r3["corr"] is not None
    assert k_r2_r3["corr"] < -0.5


def test_volume_metadata_no_simplified_variant_on_canonical() -> None:
    meta = VolumeIndicatorEngine({"indicators": []}, ["close"]).get_feature_metadata()
    for key in ("hlcv_volume_ForceIndex", "hlcv_volume_Klinger_34_55"):
        assert "variant" not in meta[key]
    assert meta["hlcv_volume_EOM_14"].get("variant") == "simplified"


def test_mutation_eom_multiply_to_divide_fails(ohlcv_df, monkeypatch) -> None:
    """Mutation BUG-2：EOM mid_move * box_ratio → / 必 FAIL。"""
    engine = VolumeIndicatorEngine({"indicators": []}, ["close"])

    def _broken_eom(data, window: int = 14):
        required = {"high", "low", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        mid = (data["high"] + data["low"]) / 2.0
        mid_move = mid.diff()
        box_ratio = (data["high"] - data["low"]) / data["volume"].replace(0, np.nan)
        eom = (mid_move / box_ratio).rolling(window).mean()
        return pd.DataFrame({f"hlcv_volume_EOM_{window}": eom}, index=data.index)

    monkeypatch.setattr(engine, "_compute_eom", _broken_eom)
    impl = _engine_output(engine, ohlcv_df, "EOM")
    expected = ref.eom_simplified(ohlcv_df).to_numpy(dtype=float)
    mask = ~(np.isnan(impl) | np.isnan(expected))
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(impl[mask], expected[mask], rtol=1e-6, atol=1e-6)


def test_mutation_klinger_missing_abs_fails(monkeypatch) -> None:
    """Mutation BUG-2 round3：拿掉 abs（還原 round2 bug）→ worked-example VF 必 FAIL。"""
    import momentum.FeatureEngineering.atomic.volume_indicators as vol_mod

    original_klinger = VolumeIndicatorEngine._compute_klinger

    def _broken_klinger(self, data, fast: int = 34, slow: int = 55):
        required = {"high", "low", "close", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)
        hlc = (high + low + close).values
        trend = np.where(hlc > np.roll(hlc, 1), 1.0, -1.0)
        trend[0] = 1.0
        dm = (high - low).values
        cm = VolumeIndicatorEngine._klinger_cumulative_measurement(dm, trend)
        cm = np.where(cm == 0, np.nan, cm)
        vf = volume.values * (2.0 * (dm / cm - 1.0)) * trend * 100.0
        vf = np.nan_to_num(vf, nan=0.0, posinf=0.0, neginf=0.0)
        ema_fast = vol_mod.talib.EMA(vf.astype(float), timeperiod=fast)
        ema_slow = vol_mod.talib.EMA(vf.astype(float), timeperiod=slow)
        return pd.DataFrame(
            {f"hlcv_volume_Klinger_{fast}_{slow}": pd.Series(ema_fast - ema_slow, index=data.index)},
            index=data.index,
        )

    monkeypatch.setattr(VolumeIndicatorEngine, "_compute_klinger", _broken_klinger)
    try:
        impl_vf = _capture_klinger_vf(_KLINGER_WORKED_BARS)
        with pytest.raises(AssertionError):
            np.testing.assert_allclose(impl_vf, _KLINGER_EXPECTED_VF, rtol=1e-6, atol=1e-6)
    finally:
        monkeypatch.setattr(VolumeIndicatorEngine, "_compute_klinger", original_klinger)
