"""RATIOUNSAFE Task 1.2／3.1（docs/RATIOUNSAFE_SPEC.md v5）：IC 頁「套用後處理」對**帶週期標記**之 ratio-unsafe 欄明示排除。

經真服務路徑 `ic_analysis_service._apply_transforms_sync`（沿用 `tests/api/test_icpostleak_api.py` 之 `_run`），特徵值取自真實 kline；
欄名依生產落盤規則（`ohlc_12h_pattern_*`）。參數：`tests/_golden/ratiounsafe/contract.json`。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from momentum.FeatureEngineering import feature_naming as fn
from tests.api import test_icpostleak_api as icp

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/ratiounsafe/contract.json").read_text(encoding="utf-8"))
REASON = CONTRACT["excluded_reason"]
TAGGED_UNSAFE = ["ohlc_12h_pattern_CDLDOJI", "ohlc_12h_pattern_CDLENGULFING"]


def _frame(with_unsafe: bool = True) -> pd.DataFrame:
    frame = icp._real_frame()
    if with_unsafe:
        for i, name in enumerate(TAGGED_UNSAFE):
            frame[name] = frame[frame.columns[0]].to_numpy() * (1.0 + 0.01 * (i + 1))
    return frame


def test_tagged_unsafe_excluded_with_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = _frame()
    got = icp._run(tmp_path, frame, ["zscore"], tag="ru_tagged")
    excluded = got["result"]["excluded_features"]
    assert [e["name"] for e in excluded] == TAGGED_UNSAFE
    assert all(e["reason"] == REASON for e in excluded)
    assert not set(TAGGED_UNSAFE) & set(got["frame"].columns)


def test_safe_columns_output_unchanged_by_unsafe_presence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """非 ratio-unsafe 欄之輸出與「未混入 ratio-unsafe 欄」時逐位元組相同。"""
    monkeypatch.chdir(tmp_path)
    with_u = icp._run(tmp_path, _frame(True), ["rank", "zscore"], tag="ru_with")["frame"]
    without = icp._run(tmp_path, _frame(False), ["rank", "zscore"], tag="ru_without")["frame"]
    pd.testing.assert_frame_equal(with_u[without.columns], without, check_exact=True)


def test_boundary_01_all_tagged_unsafe_selected_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界①（IC 頁）：全選帶標記 ratio-unsafe 欄 ⇒ 既有 ValueError，訊息列欄名。"""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match=re.escape(TAGGED_UNSAFE[0])):
        icp._run(tmp_path, _frame(), ["zscore"], selected=TAGGED_UNSAFE, tag="ru_all")


def test_boundary_02_response_schema_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 邊界②：`excluded_features` 項之鍵集合不變（前端顯示所依）。"""
    monkeypatch.chdir(tmp_path)
    got = icp._run(tmp_path, _frame(), ["zscore"], tag="ru_schema")
    assert {tuple(sorted(e)) for e in got["result"]["excluded_features"]} == {("name", "reason")}


def test_mutation_common_core_none_lets_tagged_unsafe_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """共同核心 mutant：`feature_naming.ratio_unsafe_category` 恆回 None ⇒ IC 頁不再排除帶標記欄。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: None)
    got = icp._run(tmp_path, _frame(), ["zscore"], tag="ru_mut")
    assert got["result"]["excluded_features"] == []


def test_mutation_factories_reverted_to_old_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """接線 mutant：IC 服務所引用之 `ratio_unsafe_category` 改回舊位置規則 ⇒ 帶標記欄不被排除。"""
    from api.services import ic_analysis_service as svc_mod

    def _old(column: str):
        parts = str(column).split("_", 2)
        return parts[1] if len(parts) >= 2 and parts[1] in fn.RATIO_UNSAFE_CATEGORIES else None

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(svc_mod, "ratio_unsafe_category", _old)
    # 服務端漏判 ⇒ 帶標記欄進入正式轉換後被剔除，服務取欄即 KeyError；或回應未列排除——兩者皆與正確行為不同
    try:
        got = icp._run(tmp_path, _frame(), ["zscore"], tag="ru_wire")
    except KeyError:
        return
    assert [e["name"] for e in got["result"]["excluded_features"]] != TAGGED_UNSAFE
