from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import AlignmentMeta, ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import CURRENT_MTF_ALIGN_VERSION, TimeframeAligner


HOUR = 3600
NS = 1_000_000_000


def _ms(index: pd.DatetimeIndex) -> pd.Series:
    return pd.Series((index.view("int64") // 1_000_000).astype(np.int64))


def test_asof_source_close_rule() -> None:
    source_s = np.array([0, 12 * HOUR, 24 * HOUR], dtype=np.int64)
    primary_s = np.arange(0, 37 * HOUR, HOUR, dtype=np.int64)

    open_idx = TimeframeAligner.build_asof_index_map(
        primary_s,
        source_s,
        source_dur_ns=12 * HOUR * NS,
        primary_dur_ns=HOUR * NS,
        mode="open_time",
    )
    close_idx = TimeframeAligner.build_asof_index_map(
        primary_s,
        source_s,
        source_dur_ns=12 * HOUR * NS,
        primary_dur_ns=HOUR * NS,
        mode="close_time",
    )

    assert open_idx[0] == -1
    assert open_idx[11] == -1
    assert open_idx[12] == 0
    assert open_idx[23] == 0
    assert open_idx[24] == 1
    assert close_idx[10] == -1
    assert close_idx[11] == 0
    assert close_idx[23] == 1

    warmup = TimeframeAligner.build_asof_index_map(
        np.array([0, HOUR], dtype=np.int64),
        np.array([12 * HOUR], dtype=np.int64),
        source_dur_ns=12 * HOUR * NS,
        primary_dur_ns=HOUR * NS,
        mode="open_time",
    )
    np.testing.assert_array_equal(warmup, np.array([-1, -1], dtype=np.int64))


def test_searchsorted_eq_mergeasof(monkeypatch: pytest.MonkeyPatch) -> None:
    source_index = pd.date_range("2026-01-01", periods=6, freq="12h")
    primary_index = pd.date_range("2026-01-01", periods=72, freq="1h")
    source_df = pd.DataFrame({"feature": np.arange(len(source_index), dtype=np.float32)}, index=source_index)
    primary_ts = _ms(primary_index)

    outputs = []
    for flag in ("0", "1"):
        monkeypatch.setenv("FFACT_USE_SEARCHSORTED", flag)
        outputs.append(
            TimeframeAligner.align_to_primary(
                source_df,
                "12h",
                primary_ts,
                "1h",
                alignment_mode=AlignmentMode.OPEN_MINUS,
            )
        )

    np.testing.assert_allclose(outputs[0].to_numpy(), outputs[1].to_numpy(), equal_nan=True)


class _Timeframes:
    def __init__(self, primary: str, training: list[str], mode: AlignmentMode = AlignmentMode.OPEN_MINUS) -> None:
        self.primary = primary
        self.training = training
        self.alignment_mode = mode


class _Config:
    def __init__(self, primary: str, training: list[str], mode: AlignmentMode = AlignmentMode.OPEN_MINUS) -> None:
        self.timeframes = _Timeframes(primary, training, mode)
        self.preprocessing = SimpleNamespace(enabled=False)


def test_multitf_durations_and_updown(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int, str]] = []
    original = TimeframeAligner.build_asof_index_map

    def _spy(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode):
        calls.append((int(source_dur_ns), int(primary_dur_ns), str(mode)))
        return original(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode)

    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_spy))

    down = MultiTFGenerator.__new__(MultiTFGenerator)
    down._primary_tf = "1h"
    down._config = _Config("1h", ["1h", "12h"])
    down._alignment_params_or_raise("12h")

    up = MultiTFGenerator.__new__(MultiTFGenerator)
    up._primary_tf = "12h"
    up._config = _Config("12h", ["12h", "1h"])
    up._alignment_params_or_raise("1h")

    TimeframeAligner.build_asof_index_map(
        np.array([12 * HOUR], dtype=np.int64),
        np.array([0], dtype=np.int64),
        *down._alignment_params_or_raise("12h"),
    )
    TimeframeAligner.build_asof_index_map(
        np.array([12 * HOUR], dtype=np.int64),
        np.arange(12, dtype=np.int64) * HOUR,
        *up._alignment_params_or_raise("1h"),
    )

    assert calls == [
        (12 * HOUR * NS, HOUR * NS, "open_time"),
        (HOUR * NS, 12 * HOUR * NS, "open_time"),
    ]

    invalid = MultiTFGenerator.__new__(MultiTFGenerator)
    invalid._primary_tf = "2h"
    invalid._config = _Config("2h", ["45m"])
    with pytest.raises(ValueError, match="Non-divisible"):
        invalid._alignment_params_or_raise("45m")


def test_hash_changes_with_align_version() -> None:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._adapter_registry = SimpleNamespace(get_last_timestamp=lambda symbol, timeframe: 123)
    config = SimpleNamespace(
        model_dump=lambda by_alias=True: {
            "timeframes": {"training": ["12h", "1h"], "alignment_mode": "open_minus"},
        }
    )

    new_hash = factory._compute_config_hash(config, "BTCUSDT", "1h")
    old_payload = config.model_dump(by_alias=True)
    old_payload["timeframes"]["training"] = sorted(old_payload["timeframes"]["training"])
    old_payload["_kline_last_ts"] = 123
    old_payload["_start_date"] = None
    old_payload["_end_date"] = None
    old_payload["_timeframe"] = "1h"
    old_hash = hashlib.md5(json.dumps(old_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    assert new_hash != old_hash


def test_resume_rejects_stale_idxmap(tmp_path: Path) -> None:
    registry = ColumnGroupRegistry(tmp_path / "work")
    data_path = registry.work_dir / "12h_L1_test.npy"
    idx_path = registry.work_dir / ".align_12h_to_1h_open_minus.npy"
    np.save(data_path, np.ones((2, 1), dtype=np.float32), allow_pickle=False)
    np.save(idx_path, np.array([-1, 0, 0], dtype=np.int32), allow_pickle=False)
    registry.register(
        ColumnGroup(
            group_id="12h_L1_test",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("x",),
            shape=(3, 1),
            disk_path=data_path,
            alignment=AlignmentMeta(
                source_timeframe="12h",
                primary_timeframe="1h",
                source_n_rows=2,
                primary_n_rows=3,
                idx_map_path=idx_path,
                alignment_mode="open_minus",
                align_algo_version=CURRENT_MTF_ALIGN_VERSION - 1,
            ),
        )
    )

    assert not MultiTFGenerator._tf_alignment_version_current(registry, "12h", (LayerSource.L1,))
    MultiTFGenerator._drop_timeframe_groups_from_registry(registry, "12h", (LayerSource.L1,))
    assert not registry.has_layers_for_timeframe("12h", (LayerSource.L1,))
