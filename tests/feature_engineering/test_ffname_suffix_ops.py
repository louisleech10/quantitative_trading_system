"""FF-NAME Task 2.4 — L3、L4、L5、L6、L6.5 後綴改 op 段、L4 raw 入文法（docs/FFNAME_SPEC.md Task 2.4）。

真實 kline 輕量 run（`fftfmeta_golden_helpers.prepare_env` 隔離於 tmp）；禁合成 fixture。
邊界：①L4 對 L2 欄之 lag（`apply_to=all`）②L6.5 replace 模式名不變（只 append 加 op）。
驗證：L3、L4（含 raw）、L5、L6、L6.5 每類至少一例 `format(parse(n)) == n`；§G ②④⑥ 由 Task 2.6 驗。
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.feature_config import CategoryConfig
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from tests.feature_engineering.ffname_helpers import kline_symbols, last_op_name, ops_tuple, parse_untagged, real_slice, roundtrip_ok
from tests.feature_engineering.fftfmeta_golden_helpers import fast_payload, l7_manifest, prepare_env
from tests.feature_engineering.ffstat_helpers import HEALTHY, PRIMARY_TF, SYMBOL, run_stat

TF = PRIMARY_TF
L65_OPS = {"fracdiff", "diff", "rank", "gaussian", "zscore"}
_L3_RE = re.compile(r"^(Mean|Std|Min|Max|Range|Slope|Rank|ZScore|Skew|Kurt)-W\d+$")


def _payload(mode: str) -> Dict[str, Any]:
    payload = fast_payload([TF], **HEALTHY)
    payload["data_sources"] = {"enabled_sources": ["close", "taker_ratio"], "synthetic_sources": []}
    payload["operators"] = {"enabled": True, "cross": {"enabled": True}, "ratio": {"enabled": False},
                            "distance": {"enabled": False}, "momentum": {"enabled": False},
                            "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}}
    payload["rolling_aggregation"] = {"enabled": True, "windows": [5, 13], "aggregators": {"kurt": {"enabled": True}}}
    payload["lag_features"] = {"enabled": True, "apply_to": "all"}
    payload["meta_features"] = {"enabled": True}
    reference = next(s for s in kline_symbols() if s != SYMBOL)
    payload["cross_sectional"] = {"enabled": True, "reference_symbol": reference}
    pre = payload["preprocessing"]
    pre["mode"] = mode
    pre["fractional_differencing"] = {"enabled": True, "apply_to": "non_stationary"}
    pre["adf_differencing"] = {"enabled": True, "apply_to": "non_stationary"}
    pre["rank_transform"] = {"enabled": True}
    pre["gaussian_normalize"] = {"enabled": True}
    pre["adaptive_zscore"] = {"enabled": True}
    return payload


def _columns(root: Path, result: Any) -> List[str]:
    manifest = l7_manifest(root, TF, result)
    cols: List[str] = []
    for artifact in (manifest.get("artifacts") or {}).values():
        for info in (artifact.get("groups") or {}).values():
            cols.extend(str(c) for c in info.get("columns") or [])
    return sorted(set(cols))


def _run(tmp_path_factory, mode: str, lag_apply_to: str = "all") -> List[str]:
    tmp = tmp_path_factory.mktemp(f"ffname_suffix_{mode}_{lag_apply_to}")
    payload = _payload(mode)
    payload["lag_features"]["apply_to"] = lag_apply_to
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp)
        root, _factory, result = run_stat(tmp, payload)
        return _columns(root, result)


@pytest.fixture(scope="module")
def append_cols(tmp_path_factory) -> List[str]:
    return _run(tmp_path_factory, "append")


@pytest.fixture(scope="module")
def raw_lag_cols(tmp_path_factory) -> List[str]:
    return _run(tmp_path_factory, "append", lag_apply_to="layer1_and_raw")


@pytest.fixture(scope="module")
def replace_cols(tmp_path_factory) -> List[str]:
    return _run(tmp_path_factory, "replace")


def _idents(cols: List[str]):
    return [(c, fn.parse_feature_name(c)) for c in cols]


# ---------------------------------------------------------------- 邊界

def test_boundary_01_lag_on_l2_columns(append_cols):
    hits = [c for c, ident in _idents(append_cols)
            if len(ops_tuple(ident)) >= 2 and ops_tuple(ident)[-2] in {"Cross"} and last_op_name(ident) == "Lag"]
    assert hits, "apply_to=all 下無 L2 欄之 lag"
    assert all(roundtrip_ok(c) for c in hits)


def test_boundary_02_replace_mode_has_no_transform_op(append_cols, replace_cols):
    assert not [c for c, ident in _idents(replace_cols) if last_op_name(ident) in L65_OPS]
    assert set(replace_cols) <= set(append_cols)
    assert [c for c, ident in _idents(append_cols) if last_op_name(ident) in L65_OPS], "append 模式無 L6.5 op"


# ---------------------------------------------------------------- 驗證：每類至少一例往返

def test_all_columns_roundtrip(append_cols, raw_lag_cols, replace_cols):
    bad = [c for c in set(append_cols) | set(raw_lag_cols) | set(replace_cols) if not roundtrip_ok(c)]
    assert bad == [], bad[:20]


def test_l3_rolling_op(append_cols):
    assert [c for c, ident in _idents(append_cols) if ops_tuple(ident) and _L3_RE.match(ops_tuple(ident)[-1])]


def test_l4_raw_lag_identity(raw_lag_cols):
    raw = [(c, ident) for c, ident in _idents(raw_lag_cols) if ident.category == "raw"]
    assert raw, "layer1_and_raw 下無 raw lag 欄"
    sources = {ident.source for _c, ident in raw}
    assert "taker-ratio" in sources and "close" in sources
    for c, ident in raw:
        assert ident.indicator == "value" and last_op_name(ident) == "Lag"
        assert re.match(r"^Lag-\d+$", ops_tuple(ident)[-1])


def test_l5_cross_sectional(append_cols):
    xsec = [ident for _c, ident in _idents(append_cols) if ident.category == "cross-sectional"]
    assert xsec
    assert {i.source for i in xsec} == {"xsec"}
    assert {i.indicator for i in xsec} <= {"relative-price", "beta", "idiosyncratic-momentum"}


def test_l6_meta(append_cols):
    meta = [ident for _c, ident in _idents(append_cols) if ident.category == "meta"]
    assert meta
    assert {i.source for i in meta} == {"meta"}
    assert "trend-consensus" in {i.indicator for i in meta}
    assert all("_" not in i.indicator for i in meta)


def test_append_mode_transform_ops(append_cols):
    ops = {ops_tuple(ident)[-1] for _c, ident in _idents(append_cols) if last_op_name(ident) in L65_OPS}
    names = {op.split("-")[0] for op in ops}
    assert {"rank", "gaussian", "zscore"} <= names
    assert all(re.match(r"^(fracdiff|diff-\d+|rank|gaussian|zscore-\d+)$", op) for op in ops)


# ---------------------------------------------------------------- 單元：L3 名稱（真實 kline 切片）

def _l3_names() -> List[str]:
    kline = real_slice(400)
    cfg = CategoryConfig(indicators=[{"name": "EMA", "periods": [5, 13]}]).model_dump()
    l1 = TrendIndicatorEngine(cfg, ["close"]).compute_all(kline)
    out = RollingAggregator({"enabled": True, "windows": [5], "aggregators": {"kurt": {"enabled": True}}}).compute_all(l1)
    frame = out if isinstance(out, pd.DataFrame) else out[0]
    return [str(c) for c in frame.columns]


def test_l3_unit_names_parse():
    names = _l3_names()
    assert names
    for n in names:
        ident = parse_untagged(n)
        assert ops_tuple(ident)[-1] == "Kurt-W5"
        assert ident.kind == "rolling"


def test_mutation_l3_label_with_underscore_is_caught(monkeypatch):
    """mutant：L3 後綴恢復舊式（`Kurt_W5`，段內用底線）⇒ 名稱不可解析或 op 不符。"""
    monkeypatch.setattr(RollingAggregator, "_format_agg_label", lambda self, agg: "Kurt_X")
    names = _l3_names()
    ok = []
    for n in names:
        try:
            ok.append(ops_tuple(parse_untagged(n))[-1] == "Kurt-W5")
        except Exception:  # noqa: BLE001
            ok.append(False)
    assert not all(ok)
