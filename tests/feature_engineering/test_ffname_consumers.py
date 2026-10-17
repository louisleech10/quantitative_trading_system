"""FF-NAME Task 3.1 — 後端解析點（momentum／scripts 側；docs/FFNAME_SPEC.md Task 3.1）。

凡由欄名推 source／category／indicator／params／ops 或 layer 者一律 `parse_feature_name`：
`core/column_group_registry.py`（`_column_sort_key`、`_extract_*`、`_CATEGORY_ORDER` 補齊封閉集合）、
`feature_naming.ratio_unsafe_category`、`atomic/pattern_indicators.py:65`、`scripts/analyze_problem_features.py`
（自製 parser 改呼叫 `parse_feature_name`，讀特徵 parquet 改經 reader）。
驗證：`_extract_category` 對 §G 全部新名與身分一致（不一致數 == 0）。API 側見 tests/api/test_feature_name_parser.py。
"""

from __future__ import annotations

import ast
from types import SimpleNamespace
from typing import Iterable, List

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from tests.feature_engineering.ffname_helpers import CATEGORIES, REPO, VALID, iter_new_names_from_baseline


def _bare_registry() -> ColumnGroupRegistry:
    return ColumnGroupRegistry.__new__(ColumnGroupRegistry)


def _group(name: str) -> SimpleNamespace:
    ident = fn.parse_feature_name(name)
    return SimpleNamespace(group_id=f"{ident.tf}_L1_{ident.category}_{ident.indicator}", timeframe=ident.tf,
                           indicator=ident.indicator, data_source=ident.source, layer=None)


def _category_mismatches(names: Iterable[str], extract) -> List[str]:
    reg = _bare_registry()
    bad = []
    for n in names:
        _key, value = extract(reg, _group(n), n)
        if value != fn.parse_feature_name(n).category:
            bad.append(n)
    return bad


def test_non_feature_names_not_misclassified():
    """（Task 3.1 邊界之 momentum 側對應；具名邊界測試見 tests/api/test_feature_name_parser.py）label、raw kline 欄不誤判。"""
    reg = _bare_registry()
    for name in ("label_binary_5d", "taker_ratio"):
        assert fn.ratio_unsafe_category(name) is None
        key, value = ColumnGroupRegistry._extract_category(reg, SimpleNamespace(group_id="1h_label", timeframe="1h",
                                                                                 indicator="", data_source="", layer=None), name)
        assert value not in CATEGORIES or value == "raw", (name, value)


def test_category_order_covers_closed_set():
    assert set(CATEGORIES) <= set(ColumnGroupRegistry._CATEGORY_ORDER)


def test_extract_category_matches_identity_spec_names():
    assert _category_mismatches(VALID.values(), ColumnGroupRegistry._extract_category) == []


def test_extract_category_matches_identity_all_frozen_new_names():
    names = list(iter_new_names_from_baseline())
    assert names
    assert _category_mismatches(names, ColumnGroupRegistry._extract_category) == []


def test_ratio_unsafe_category_via_parse():
    assert fn.ratio_unsafe_category(VALID["pattern_count"]) == "pattern"
    assert fn.ratio_unsafe_category("ohlc_1h_pattern_CDLDOJI") == "pattern"
    assert fn.ratio_unsafe_category(VALID["multi_output"]) is None
    # source 含連字號、category 非 pattern 不得誤判
    assert fn.ratio_unsafe_category("close-volume_1h_statistics_Beta-CloseVolume_13") is None


def _calls(path: str) -> set:
    tree = ast.parse((REPO / path).read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            out.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    return out


def test_pattern_frequency_window_not_from_name_split():
    src = (REPO / "momentum/FeatureEngineering/atomic/pattern_indicators.py").read_text(encoding="utf-8")
    assert 'rsplit("_W"' not in src and "rsplit('_W'" not in src


def test_analyze_problem_features_uses_parser_and_reader():
    calls = _calls("scripts/analyze_problem_features.py")
    assert "parse_feature_name" in calls
    src = (REPO / "scripts/analyze_problem_features.py").read_text(encoding="utf-8")
    assert "pq.read_table" not in src and "read_parquet" not in src
    assert "FeatureReader" in src or "create_feature_reader" in src


def test_mutation_token_scan_extract_category_is_caught(monkeypatch):
    """mutant：恢復以底線切 token 掃 category（舊 `_extract_category`）⇒ source 段恰為某 category 詞（`volume`）之名誤判。"""
    order = {c: i for i, c in enumerate(CATEGORIES)}

    def token_scan(self, group, column):
        for token in [t.lower() for t in column.split("_")]:
            if token in order:
                return order[token], token
        return len(order) + 1, ""

    names = ["volume_1h_trend_EMA_8"]
    assert _category_mismatches(names, ColumnGroupRegistry._extract_category) == []
    monkeypatch.setattr(ColumnGroupRegistry, "_extract_category", token_scan)
    assert _category_mismatches(names, ColumnGroupRegistry._extract_category) == names
