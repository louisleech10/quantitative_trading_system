"""FF-NAME Task 3.1 — API 欄名解析一律經 `parse_feature_name`（docs/FFNAME_SPEC.md Task 3.1）。

邊界：非特徵名（label、raw kline 欄）具名回傳，不落入 other。
驗證：`infer_category`／`infer_layer` 對 §G 全部新名與身分一致（不一致數 == 0；今日誤判之 `*_volume_statistics_*`、
`ms_ofi_zscore_*` 為反例）；不得保留子字串判 category／layer。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable, Iterable, List

import pytest

import api.utils.feature_name_parser as parser_mod
import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import REPO, VALID, iter_new_names_from_baseline, layer_of_identity

# 今日誤判反例之新名（同一身分）：BETA 配對（舊 `close_12h_volume_statistics_BETA_13_144_Cross` 被判 volume）、
# OFI zscore（舊 `ms_ofi_zscore_21` 被判 L6.5）
COUNTER_EXAMPLES = (
    "close-volume_12h_statistics_Beta-CloseVolume_13~144_Cross",
    "taker-ratio_12h_microstructure_ofi-zscore_21",
)


def _mismatches(names: Iterable[str], infer_category: Callable[[str], str], infer_layer: Callable[[str], str]) -> List[str]:
    bad = []
    for n in names:
        ident = fn.parse_feature_name(n)
        if infer_category(n) != ident.category or infer_layer(n) != layer_of_identity(ident):
            bad.append(n)
    return bad


def test_boundary_01_non_feature_names_named_not_other():
    label = "label_binary_5d"
    raw_kline = "taker_ratio"
    for name in (label, raw_kline):
        cat = parser_mod.infer_category(name)
        layer = parser_mod.infer_layer(name)
        assert cat and cat != "other", name
        assert layer and layer not in {"other", "layer1"}, name
    assert parser_mod.infer_category(label) != parser_mod.infer_category(raw_kline)


def test_spec_names_consistent_with_identity():
    assert _mismatches(VALID.values(), parser_mod.infer_category, parser_mod.infer_layer) == []


def test_counter_examples_consistent():
    assert _mismatches(COUNTER_EXAMPLES, parser_mod.infer_category, parser_mod.infer_layer) == []
    assert parser_mod.infer_category(COUNTER_EXAMPLES[0]) == "statistics"
    assert parser_mod.infer_layer(COUNTER_EXAMPLES[1]) == "layer1"


def test_all_frozen_new_names_consistent():
    names = list(iter_new_names_from_baseline())
    assert names
    bad = _mismatches(names, parser_mod.infer_category, parser_mod.infer_layer)
    assert len(bad) == 0, bad[:20]


def test_no_substring_heuristics_remain():
    src = (REPO / "api" / "utils" / "feature_name_parser.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    affix = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in {"startswith", "endswith"} and n.args and isinstance(n.args[0], ast.Constant)
             and n.args[0].value != "label_"]
    substr_in = [n for n in ast.walk(tree) if isinstance(n, ast.Compare) and any(isinstance(op, ast.In) for op in n.ops)
                 and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str) and "_" in n.left.value]
    regex = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in {"search", "match", "compile"}]
    assert affix == [] and substr_in == [] and regex == []
    assert "parse_feature_name" in src


def test_mutation_substring_infer_category_is_caught(monkeypatch):
    """mutant：恢復子字串判 category（`_volume_` 先於 `_statistics_`）⇒ 反例不一致。"""
    def substring_category(name: str) -> str:
        for token in ("trend", "momentum", "volatility", "volume", "statistics", "microstructure"):
            if f"_{token}_" in name or name.startswith(f"{token}_") or f"-{token}_" in name:
                return token
        return "other"

    monkeypatch.setattr(parser_mod, "infer_category", substring_category)
    assert _mismatches(COUNTER_EXAMPLES, parser_mod.infer_category, parser_mod.infer_layer) != []
