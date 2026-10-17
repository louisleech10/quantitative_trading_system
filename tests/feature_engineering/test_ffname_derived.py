"""FF-NAME Task 2.3 — L2 衍生層（docs/FFNAME_SPEC.md Task 2.3）。

真實 kline 尾段切片＋正式 `FeatureFactory._build_indicator_specs`；禁合成 fixture。
邊界：①同家族不同參數兩分支合併後配對＝單分支給全部參數 ②`close-volume` 來源配對。
驗證：兩分支同家族合併、重複參數 ValueError、Distance 對 `taker-ratio` 來源產欄數 > 0、TsCorr 名 `parse` 成功；
§G ⑤ 由 Task 2.6 驗。mutation：§V ②L2 只 canonical 一臂 ③移除重複參數 ValueError ④Distance 改回以顯示 source 查 raw
⑥TsCorr 改回內嵌全名。
v13：`indicator_specs` 每筆帶 `raw_lookup_key`；L1／L2 欄於生成期間為未標記形，以 `parse_feature_name(name, tagged=False)` 解析。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from tests.feature_engineering.ffname_helpers import (
    REPO,
    ops_tuple,
    params_str,
    parse_untagged,
    patch_everywhere,
    real_slice,
    untagged_roundtrip_ok,
)
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR
from tests.feature_engineering.ffstat_helpers import PRIMARY_TF

TF = PRIMARY_TF
PERIODS = [5, 13, 21, 55, 144]
_TSCORR_RE = re.compile(r"^TsCorr-[0-9a-f]{8}-W(\d+)$")


def _payload() -> Dict[str, Any]:
    off = {"enabled": False}
    return {
        "data_sources": {"enabled_sources": ["close", "taker_ratio"], "synthetic_sources": []},
        "atomic_indicators": {
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "periods": PERIODS}]},
            "statistics": {"enabled": True, "indicators": [{"name": "Beta_CloseVolume", "periods": PERIODS}]},
            "momentum": off, "volatility": off, "volume": off, "cycle": off, "pattern": off,
            "microstructure": off, "entropy": off, "tail_risk": off,
        },
    }


@pytest.fixture(scope="module")
def setup() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict]]:
    kline = real_slice(800)
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config(_payload())
    sources = factory._select_single_series_sources(config)
    l1 = pd.concat([
        TrendIndicatorEngine(config.atomic_indicators.trend.model_dump(), sources).compute_all(kline),
        StatisticsIndicatorEngine(config.atomic_indicators.statistics.model_dump(), sources).compute_all(kline),
    ], axis=1)
    specs = factory._build_indicator_specs(l1, config)
    assert specs, "indicator_specs 為空"
    return kline, l1, specs


def _ops(cross=False, ratio=False, distance=False, worldquant: Optional[Dict] = None) -> Dict[str, Any]:
    return {"cross": {"enabled": cross}, "ratio": {"enabled": ratio}, "distance": {"enabled": distance},
            "momentum": {"enabled": False}, "binary_signal": {"enabled": False}, "signed_strength": {"enabled": False},
            "worldquant": worldquant or {"enabled": False}}


def _family_cols(l1: pd.DataFrame, source: str, indicator: str):
    return [c for c in l1.columns if parse_untagged(c).source == source and parse_untagged(c).indicator == indicator]


def _pair_names(engine_cfg, l1, kline, specs) -> set:
    out = DerivedOperatorEngine(engine_cfg).compute_all(l1, kline, specs)
    return set(map(str, out.columns))


def _merge_equal(l1, kline, specs) -> bool:
    """同家族之一半欄走分支一（給 spec）、另一半走分支二（不給 spec）⇒ 配對欄集合＝全部給 spec。"""
    try:
        fam = _family_cols(l1, "taker-ratio", "EMA")
        if len(fam) < 4:
            return False
        half = {k: v for k, v in specs.items() if k not in set(fam[: len(fam) // 2])}
        full = _pair_names(_ops(cross=True), l1, kline, specs)
        mixed = _pair_names(_ops(cross=True), l1, kline, half)
        return bool(full) and mixed == full
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- 邊界

def test_boundary_01_two_branch_same_family_merges(setup):
    kline, l1, specs = setup
    assert _merge_equal(l1, kline, specs)


def test_boundary_02_close_volume_source_pairs(setup):
    kline, l1, specs = setup
    names = _pair_names(_ops(cross=True), l1, kline, specs)
    pairs = [n for n in names if parse_untagged(n).source == "close-volume"]
    assert pairs, "close-volume 來源無配對欄"
    for n in pairs:
        ident = parse_untagged(n)
        assert ident.indicator == "Beta-CloseVolume" and ops_tuple(ident) == ("Cross",)
        fast, slow = params_str(ident).split("~")
        assert int(float(fast)) in PERIODS and int(float(slow)) in PERIODS and float(fast) < float(slow)


# ---------------------------------------------------------------- 驗證

def test_pair_name_is_base_identity_plus_fast_slow_plus_op(setup):
    kline, l1, specs = setup
    names = _pair_names(_ops(cross=True, ratio=True), l1, kline, specs)
    assert names
    for n in names:
        ident = parse_untagged(n)
        assert untagged_roundtrip_ok(n, TF)  # 生成期間未標記形可解析且標記後完整形往返
        assert "~" in params_str(ident) and ops_tuple(ident)[-1] in {"Cross", "Ratio"}


def test_indicator_specs_carry_raw_lookup_key(setup):
    _kline, l1, specs = setup
    assert all("raw_lookup_key" in v for v in specs.values())
    taker = [k for k in specs if parse_untagged(k).source == "taker-ratio"]
    assert taker and {specs[k]["raw_lookup_key"] for k in taker} == {"taker_ratio"}
    assert {specs[k]["source"] for k in taker} == {"taker-ratio"}


def _duplicate_rejected(l1, kline, specs) -> bool:
    fam = _family_cols(l1, "taker-ratio", "EMA")
    a = fam[0]
    twin = f"{a}-twin"  # 不同欄名、同家族同參數（spec 複製自 a）
    frame = l1.copy()
    frame[twin] = frame[a].to_numpy()
    twin_specs = dict(specs)
    twin_specs[twin] = dict(specs[a])
    try:
        DerivedOperatorEngine(_ops(cross=True)).compute_all(frame, kline, twin_specs)
    except ValueError as exc:
        return a in str(exc) and twin in str(exc)
    return False


def test_duplicate_params_in_family_raises_value_error_listing_both(setup):
    kline, l1, specs = setup
    assert _duplicate_rejected(l1, kline, specs)


def _distance_taker_count(l1, kline, specs) -> int:
    out = DerivedOperatorEngine(_ops(distance=True)).compute_all(l1, kline, specs)
    return sum(1 for c in out.columns
               if ops_tuple(parse_untagged(c))[-1:] == ("Distance",) and parse_untagged(c).source == "taker-ratio")


def test_distance_on_taker_ratio_source_produces_columns(setup):
    kline, l1, specs = setup
    assert _distance_taker_count(l1, kline, specs) > 0


def test_tscorr_name_parses_with_digest(setup):
    kline, l1, specs = setup
    wq = lambda target: {"enabled": True, "operators": ["ts_corr"], "transforms": [], "windows": [21], "corr_with": target}
    by_target = {}
    for target in ("volume", "close"):
        out = DerivedOperatorEngine(_ops(worldquant=wq(target))).compute_all(l1, kline, specs)
        cols = [c for c in out.columns if "TsCorr" in c]
        assert cols
        digests = set()
        for c in cols:
            ident = parse_untagged(c)
            op = ops_tuple(ident)[-1]
            m = _TSCORR_RE.match(op)
            assert m and m.group(1) == "21", op
            assert target not in op
            digests.add(op.split("-")[1])
        by_target[target] = digests
    assert by_target["volume"].isdisjoint(by_target["close"])


def test_binary_signal_multiword_suffix_generates_single_canonical_op(setup):
    """SPEC v14 Task 1.1／2.3：多字後綴（預設 ADX `Strong_Trend`）經 canonical_segment 成單一 op 段，產出名可 parse。"""
    kline, l1, specs = setup
    ops = _ops()
    ops["binary_signal"] = {"enabled": True, "rules": [{"indicator": "EMA", "condition": "> 0", "name_suffix": "Strong_Trend"}]}
    out = DerivedOperatorEngine(ops).compute_all(l1, kline, specs)
    cols = [c for c in out.columns if "BinarySignal" in c]
    assert cols
    for c in cols:
        assert ops_tuple(parse_untagged(c))[-1] == "BinarySignal-Strong-Trend", c


def test_binary_signal_rule_suffix_validated_at_config_load():
    """SPEC v14 Task 2.3：`BinarySignalRule.name_suffix` 經 canonical_segment 後不合字母表 ⇒ 載入時 ValueError；
    `config/` 內全部既有 `name_suffix` 實值皆通過（與既有使用者設定相容）。"""
    import yaml
    from momentum.FeatureEngineering.feature_config import BinarySignalRule

    with pytest.raises(ValueError):
        BinarySignalRule(indicator="RSI", condition="> 70", name_suffix="Bad Suffix!")
    with pytest.raises(ValueError):
        BinarySignalRule(indicator="RSI", condition="> 70", name_suffix="")
    suffixes = []

    def walk(node):
        if isinstance(node, dict):
            if "name_suffix" in node:
                suffixes.append(node["name_suffix"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in sorted((REPO / "config").glob("*.yaml")):
        walk(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert "Strong_Trend" in suffixes
    for suffix in suffixes:
        BinarySignalRule(indicator="RSI", condition="> 70", name_suffix=suffix)


# ---------------------------------------------------------------- mutation

def test_mutation_only_one_arm_canonical_is_caught(setup, monkeypatch):
    """§V mutation ②：canonical 只作用一臂（canonical_segment 失效 ⇒ 分支一保留原始值）⇒ 兩分支不再合併。"""
    kline, l1, specs = setup
    raw_specs = {k: {**v, "source": str(v.get("source")).replace("-", "_")} for k, v in specs.items()}
    patch_everywhere(monkeypatch, fn.canonical_segment, lambda x: str(x))  # L2 端之 canonical 失效
    assert _merge_equal(l1, kline, raw_specs) is False


def test_mutation_duplicate_value_error_removed_is_caught(setup, monkeypatch):
    """§V mutation ③：移除重複參數 ValueError（分組前靜默去重）⇒ 不再拋。"""
    kline, l1, specs = setup
    original = DerivedOperatorEngine._build_feature_info

    def dedup(self, columns, indicator_specs):
        return original(self, [c for c in columns if not str(c).endswith("-twin")], indicator_specs)

    monkeypatch.setattr(DerivedOperatorEngine, "_build_feature_info", dedup)
    assert _duplicate_rejected(l1, kline, specs) is False


def test_mutation_distance_by_display_source_is_caught(setup, monkeypatch):
    """§V mutation ④：Distance 改回以顯示（canonical）source 查 raw ⇒ `taker-ratio` 對不上 raw `taker_ratio` ⇒ 0 欄。"""
    kline, l1, specs = setup
    display_specs = {k: {**v, "raw_lookup_key": v.get("source")} for k, v in specs.items()}
    assert _distance_taker_count(l1, kline, specs) > 0
    monkeypatch.setattr(DerivedOperatorEngine, "_build_feature_info",
                        lambda self, columns, indicator_specs, _o=DerivedOperatorEngine._build_feature_info: _o(self, columns, display_specs))
    assert _distance_taker_count(l1, kline, specs) == 0
