"""FF-NAME Task 2.1／2.2 — atomic 引擎之身分建構（docs/FFNAME_SPEC.md Task 2.1、2.2）。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）尾段切片；禁合成 fixture。
Task 2.1 邊界：①`close_volume`→`close-volume` ②多輸出 ③pattern CDL。
Task 2.2 邊界：④vpin 輸出點契約參數 `n_buckets` 與 metadata 一致 ⑤無參數指標。
Task 2.1 驗證：metadata 之 source／indicator 為 canonical、`raw_lookup_key` 為原始鍵。
Task 2.2 驗證：每指標 compute、輸出點、metadata 三處欄名 == 同一身分 format；microstructure 以「含 `quote_volume`／
`taker_ratio`」與「不含」兩份真實資料各生成，同一指標之欄名不同且 source == 輸出點輸入元組之 canonical 串接；
custom 同 slug 兩定義 ⇒ 拒收。§G ②④ 由 Task 2.6 驗。
v13：引擎輸出為未標記形，以 `parse_feature_name(name, tagged=False)` 解析；microstructure、entropy、tail-risk 之 source
一律＝輸出點輸入元組之 canonical 串接（`("close",)` ⇒ `close`）；custom slug 於設定驗證時拒收（呼叫使用者函式前）。
"""

from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
from momentum.FeatureEngineering.atomic.volume_indicators import VolumeIndicatorEngine
from momentum.FeatureEngineering.feature_config import CategoryConfig, EntropyConfig, MicrostructureConfig, TailRiskConfig
from tests.feature_engineering.ffname_helpers import params_str, parse_untagged, patch_everywhere, real_slice, untagged_roundtrip_ok
from tests.feature_engineering.ffstat_helpers import PRIMARY_TF

TF = PRIMARY_TF
_OPTIONAL_KEYS = ("quote_volume", "taker_ratio")


@pytest.fixture(scope="module")
def kline() -> pd.DataFrame:
    return real_slice(800)


@pytest.fixture(scope="module")
def kline_without_optional(kline) -> pd.DataFrame:
    """同一份真實資料去掉 `quote_volume`／`taker_ratio`（走 microstructure 退回分支）。"""
    return kline.drop(columns=[c for c in _OPTIONAL_KEYS if c in kline.columns])


def _all_parse(columns: Iterable[str]) -> List[str]:
    """引擎輸出為生成期間之未標記形（SPEC v13）：`parse(tagged=False)` 成功且標記後之完整形往返。"""
    return [str(c) for c in columns if not untagged_roundtrip_ok(str(c), TF)]


def _canonical_join(keys: Iterable[str]) -> str:
    return "-".join(fn.canonical_segment(k) for k in keys)


def _talib_engine(cls, sources: List[str]):
    return cls(CategoryConfig().model_dump(), sources)


# ---------------------------------------------------------------- Task 2.1 邊界

def test_boundary_01_close_volume_source_is_canonical(kline):
    engine = _talib_engine(VolumeIndicatorEngine, ["close"])
    out = engine.compute_all(kline)
    meta = engine.get_feature_metadata()
    obv = [c for c in out.columns if parse_untagged(c).indicator == "OBV"]
    assert obv, "OBV 欄不存在"
    for c in obv:
        ident = parse_untagged(c)
        assert ident.source == "close-volume"
        assert meta[c]["source"] == "close-volume"


def test_boundary_02_multi_output_indicator(kline):
    engine = _talib_engine(TrendIndicatorEngine, ["close"])
    out = engine.compute_all(kline)
    meta = engine.get_feature_metadata()
    bbands = [c for c in out.columns if str(meta.get(c, {}).get("indicator", "")).startswith("BBANDS-")]
    assert {meta[c]["indicator"] for c in bbands} == {"BBANDS-Upper", "BBANDS-Middle", "BBANDS-Lower"}
    for c in bbands:
        assert parse_untagged(c).indicator == meta[c]["indicator"]


def test_boundary_03_pattern_cdl(kline):
    engine = _talib_engine(PatternIndicatorEngine, ["close"])
    out = engine.compute_all(kline)
    meta = engine.get_feature_metadata()
    cdl = [c for c in out.columns if "CDL" in c]
    assert cdl
    assert _all_parse(out.columns) == []
    for c in cdl:
        ident = parse_untagged(c)
        assert ident.category == "pattern" and ident.indicator.startswith("CDL")
        assert c in meta and meta[c]["indicator"] == ident.indicator


# ---------------------------------------------------------------- Task 2.1 驗證

@pytest.mark.parametrize("engine_cls", [TrendIndicatorEngine, VolatilityIndicatorEngine, VolumeIndicatorEngine])
def test_talib_metadata_canonical_and_raw_lookup_key(kline, engine_cls):
    sources = ["close", "taker_ratio"]
    engine = _talib_engine(engine_cls, sources)
    out = engine.compute_all(kline)
    meta = engine.get_feature_metadata()
    assert _all_parse(out.columns) == []
    missing = [c for c in out.columns if c not in meta]
    assert missing == []
    for c in out.columns:
        entry = meta[c]
        ident = parse_untagged(c)
        assert "_" not in str(entry["source"]) and "_" not in str(entry["indicator"])
        assert entry["source"] == ident.source and entry["indicator"] == ident.indicator
        if ident.source == "taker-ratio":
            assert entry["raw_lookup_key"] == "taker_ratio"
        if ident.source == "close":
            assert entry["raw_lookup_key"] == "close"


# ---------------------------------------------------------------- Task 2.2 邊界

def test_boundary_04_vpin_n_buckets_consistent(kline):
    engine = MicrostructureIndicatorEngine(MicrostructureConfig().model_dump(), ["close"])
    points = engine._output_points(kline)
    meta = engine.get_feature_metadata()
    vpin = [c for c in points if parse_untagged(c).indicator == "vpin"]
    assert vpin
    for c in vpin:
        n = points[c]["params"]["n_buckets"]
        assert meta[c]["params"]["n_buckets"] == n
        assert params_str(parse_untagged(c)) == str(n)


def test_boundary_05_no_param_indicator(kline):
    engine = MicrostructureIndicatorEngine(MicrostructureConfig().model_dump(), ["close"])
    out = engine.compute_all(kline)
    ofi_raw = [c for c in out.columns if parse_untagged(c).indicator == "ofi-raw"]
    assert len(ofi_raw) == 1
    ident = parse_untagged(ofi_raw[0])
    assert params_str(ident) == ""
    assert fn.format_feature_name(ident) == fn.tag_timeframe(ofi_raw[0], TF)


# ---------------------------------------------------------------- Task 2.2 驗證

def _points(engine, data) -> Dict[str, Dict]:
    try:
        return engine._output_points(data)
    except TypeError:
        return engine._output_points()


def _three_places(engine, data) -> Dict[str, set]:
    out = engine.compute_all(data)
    return {"compute": set(map(str, out.columns)), "points": set(_points(engine, data)),
            "meta": set(engine.get_feature_metadata())}


_ADVANCED = [
    lambda: MicrostructureIndicatorEngine(MicrostructureConfig().model_dump(), ["close"]),
    lambda: EntropyIndicatorEngine(EntropyConfig().model_dump(), ["close"]),
    lambda: TailRiskIndicatorEngine(TailRiskConfig().model_dump(), ["close"]),
]
_ADVANCED_IDS = ["microstructure", "entropy", "tail_risk"]


@pytest.mark.parametrize("engine_factory", _ADVANCED, ids=_ADVANCED_IDS)
def test_compute_points_metadata_same_names(kline, engine_factory):
    places = _three_places(engine_factory(), kline)
    assert places["compute"] == places["points"] == places["meta"]
    assert _all_parse(places["compute"]) == []


@pytest.mark.parametrize("engine_factory", _ADVANCED, ids=_ADVANCED_IDS)
def test_source_equals_canonical_input_tuple(kline, engine_factory):
    """v13：source 一律＝輸出點輸入元組之 canonical 串接（tail-risk、entropy 之 `("close",)` ⇒ `close`）。"""
    engine = engine_factory()
    out = engine.compute_all(kline)
    points = _points(engine, kline)
    bad = [c for c in out.columns if parse_untagged(c).source != _canonical_join(points[c]["inputs"])]
    assert bad == []


def test_tail_risk_and_entropy_close_input_source_is_close(kline):
    for engine in (TailRiskIndicatorEngine(TailRiskConfig().model_dump(), ["close"]),
                   EntropyIndicatorEngine(EntropyConfig().model_dump(), ["close"])):
        points = _points(engine, kline)
        close_only = [c for c in engine.compute_all(kline).columns if tuple(points[c]["inputs"]) == ("close",)]
        assert close_only
        assert {parse_untagged(c).source for c in close_only} == {"close"}
    assert {parse_untagged(c).category for c in TailRiskIndicatorEngine(TailRiskConfig().model_dump(), ["close"]).compute_all(kline).columns} == {"tail-risk"}


def _microstructure_branch_sources(data: pd.DataFrame) -> Dict[str, str]:
    engine = MicrostructureIndicatorEngine(MicrostructureConfig().model_dump(), ["close"])
    out = engine.compute_all(data)
    points = engine._output_points(data)
    result = {}
    for c in out.columns:
        ident = parse_untagged(c)
        assert ident.source == _canonical_join(points[c]["inputs"]), c
        result[f"{ident.indicator}|{params_str(ident)}"] = c
    return result


def _dual_branch_names_distinct(full: pd.DataFrame, reduced: pd.DataFrame) -> bool:
    try:
        main = _microstructure_branch_sources(full)
        fallback = _microstructure_branch_sources(reduced)
    except Exception:  # noqa: BLE001 — mutant 使契約不成立亦視為失敗
        return False
    amihud = [k for k in main if k.startswith("amihud-illiq|")]
    ofi = [k for k in main if k.startswith("ofi-raw|")]
    if not amihud or not ofi:
        return False
    return all(main[k] != fallback[k] for k in amihud + ofi)


def test_microstructure_branch_changes_name(kline, kline_without_optional):
    assert {"quote_volume", "taker_ratio"} <= set(kline.columns)
    main = _microstructure_branch_sources(kline)
    fallback = _microstructure_branch_sources(kline_without_optional)
    amihud_key = next(k for k in main if k.startswith("amihud-illiq|"))
    assert parse_untagged(main[amihud_key]).source == "close-quote-volume"
    assert parse_untagged(fallback[amihud_key]).source == "close-volume"
    ofi_key = next(k for k in main if k.startswith("ofi-raw|"))
    assert parse_untagged(main[ofi_key]).source == "taker-ratio"
    assert parse_untagged(fallback[ofi_key]).source == "taker-buy-volume-volume"
    assert _dual_branch_names_distinct(kline, kline_without_optional)


def custom_close_copy(data: pd.DataFrame, out: str = "x", **params) -> pd.DataFrame:
    """custom 定義之被呼叫函式（本測試模組內；slug 拒收須先於呼叫）；回傳宣告之輸出欄，避免夾帶其他錯誤。"""
    custom_close_copy.calls += 1
    return pd.DataFrame({out: data["close"]}, index=data.index)


custom_close_copy.calls = 0


def _custom_def(name: str) -> Dict:
    return {"name": name, "module": __name__, "function": "custom_close_copy", "params": {"out": name},
            "outputs": {name: {"params": {}, "period_keys": []}}}


def _custom_rejected(defs: List[Dict], data: pd.DataFrame, slug: str) -> bool:
    """v13：custom slug 於設定驗證（feature_config）時拒收——設定解析即拋 ValueError（含 slug），不待引擎計算。"""
    from momentum.factories import create_feature_factory

    try:
        create_feature_factory()._resolve_config({"custom_indicators": defs})
    except ValueError as exc:
        return slug in str(exc)
    return False


def test_custom_valid_single_slug_passes_config_validation(kline):
    """正向對照：合法且唯一之 slug 通過設定驗證（拒收確由 slug 規則觸發，非其他欄位錯誤）。"""
    from momentum.factories import create_feature_factory

    custom_close_copy.calls = 0
    config = create_feature_factory()._resolve_config({"custom_indicators": [_custom_def("ffname-probe")]})
    assert [d.name for d in config.custom_indicators] == ["ffname-probe"]
    assert custom_close_copy.calls == 0


def test_custom_same_slug_two_definitions_rejected(kline):
    custom_close_copy.calls = 0
    assert _custom_rejected([_custom_def("ffname-probe"), _custom_def("ffname-probe")], kline, "ffname-probe")
    assert custom_close_copy.calls == 0


def test_custom_invalid_slug_rejected(kline):
    custom_close_copy.calls = 0
    assert _custom_rejected([_custom_def("Bad_Slug")], kline, "Bad_Slug")
    assert custom_close_copy.calls == 0


# ---------------------------------------------------------------- mutation

def test_mutation_generator_bypassing_formatter_is_caught(kline, monkeypatch):
    """§V mutation ①：某產生端繞過 formatter（以底線串段）⇒ 欄名不可解析。"""
    original = fn.format_feature_name
    replaced = patch_everywhere(monkeypatch, original, lambda ident: original(ident).replace("-", "_"))
    assert replaced >= 1
    engine = MicrostructureIndicatorEngine(MicrostructureConfig().model_dump(), ["close"])
    assert _all_parse(engine.compute_all(kline).columns) != []


def test_mutation_microstructure_fallback_reuses_main_source_is_caught(kline, kline_without_optional, monkeypatch):
    """§V mutation ⑬：退回分支沿用主分支 source（輸出點恆以主分支輸入）⇒ 雙資料測試必紅。"""
    original = MicrostructureIndicatorEngine._output_points

    def main_branch_points(self, data):
        filled = data.copy()
        for key in _OPTIONAL_KEYS:
            if key not in filled.columns:
                filled[key] = data["close"]
        return original(self, filled)

    monkeypatch.setattr(MicrostructureIndicatorEngine, "_output_points", main_branch_points)
    assert _dual_branch_names_distinct(kline, kline_without_optional) is False
