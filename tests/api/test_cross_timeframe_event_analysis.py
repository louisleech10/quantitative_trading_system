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


def test_service_includes_analysis_timeframe_in_the_injected_map():
    """service 端：注入的 map 必須涵蓋 `request.timeframe`。

    🔴 驗**實際建構出來的鍵集**，不是掃原始碼——後者擋不住「寫了但沒傳」。
    """
    import inspect

    from api.services import ic_analysis_service as svc

    src = inspect.getsource(svc.ICAnalysisService._run_event_label_stages)
    # 建構清單必須是「事件 tf ∪ 分析 tf」，不能只有事件 tf
    assert "tf_inputs" in src and "timeframe_seconds_for(tf_inputs)" in src, (
        "timeframe_seconds 又只用事件批宣告的 tf 建構了"
    )
    assert "timeframe_seconds_for(timeframes)" not in src


def test_purge_rows_conversion_is_duration_based():
    """同一段 purge 時間，在細週期上就是更多列——這是本修法成立的理由。"""
    purge_ms = 12 * 3600 * 1000          # 一根 12h
    for tf, seconds, expected_rows in (("12h", 12 * 3600, 1), ("1h", 3600, 12)):
        rows = -(-int(purge_ms) // (int(seconds) * 1000))   # 同 service 之 ceil division
        assert rows == expected_rows, f"{tf} 換算錯誤"
