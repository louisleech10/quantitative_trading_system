"""跨週期分析：粗週期事件批 × 細週期特徵 run（UAT，2026-09-07）。"""
from __future__ import annotations

import pytest

from momentum.factories import create_event_sample_pipeline


def test_timeframe_seconds_for_accepts_analysis_tf_beyond_event_tfs():
    """🔴 鍵集必須含**分析用** timeframe，不只事件批宣告的那些。

    出生事故：使用者拿 12h 的事件批配 1h 的特徵 run，被
    `分析用 timeframe '1h' 不在注入之 timeframe_seconds 鍵集（['12h']）` 擋死。

    那是過嚴：`purge_ms` 是**時間長度**（與 timeframe 無關），換算成 1h 的列數
    只是「同樣一段時間等於幾根 1h」；而且對齊層在那之前已經成功把事件映射到 1h 的列上。
    跨週期（粗事件 × 細特徵）本來就是這個系統支援的用法。
    """
    pipeline = create_event_sample_pipeline()
    # 事件批只宣告 12h，分析用 1h ⇒ 兩者都要在鍵集裡
    out = pipeline.timeframe_seconds_for(sorted({"12h"} | {"1h"}))
    assert out["12h"] == 12 * 3600
    assert out["1h"] == 3600


def test_timeframe_seconds_for_still_fails_closed_on_unknown():
    """放寬的是「哪些 tf 要建構」，**不是** fail-closed 本身。"""
    pipeline = create_event_sample_pipeline()
    with pytest.raises(ValueError, match="不認得的 timeframe"):
        pipeline.timeframe_seconds_for(["12h", "3weeks"])


from momentum.Analysis.event_samples.pipeline import EventSamplePipeline as _EventSamplePipeline

_REAL_ISOLATION_TERMS_ROWS = _EventSamplePipeline.isolation_terms_rows
_H12_MS = 43_200_000
_T0 = 1704067200000


class _Stop(Exception):
    """攔截哨：取得中途值後中止五階段（不需特徵 run 目錄）。"""


def _run_stages_until_isolation(monkeypatch, analysis_tf: str):
    """以真實 ETHUSDT 12h/1h kline 跑 `_run_event_label_stages` 至隔離換算為止。

    只替換兩個與本主題無關之環節：特徵 run 涵蓋閘（需磁碟上之 run manifest，與 timeframe 換算無關）
    與 isolation 之後的流程（以哨兵中止）；timeframe 鍵集建構／bars 載入／窗換算皆為真實碼。
    回傳 (bars_from_kline_cache 收到之 timeframes, 注入之 timeframe_seconds, EventIsolationRows)。
    """
    from types import SimpleNamespace

    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h", "1h"))
    seen = {}

    def fake_bars(symbols, timeframes, **kw):
        seen["bars_tfs"] = list(timeframes)
        return bars

    real_iso = _REAL_ISOLATION_TERMS_ROWS  # 模組載入時取得（避免同測內二次 patch 取到哨兵）

    def iso(*a, **kw):
        seen["ts"] = dict(kw["timeframe_seconds"])
        seen["iso"] = real_iso(*a, **kw)
        raise _Stop()

    monkeypatch.setattr(pipeline_mod.EventSamplePipeline, "bars_from_kline_cache", staticmethod(fake_bars))
    monkeypatch.setattr(pipeline_mod.EventSamplePipeline, "isolation_terms_rows", staticmethod(iso))
    monkeypatch.setattr(
        svc, "check_feature_run_coverage",
        lambda **kw: SimpleNamespace(evaluated=False, covered_event_ids=frozenset()),
    )
    records = [
        make_event(0, t0=_T0 + 100 * _H12_MS, label=1, direction="long"),
        make_event(1, t0=_T0 + 110 * _H12_MS, label=0, direction="long"),
    ]
    batch = {
        "records": records,
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {"12h": 0},
    }

    class _Req:
        event_import_id = "imp-xtf"
        event_timestamps = None
        timeframe = analysis_tf

    with pytest.raises(_Stop):
        svc.ICAnalysisService._run_event_label_stages(
            _Req(), batch,
            features_path="data_cache/features/ETHUSDT/1h/x/x.h5", meta_path=None,
        )
    return seen["bars_tfs"], seen["ts"], seen["iso"]


def test_service_includes_analysis_timeframe_in_the_injected_map(monkeypatch):
    """service 端：注入的 map 必須涵蓋 `request.timeframe`。

    🔴 驗**實際建構出來的鍵集**（真實跑 `_run_event_label_stages`），不掃原始碼——
    後者擋不住「寫了但沒傳」。對照：分析 tf 即事件 tf 時鍵集不含多餘 tf。
    """
    bars_tfs, ts_map, _ = _run_stages_until_isolation(monkeypatch, "1h")
    assert ts_map == {"12h": 12 * 3600, "1h": 3600}      # 事件 tf ∪ 分析 tf
    assert bars_tfs == ["12h", "1h"]                      # bars 同樣載入兩個 tf

    bars_tfs_same, ts_same, _ = _run_stages_until_isolation(monkeypatch, "12h")
    assert ts_same == {"12h": 12 * 3600}
    assert bars_tfs_same == ["12h"]


def test_purge_rows_conversion_is_duration_based(monkeypatch):
    """同一段 purge 時間，在細週期上就是更多列——這是本修法成立的理由。

    真實跑五階段至 isolation：同一批 12h 事件（horizon 2 根 12h＝24h 窗），
    以 12h 特徵 run 分析得 2 列、以 1h 特徵 run 分析得 24 列（×12）。
    """
    _, _, iso_12h = _run_stages_until_isolation(monkeypatch, "12h")
    _, _, iso_1h = _run_stages_until_isolation(monkeypatch, "1h")
    assert iso_12h.label_window_rows == 2
    assert iso_1h.label_window_rows == 24
    assert iso_1h.label_window_rows == 12 * iso_12h.label_window_rows
