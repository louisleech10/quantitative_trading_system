"""FF-NAME Task 3.2 — 結構化選欄：數值路徑不讀欄名子字串（docs/FFNAME_SPEC.md Task 3.2）。

`operators/lag_processor.py`（`_is_layer1_or_raw` 改讀 group layer）、`meta_features/consensus_features.py`、
`meta_features/interaction_features.py`（`_find_column` 改身分精確比對）、`utils/cascade_blacklist.py`（比對 parse 後 indicator）。
邊界：使用者 `exclude_patterns` 仍為 fnmatch（使用者輸入）。
驗證：lag 輸入集合 == L1 群組欄＋raw 欄；`ATR-14` 不命中 `NATR-14`；cascade 黑名單對連字號名精確命中；§G ⑥（Task 2.6）。
真實 kline（輕量 run 與尾段切片）；禁合成 fixture。mutation：§V ⑨lag 改回欄名啟發式。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_naming as fn
import momentum.FeatureEngineering.utils.cascade_blacklist as cascade
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.atomic.volatility_indicators import VolatilityIndicatorEngine
from momentum.FeatureEngineering.feature_config import CategoryConfig
from momentum.FeatureEngineering.meta_features.consensus_features import ConsensusFeatureEngine
from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
import fnmatch

from tests.feature_engineering.ffname_helpers import (
    G6_GLOBS,
    drop_last_op,
    group_layer,
    last_op_name,
    manifest_group_columns,
    real_slice,
)
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, fast_payload, l7_manifest, prepare_env
from tests.feature_engineering.ffstat_helpers import HEALTHY, PRIMARY_TF, run_stat

TF = PRIMARY_TF


def _lag_payload() -> Dict[str, Any]:
    payload = fast_payload([TF], **HEALTHY)
    payload["data_sources"] = {"enabled_sources": ["close", "taker_ratio"], "synthetic_sources": []}
    for cat in ("volume", "pattern"):
        payload["atomic_indicators"][cat] = {"enabled": True}
    payload["lag_features"] = {"enabled": True, "apply_to": "layer1_and_raw"}
    return payload


@pytest.fixture(scope="module")
def lag_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ffname_lag_selection")
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp)
        root, _factory, result = run_stat(tmp, _lag_payload())
        return l7_manifest(root, TF, result)


def _strip_last_op(name: str) -> str:
    """落盤名（完整形）去掉最外層 op。"""
    return fn.format_feature_name(drop_last_op(fn.parse_feature_name(name)))


def _lag_inputs(manifest: Dict[str, Any]) -> Set[str]:
    cols = [c for cols in manifest_group_columns(manifest).values() for c in cols]
    return {_strip_last_op(c) for c in cols if last_op_name(fn.parse_feature_name(c)) == "Lag"}


def _cascade_blacklisted(columns: Set[str]) -> Set[str]:
    """本 run 設定之生產 cascade 黑名單（`nan_strategy.categorical_blacklist` 經生產 `expand_blacklist_patterns` 展開；
    SPEC v17 §G ⑥：L4 前即剔除，改前即如此）。"""
    config = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)._resolve_config(_lag_payload())
    patterns = list(config.nan_strategy.categorical_blacklist or [])
    assert patterns, "本 run 設定之 cascade 黑名單為空（§G ⑥ 之扣除前提不成立）"
    return set(cascade.expand_blacklist_patterns(patterns, sorted(columns)))


def _expected_inputs(manifest: Dict[str, Any], lag_inputs: Set[str]) -> Set[str]:
    """§G ⑥（v17）：L1 群組欄扣除 cascade 黑名單＋raw 欄。"""
    groups = manifest_group_columns(manifest)
    l1 = {c for gid, cols in groups.items() if group_layer(gid) == "L1" for c in cols}
    blacklisted = _cascade_blacklisted(l1)
    assert blacklisted, "L1 群組欄中無 cascade 黑名單欄（本 run 設定含 pattern／cycle，扣除面不得為空）"
    raw = {c for c in lag_inputs if fn.parse_feature_name(c).category == "raw"}
    return (l1 - blacklisted) | raw


def _lag_inputs_ok(selected: Set[str], expected: Set[str]) -> bool:
    return bool(expected) and selected == expected


# ---------------------------------------------------------------- 邊界

def test_boundary_01_user_exclude_patterns_still_fnmatch():
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    config = factory._resolve_config({"lag_features": {"enabled": True, "apply_to": "layer1_and_raw",
                                                        "exclude_patterns": ["*_VolumeMA-Ratio_*", "meta_*"]}})
    proc = LagProcessor(config)
    assert proc._is_excluded("volume_1h_volume_VolumeMA-Ratio_20") is True
    assert proc._is_excluded("meta_1h_meta_trend-consensus") is True
    assert proc._is_excluded("volume_1h_volume_VWAP_20") is False


# ---------------------------------------------------------------- 驗證

def test_lag_inputs_equal_l1_groups_plus_raw(lag_run):
    selected = _lag_inputs(lag_run)
    expected = _expected_inputs(lag_run, selected)
    assert _lag_inputs_ok(selected, expected), sorted(selected ^ expected)[:20]
    indicators = {fn.parse_feature_name(c).indicator for c in selected}
    assert {"VolumeMA-Ratio", "BullishCount"} <= indicators
    for glob in G6_GLOBS:  # SPEC v13 §G ⑥
        assert any(fnmatch.fnmatch(c, glob) for c in selected), glob
    assert {fn.parse_feature_name(c).source for c in selected if fn.parse_feature_name(c).category == "raw"} >= {"close", "taker-ratio"}


def _regime(periods_indicator: str) -> pd.Series:
    kline = real_slice(600)
    cfg = CategoryConfig(indicators=[{"name": periods_indicator, "periods": [14, 55]}]).model_dump()
    layer1 = VolatilityIndicatorEngine(cfg, ["close"]).compute_all(kline)
    keep = [c for c in layer1.columns if periods_indicator in c and "Keltner" not in c and "Donchian" not in c
            and "Parkinson" not in c and "GarmanKlass" not in c]
    return ConsensusFeatureEngine().compute_volatility_regime(layer1[keep])


def test_meta_find_column_atr_not_hit_by_natr():
    natr_only = _regime("NATR")
    assert natr_only.isna().all()
    atr = _regime("ATR")
    assert atr.notna().any()


def _cascade_exact(expand) -> bool:
    cols = ["close_1h_cycle_HT-DCPHASE", "close_1h_cycle_HT-DCPHASE_Kurt-W5", "close_1h_cycle_HT-DCPERIOD",
            "hlc_1h_volatility_ATR_14", "hlc_1h_volatility_NATR_14"]
    return (set(expand(["HT-DCPHASE"], cols)) == {"close_1h_cycle_HT-DCPHASE", "close_1h_cycle_HT-DCPHASE_Kurt-W5"}
            and set(expand(["ATR"], cols)) == {"hlc_1h_volatility_ATR_14"})


def test_cascade_blacklist_exact_on_hyphenated_names():
    assert _cascade_exact(cascade.expand_blacklist_patterns)


# ---------------------------------------------------------------- mutation

def _old_heuristic(col: str) -> bool:
    tokens = ["_Distance", "_Cross", "_Momentum", "_Ratio", "_Lag", "_Kurt", "_Mean", "_Std"]
    return not any(t in col for t in tokens) and re.search(r"_W\d+$", col) is None


def _inverse_baseline_mapping() -> Dict[str, str]:
    """新名（標記後）→ 舊名：§G 零件以新 formatter 推導之映射（tests/_golden/ffname/baseline.json）之反函數
    （同 test_ffname_value_invariance）。舊啟發式只認得舊名之 `_Ratio`、`_W5` 等字樣，故須套在舊名上。"""
    import json

    from tests.feature_engineering.ffname_helpers import BASELINE_PATH, load_freeze_module

    freeze = load_freeze_module()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    parts = {row["old_name"]: freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                                   "ops": tuple(row.get("ops") or ())})
             for row in data["parts"]}
    mapping = freeze.derive_mapping(parts, {k: p.tf for k, p in parts.items()})
    return {new: old for old, new in mapping.items()}


def test_mutation_lag_name_heuristic_is_caught(lag_run):
    """§V mutation ⑨：lag 改回欄名啟發式（子字串黑名單＋`_W\\d+$`，套在經 baseline 反映射取回之舊名上）⇒
    VolumeMA-Ratio／BullishCount 落選，集合不等。"""
    selected = _lag_inputs(lag_run)
    expected = _expected_inputs(lag_run, selected)
    inverse = _inverse_baseline_mapping()
    mapped = {c: inverse[c] for c in expected if c in inverse}
    rejected_by_old = {c for c, old in mapped.items() if not _old_heuristic(fn.strip_timeframe_tag(old))}
    assert any(fnmatch.fnmatch(c, g) for c in rejected_by_old for g in G6_GLOBS), sorted(rejected_by_old)[:10]
    heuristic = {c for c in expected if c not in rejected_by_old}
    assert _lag_inputs_ok(heuristic, expected) is False


def test_mutation_cascade_substring_is_caught(monkeypatch):
    """mutant：cascade 黑名單恢復子字串比對 ⇒ `ATR` 命中 `NATR`。"""
    monkeypatch.setattr(cascade, "expand_blacklist_patterns",
                        lambda patterns, columns: frozenset(c for p in patterns for c in columns if p in c))
    assert _cascade_exact(cascade.expand_blacklist_patterns) is False


def test_mutation_meta_substring_find_column_is_caught(monkeypatch):
    """mutant：meta `_find_column` 恢復子字串比對 ⇒ `ATR-14` 命中 `NATR-14`，NATR-only 時 regime 非全 NaN。"""
    def substring_find(df, candidates):
        for col in df.columns:  # 子字串 "ATR" 亦命中 "NATR"（不論 candidates 之型別）
            if "ATR" in str(col):
                return df[col]
        return None

    monkeypatch.setattr(ConsensusFeatureEngine, "_find_column", staticmethod(substring_find))
    assert _regime("NATR").notna().any()
