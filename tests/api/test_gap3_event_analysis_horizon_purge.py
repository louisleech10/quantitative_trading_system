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
        timeframe = "12h"  # 階段 4 之 ms→列數換算要用它（R1 修法後新增）

    out = svc.ICAnalysisService._run_event_label_stages(
        _Req(), batch,
        features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
        meta_path=None,
    )
    assert calls["n"] == 1, f"prepare 被呼叫 {calls['n']} 次（須恰 1 次）"
    assert out["event_label_values"], "應產出至少一個 label_value"
    # 🔴 token 為非決定性 ⇒ 它出現在輸出代表確實是「同一次呼叫」傳下來的，不是重算
    assert out["prepared_token"] == out["prepared"].prepared_token

    # ⑭(c)：餵進 IC 的鍵集 ⊆ allowed_event_ids（以 per_tf 之 cutoff 反查 event_id）
    prepared = out["prepared"]
    cutoff_to_eid = {p.feature_cutoff_ms: p.event_id for p in prepared.per_tf}
    fed_eids = {cutoff_to_eid[ts] for ts in out["event_timestamps"] if ts in cutoff_to_eid}
    assert fed_eids <= set(prepared.allowed_event_ids), "餵進 IC 的 event_id 不得超出 allowed"
    assert fed_eids, "對照：至少有一個 eid 真的被餵進去（防空集合恆成立）"

    # 🔴 **feature sample key 取自 receipt 之 per-TF cutoff，不是原始 t0**（Task 7.7 ⑦／⑫ 之核心）
    t0_seconds = {int(r["t0"]) // 1000 for r in records}
    assert not (set(out["event_timestamps"]) & t0_seconds), \
        "送進 IC 的時間戳不得等於「t0 ÷ 1000」——那正是被移除的前端映射之形狀"


def test_event_analysis_horizon_purge_r1_full_analysis_rejects_event_batch(client):
    """R1 三家全員：`/full-analysis` 收到 `event_import_id` ⇒ **400 明說拒絕**，不靜默忽略。

    🔴 原本 `ICFullAnalysisRequest` 繼承該欄位、收得下，但 `_run_full_analysis`
    **不跑五階段、不跑 coverage 閘** ⇒ 使用者以為做了事件分析，實際上那個欄位被丟掉。
    「靜默忽略」比「明說不支援」危險得多：前者會產出一份看起來正常但語意錯誤的報告。
    """
    r = client.post("/api/v1/ic/full-analysis", json={
        "symbol": "ETHUSDT", "timeframe": "12h", "config_hash": "abc",
        "labels_path": "/tmp/x.h5", "event_import_id": "imp-1",
    })
    assert r.status_code == 400, r.text
    assert "event_batch_not_supported_on_full_analysis" in r.text


def test_event_analysis_horizon_purge_r1_cross_sectional_rejects_event_batch(client):
    """R1 三家全員：`mode=cross_sectional` ＋ `event_import_id` ⇒ 拒收（同上理由）。"""
    r = client.post("/api/v1/ic/analyze", json={
        "mode": "cross_sectional", "timeframe": "12h",
        "symbols": ["ETHUSDT", "BTCUSDT"], "event_import_id": "imp-1",
    })
    assert r.status_code == 422, r.text
    assert "cross_sectional" in r.text


def test_event_analysis_horizon_purge_r1_missing_import_is_404_not_500(client):
    """`COMPOSER-R1-P1-04`／`CODEX-R1-P2-04`：不存在之批次 ⇒ **404**，不是 500。

    🔴 根因：`HTTPException` 繼承 `Exception`，route 的 `except Exception` 把我刻意設計的
    404 吞成 500。所有「我方設計的狀態碼」都會被這樣降級——不是只有這一個。
    """
    r = client.post("/api/v1/ic/analyze", json={
        "symbol": "ETHUSDT", "timeframe": "12h", "config_hash": "abc",
        "event_import_id": "definitely-not-there",
    })
    assert r.status_code == 404, r.text


def test_event_analysis_horizon_purge_r1_divergent_purge_is_fail_closed(monkeypatch):
    """`CODEX-R1-P1-02` 之修法：各 symbol purge 下界**不一致** ⇒ fail-closed，不取 max。

    🔴 取 max 折成全域 scalar **正是 §D-3′-a(ii) 明令禁止**的 per-scope 冒充
    （本 epic 在 B3／B5 各犯過一次）。IC 切分器只接受列數之全域 scalar embargo，
    所以「能表達就套用、不能表達就拒絕」是唯一不違規的解——這是 B3 的既有先例。
    """
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )
    # 兩個 symbol、窗寬不同 ⇒ 下界必不一致（bars 只有 ETHUSDT，另一個會對齊失敗，
    # 故改以 lookahead 宣告製造差異：兩個 tf 不同深度，但只有一個 tf 有事件 ⇒ 用兩批比對）
    fake_rows = (
        pipeline_mod.EventSamplePipeline.project_purge,  # 佔位，確保 import 生效
    )
    assert fake_rows  # 防 lint

    class _Req:
        event_import_id = "imp-1"
        event_timestamps = None
        timeframe = "12h"

    real_prepare = pipeline_mod.EventSamplePipeline.prepare_analysis_windows

    def prepare_with_divergent_purge(*a, **kw):
        from dataclasses import replace as _replace
        from momentum.Analysis.event_samples.label_value_from_case import SymbolPurgeRow
        prepared = real_prepare(*a, **kw)
        return _replace(prepared, purge_lower_bound_ms_by_symbol=(
            SymbolPurgeRow(symbol="AAAUSDT", purge_lower_bound_ms=H12_MS),
            SymbolPurgeRow(symbol="BBBUSDT", purge_lower_bound_ms=9 * H12_MS),
        ))

    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "prepare_analysis_windows",
        staticmethod(prepare_with_divergent_purge),
    )
    batch = {
        "records": [
            make_event(0, t0=T0 + 100 * H12_MS, label=1, direction="long"),
            make_event(1, t0=T0 + 110 * H12_MS, label=0, direction="long"),
        ],
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {"12h": 0},
    }
    with pytest.raises(ValueError, match="purge 下界不一致"):
        svc.ICAnalysisService._run_event_label_stages(
            _Req(), batch,
            features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
            meta_path=None,
        )


def test_event_analysis_horizon_purge_r1_duplicate_cutoff_is_loud(monkeypatch):
    """`CODEX-R1-P1-03`：兩事件映射到**同一個 feature 列** ⇒ raise，不得靜默覆蓋。

    🔴 原本這裡是 `ts_map[key] = value`，後到的**靜默蓋掉**先到的——等於默默丟掉一個事件，
    而且丟哪一個取決於迭代順序。`ic_feed.py:79-81` 對同一情形本來就 raise
    （「禁默默覆蓋；請先 dedupe」），我這條路徑繞過 `ic_feed` 就把那道保護一起繞掉了。
    """
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )

    class _Req:
        event_import_id = "imp-1"
        event_timestamps = None
        timeframe = "12h"

    same_t0 = T0 + 100 * H12_MS
    batch = {
        # 🔴 **同一個 t0、不同 event_id** ⇒ 兩者之 feature cutoff 必然相同
        "records": [
            make_event(0, t0=same_t0, label=1, direction="long"),
            make_event(1, t0=same_t0, label=0, direction="long"),
        ],
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {"12h": 0},
    }
    with pytest.raises(ValueError, match="映射到同一個 feature 列"):
        svc.ICAnalysisService._run_event_label_stages(
            _Req(), batch,
            features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
            meta_path=None,
        )


def test_event_analysis_horizon_purge_r1_all_alignment_failed_is_loud(monkeypatch):
    """`CODEX-R1-P1-03` 之另一半：全批對齊失敗 ⇒ **raise**，不得靜默出一張空表。

    🔴 **這條是我自己的 mutation 抓出來的缺口**：R1 修法時我加了 `if not prepared1.windows: raise`
    這道守衛，卻**沒寫任何測試**——`R1-M6`（把它改回靜默）錄到空紅集合，才發現。
    加了守衛沒加測試，等於下一個人可以無聲地把它拿掉。

    構造方式：`t0` 刻意不落在任何 12h bar 的 open 上（偏移一小時）
    ⇒ `align_events` 判 `no_boundary_match`，全批無 `WindowRow`。
    """
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )

    class _Req:
        event_import_id = "imp-1"
        event_timestamps = None
        timeframe = "12h"

    off_grid = T0 + 100 * H12_MS + H1_MS  # 偏移一小時 ⇒ 不是 12h bar 的 open
    batch = {
        "records": [
            make_event(0, t0=off_grid, label=1, direction="long"),
            make_event(1, t0=off_grid + 10 * H12_MS, label=0, direction="long"),
        ],
        "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                             "label_return_mode": "close_to_close", "decision_offset_bars": 0},
        "lookahead_bars_declared": {"12h": 0},
    }
    with pytest.raises(ValueError, match="沒有任何可用窗"):
        svc.ICAnalysisService._run_event_label_stages(
            _Req(), batch,
            features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
            meta_path=None,
        )


def test_event_analysis_horizon_purge_timeframe_seconds_identity(monkeypatch):
    """SPEC R26／⑥(d)：purge 與 feature-run gate 收到**同一個** `timeframe_seconds` 物件（`is`）。

    🔴 這條是 R1 由 **composer 與 grok 兩家獨立**指出的缺口，而我自己在 brief 的
    `assumed` 段就已自陳「沒有寫 `is` 斷言把它釘住」——寫出來但沒補，兩家都抓了。
    🔴 為什麼「內容相同」不夠：`timeframe_seconds` 是**注入**的，若哪天有人在其中一側
    改成 `dict(timeframe_seconds)` 或重新 `timeframe_seconds_for(...)` 建一份，
    內容一樣但**兩份會各自演化**——那正是 B9 花五輪修的「閘門與 loader 各算各的」同型病。
    只有身分比對擋得住。
    """
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import label_value_from_case as lvfc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )

    seen: dict = {}
    real_purge = lvfc.purge_lower_bound_rows
    real_gate = svc.check_feature_run_coverage

    def spy_purge(*a, **kw):
        seen["purge"] = kw["timeframe_seconds"]
        return real_purge(*a, **kw)

    def spy_gate(**kw):
        seen["gate"] = kw["timeframe_seconds"]
        return real_gate(**kw)

    monkeypatch.setattr(lvfc, "purge_lower_bound_rows", spy_purge)
    monkeypatch.setattr(svc, "check_feature_run_coverage", spy_gate)

    class _Req:
        event_import_id = "imp-1"
        event_timestamps = None
        timeframe = "12h"

    svc.ICAnalysisService._run_event_label_stages(
        _Req(),
        {
            "records": [
                make_event(0, t0=T0 + 100 * H12_MS, label=1, direction="long"),
                make_event(1, t0=T0 + 110 * H12_MS, label=0, direction="long"),
            ],
            "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                                 "label_return_mode": "close_to_close", "decision_offset_bars": 0},
            "lookahead_bars_declared": {"12h": 0},
        },
        features_path="data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/x.h5",
        meta_path=None,
    )
    assert "purge" in seen and "gate" in seen, "兩個 consumer 都必須真的被呼叫到"
    assert seen["purge"] is seen["gate"], "兩處收到的 timeframe_seconds 必須是**同一個物件**"
    # 🔴 **over 向對照**：內容相等但身分不同時，`is` 必須為 False——證明本條不是恆真
    assert not (dict(seen["purge"]) is seen["gate"])


def test_event_analysis_horizon_purge_14abd_coverage_filter_semantics():
    """SPEC ⑭(a)(b)(d) 之語意——**對 `apply_event_coverage` 直接驗**。

    🔴 **具名邊界（composer／grok R1 兩家指出）**：現行 live 路徑之 3a
    （`check_feature_run_coverage`）是**批次級 pass/fail**、不產生 event-id 子集
    ⇒ 編排層永遠傳全集，⑭(a)(b)(d) 在 live 路徑上**不可證偽**。
    本條把該語意拉到 `apply_event_coverage` 這一層直接驗——**這不等於 live 路徑有守到**，
    差額已具名為 `R-B10-2`。之所以仍要有這條：GAP-6 之分塊計算會讓 3a 產生子集，
    屆時語意必須已經是對的。
    """
    from momentum.Analysis.event_samples.label_value_from_case import (
        PreparedAnalysisWindows, apply_event_coverage,
    )

    base = PreparedAnalysisWindows(
        supported=True,
        windows=(win("evA", start=T0, end=T0 + H12_MS), win("evB", start=T0, end=T0 + H12_MS)),
        analysis_alignment_receipt_hash="h",
        per_tf=(), normalized_spec_bytes=b"{}",
        allowed_event_ids=frozenset({"evA", "evB"}),
        purge_lower_bound_ms_by_symbol=(), prepared_token="tok",
        reason=None, direction_sign=1,
    )
    # (a)(b)：剔除後之 allowed 就是後續 manifest／split 之唯一定義域
    kept = apply_event_coverage(base, frozenset({"evA"}))
    assert kept.allowed_event_ids == frozenset({"evA"})
    assert kept.prepared_token == base.prepared_token       # 身分攜帶
    assert kept.windows == base.windows                     # windows 本身不被剔除，濾的是 allowed
    # (d)：allowed 為**空** ⇒ 仍回一個合法物件（由編排層走 loud），不是靜默出空表
    empty = apply_event_coverage(base, frozenset())
    assert empty.allowed_event_ids == frozenset()
    assert empty.prepared_token == base.prepared_token
    # 🔴 **over 向**：不剔除任何列時兩者 allowed 相等（證明上面不是「總是變空」）
    assert apply_event_coverage(base, base.allowed_event_ids).allowed_event_ids == base.allowed_event_ids


def test_event_analysis_horizon_purge_12_decision_at_mapping_k3_vs_k0(monkeypatch):
    """Task 7.7 ⑫：`decision_offset_bars = 3` 之批次 ⇒ 每列之 feature cutoff `<= decision_at < t0`；
    `k = 0` 之批次為**對照組**（`decision_at == t0`），證明本條既非恆真也非恆假。

    🔴 k=3 落在 F-1′ 支援矩陣**之外**（分析層不算 label_value），但 **windows 仍會產生**
    ——這正是 SPEC 驗收 ④ 要求的：k 的映射必須看得出來確實生效了。
    """
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(
        pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
        staticmethod(lambda symbols, timeframes, **kw: bars),
    )

    def prepared_for(k: int):
        recs = [
            make_event(0, t0=T0 + 100 * H12_MS, label=1, direction="long"),
            make_event(1, t0=T0 + 110 * H12_MS, label=0, direction="long"),
        ]
        return pipeline_mod.EventSamplePipeline.prepare_analysis_windows(
            recs, bars,
            event_label_spec={"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                              "label_return_mode": "close_to_close", "decision_offset_bars": k},
            event_import_id="imp-1",
            lookahead_bars_declared={"12h": 0},
            timeframe_seconds={"12h": 43200},
        ), {r["event_id"]: int(r["t0"]) for r in recs}

    p3, t0_by_id = prepared_for(3)
    assert p3.windows, "k=3 之批次仍須產出 windows（否則本條無從斷言）"
    cutoffs3 = {p.event_id: p.feature_cutoff_ms for p in p3.per_tf}
    for w in p3.windows:
        assert w.decision_at_ms < t0_by_id[w.event_id], "k=3 ⇒ decision_at 須早於 t0"
        assert cutoffs3[w.event_id] <= w.decision_at_ms, "feature cutoff 不得晚於 decision_at"

    # 🔴 **對照組**：k=0 ⇒ decision_at == t0（證明上面那條不是恆真）
    p0, _ = prepared_for(0)
    for w in p0.windows:
        assert w.decision_at_ms == t0_by_id[w.event_id], "k=0 ⇒ decision_at 應等於 t0"
