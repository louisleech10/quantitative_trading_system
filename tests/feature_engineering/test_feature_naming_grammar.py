"""FF-NAME Task 1.1 — `FeatureIdentity`、formatter、parser（docs/FFNAME_SPEC.md Task 1.1）。

文法 `<source>_<tf>_<category>_<indicator>[_<params>][_<op>]*`；段間 `_`、段內 `-`；任一段不得含 `_`。
邊界：①多輸出指標（`BBANDS-Lower`）②參數含小數（`20-2.0`）③配對成員參數數不同 ④無參數指標（params 段省略）。
驗證：往返（隨機身分 1,000 例＋§G 零件推導之全部新名）、拒收（底線入段、未知 category、未知 op、非法參數字元、
空段、TsCorr 缺 digest）、冪等 `canonical_segment`、tf 鍵取自 aligner（新增鍵不需改碼）。
規則資料取自 `tests/_golden/ffname/contract.json`。
"""

from __future__ import annotations

import dataclasses
import random

import pytest

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from tests.feature_engineering.ffname_helpers import (
    CATEGORIES,
    KIND_EXAMPLES,
    KINDS,
    NAMING_VERSION,
    REJECT,
    UNTAGGED,
    VALID,
    iter_new_names_from_baseline,
    params_str,
    rejects,
    roundtrip_ok,
)


def _ident(name: str):
    return fn.parse_feature_name(name)


# ---------------------------------------------------------------- 邊界

def test_boundary_01_multi_output_indicator():
    name = VALID["multi_output"]
    ident = _ident(name)
    assert ident.indicator == "BBANDS-Lower"
    assert ident.category == "trend" and ident.source == "close" and ident.tf == "1h"
    assert params_str(ident) == "13"
    assert fn.format_feature_name(ident) == name


def test_boundary_02_decimal_params():
    name = VALID["decimal_params"]
    ident = _ident(name)
    assert ident.indicator == "Keltner-Width" and params_str(ident) == "20-2.0"
    assert fn.format_feature_name(ident) == name


def test_boundary_03_pair_members_with_different_param_counts():
    name = VALID["pair_param_count_differs"]
    ident = _ident(name)
    assert params_str(ident) == "20-2.0~55"
    assert fn.format_feature_name(ident) == name
    same_count = _ident(VALID["pair_params"])
    assert params_str(same_count) == "12-26-0~5-30-0"


def test_boundary_04_no_param_indicator_omits_params_segment():
    name = VALID["no_params"]
    ident = _ident(name)
    assert ident.indicator == "ForceIndex"
    assert params_str(ident) == ""
    assert fn.format_feature_name(ident) == name
    assert name.count("_") == 3  # source_tf_category_indicator，無空 params 段


# ---------------------------------------------------------------- 往返

_SOURCES = ("close", "hlc", "close-volume", "taker-ratio", "close-quote-volume", "ohlc")
_ATOMIC_CATEGORIES = tuple(c for c in CATEGORIES if c not in {"raw", "cross-sectional", "meta", "custom"})


def _random_name(rng: random.Random, tfs) -> str:
    source = rng.choice(_SOURCES)
    tf = rng.choice(tfs)
    category = rng.choice(_ATOMIC_CATEGORIES)
    indicator = rng.choice(("EMA", "BBANDS-Upper", "Keltner-Width", "RSI", "amihud-illiq", "HT-DCPHASE", "T3"))
    segs = [source, tf, category, indicator]
    n_params = rng.choice((0, 1, 2, 3))
    if n_params:
        segs.append("-".join(rng.choice(("5", "13", "21", "2.0", "0", "144")) for _ in range(n_params)))
    if rng.random() < 0.5:
        segs.append(rng.choice(("Distance", f"Momentum-L{rng.choice((1, 5))}")))
    if rng.random() < 0.5:
        segs.append(f"{rng.choice(('Kurt', 'Mean', 'Std', 'Slope'))}-W{rng.choice((5, 13))}")
    if rng.random() < 0.5:
        segs.append(f"Lag-{rng.choice((1, 2, 3))}")
    if rng.random() < 0.5:
        segs.append(rng.choice(("fracdiff", "diff-1", "rank", "gaussian", "zscore-21")))
    return "_".join(segs)


def test_roundtrip_random_1000_identities():
    rng = random.Random(20261018)
    tfs = sorted(fn.timeframe_keys())
    names = {_random_name(rng, tfs) for _ in range(1000)}
    bad = [n for n in names if not roundtrip_ok(n)]
    assert bad == []
    for n in sorted(names)[:200]:
        ident = _ident(n)
        assert fn.parse_feature_name(fn.format_feature_name(ident)) == ident
        assert ident.kind in KINDS and ident.category in CATEGORIES


def test_roundtrip_identity_constructed_by_replace():
    """以既有身分 `dataclasses.replace` 構造新身分：format 後 parse 回同一身分。"""
    base = _ident(VALID["multi_output"])
    for tf in sorted(fn.timeframe_keys())[:5]:
        ident = dataclasses.replace(base, tf=tf)
        assert fn.parse_feature_name(fn.format_feature_name(ident)) == ident


def test_roundtrip_all_spec_valid_names():
    bad = [n for n in VALID.values() if not roundtrip_ok(n)]
    assert bad == []


def test_roundtrip_all_new_names_from_frozen_parts():
    names = list(iter_new_names_from_baseline())
    assert len(names) > 0
    bad = [n for n in names if not roundtrip_ok(n)]
    assert bad == [], bad[:20]


# ---------------------------------------------------------------- 拒收

@pytest.mark.parametrize("case", ["underscore_in_segment", "unknown_category", "unknown_op",
                                  "illegal_param_char", "empty_segment", "tscorr_missing_digest"])
def test_rejects_invalid_names(case):
    assert rejects(REJECT[case]), case


def test_label_is_not_feature_grammar():
    label = REJECT["label"]
    assert fn.is_label_column(label) is True
    assert fn.is_label_column(VALID["multi_output"]) is False
    with pytest.raises(fn.LabelColumnNotFeatureError):
        fn.parse_feature_name(label)
    with pytest.raises(fn.LabelColumnNotFeatureError):
        fn.parse_feature_name(label, tagged=False)


def test_exception_hierarchy_v13():
    assert issubclass(fn.FeatureNameParseError, ValueError)
    assert issubclass(fn.LabelColumnNotFeatureError, fn.FeatureNameParseError)
    assert issubclass(fn.FeatureNamingVersionError, RuntimeError)
    assert not issubclass(fn.FeatureNamingVersionError, ValueError)


# ---------------------------------------------------------------- 身分形態（v13 介面定案）

def test_identity_is_frozen_dataclass_with_tuple_fields():
    ident = _ident(VALID["pair_params"])
    assert dataclasses.is_dataclass(ident)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ident.source = "x"  # type: ignore[misc]
    assert ident.params == (("12", "26", "0"), ("5", "30", "0"))
    assert ident.ops == ("Cross",)
    single = _ident(VALID["decimal_params"])
    assert single.params == (("20", "2.0"),) and single.ops == ()
    assert _ident(VALID["no_params"]).params == ()
    rolled = _ident(VALID["rolling"])
    assert rolled.params == (("144",),) and rolled.ops == ("Kurt-W13",)


@pytest.mark.parametrize("name", sorted(KIND_EXAMPLES))
def test_kind_mechanically_derived(name):
    assert _ident(name).kind == KIND_EXAMPLES[name]
    assert roundtrip_ok(name)


# ---------------------------------------------------------------- 標記前後兩形

@pytest.mark.parametrize("key", sorted(UNTAGGED))
def test_untagged_form_parses_and_matches_tagged(key):
    name = UNTAGGED[key]
    untagged = fn.parse_feature_name(name, tagged=False)
    tf = sorted(fn.timeframe_keys())[0]
    full = fn.tag_timeframe(name, tf)
    tagged = fn.parse_feature_name(full)
    assert tagged.tf == tf
    assert dataclasses.replace(tagged, tf=untagged.tf) == untagged
    assert fn.format_feature_name(tagged) == full
    assert fn.strip_timeframe_tag(full) == name


def test_forms_are_not_interchangeable():
    tf = sorted(fn.timeframe_keys())[0]
    untagged = UNTAGGED["multi_output"]
    with pytest.raises(fn.FeatureNameParseError):
        fn.parse_feature_name(untagged)  # 預設 tagged=True：第 2 段非週期鍵
    with pytest.raises(fn.FeatureNameParseError):
        fn.parse_feature_name(fn.tag_timeframe(untagged, tf), tagged=False)  # 週期段被當 category


def test_tscorr_with_digest_parses():
    name = "close_1h_trend_EMA_8_TsCorr-0a1b2c3d-W21"
    assert roundtrip_ok(name)


# ---------------------------------------------------------------- canonical_segment／版本／tf 鍵

@pytest.mark.parametrize("raw", ["close_volume", "BBANDS_Lower", "taker_buy_volume", "already-ok", "Keltner_Width"])
def test_canonical_segment_idempotent_and_underscore_free(raw):
    once = fn.canonical_segment(raw)
    assert "_" not in once
    assert fn.canonical_segment(once) == once
    assert once == raw.replace("_", "-")


def test_current_version_constant():
    assert fn.CURRENT_FEATURE_NAMING_VERSION == NAMING_VERSION
    assert isinstance(fn.CURRENT_FEATURE_NAMING_VERSION, int)


def test_tf_keys_come_from_aligner(monkeypatch):
    original = TimeframeAligner._timeframe_seconds_keys
    existing = set(original())
    new_key = next(f"{n}h" for n in range(7, 1000) if f"{n}h" not in existing)
    name = f"close_{new_key}_trend_EMA_8"
    fn.timeframe_keys.cache_clear()
    try:
        assert rejects(name)
        monkeypatch.setattr(TimeframeAligner, "_timeframe_seconds_keys", staticmethod(lambda: list(existing | {new_key})))
        fn.timeframe_keys.cache_clear()
        assert roundtrip_ok(name)
        assert fn.tag_timeframe("close_trend_EMA_8", new_key) == name
    finally:
        monkeypatch.undo()
        fn.timeframe_keys.cache_clear()


def test_strip_timeframe_tag_inverse_of_tag():
    for tf in sorted(fn.timeframe_keys()):
        assert fn.strip_timeframe_tag(fn.tag_timeframe("close_trend_EMA_8", tf)) == "close_trend_EMA_8"


# ---------------------------------------------------------------- mutation

def test_mutation_parser_accepting_underscore_in_segment_is_caught(monkeypatch):
    """§V mutation ⑤：parser 接受底線入段（以 `split('_')` 寬鬆切段、不驗 tf／category）⇒ 拒收測試翻轉。"""
    real = fn.parse_feature_name

    def lenient(name: str, tagged: bool = True):
        parts = name.split("_")
        base = real(VALID["multi_output"])
        return dataclasses.replace(base, source=parts[0], tf=parts[1] if len(parts) > 1 else base.tf)

    assert rejects(REJECT["underscore_in_segment"]) is True
    monkeypatch.setattr(fn, "parse_feature_name", lenient)
    assert rejects(REJECT["underscore_in_segment"], parse=fn.parse_feature_name) is False


def test_mutation_non_idempotent_canonical_segment_is_caught(monkeypatch):
    """mutant：canonical_segment 改為不冪等（每次多加前綴）⇒ 冪等斷言翻轉。"""
    monkeypatch.setattr(fn, "canonical_segment", lambda x: "x-" + str(x).replace("_", "-"))
    once = fn.canonical_segment("close_volume")
    assert fn.canonical_segment(once) != once
