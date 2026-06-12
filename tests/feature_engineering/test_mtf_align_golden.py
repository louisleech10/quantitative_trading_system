from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

from tests._helpers.stub_layer_execute import (
    stub_execute_layer1_6,
    stub_layer_data,
    stub_spill_to_memmap,
)


HOUR = 3600
NS = 1_000_000_000
KLINE_CACHE = Path("data_cache/feature_klines/kline_cache.h5")
GOLDEN_START = "2026-01-01"
GOLDEN_END = "2026-01-03"
OPEN_12H_0000_CLOSE = 88024.640625
OPEN_12H_1200_CLOSE = 88839.0390625


class _Timeframes:
    def __init__(self, primary: str, training: list[str], mode: AlignmentMode) -> None:
        self.primary = primary
        self.training = training
        self.alignment_mode = mode


class _Config:
    def __init__(self, primary: str, training: list[str], mode: AlignmentMode) -> None:
        self.timeframes = _Timeframes(primary, training, mode)
        self.preprocessing = SimpleNamespace(enabled=False)


class _RealLayer0Factory:
    """Minimal factory that preserves the real HDF5 _layer0 timestamp/index contract."""

    def __init__(self, cache_path: Path, *, cgsa_work_dir: Path | None = None) -> None:
        self._cache_path = cache_path
        self._current_timeframe = "1h"
        self._cgsa_registry = (
            ColumnGroupRegistry(cgsa_work_dir, memory_buffer_groups=0)
            if cgsa_work_dir is not None
            else None
        )

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del config
        with h5py.File(self._cache_path, "r") as handle:
            arr = handle[f"{symbol}/{timeframe}/data"][:]
        df = pd.DataFrame.from_records(arr)
        df = df.set_index("timestamp", drop=True).sort_index()
        if start_date is not None or end_date is not None:
            dt = pd.to_datetime(df.index.to_numpy(dtype=np.int64), unit="s")
            mask = np.ones(len(df), dtype=bool)
            if start_date is not None:
                mask &= np.asarray(dt >= pd.Timestamp(start_date))
            if end_date is not None:
                mask &= np.asarray(dt <= pd.Timestamp(end_date))
            df = df.loc[mask]
        return df

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    def _execute_layer1_6_preserve_dtype(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

    def _layer1_atomic_indicators(self, data, config):
        del config
        timeframe = str(self._current_timeframe)
        column = f"close_{timeframe}_raw" if self._cgsa_registry is not None else "close_raw"
        frame = pd.DataFrame({column: data["close"].to_numpy(dtype=np.float32)}, index=data.index)
        if self._cgsa_registry is not None:
            group = ColumnGroup(
                group_id=f"{timeframe}_L1_close_raw",
                layer=LayerSource.L1,
                timeframe=timeframe,
                data_source="close",
                indicator="RAW",
                columns=(column,),
                shape=frame.shape,
            )
            self._cgsa_registry.save_data(group, frame.to_numpy(dtype=np.float32))
        return frame

    def _layer2_derived_features(self, layer1, data, config):
        return pd.DataFrame(index=layer1.index)

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        return pd.DataFrame(index=layer1.index)

    def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
        return pd.DataFrame(index=layer1.index)

    def _layer5_cross_sectional(self, layer1, layer2, config):
        return pd.DataFrame(index=layer1.index)

    def _layer6_meta_features(self, layer1, layer2, data, config):
        return pd.DataFrame(index=layer1.index)

    def _layer6_5_preprocessing(self, all_features, config):
        return all_features

    def _combine_layers(self, layers, context="unknown"):
        valid = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid:
            return pd.DataFrame()
        combined = pd.concat(valid, axis=1)
        return combined.loc[:, ~combined.columns.duplicated(keep="first")]

    def _compute_config_hash(self, config, symbol=None, timeframe=None, start_date=None, end_date=None):
        return "golden"

    @staticmethod
    def _cgsa_enabled() -> bool:
        return True

    def _persist_layer_output_groups(self, frame, layer, label):
        del frame, layer, label

    def _layer7_raw_from_cgsa_pipeline(
        self,
        symbol,
        timeframe,
        raw_data,
        config,
        elapsed,
        config_hash,
        compute_warnings=None,
        persist: bool = True,
    ):
        del symbol, timeframe, config, compute_warnings, persist
        if self._cgsa_registry is None:
            raise ValueError("CGSA registry missing in golden test factory")
        frames = []
        for group_id, group in self._cgsa_registry.iter_all():
            data = np.asarray(self._cgsa_registry.load_data(group_id), dtype=np.float32)
            frames.append(pd.DataFrame(data, index=raw_data.index, columns=list(group.columns)))
        features_df = pd.concat(frames, axis=1).loc[:, lambda frame: ~frame.columns.duplicated(keep="first")]
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"config_hash": config_hash},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
        )

    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash):
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"config_hash": config_hash},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
        )


def test_before_baseline_shows_lookahead() -> None:
    before = json.loads(Path("tests/_golden/mtf_align/before.json").read_text())
    assert before["1h@12:00"] == 91729


@pytest.fixture(autouse=True)
def _require_real_kline_cache() -> None:
    if not KLINE_CACHE.exists():
        pytest.skip(f"golden kline cache missing: {KLINE_CACHE}")


def _run_real_generate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    primary: str,
    training: list[str],
    mode: AlignmentMode,
    use_searchsorted: bool,
    use_cgsa: bool,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    monkeypatch.setenv("FFACT_USE_CGSA", "1" if use_cgsa else "0")
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1" if use_searchsorted else "0")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / f"cgsa_{primary}_{mode.value}_{use_cgsa}_{use_searchsorted}"))
    captures: list[dict[str, object]] = []
    original = TimeframeAligner.build_asof_index_map

    def _capture(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode):
        idx_map = original(primary_ts, source_ts, source_dur_ns, primary_dur_ns, mode)
        captures.append(
            {
                "primary_ts": np.asarray(primary_ts, dtype=np.int64).copy(),
                "source_ts": np.asarray(source_ts, dtype=np.int64).copy(),
                "source_dur_ns": int(source_dur_ns),
                "primary_dur_ns": int(primary_dur_ns),
                "mode": str(mode),
                "idx_map": idx_map.copy(),
            }
        )
        return idx_map

    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capture))
    factory = _RealLayer0Factory(KLINE_CACHE, cgsa_work_dir=tmp_path / "registry" if use_cgsa else None)
    generator = MultiTFGenerator(factory, _Config(primary, training, mode))
    result = generator.generate_multi_tf("BTCUSDT", start_date=GOLDEN_START, end_date=GOLDEN_END)
    return result.features_df, captures


def _assert_no_lookahead(capture: dict[str, object]) -> None:
    idx_map = capture["idx_map"]
    valid = idx_map >= 0
    source_close = capture["source_ts"][idx_map[valid]] + int(capture["source_dur_ns"]) // NS
    decision = capture["primary_ts"][valid]
    if capture["mode"] == "close_time":
        decision = decision + int(capture["primary_dur_ns"]) // NS
    assert np.all(source_close <= decision)


def _value_at(df: pd.DataFrame, timestamp: str, column: str) -> float:
    epoch_s = int(pd.Timestamp(timestamp).timestamp())
    return float(df.loc[epoch_s, column])


def _assert_down_open_after_exact(df: pd.DataFrame) -> None:
    for hour in range(12, 23):
        assert _value_at(df, f"2026-01-01 {hour:02d}:00:00", "close_12h_raw") == OPEN_12H_0000_CLOSE
    assert _value_at(df, "2026-01-01 23:00:00", "close_12h_raw") == OPEN_12H_0000_CLOSE
    assert _value_at(df, "2026-01-02 00:00:00", "close_12h_raw") == OPEN_12H_1200_CLOSE


def _assert_down_close_after_exact(df: pd.DataFrame) -> None:
    assert _value_at(df, "2026-01-01 23:00:00", "close_12h_raw") == OPEN_12H_1200_CLOSE


def test_real_generate_down_open_close_and_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    open_df, open_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.OPEN_MINUS,
        use_searchsorted=True,
        use_cgsa=False,
    )
    assert not open_df.empty
    assert open_captures
    _assert_no_lookahead(open_captures[0])
    assert open_captures[0]["idx_map"][0] == -1
    assert np.flatnonzero(open_captures[0]["idx_map"] >= 0)[0] == 12
    assert _value_at(open_df, "2026-01-01 12:00:00", "close_12h_raw") != 91729
    _assert_down_open_after_exact(open_df)

    close_df, close_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.CLOSE_TIME,
        use_searchsorted=True,
        use_cgsa=False,
    )
    assert not close_df.empty
    _assert_no_lookahead(close_captures[0])
    assert np.flatnonzero(close_captures[0]["idx_map"] >= 0)[0] == 11
    _assert_down_close_after_exact(close_df)


def test_real_generate_up_and_path_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    outputs = []
    for use_cgsa in (False, True):
        for use_searchsorted in (False, True):
            df, captures = _run_real_generate(
                monkeypatch,
                tmp_path,
                primary="12h",
                training=["12h", "1h"],
                mode=AlignmentMode.OPEN_MINUS,
                use_searchsorted=use_searchsorted,
                use_cgsa=use_cgsa,
            )
            assert not df.empty
            if use_cgsa or use_searchsorted:
                assert captures
                _assert_no_lookahead(captures[0])
            outputs.append(df)

    pd.testing.assert_frame_equal(outputs[0], outputs[1], check_dtype=False)
    pd.testing.assert_frame_equal(outputs[2], outputs[3], check_dtype=False)


def test_real_generate_down_cgsa_path_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    outputs = []
    for use_searchsorted in (False, True):
        df, captures = _run_real_generate(
            monkeypatch,
            tmp_path,
            primary="12h",
            training=["12h", "1h"],
            mode=AlignmentMode.OPEN_MINUS,
            use_searchsorted=use_searchsorted,
            use_cgsa=True,
        )
        assert not df.empty
        assert captures
        _assert_no_lookahead(captures[0])
        outputs.append(df)

    pd.testing.assert_frame_equal(outputs[0], outputs[1], check_dtype=False)
