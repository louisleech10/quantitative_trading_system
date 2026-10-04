"""ICFIRSTALIGN 乙 Task 3.1：FU-2 close carrier 接時間軸＋全 NaN 守衛（docs/ICFIRSTALIGN_SPEC.md v18）。

現況（收據 handoffs/run_receipts/20261004-icfirstalign-fu2-close-carrier.json）：正常 production 路徑 carrier 恆全 NaN
（kline 讀回為 RangeIndex、以位置索引直接 reindex 到 DatetimeIndex）。修法：單一實作 `_build_close_carrier`
（經 `_normalize_frame_time_index` 依時間戳 reindex）＋守衛 `_validate_close_carrier`（全 NaN／長度 0 ⇒
`CloseCarrierInvalidError`）。真實 kline，沿用 scripts/ic1d_baseline_freeze 之 production 路徑。
實作前應為紅：兩函式不存在、正常路徑 carrier 全 NaN。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Tuple

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from momentum.Analysis import ic_filter_orchestrator as ifo  # noqa: E402
from momentum.core.icfirstalign_errors import CloseCarrierInvalidError  # noqa: E402
from scripts.ic1d_baseline_freeze import _build_advanced_config, prepare_real_kline_inputs  # noqa: E402

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def production(tmp_path_factory: pytest.TempPathFactory) -> Tuple[Any, pd.DataFrame]:
    """正常 production 路徑一次（真實 kline）；回傳 (orchestrator, 真實 kline raw_data)。"""
    tmp = tmp_path_factory.mktemp("icfa_fu2")
    features_path, labels_path, meta_path, kline_reader, _ = prepare_real_kline_inputs(tmp)
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    orch = ifo.ICFilterOrchestrator(_build_advanced_config())
    orch._suppress_persist = True
    orch.analyze(features_path=str(features_path), labels_path=str(labels_path), meta_path=str(meta_path),
                 kline_reader=kline_reader)
    raw = kline_reader.read_klines(meta["symbol"], meta["timeframe"])
    return orch, raw


def _kline_close_at(raw: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """測試端獨立：kline 之 `timestamp` 欄（秒或毫秒）→ UTC tz-naive 時間，依時間戳取 close。"""
    ts = pd.to_numeric(raw["timestamp"])
    unit = "ms" if ts.max() > 10**11 else "s"
    series = pd.Series(raw["close"].to_numpy(dtype=np.float64), index=pd.DatetimeIndex(pd.to_datetime(ts, unit=unit)))
    target = index.tz_convert("UTC").tz_localize(None) if index.tz is not None else index
    return series.reindex(target)


def test_production_close_carrier_equals_kline_close(production: Tuple[Any, pd.DataFrame]) -> None:
    """正常路徑 carrier 於特徵時間戳之值與真實 kline close 逐一相等（有限）。"""
    orch, raw = production
    carrier = orch._ic_cache["close_series"]
    expected = _kline_close_at(raw, carrier.index)
    assert np.isfinite(carrier.to_numpy()).all()
    np.testing.assert_array_equal(carrier.to_numpy(dtype=np.float64), expected.to_numpy(dtype=np.float64))


def test_build_close_carrier_all_nan_close_fails_closed(production: Tuple[Any, pd.DataFrame]) -> None:
    orch, raw = production
    broken = raw.copy()
    broken["close"] = np.nan
    with pytest.raises(CloseCarrierInvalidError):
        ifo._build_close_carrier(broken, orch._ic_cache["features_df"].index)


def test_build_close_carrier_disjoint_timestamps_fails_closed(production: Tuple[Any, pd.DataFrame]) -> None:
    orch, raw = production
    shifted = raw.copy()
    shifted["timestamp"] = pd.to_numeric(shifted["timestamp"]) + 1800 * (1000 if shifted["timestamp"].max() > 10**11 else 1)
    with pytest.raises(CloseCarrierInvalidError):
        ifo._build_close_carrier(shifted, orch._ic_cache["features_df"].index)


def test_boundary_01_partial_nan_close_unchanged(production: Tuple[Any, pd.DataFrame]) -> None:
    """Task 3.1 邊界①：部分 NaN ⇒ 不拋、NaN 位置與輸入一致。"""
    orch, raw = production
    partial = raw.copy()
    n = len(partial) // 3
    partial.iloc[:n, partial.columns.get_loc("close")] = np.nan
    index = orch._ic_cache["features_df"].index
    carrier = ifo._build_close_carrier(partial, index)
    expected = _kline_close_at(partial, index)
    np.testing.assert_array_equal(np.isnan(carrier.to_numpy(dtype=np.float64)), np.isnan(expected.to_numpy()))
    assert carrier.notna().any() and carrier.isna().any()


def test_boundary_02_empty_close_carrier_fails_closed() -> None:
    """Task 3.1 邊界②：close 長度 0 ⇒ 具名錯誤。"""
    with pytest.raises(CloseCarrierInvalidError):
        ifo._validate_close_carrier(pd.Series([], dtype=np.float64))


def _variant_raw(raw: pd.DataFrame, source: str) -> pd.DataFrame:
    """同一真實 kline 之時間表示變體：epoch 秒（原樣）或 UTC tz-aware Timestamp（時刻不變）。"""
    if source == "epoch":
        return raw
    out = raw.copy()
    ts = pd.to_numeric(raw["timestamp"])
    out["timestamp"] = pd.to_datetime(ts, unit="ms" if ts.max() > 10**11 else "s", utc=True)
    return out


def _variant_target(index: pd.DatetimeIndex, target: str) -> pd.DatetimeIndex:
    utc = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    return utc if target == "aware" else utc.tz_localize(None)


@pytest.mark.parametrize("source", ["epoch", "utc_aware"])
@pytest.mark.parametrize("target", ["aware", "naive"])
def test_utc_representation_equivalence(production: Tuple[Any, pd.DataFrame], source: str, target: str) -> None:
    """同一 UTC 時刻之不同表示（來源 epoch 秒／UTC tz-aware × 目標 tz-aware／tz-naive）⇒ 逐值相等、索引保持目標。"""
    orch, raw = production
    index = _variant_target(orch._ic_cache["features_df"].index, target)
    carrier = ifo._build_close_carrier(_variant_raw(raw, source), index)
    pd.testing.assert_index_equal(carrier.index, index, exact=True)
    expected = _kline_close_at(raw, index)
    np.testing.assert_array_equal(carrier.to_numpy(dtype=np.float64), expected.to_numpy(dtype=np.float64))


def test_mutation_utc_unification_removed(production: Tuple[Any, pd.DataFrame], monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：移除 UTC 表示統一（`_utc_instant_key` 改恆等）⇒ tz-aware 來源對 tz-naive 目標全不相交 ⇒ 守衛拒絕。"""
    orch, raw = production
    monkeypatch.setattr(ifo, "_utc_instant_key", lambda index: index)
    index = _variant_target(orch._ic_cache["features_df"].index, "naive")
    with pytest.raises(CloseCarrierInvalidError):
        ifo._build_close_carrier(_variant_raw(raw, "utc_aware"), index)


def test_event_type_carrier_values_and_nan_positions(production: Tuple[Any, pd.DataFrame], tmp_path: Path) -> None:
    """事件型：事件篩選（真實特徵軸之事件時間戳）後 stage4 經同一 carrier；事件列之值與 NaN 位置與 kline close 對證。"""
    features_path, labels_path, meta_path, kline_reader, _ = prepare_real_kline_inputs(tmp_path)
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    index = production[0]._ic_cache["features_df"].index  # 正常路徑讀入之真實特徵軸
    config = _build_advanced_config()
    config.event_filter.enabled = True
    orch = ifo.ICFilterOrchestrator(config)
    orch._suppress_persist = True
    orch.analyze(features_path=str(features_path), labels_path=str(labels_path), meta_path=str(meta_path),
                 kline_reader=kline_reader, event_timestamps=list(index[::2]))
    carrier = orch._ic_cache["close_series"]
    raw = kline_reader.read_klines(meta["symbol"], meta["timeframe"])
    expected = _kline_close_at(raw, carrier.index)
    np.testing.assert_array_equal(np.isnan(carrier.to_numpy(dtype=np.float64)), np.isnan(expected.to_numpy()))
    np.testing.assert_array_equal(carrier.dropna().to_numpy(dtype=np.float64), expected.dropna().to_numpy())
    assert carrier.notna().any()


def test_mutation_carrier_positional_reindex_all_nan(production: Tuple[Any, pd.DataFrame],
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：carrier 改回 HEAD 之「位置索引直接 reindex」⇒ 全 NaN（相等斷言翻轉）。"""
    orch, raw = production

    def head_carrier(raw_data: pd.DataFrame, feature_index: pd.Index) -> pd.Series:
        return pd.to_numeric(raw_data["close"], errors="coerce").reindex(feature_index)

    monkeypatch.setattr(ifo, "_build_close_carrier", head_carrier)
    carrier = ifo._build_close_carrier(raw, orch._ic_cache["features_df"].index)
    assert carrier.isna().all()


def test_mutation_guard_removed_all_nan_passes_silently(production: Tuple[Any, pd.DataFrame],
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：刪守衛（`_validate_close_carrier` 改 no-op）⇒ 全 NaN close 不拋。"""
    orch, raw = production
    monkeypatch.setattr(ifo, "_validate_close_carrier", lambda close: None)
    broken = raw.copy()
    broken["close"] = np.nan
    carrier = ifo._build_close_carrier(broken, orch._ic_cache["features_df"].index)
    assert carrier.isna().all()
