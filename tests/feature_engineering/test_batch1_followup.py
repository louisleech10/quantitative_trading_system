from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.feature_factory as feature_factory_module
from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.utils.layer_ids import (
    qualify_failed_layer_id,
    qualify_failed_layer_ids,
)
from momentum.FeatureEngineering.feature_validator import FeatureValidator
from momentum.FeatureEngineering.utils.nan_stats import (
    ColumnNanAccumulator,
    abnormal_nan_count,
)
from momentum.FeatureEngineering.utils.winsor_params import resolve_winsor_min_periods
from momentum.factories import create_feature_factory


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests/_golden/batch1_followup/baseline.json"
MAX_NAN_RATIO_ORACLE_PATH = REPO_ROOT / "tests/_golden/failopen/max_nan_ratio.json"
MAX_NAN_RATIO_RESOURCE_PATH = (
    REPO_ROOT / "momentum/FeatureEngineering/_resources/max_nan_ratio.json"
)


def _load_baseline() -> dict[str, object]:
    if not BASELINE_PATH.exists():
        pytest.fail(f"Batch1 follow-up baseline missing: {BASELINE_PATH}")
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        pytest.fail(f"Batch1 follow-up baseline unreadable: {exc}")


def _winsor_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(20260612)
    values = rng.standard_normal((1_000, 3)).astype(np.float32)
    values[:60, 0] = np.nan
    values[400:405, 1] = np.nan
    values[250, 2] = 8.0 * float(np.nanstd(values[:, 2]))
    values[750, 2] = -8.0 * float(np.nanstd(values[:, 2]))
    return pd.DataFrame(values, columns=["leading", "mid_hole", "outliers"])


def _hash_array(values: np.ndarray) -> tuple[str, str]:
    mask = np.isnan(values)
    normalized = np.where(mask, 0.0, values).astype(np.float64)
    return (
        hashlib.sha256(normalized.tobytes()).hexdigest(),
        hashlib.sha256(mask.tobytes()).hexdigest(),
    )


def _nan_reference_cases() -> dict[str, np.ndarray]:
    leading = np.arange(50, dtype=np.float64)[:, None]
    leading[:30] = np.nan
    trailing = np.arange(50, dtype=np.float64)[:, None]
    trailing[-30:] = np.nan
    mid_hole = np.arange(50, dtype=np.float64)[:, None]
    mid_hole[20:27] = np.nan
    cross_chunk = np.arange(700, dtype=np.float64)[:, None]
    cross_chunk[333:] = np.nan
    return {
        "empty": np.empty((0, 1), dtype=np.float64),
        "all_nan": np.full((50, 1), np.nan, dtype=np.float64),
        "leading_only": leading,
        "trailing_only": trailing,
        "mid_hole": mid_hole,
        "cross_chunk": cross_chunk,
    }


class TestGolden:
    def test_golden_baseline_is_readable_and_complete(self) -> None:
        baseline = _load_baseline()
        required = {
            "winsor_default_value_hash",
            "winsor_default_mask_hash",
            "winsor_w100_value_hash",
            "winsor_w100_mask_hash",
            "winsor_w100_min_periods",
            "max_nan_ratio_btc_12h",
            "nan_stats_reference",
            "perf_wall_seconds",
            "perf_peak_bytes",
        }
        assert required <= baseline.keys()
        assert set(baseline["nan_stats_reference"]) == {
            "empty",
            "all_nan",
            "leading_only",
            "trailing_only",
            "mid_hole",
            "cross_chunk",
        }

    def test_golden_default_winsor_matches_public_validator(self) -> None:
        baseline = _load_baseline()
        frame = _winsor_fixture()
        result = SimpleNamespace(
            features_df=frame.copy(),
            feature_count=frame.shape[1],
            config_used={},
        )
        FeatureValidator().validate_factory_output(result)
        value_hash, mask_hash = _hash_array(result.features_df.to_numpy())
        assert value_hash == baseline["winsor_default_value_hash"]
        assert mask_hash == baseline["winsor_default_mask_hash"]

    def test_golden_max_nan_ratio_matches_head(self) -> None:
        baseline = _load_baseline()
        assert FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h") == baseline[
            "max_nan_ratio_btc_12h"
        ]


class TestN4:
    def test_n4_resource_matches_golden_and_baseline(self) -> None:
        baseline = _load_baseline()
        assert FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h") == baseline[
            "max_nan_ratio_btc_12h"
        ]
        assert hashlib.sha256(MAX_NAN_RATIO_ORACLE_PATH.read_bytes()).digest() == (
            hashlib.sha256(MAX_NAN_RATIO_RESOURCE_PATH.read_bytes()).digest()
        )

    def test_n4_missing_resource_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            feature_factory_module,
            "_MAX_NAN_RATIO_ARTIFACT_PATH",
            tmp_path / "missing.json",
        )
        with pytest.raises(RuntimeError, match="artifact unavailable"):
            FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h")

    @pytest.mark.parametrize(
        "payload, expected",
        [
            ("{not-json", "artifact unavailable"),
            ('{"schema_version": 1}', "artifact has no observed ratios"),
        ],
    )
    def test_n4_invalid_resource_fails_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        payload: str,
        expected: str,
    ) -> None:
        artifact = tmp_path / "max_nan_ratio.json"
        artifact.write_text(payload, encoding="utf-8")
        monkeypatch.setattr(
            feature_factory_module, "_MAX_NAN_RATIO_ARTIFACT_PATH", artifact
        )
        with pytest.raises(RuntimeError, match=expected):
            FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h")


class TestNanStats:
    def test_nan_stats_matches_frozen_reference(self) -> None:
        reference = _load_baseline()["nan_stats_reference"]
        for name, values in _nan_reference_cases().items():
            assert abnormal_nan_count(values) == reference[name]
        assert abnormal_nan_count(np.full((50, 1), np.nan)) == 50
        assert abnormal_nan_count(np.array([[np.nan]])) == 1

    def test_nan_stats_accumulator_matches_batch_calculation(self) -> None:
        rng = np.random.default_rng(20260612)
        for _ in range(200):
            row_count = int(rng.integers(0, 500))
            mask = rng.random(row_count) < rng.uniform(0.0, 0.7)
            split_a = row_count // 3
            split_b = 2 * row_count // 3
            accumulator = ColumnNanAccumulator()
            for chunk in (mask[:split_a], mask[split_a:split_b], mask[split_b:]):
                accumulator.update(chunk)
            values = np.where(mask, np.nan, 1.0)[:, None]
            assert accumulator.abnormal() == abnormal_nan_count(values)
            assert accumulator.total == row_count

    def test_nan_stats_rejects_non_column_mask(self) -> None:
        with pytest.raises(ValueError, match="must be 1D"):
            ColumnNanAccumulator().update(np.zeros((2, 2), dtype=bool))


def _write_n6_case(tmp_path: Path, name: str, values: np.ndarray) -> dict[str, object]:
    registry = ColumnGroupRegistry(tmp_path / f"{name}-registry", memory_buffer_groups=0)
    data = values.astype(np.float32, copy=False)[:, None]
    registry.save_data(
        ColumnGroup(
            group_id=f"12h_L2_{name}",
            layer=LayerSource.L2,
            timeframe="12h",
            data_source="test",
            indicator=name,
            columns=(name,),
            shape=data.shape,
            dtype="float32",
        ),
        data,
    )
    storage = FeatureStorage(str(tmp_path / f"{name}-features"))
    _, summary = storage.write_raw_from_registry_stream(
        symbol="BTCUSDT",
        tf="12h",
        config_hash=name,
        registry=registry,
        preprocessor=None,
        n_workers=1,
        cleanup_intermediate=False,
        l65_mode="none",
    )
    return summary["validation"]


class TestN6:
    def test_n6_stream_nan_ratio_drives_warmup_aware_gate(self, tmp_path: Path) -> None:
        warmup = np.arange(400, dtype=np.float32)
        warmup[:80] = np.nan
        mid_hole = np.arange(400, dtype=np.float32)
        # 72 / 400 = 0.18 > BTCUSDT/12h baseline threshold 0.163461...
        mid_hole[164:236] = np.nan

        warmup_validation = _write_n6_case(tmp_path, "warmup", warmup)
        mid_hole_validation = _write_n6_case(tmp_path, "mid_hole", mid_hole)

        assert warmup_validation["nan_ratio"] == 0.0
        assert mid_hole_validation["nan_ratio"] == pytest.approx(72 / 400)

        factory = object.__new__(FeatureFactory)
        warmup_metadata = {"quality_status": "complete", "run_status": "complete"}
        mid_hole_metadata = {"quality_status": "complete", "run_status": "complete"}
        config = {"max_inf_ratio": 0.0, "max_nan_ratio": None}
        factory._apply_runtime_quality_gate(
            warmup_metadata,
            config,
            "BTCUSDT",
            "12h",
            nan_ratio=float(warmup_validation["nan_ratio"]),
            inf_ratio=0.0,
        )
        factory._apply_runtime_quality_gate(
            mid_hole_metadata,
            config,
            "BTCUSDT",
            "12h",
            nan_ratio=float(mid_hole_validation["nan_ratio"]),
            inf_ratio=0.0,
        )
        assert warmup_metadata["quality_status"] == "complete"
        assert mid_hole_metadata["quality_status"] == "partial"

    def test_n6_missing_summary_key_warns_and_preserves_fallback(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("WARNING"):
            ratio = FeatureFactory._resolve_stream_nan_ratio({"coverage": 0.8})
        assert ratio == pytest.approx(0.2)
        assert "stream validation missing nan_ratio" in caplog.text


class TestN3:
    @staticmethod
    def _result(frame: pd.DataFrame, *, l65_applied: bool = False) -> SimpleNamespace:
        config_used = {
            "preprocessing": {
                "enabled": l65_applied,
                "winsorization": {"enabled": l65_applied},
            }
        }
        return SimpleNamespace(
            features_df=frame.copy(),
            feature_count=frame.shape[1],
            config_used=config_used,
        )

    def test_n3_public_validator_default_and_w100_match_baseline(self) -> None:
        baseline = _load_baseline()
        frame = _winsor_fixture()

        default_result = self._result(frame)
        FeatureValidator().validate_factory_output(default_result)
        assert _hash_array(default_result.features_df.to_numpy()) == (
            baseline["winsor_default_value_hash"],
            baseline["winsor_default_mask_hash"],
        )

        w100_result = self._result(frame)
        FeatureValidator().validate_factory_output(w100_result, winsor_window=100)
        assert resolve_winsor_min_periods(100) == baseline["winsor_w100_min_periods"]
        assert _hash_array(w100_result.features_df.to_numpy()) == (
            baseline["winsor_w100_value_hash"],
            baseline["winsor_w100_mask_hash"],
        )

    def test_n3_min_periods_prefix_and_l65_deduplication(self) -> None:
        frame = _winsor_fixture()
        original_prefix = frame.iloc[:24].to_numpy(copy=True)
        validator = FeatureValidator()
        result = self._result(frame)
        validator.validate_factory_output(result, winsor_window=100)
        np.testing.assert_equal(result.features_df.iloc[:24].to_numpy(), original_prefix)
        assert validator._last_winsorization_count == 1

        already_applied = self._result(frame, l65_applied=True)
        validator.validate_factory_output(already_applied, winsor_window=100)
        assert validator._last_winsorization_count == 0
        np.testing.assert_equal(already_applied.features_df.to_numpy(), frame.to_numpy())

    def test_n3_window_edges(self) -> None:
        assert resolve_winsor_min_periods(1) == 1
        short = pd.DataFrame({"x": [1.0, 100.0, 2.0]})
        output = FeatureValidator().winsorize(short, window=100)
        np.testing.assert_equal(output.to_numpy(), short.to_numpy())
        with pytest.raises(ValueError, match="must be positive"):
            FeatureValidator().winsorize(short, window=0)


class TestN7:
    def test_n7_canonicalizer_is_idempotent_and_preserves_order(self) -> None:
        entries = [
            "L3",
            "L3:boom",
            "L3:network:timeout",
            "L4:4h",
            "L4:4h:disk",
            "timeframe:1h",
        ]
        expected = [
            "L3:12h",
            "L3:12h:boom",
            "L3:12h:network:timeout",
            "L4:4h",
            "L4:4h:disk",
            "timeframe:1h",
        ]
        qualified = qualify_failed_layer_ids(entries, "12h")
        assert qualified == expected
        assert qualify_failed_layer_ids(qualified, "12h") == expected
        assert qualify_failed_layer_ids([], "12h") == []

    def test_n7_stream_legacy_and_worker_expected_lists(self) -> None:
        completeness = {"failed_layers": ["L3"], "failure_reasons": ["L3:boom"]}
        stream = qualify_failed_layer_ids(completeness["failed_layers"], "12h")
        legacy = qualify_failed_layer_ids(completeness["failure_reasons"], "12h")
        worker = qualify_failed_layer_ids(["L3", "L4:4h:disk"], "4h")
        assert stream == ["L3:12h"]
        assert legacy == ["L3:12h:boom"]
        assert worker == ["L3:4h", "L4:4h:disk"]
        assert qualify_failed_layer_id("timeframe:4h", "12h") == "timeframe:4h"


class TestT5:
    def test_t5_present_timeframes_preserves_training_order(self) -> None:
        generator = object.__new__(MultiTFGenerator)
        generator._training_tfs = ["12h", "1h", "4h"]
        assert generator._present_timeframes(["1h"]) == ["12h", "4h"]
        assert generator._present_timeframes(["12h", "1h", "4h"]) == []


@pytest.mark.slow
def test_perf_smoke_nan_stats_within_frozen_budget() -> None:
    baseline = _load_baseline()
    benchmark = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from scripts.freeze_batch1_baseline import run_stream_benchmark; "
                "wall, peak = run_stream_benchmark(); "
                "print(json.dumps({'wall': wall, 'peak': peak}))"
            ),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    metrics = json.loads(benchmark.stdout.strip().splitlines()[-1])
    wall = float(metrics["wall"])
    peak = int(metrics["peak"])
    assert wall <= float(baseline["perf_wall_seconds"]) * 1.15
    assert peak <= int(baseline["perf_peak_bytes"]) * 1.10

    mask = np.zeros(20_000_000, dtype=bool)
    mask[10_000_000:10_000_100] = True
    accumulator = ColumnNanAccumulator()
    ColumnNanAccumulator().update(np.array([False, True], dtype=bool))
    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        accumulator.update(mask)
        _, peak_after = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak_after - before < 1_024
    assert accumulator.abnormal() == 100


@pytest.mark.slow
def test_real_kline_stream_nan_ratio_matches_written_arrays(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kline_path = REPO_ROOT / "data_cache/feature_klines/kline_cache.h5"
    if not kline_path.is_file():
        pytest.fail(f"missing required real kline cache: {kline_path}")

    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    factory = create_feature_factory(
        cache_dir="data_cache/feature_klines", validate_continuity=False
    )
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override={
            "timeframes": {
                "primary": "12h",
                "training": ["12h"],
                "alignment_mode": "open_minus",
            },
            "data_sources": {
                "enabled_sources": ["close"],
                "synthetic_sources": [],
            },
            "preprocessing": {"enabled": False},
            "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        },
        force_regenerate=True,
        persist=True,
        start_date="2024-06-01",
        end_date="2024-12-01",
    )

    validation = result.metadata["validation"]
    assert "nan_ratio" in validation
    abnormal = 0
    total = 0
    parquet_paths = sorted(Path(result.metadata["raw_path"]).glob("*.parquet"))
    assert parquet_paths
    for parquet_path in parquet_paths:
        values = pd.read_parquet(parquet_path).to_numpy()
        abnormal += abnormal_nan_count(values)
        total += int(values.size)
    recomputed = float(abnormal / total) if total else 0.0
    assert float(validation["nan_ratio"]) == recomputed

    threshold = FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h")
    expected_status = "partial" if recomputed > threshold else "complete"
    assert result.metadata["quality_status"] == expected_status
