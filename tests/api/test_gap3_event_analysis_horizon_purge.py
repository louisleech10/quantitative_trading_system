"""GAP-3 UX **Task 7.0b** 之編排驗收（`pytest tests/api -q -k event_analysis_horizon_purge`）。

涵蓋 SPEC ⑧（h 不得沿用）／⑨（purge 權威式，含 (a)(b)(c)(d)）／⑨(f)（`project_purge` 三條）／
⑩(i)（single-pass spy）／⑪（transport 400）。

🔴 **具名邊界**：⑩ 之 single-pass spy 打在 `_run_event_label_stages` 這一層，
**不是** render 整個 `_run_analysis`（後者要真的跑完一次 IC 分析，十分鐘級）。
這證明「五階段編排只呼叫 prepare 一次」，**不證明** `_run_analysis` 沒有在別處再呼叫一次；
後者由「該方法是事件分支唯一入口」這個結構性質承擔（`grep -c _run_event_label_stages` == 2：
一處定義、一處呼叫）。此邊界刻意寫出來，不當成已證明。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from momentum.Analysis.event_samples.label_value_from_case import (
    LabelProducerError,
    SymbolPurgeRow,
    WindowRow,
    project_purge,
    purge_lower_bound_rows,
)

H1_MS = 3600_000
H12_MS = 43200_000
T0 = 1704067200000


def win(eid: str, *, symbol="ETHUSDT", tf="12h", start: int, end: int) -> WindowRow:
    return WindowRow(
        event_id=eid, symbol=symbol, timeframe=tf,
        decision_at_ms=start, entry_at_ms=start,
        label_start_ms=start, label_end_ms=end,
    )


# ── ⑨ purge 權威式：max(lookahead_depth_ms, label_window_ms) 逐 scope 取 max ──────

def test_event_analysis_horizon_purge_09a_depth_side_wins():
    """(a) 深度 12 根、答案窗 3 根 ⇒ **深度側勝**。"""
    rows = purge_lower_bound_rows(
        [win("ev0", start=T0, end=T0 + 3 * H12_MS)],
        lookahead_bars_declared={"12h": 12},
        timeframe_seconds={"12h": 43200},
        symbols=["ETHUSDT"],
    )
    assert rows == (SymbolPurgeRow(symbol="ETHUSDT", purge_lower_bound_ms=12 * H12_MS),)


def test_event_analysis_horizon_purge_09b_window_side_wins():
    """(b) 深度 1 根、答案窗 7 根 ⇒ **窗寬側勝**（證明不是恆取深度）。"""
    rows = purge_lower_bound_rows(
        [win("ev0", start=T0, end=T0 + 7 * H12_MS)],
        lookahead_bars_declared={"12h": 1},
        timeframe_seconds={"12h": 43200},
        symbols=["ETHUSDT"],
    )
    assert rows == (SymbolPurgeRow(symbol="ETHUSDT", purge_lower_bound_ms=7 * H12_MS),)


def test_event_analysis_horizon_purge_09c_mixed_tf_converts_per_row():
    """(c) 同批混 1h 與 12h、同一 symbol、同樣宣告 4 根 ⇒ 兩列深度**相差 12 倍**。

    🔴 換算用**該列自己的** `timeframe`，不是批內 max／min tf。
    取 max 之後 scope 的下界＝12h 那列的 4×12h。
    """
    rows = purge_lower_bound_rows(
        [
            win("ev1h", tf="1h", start=T0, end=T0 + H1_MS),
            win("ev12h", tf="12h", start=T0, end=T0 + H12_MS),
        ],
        lookahead_bars_declared={"1h": 4, "12h": 4},
        timeframe_seconds={"1h": 3600, "12h": 43200},
        symbols=["ETHUSDT"],
    )
    assert rows == (SymbolPurgeRow(symbol="ETHUSDT", purge_lower_bound_ms=4 * H12_MS),)
    # 🔴 **over 向對照**：只留 1h 那列 ⇒ 下界降為 4×1h（證明上面那個值真的來自 12h 列，
    #    而不是某個與 tf 無關的常數）
    only_1h = purge_lower_bound_rows(
        [win("ev1h", tf="1h", start=T0, end=T0 + H1_MS)],
        lookahead_bars_declared={"1h": 4, "12h": 4},
        timeframe_seconds={"1h": 3600, "12h": 43200},
        symbols=["ETHUSDT"],
    )
    assert only_1h == (SymbolPurgeRow(symbol="ETHUSDT", purge_lower_bound_ms=4 * H1_MS),)


def test_event_analysis_horizon_purge_09d_per_symbol_not_batch_scalar():
    """(d) 兩個 symbol、窗寬不同 ⇒ 各自成立；**小窗 symbol 未被大窗抬高**。

    🔴 這條證偽「全批單一 scalar embargo」——那是 §D-3′-a(ii) 明令禁止的 per-scope 冒充，
    而且本 epic 在 B3／B5 各犯過一次。
    """
    rows = purge_lower_bound_rows(
        [
            win("evA", symbol="AAAUSDT", start=T0, end=T0 + 2 * H12_MS),
            win("evB", symbol="BBBUSDT", start=T0, end=T0 + 9 * H12_MS),
        ],
        lookahead_bars_declared={"12h": 0},
        timeframe_seconds={"12h": 43200},
        symbols=["AAAUSDT", "BBBUSDT"],
    )
    by = {r.symbol: r.purge_lower_bound_ms for r in rows}
    assert by["AAAUSDT"] == 2 * H12_MS       # 未被 BBB 的 9 根抬高
    assert by["BBBUSDT"] == 9 * H12_MS
    assert by["AAAUSDT"] != by["BBBUSDT"]    # 防「兩者恰好相等」使本條失去鑑別力


def test_event_analysis_horizon_purge_09_missing_key_fail_closed():
    """缺 `lookahead_bars_declared` 或 `timeframe_seconds` 之鍵 ⇒ fail-closed（不補預設）。"""
    with pytest.raises(LabelProducerError, match="lookahead_bars_declared"):
        purge_lower_bound_rows(
            [win("ev0", start=T0, end=T0 + H12_MS)],
            lookahead_bars_declared={}, timeframe_seconds={"12h": 43200}, symbols=["ETHUSDT"],
        )
    with pytest.raises(LabelProducerError, match="timeframe_seconds"):
        purge_lower_bound_rows(
            [win("ev0", start=T0, end=T0 + H12_MS)],
            lookahead_bars_declared={"12h": 0}, timeframe_seconds={}, symbols=["ETHUSDT"],
        )


def test_event_analysis_horizon_purge_09_symbol_without_window_kept():
    """某 symbol 於對齊後無 window ⇒ **該列仍留在 tuple 內**（下界 0），split 讀到略過即可。

    🔴 R14 明定：鍵集恰等於 **pre-coverage 之 symbol 集合**。少一列會讓 split 在
    「這個 symbol 有沒有下界」與「下界是多少」之間分不清楚。
    """
    rows = purge_lower_bound_rows(
        [win("evA", symbol="AAAUSDT", start=T0, end=T0 + H12_MS)],
        lookahead_bars_declared={"12h": 0},
        timeframe_seconds={"12h": 43200},
        symbols=["AAAUSDT", "ZZZUSDT"],
    )
    assert {r.symbol for r in rows} == {"AAAUSDT", "ZZZUSDT"}
    assert dict((r.symbol, r.purge_lower_bound_ms) for r in rows)["ZZZUSDT"] == 0


# ── ⑨(f) `project_purge` 之三條（R17 重寫；原兩條可假綠） ────────────────────

def test_event_analysis_horizon_purge_09f_duplicate_symbol_raises():
    """① duplicate 用 **exception oracle**，不用等式。

    🔴 用等式會假綠：`{'A':100}`／`{'A':200}` 兩列以 dict 生成式建 expected 時，
    重複列已被**靜默折疊**成 `{'A':200}`，兩邊相等而綠（`CODEX-R17-P1-03` 之反例）。
    """
    with pytest.raises(ValueError, match="重複"):
        project_purge([
            SymbolPurgeRow(symbol="AAA", purge_lower_bound_ms=100),
            SymbolPurgeRow(symbol="AAA", purge_lower_bound_ms=200),
        ])


def test_event_analysis_horizon_purge_09f_exact_projection_non_max_key():
    """② 合法 case 用**非最大鍵**之 exact 等式：`A→100`／`B→300`。

    🔴 若投影錯寫成「全部取 max」，`A` 會變成 300 ⇒ 本條紅。
    兩值必須不同、且被檢查的是**非最大**那個鍵，否則 mutation 與原值相同而不紅。
    """
    out = project_purge([
        SymbolPurgeRow(symbol="AAA", purge_lower_bound_ms=100),
        SymbolPurgeRow(symbol="BBB", purge_lower_bound_ms=300),
    ])
    assert dict(out) == {"AAA": 100, "BBB": 300}
    assert out["AAA"] == 100 != max(out.values())


def test_event_analysis_horizon_purge_09f_returns_readonly_mapping():
    """投影回 **read-only** view ⇒ 「不得掛回 `PreparedAnalysisWindows`」不只靠紀律。"""
    out = project_purge([SymbolPurgeRow(symbol="AAA", purge_lower_bound_ms=100)])
    with pytest.raises(TypeError):
        out["AAA"] = 999  # type: ignore[index]


# ── ⑪ transport 之兩條 400（含 over 向） ────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_event_analysis_horizon_purge_11_spec_without_import_id_is_400(client):
    """⑪ `event_label_spec` 存在而 `event_import_id` 缺 ⇒ **400**。"""
    r = client.post("/api/v1/ic/analyze", json={
        "symbol": "ETHUSDT", "timeframe": "12h",
        "event_label_spec": {"horizon_bars": 1, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
    })
    assert r.status_code == 422, r.text  # pydantic 驗證層 ⇒ FastAPI 回 422
    assert "event_import_id" in r.text


def test_event_analysis_horizon_purge_11b_import_id_with_timestamps_is_rejected(client):
    """`event_import_id` 與 `event_timestamps` **互斥** ⇒ 拒收（兩個真相源）。"""
    r = client.post("/api/v1/ic/analyze", json={
        "symbol": "ETHUSDT", "timeframe": "12h",
        "event_import_id": "imp-x", "event_timestamps": [T0],
    })
    assert r.status_code == 422, r.text
    assert "event_timestamps" in r.text


def test_event_analysis_horizon_purge_11c_legacy_timestamps_only_still_accepted(client):
    """🔴 **over 向**：legacy 呼叫端只帶 `event_timestamps` ⇒ **不得**被上面兩條誤擋。

    這條是「新增一條路徑、不改既有語意」的證據。它不驗分析結果，只驗**沒有在 transport 層被拒**。
    """
    r = client.post("/api/v1/ic/analyze", json={
        "symbol": "ETHUSDT", "timeframe": "12h", "event_timestamps": [T0],
    })
    assert r.status_code != 422, r.text


# ── ⑩(i) single-pass：prepare 只被呼叫一次 ──────────────────────────────────

def test_event_analysis_horizon_purge_10i_prepare_called_once(monkeypatch):
    """⑩(i) 一次五階段編排中 `prepare_analysis_windows` 之 `call_count == 1`。

    🔴 hash 是**決定性**的 ⇒ 三個 consumer 各自呼叫一次也會得到相同 hash，
    「hash 相同」擋不住重入。所以要直接數呼叫次數。
    🔴 本條之邊界見檔頭：spy 打在 `_run_event_label_stages`，不是整個 `_run_analysis`。
    """
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod

    calls = {"n": 0}
    real = pipeline_mod.EventSamplePipeline.prepare_analysis_windows

    def spy(*a, **kw):
        calls["n"] += 1
        return real(*a, **kw)

    monkeypatch.setattr(pipeline_mod.EventSamplePipeline, "prepare_analysis_windows", staticmethod(spy))

    from tests.momentum.event_samples.helpers import load_bars, make_event
    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )
    records = [
        make_event(0, t0=T0 + 100 * H12_MS, label=1, direction="long"),
        make_event(1, t0=T0 + 110 * H12_MS, label=0, direction="long"),
    ]
    batch = {
        "records": records,
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {"12h": 0},
    }

    class _Req:
        event_import_id = "imp-1"
        event_timestamps = None

    out = svc.ICAnalysisService._run_event_label_stages(
        _Req(), batch,
        features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
        meta_path=None,
    )
    assert calls["n"] == 1, f"prepare 被呼叫 {calls['n']} 次（須恰 1 次）"
    assert out["event_label_values"], "應產出至少一個 label_value"
    # 🔴 token 為非決定性 ⇒ 它出現在輸出代表確實是「同一次呼叫」傳下來的，不是重算
    assert out["prepared_token"] == out["prepared"].prepared_token
