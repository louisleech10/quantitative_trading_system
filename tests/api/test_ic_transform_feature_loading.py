"""IC transform 特徵來源選擇契約測試。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from api.services.ic_analysis_service import ICAnalysisService


def test_explicit_path_takes_priority_over_library(tmp_path) -> None:
    """明確 path 與 run selector 並存時固定讀 path（FF-NAME Task 3.4：path 須為 canonical run，經 library 以 path
    解析出之 run 載入，不用 selector 之 symbol／timeframe／config_hash）。"""
    from tests.feature_engineering.ffname_helpers import real_slice, write_canonical_run
    from tests.feature_engineering.ffstat_helpers import PRIMARY_TF, SYMBOL

    kline = real_slice(16)
    # V2 時間軸 sidecar 讀回為 naive UTC（epoch 秒）
    expected = pd.DataFrame({"alpha": kline["close"].to_numpy(dtype=float)},
                            index=pd.DatetimeIndex(kline.index).tz_convert("UTC").tz_localize(None))
    expected.index.name = "timestamp"
    library, features_path = write_canonical_run(tmp_path / "features", expected, SYMBOL, PRIMARY_TF, "path-hash")
    calls = []
    real_load = library.load

    def spy_load(symbol, timeframe, **kwargs):
        calls.append((symbol, timeframe, kwargs.get("config_hash")))
        return real_load(symbol, timeframe, **kwargs)

    library.load = spy_load
    service = ICAnalysisService()
    service._feature_library = library

    actual = service._load_features_for_transforms(
        "ETHUSDT",
        "12h",
        str(features_path),
        config_hash="pinned-hash",
    )

    pd.testing.assert_frame_equal(actual, expected, check_exact=True, check_dtype=True, check_freq=False)
    assert calls == [(SYMBOL, PRIMARY_TF, "path-hash")]


def test_library_load_receives_pinned_config_hash() -> None:
    """無 path 時將 pinned hash 原樣交給既有 library。"""
    expected = pd.DataFrame({"alpha": [1.0]})
    service = ICAnalysisService()
    service._feature_library = MagicMock()
    service._feature_library.load.return_value = expected

    actual = service._load_features_for_transforms(
        "BTCUSDT",
        "12h",
        None,
        config_hash="pinned-hash",
    )

    assert actual is expected
    service._feature_library.load.assert_called_once_with(
        "BTCUSDT",
        "12h",
        config_hash="pinned-hash",
    )


def test_library_load_receives_none_for_latest() -> None:
    """未指定 hash 時保留 library 的 latest 語意。"""
    expected = pd.DataFrame({"alpha": [1.0]})
    service = ICAnalysisService()
    service._feature_library = MagicMock()
    service._feature_library.load.return_value = expected

    actual = service._load_features_for_transforms("BTCUSDT", "12h", None)

    assert actual is expected
    service._feature_library.load.assert_called_once_with(
        "BTCUSDT",
        "12h",
        config_hash=None,
    )


def test_library_error_preserves_no_source_value_error() -> None:
    """Library 失敗且無 path 時維持既有無來源錯誤類型。"""
    service = ICAnalysisService()
    service._feature_library = MagicMock()
    service._feature_library.load.side_effect = KeyError("missing run")

    with pytest.raises(ValueError, match="Cannot load features"):
        service._load_features_for_transforms(
            "BTCUSDT",
            "12h",
            None,
            config_hash="missing-hash",
        )


def test_all_sources_missing_preserves_value_error() -> None:
    """所有來源欄位皆缺時維持既有 ValueError。"""
    service = ICAnalysisService()

    with pytest.raises(ValueError, match="Cannot load features"):
        service._load_features_for_transforms(None, None, None)


def test_apply_transforms_forwards_task_config_hash(monkeypatch) -> None:
    """Caller 會把 task 當時的 config hash 傳進來源 helper。"""
    service = ICAnalysisService()
    service._tasks["task"] = {
        "req_symbol": "BTCUSDT",
        "req_timeframe": "12h",
        "req_features_path": None,
        "req_config_hash": "pinned-hash",
    }
    load = MagicMock(side_effect=RuntimeError("stop-after-source-selection"))
    monkeypatch.setattr(service, "_load_features_for_transforms", load)

    with pytest.raises(RuntimeError, match="stop-after-source-selection"):
        service._apply_transforms_sync(
            "task",
            ["alpha"],
            rank=True,
            zscore=False,
            gaussian=False,
            rank_window=5,
            zscore_windows=[5],
        )

    load.assert_called_once_with(
        "BTCUSDT",
        "12h",
        None,
        config_hash="pinned-hash",
    )
