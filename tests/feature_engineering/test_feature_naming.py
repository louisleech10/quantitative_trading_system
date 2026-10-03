"""RATIOUNSAFE Task 1.1（docs/RATIOUNSAFE_SPEC.md v5）：`feature_naming` 純函式之判定、加剝標記、互逆定義域、常數同一性。

名稱集合以生產命名規則造（`TALibWrapper._CATEGORY_MAP`＋`normalize_indicator_name`，同 §A FACT-RECEIPT 1 探針），
具名案例取自 `tests/_golden/ratiounsafe/contract.json`。實作前應為紅（`feature_naming` 為 NotImplementedError 空殼）；
不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from momentum.FeatureEngineering import feature_naming as fn
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/ratiounsafe/contract.json").read_text(encoding="utf-8"))


def _pattern_names() -> List[str]:
    cmap = TALibWrapper._CATEGORY_MAP
    l1 = [f"ohlc_pattern_{TALibWrapper.normalize_indicator_name(i)}" for i in cmap["pattern"]]
    return l1 + [f"{c}_BinarySignal" for c in l1] + [f"{c}_Lag_5" for c in l1]


def _other_names() -> List[str]:
    out = []
    for cat, inds in TALibWrapper._CATEGORY_MAP.items():
        if cat in ("pattern", "price_transform"):
            continue
        out += [f"close_{cat}_{TALibWrapper.normalize_indicator_name(i)}_20" for i in inds]
    return out + ["ms_amihud_illiq_5", "ent_shannon_close_20", "tr_cvar_5pct_20", "meta_Trend_Consensus",
                  "close_trend_EMA_20_mean_W20", "taker-ratio_trend_EMA_8"]


TF_KEYS = sorted(TimeframeAligner._timeframe_seconds_keys())


def test_timeframe_keys_equal_aligner_keys() -> None:
    assert fn.timeframe_keys() == frozenset(TimeframeAligner._timeframe_seconds_keys())


@pytest.mark.parametrize("tf", TF_KEYS)
def test_pattern_names_flagged_untagged_and_tagged(tf: str) -> None:
    pats = _pattern_names()
    assert all(fn.is_ratio_unsafe_column(c) for c in pats)
    assert all(fn.is_ratio_unsafe_column(fn.tag_timeframe(c, tf)) for c in pats)
    assert all(fn.ratio_unsafe_category(fn.tag_timeframe(c, tf)) == "pattern" for c in pats)


@pytest.mark.parametrize("tf", TF_KEYS)
def test_non_pattern_names_never_flagged(tf: str) -> None:
    others = _other_names()
    assert not any(fn.is_ratio_unsafe_column(c) for c in others)
    assert not any(fn.is_ratio_unsafe_column(fn.tag_timeframe(c, tf)) for c in others)


@pytest.mark.parametrize("tf", TF_KEYS)
def test_roundtrip_within_domain(tf: str) -> None:
    keys = set(TF_KEYS)
    domain = [c for c in _pattern_names() + _other_names() + ["ret_1d_x"]
              if not c.startswith("label_") and len(c.split("_")) >= 2 and c.split("_")[1] not in keys]
    assert domain
    assert [fn.strip_timeframe_tag(fn.tag_timeframe(c, tf)) for c in domain] == domain


@pytest.mark.parametrize("case", CONTRACT["tagging_cases"], ids=lambda c: f"{c['column']}@{c['timeframe']}")
def test_named_tagging_cases(case: dict) -> None:
    assert fn.tag_timeframe(case["column"], case["timeframe"]) == case["tagged"]


def test_custom_name_with_timeframe_token_distinct_across_timeframes() -> None:
    assert fn.tag_timeframe("ret_1d_x", "12h") != fn.tag_timeframe("ret_1d_x", "4h")


def test_ratio_unsafe_categories_single_object() -> None:
    from momentum.FeatureEngineering.operators import derived_operators, rolling_aggregator
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor

    assert derived_operators.RATIO_UNSAFE_CATEGORIES is fn.RATIO_UNSAFE_CATEGORIES
    assert rolling_aggregator.RATIO_UNSAFE_CATEGORIES is fn.RATIO_UNSAFE_CATEGORIES
    assert feature_preprocessor.RATIO_UNSAFE_CATEGORIES is fn.RATIO_UNSAFE_CATEGORIES
    assert fn.RATIO_UNSAFE_CATEGORIES == frozenset(CONTRACT["ratio_unsafe_categories"])


def test_boundary_01_label_prefix_neither_tagged_nor_stripped() -> None:
    for tf in TF_KEYS:
        assert fn.tag_timeframe("label_fwd_ret_1", tf) == "label_fwd_ret_1"
    assert fn.strip_timeframe_tag("label_12h_x") == "label_12h_x"


def test_boundary_02_single_segment_name_not_unsafe() -> None:
    assert fn.is_ratio_unsafe_column("pattern") is False
    assert fn.ratio_unsafe_category("singleword") is None
    assert fn.tag_timeframe("singleword", "12h") == "singleword"


@pytest.mark.parametrize("bad", CONTRACT["invalid_timeframes"])
def test_boundary_03_invalid_timeframe_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        fn.tag_timeframe("close_trend_EMA_8", bad)


def test_mutation_strip_identity_breaks_tagged_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`strip_timeframe_tag` 恆回原值 ⇒ 帶標記 pattern 名不再被判（共同核心經 strip）。"""
    assert fn.is_ratio_unsafe_column("ohlc_12h_pattern_CDLDOJI") is True
    monkeypatch.setattr(fn, "strip_timeframe_tag", lambda column: column)
    assert fn.is_ratio_unsafe_column("ohlc_12h_pattern_CDLDOJI") is False


def test_mutation_any_segment_rule_collides_across_timeframes(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`tag_timeframe` 改為「任一段含週期鍵即不標」（frame 路徑舊規則）⇒ `ret_1d_x` 跨週期同名。"""
    keys = set(TF_KEYS)

    def _any_segment(column: str, timeframe: str) -> str:
        parts = column.split("_")
        if column.startswith("label_") or len(parts) < 2 or any(p in keys for p in parts[1:]):
            return column
        return "_".join([parts[0], timeframe] + parts[1:])

    assert fn.tag_timeframe("ret_1d_x", "12h") != fn.tag_timeframe("ret_1d_x", "4h")
    monkeypatch.setattr(fn, "tag_timeframe", _any_segment)
    assert fn.tag_timeframe("ret_1d_x", "12h") == fn.tag_timeframe("ret_1d_x", "4h")
