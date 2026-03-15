"""BatchDownload 多TF向後相容測試（P0-4d / 4-12）"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from api.models.case_models import BatchDownloadRequest, CaseRecord
from api.services.batch_download_service import BatchDownloadService


class _DummyCaseStorage:
    def __init__(self, cases: list[CaseRecord]):
        self._cases = cases

    def get_cases(self, case_ids=None):
        return self._cases


class _DummyRegistry:
    def register(self, *_args, **_kwargs):
        return None


class _DummyDownloadService:
    def __init__(self):
        self.calls: list[str] = []
        self.registry = _DummyRegistry()

    def download_klines(self, source, symbol, start_time, end_time, timeframe, save_to_storage):
        self.calls.append(timeframe)
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        mid_ts = start_ts + max((end_ts - start_ts) // 2, 1)
        return pd.DataFrame(
            {
                "timestamp": [start_ts, mid_ts, end_ts],
                "open": [1.0, 1.1, 1.2],
                "high": [1.2, 1.3, 1.4],
                "low": [0.9, 1.0, 1.1],
                "close": [1.1, 1.2, 1.3],
                "volume": [100.0, 110.0, 120.0],
                "taker_buy_volume": [50.0, 55.0, 60.0],
                "taker_ratio": [0.5, 0.5, 0.5],
            }
        )


class _DummyKlineStorage:
    def get_metadata(self, symbol, timeframe):
        return None

    def read_klines(self, symbol, timeframe, start_ts=None, end_ts=None, validate_continuity=False):
        ts_start = start_ts if start_ts is not None else int(datetime(2025, 1, 1).timestamp())
        ts_end = end_ts if end_ts is not None else ts_start + 7200
        ts_mid = ts_start + max((ts_end - ts_start) // 2, 1)
        return pd.DataFrame(
            {
                "timestamp": [ts_start, ts_mid, ts_end],
                "open": [1.0, 1.1, 1.2],
                "high": [1.2, 1.3, 1.4],
                "low": [0.9, 1.0, 1.1],
                "close": [1.1, 1.2, 1.3],
                "volume": [100.0, 110.0, 120.0],
                "taker_buy_volume": [50.0, 55.0, 60.0],
                "taker_ratio": [0.5, 0.5, 0.5],
            }
        )

    def validate_range_continuity(self, symbol, timeframe, start_ts, end_ts):
        return True, None

    def update_metadata(self, **kwargs):
        return None


def test_batch_download_request_backward_compatible_with_string_timeframe():
    request = BatchDownloadRequest(timeframe="12h", lookback_bars=10, forward_bars=5)
    assert request.timeframe == ["12h"]


def test_batch_download_request_accepts_multi_timeframe_list():
    request = BatchDownloadRequest(timeframe=["1h", "4h", "12h"], lookback_bars=10, forward_bars=5)
    assert request.timeframe == ["1h", "4h", "12h"]


def test_batch_download_request_rejects_invalid_timeframe():
    with pytest.raises(ValueError):
        BatchDownloadRequest(timeframe=["2h"], lookback_bars=10, forward_bars=5)


@pytest.mark.asyncio
async def test_execute_batch_download_processes_each_timeframe_sequentially():
    case = CaseRecord(
        case_id="BTCUSDT_1735689600_1",
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=int(datetime(2025, 1, 1, 0, 0, 0).timestamp()),
        positive_case=1,
    )

    request = BatchDownloadRequest(
        case_ids=None,
        lookback_bars=10,
        forward_bars=5,
        warmup_bars=0,
        force_redownload=True,
        timeframe=["1h", "4h"],
    )

    dummy_case_storage = _DummyCaseStorage([case])
    dummy_kline_storage = _DummyKlineStorage()
    dummy_download_service = _DummyDownloadService()

    service = BatchDownloadService(
        case_storage=dummy_case_storage,
        kline_storage=dummy_kline_storage,
        download_service=dummy_download_service,
    )

    task_id = service.create_download_task(request)
    result = await service.execute_batch_download(task_id, request)
    progress = service.get_progress(task_id)

    assert dummy_download_service.calls == ["1h", "4h"]
    assert progress is not None
    assert progress.progress_percent == 100.0
    assert result.total_cases == 2
