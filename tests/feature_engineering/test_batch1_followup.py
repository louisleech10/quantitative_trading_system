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


def _reference_incomplete_window_mask(values: np.ndarray, window: int) -> np.ndarray:
    """獨立參考（不呼叫生產 stable_mask）：FF-STAT b4 R6甲「窗未滿遮 NaN」——逐欄自首個有限值起 window−1 列
    （及其前）設 NaN；全 NaN 欄不變。"""
    out = np.array(values, copy=True)
    for col in range(out.shape[1]):
        finite = np.flatnonzero(np.isfinite(out[:, col]))
        if finite.size:
            out[: finite[0] + window - 1, col] = np.nan
    return out


def _validate_winsor(
    monkeypatch: pytest.MonkeyPatch, window: int | None, *, unmasked: bool
) -> np.ndarray:
    """公開驗證器之縮尾輸出；`unmasked=True` 時暫以 no-op 取代窗未滿遮罩（只為比對凍結 golden 之計算本身）。"""
    from momentum.FeatureEngineering.preprocessing import stable_mask

    frame = _winsor_fixture()
    result = SimpleNamespace(features_df=frame.copy(), feature_count=frame.shape[1], config_used={})
    with monkeypatch.context() as patch:
        if unmasked:
            patch.setattr(stable_mask, "mask_incomplete_window_inplace", lambda values, _w: values)
        if window is None:
            FeatureValidator().validate_factory_output(result)
        else:
            FeatureValidator().validate_factory_output(result, winsor_window=window)
    return result.features_df.to_numpy()


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

    def test_golden_default_winsor_matches_public_validator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # TESTREG 4.4：d229336e（FF-STAT b4 R6甲）起縮尾於窗未滿之列遮 NaN（設計變更）⇒ 凍結 hash 不再等於最終輸出。
        # 改為兩段：①遮罩前之縮尾計算仍逐位元等於凍結 golden（計算本身不變）；②最終輸出＝①＋獨立參考遮罩（窗 252）。
        baseline = _load_baseline()
        unmasked = _validate_winsor(monkeypatch, None, unmasked=True)
        value_hash, mask_hash = _hash_array(unmasked)
        assert value_hash == baseline["winsor_default_value_hash"]
        assert mask_hash == baseline["winsor_default_mask_hash"]
        final = _validate_winsor(monkeypatch, None, unmasked=False)
        np.testing.assert_array_equal(final, _reference_incomplete_window_mask(unmasked, 252))

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


def _write_n6_case(
    tmp_path: Path, name: str, values: np.ndarray, *, quality_gate: dict[str, object] | None = None
) -> dict[str, object]:
    """寫一欄經 CGSA 串流；`quality_gate` 給定時一併走生產品質閘（feature_storage.apply_quality_degradation），
    回傳 summary（含 validation 與 completeness）；否則回傳 validation（原行為）。"""
    from momentum.core.contracts import LayerExecutionResult, LayerStatus

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
    gate_kwargs: dict[str, object] = {}
    if quality_gate is not None:
        healthy = LayerExecutionResult(
            data=pd.DataFrame(), status=LayerStatus.ok, failed_engines=(), reason=None,
            configured_engines=1, present_engines=1, required_engines=0, dependency_error=False,
        )
        gate_kwargs = {
            "quality_gate": quality_gate,
            "layer_results": {f"Layer {idx}": healthy for idx in range(1, 7)},
        }
    _, summary = storage.write_raw_from_registry_stream(
        symbol="BTCUSDT",
        tf="12h",
        config_hash=name,
        registry=registry,
        preprocessor=None,
        n_workers=1,
        cleanup_intermediate=False,
        l65_mode="none",
        **gate_kwargs,
    )
    return summary if quality_gate is not None else summary["validation"]


class TestN6:
    def test_n6_stream_nan_ratio_drives_warmup_aware_gate(self, tmp_path: Path) -> None:
        warmup = np.arange(400, dtype=np.float32)
        warmup[:80] = np.nan
        mid_hole = np.arange(400, dtype=np.float32)
        # 72 / 400 = 0.18 > BTCUSDT/12h baseline threshold 0.163461...
        mid_hole[164:236] = np.nan

        # TESTREG 4.4：原後半驗 FeatureFactory._apply_runtime_quality_gate，該方法全庫 0 生產呼叫者
        # （feature_factory.py:3542）⇒ 生產閘壞不紅；改經串流寫入之生產品質閘（feature_storage.py:1215
        # apply_quality_degradation），門檻＝factory 政策層同源之 BTCUSDT/12h 預設 max_nan_ratio
        gate = {
            "max_inf_ratio": 0.0,
            "max_nan_ratio": FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h"),
        }
        assert 72 / 400 > gate["max_nan_ratio"] > 0.0
        warmup_summary = _write_n6_case(tmp_path, "warmup", warmup, quality_gate=gate)
        mid_hole_summary = _write_n6_case(tmp_path, "mid_hole", mid_hole, quality_gate=gate)

        assert warmup_summary["validation"]["nan_ratio"] == 0.0
        assert mid_hole_summary["validation"]["nan_ratio"] == pytest.approx(72 / 400)

        assert warmup_summary["completeness"]["quality_status"] == "complete"
        assert mid_hole_summary["completeness"]["quality_status"] == "partial"
        assert any(
            str(reason).startswith("nan_ratio=")
            for reason in mid_hole_summary["completeness"]["failure_reasons"]
        )

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

    def test_n3_public_validator_default_and_w100_match_baseline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # TESTREG 4.4：同 TestGolden——凍結 hash 比遮罩前之計算；最終輸出另比獨立參考遮罩（d229336e 設計變更）
        baseline = _load_baseline()

        default_unmasked = _validate_winsor(monkeypatch, None, unmasked=True)
        assert _hash_array(default_unmasked) == (
            baseline["winsor_default_value_hash"],
            baseline["winsor_default_mask_hash"],
        )
        np.testing.assert_array_equal(
            _validate_winsor(monkeypatch, None, unmasked=False),
            _reference_incomplete_window_mask(default_unmasked, 252),
        )

        w100_unmasked = _validate_winsor(monkeypatch, 100, unmasked=True)
        assert resolve_winsor_min_periods(100) == baseline["winsor_w100_min_periods"]
        assert _hash_array(w100_unmasked) == (
            baseline["winsor_w100_value_hash"],
            baseline["winsor_w100_mask_hash"],
        )
        np.testing.assert_array_equal(
            _validate_winsor(monkeypatch, 100, unmasked=False),
            _reference_incomplete_window_mask(w100_unmasked, 100),
        )

    def test_n3_min_periods_prefix_and_l65_deduplication(self) -> None:
        frame = _winsor_fixture()
        validator = FeatureValidator()
        result = self._result(frame)
        validator.validate_factory_output(result, winsor_window=100)
        # TESTREG 4.4：原斷言前 24 列（min_periods 前）保留原值；d229336e（FF-STAT b4 R6甲）起改為窗未滿遮 NaN——
        # 逐欄自首個有限值起 99 列設 NaN，之後輸入有限處輸出亦有限（不得多遮）、輸入 NaN 處仍為 NaN
        out = result.features_df.to_numpy()
        src = frame.to_numpy()
        for col in range(src.shape[1]):
            first = int(np.flatnonzero(np.isfinite(src[:, col]))[0])
            assert np.isnan(out[: first + 99, col]).all(), f"col {col}: 窗未滿之列未遮"
            tail_src = src[first + 99:, col]
            tail_out = out[first + 99:, col]
            np.testing.assert_array_equal(np.isfinite(tail_out), np.isfinite(tail_src))
        assert validator._last_winsorization_count == 1

        already_applied = self._result(frame, l65_applied=True)
        validator.validate_factory_output(already_applied, winsor_window=100)
        assert validator._last_winsorization_count == 0
        np.testing.assert_equal(already_applied.features_df.to_numpy(), frame.to_numpy())

    def test_n3_window_edges(self) -> None:
        assert resolve_winsor_min_periods(1) == 1
        short = pd.DataFrame({"x": [1.0, 100.0, 2.0]})
        # TESTREG 4.4：d229336e 起窗未滿之列遮 NaN（原期望「窗大於列數 ⇒ 原值不變」之前提已變）：
        # 窗 100 > 3 列 ⇒ 全遮；窗＝1 ⇒ 不遮且單點分位數夾住自身＝原值；窗＝3 ⇒ 前 2 列遮、末列 2.0 落在 {1,100,2} 之
        # 1%／99% 分位數內 ⇒ 原值
        output = FeatureValidator().winsorize(short, window=100)
        assert np.isnan(output.to_numpy()).all()
        np.testing.assert_equal(
            FeatureValidator().winsorize(short, window=1).to_numpy(),
            short.to_numpy(dtype=np.float32),
        )
        np.testing.assert_equal(
            FeatureValidator().winsorize(short, window=3).to_numpy(),
            np.array([[np.nan], [np.nan], [2.0]], dtype=np.float32),
        )
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
@pytest.mark.requires_kline
def test_real_kline_stream_nan_ratio_matches_written_arrays(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kline_path = REPO_ROOT / "data_cache/feature_klines/kline_cache.h5"
    if not kline_path.is_file():
        pytest.fail(f"missing required real kline cache: {kline_path}")

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
    # FFDSTAR Task 1.6：raw 群組檔依 run manifest 宣告（`declared_group_files`），不以檔名掃描 run 目錄
    from tests.feature_engineering import preprov_helpers as ph

    raw_path = Path(result.metadata["raw_path"])
    parquet_paths = sorted(ph.declared_group_files(raw_path.parent, raw_path.name))
    assert parquet_paths
    for parquet_path in parquet_paths:
        values = pd.read_parquet(parquet_path).to_numpy()
        abnormal += abnormal_nan_count(values)
        total += int(values.size)
    recomputed = float(abnormal / total) if total else 0.0
    assert float(validation["nan_ratio"]) == recomputed

    threshold = FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h")
    # TESTREG 4.4：原假設 quality_status 只由 nan_ratio 決定；FFTFMETA／FFSTAT 起降級原因另含 L6.5 失敗、d* 事件、
    # warmup_insufficient_history（feature_storage.apply_quality_degradation）⇒ 改為：nan 門檻原因出現與否
    # ＝重算比率是否超過門檻；且狀態與全部降級原因一致（有任一原因 ⇒ partial，無 ⇒ complete）
    reasons = [str(reason) for reason in result.metadata.get("failure_reasons", [])]
    nan_reasons = [reason for reason in reasons if reason.startswith("nan_ratio=")]
    assert bool(nan_reasons) == (recomputed > threshold), (recomputed, threshold, reasons)
    expected_status = "partial" if reasons else "complete"
    assert result.metadata["quality_status"] == expected_status, reasons
