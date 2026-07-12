"""真 kline IC API fixture 的可證偽 PIT mutation 測試。"""

import pytest

from momentum.factories import create_kline_storage_manager
from tests.fixtures.ic_api_real_kline import SYMBOL, TIMEFRAME, build_real_kline_frames


@pytest.fixture(scope="module")
def real_kline():
    storage = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
    try:
        data = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    except Exception as exc:
        pytest.fail(f"requires_kline: failed reading {SYMBOL}/{TIMEFRAME}: {exc}")
    if data is None or data.empty:
        pytest.fail(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME}")
    return data


def test_feature_shift_negative_one_fails_self_test(real_kline) -> None:
    with pytest.raises(AssertionError, match="feature PIT oracle mismatch"):
        build_real_kline_frames(real_kline, feature_shift=-1)


def test_backward_label_fails_self_test(real_kline) -> None:
    with pytest.raises(Exception, match="label mismatch"):
        build_real_kline_frames(real_kline, backward_label=True)
