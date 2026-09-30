"""FF-STAT Task 2.3（SPEC v32–v44）：逐欄穩定點、公開域預熱恆開、未填起始日之逐欄校準、死欄純函式與欄集合差異。

全部以真實 `data_cache/feature_klines/kline_cache.h5`（及長歷史快取）驗證，禁合成 fixture。
實作前本檔應為紅（`stable_mask` 為 NotImplementedError 空殼、生成路徑尚未接線）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing import stable_mask as sm
from tests.feature_engineering import ffstat_helpers as h

CONTRACT = h.CONTRACT
REPO = Path(__file__).resolve().parents[2]
TABLE_PATH = REPO / CONTRACT["warmup_table"]["path"]


def _table() -> Dict[str, Dict[str, Any]]:
    import yaml

    return dict(yaml.safe_load(TABLE_PATH.read_text(encoding="utf-8"))["indicators"])


def _close(timeframe: str = "1h") -> np.ndarray:
    return h.kline_frame(timeframe=timeframe)["close"].to_numpy(dtype=np.float64)


def _hlc(timeframe: str = "1h") -> np.ndarray:
    frame = h.kline_frame(timeframe=timeframe)
    return frame[["high", "low", "close"]].to_numpy(dtype=np.float64)


def _spec(indicator: str, column: str, params: Dict[str, Any], **kw: Any) -> sm.OutputPointSpec:
    keys = tuple(_table()[indicator]["period_keys"]) if indicator in _table() else ()
    return sm.OutputPointSpec(engine="talib", indicator=indicator, column=column, params=params, period_keys=keys, **kw)


def _factor(indicator: str) -> float:
    return float(_table()[indicator]["recommended_factor"])


def _params_key(params: Dict[str, Any], defaults: Dict[str, Any]) -> str:
    """v47 `k_by_params` 之鍵：條目 `param_defaults` 疊上呼叫參數，依鍵名升序以 `鍵=值` 逗號連接（整數寫整數字面）。"""
    merged = {**defaults, **params}

    def fmt(v: Any) -> str:
        f = float(v)
        return str(int(f)) if f.is_integer() else repr(f)

    return ",".join(f"{k}={fmt(merged[k])}" for k in sorted(merged))


def _expected_k(indicator: str, params: Dict[str, Any]) -> int:
    """SPEC v46／v47（R10）：表之 `k_by_params`（全參數鍵）查得者取其值；查無才 ceil(max(period_keys 值)×係數)。"""
    entry = _table()[indicator]
    keys = entry["period_keys"]
    measured = (entry.get("k_by_params") or {}).get(_params_key(params, entry.get("param_defaults") or {}))
    if measured is not None:
        return int(measured)
    return math.ceil(max(float(params[k]) for k in keys) * float(entry["recommended_factor"]))


# ─────────────────────────────── ① L1 遮罩（逐呼叫 K）

@pytest.mark.parametrize("timeframe", ["1h", "12h"])
def test_l1_mask_first_valid_is_origin_plus_k(timeframe: str) -> None:
    """Task 2.3 ①：EMA_233（recursive）、SMA_200（window_only）、ADX_14（多輸入）首個有效值之列＝origin＋K，之前全 NaN。"""
    import talib

    close = _close(timeframe)
    hlc = _hlc(timeframe)
    cases = [
        ("EMA", "EMA_233", {"timeperiod": 233}, talib.EMA(close, timeperiod=233), close[:, None]),
        ("SMA", "SMA_200", {"timeperiod": 200}, talib.SMA(close, timeperiod=200), close[:, None]),
        ("ADX", "ADX_14", {"timeperiod": 14}, talib.ADX(hlc[:, 0], hlc[:, 1], hlc[:, 2], timeperiod=14), hlc),
    ]
    for indicator, column, params, raw, inputs in cases:
        k = sm.instance_k(_spec(indicator, column, params), _table())
        assert k == _expected_k(indicator, params), column
        origin = sm.l1_origin(inputs)
        masked = sm.apply_l1_mask(raw, origin, k)
        assert sm.first_finite_index(masked) == origin + k, column
        assert np.isnan(masked[: origin + k]).all(), column
        np.testing.assert_array_equal(masked[origin + k:], raw[origin + k:])


def test_l1_mask_per_call_k_ema5_vs_ema233() -> None:
    """Task 2.3 ①（v37）：同一指標之 EMA_5 與 EMA_233 之 K 分別依各自參數，不取整個指標之最大週期。"""
    k5 = sm.instance_k(_spec("EMA", "EMA_5", {"timeperiod": 5}), _table())
    k233 = sm.instance_k(_spec("EMA", "EMA_233", {"timeperiod": 233}), _table())
    assert k5 == _expected_k("EMA", {"timeperiod": 5})
    assert k233 == _expected_k("EMA", {"timeperiod": 233})
    assert k5 < k233


def test_l1_mask_stoch_combo_k_uses_max_period_key() -> None:
    """Task 2.3 ①：STOCH 一組 combo 之 K 依其三個週期鍵（v46：k_by_params 查得者優先，否則 ceil(max×係數)）；
    表外之組合（fastk 377）走比例公式。"""
    params = {"fastk_period": 55, "slowk_period": 8, "slowk_matype": 0, "slowd_period": 5, "slowd_matype": 0}
    k = sm.instance_k(_spec("STOCH", "STOCH_slowk", params), _table())
    assert k == _expected_k("STOCH", params)
    unmeasured = {"fastk_period": 377, "slowk_period": 8, "slowk_matype": 0, "slowd_period": 5, "slowd_matype": 0}
    assert sm.instance_k(_spec("STOCH", "STOCH_slowk", unmeasured), _table()) == math.ceil(377 * _factor("STOCH"))


def test_l1_mask_k_by_params_preferred_over_factor() -> None:
    """v46（R10 實測根數優先）：KAMA_233 之 K＝表 k_by_params 之實測值，且小於 ceil(233×係數)（比例公式高估）。"""
    params = {"timeperiod": 233}
    measured = _table()["KAMA"]["k_by_params"][_params_key(params, _table()["KAMA"].get("param_defaults") or {})]
    assert measured < math.ceil(233 * _factor("KAMA"))
    assert sm.instance_k(_spec("KAMA", "close_trend_KAMA_233", params), _table()) == measured


def test_l1_mask_unmeasured_nonperiod_variant_fails_closed() -> None:
    """v47（r31 codex P1-02）：非週期參數改變收斂（MA matype=4 實測 258 > 233）⇒ 未量測之變體於輸出前擋下；
    預設變體（matype 0）照常。"""
    assert sm.instance_k(_spec("MA", "close_trend_MA_233", {"timeperiod": 233}), _table()) == _expected_k(
        "MA", {"timeperiod": 233})
    with pytest.raises(sm.UnmeasuredVariantError) as exc:
        sm.instance_k(_spec("MA", "close_trend_MA_4-233", {"timeperiod": 233, "matype": 4}), _table())
    assert "matype=4" in str(exc.value) and "close_trend_MA_4-233" in str(exc.value)


def test_derived_output_k_follows_upstream() -> None:
    """§C v39：同引擎衍生輸出之 K＝上游 K 最大者＋window−1（窗型）或上游 K 最大者（逐點聚合）。"""
    windowed = sm.OutputPointSpec(engine="microstructure", indicator="VPIN_ZSCORE", column="ms_vpin_zscore_21",
                                  params={"window": 21}, period_keys=(), upstream=("ms_vpin_30", "ms_sigma_50"), window=21)
    assert sm.instance_k(windowed, _table(), upstream_k={"ms_vpin_30": 40, "ms_sigma_50": 60}) == 60 + 20
    pointwise = sm.OutputPointSpec(engine="pattern", indicator="CDL_PATTERN", column="ohlc_pattern_Consensus",
                                   params={}, period_keys=(), upstream=("ohlc_pattern_CDLDOJI", "ohlc_pattern_CDLENGULFING"))
    assert sm.instance_k(pointwise, _table(), upstream_k={"ohlc_pattern_CDLDOJI": 5, "ohlc_pattern_CDLENGULFING": 7}) == 7


def test_output_point_missing_period_key_fails_closed() -> None:
    """§C 輸出點契約：參數字典缺登記之 period key ⇒ StableMaskError，訊息列引擎、輸出欄與缺少之鍵。"""
    with pytest.raises(sm.StableMaskError) as exc:
        sm.instance_k(_spec("STOCH", "STOCH_slowk", {"fastk_period": 55}), _table())
    message = str(exc.value)
    assert "talib" in message and "STOCH_slowk" in message and "slowk_period" in message


def test_output_point_unregistered_indicator_fails_closed() -> None:
    """§C／R5：倍數表查不到之指標 ⇒ StableMaskError（不得套後備係數）。"""
    spec = sm.OutputPointSpec(engine="talib", indicator="NOT_IN_TABLE_XYZ", column="x", params={"timeperiod": 10},
                              period_keys=("timeperiod",))
    with pytest.raises(sm.StableMaskError):
        sm.instance_k(spec, _table())


def test_custom_indicator_outputs_declaration_required() -> None:
    """§C v39②：`CustomIndicatorDef` 之 `outputs` 必填；缺即設定驗證失敗。"""
    from pydantic import ValidationError

    from momentum.FeatureEngineering.feature_config import CustomIndicatorDef

    with pytest.raises(ValidationError):
        CustomIndicatorDef(name="two_windows", module="tests.feature_engineering.test_ffstat_stable_start",
                           function="_custom_two_windows", params={})


def _custom_two_windows(data: pd.DataFrame) -> pd.DataFrame:
    """r18 codex 反例：一次呼叫回傳兩個不同窗長之欄。"""
    return pd.DataFrame({"short": data["close"].rolling(5).mean(), "long": data["close"].rolling(233).mean()})


def test_custom_indicator_undeclared_output_fails_closed() -> None:
    """§C v39②：回傳欄集合≠宣告集合 ⇒ concat 前 StableMaskError，訊息列引擎、輸出欄與缺少之鍵。"""
    from momentum.FeatureEngineering.atomic.custom_indicators import CustomIndicatorEngine

    data = h.kline_frame(timeframe="12h").iloc[:600]
    definition = {"name": "two_windows", "module": __name__, "function": "_custom_two_windows", "params": {},
                  "outputs": {"short": {"params": {"window": 5}, "period_keys": ["window"]}}}
    with pytest.raises(sm.StableMaskError) as exc:
        CustomIndicatorEngine().compute_all(data, [definition])
    assert "long" in str(exc.value)


# ─────────────────────────────── ② 不傳遞 NaN 之步驟

def test_incomplete_window_mask_winsor_full_window() -> None:
    """Task 2.3 ②：縮尾（第①類，window 252）⇒ 輸出首個有效值＝輸入首個有效值＋251；只遮罩、其後值不變。"""
    import talib

    rsi = talib.RSI(_close("1h"), timeperiod=14)
    first = sm.first_finite_index(rsi)
    fake_winsor_output = rsi.copy()  # 縮尾於界線未定時保留原值 ⇒ 以原值代表其開頭段
    out = sm.mask_incomplete_window(fake_winsor_output, rsi, CONTRACT["non_propagating_steps"]["incomplete_window"]["winsorization"])
    assert sm.first_finite_index(out) == first + 251
    np.testing.assert_array_equal(out[first + 251:], fake_winsor_output[first + 251:])


def test_pointwise_prefix_mask_binary_signal() -> None:
    """Task 2.3 ②（第④類）：binary_signal 之輸出首個有效值＝輸入首個有效值；其後之間歇 NaN 處理不變。"""
    import talib

    rsi = sm.apply_l1_mask(talib.RSI(_close("1h"), timeperiod=14), 0, 50)
    signal = (rsi > 70).astype(float)  # 現行 compute_binary_signal：NaN 比較為 False ⇒ 0
    out = sm.mask_pointwise_prefix(signal, [rsi])
    assert sm.first_finite_index(out) == sm.first_finite_index(rsi)
    np.testing.assert_array_equal(out[50:], signal[50:])


def _denominator_checks(mask_fn) -> None:
    """v53（審查 r36 兩家一致）：分母近零遮罩為因果、窗滿後與起算點無關，pandas 與 Polars 兩路徑同一結果。
    真實 BTC 1h STOCHRSI fastk（邊界常有 ~1e-14 噪音，即此守衛之用途）與 close。`mask_fn(values)` 為受測遮罩。"""
    import talib

    close = _close("1h")[:6000]
    fastk, _ = talib.STOCHRSI(close, timeperiod=14, fastk_period=3, fastd_period=3, fastd_matype=0)
    for series in (fastk, close):
        base = np.asarray(mask_fn(series), dtype=bool)
        # ①未來洩漏：尾端追加三倍長之「同一真實序列 ×1e9」（未來尺度劇變，使全欄中位數落入尾段），既有列之遮罩不變
        tail = np.asarray(mask_fn(np.r_[series, np.tile(series * 1e9, 3)]), dtype=bool)[: len(series)]
        assert np.array_equal(base, tail), "future"
        # ②與起算點無關：刪前 1,000 列重算，窗滿後逐列相同
        again = np.asarray(mask_fn(series[1000:]), dtype=bool)
        assert np.array_equal(base[1000:][300:], again[300:]), "start"


def test_denominator_mask_causal_and_start_independent() -> None:
    """Task 2.3（v53）：`safe_denominator` 與 Polars `_safe_denom_expr` 之近零遮罩因果、與起算點無關、兩路徑相同。"""
    import polars as pl

    from momentum.FeatureEngineering.polars_adapter import _safe_denom_expr
    from momentum.FeatureEngineering.utils.numeric_guards import safe_denominator

    def pandas_mask(values: np.ndarray) -> np.ndarray:
        return safe_denominator(pd.Series(values)).isna().to_numpy()

    def polars_mask(values: np.ndarray) -> np.ndarray:
        frame = pl.DataFrame({"d": values})
        return frame.select(_safe_denom_expr(frame, "d").alias("d"))["d"].fill_nan(None).is_null().to_numpy()

    _denominator_checks(pandas_mask)
    _denominator_checks(polars_mask)
    close = _close("1h")[:3000]
    assert np.array_equal(pandas_mask(close), polars_mask(close))


def test_mutation_denominator_full_column_median_is_caught() -> None:
    """v53 mutant：改回以全欄非零絕對值中位數為尺度（改前實作）⇒ 追加未來極值改變既有列之遮罩 ⇒ 必紅。"""

    def full_column(values: np.ndarray) -> np.ndarray:
        abs_d = np.abs(np.asarray(values, dtype=np.float64))
        nonzero = abs_d[np.isfinite(abs_d) & (abs_d > 0)]
        threshold = np.median(nonzero) * 1e-6 if nonzero.size else 0.0
        return ~np.isfinite(abs_d) | (abs_d == 0) | (abs_d < threshold)

    with pytest.raises(AssertionError):
        _denominator_checks(full_column)


def test_noncausal_winsor_helpers_fail_closed() -> None:
    """v53（審查 r36 codex P1-02）：`polars_l65_winsorization`、`transform_array_fast` 直接以
    `causal_preprocessing=False` 呼叫即拋例外（改前走全欄統計量＝未來洩漏；sigma 分支另於實跑拋 IndexError）；
    因果呼叫照常。"""
    import polars as pl

    from momentum.FeatureEngineering.polars_adapter import polars_l65_winsorization
    from momentum.FeatureEngineering.preprocessing._numba_transforms import transform_array_fast

    values = _close("1h")[:600].reshape(-1, 1).astype(np.float32)
    frame = pl.DataFrame({"c": values[:, 0].astype(np.float64)})
    for method in ("sigma", "quantile"):
        with pytest.raises(ValueError):
            polars_l65_winsorization(frame, columns=["c"], method=method, causal_preprocessing=False)
        with pytest.raises(ValueError):
            transform_array_fast(values, winsor_method=method, causal_preprocessing=False)
        polars_l65_winsorization(frame, columns=["c"], method=method, causal_preprocessing=True)
        transform_array_fast(values, winsor_method=method, causal_preprocessing=True)


def _foreign_market_ingestion_raises() -> bool:
    """以真實 BTC 1h 資料、但宣告市場為倍數表未量測者之 adapter 走 `_layer0_data_ingestion`；回傳是否 fail-closed。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
    from momentum.FeatureEngineering.atomic.warmup_lookup import WarmupTableError

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    registry = factory._adapter_registry
    real = registry.get("crypto_spot")

    class ForeignMarket(CryptoSpotAdapter):
        @property
        def market(self) -> str:
            return "tw_stock"

    foreign = object.__new__(ForeignMarket)
    foreign.__dict__.update(real.__dict__)
    registry._adapters["crypto_spot"] = foreign
    config = factory._resolve_config(h.stat_payload(fracdiff=False, adf=False))
    try:
        factory._layer0_data_ingestion(h.SYMBOL, h.PRIMARY_TF, config)
    except WarmupTableError:
        return True
    finally:
        registry._adapters["crypto_spot"] = real
    return False


def test_warmup_table_market_scope_fail_closed() -> None:
    """v52（審查 r35 codex P1-04）：倍數表僅以其 `_meta.market_scopes` 所列市場之真實資料量得；未量測市場之資料
    生成前即 fail-closed（不得把加密貨幣之 K 靜默套用於台股／美股／期貨）；已量測市場照常。"""
    from momentum.FeatureEngineering.atomic import warmup_lookup

    assert warmup_lookup.measured_market_scopes() == ("crypto",)
    warmup_lookup.assert_market_measured("crypto")
    with pytest.raises(warmup_lookup.WarmupTableError):
        warmup_lookup.assert_market_measured("tw_stock")
    assert _foreign_market_ingestion_raises()


def test_mutation_market_scope_check_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v52 mutant：生成入口之市場檢查改為 no-op ⇒ 未量測市場之資料照常生成 ⇒ 必紅。"""
    from momentum.FeatureEngineering.atomic import warmup_lookup

    monkeypatch.setattr(warmup_lookup, "assert_market_measured", lambda market: None)
    assert not _foreign_market_ingestion_raises()


def _binary_signal_checks() -> None:
    """第④類之生產呼叫端判定（審查 r34 codex P1-02）：以真實 BTC 1h RSI 14（L1 遮罩後）經
    `DerivedOperatorEngine.compute_binary_signal` 實跑——輸入首個有限值前之輸出全為 NaN、其後與逐點比較結果相同。"""
    import talib

    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    k = 50
    rsi = pd.Series(sm.apply_l1_mask(talib.RSI(_close("1h"), timeperiod=14), 0, k))
    first = sm.first_finite_index(rsi.to_numpy())
    assert first == k
    engine = DerivedOperatorEngine({})
    for condition, expect in (("> 20", rsi > 20), ("< 30", rsi < 30), ("> 70", rsi > 70)):
        out = engine.compute_binary_signal(rsi, condition, "close_1h_momentum_RSI_14").to_numpy()
        assert not np.isfinite(out[:first]).any(), condition
        np.testing.assert_array_equal(out[first:], expect.astype(float).to_numpy()[first:], err_msg=condition)


def test_binary_signal_prefix_masked_on_production_caller() -> None:
    """Task 2.3 ②（第④類，v51）：生產呼叫端 `compute_binary_signal` 之開頭段遮罩。"""
    _binary_signal_checks()


def test_mutation_binary_signal_prefix_unmasked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """第④類 mutant（審查 r34 codex P1-02）：`mask_pointwise_prefix` 改為不遮 ⇒ 開頭段為 0 而非 NaN ⇒ 必紅。"""
    monkeypatch.setattr(sm, "mask_pointwise_prefix", lambda output, inputs: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        _binary_signal_checks()


def test_nan_propagation_inventory_complete() -> None:
    """Task 2.3 ②：盤點收據之步驟集合＝AST 列舉 L2–L6.5 與多週期對齊之步驟函式集合（少一即紅），且每步有碼證與分類。"""
    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-nan-propagation-inventory.json"))
    assert receipts, "缺盤點收據（SPEC Task 2.3 檔案段）"
    inventory = json.loads(receipts[-1].read_text(encoding="utf-8"))
    steps = {row["function"]: row for row in inventory["steps"]}
    expected = _ast_step_functions()
    # r28 codex P1-01：三者須完全相等——AST 閉包、收據、golden 分類表；閉包意外縮小（漏列既有步驟）即紅
    golden = set(json.loads((REPO / "tests" / "_golden" / "ffstat" / "nan_propagation_classes.json")
                            .read_text(encoding="utf-8"))["steps"])
    assert set(steps) == expected, (sorted(expected - set(steps)), sorted(set(steps) - expected))
    assert set(steps) == golden, (sorted(golden - set(steps)), sorted(set(steps) - golden))
    classes = {"propagating", "incomplete_window", "recursive", "cumulative", "pointwise_prefix",
               "not_in_generation_path", "dispatcher", "index_derived", "helper", "column_filter", "mask"}
    for name, row in steps.items():
        assert row["propagates_nan"] in (True, False), name
        assert row["evidence"], name
        assert row["class"] in classes, name
        assert row["propagates_nan"] == (row["class"] == "propagating"), name
        if row["class"] == "dispatcher":
            # r25 codex P1-04／r26 codex P1-01：派發函式之輸出＝其所呼叫之已分類步驟之聯集 ⇒ 函式體須以限定名
            # （同類 self.X／cls.X ⇒ module:Class.X；同模組 X ⇒ module:X）呼叫至少一個非自身之已列步驟
            called = _called_qualified(name)
            assert called & (set(steps) - {name}), name
        if row["class"] in _NO_INLINE_CLASSES:
            # r27 codex P1-01：宣稱不自行產生未穩定值之類別，函式體不得內聯「NaN／未滿窗→有限值」之運算；
            # 有者須改列其非傳遞類（或列 _INLINE_ALLOWED 並附不產輸出值之理由）
            hits = _inline_nan_filling_calls(_function_node(name))
            assert not hits or name in _INLINE_ALLOWED, (name, hits)


# r27 codex P1-01：會把 NaN 或不完整窗變成有限值之運算（方法名）；比較式直接 astype 亦屬之（NaN 比較為 False）
_NAN_FILLING = frozenset({
    "rolling", "ewm", "expanding", "fillna", "ffill", "bfill", "interpolate", "cumsum", "cumprod", "cummax", "cummin",
    "nan_to_num", "where", "clip", "shift", "diff", "pct_change", "rank", "apply", "map_batches", "fill_null", "fill_nan",
    "forward_fill", "backward_fill", "nanmean", "nanstd", "nanquantile", "quantile", "rolling_mean", "rolling_std",
    "rolling_max", "rolling_min", "rolling_sum", "convolve", "lfilter",
})
# index_derived 之輸入為時間索引（無 NaN），由 test_index_derived_step_has_no_warmup 以真實切片驗證，不在此列
_NO_INLINE_CLASSES = frozenset({"dispatcher", "helper", "column_filter"})
# 函式體有上列運算但其結果不成為輸出特徵值者（限定名 → 理由）
_INLINE_ALLOWED = {
    "momentum.FeatureEngineering.preprocessing._hurst_prior:estimate_hurst_rs": "cumsum 算 Hurst 先驗純量（d* 搜尋用）",
    "momentum.FeatureEngineering.preprocessing._non_stationary_cache:NonStationaryCache.make_key": "nan_to_num 只用於快取鍵雜湊",
    "momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor._find_min_d": "ffill 於校準值上搜尋 d*，產出 d",
    "momentum.FeatureEngineering.timeframe.multi_tf_generator:MultiTFGenerator._log_gap_source_if_any": "diff 於時間戳記判缺口並記日誌",
    "momentum.FeatureEngineering.preprocessing.stable_mask:_dead_columns_2d": "np.where 算死欄判定統計量（NaN 率、有限值遮罩），只回判定、不產輸出值",
}


def _function_node(qualified: str) -> ast.FunctionDef:
    module, qual = qualified.split(":")
    path = REPO / Path(*module.split(".")).with_suffix(".py")
    return _module_functions(ast.parse(path.read_text(encoding="utf-8")))[qual]


def _inline_nan_filling_calls(node: ast.AST) -> List[str]:
    """函式體內 `X.<_NAN_FILLING>(…)` 與 `(比較式).astype(…)` 之呼叫（`名稱@行`）。"""
    hits = []
    for call in ast.walk(node):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
            attr = call.func.attr
            if attr in _NAN_FILLING or (attr == "astype" and isinstance(call.func.value, ast.Compare)):
                hits.append(f"{attr}@{call.lineno}")
    return hits


def test_mutation_dispatcher_inline_rolling_is_caught() -> None:
    """r27 codex P1-01 反例之可證偽版：派發函式先呼叫合法子步驟、再於函式體內以 min_periods=1 之 rolling 自原始
    close 造欄 ⇒ 內聯檢查須命中；只原樣搬移原始欄（無暖機，首個有限值即穩定）不在遮罩語意內，不命中。"""
    import inspect
    import textwrap

    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    node = ast.parse(textwrap.dedent(inspect.getsource(DerivedOperatorEngine.compute_all))).body[0]
    assert not _inline_nan_filling_calls(node)
    injected = ast.parse("_inj = raw_data['close'].rolling(20, min_periods=1).mean()").body[0]
    node.body.insert(0, injected)
    assert _inline_nan_filling_calls(node) == [f"rolling@{injected.lineno}"]
    node.body[0] = ast.parse("_inj = raw_data['close'].to_numpy()").body[0]
    assert not _inline_nan_filling_calls(node)
    node.body[0] = ast.parse("_inj = (raw_data['close'] > 0).astype(float)").body[0]
    assert _inline_nan_filling_calls(node)


def _step_source_files() -> List[Path]:
    """盤點之 AST 來源檔：L2–L6.5 與多週期對齊之子套件，外加 polars_adapter.py。"""
    base = REPO / "momentum" / "FeatureEngineering"
    files: List[Path] = []
    for root in ("operators", "cross_sectional", "meta_features", "preprocessing", "timeframe"):
        files.extend(sorted((base / root).rglob("*.py")))
    files.append(base / "polars_adapter.py")
    return files


def _import_map(tree: ast.AST, module: str) -> Dict[str, str]:
    """模組內 `from X import name [as alias]` 之 alias → X（相對 import 依 module 解析）。"""
    out: Dict[str, str] = {}
    pkg = module.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None or isinstance(node, ast.ImportFrom) and node.level:
            src = node.module or ""
            if node.level:
                parts = pkg.split(".")
                src = ".".join(parts[: len(parts) - node.level + 1] + ([src] if src else []))
            for alias in node.names:
                out[alias.asname or alias.name] = f"{src}:{alias.name}"
    return out


def _module_functions(tree: ast.AST) -> Dict[str, ast.FunctionDef]:
    """模組內函式之限定名 → 節點：類別方法 `Class.f`；非類別、非巢狀於函式者 `f`（含定義於模組層
    `if HAS_NUMBA:`／`try:` 區塊內者，如 `_worldquant_numba._ts_argmax_2d`）。"""
    out: Dict[str, ast.FunctionDef] = {}

    def visit(node: ast.AST, owner: Optional[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, child.name)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[f"{owner}.{child.name}" if owner else child.name] = child
            else:
                visit(child, owner)

    visit(tree, None)
    return out


def _called_qualified(qualified: str) -> set:
    """函式體內引用之限定名集合（AST；含呼叫與以值傳遞如 `executor.submit(self.f, …)`）：`self.X`／`cls.X`
    綁定於同一類別；`Class.X`（同模組類別）綁定於該類別；裸名 `X` 依模組之 from-import 解析為來源限定名，
    否則綁定於同一模組；`mod.X`（`from pkg import mod`）⇒ `pkg.mod:X`（r27 codex P1-01）。"""
    module, qual = qualified.split(":")
    path = REPO / Path(*module.split(".")).with_suffix(".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = _module_functions(tree).get(qual)
    if node is None:
        return set()
    owner = qual.split(".")[0] if "." in qual else None
    imports = _import_map(tree, module)
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    names = set()
    for ref in ast.walk(node):
        if isinstance(ref, ast.Attribute) and isinstance(ref.value, ast.Name):
            base = ref.value.id
            if base in ("self", "cls") and owner:
                names.add(f"{module}:{owner}.{ref.attr}")
            elif base in classes:
                names.add(f"{module}:{base}.{ref.attr}")
            elif base in imports:
                # `from pkg import mod` ⇒ pkg.mod:X；`from pkg.mod import Class` ⇒ pkg.mod:Class.X（r28 codex P2-02）
                src, imported = imports[base].split(":")
                as_module = REPO / Path(*f"{src}.{imported}".split(".")).with_suffix(".py")
                names.add(f"{src}.{imported}:{ref.attr}" if as_module.exists() else f"{src}:{imported}.{ref.attr}")
        elif isinstance(ref, ast.Name) and isinstance(ref.ctx, ast.Load):
            names.add(imports.get(ref.id, f"{module}:{ref.id}"))
    return names


def test_dispatcher_call_resolution_is_class_bound() -> None:
    """r26 codex P1-01：派發檢查以限定名綁定類別——`_rolling_last_rank_pct` 於 L2（DerivedOperatorEngine）與
    L3（RollingAggregator）同名，L3 派發函式之呼叫集合不得含 L2 之同名方法，反之亦然。"""
    base = "momentum.FeatureEngineering.operators"
    l3 = _called_qualified(f"{base}.rolling_aggregator:RollingAggregator.compute_all")
    assert any(n.startswith(f"{base}.rolling_aggregator:RollingAggregator.") for n in l3)
    assert not any("DerivedOperatorEngine." in n for n in l3)
    l2 = _called_qualified(f"{base}.derived_operators:DerivedOperatorEngine.compute_all")
    assert any(n.startswith(f"{base}.derived_operators:DerivedOperatorEngine.") for n in l2)
    assert not any("RollingAggregator." in n for n in l2)


def test_inventory_closure_reaches_off_prefix_and_nested_steps() -> None:
    """r27 codex P1-01：盤點為呼叫鏈遞移閉包——名稱不合前綴（縮尾核心）、模組層 `if HAS_NUMBA:` 內定義（WQ 核心）、
    polars_adapter 經 import 呼叫、以及 L6.5 公開入口皆須入列。"""
    got = _ast_step_functions()
    fe = "momentum.FeatureEngineering"
    for name in (f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent",
                 f"{fe}.operators._worldquant_numba:_ts_argmax_2d",
                 f"{fe}.polars_adapter:polars_l2_derived_momentum",
                 f"{fe}.polars_adapter:polars_l65_winsorization",
                 f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor.transform_registry_groups_to_sink",
                 f"{fe}.preprocessing._numba_transforms:transform_array_fast",
                 # r28 codex P2-02：`from … import TimeframeAligner` 後之 TimeframeAligner.X 解析為類別方法
                 f"{fe}.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys"):
        assert name in got, name


def test_index_derived_step_has_no_warmup() -> None:
    """r25 codex P1-04：index_derived（時間特徵）只由索引算出 ⇒ 真實 1h 切片第 0 列即有限值、與 L1 遮罩無關。"""
    from momentum.FeatureEngineering.meta_features.time_features import TimeFeatureEngine

    index = h.kline_frame(timeframe="1h").index[:500]
    out = TimeFeatureEngine().compute_all(pd.Series(index, index=index))
    assert not out.empty
    assert out.iloc[0].notna().all()


def _ast_step_functions() -> set:
    """L2 operators、L3 rolling、L4 lag、L5 cross_sectional、L6 meta_features、L6.5 preprocessing、多週期 tf_aligner
    之公開計算函式（模組:限定名）。"""
    # r24 codex P1-01：公開與私有之計算／對齊入口皆列（含 _compute_all_streaming、_searchsorted_align、_merge_asof_align）
    # r27 codex P1-01：納入 polars_adapter.py（L2 Polars 批次與 L6.5 Polars 縮尾）與 L6.5 之 _transform* 執行入口
    # 前綴只作種子；再取「種子所呼叫、且定義於來源檔之函式」之遞移閉包——名稱不合前綴之步驟
    # （如 _winsorize_2d_legacy_equivalent、_gaussian_2d）只要在呼叫鏈上即入盤點
    prefixes = ("compute", "_compute", "apply", "_apply", "align", "_align", "_merge", "_searchsorted", "_rolling",
                "_dead", "_variance", "polars_", "_transform")
    defined = set()
    for path in _step_source_files():
        module = ".".join(path.relative_to(REPO).with_suffix("").parts)
        defined |= {f"{module}:{q}" for q in _module_functions(ast.parse(path.read_text(encoding="utf-8")))}
    # 種子＝一切公開函式（L6.5 之 transform／transform_registry_groups* 等入口不合前綴）＋合前綴之私有函式
    out = {q for q in defined if not (n := q.split(":")[1].split(".")[-1]).startswith("_") or n.startswith(prefixes)}
    frontier = set(out)
    while frontier:
        reached = set().union(*(_called_qualified(q) for q in frontier)) & defined
        frontier = reached - out
        out |= frontier
    return out


# ─────────────────────────────── ③④ 無起始日

def test_no_start_stationarity_off_stable_values_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ③：無起始日、平穩化關閉 ⇒ 各欄 stable_start 前全 NaN；鏈上無第②③類者 stable_start 後與凍結基準逐位元組相同。"""
    baseline_path = REPO / CONTRACT["nostart_baseline"]
    assert baseline_path.exists(), "缺無起始日凍結基準（§G：以 FF-STAT 動工前 commit 於獨立 worktree 重凍）"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    block = int(baseline["block_rows"])
    h.prepare_stat_env(monkeypatch, tmp_path)
    # 基準為全史（無起始日、無結束日，freeze_baseline_nostart.py）⇒ 本 run 亦不帶結束日（helper 預設結束日為 WINDOW 末，
    # 會使末一區塊只含部分列而 hash 必不同）
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=None,
                                        end_date=None)
    assert int(baseline["rows"]) == len(_public_column(root, next(iter(baseline["columns"])))), "列數與基準不同"
    stable = result.metadata[CONTRACT["stable_start_receipt_key"]]
    # v50（審查 r33）：L3 mean／std／zscore／skew／kurt 改為逐窗精確計算，改前基準之該類值帶增量實作之缺陷（常數窗
    # std 非零、值依起算點而異）⇒ 不與改前基準逐位元組比，改由 ⑨′ 以 float64 逐窗 oracle 驗；其餘欄照常比
    import re

    v50_changed = re.compile(r"_(Mean|Std|ZScore|Skew|Kurt)_W\d+$")
    exempt = set(baseline.get("chain_has_class_2_or_3", [])) | {c for c in baseline["columns"] if v50_changed.search(c)}
    compared = 0
    for column, blocks in baseline["columns"].items():
        series = _public_column(root, column)
        start = pd.Timestamp(stable[column])
        assert series.loc[:start - pd.Timedelta(microseconds=1)].isna().all(), column
        if column in exempt:
            continue
        first_full_block = -(-int((series.index < start).sum()) // block)
        values = series.to_numpy(dtype=np.float64)
        for b in range(first_full_block, len(blocks)):
            chunk = values[b * block:(b + 1) * block]
            assert hashlib.sha256(chunk.tobytes()).hexdigest() == blocks[b], (column, b)
            compared += 1
    assert compared > 0


def test_no_start_calibration_rows_masked_from_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：無起始日、平穩化開啟 ⇒ 校準值＝各欄最早 N 個有效值（spy）；該 N 列於公開輸出（含衍生欄）全 NaN。"""
    calls: List[Any] = []
    original = sm.calibration_rows_no_start

    def spy(values: np.ndarray, n: int):
        rows = original(values, n)
        calls.append(rows)
        return rows

    monkeypatch.setattr(sm, "calibration_rows_no_start", spy)
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(), start_date=None)
    assert calls, "未以 calibration_rows_no_start 取校準列"
    assert result.metadata[h.META["output_start_source"]] == "per_column"
    assert h.META["effective_output_start"] not in result.metadata  # v44：per_column 不寫
    for column, record in h.decisions(result).items():
        if record.get("calibration_end") is None:
            continue
        out = _public_column(root, column)
        window = out.loc[:pd.Timestamp(record["calibration_end"])]
        assert window.isna().all(), column


_COLUMN_INDEX: Dict[str, Dict[str, Path]] = {}
_TIME_AXIS: Dict[str, Any] = {}


def _column_index(root: Path) -> Dict[str, Path]:
    """root 下公開輸出之欄名 → 所在 parquet（只讀檔頭 schema，一個 root 建一次）。逐欄呼叫 `_public_column` 時
    避免每欄重讀全部檔案（多週期全史數千欄 × 數十檔之 I/O 於 8GB 機器可達數小時）。"""
    import pyarrow.parquet as pq

    key = str(root.resolve())
    if key not in _COLUMN_INDEX:
        index: Dict[str, Path] = {}
        for p in sorted(root.rglob("*.parquet")):
            if p.name == "timestamps.parquet":
                continue
            for n in pq.read_schema(p).names:
                index.setdefault(n, p)
        _COLUMN_INDEX[key] = index
    return _COLUMN_INDEX[key]


def _public_column(root: Path, column: str) -> pd.Series:
    import pyarrow.parquet as pq

    p = _column_index(root).get(column)
    if p is None:
        raise AssertionError(f"找不到欄 {column}")
    names = pq.read_schema(p).names
    frame = pq.read_table(p, columns=[column] + (["timestamp"] if "timestamp" in names else []))
    if "timestamp" in names:
        idx = pd.to_datetime(frame.column("timestamp").to_numpy(), unit="ms", utc=True)
    else:
        # L7 raw：群組 parquet 無時間欄，時間軸為 run 目錄之 timestamps.parquet（UTC epoch 秒）
        stamps = next((q for q in [*p.parents] if (q / "timestamps.parquet").exists()), None)
        assert stamps is not None, f"找不到 {p} 所屬 run 之 timestamps.parquet"
        skey = str(stamps.resolve())
        if skey not in _TIME_AXIS:
            seconds = pq.read_table(stamps / "timestamps.parquet").column("timestamp").to_numpy()
            _TIME_AXIS[skey] = pd.to_datetime(seconds, unit="s", utc=True)
        idx = _TIME_AXIS[skey]
    return pd.Series(frame.column(column).to_numpy(zero_copy_only=False), index=idx)


def _utc(value: Any) -> pd.Timestamp:
    """時間比較一律 UTC（metadata 之時間為帶時區 ISO；K 線 index 可能無時區——視為 UTC）。"""
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def test_no_start_leak_after_calibration_rows_does_not_change_decisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：改動校準列之後之 close（×1.5）⇒ 決策與 d 不變。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "a")
    _r, _f, base = h.run_stat(tmp_path / "a", h.stat_payload(), start_date=None)
    klines = h.kline_copy(tmp_path / "b")
    latest_cal_end = max(pd.Timestamp(r["calibration_end"]) for r in h.decisions(base).values() if r.get("calibration_end"))
    h.scale_kline_close(klines, (latest_cal_end + pd.Timedelta(hours=1)).isoformat(), "2100-01-01", 1.5)
    h.prepare_stat_env(monkeypatch, tmp_path / "b")
    _r2, _f2, moved = h.run_stat(tmp_path / "b", h.stat_payload(), start_date=None, kline_dir=str(klines))
    for column, record in h.decisions(base).items():
        other = h.decisions(moved)[column]
        assert (record["fracdiff"], record["adf_differenced"], record["d"]) == (other["fracdiff"], other["adf_differenced"], other["d"]), column


def test_no_start_change_inside_calibration_rows_changes_some_decision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：改動校準列內之 close ⇒ 至少一欄決策或 d 改變（證明確實讀校準列）。"""
    h.prepare_stat_env(monkeypatch, tmp_path / "a")
    _r, _f, base = h.run_stat(tmp_path / "a", h.stat_payload(), start_date=None)
    klines = h.kline_copy(tmp_path / "b")
    first = h.kline_frame().index[0]
    h.scale_kline_close(klines, first.isoformat(), (first + pd.Timedelta(days=120)).isoformat(), 3.0)
    h.prepare_stat_env(monkeypatch, tmp_path / "b")
    _r2, _f2, moved = h.run_stat(tmp_path / "b", h.stat_payload(), start_date=None, kline_dir=str(klines))
    changed = [c for c, r in h.decisions(base).items()
               if (r["fracdiff"], r["d"]) != (h.decisions(moved)[c]["fracdiff"], h.decisions(moved)[c]["d"])]
    assert changed


def test_no_start_insufficient_history_column_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ④：全史有效值不足 N 之欄 ⇒ calibration_insufficient_history、未平穩化、partial、有效值照常輸出。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    klines = h.kline_copy(tmp_path)
    last = h.kline_frame().index[-1]
    h.drop_kline_rows_before(klines, (last - pd.Timedelta(hours=700)).isoformat(), symbol=h.SYMBOL)
    payload = h.stat_payload()
    payload["preprocessing"]["calibration_bars"] = 500
    # 結束日取保留段之末（helper 預設 WINDOW 結束日早於保留之最後 700 小時 ⇒ 否則 L0 為空）
    root, _factory, result = h.run_stat(tmp_path, payload, start_date=None, end_date=last.isoformat(),
                                        kline_dir=str(klines))
    flagged = [c for c, r in h.decisions(result).items() if h.EVENTS["calibration_insufficient"] in " ".join(r["events"])]
    assert flagged
    assert result.metadata.get("quality_status") == "partial"
    for column in flagged:
        assert not h.decisions(result)[column]["fracdiff"]
        assert _public_column(root, column).notna().any(), column


# ─────────────────────────────── ⑤ 有起始日

def test_with_start_far_no_warmup_insufficient(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑤：起始日離資料起點足夠遠 ⇒ 全部欄首個有效值 ≤ 起始日、無 warmup_insufficient_history。

    「首個有效值」指計算域（含起始日前之預熱列）之首個有限值。公開輸出首列為 NaN 而計算域更早已有有限值者屬資料
    所致之間歇 NaN（真實 BTC 1h：2026-01-01 前 16 小時 MIDPOINT_144 恆定 ⇒ 13 根窗 Kurt 無定義），非預熱不足；
    以獨立之第二次生成（起始日提前 30 日）驗此類欄於原起始日前確有有限值。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    payload = h.stat_payload(fracdiff=False, adf=False)
    root, _factory, result = h.run_stat(tmp_path, payload)
    assert h.EVENTS["warmup_insufficient"] not in json.dumps(result.metadata.get("failure_reasons", []))
    assert not result.metadata.get("warmup_insufficient_columns")
    start = pd.Timestamp(h.WINDOW[0], tz="UTC")
    public_late = sorted(c for c, ts in result.metadata[CONTRACT["stable_start_receipt_key"]].items()
                         if ts is not None and pd.Timestamp(ts) > start)
    if not public_late:
        return
    earlier = (start - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    root_b, _factory_b, result_b = h.run_stat(tmp_path / "earlier", payload, start_date=earlier)
    starts_b = result_b.metadata[CONTRACT["stable_start_receipt_key"]]
    for column in public_late:
        assert starts_b.get(column) is not None and pd.Timestamp(starts_b[column]) < start, column
        series = _public_column(root_b, column)
        assert np.isfinite(series[series.index < start].to_numpy(dtype=np.float64)).any(), column


def test_chunked_memmap_keeps_appended_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """⑪ 實跑所得（frame 路徑 L6.5 靜默降級）：欄分塊＋memmap 時，append 模式之衍生欄使 chunk 輸出寬於輸入
    ⇒ 輸出欄名與值須與不走 memmap 之分塊結果相同（改前固定寬度 ⇒ broadcast 例外、整層降級）；另含 chunk 輸出
    窄於輸入之情形（欄名不得錯位）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    close = pd.Series(_close("1h")[:3000])
    frame = pd.DataFrame({f"c_{w}": close.rolling(w).mean() for w in (2, 3, 5, 8, 13, 21, 34)})

    def fake_single(self, chunk: pd.DataFrame) -> pd.DataFrame:
        out = chunk.copy()
        for name in chunk.columns:
            if name.endswith(("_2", "_5", "_13")):
                out[f"{name}_fracdiff"] = chunk[name].diff()  # append 模式衍生欄
            if name.endswith("_34"):
                out = out.drop(columns=[name])  # 窄於輸入
        return out

    monkeypatch.setattr(FeaturePreprocessor, "_transform_single", fake_single)
    pre = FeaturePreprocessor({})
    monkeypatch.setattr(FeaturePreprocessor, "_CHUNKED_MEMMAP_MIN_BYTES", 10 ** 18)
    expected = pre._transform_chunked(frame, chunk_size=2)
    monkeypatch.setattr(FeaturePreprocessor, "_CHUNKED_MEMMAP_MIN_BYTES", 0)
    got = pre._transform_chunked(frame, chunk_size=2)
    assert list(got.columns) == list(expected.columns)
    assert len(expected.columns) == len(frame.columns) + 3 - 1
    np.testing.assert_array_equal(got.to_numpy(), expected.to_numpy(dtype=np.float32))


_WINSOR_PATHS = {
    # 路徑名 → (FFACT_USE_POLARS, FFACT_L65_OPTIMIZATION_PROFILE, mode, 欄分塊大小〔0＝不分塊〕)
    "polars": ("1", "optimized", "append", 0),
    "legacy_append": ("0", "optimized", "append", 0),
    "optimized_replace": ("0", "optimized", "replace", 0),
    "legacy_replace": ("0", "legacy", "replace", 0),
    "chunked": ("0", "optimized", "append", 2),
}


@pytest.mark.parametrize("path", sorted(_WINSOR_PATHS))
def test_winsorization_switch_honoured_on_every_path(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """審查 r34 主委實跑所得（改前既有缺陷）：`winsorization.enabled=False` 時 L6.5 各轉換路徑須不縮尾、輸出＝輸入；
    改前 `_transform_single_legacy`、`_transform_single_optimized_df`、`_transform_single_polars` 無視開關（其餘轉換皆有
    `enabled` 判斷），關縮尾仍縮尾並遮開頭 251 列。同一路徑開縮尾須與輸入不同（證明本測試觀測得到縮尾）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    polars, profile, mode, chunk = _WINSOR_PATHS[path]
    monkeypatch.setenv("FFACT_USE_POLARS", polars)
    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", profile)
    close = pd.Series(_close("1h")[:2000])
    frame = pd.DataFrame({f"c_{w}": close.pct_change(w) for w in (1, 3, 8)}).astype(np.float32)

    def run(enabled: bool) -> pd.DataFrame:
        pre = FeaturePreprocessor({"enabled": True, "mode": mode, "causal_preprocessing": True,
                                   "winsorization": {"enabled": enabled, "method": "quantile"},
                                   "rank_transform": {"enabled": False}, "adaptive_zscore": {"enabled": False},
                                   "gaussian_normalize": {"enabled": False},
                                   "fractional_differencing": {"enabled": False},
                                   "adf_differencing": {"enabled": False}})
        if chunk:
            return pre._transform_chunked(frame, chunk_size=chunk)
        return pre.transform(frame)

    off = run(False)
    for name in frame.columns:
        np.testing.assert_array_equal(off[name].to_numpy(dtype=np.float32), frame[name].to_numpy(), err_msg=name)
    on = run(True)
    assert not np.array_equal(np.isnan(on["c_1"].to_numpy()), np.isnan(frame["c_1"].to_numpy())), path


def _l3_oracle(values: np.ndarray, window: int) -> np.ndarray:
    """L3 滾動統計之獨立 float64 逐窗 oracle（numpy＋scipy）：mean、std(ddof=1)、zscore、skew（bias=False）、
    kurt（Fisher、bias=False）；窗內任一 NaN ⇒ NaN。常數窗 std＝0、其餘 NaN。

    v51（審查 r34 codex P1-03）：skew／kurt 之退化契約（canonical，`numba_rolling._compute_skew`／`_compute_kurt`
    之既有守衛，此處以 numpy 獨立重算）——①相對退化：Σ(x−mean)² ≤ 1e-12 ×（Σ(x−mean)²＋n·mean²）⇒ NaN（例：真實
    BTC 1h MIDPOINT 窗內僅 float32 末位之差）；②樣本界：|skew| > √n 或 kurt 超出 [−2(n−1)/(n−3), n]（容差 1e-9）⇒ NaN。"""
    from scipy import stats

    n = len(values)
    out = np.full((n, 5), np.nan)
    xs = np.lib.stride_tricks.sliding_window_view(values, window)
    w = float(window)
    for k, win in enumerate(xs):
        i = k + window - 1
        if not np.isfinite(win).all():
            continue
        mean = float(np.mean(win))
        out[i, 0] = mean
        if win.max() == win.min():
            out[i, 1] = 0.0
            continue
        std = float(np.std(win, ddof=1))
        out[i, 1] = std
        out[i, 2] = (win[-1] - mean) / std
        m2 = float(np.sum((win - mean) ** 2))
        if m2 <= 1e-12 * (m2 + w * mean * mean):
            continue
        skew = float(stats.skew(win, bias=False))
        kurt = float(stats.kurtosis(win, fisher=True, bias=False))
        if window >= 3 and abs(skew) <= math.sqrt(w) * (1.0 + 1e-9):
            out[i, 3] = skew
        if window >= 4 and -2.0 * (w - 1.0) / (w - 3.0) * (1.0 + 1e-9) <= kurt <= w * (1.0 + 1e-9):
            out[i, 4] = kurt
    return out


def _l3_exact_checks(fused, skew_kurt) -> None:
    """⑨′ 之判定：真實 BTC 1h MIDPOINT_21（分段常數、常數窗多）與 EMA_34 之 L3 與 oracle 相等（float32 精度內）、
    常數窗 std＝0、刪前 300 列重算重疊段逐位元組相同。`fused`／`skew_kurt` 為受測函式（mutant 以此注入）。"""
    import talib

    close = _close("1h")[:6000]
    for series in (talib.MIDPOINT(close, 21), talib.EMA(close, 34)):
        for window in (5, 13, 21):
            got = np.column_stack([fused(series, window)[:, [0, 1, 5]], skew_kurt(series, window)]).astype(np.float64)
            want = _l3_oracle(series, window)
            for k in range(5):
                # v51（審查 r34 codex P1-03）：先要求有限值位置全等（改前只比兩邊皆有限之列，NaN 可掩蓋有限值）
                assert np.array_equal(np.isfinite(got[:, k]), np.isfinite(want[:, k])), ("mask", window, k)
                both = np.isfinite(got[:, k]) & np.isfinite(want[:, k])
                scale = np.maximum(np.abs(want[both, k]), 1.0)
                assert np.all(np.abs(got[both, k] - want[both, k]) <= 1e-5 * scale), (window, k)
            const = np.isfinite(want[:, 0]) & (want[:, 1] == 0.0)
            assert np.all(got[const, 1] == 0.0) and not np.isfinite(got[const, 2]).any(), window
            again = np.column_stack([fused(series[300:], window), skew_kurt(series[300:], window)])
            first = np.column_stack([fused(series, window), skew_kurt(series, window)])[300:]
            assert np.array_equal(first[window:], again[window:], equal_nan=True), window


def test_l3_rolling_exact_and_start_independent() -> None:
    """Task 2.3 ⑨′（v50，審查 r33 兩家一致）：L3 滾動 mean／std／zscore／skew／kurt 為與起算點無關之逐窗精確計算。"""
    from momentum.FeatureEngineering.operators.numba_rolling import fused_rolling_stats, rolling_skew_kurt

    _l3_exact_checks(fused_rolling_stats, rolling_skew_kurt)


def test_mutation_l3_incremental_welford_is_caught() -> None:
    """⑨′ mutant：改回 Welford 增量加入／移除（改前實作）⇒ 常數窗 std 非零、刪前列重算不同 ⇒ 必紅。"""
    from momentum.FeatureEngineering.operators.numba_rolling import rolling_skew_kurt

    def welford_fused(data: np.ndarray, window: int) -> np.ndarray:
        out = np.full((len(data), 6), np.nan)
        count, mean, m2 = 0, 0.0, 0.0
        for i, value in enumerate(data):
            if i >= window and np.isfinite(data[i - window]):
                old = data[i - window]
                count -= 1
                if count:
                    delta = old - mean
                    mean -= delta / count
                    m2 -= delta * (old - mean)
                else:
                    mean, m2 = 0.0, 0.0
            if np.isfinite(value):
                count += 1
                delta = value - mean
                mean += delta / count
                m2 += delta * (value - mean)
            if i >= window - 1 and count >= window:
                std = np.sqrt(max(m2, 0.0) / (count - 1))
                out[i, 0], out[i, 1] = mean, std
                out[i, 5] = (value - mean) / std if std > 0 else np.nan
        return out.astype(np.float32)

    with pytest.raises(AssertionError):
        _l3_exact_checks(welford_fused, rolling_skew_kurt)


def _slope_checks(slope_fn) -> None:
    """v51：L3 Slope 為逐窗精確（與 float64 最小平方 oracle 相等）且與起算點無關（刪前 2,049 列重算重疊段逐位元組
    相同）。真實 BTC 1h close 與 STOCHRSI fastd（§G⑦ 分解判準實跑所得之不等欄）。"""
    import talib

    close = _close("1h")[:8000]
    _, fastd = talib.STOCHRSI(close, timeperiod=14, fastk_period=3, fastd_period=3, fastd_matype=0)
    for series in (close, fastd):
        for window in (3, 5, 21):
            got = np.asarray(slope_fn(series, window), dtype=np.float64)
            xs = np.lib.stride_tricks.sliding_window_view(series, window)
            x = np.arange(window, dtype=np.float64)
            want = np.full(len(series), np.nan)
            ok = np.isfinite(xs).all(axis=1)
            want[window - 1:][ok] = [np.polyfit(x, win, 1)[0] for win in xs[ok]]
            assert np.array_equal(np.isfinite(got), np.isfinite(want)), ("mask", window)
            both = np.isfinite(want)
            scale = np.maximum(np.abs(want[both]), np.nanstd(series) * 1e-3)
            assert np.all(np.abs(got[both] - want[both]) <= 1e-5 * scale), ("value", window)
            again = np.asarray(slope_fn(series[2049:], window))
            assert np.array_equal(np.asarray(slope_fn(series, window))[2049:][window:], again[window:],
                                  equal_nan=True), ("start", window)


def test_l3_slope_exact_and_start_independent() -> None:
    """Task 2.3 ⑨′（v51）：L3 Slope 逐窗精確、與起算點無關。"""
    from momentum.FeatureEngineering.operators.numba_rolling import rolling_slope

    _slope_checks(rolling_slope)


def test_l3_slope_fallback_path_exact_and_start_independent() -> None:
    """Task 2.3 ⑨′（v52，審查 r35 codex P1-06）：非預設路徑（non-streaming、chunked、pandas 備援）之
    `RollingAggregator._compute_slope_vectorized` 與預設路徑同一契約。"""
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    def via_fallback(series: np.ndarray, window: int) -> np.ndarray:
        frame = pd.DataFrame({"x": np.asarray(series, dtype=np.float64)})
        return RollingAggregator._compute_slope_vectorized(frame, window)["x"].to_numpy()

    _slope_checks(via_fallback)


def test_mutation_l3_slope_absolute_index_running_sums_is_caught() -> None:
    """⑨′ mutant（v51）：改回以絕對列號累加之 running sums（改前實作）⇒ 刪前列重算之末位不同 ⇒ 必紅。"""

    def running_sums(data: np.ndarray, window: int) -> np.ndarray:
        n = len(data)
        out = np.full(n, np.nan)
        w = float(window)
        sum_x = w * (w - 1.0) / 2.0
        den = w * (w * (w - 1.0) * (2.0 * w - 1.0) / 6.0) - sum_x * sum_x
        sum_y = sum_jy = 0.0
        valid = 0
        for i in range(n):
            if i >= window and np.isfinite(data[i - window]):
                sum_y -= data[i - window]
                sum_jy -= float(i - window) * data[i - window]
                valid -= 1
            if np.isfinite(data[i]):
                sum_y += data[i]
                sum_jy += float(i) * data[i]
                valid += 1
            if i >= window - 1 and valid >= window:
                out[i] = (w * (sum_jy - float(i - window + 1) * sum_y) - sum_x * sum_y) / den
        return out.astype(np.float32)

    with pytest.raises(AssertionError):
        _slope_checks(running_sums)


def test_mutation_l3_skew_kurt_all_nan_is_caught() -> None:
    """⑨′ mutant（審查 r34 codex P1-03）：skew／kurt 全列回傳 NaN ⇒ 有限值位置與 oracle 不等 ⇒ 必紅。"""
    from momentum.FeatureEngineering.operators.numba_rolling import fused_rolling_stats

    with pytest.raises(AssertionError, match="mask"):
        _l3_exact_checks(fused_rolling_stats, lambda data, window: np.full((len(data), 2), np.nan))


def test_mutation_l3_degeneracy_guard_removed_is_caught() -> None:
    """⑨′ mutant（審查 r34 codex P1-03）：刪相對退化守衛（窗內僅末位之差仍出 skew／kurt）⇒ 真實 BTC 1h MIDPOINT 之
    近常數窗有限值位置與 oracle 不等 ⇒ 必紅。"""
    from scipy import stats

    from momentum.FeatureEngineering.operators.numba_rolling import fused_rolling_stats

    def unguarded(data: np.ndarray, window: int) -> np.ndarray:
        out = np.full((len(data), 2), np.nan)
        for k, win in enumerate(np.lib.stride_tricks.sliding_window_view(data, window)):
            if np.isfinite(win).all() and win.max() != win.min():
                out[k + window - 1] = (stats.skew(win, bias=False), stats.kurtosis(win, fisher=True, bias=False))
        return out

    with pytest.raises(AssertionError, match="mask"):
        _l3_exact_checks(fused_rolling_stats, unguarded)


def test_chunked_memmap_all_chunks_empty_returns_zero_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """審查 r33 codex P1-05：欄分塊＋memmap 時每個 chunk 皆回傳零欄 ⇒ 回傳與 index 對齊之零欄 DataFrame（改前零大小
    memmap 拋 `ValueError: cannot mmap an empty file`）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    close = pd.Series(_close("1h")[:500])
    frame = pd.DataFrame({f"c_{w}": close.rolling(w).mean() for w in (2, 3, 5)})
    monkeypatch.setattr(FeaturePreprocessor, "_transform_single", lambda self, chunk: pd.DataFrame(index=chunk.index))
    monkeypatch.setattr(FeaturePreprocessor, "_CHUNKED_MEMMAP_MIN_BYTES", 0)
    got = FeaturePreprocessor({})._transform_chunked(frame, chunk_size=2)
    assert got.shape == (len(frame), 0) and got.index.equals(frame.index)


def test_probe_columns_without_finite_values_counted_late(monkeypatch: pytest.MonkeyPatch) -> None:
    """審查 r33 codex P1-03：探測段內無有限值之欄（首個有限值落在探測上界之後）須計入晚到集合，不得因 `has=False`
    被當成未晚到而漏報。以真實 BTC 1h close 為探測域之一欄；另一欄為真實 TA-Lib SMA、週期＝探測域列數＋1（v51，審查
    r34 codex P2-01：改前為全 NaN 常數欄）——探測段內無有限值，而同一指標於探測上界之後之真實資料確有有限值。"""
    import talib

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing import calibration as cal

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(h.stat_payload(fracdiff=False, adf=False))
    probed: Dict[str, Any] = {}

    def fake_domain(_factory, _symbol, _tf, _config, klines):
        close = klines["close"].to_numpy(dtype=np.float64)
        probed["start"], probed["end"], probed["period"] = klines.index[0], klines.index[-1], len(close) + 1
        late = talib.SMA(close, timeperiod=probed["period"])
        return pd.DataFrame({"close_trend_REAL": close, "close_trend_LATE": late}, index=klines.index)

    monkeypatch.setattr(cal, "compute_calibration_domain", fake_domain)
    window = factory._resolve_public_window(h.SYMBOL, h.PRIMARY_TF, config, *h.WINDOW)
    bound_window, late = factory._public_warmup_late
    assert bound_window is window
    # 同一指標自同一起點延續至探測上界之後之真實資料：首個有限值恰在上界之後（真實延後出值，非恆 NaN）
    full = h.kline_frame(timeframe=h.PRIMARY_TF)
    tail = full[pd.DatetimeIndex(full.index) >= pd.to_datetime(probed["start"], utc=True)]
    after = talib.SMA(tail["close"].to_numpy(dtype=np.float64), timeperiod=probed["period"])
    first = int(np.argmax(np.isfinite(after)))
    assert np.isfinite(after).any() and tail.index[first] > pd.to_datetime(probed["end"], utc=True)
    assert cal.tagged_column_name("close_trend_LATE", h.PRIMARY_TF) in late
    assert cal.tagged_column_name("close_trend_REAL", h.PRIMARY_TF) not in late


def test_warmup_late_only_counts_probe_late_columns() -> None:
    """Task 2.3 ⑤：歷史不足只計加倍探測末輪仍晚到之欄；資料所致之晚到不計；平穩化衍生欄依基礎欄判定；
    未經探測（probe_late=None）時公開晚到全計。"""
    from momentum.FeatureEngineering.warmup_window import warmup_late_columns

    start = "2026-01-01T00:00:00+00:00"
    stable = {
        "a_1h_x": "2026-01-01T05:00:00+00:00",          # 探測晚到 ⇒ 計
        "b_1h_kurt": "2026-01-01T16:00:00+00:00",       # 資料所致 ⇒ 不計
        "c_1h_ok": "2025-12-31T00:00:00+00:00",         # 不晚
        "a_1h_x_fracdiff": "2026-01-02T00:00:00+00:00",  # 基礎欄探測晚到 ⇒ 計
        "c_1h_ok_diff1": "2026-01-01T03:00:00+00:00",   # 基礎欄不晚 ⇒ 晚到來自平穩化窗寬 ⇒ 計
        "b_1h_kurt_fracdiff": "2026-01-02T00:00:00+00:00",  # 基礎欄資料所致晚到 ⇒ 不計
        "d_1h_dead": None,
    }
    assert warmup_late_columns(stable, start, frozenset({"a_1h_x"})) == ["a_1h_x", "a_1h_x_fracdiff", "c_1h_ok_diff1"]
    assert warmup_late_columns(stable, start, None) == sorted(
        ["a_1h_x", "b_1h_kurt", "a_1h_x_fracdiff", "c_1h_ok_diff1", "b_1h_kurt_fracdiff"])
    assert warmup_late_columns(stable, None, frozenset({"a_1h_x"})) == []


def test_with_start_near_data_start_flags_slow_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑤：起始日取資料起點後 400 列 ⇒ 慢欄記 warmup_insufficient_history、partial、起始日至首個有效值為 NaN，快欄照常。

    （原 100 列：R6 縮尾完整窗遮罩使每欄穩定點至少 +251 列，100 列內無快欄可驗；400 列時 EMA_5 類約 271 列即穩定、
    EMA_233 類逾 1,000 列，快慢兩類皆在。）"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    index = h.kline_frame().index
    start = index[400].isoformat()
    root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=start)
    reasons = json.dumps(result.metadata.get("failure_reasons", []))
    assert h.EVENTS["warmup_insufficient"] in reasons
    assert result.metadata.get("quality_status") == "partial"
    starts = {c: pd.Timestamp(t) for c, t in result.metadata[CONTRACT["stable_start_receipt_key"]].items()}
    assert any(t > pd.Timestamp(start) for t in starts.values())
    assert any(t <= pd.Timestamp(start) for t in starts.values())
    receipt = result.metadata.get(CONTRACT["warmup_doubling"]["key"])
    assert receipt and set(CONTRACT["warmup_doubling"]["fields"]) <= set(receipt)


# ─────────────────────────────── ⑦ 死欄純函式與欄集合差異

def test_dead_filter_mask_invariant_real_12h() -> None:
    """Task 2.3 ⑦：真實 BTC 12h close 前 1,540 列設 NaN（r13 codex 反例）⇒ L3 門檻下不判死欄。"""
    close = _close("12h")[:1696].copy()
    close[:1540] = np.nan
    decision = sm.dead_column_decision(close, nan_rate_threshold=CONTRACT["dead_filter_thresholds"]["l3_nan_rate"],
                                       min_valid=CONTRACT["dead_filter_thresholds"]["l3_min_effective_n"])
    assert not decision.dead
    assert decision.nan_rate == 0.0 and decision.valid_count == 156


@pytest.mark.parametrize("valid, threshold, dead", [(29, 30, True), (30, 30, False), (99, 100, True), (100, 100, False)])
def test_dead_filter_threshold_boundaries(valid: int, threshold: int, dead: bool) -> None:
    """Task 2.3 ⑦：L3 30、L7 100 之 29／30、99／100 邊界（真實 close 取段）。"""
    values = _close("1h")[:valid].copy()
    assert sm.dead_column_decision(values, nan_rate_threshold=None, min_valid=threshold).dead is dead


def test_dead_filter_shared_by_l3_and_l7(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑦：L3 與 L7 皆呼叫同一死欄純函式（spy），門檻依呼叫端。"""
    seen: List[Any] = []
    original = sm.dead_column_decision

    def spy(values, *, nan_rate_threshold, min_valid):
        seen.append((nan_rate_threshold, min_valid))
        return original(values, nan_rate_threshold=nan_rate_threshold, min_valid=min_valid)

    monkeypatch.setattr(sm, "dead_column_decision", spy)
    h.prepare_stat_env(monkeypatch, tmp_path)
    payload = h.stat_payload(fracdiff=False, adf=False)
    # 共用 helper 之輕量設定關閉 L7 死欄剔除（fftfmeta_golden_helpers）；本測試驗 L7 呼叫端 ⇒ 開啟（生產預設即開）
    payload["nan_strategy"] = {**payload.get("nan_strategy", {}), "l7_dead_feature_drop": {"enabled": True}}
    h.run_stat(tmp_path, payload)
    thresholds = CONTRACT["dead_filter_thresholds"]
    assert (thresholds["l3_nan_rate"], thresholds["l3_min_effective_n"]) in seen
    assert (None, thresholds["l7_min_valid_samples_default"]) in seen


def test_column_set_delta_canonical_and_permutation_invariant() -> None:
    """Task 2.3 ⑦（v35）：同一 delta 之鍵序與列序置換後 sha256 不變；欄名含非 ASCII 與 `,:"` 亦然；不同 delta 不同 digest。"""
    before = ["close_trend_EMA_233", "ohlc_pattern_Consensus", "測試,欄:\"x\""]
    after = ["close_trend_EMA_233", "新欄"]
    reasons = {"ohlc_pattern_Consensus": "stable_samples_below_min", "測試,欄:\"x\"": "stable_samples_below_min",
               "新欄": "nan_rate_rule"}
    delta = sm.column_set_delta(before, after, reasons)
    permuted = {"reasons": dict(reversed(list(delta["reasons"].items()))), "removed": list(reversed(delta["removed"])),
                "added": list(delta["added"])}
    assert sm.delta_sha256(sm.column_set_delta(after, before[::-1], {k: v for k, v in reasons.items()})) != sm.delta_sha256(delta)
    assert sm.canonical_delta_bytes(delta) == json.dumps(delta, sort_keys=True, ensure_ascii=False,
                                                         separators=(",", ":")).encode("utf-8")
    assert sm.delta_sha256(sm.column_set_delta(before[::-1], after[::-1], reasons)) == sm.delta_sha256(delta)
    assert sorted(permuted["removed"]) == delta["removed"]
    empty = sm.column_set_delta(after, after, {})
    assert empty == CONTRACT["column_set_delta"]["empty"]
    joined = "\n".join(sorted(set(after), key=lambda s: s.encode("utf-8"))).encode("utf-8")
    assert sm.column_set_sha256(after[::-1]) == hashlib.sha256(joined).hexdigest()


def test_column_set_delta_unknown_reason_rejected() -> None:
    """Task 2.3 ⑦（v36）：原因值不在封閉集合 ⇒ DeltaReasonError；差異欄缺原因亦同。"""
    with pytest.raises(sm.DeltaReasonError):
        sm.column_set_delta(["a", "b"], ["a"], {"b": "constant_rule"})
    with pytest.raises(sm.DeltaReasonError):
        sm.column_set_delta(["a", "b"], ["a"], {})
    assert tuple(CONTRACT["column_set_delta"]["reasons"]) == sm.DELTA_REASONS


def _receipts_module():
    import importlib.util

    path = REPO / "handoffs" / "run_receipts" / "ffstat_probes" / "stable_start_receipts.py"
    spec = importlib.util.spec_from_file_location("ffstat_stable_start_receipts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_warmup_restored_evidence_frozen_from_prebase() -> None:
    """Task 2.3 ⑦（v49）：改前 L3 剔除紀錄凍結於 b4 動工前原始碼 5a148b8e；每筆欄位齊全；
    「開頭過長」判定：凍結檔全部紀錄（真實改前 run）皆判真；同一紀錄改為含 inf、開頭無 NaN、或低基數閘所剔而輸入非全 NaN ⇒ 判假。"""
    receipts = _receipts_module()
    frozen = json.loads(receipts.DEAD_DROPS_PATH.read_text(encoding="utf-8"))
    assert frozen["commit"].startswith("5a148b8e") and frozen["quality_status"] == "complete"
    records = frozen["l3_dead_drops"]
    assert records
    fields = {"rows", "leading_nan", "nan_rate", "valid", "has_inf", "constant"}
    assert all(fields <= set(r) for r in records.values())
    assert all(receipts.leading_caused(r) for r in records.values())
    sample = next(r for r in records.values() if not r.get("low_cardinality_skip") and r["leading_nan"] < r["rows"])
    assert not receipts.leading_caused({**sample, "has_inf": True})
    assert not receipts.leading_caused({**sample, "leading_nan": 0, "valid": sample["rows"]})
    assert not receipts.leading_caused({**sample, "low_cardinality_skip": True})


def test_warmup_restored_classification_causal() -> None:
    """Task 2.3 ⑦（v50，審查 r33 codex P1-01、composer P2-01）：`warmup_restored` 須因果配對——改前開頭過長被剔
    （凍結檔真實紀錄）＋改後公開輸出於改前開頭段內有有限值＋stable_start ≤ 起始日；開頭段內無有限值 ⇒ 無原因；
    未於起始日前穩定 ⇒ nan_rate_rule；含 inf 之改前剔除（非開頭所致）⇒ 無原因（mixed delta 負例）。
    新值以真實 BTC 1h close 之 721 列充當改後欄值（只取其有限性），開頭段 NaN 版本以同一真實序列遮前段。"""
    receipts = _receipts_module()
    frozen = json.loads(receipts.DEAD_DROPS_PATH.read_text(encoding="utf-8"))["l3_dead_drops"]
    rec = next(r for r in frozen.values() if not r.get("low_cardinality_skip") and 0 < r["leading_nan"] < r["rows"])
    real = _close("1h")[:int(rec["rows"])].copy()
    head_nan = real.copy()
    head_nan[:int(rec["leading_nan"])] = np.nan
    assert receipts.classify_added(rec, real, True) == "warmup_restored"
    assert receipts.classify_added(rec, head_nan, True) is None
    assert receipts.classify_added(rec, real, False) == "nan_rate_rule"
    assert receipts.classify_added({**rec, "has_inf": True}, real, True) is None
    assert receipts.classify_added(None, real, True) is None


def test_mutation_leading_caused_always_true_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v50 mutant：`leading_caused` 恆真（非開頭所致之改前剔除亦被接受）⇒ 因果配對測試必紅。"""
    import importlib.util

    path = REPO / "handoffs" / "run_receipts" / "ffstat_probes" / "stable_start_receipts.py"
    spec = importlib.util.spec_from_file_location("ffstat_stable_start_receipts_mut1", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.leading_caused = lambda rec: True
    monkeypatch.setattr(sys.modules[__name__], "_receipts_module", lambda: module)
    with pytest.raises(AssertionError):
        test_warmup_restored_classification_causal()


def test_mutation_restored_always_true_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v50 mutant：凡改前開頭過長者一律判 `warmup_restored`（不看開頭段填回與起始日）⇒ 因果配對測試必紅。"""
    import importlib.util

    path = REPO / "handoffs" / "run_receipts" / "ffstat_probes" / "stable_start_receipts.py"
    spec = importlib.util.spec_from_file_location("ffstat_stable_start_receipts_mut2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.classify_added
    module.classify_added = lambda rec, values, restored: (
        "warmup_restored" if original(rec, values, True) is not None or original(rec, values, restored) else None)
    monkeypatch.setattr(sys.modules[__name__], "_receipts_module", lambda: module)
    with pytest.raises(AssertionError):
        test_warmup_restored_classification_causal()


def test_column_set_approval_matches_delta() -> None:
    """Task 2.3 ⑦：核可紀錄之 delta sha256＝本次 delta sha256；delta 非空而無核可紀錄即紅。"""
    rr = REPO / "handoffs" / "run_receipts"
    deltas = sorted(rr.glob("*-ffstat-column-set-delta.json"))
    assert deltas, "缺欄集合差異收據"
    delta_doc = json.loads(deltas[-1].read_text(encoding="utf-8"))
    digest = sm.delta_sha256(delta_doc["delta"])
    assert digest == delta_doc["delta_sha256"]
    if delta_doc["delta"] != CONTRACT["column_set_delta"]["empty"]:
        approvals = sorted(rr.glob("*-ffstat-column-set-approval.json"))
        assert approvals, "delta 非空而無使用者核可紀錄"
        approval = json.loads(approvals[-1].read_text(encoding="utf-8"))
        assert set(CONTRACT["column_set_delta"]["approval_fields"]) <= set(approval)
        assert approval["delta_sha256"] == digest


# ─────────────────────────────── ⑧⑨⑩ 多週期、快取、開關

def test_multi_tf_mask_applied_before_alignment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑧：1h＋12h 無起始日 ⇒ 12h 欄於對齊後之首個有效值時間＝其 12h stable_start 可被 1h 取用之時間。

    metadata 之 `stable_start` 依 §C 為「公開輸出中該欄第一個有限值之時間」——多週期時即 1h 格線上之時間；
    12h 原生穩定點另以獨立之 12h 單週期生成（同設定、`training=[12h]`、`primary=12h`）取得，作為本測試之 oracle。"""
    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import scale_window_for_native

    h.prepare_stat_env(monkeypatch, tmp_path)
    root, factory, result = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"], fracdiff=False, adf=False), start_date=None)
    # 多週期時 12h 欄之 L6.5 於原生週期子實例進行，縮尾窗由主週期根數換算為原生根數（252 根 1h ⇒ 21 根 12h）；
    # 單週期 oracle 須用同一換算後之窗，方為同一計算
    window_1h = int(factory._resolve_config(h.stat_payload(["1h", "12h"])).preprocessing.winsorization.window)
    native_payload = h.stat_payload(["12h"], fracdiff=False, adf=False)
    native_payload["preprocessing"]["winsorization"] = {
        **native_payload["preprocessing"]["winsorization"], "window": scale_window_for_native(window_1h, "12h", "1h")}
    native_payload["timeframes"] = {**native_payload["timeframes"], "primary": "12h"}
    _root_n, _factory_n, native = h.run_stat(tmp_path / "native12h", native_payload, start_date=None, primary_tf="12h")
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    stable = result.metadata[CONTRACT["stable_start_receipt_key"]]
    native_stable = native.metadata[CONTRACT["stable_start_receipt_key"]]
    twelve = [c for c in stable if "_12h_" in c]
    assert twelve
    assert set(twelve) <= set(native_stable), sorted(set(twelve) - set(native_stable))[:5]
    idx_12h = h.kline_frame(timeframe="12h").index
    idx_1h = h.kline_frame(timeframe="1h").index
    # 12h K 棒序號經同一對齊器對到 1h 一次（原逐欄對齊數千次：每次新建物件並記一行 log，pytest 保留全部擷取之 log
    # 於記憶體，8GB 機器上三度被系統砍掉）。對齊為「每個 1h 列取其時可用之最近 12h K 棒」⇒ 對齊後序號單調不減；
    # 某欄 12h 原生穩定於第 p 根 ⇒ 1h 首個有值時間＝對齊後序號首次 ≥ p 之 1h 時間（與原逐欄標記法同義）。
    ordinal = pd.DataFrame({"m": np.arange(len(idx_12h), dtype=np.float64)}, index=idx_12h)
    ordinal.index.name = "timestamp"
    aligned = TimeframeAligner.align_to_primary(ordinal.reset_index(), "12h", pd.Series(idx_1h), "1h")["m"]
    aligned_times = pd.DatetimeIndex([_utc(t) for t in aligned.index])
    aligned_ordinal = aligned.to_numpy(dtype=np.float64)
    native_times = pd.DatetimeIndex([_utc(t) for t in idx_12h])
    checked = 0
    for column in twelve:
        series = _public_column(root, column)
        if native_stable[column] is None:
            # 原生週期於全史內無穩定值（如 12h T3_233：穩定點超出約 1,700 根）⇒ 對齊後亦須全 NaN
            assert stable[column] is None and series.isna().all(), column
            continue
        checked += 1
        # 預期：12h 於其原生 stable_start 首個有效之列，經同一對齊器對到 1h 後之第一個有值時間（r24 codex P1-03：精確相等）
        p = int(native_times.searchsorted(_utc(native_stable[column]), side="left"))
        reached = np.flatnonzero(np.nan_to_num(aligned_ordinal, nan=-1.0) >= p)
        assert reached.size, column
        expected = aligned_times[int(reached[0])]
        assert _utc(series.first_valid_index()) == expected, column
        assert series.loc[:expected - pd.Timedelta(microseconds=1)].isna().all(), column
    assert checked, len(twelve)


def test_config_hash_includes_warmup_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑨：設定 hash 納入 warmup_policy ⇒ 改動政策字串即改變 hash（改前快取未命中）。"""
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(h.stat_payload())
    base = factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=None, end_date=None)
    monkeypatch.setattr(sm, "WARMUP_POLICY", "per_column_stable_v0")
    assert factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=None, end_date=None) != base


def test_warmup_trim_switch_removed() -> None:
    """Task 2.3 ⑩：`FFACT_WARMUP_TRIM` 與 `is_warmup_trim_enabled` 於生產碼 0 命中。"""
    hits = []
    for root in ("momentum", "api"):
        for path in (REPO / root).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "FFACT_WARMUP_TRIM" in text or "is_warmup_trim_enabled" in text:
                hits.append(str(path.relative_to(REPO)))
    assert not hits, hits


# ─────────────────────────────── 12h 逐輸出點、每個 L1 輸出皆經契約

def test_every_l1_output_column_passes_output_point_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ①（v38）：以真實 BTC 12h 跑預設全設定之 L1 ⇒ 每個 L1 輸出欄皆有一次 instance_k 呼叫（未驗即紅）。"""
    seen: List[str] = []
    original = sm.instance_k

    def spy(spec, table, upstream_k=None):
        seen.append(spec.column)
        return original(spec, table, upstream_k)

    monkeypatch.setattr(sm, "instance_k", spy)
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.factories import create_feature_factory

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    config = ConfigManager().get_merged_config()
    raw = factory._layer0_data_ingestion(h.SYMBOL, "12h", config)
    layer1 = factory._layer1_atomic_indicators(raw, config).data
    missing = sorted(set(layer1.columns) - set(seen))
    assert not missing, missing[:20]
    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-12h-output-points.json"))
    assert receipts, "缺 12h 逐輸出點收據（列已驗與未驗之輸出點）"
    doc = json.loads(receipts[-1].read_text(encoding="utf-8"))
    assert not doc["unverified"], doc["unverified"][:20]


# ─────────────────────────────── 邊界（Task 2.3 邊界①–④，接續既有編號 22–25）

def test_boundary_22_sparse_column_calibrates_on_first_n_valid() -> None:
    """Task 2.3 邊界①：稀疏欄之校準取遮罩後最早 N 個有效值（間歇 NaN 跳過）。"""
    values = _close("1h")[:3000].copy()
    values[::3] = np.nan
    rows = sm.calibration_rows_no_start(values, 500)
    finite_positions = np.flatnonzero(np.isfinite(values))
    assert rows == (int(finite_positions[0]), int(finite_positions[499]))


def test_boundary_23_cumulative_listed_start_dependent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 邊界②：累積型欄（OBV、AD）列入 start_dependent_columns。"""
    payload = h.stat_payload(fracdiff=False, adf=False)
    payload["atomic_indicators"]["volume"] = {"enabled": True, "indicators": [{"name": "OBV", "enabled": True}]}
    h.prepare_stat_env(monkeypatch, tmp_path)
    _root, _factory, result = h.run_stat(tmp_path, payload)
    listed = result.metadata[CONTRACT["start_dependent_key"]]
    assert any("OBV" in c for c in listed)


def test_boundary_24_reference_symbol_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 邊界③：參考標的起點晚於主標的 ⇒ cs 欄之 stable_start 不早於參考標的之首列。"""
    klines = h.kline_copy(tmp_path)
    ref_start = h.kline_frame(symbol="ETHUSDT").index[0] + pd.Timedelta(days=60)
    h.drop_kline_rows_before(klines, ref_start.isoformat(), symbol="ETHUSDT")
    h.prepare_stat_env(monkeypatch, tmp_path)
    _root, _factory, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False, cross_sectional=True),
                                         start_date=None, kline_dir=str(klines))
    for column, ts in result.metadata[CONTRACT["stable_start_receipt_key"]].items():
        if column.startswith("cs_"):
            assert _utc(ts) >= _utc(ref_start), column


# Task 2.3 邊界④（帶 start_date ⇒ output_start_source == "user"、effective_output_start＝該日）之唯一具名測試為既有
# test_ffstat_calibration.py::test_boundary_11_user_start_source_is_user（r24 codex P2-05：不另建重複落點）；
# per_column 不寫 effective_output_start 由 test_no_start_calibration_rows_masked_from_output 斷言。


# ─────────────────────────────── ⑪ 四條執行路徑

_PATHS = {
    "cgsa_serial": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"},
    "cgsa_parallel": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "1"},
    # 大記憶體機器之記憶體級距（共用 FIXED_ENV 固定 L3 為 streaming ⇒ 改回 auto 由級距決定：24gb＝hybrid、
    # 32gb＝in_memory，並連帶該級距之 L6.5／L7 worker 數與分割門檻）
    "tier_24gb": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0", "FFACT_MEMORY_TIER": "24gb",
                  "FFACT_L3_PERSIST_MODE": "auto"},
    "tier_32gb": {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0", "FFACT_MEMORY_TIER": "32gb",
                  "FFACT_L3_PERSIST_MODE": "auto"},
}


_EXPECTED_L3_MODE = {"cgsa_serial": "streaming", "resume": "streaming", "tier_24gb": "hybrid", "tier_32gb": "in_memory"}


def _path_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> Dict[str, Any]:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
    from momentum.FeatureEngineering.utils import hardware_utils

    env = _PATHS["cgsa_serial" if mode == "resume" else mode]
    h.prepare_stat_env(monkeypatch, tmp_path, **env)
    # 審查 r33 codex P1-02：只比結果同值不足以證明級距路徑被執行 ⇒ 記錄 L3 persist mode 之解析值與 L3 實際分支
    # （有 persist_callback＝邊算邊寫之 streaming／hybrid；無＝in_memory）。平行路徑之 worker 為子程序，主程序看不到。
    observed: Dict[str, List[Any]] = {"modes": [], "callbacks": []}
    real_mode, real_compute = hardware_utils.get_l3_persist_mode, RollingAggregator.compute_all

    def spy_mode() -> str:
        value = real_mode()
        observed["modes"].append(value)
        return value

    def spy_compute(self, features_df, persist_callback=None):
        observed["callbacks"].append(persist_callback is not None)
        return real_compute(self, features_df, persist_callback=persist_callback)

    monkeypatch.setattr(hardware_utils, "get_l3_persist_mode", spy_mode)
    monkeypatch.setattr(RollingAggregator, "compute_all", spy_compute)
    # 多週期取 1h＋4h：CGSA 續跑只接 complete 之前次 run（consumer_gate.is_run_status_cacheable），而真實 12h 資料
    # （約 1,700 根）下 KAMA_233 等慢欄之穩定點晚至 2025-12，N＝500 缺 133 欄、N＝100 仍缺 20 欄 ⇒ partial、resume
    # 永不觸發（主委實跑 2026-09-28）；4h 約 5,088 根，預設 N 下全部欄湊滿
    payload = h.stat_payload(["1h", "4h"])
    root, _factory, result = h.run_stat(tmp_path, payload, start_date=None)
    if mode == "resume":
        # r25 codex P1-01：第二次須真走 CGSA 續跑——令快取探測落空，並斷言 resume_from_manifest 被呼叫
        resumed: List[Any] = []
        real_resume = ColumnGroupRegistry.resume_from_manifest  # classmethod（已綁定）

        def spy_resume(cls, work_dir):
            resumed.append(1)
            return real_resume(work_dir)

        monkeypatch.setattr(FeatureFactory, "_try_load_cache", lambda self, *a, **k: None)
        monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(spy_resume))
        root, _factory, result = h.run_stat(tmp_path, payload, start_date=None, force_regenerate=False)
        assert resumed, "resume 路徑未呼叫 ColumnGroupRegistry.resume_from_manifest"
    if mode in _EXPECTED_L3_MODE:
        expected = _EXPECTED_L3_MODE[mode]
        assert observed["modes"] and set(observed["modes"]) == {expected}, (mode, observed["modes"])
        assert observed["callbacks"] and set(observed["callbacks"]) == {expected != "in_memory"}, (mode, observed)
    return {"root": root, "result": result, "observed": observed}


def _strip_cache_hit(decisions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {c: {k: v for k, v in r.items() if k != "dstar_cache_hit"} for c, r in decisions.items()}


@pytest.mark.parametrize("mode", ["cgsa_parallel", "resume", "tier_24gb", "tier_32gb"])
def test_paths_same_stable_start_and_masks(mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑪（v49 改寫；r24 codex P1-02）：生產路徑 CGSA 序列、CGSA 平行、resume、24gb（L3 hybrid）與 32gb（L3 in_memory）級距之 stable_start、決策與
    公開輸出全部欄（基礎欄 parquet＋_L65 衍生欄）之 NaN mask 與 float32 值全同，且皆 complete。"""
    key = CONTRACT["stable_start_receipt_key"]
    base = _path_run(tmp_path / "cgsa_serial", monkeypatch, "cgsa_serial")
    other = _path_run(tmp_path / mode, monkeypatch, mode)
    for run in (base, other):
        assert run["result"].metadata.get("quality_status") == "complete", run["result"].metadata.get("failure_reasons")
    assert other["result"].metadata[key] == base["result"].metadata[key]
    assert _strip_cache_hit(h.decisions(other["result"])) == _strip_cache_hit(h.decisions(base["result"]))
    base_fp, other_fp = h.public_fingerprints(base["root"]), h.public_fingerprints(other["root"])
    assert base_fp and set(other_fp) == set(base_fp), sorted(set(other_fp) ^ set(base_fp))[:10]
    assert [c for c in base_fp if base_fp[c] != other_fp[c]] == []


# ─────────────────────────────── ⑫ run_ic_first（v29–v31）

def _ic_first_kwargs(tmp_path: Path) -> Dict[str, Any]:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    root = tmp_path / "ic_first"
    # run_ic_first 須注入 IC 引擎（同 ffstat_helpers 之 IC-first 呼叫）；IC 階段既有之對齊例外由 ic_first_to_l65 處理
    return {"storage": FeatureStorage(str(root)), "persist": True, "ic_engine": ICEngine({"methods": ["spearman"]}),
            "feature_reader": FeatureReader(str(root)), "ic_threshold": 0.0}


def _factory_and_config():
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    return factory, factory._resolve_config(h.stat_payload())


def test_run_ic_first_requires_start_date_when_stationarizing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：平穩化開啟而 start_date 為 None ⇒ CalibrationError（field＝output_start）、零寫入。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    kwargs = _ic_first_kwargs(tmp_path)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError) as exc:
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, config, start_date=None, end_date=h.WINDOW[1], **kwargs)
    assert getattr(exc.value, "field", None) == "output_start"
    assert h.snapshot_tree(tmp_path) == before


def test_run_ic_first_rejects_config_hash_when_stationarizing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：平穩化開啟而傳入 config_hash ⇒ CalibrationError（field＝config_hash）、零寫入。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    kwargs = _ic_first_kwargs(tmp_path)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError) as exc:
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, config, start_date=h.WINDOW[0], end_date=h.WINDOW[1],
                             config_hash="deadbeef", **kwargs)
    assert getattr(exc.value, "field", None) == "config_hash"
    assert h.snapshot_tree(tmp_path) == before


def test_run_ic_first_uses_own_window_not_previous(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v29）：同一 factory 先生成 A 窗再生成 B 窗，run_ic_first 帶 A 之起訖 ⇒ 校準上界 < A 起始日、
    lease hash＝以 A 起訖重算之設定 hash；預設不相干之 _current_output_window／_current_config_hash 亦同。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    a_start, a_end = h.WINDOW
    b_start = (pd.Timestamp(a_end) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    b_end = (pd.Timestamp(a_end) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    factory._storage = FeatureStorage(str(tmp_path / "gen"))
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=a_start, end_date=a_end)
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=b_start, end_date=b_end)
    expected_hash = factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY_TF, start_date=a_start, end_date=a_end)
    for preset in (False, True):
        if preset:
            factory._current_output_window = object()
            factory._current_config_hash = "unrelated"
        leases: List[Any] = []
        try:
            h.ic_first_to_l65(factory, config, start_date=a_start, end_date=a_end, lease_sink=leases,
                              **_ic_first_kwargs(tmp_path / str(preset)))
            decisions = getattr(factory, CONTRACT["factory_decisions_attr"])
            assert all(pd.Timestamp(d["calibration_end"]) < pd.Timestamp(a_start, tz="UTC")
                       for d in decisions.values() if d.get("calibration_end")), preset
            # r25 codex P1-02：RunLease 無 __str__，以 lease.path 之檔名比對設定 hash
            assert leases and any(expected_hash in lease.path.name for lease in leases), preset
        finally:
            for lease in leases:  # r25 codex P1-03：釋放 exclusive lease，避免下一迭代 RunBusyError
                lease.release()


@pytest.mark.parametrize("ending", ["preflight_error", "l1_l6_error", "success"])
def test_run_ic_first_restores_state_on_all_endings(ending: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 ⑫（v30）：平穩化開啟之 run_ic_first 結束後（前置關卡失敗、L1–L6 失敗、成功）
    `_current_output_window` 與 `_current_config_hash` 皆與呼叫前為同一物件（is）。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory, config = _factory_and_config()
    factory._storage = FeatureStorage(str(tmp_path / "gen"))
    factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload(), start_date=h.WINDOW[0], end_date=h.WINDOW[1])
    window_before, hash_before = factory._current_output_window, factory._current_config_hash
    w1_start = (pd.Timestamp(h.WINDOW[1]) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    w1_end = (pd.Timestamp(h.WINDOW[1]) + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
    if ending == "preflight_error":
        monkeypatch.setattr(FeatureFactory, "run_calibration_preflight",
                            lambda *a, **k: (_ for _ in ()).throw(CalibrationError("injected")))
    elif ending == "l1_l6_error":
        monkeypatch.setattr(FeatureFactory, "_run_l1_l6_for_ic_first",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    try:
        h.ic_first_to_l65(factory, config, start_date=w1_start, end_date=w1_end, **_ic_first_kwargs(tmp_path))
    except (CalibrationError, RuntimeError):
        assert ending != "success"
    assert factory._current_output_window is window_before
    assert factory._current_config_hash is hash_before


def test_retired_tests_absent_and_replaced() -> None:
    """§V 防假綠：退役表中之舊測試已不在原檔，且其接替測試存在。"""
    table = json.loads((REPO / CONTRACT["retired_tests_path"]).read_text(encoding="utf-8"))
    for row in table["retired"]:
        old_file, old_name = row["test"].split("::")
        new_file, new_name = row["replacement"].split("::")
        assert f"def {old_name}(" not in (REPO / old_file).read_text(encoding="utf-8"), row["test"]
        assert f"def {new_name}(" in (REPO / new_file).read_text(encoding="utf-8"), row["replacement"]
        assert row["reason"], row["test"]


# ─────────────────────────────── §V mutants（v32–v42）

def test_mutation_l1_mask_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁴：刪 L1 遮罩（apply_l1_mask 原樣回傳）⇒ ① 必紅。"""
    monkeypatch.setattr(sm, "apply_l1_mask", lambda values, origin, k: np.asarray(values, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_l1_mask_first_valid_is_origin_plus_k("1h")


def test_mutation_k_by_params_ignored_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v46：instance_k 忽略 k_by_params（一律比例公式）⇒ 實測根數優先測試必紅。"""
    stripped = {name: {k: v for k, v in entry.items() if k != "k_by_params"} for name, entry in _table().items()}
    original = sm.instance_k
    monkeypatch.setattr(sm, "instance_k", lambda spec, table, upstream_k=None: original(spec, stripped, upstream_k))
    with pytest.raises(AssertionError):
        test_l1_mask_k_by_params_preferred_over_factor()


def test_mutation_whole_indicator_max_period_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v37：K 改取整個指標之最大週期（EMA_5 亦 336）⇒ 逐呼叫測試必紅。"""
    monkeypatch.setattr(sm, "instance_k", lambda spec, table, upstream_k=None: math.ceil(233 * _factor(spec.indicator)))
    with pytest.raises(AssertionError):
        test_l1_mask_per_call_k_ema5_vs_ema233()


def test_mutation_winsor_unmasked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁵：縮尾輸出不遮 ⇒ ② 必紅。"""
    monkeypatch.setattr(sm, "mask_incomplete_window", lambda output, input_values, window: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_incomplete_window_mask_winsor_full_window()


def test_mutation_pointwise_prefix_unmasked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦²⁰：第④類不遮 ⇒ ② 必紅。"""
    monkeypatch.setattr(sm, "mask_pointwise_prefix", lambda output, inputs: np.asarray(output, dtype=float).copy())
    with pytest.raises(AssertionError):
        test_pointwise_prefix_mask_binary_signal()


def test_mutation_calibration_rows_not_masked_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹¹（v32）：校準列取法錯位（取最末 N 個）⇒ 邊界① 必紅。"""
    monkeypatch.setattr(sm, "calibration_rows_no_start",
                        lambda values, n: (int(np.flatnonzero(np.isfinite(values))[-n]), int(np.flatnonzero(np.isfinite(values))[-1])))
    with pytest.raises(AssertionError):
        test_boundary_22_sparse_column_calibrates_on_first_n_valid()


def test_mutation_dead_filter_full_denominator_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁸／⑦²²：死欄 NaN 率分母改回全列 ⇒ ⑦ 反例必紅。"""
    def full_denominator(values, *, nan_rate_threshold, min_valid):
        arr = np.asarray(values, dtype=float)
        rate = float(np.isnan(arr).mean())
        valid = int(np.isfinite(arr).sum())
        dead = (nan_rate_threshold is not None and rate > nan_rate_threshold) or valid < min_valid
        return sm.DeadDecision(dead=dead, reason=None, nan_rate=rate, valid_count=valid)

    monkeypatch.setattr(sm, "dead_column_decision", full_denominator)
    with pytest.raises(AssertionError):
        test_dead_filter_mask_invariant_real_12h()


def test_mutation_delta_non_canonical_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v35：delta 序列化不排序鍵 ⇒ 置換不變測試必紅。"""
    monkeypatch.setattr(sm, "canonical_delta_bytes", lambda delta: json.dumps(delta, ensure_ascii=False).encode("utf-8"))
    with pytest.raises(AssertionError):
        test_column_set_delta_canonical_and_permutation_invariant()


def test_mutation_unknown_reason_accepted_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """v36：接受第三種原因值 ⇒ 必紅。"""
    monkeypatch.setattr(sm, "DELTA_REASONS", (*sm.DELTA_REASONS, "constant_rule"))
    # 內層以 pytest.raises 斷言；mutant 下「未拋」為 pytest 之 Failed（非 AssertionError 子類），兩者皆算抓到
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        test_column_set_delta_unknown_reason_rejected()


def test_mutation_config_hash_without_policy_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹²（v32）：設定 hash 不含 warmup_policy ⇒ ⑨ 必紅。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    original = FeatureFactory._compute_config_hash

    def hash_ignoring_policy(self, *a, **k):
        saved = sm.WARMUP_POLICY
        try:
            sm.WARMUP_POLICY = "fixed"
            return original(self, *a, **k)
        finally:
            sm.WARMUP_POLICY = saved

    monkeypatch.setattr(FeatureFactory, "_compute_config_hash", hash_ignoring_policy)
    with pytest.raises(AssertionError):
        test_config_hash_includes_warmup_policy(monkeypatch)
