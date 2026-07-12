"""IC analysis service integration tests for run selector."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pandas as pd
import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis import ic_filter_orchestrator

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
# 2026-07-06 重凍:改用現行真實 12h run(取代已不在資料集的舊 1c4b825)。
HASH_A = "e53e22906c35363757f4cd49d27f973e"


class _SleepingAnalyzer:
    def analyze(self, **_kwargs):
        time.sleep(0.2)
        return {"summary_table": []}

    def analyze_cross_sectional(self, **_kwargs):
        time.sleep(0.2)
        return {"summary_table": []}


class _ProgressAnalyzer:
    def analyze(self, **kwargs):
        progress_callback = kwargs["progress_callback"]
        progress_callback({"stage": "ic_calculation", "progress": 0.5, "message": "worker tick"})
        return {"summary_table": []}


def _require_run() -> None:
    service = ICAnalysisService()
    if service._feature_library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")


# 第二刀首項 bug 已修(feature_library.load 貼回 row_index 時間軸,
# commit CUT2 ROWINDEX):xfail(strict) 移除=finding 閉合訊號。原 bug=物化 12h
# 特徵進切分驗證時 index 為位置整數→_validate_expected_frequency 誤判缺口 raise。
#
# 為何斷言在「切分驗證邊界」而非 full analyze 完成:full analyze 對此 run 的
# 218,369 特徵需 >17min(與本 bug 正交的效能/實資料遷移 epic 範疇)。本 bug 的
# 失敗點就是 _materialize_features_for_ic→h5 時間軸→_validate_expected_frequency;
# 在該邊界斷言即完整、可證偽閉合此 finding。mutation:還原 attach → h5 落 arange
# 偽時間軸 → 下方 assert(真時間軸 + 驗證不 raise)FAIL。
@pytest.mark.ic_persist_redirect
@pytest.mark.usefixtures("ic_persist_redirect")
def test_analyze_real_run_split_validation_passes_with_real_axis() -> None:
    _require_run()
    service = ICAnalysisService()
    features_path, _meta_path = service._materialize_features_for_ic(SYMBOL, TIMEFRAME, HASH_A)

    group_key = f"{SYMBOL}/{TIMEFRAME}"
    with h5py.File(features_path, "r") as file:
        timestamps = file[group_key]["timestamps"][:]

    # 真時間軸:非位置整數 arange(0,1,2,…);12h run 首兩點差 = 43200s。
    assert not np.array_equal(timestamps[:3], np.array([0, 1, 2])), (
        "materialized h5 仍是 arange 偽時間軸——attach 未生效"
    )
    assert int(timestamps[1] - timestamps[0]) == 12 * 3600

    index = pd.DatetimeIndex(pd.to_datetime(timestamps, unit="s"))
    expected_freq = ic_filter_orchestrator._resolve_expected_freq({"timeframe": TIMEFRAME})
    # 原 bug 就在此 raise;修後不得 raise。
    ic_filter_orchestrator._validate_expected_frequency(index, expected_freq)


@pytest.mark.ic_run_selector
@pytest.mark.ic_persist_redirect
@pytest.mark.usefixtures("ic_persist_redirect")
def test_resolve_run_path_contains_config_hash() -> None:
    _require_run()
    service = ICAnalysisService()
    entry = service._feature_library._registry.get(SYMBOL, TIMEFRAME, HASH_A)
    assert entry is not None
    features_path, _meta_path = service._materialize_features_for_ic(SYMBOL, TIMEFRAME, HASH_A)
    assert HASH_A in entry["hdf5_relative_path"]
    assert features_path.endswith(".h5")


@pytest.mark.asyncio
async def test_run_analysis_does_not_block_event_loop(monkeypatch) -> None:
    service = ICAnalysisService()
    analyzer = _SleepingAnalyzer()

    async def run_and_probe(task_id: str, request: ICAnalyzeRequest) -> None:
        service._tasks[task_id] = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "error": None,
            "result": None,
        }
        started = time.perf_counter()
        task = asyncio.create_task(service._run_analysis(task_id, analyzer, request, {}))
        await asyncio.sleep(0.02)
        elapsed = time.perf_counter() - started
        await task

        assert elapsed < 0.1
        assert service.get_task_status(task_id)["status"] == "completed"

    await run_and_probe(
        "longitudinal-task",
        ICAnalyzeRequest(features_path="features.h5", labels_path="labels.h5"),
    )

    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0],
            "label": [0.1, 0.2],
        },
        index=pd.Index([1, 2], name="timestamp"),
    )
    monkeypatch.setattr(
        service,
        "_feature_library",
        SimpleNamespace(load_multi=lambda *_args, **_kwargs: {"BTC": frame, "ETH": frame}),
    )

    await run_and_probe(
        "cross-sectional-task",
        ICAnalyzeRequest(
            mode="cross_sectional",
            symbols=["BTC", "ETH"],
            timeframe="12h",
            labels_path="labels.h5",
        ),
    )


@pytest.mark.asyncio
async def test_progress_callback_from_to_thread_schedules_on_event_loop() -> None:
    service = ICAnalysisService()
    task_id = "progress-task"
    scheduled: list[asyncio.Task] = []
    callback_errors: list[str] = []

    async def noop() -> None:
        return None

    def notification_callback(payload):
        if payload.get("status") != "running":
            return
        try:
            scheduled.append(asyncio.create_task(noop()))
        except RuntimeError as exc:
            callback_errors.append(str(exc))
            raise

    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "progress": 0.0,
        "error": None,
        "result": None,
    }
    service.register_notification_callback(task_id, notification_callback)

    await service._run_analysis(
        task_id,
        _ProgressAnalyzer(),
        ICAnalyzeRequest(features_path="features.h5", labels_path="labels.h5"),
        {},
    )
    await asyncio.sleep(0)

    assert callback_errors == []
    assert len(scheduled) == 1
    await scheduled[0]
    assert service.get_task_status(task_id)["status"] == "completed"


# ---------------------------------------------------------------------------
# CUT2 cross_sectional F1: _append_cross_sectional_labels datetime 對齊
# ---------------------------------------------------------------------------

XSEC_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
XSEC_TIMEFRAME = "12h"
XSEC_HASH = "e53e22906c35363757f4cd49d27f973e"
XSEC_MINI_REGISTRY = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


@pytest.fixture
def xsec_pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(XSEC_MINI_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


def _require_xsec_run(xsec_pinned_registry: Path) -> None:
    from momentum.factories import create_feature_library

    library = create_feature_library()
    for symbol in XSEC_SYMBOLS:
        if library._registry.get(symbol, XSEC_TIMEFRAME, XSEC_HASH) is None:
            pytest.skip(f"missing registry run {symbol}/{XSEC_HASH}")


def _build_xsec_cross_index() -> pd.DataFrame:
    """真 3sym×12h row_index 建 cross MultiIndex frame（輕量，不載 218k 特徵）。"""
    from momentum.factories import create_feature_library

    library = create_feature_library()
    frames: list[pd.DataFrame] = []
    for symbol in XSEC_SYMBOLS:
        row_index = library._reader.load_row_index_v2(
            symbol, XSEC_TIMEFRAME, XSEC_HASH, artifact_kind="raw"
        )
        if row_index is None:
            pytest.skip(f"missing row_index for {symbol}")
        idx = pd.DatetimeIndex(row_index)
        frame = pd.DataFrame({"feat_dummy": np.arange(len(idx), dtype=np.float32)}, index=idx)
        frame.index.name = "timestamp"
        frame["_symbol"] = symbol
        frames.append(frame)
    return pd.concat(frames, axis=0).set_index("_symbol", append=True)


def _kline_forward_log_oracle(symbol: str, timeframe: str, timestamps: pd.DatetimeIndex) -> pd.Series:
    """逐幣 kline close 手算 forward log-return oracle。"""
    from momentum.factories import create_kline_storage_manager

    kr = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
    raw = kr.read_klines(symbol, timeframe)
    close = raw["close"].copy()
    close.index = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s"))
    shifted = close.shift(-1)
    oracle = np.log(shifted / close).astype(np.float32)
    return oracle.reindex(timestamps)


@pytest.mark.ic_run_selector
def test_append_cross_sectional_labels_real_3sym_oracle(
    xsec_pinned_registry: Path,
) -> None:
    """F1 Golden: 真 3sym×12h return_1 逐幣對 kline oracle，覆蓋率 ≥5085/5088。"""
    _require_xsec_run(xsec_pinned_registry)
    cross_df = _build_xsec_cross_index()
    service = ICAnalysisService()
    labeled = service._append_cross_sectional_labels(cross_df, XSEC_SYMBOLS, XSEC_TIMEFRAME)

    total = len(labeled)
    non_nan = int(labeled["return_1"].notna().sum())
    assert non_nan >= 5085
    assert non_nan <= total

    for symbol in XSEC_SYMBOLS:
        mask = labeled.index.get_level_values("_symbol") == symbol
        sym_labels = labeled.loc[mask, "return_1"].droplevel("_symbol")
        oracle = _kline_forward_log_oracle(symbol, XSEC_TIMEFRAME, sym_labels.index)
        valid = sym_labels.notna().to_numpy() & oracle.notna().to_numpy()
        np.testing.assert_allclose(
            sym_labels.to_numpy(dtype=np.float32)[valid],
            oracle.to_numpy(dtype=np.float32)[valid],
            rtol=1e-5,
            atol=1e-5,
        )
        assert bool(pd.isna(sym_labels.iloc[-1]))

    t0 = labeled.index.get_level_values("timestamp").unique()[500]
    per_sym = {
        s: float(labeled.xs((t0, s), level=["timestamp", "_symbol"])["return_1"].iloc[0])
        for s in XSEC_SYMBOLS
    }
    assert len({round(v, 8) for v in per_sym.values()}) == len(XSEC_SYMBOLS)


@pytest.mark.ic_run_selector
def test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise(
    xsec_pinned_registry: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1 Option B: kline 缺孔 → 該列 label NaN、其餘對齊正確、不 raise。"""
    _require_xsec_run(xsec_pinned_registry)
    cross_df = _build_xsec_cross_index()
    service = ICAnalysisService()
    hole_symbol = XSEC_SYMBOLS[0]
    hole_ts = cross_df.xs(hole_symbol, level="_symbol").index[100]

    from momentum.factories import create_kline_storage_manager

    real_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
    original_read = real_reader.read_klines

    def read_klines_with_hole(symbol: str, timeframe: str):
        raw = original_read(symbol, timeframe)
        if symbol != hole_symbol:
            return raw
        hole_epoch = int(pd.Timestamp(hole_ts).timestamp())
        keep = raw["timestamp"].to_numpy() != hole_epoch
        return raw.loc[keep].reset_index(drop=True)

    monkeypatch.setattr(real_reader, "read_klines", read_klines_with_hole)
    monkeypatch.setattr(
        "api.services.ic_analysis_service.create_kline_storage_manager",
        lambda cache_dir="data_cache/feature_klines": real_reader,
    )

    labeled = service._append_cross_sectional_labels(cross_df, XSEC_SYMBOLS, XSEC_TIMEFRAME)
    sym_labels = labeled.xs(hole_symbol, level="_symbol")["return_1"]
    assert pd.isna(sym_labels.loc[hole_ts])

    def _holed_oracle(symbol: str, timestamps: pd.DatetimeIndex) -> pd.Series:
        raw = read_klines_with_hole(symbol, XSEC_TIMEFRAME)
        close = raw["close"].copy()
        close.index = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s"))
        shifted = close.shift(-1)
        oracle = np.log(shifted / close).astype(np.float32)
        return oracle.reindex(timestamps)

    for symbol in XSEC_SYMBOLS:
        mask = labeled.index.get_level_values("_symbol") == symbol
        sym_series = labeled.loc[mask, "return_1"].droplevel("_symbol")
        if symbol == hole_symbol:
            oracle = _holed_oracle(symbol, sym_series.index)
        else:
            oracle = _kline_forward_log_oracle(symbol, XSEC_TIMEFRAME, sym_series.index)
        valid = sym_series.notna().to_numpy() & oracle.notna().to_numpy()
        np.testing.assert_allclose(
            sym_series.to_numpy(dtype=np.float32)[valid],
            oracle.to_numpy(dtype=np.float32)[valid],
            rtol=1e-5,
            atol=1e-5,
        )

    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config

    orchestrator = ICFilterOrchestrator(load_ic_config())
    report = orchestrator.analyze_cross_sectional(
        labeled,
        timeframe=XSEC_TIMEFRAME,
        config_override={"ic_train_test_split": False},
    )
    assert "per_symbol_coverage" in report["metadata"]


@pytest.mark.ic_run_selector
def test_append_cross_sectional_labels_mutation_rangeindex_regresses(
    xsec_pinned_registry: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1 mutation: 還原 RangeIndex reindex → 覆蓋率回 0/5088（D-4 red-on-break）。"""
    _require_xsec_run(xsec_pinned_registry)
    cross_df = _build_xsec_cross_index()
    service = ICAnalysisService()
    original = service._append_cross_sectional_labels

    def broken_append(cross_df_in, symbols, timeframe):
        from momentum.factories import create_kline_storage_manager, create_label_generator

        kline_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
        label_generator = create_label_generator()
        working_df = cross_df_in.copy()
        symbol_level_idx = working_df.index.names.index("_symbol")
        for symbol in symbols:
            raw_data = kline_reader.read_klines(symbol, timeframe)
            label_series = label_generator.generate_returns_by_type(raw_data["close"], 1, "log")
            symbol_mask = working_df.index.get_level_values(symbol_level_idx) == symbol
            symbol_index = working_df.index[symbol_mask].droplevel(symbol_level_idx)
            working_df.loc[symbol_mask, "return_1"] = label_series.reindex(symbol_index).to_numpy()
        return working_df

    monkeypatch.setattr(service, "_append_cross_sectional_labels", broken_append)
    labeled = broken_append(cross_df, XSEC_SYMBOLS, XSEC_TIMEFRAME)
    assert int(labeled["return_1"].notna().sum()) == 0
    labeled_fixed = original(cross_df, XSEC_SYMBOLS, XSEC_TIMEFRAME)
    assert int(labeled_fixed["return_1"].notna().sum()) >= 5085


def test_cross_sectional_coverage_guard_short_series_all_nan() -> None:
    """F4 邊界: len_s==horizon 全 NaN → InvalidInputError（非靜默通過）。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.core.exceptions import InvalidInputError

    orchestrator = ICFilterOrchestrator(load_ic_config())
    timestamps = pd.date_range("2020-01-01", periods=1, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT"]
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    features = pd.DataFrame(
        {"alpha": np.random.randn(len(index)).astype(np.float32), "return_1": np.nan},
        index=index,
    )
    with pytest.raises(InvalidInputError, match="all-NaN|insufficient"):
        orchestrator.analyze_cross_sectional(
            features,
            config_override={"ic_train_test_split": False},
        )


def test_cross_sectional_coverage_guard_all_nan_raises() -> None:
    """F4: 全 NaN label → InvalidInputError。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.core.exceptions import InvalidInputError

    orchestrator = ICFilterOrchestrator(load_ic_config())
    timestamps = pd.date_range("2020-01-01", periods=20, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    features = pd.DataFrame(
        {"alpha": np.random.randn(len(index)).astype(np.float32), "return_1": np.nan},
        index=index,
    )
    with pytest.raises(InvalidInputError, match="all-NaN|coverage too low"):
        orchestrator.analyze_cross_sectional(
            features,
            config_override={"ic_train_test_split": False},
        )


def test_cross_sectional_coverage_guard_one_symbol_all_nan_raises() -> None:
    """F4 D-3: 1/3 幣全 NaN → per-symbol raise（全域平均會漏）。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.core.exceptions import InvalidInputError

    orchestrator = ICFilterOrchestrator(load_ic_config())
    timestamps = pd.date_range("2020-01-01", periods=20, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    labels = np.tile(np.linspace(0.01, 0.02, len(timestamps)), len(symbols)).astype(np.float32)
    labels[np.array(index.get_level_values("_symbol")) == "BCHUSDT"] = np.nan
    features = pd.DataFrame({"alpha": np.random.randn(len(index)).astype(np.float32), "return_1": labels}, index=index)
    with pytest.raises(InvalidInputError, match="BCHUSDT"):
        orchestrator.analyze_cross_sectional(
            features,
            config_override={"ic_train_test_split": False},
        )


def test_cross_sectional_coverage_guard_normal_passes_metadata() -> None:
    """F4: 正常覆蓋 → 不 raise 且 metadata 有 per_symbol_coverage。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config

    orchestrator = ICFilterOrchestrator(load_ic_config())
    timestamps = pd.date_range("2020-01-01", periods=20, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT"]
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    rng = np.random.default_rng(0)
    base = np.tile(np.linspace(0.01, 0.02, len(timestamps)), len(symbols))
    features = pd.DataFrame(
        {
            "alpha": (base + rng.normal(0, 0.001, len(index))).astype(np.float32),
            "return_1": base.astype(np.float32),
        },
        index=index,
    )
    features.loc[(features.index.get_level_values("timestamp")[-1], slice(None)), "return_1"] = np.nan
    report = orchestrator.analyze_cross_sectional(
        features,
        config_override={"ic_train_test_split": False},
    )
    assert "per_symbol_coverage" in report["metadata"]
    assert len(report["metadata"]["per_symbol_coverage"]) == 2
