"""IC analysis service integration tests for run selector."""

from __future__ import annotations

import asyncio
import time
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
