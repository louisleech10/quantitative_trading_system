"""SPLITUNIFY v7 `R5-C9`：IC 事件路徑之特徵列鍵（真實資料）。

規格：`docs/SPLITUNIFY_SPEC.md` v7 `R5-C9` 1.–5.；施工清單：`docs/SPLITUNIFY_TODO.md` §C-10 `Task 10.2`。

🔴 **本檔一律用真實資料**（`data_cache/events/`、`data_cache/features/`、
`data_cache/feature_klines/kline_cache.h5`）；禁合成 fixture（CLAUDE.md 資料真實性鐵律）。
資料缺席時 `skip`（本機以外環境沒有 `data_cache/`），**不得**改用假資料讓它變綠。

驗的是什麼：事件對到的那一列特徵，其主週期 K 線之**收盤**不得晚於該事件之 `decision_at_ms`。
舊實作以 `feature_cutoff_ms`（收盤時刻）當列鍵，而特徵表以**開盤**時刻編索引 ⇒ 選到晚一根、
含決策後資訊之列（實測 165/165 命中）。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_event_sample_pipeline

REPO = Path(__file__).resolve().parents[3]
BATCH_12H = REPO / "data_cache/events/20260909T130533Z-7f73e4c7.json"
RUN_1H = REPO / "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5"
RUN_12H = REPO / "data_cache/features/ETHUSDT/12h/e53e22906c35363757f4cd49d27f973e"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"
BAR_MS = {"1h": 3_600_000, "12h": 43_200_000}


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def _batch() -> dict:
    return json.loads(BATCH_12H.read_text())


def _prepare(run_tf: str):
    b = _batch()
    decl = b["lookahead_declaration"]["lookahead_bars_declared"]
    spec = {
        "entry_price_semantic": "trigger_open",
        "label_return_mode": "open_to_horizon_close",
        "horizon_bars": int(decl["12h"]),
        "decision_offset_bars": 0,
    }
    pipe = create_event_sample_pipeline()
    tfs = sorted({"12h", run_tf})
    bars = pipe.bars_from_kline_cache(["ETHUSDT"], tfs)
    prepared = pipe.prepare_analysis_windows(
        tuple(b["records"]), bars,
        event_label_spec=spec,
        event_import_id=b["import_id"],
        lookahead_bars_declared=decl,
        timeframe_seconds=pipe.timeframe_seconds_for(tfs),
        feature_timeframe=run_tf,
    )
    return pipe, prepared, pipe.timeframe_seconds_for(tfs)


def _feature_index_ms(run_dir: Path) -> np.ndarray:
    ts = pd.read_parquet(run_dir / "timestamps.parquet")["timestamp"].to_numpy()
    return ts.astype(np.int64) * 1000


def _kline_bop(tf: str) -> pd.Series:
    import h5py

    with h5py.File(KLINE, "r") as f:
        d = f[f"ETHUSDT/{tf}/data"][:]
    rng = d["high"] - d["low"]
    bop = np.where(rng != 0, (d["close"] - d["open"]) / np.where(rng != 0, rng, 1), 0.0)
    return pd.Series(bop, index=d["timestamp"].astype(np.int64) * 1000)


@pytest.mark.parametrize("run_tf,run_dir", [("1h", RUN_1H), ("12h", RUN_12H)])
def test_selected_row_close_not_after_decision(run_tf: str, run_dir: Path) -> None:
    """`R5-C9` 1.：逐事件，特徵列鍵所屬 K 線之收盤 ≤ `decision_at_ms`；且鍵落在特徵索引內。

    對照（防空集合恆成立）：同一批以舊鍵（`feature_cutoff_ms`）計算時，**全部**事件之列收盤晚於決策時點。
    """
    _require(BATCH_12H, run_dir, KLINE)
    pipe, prepared, tsec = _prepare(run_tf)
    keys = pipe.feature_row_keys(prepared, feature_timeframe=run_tf, timeframe_seconds=tsec)
    index_ms = set(int(x) for x in _feature_index_ms(run_dir))
    bar = BAR_MS[run_tf]
    old_key_late = 0
    per_tf_old = {(p.event_id, p.timeframe): int(p.feature_cutoff_ms) for p in prepared.per_tf}

    assert prepared.windows, "真實批須有可用窗，否則本條無從斷言"
    for w in prepared.windows:
        key = int(keys[w.event_id])
        assert key + bar <= int(w.decision_at_ms), (
            f"事件 {w.event_id}：特徵列 {key} 之收盤 {key + bar} 晚於 decision_at {w.decision_at_ms}"
        )
        assert key in index_ms, f"事件 {w.event_id}：特徵列鍵 {key} 不在 post-trim 特徵索引內"
        old = per_tf_old[(w.event_id, w.timeframe)]
        if old + bar > int(w.decision_at_ms):
            old_key_late += 1
    assert old_key_late == len(prepared.windows), (
        "對照失效：舊鍵（feature_cutoff_ms）本應每一筆都晚一根，實得 "
        f"{old_key_late}/{len(prepared.windows)}"
    )


@pytest.mark.parametrize("run_tf,run_dir", [("1h", RUN_1H), ("12h", RUN_12H)])
def test_selected_row_value_matches_that_kline_bar(run_tf: str, run_dir: Path) -> None:
    """列以**開盤**時刻編索引之逐值證據：選中列之 BOP＝「開盤＝鍵」那根 kline 之 BOP。

    BOP=(close-open)/(high-low) 只依賴當根 ⇒ 可逐值對證。float16 量化使少數列有誤差，
    故以 95% 為門檻並同時要求「對錯一根」之比例為 0（選錯列會整批不符）。
    """
    _require(BATCH_12H, run_dir, KLINE)
    pipe, prepared, tsec = _prepare(run_tf)
    keys = pipe.feature_row_keys(prepared, feature_timeframe=run_tf, timeframe_seconds=tsec)
    ts = _feature_index_ms(run_dir)
    col = pd.read_parquet(run_dir / "raw" / f"{run_tf}_L1_momentum_BOP.parquet")
    values = pd.Series(col[col.columns[0]].to_numpy().astype(np.float64), index=ts)
    kb = _kline_bop(run_tf)
    bar = BAR_MS[run_tf]

    match_same = match_next = total = 0
    for w in prepared.windows:
        key = int(keys[w.event_id])
        if key not in values.index:
            continue
        total += 1
        v = float(values.loc[key])
        same = kb.get(key, np.nan)
        nxt = kb.get(key + bar, np.nan)
        if np.isfinite(same) and np.isclose(v, same, rtol=1e-3, atol=1e-4):
            match_same += 1
        elif np.isfinite(nxt) and np.isclose(v, nxt, rtol=1e-3, atol=1e-4):
            match_next += 1
    assert total > 0, "無可比對之列"
    assert match_next == 0, f"有 {match_next}/{total} 列之值等於**下一根** kline ⇒ 選錯列"
    assert match_same / total >= 0.95, f"逐值相符率 {match_same}/{total} 低於門檻"


BATCH_1H = REPO / "data_cache/events/20260918T060524Z-d2c97d3b.json"


def _prepare_1h_batch(k: int):
    """1h 單週期批 × 12h run（Task 10.2 邊界③之非整點幾何）。

    該批依施工清單四步取得：真實混週期批之 14 筆 1h 記錄（`t0` 未改）、宣告裁切為僅 1h 鍵、
    匯入時明示 `batch_defaults.label_origin="user_csv"`、落檔 `20260918T060524Z-d2c97d3b`
    （`upload_sha256=72a8c9861ed3389350bab8c04ef672e250722100cbf0fb1aebd279467afb42ce`）。
    """
    b = json.loads(BATCH_1H.read_text())
    decl = b["lookahead_declaration"]["lookahead_bars_declared"]
    spec = {
        "entry_price_semantic": "trigger_open",
        "label_return_mode": "open_to_horizon_close",
        "horizon_bars": max(1, int(decl["1h"])),
        "decision_offset_bars": k,
    }
    pipe = create_event_sample_pipeline()
    tfs = ["1h", "12h"]
    bars = pipe.bars_from_kline_cache(["ETHUSDT"], tfs)
    prepared = pipe.prepare_analysis_windows(
        tuple(b["records"]), bars,
        event_label_spec=spec,
        event_import_id=b["import_id"],
        lookahead_bars_declared=decl,
        timeframe_seconds=pipe.timeframe_seconds_for(tfs),
        feature_timeframe="12h",
    )
    return pipe, prepared, pipe.timeframe_seconds_for(tfs)


def test_1h_events_12h_run_off_grid_key_is_pit_correct() -> None:
    """`R5-C9` 1.＋Task 10.2 邊界③：1h 事件 × 12h run、決策時點**不在** 12h 網格上。

    前置條件（不成立即 fail，擋空心通過）：fixture 中至少一筆 `last_bar_open_ms != decision_at_ms − 12h`。
    """
    _require(BATCH_1H, RUN_12H, KLINE)
    pipe, prepared, tsec = _prepare_1h_batch(k=5)
    keys = pipe.feature_row_keys(prepared, feature_timeframe="12h", timeframe_seconds=tsec)
    index_ms = set(int(x) for x in _feature_index_ms(RUN_12H))
    bar = BAR_MS["12h"]

    off_grid = 0
    assert prepared.windows, "1h 批須有可用窗"
    for w in prepared.windows:
        key = int(keys[w.event_id])
        dec = int(w.decision_at_ms)
        assert key + bar <= dec, f"事件 {w.event_id}：列收盤 {key + bar} 晚於 decision_at {dec}"
        assert key in index_ms, f"事件 {w.event_id}：鍵 {key} 不在 12h 特徵索引內"
        if key != dec - bar:
            off_grid += 1
    assert off_grid >= 1, (
        "前置條件不成立：fixture 中無任何決策時點落在 12h 網格外之事件 ⇒ 本條無鑑別力"
    )


def test_1h_events_12h_run_old_key_drops_events_entirely() -> None:
    """舊鍵（觸發週期之 `feature_cutoff_ms`）在非整點幾何下之失敗型態＝事件**整筆丟棄**。

    對照 12h 事件之失敗型態（晚一根仍落在索引內），此處舊鍵多半不落在 12h 索引 ⇒ IC 取不到列。
    """
    _require(BATCH_1H, RUN_12H, KLINE)
    _pipe, prepared, tsec = _prepare_1h_batch(k=5)
    index_ms = set(int(x) for x in _feature_index_ms(RUN_12H))
    old_keys = {
        p.event_id: int(p.feature_cutoff_ms) for p in prepared.per_tf if p.timeframe == "1h"
    }
    hit = sum(1 for w in prepared.windows if old_keys[w.event_id] in index_ms)
    assert hit == 0, f"舊鍵仍有 {hit}/{len(prepared.windows)} 落在 12h 索引 ⇒ 對照失效"


def test_pit_guard_rejects_open_eq_cutoff() -> None:
    """`R5-C9` 5.：收據之開盤等於收盤（非法幾何）⇒ 取鍵當下 raise。"""
    _require(BATCH_12H, RUN_1H, KLINE)
    import dataclasses

    from momentum.Analysis.event_samples.label_value_from_case import feature_row_keys

    pipe, prepared, tsec = _prepare("1h")
    bad = tuple(
        dataclasses.replace(p, last_bar_open_ms=p.feature_cutoff_ms) if p.timeframe == "1h" else p
        for p in prepared.per_tf
    )
    tampered = dataclasses.replace(prepared, per_tf=bad)
    with pytest.raises(Exception) as exc:
        feature_row_keys(tampered, feature_timeframe="1h", timeframe_seconds=tsec)
    assert "非同一根" in str(exc.value)


def test_pit_guard_rejects_earlier_real_bar_as_key() -> None:
    """🔴 B10A 審碼 `CODEX-R30-P1-01`：把收據換成**更早之真實 bar**（仍滿足 開盤<收盤<=決策）須被擋。

    只驗不等式擋不住這種竄改——守衛須驗「開盤＋一根＝收盤」，把列釘回 cutoff 所屬那根。
    """
    _require(BATCH_12H, RUN_1H, KLINE)
    import dataclasses

    from momentum.Analysis.event_samples.label_value_from_case import feature_row_keys

    pipe, prepared, tsec = _prepare("1h")
    bar = BAR_MS["1h"]
    first = prepared.windows[0]
    bad = tuple(
        dataclasses.replace(p, last_bar_open_ms=p.last_bar_open_ms - 10 * bar)
        if (p.event_id == first.event_id and p.timeframe == "1h") else p
        for p in prepared.per_tf
    )
    tampered = dataclasses.replace(prepared, per_tf=bad)
    with pytest.raises(Exception) as exc:
        feature_row_keys(tampered, feature_timeframe="1h", timeframe_seconds=tsec)
    assert first.event_id in str(exc.value) and "非同一根" in str(exc.value)


def test_pit_guard_rejects_cutoff_after_decision() -> None:
    """`R5-C9` 5.：收據之收盤晚於決策時點 ⇒ 取鍵當下 raise。"""
    _require(BATCH_12H, RUN_1H, KLINE)
    import dataclasses

    from momentum.Analysis.event_samples.label_value_from_case import feature_row_keys

    pipe, prepared, tsec = _prepare("1h")
    first = prepared.windows[0]
    bad = tuple(
        dataclasses.replace(p, feature_cutoff_ms=int(first.decision_at_ms) + BAR_MS["1h"])
        if (p.event_id == first.event_id and p.timeframe == "1h") else p
        for p in prepared.per_tf
    )
    tampered = dataclasses.replace(prepared, per_tf=bad)
    with pytest.raises(Exception) as exc:
        feature_row_keys(tampered, feature_timeframe="1h", timeframe_seconds=tsec)
    assert first.event_id in str(exc.value)


def test_missing_feature_tf_row_fail_closed() -> None:
    """`R5-C9` 3.：事件缺該特徵週期之 per-TF 收據 ⇒ fail-closed，訊息含事件與週期。"""
    _require(BATCH_12H, RUN_1H, KLINE)
    import dataclasses

    from momentum.Analysis.event_samples.label_value_from_case import feature_row_keys

    pipe, prepared, tsec = _prepare("1h")
    dropped = prepared.windows[0].event_id
    bad = tuple(p for p in prepared.per_tf if not (p.event_id == dropped and p.timeframe == "1h"))
    tampered = dataclasses.replace(prepared, per_tf=bad)
    with pytest.raises(Exception) as exc:
        feature_row_keys(tampered, feature_timeframe="1h", timeframe_seconds=tsec)
    assert dropped in str(exc.value) and "1h" in str(exc.value)


def test_alignment_loads_union_of_timeframes() -> None:
    """`R5-C9` 3.：12h 事件 × 1h run ⇒ `per_tf` 須含 1h 列（只載觸發週期時取不到鍵）。"""
    _require(BATCH_12H, RUN_1H, KLINE)
    _pipe, prepared, tsec = _prepare("1h")
    tfs = {p.timeframe for p in prepared.per_tf}
    assert {"12h", "1h"} <= tfs, f"per_tf 僅含 {sorted(tfs)}"
