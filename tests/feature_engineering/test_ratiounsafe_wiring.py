"""RATIOUNSAFE Task 1.2／1.3（docs/RATIOUNSAFE_SPEC.md v5）：判定之 consumer 接線、共同核心鑑別、標記規則（storage／calibration）一致。

輸入值取自真實 kline（`ffstat_helpers.kline_frame()`）；欄名依生產命名規則（含週期標記）。參數：`tests/_golden/ratiounsafe/contract.json`。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import feature_naming as fn
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from tests.feature_engineering import ffstat_helpers as h

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((REPO / "tests/_golden/ratiounsafe/contract.json").read_text(encoding="utf-8"))
TAGGED_UNSAFE = ["ohlc_12h_pattern_CDLDOJI", "ohlc_4h_pattern_CDLENGULFING", "ohlc_12h_pattern_CDLDOJI_Lag_5"]
UNTAGGED_UNSAFE = ["ohlc_pattern_CDLDOJI", "ohlc_pattern_CDLENGULFING"]
SAFE = ["close_12h_trend_EMA_8", "close_trend_SMA_13"]


def _old_rule(column: str) -> bool:
    """改前之位置判定（`split("_", 2)[1]`）；接線 mutant 用。"""
    parts = str(column).split("_", 2)
    return len(parts) >= 2 and parts[1] in fn.RATIO_UNSAFE_CATEGORIES


def _real_frame(columns: List[str]) -> pd.DataFrame:
    base = h.kline_frame(symbol="BTCUSDT", timeframe="12h").iloc[:600]
    close = base["close"].to_numpy(dtype=np.float64)
    return pd.DataFrame({c: close * (1.0 + 0.001 * i) for i, c in enumerate(columns)}, index=base.index)


# ---------------------------------------------------------------- Task 1.2：重複實作刪除與 consumer

def test_no_duplicate_ratio_unsafe_implementation() -> None:
    out = subprocess.run(["grep", "-rn", "def _is_ratio_unsafe_column", "momentum"], cwd=REPO,
                         capture_output=True, text=True)
    assert out.stdout.strip() == "", out.stdout


def _l3_candidates(columns: List[str]) -> List[str]:
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    return RollingAggregator({"windows": [5], "aggregators": ["mean"]})._select_columns(list(columns))


def test_l3_select_columns_excludes_tagged_and_untagged_pattern() -> None:
    cand = _l3_candidates(TAGGED_UNSAFE + UNTAGGED_UNSAFE + SAFE)
    assert set(cand) == set(SAFE)


def test_preprocessor_transform_drops_tagged_pattern() -> None:
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    frame = _real_frame(TAGGED_UNSAFE + SAFE)
    out = FeaturePreprocessor({"enabled": True, "mode": "replace"}).transform(frame)
    assert not set(TAGGED_UNSAFE) & set(out.columns)
    assert set(SAFE) <= set(out.columns)


def test_factories_category_for_tagged_names() -> None:
    from momentum.factories import ratio_unsafe_category

    assert [ratio_unsafe_category(c) for c in TAGGED_UNSAFE] == ["pattern"] * len(TAGGED_UNSAFE)
    assert [ratio_unsafe_category(c) for c in SAFE] == [None] * len(SAFE)


def test_boundary_01_l3_untagged_generation_behavior_unchanged() -> None:
    """Task 1.2 邊界①：生成期未標記名之 L3 選欄＝改前位置判定之結果（L3 存活欄數不變之單元層等價）。"""
    names = UNTAGGED_UNSAFE + ["close_trend_EMA_8", "close_momentum_RSI_14", "ms_amihud_illiq_5", "meta_Trend_Consensus"]
    assert _l3_candidates(names) == [c for c in names if not _old_rule(c)]


def test_boundary_02_non_pattern_zero_false_positive() -> None:
    names = SAFE + ["ms_12h_amihud_illiq_5", "ent_1h_shannon_close_20", "tr_4h_cvar_5pct_20", "meta_12h_Trend_Consensus",
                    "taker_12h_ratio_trend_EMA_5_20_Cross"]
    assert not any(fn.is_ratio_unsafe_column(c) for c in names)


def test_mutation_common_core_breaks_all_consumers(monkeypatch: pytest.MonkeyPatch) -> None:
    """共同核心 mutant：`ratio_unsafe_category` 恆回 None ⇒ L3、transform 入口、factories 三處同時失效。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.factories import ratio_unsafe_category

    monkeypatch.setattr(fn, "ratio_unsafe_category", lambda column: None)
    assert set(TAGGED_UNSAFE) <= set(_l3_candidates(TAGGED_UNSAFE + SAFE))
    out = FeaturePreprocessor({"enabled": True, "mode": "replace"}).transform(_real_frame(TAGGED_UNSAFE + SAFE))
    assert set(TAGGED_UNSAFE) <= set(out.columns)
    assert ratio_unsafe_category(TAGGED_UNSAFE[0]) is None


@pytest.mark.parametrize("module_path", ["momentum.FeatureEngineering.operators.rolling_aggregator",
                                         "momentum.FeatureEngineering.preprocessing.feature_preprocessor"])
def test_mutation_wiring_consumer_reverted_to_old_rule(monkeypatch: pytest.MonkeyPatch, module_path: str) -> None:
    """接線 mutant：單一 consumer 之判定改回舊位置規則 ⇒ 該 consumer 對帶標記名失效。
    consumer 須以模組層名稱 `is_ratio_unsafe_column` 引用 `feature_naming`（Task 1.2 改法）。"""
    import importlib

    mod = importlib.import_module(module_path)
    assert getattr(mod, "is_ratio_unsafe_column") is fn.is_ratio_unsafe_column
    monkeypatch.setattr(mod, "is_ratio_unsafe_column", _old_rule)
    if module_path.endswith("rolling_aggregator"):
        assert set(TAGGED_UNSAFE) <= set(_l3_candidates(TAGGED_UNSAFE + SAFE))
    else:
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        out = FeaturePreprocessor({"enabled": True, "mode": "replace"}).transform(_real_frame(TAGGED_UNSAFE + SAFE))
        assert set(TAGGED_UNSAFE) <= set(out.columns)


# ---------------------------------------------------------------- Task 1.3：storage／calibration 標記一致

def _all_names() -> List[str]:
    from tests.feature_engineering.test_feature_naming import _other_names, _pattern_names

    return _pattern_names() + _other_names() + [c["column"] for c in CONTRACT["tagging_cases"]]


@pytest.mark.parametrize("tf", sorted(TimeframeAligner._timeframe_seconds_keys()))
def test_calibration_tagging_equals_naming(tf: str) -> None:
    from momentum.FeatureEngineering.preprocessing.calibration import tagged_column_name

    names = _all_names()
    assert [tagged_column_name(c, tf) for c in names] == [fn.tag_timeframe(c, tf) for c in names]


def _storage_persisted_columns(tmp_path: Path, group_id: str, columns: List[str], tf: str) -> List[str]:
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    frame = _real_frame(columns)
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = ColumnGroup(group_id=group_id, layer=LayerSource.L1, timeframe=tf, data_source="ohlc",
                        indicator="RATIOUNSAFE", columns=tuple(columns), shape=(0, 0), dtype="float32", disk_path=None)
    registry.save_data(group, frame.to_numpy(dtype=np.float32))
    storage = FeatureStorage(str(tmp_path / "features"))
    config_hash = "ratiounsafe0000000000000000000000"
    storage.write_raw_from_registry_stream("BTCUSDT", tf, config_hash, registry, preprocessor=None,
                                           row_index=pd.DatetimeIndex(frame.index))
    reader = FeatureReader(str(tmp_path / "features"))
    cols: List[str] = []
    for _, df in reader.stream_groups_v2("BTCUSDT", tf, config_hash, "raw", allow_partial=True):
        cols += [str(c) for c in df.columns]
    return cols


def test_boundary_01_storage_tags_weekly_group(tmp_path: Path) -> None:
    """Task 1.3 邊界①：storage 對 `1w` 群組之欄名加標記（改前永不標）。"""
    cols = _storage_persisted_columns(tmp_path, "1w_L1_pattern_CDLDOJI", ["ohlc_pattern_CDLDOJI"], "1w")
    assert cols == ["ohlc_1w_pattern_CDLDOJI"]


def test_storage_custom_name_distinct_across_timeframes(tmp_path: Path) -> None:
    a = _storage_persisted_columns(tmp_path / "a", "12h_L1_custom_RET", ["ret_1d_x"], "12h")
    b = _storage_persisted_columns(tmp_path / "b", "4h_L1_custom_RET", ["ret_1d_x"], "4h")
    assert a == ["ret_12h_1d_x"] and b == ["ret_4h_1d_x"]


def test_mutation_calibration_old_rule_diverges(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：calibration 改回「`parts[1]` 為任一週期鍵即不標」⇒ `ret_1d_x` 與 storage 規則不一致。"""
    from momentum.FeatureEngineering.preprocessing import calibration

    keys = set(TimeframeAligner._timeframe_seconds_keys())

    def _old(column: str, timeframe: str) -> str:
        parts = str(column).split("_")
        if str(column).startswith("label_") or len(parts) < 2 or parts[1] in keys:
            return str(column)
        return "_".join([parts[0], str(timeframe)] + parts[1:])

    assert calibration.tagged_column_name("ret_1d_x", "12h") == fn.tag_timeframe("ret_1d_x", "12h")
    monkeypatch.setattr(calibration, "tagged_column_name", _old)
    assert calibration.tagged_column_name("ret_1d_x", "12h") != fn.tag_timeframe("ret_1d_x", "12h")


# ---------------------------------------------------------------- 禁令之可觀測檢查（manifest forbidden）

def test_registry_fast_transform_has_no_ratio_unsafe_check() -> None:
    """Task 2.1 改法：`_registry_fast_transform` 維持無欄名介面、其內不加判定（切片在呼叫點）。"""
    import inspect

    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    src = inspect.getsource(FeaturePreprocessor._registry_fast_transform)
    assert "ratio_unsafe" not in src and "feature_naming" not in src


def test_frame_path_taggers_untouched() -> None:
    """Task 1.3 不可做：既有標記器不改，不得改呼叫 feature_naming（FRAMEPATH 已刪 frame 整表標記
    `FeatureFactory._apply_timeframe_tag`、`MultiTFGenerator._apply_timeframe_tag`；保留之單欄標記器受檢）。"""
    import inspect

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    for fn_obj in (FeatureFactory._timeframe_tagged_name,):
        assert "feature_naming" not in inspect.getsource(fn_obj)
