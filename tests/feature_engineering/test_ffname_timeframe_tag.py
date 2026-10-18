"""FF-NAME Task 2.5 — 週期標記與 group_id 單一實作（docs/FFNAME_SPEC.md Task 2.5）。

邊界：①欄名後段含週期 token（只看第 2 段）②label 不標記。
驗證：舊第二套標記實作於 momentum／api／scripts／tests 零出現；標記呼叫點改用 `feature_naming.tag_timeframe`；
§G 之欄序、group_id、平穩化決策鍵經映射一致（由 Task 2.6 驗）。mutation：§V ⑩保留第二套週期標記。
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import momentum.FeatureEngineering.feature_naming as fn
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from tests.feature_engineering.ffname_helpers import REPO, patch_everywhere

# 舊實作名以拼接取得，避免本檔自身命中零出現檢查
_OLD_TAGGER = "_timeframe_" + "tagged_name"
_CALLERS = (
    "momentum/FeatureEngineering/feature_factory.py",
    "momentum/FeatureEngineering/feature_storage.py",
    "momentum/FeatureEngineering/preprocessing/calibration.py",
    "scripts/freeze_batch2d_baseline.py",
)


def _tf_pair():
    keys = sorted(fn.timeframe_keys())
    return keys[0], keys[1]


def _only_second_segment_counts(tag) -> bool:
    tf_in_tail, tf = _tf_pair()
    name = f"close_trend_EMA_{tf_in_tail}"
    return tag(name, tf) == f"close_{tf}_trend_EMA_{tf_in_tail}"


def test_boundary_01_tf_token_in_tail_is_not_a_tag():
    assert _only_second_segment_counts(fn.tag_timeframe)
    tf_in_tail, tf = _tf_pair()
    tagged = fn.tag_timeframe(f"close_trend_EMA_{tf_in_tail}", tf)
    assert fn.strip_timeframe_tag(tagged) == f"close_trend_EMA_{tf_in_tail}"


def test_boundary_02_label_not_tagged():
    _a, tf = _tf_pair()
    for label in ("label_binary_5d", "label_return_5d"):
        assert fn.tag_timeframe(label, tf) == label
        assert fn.strip_timeframe_tag(label) == label


def test_old_tagger_zero_occurrences():
    # SPEC v17 Task 2.5：他票凍結 golden 之字面不屬程式碼 ⇒ 排除 `_golden` 目錄
    proc = subprocess.run(["grep", "-rn", _OLD_TAGGER, "momentum", "api", "scripts", "tests", "--exclude-dir=_golden"],
                          cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 1 and proc.stdout == "", proc.stdout[:2000]
    assert not hasattr(FeatureFactory, _OLD_TAGGER)


def test_tag_call_sites_use_single_implementation():
    for rel in _CALLERS:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
                {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        assert "tag_timeframe" in names, rel


def test_mutation_second_tagging_rule_is_caught(monkeypatch):
    """§V mutation ⑩：保留第二套標記條件（任一後段為週期鍵即視為已標記）⇒ 邊界①翻轉。"""
    keys = fn.timeframe_keys()

    def old_rule(column, timeframe):
        parts = str(column).split("_")
        if str(column).startswith("label_") or any(p in keys for p in parts[1:]):
            return str(column)
        return "_".join([parts[0], str(timeframe)] + parts[1:])

    patch_everywhere(monkeypatch, fn.tag_timeframe, old_rule)
    monkeypatch.setattr(fn, "tag_timeframe", old_rule)
    assert _only_second_segment_counts(fn.tag_timeframe) is False
