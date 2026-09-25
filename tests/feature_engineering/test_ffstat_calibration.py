"""FF-STAT Task 2.1／2.2／2.3：校準資料只取輸出起始日之前（docs/FFSTAT_SPEC.md §C、§P Phase 2）。

純函式測試以真實 kline 切片（`kline_cache.h5`）驗；整合測試以輕量真實 run（`ffstat_helpers.stat_payload`）驗，
一切寫入隔離於 tmp（含 d* 快取目錄）。實作前應為紅。
"""

from __future__ import annotations

import hashlib
import inspect
import struct
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.preprocessing import calibration as cal
from momentum.FeatureEngineering.preprocessing.calibration import (
    CalibrationError,
    CalibrationKey,
    CalibrationPacket,
)
from tests.feature_engineering import ffstat_helpers as h

CONTRACT = h.CONTRACT
OUT_START = pd.Timestamp(h.WINDOW[0], tz="UTC")


# ---------------------------------------------------------------- 純函式（真實 kline 切片）

def _independent_sha(frame: pd.DataFrame) -> str:
    """§C 位元組框架之獨立實作（逐欄位 struct.pack）。"""
    cols = sorted(frame.columns, key=lambda c: c.encode("utf-8"))
    buf = bytearray("\n".join(cols).encode("utf-8") + b"\n\n")
    nan_bits = int(CONTRACT["canonical_nan_bits_hex"], 16)
    for ts, row in zip(frame.index, frame[cols].itertuples(index=False)):
        buf += struct.pack("<q", int(pd.Timestamp(ts).value))
        for v in row:
            if np.isnan(v):
                buf += struct.pack("<Q", nan_bits)
            else:
                buf += struct.pack("<d", float(v))
    return hashlib.sha256(bytes(buf)).hexdigest()


def _slice(start: str = "2025-12-01", end: str = h.WINDOW[0]) -> pd.DataFrame:
    k = h.kline_frame()
    return k[(k.index >= pd.Timestamp(start, tz="UTC")) & (k.index < pd.Timestamp(end, tz="UTC"))]


def test_source_sha256_matches_independent_struct_pack() -> None:
    """Task 2.1 驗證：真實前史切片以 §C 框架獨立實作算出之 sha256 與生產函式相等。"""
    frame = _slice()
    assert len(frame) > 500
    assert cal.calibration_source_sha256(frame) == _independent_sha(frame)


def test_source_sha256_nan_is_canonical() -> None:
    """Task 2.1 驗證：切片放入非正規位元之 NaN，兩實作仍相等（NaN 一律寫為契約之單一位元樣式）。"""
    frame = _slice().copy()
    odd_nan = np.frombuffer(struct.pack("<Q", 0x7FF8000000000123), dtype="<f8")[0]
    frame.iloc[3, 0] = odd_nan
    assert np.isnan(frame.iloc[3, 0])
    assert cal.calibration_source_sha256(frame) == _independent_sha(frame)


def test_source_sha256_changes_when_one_value_changes() -> None:
    """Task 2.1 驗證：前史切片任一根 K 線之一個值改動 ⇒ 指紋必變（mutant ⑦⁹ 之靶）。"""
    frame = _slice()
    changed = frame.copy()
    changed.iloc[len(changed) // 2, list(changed.columns).index("close")] *= 1.0001
    assert cal.calibration_source_sha256(frame) != cal.calibration_source_sha256(changed)


def _packet(**key_over: Any) -> CalibrationPacket:
    series = _slice()["close"]
    key = CalibrationKey(symbol=h.SYMBOL, timeframe=h.PRIMARY_TF, output_start=OUT_START, config_hash="cfg",
                         n=500, column_set_digest=cal.column_set_digest(["close_1h_x"]))
    key = CalibrationKey(**{**key.__dict__, **key_over})
    return CalibrationPacket(key=key, values={"close_1h_x": series.to_numpy()[-500:]},
                             last_calibration_ts={"close_1h_x": series.index[-1]},
                             calibration_source_sha256="0" * 64)


def _expected_key() -> CalibrationKey:
    return CalibrationKey(symbol=h.SYMBOL, timeframe=h.PRIMARY_TF, output_start=OUT_START, config_hash="cfg",
                          n=500, column_set_digest=cal.column_set_digest(["close_1h_x"]))


@pytest.mark.parametrize("field,value", [("symbol", "ETHUSDT"), ("output_start", OUT_START + pd.Timedelta(hours=1)),
                                         ("n", 1000), ("column_set_digest", "deadbeef")])
def test_verify_packet_rejects_each_key_field(field: str, value: Any) -> None:
    """Task 2.1 驗證：竄改身分鍵任一欄 ⇒ CalibrationError，訊息含週期與不符欄位（mutant ⑦⁶ 之靶）。"""
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_packet(**{field: value}), _expected_key(), ["close_1h_x"])
    assert err.value.field == field and err.value.timeframe == h.PRIMARY_TF
    assert field in str(err.value) and h.PRIMARY_TF in str(err.value)


def test_verify_packet_rejects_missing_column() -> None:
    """Task 2.1 驗證：公開域之欄在封包缺欄 ⇒ CalibrationError，訊息含欄名。"""
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_packet(), _expected_key(), ["close_1h_x", "close_1h_y"])
    assert err.value.column == "close_1h_y" and "close_1h_y" in str(err.value)


def test_verify_packet_rejects_last_ts_at_output_start() -> None:
    """Task 2.1 驗證：某欄最晚校準時間＝輸出起始日當日 ⇒ CalibrationError（mutant ⑦⁷ 之靶）。"""
    pkt = _packet()
    bad = CalibrationPacket(key=pkt.key, values=pkt.values, last_calibration_ts={"close_1h_x": OUT_START},
                            calibration_source_sha256=pkt.calibration_source_sha256)
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(bad, _expected_key(), ["close_1h_x"])
    assert err.value.column == "close_1h_x"


def test_calibration_values_before_returns_last_n_finite() -> None:
    """§C 校準資料無洩漏：取輸出起始日之前最後 n 個有限值，依時間升序。"""
    series = h.kline_frame()["close"]
    got = cal.calibration_values_before(series, OUT_START, 500)
    want = series[series.index < OUT_START].dropna().to_numpy()[-500:]
    assert np.array_equal(got, want)


def test_calibration_values_before_insufficient_raises_with_shortfall() -> None:
    """§C 前史深度：前史有限值不足 n ⇒ CalibrationError，訊息含缺少根數。"""
    series = h.kline_frame()["close"]
    early = series.index[100]
    with pytest.raises(CalibrationError) as err:
        cal.calibration_values_before(series.rename("close_1h_x"), early, 500)
    assert "400" in str(err.value) and "close_1h_x" in str(err.value)


def _gap_index():
    """真實 1h index 刪除 48 列模擬交易所停機缺口（真實 kline 十標的三週期皆無缺口，主委實跑 2026-09-24）；
    只驗計數邏輯，不作數值正確性依據。回傳 (index, 缺口前最後一列之位置)。"""
    full = h.kline_frame().index
    cut = 10000
    idx = full.delete(range(cut, cut + 48))
    assert int(np.sum(np.diff(idx.asi8) > pd.Timedelta(hours=1).value)) == 1
    return idx, cut - 1


def test_calibration_ingest_start_counts_actual_rows_across_gap() -> None:
    """Task 2.3 驗證：前史深度依實際存在之 K 線列計數（缺口不補、不以固定秒數換算）。"""
    idx, g = _gap_index()
    out_start = idx[g + 50]
    start = cal.calibration_ingest_start(idx, out_start, 300)
    assert int(((idx >= start) & (idx < out_start)).sum()) == 300


def test_resolve_effective_output_start_exact_depth_rows_before() -> None:
    """Task 2.3 驗證：有效起始日之前恰有 depth 根（0 起算之索引 depth），並對齊主週期 index。"""
    idx_1h = h.kline_frame(timeframe="1h").index
    eff = cal.resolve_effective_output_start({"1h": idx_1h}, {"1h": 700}, idx_1h)
    assert eff == idx_1h[700]
    assert int((idx_1h < eff).sum()) == 700


def test_boundary_10_effective_start_takes_latest_timeframe() -> None:
    """Task 2.3 邊界①：多週期時取各週期推算值之最晚者（較短歷史之週期決定起點），再對齊主週期 index。"""
    idx_1h = h.kline_frame(timeframe="1h").index
    idx_12h = h.kline_frame(timeframe="12h").index
    eff = cal.resolve_effective_output_start({"1h": idx_1h, "12h": idx_12h}, {"1h": 700, "12h": 700}, idx_1h)
    assert eff >= idx_12h[700] and eff >= idx_1h[700]
    assert eff in set(idx_1h)
    assert int((idx_12h < eff).sum()) >= 700 and int((idx_1h < eff).sum()) >= 700


def _with_values(pkt: CalibrationPacket, values: Dict[str, Any], last_ts: Dict[str, Any] = None) -> CalibrationPacket:
    return CalibrationPacket(key=pkt.key, values=values,
                             last_calibration_ts=pkt.last_calibration_ts if last_ts is None else last_ts,
                             calibration_source_sha256=pkt.calibration_source_sha256)


@pytest.mark.parametrize("where", ["values", "last_calibration_ts"])
def test_verify_packet_rejects_extra_column(where: str) -> None:
    """b3 審碼 r1 codex P1-02：封包多出欄集合以外之欄 ⇒ CalibrationError，指名該欄與欄位。"""
    pkt = _packet()
    values = dict(pkt.values)
    last_ts = dict(pkt.last_calibration_ts)
    target = values if where == "values" else last_ts
    target["close_1h_extra"] = next(iter(target.values()))
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_with_values(pkt, values, last_ts), _expected_key(), ["close_1h_x"])
    assert err.value.column == "close_1h_extra" and err.value.field == where
    assert "close_1h_extra" in str(err.value) and h.PRIMARY_TF in str(err.value)


@pytest.mark.parametrize("bad", ["short", "long", "2d"])
def test_verify_packet_rejects_wrong_length_values(bad: str) -> None:
    """b3 審碼 r1 codex P1-02：校準值須為一維、長度恰為 N（短、長、二維各一）。"""
    pkt = _packet()
    v = pkt.values["close_1h_x"]
    wrong = {"short": v[:-1], "long": np.concatenate([v, v[:1]]), "2d": v.reshape(-1, 1)}[bad]
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_with_values(pkt, {"close_1h_x": wrong}), _expected_key(), ["close_1h_x"])
    assert err.value.column == "close_1h_x" and err.value.field == "values"


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_verify_packet_rejects_non_finite_values(bad: float) -> None:
    """b3 審碼 r1 codex P1-02：校準值含 NaN／±inf ⇒ CalibrationError。"""
    pkt = _packet()
    v = np.asarray(pkt.values["close_1h_x"], dtype=np.float64).copy()
    v[3] = bad
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_with_values(pkt, {"close_1h_x": v}), _expected_key(), ["close_1h_x"])
    assert err.value.column == "close_1h_x" and err.value.field == "values"


def test_verify_packet_rejects_mixed_timezone_last_ts() -> None:
    """b3 審碼 r2 codex P2-01：最晚校準時間無 tz、輸出起始日有 tz（或反之）⇒ CalibrationError(field=timezone)。"""
    pkt = _packet()
    naive_last = pd.Timestamp(pkt.last_calibration_ts["close_1h_x"]).tz_localize(None)
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(_with_values(pkt, pkt.values, {"close_1h_x": naive_last}), _expected_key(), ["close_1h_x"])
    assert err.value.field == "timezone" and err.value.column == "close_1h_x"
    naive_key = CalibrationKey(**{**_expected_key().__dict__, "output_start": OUT_START.tz_localize(None)})
    naive_pkt = CalibrationPacket(key=naive_key, values=pkt.values, last_calibration_ts=pkt.last_calibration_ts,
                                  calibration_source_sha256=pkt.calibration_source_sha256)
    with pytest.raises(CalibrationError) as err:
        cal.verify_packet(naive_pkt, naive_key, ["close_1h_x"])
    assert err.value.field == "timezone"


def test_verify_packet_accepts_exact_packet() -> None:
    """P1-02 之對照：欄集合、長度、有限值皆合 ⇒ 不拋（避免上列測試因一律拋錯而假綠）。"""
    cal.verify_packet(_packet(), _expected_key(), ["close_1h_x"])


def test_resolve_effective_output_start_rejects_mixed_timezone() -> None:
    """b3 審碼 r1 codex P2-03：主週期與 K 線 index 時區狀態不一（有 tz／無 tz）⇒ CalibrationError(field=timezone)。"""
    idx_1h = h.kline_frame(timeframe="1h").index
    naive = idx_1h.tz_localize(None) if idx_1h.tz is not None else idx_1h
    aware = naive.tz_localize("UTC")
    for klines, primary in ((aware, naive), (naive, aware)):
        with pytest.raises(CalibrationError) as err:
            cal.resolve_effective_output_start({"1h": klines}, {"1h": 700}, primary)
        assert err.value.field == "timezone"
    assert cal.resolve_effective_output_start({"1h": naive}, {"1h": 700}, naive) == naive[700]


def test_warmup_converts_each_native_n_to_primary_bars() -> None:
    """b3 審碼 r1 codex P1-01：warmup 之 N 逐原生週期換成主週期根數＝ceil(N_tf × 週期秒 ÷ 主週期秒)。
    主 1h、訓練 [1h,12h]、calibration_bars=20、12h 分設 2000 ⇒ 12h 前史 2000 根＝24000 根 1h。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.warmup_window import estimate_max_warmup_bars

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)

    def warmup(by_tf: Dict[str, int]) -> int:
        payload = h.stat_payload(["1h", "12h"])
        payload["preprocessing"]["calibration_bars"] = 20
        payload["preprocessing"]["calibration_bars_by_timeframe"] = by_tf
        return estimate_max_warmup_bars(factory._resolve_config(payload), "1h", ["1h", "12h"])

    base = warmup({})
    assert base >= 20 * 12  # 12h 之 N=20 ＝ 240 根 1h
    assert warmup({"12h": 2000}) == max(base, 24000)
    assert warmup({"1h": 2000}) == max(base, 2000)


def test_seams_exist_for_injection() -> None:
    """注入介面存在（前置關卡須經之讀前史與計算校準域；Task 2.1 驗證之注入點）。"""
    assert callable(cal.load_calibration_klines) and callable(cal.compute_calibration_domain)


# ---------------------------------------------------------------- 真實 run（模組共用）

@pytest.fixture(scope="module")
def user_run(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """帶 start_date 之單週期開平穩化 run（Task 2.1 驗證、Task 2.3 邊界②）。"""
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("ffstat_user")
    try:
        h.prepare_stat_env(mp, tmp)
        root, factory, result = h.run_stat(tmp, h.stat_payload())
        return {"root": root, "result": result, "decisions": h.decisions(result)}
    finally:
        mp.undo()


def test_every_column_calibrated_before_output_start(user_run: Dict[str, Any]) -> None:
    """§G ③：每欄 max(校準時間) < 輸出起始日；收據逐欄含校準時間範圍、N、p 值、決策。"""
    dec = user_run["decisions"]
    assert dec, "須有逐欄決策"
    for col, d in dec.items():
        assert set(CONTRACT["decision_fields"]) <= set(d), col
        assert pd.Timestamp(d["calibration_end"]) < OUT_START, col
        assert d["n"] == CONTRACT["calibration_n_default"], col


def test_boundary_11_user_start_source_is_user(user_run: Dict[str, Any]) -> None:
    """Task 2.3 邊界②：帶 start_date ⇒ `output_start_source == "user"`，有效起始日＝該日。"""
    meta = user_run["result"].metadata
    assert meta[h.META["output_start_source"]] == "user"
    assert pd.Timestamp(meta[h.META["effective_output_start"]]) == OUT_START


def test_source_sha256_recorded_in_metadata(user_run: Dict[str, Any]) -> None:
    """§C 校準封包：來源紀錄記入 metadata（每原生週期一筆 64 位十六進位）。"""
    rec = user_run["result"].metadata[h.META["calibration_source_sha256"]]
    assert set(rec) == {h.PRIMARY_TF} and len(rec[h.PRIMARY_TF]) == 64


def test_leak_output_range_change_does_not_change_decisions(user_run: Dict[str, Any], tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ④ 洩漏證偽：改動輸出範圍內 close 後重跑，每欄決策與 d 不變。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    klines = h.kline_copy(tmp_path)
    assert h.scale_kline_close(klines, h.WINDOW[0], h.WINDOW[1], 1.5) > 0
    _, _, result = h.run_stat(tmp_path, h.stat_payload(), kline_dir=str(klines))
    base = user_run["decisions"]
    new = h.decisions(result)
    assert set(new) == set(base)
    for col in base:
        assert (new[col]["fracdiff"], new[col]["d"], new[col]["adf_differenced"]) == \
               (base[col]["fracdiff"], base[col]["d"], base[col]["adf_differenced"]), col


def test_leak_pre_history_change_changes_some_decision(user_run: Dict[str, Any], tmp_path: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    """§G ④ 洩漏證偽：改動前史之 close 後重跑，至少一欄之決策或 d 改變（證明確實讀前史）。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    klines = h.kline_copy(tmp_path)
    assert h.scale_kline_close(klines, "2025-10-01", h.WINDOW[0], 1.3) > 0
    _, _, result = h.run_stat(tmp_path, h.stat_payload(), kline_dir=str(klines))
    base = user_run["decisions"]
    new = h.decisions(result)
    changed = [c for c in base if (new[c]["adf_pvalue"], new[c]["d"]) != (base[c]["adf_pvalue"], base[c]["d"])]
    assert changed


def test_cross_sectional_public_values_unchanged_by_calibration(tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證（r13）：開 cross-sectional 時，「校準域＋公開域」與「只算公開域」之公開 L5 欄四 hash 全等
    （校準域於獨立 FeatureFactory 實例，不共用 L5 參考標的快取）。"""
    from tests.feature_engineering.test_ffstat_golden import base_fingerprints

    h.prepare_stat_env(monkeypatch, tmp_path / "on")
    root_on, _, _ = h.run_stat(tmp_path / "on", h.stat_payload(cross_sectional=True))
    h.prepare_stat_env(monkeypatch, tmp_path / "off")
    root_off, _, _ = h.run_stat(tmp_path / "off", h.stat_payload(cross_sectional=True, fracdiff=False, adf=False))
    on, off = base_fingerprints(root_on), base_fingerprints(root_off)
    l5 = [c for c in off if "_L5_" in c or "relative" in c.lower() or "beta" in c.lower()]
    assert l5, "cross-sectional 須產出 L5 欄"
    assert {c: on[c] for c in l5} == {c: off[c] for c in l5}


def test_decisions_attr_is_instance_level() -> None:
    """Task 2.1 契約（r20 composer P2-02）：`factory_decisions_attr` 為實例屬性、初值 None，不宣告於類別上
    （多實例／多週期不得互相覆寫）。"""
    from momentum.factories import create_feature_factory

    attr = CONTRACT["factory_decisions_attr"]
    assert attr not in vars(FeatureFactory)
    a, b = create_feature_factory(), create_feature_factory()
    assert attr in vars(a) and getattr(a, attr) is None
    setattr(a, attr, {"x": {}})
    assert getattr(b, attr) is None


def test_three_entries_same_decisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證：同 symbol／週期／起始日／設定下，generate_features、run_ic_first（自算路徑）、
    多週期 worker（parallel）之 1h 欄校準時間上界、N、決策與 d 全同。run_ic_first 之決策讀 factory 之
    `factory_decisions_attr`（契約；L6.5 形成、先於 IC 階段；呼叫前清空以防讀到 generate_features 之殘值），
    IC 階段既有之 `AlignmentViolationError` 見 `ffstat_helpers.ic_first_to_l65`。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    attr = CONTRACT["factory_decisions_attr"]
    h.prepare_stat_env(monkeypatch, tmp_path / "gen", FFACT_USE_CGSA="0")
    root, factory, gen = h.run_stat(tmp_path / "gen", h.stat_payload())
    assert getattr(factory, attr) == h.decisions(gen)  # 同一物件為 metadata 之來源
    setattr(factory, attr, None)
    # run_ic_first 沿用同一 factory 於 generate_features 所設之輸出窗（比照 test_b6_warmup_trim 之用法），走自算路徑
    ic = h.ic_first_to_l65(factory, factory._resolve_config(h.stat_payload()),
                           ic_engine=ICEngine({"methods": ["spearman"]}), feature_reader=FeatureReader(str(root)),
                           storage=factory._storage, ic_threshold=0.0, persist=True)
    i = getattr(factory, attr)
    assert i, "run_ic_first 未產生平穩化決策"
    if ic is not None:
        assert h.decisions(ic) == i
    h.prepare_stat_env(monkeypatch, tmp_path / "par", FFACT_MULTI_TF_PARALLEL="1")
    _, _, par = h.run_stat(tmp_path / "par", h.stat_payload(["1h", "12h"]))
    keys = ("calibration_end", "n", "fracdiff", "d", "adf_differenced")
    g, p = h.decisions(gen), h.decisions(par)
    for col, d in g.items():
        assert tuple(i[col][k] for k in keys) == tuple(d[k] for k in keys), col
        assert tuple(p[col][k] for k in keys) == tuple(d[k] for k in keys), col


def _fail_second_tf_read(monkeypatch: pytest.MonkeyPatch) -> None:
    real = cal.load_calibration_klines

    def _mutant(factory, symbol, timeframe, start, end):
        if timeframe == "12h":
            raise OSError("calibration unavailable")
        return real(factory, symbol, timeframe, start, end)

    monkeypatch.setattr(cal, "load_calibration_klines", _mutant)


def _fail_second_tf_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    real = cal.compute_calibration_domain

    def _mutant(factory, symbol, timeframe, config, klines):
        if timeframe == "12h":
            raise RuntimeError("calibration compute failed")
        return real(factory, symbol, timeframe, config, klines)

    monkeypatch.setattr(cal, "compute_calibration_domain", _mutant)


@pytest.mark.parametrize("path_env", [
    {"FFACT_USE_CGSA": "0"},
    {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "0"},
    {"FFACT_USE_CGSA": "1", "FFACT_MULTI_TF_PARALLEL": "1"},
], ids=["frame", "cgsa_serial", "cgsa_parallel"])
@pytest.mark.parametrize("injection", ["read", "compute", "short_history"])
def test_second_tf_calibration_failure_zero_writes(path_env: Dict[str, str], injection: str, tmp_path: Path,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證：第二原生週期之校準讀取錯（注入 OSError）、計算錯、前史不足 ⇒ 失敗，且整個 run 目錄與
    registry 前後快照相同（零寫入）；`allow_partial_layers=True` 亦同。"""
    h.prepare_stat_env(monkeypatch, tmp_path, **path_env)
    start = h.WINDOW[0]
    if injection == "read":
        _fail_second_tf_read(monkeypatch)
    elif injection == "compute":
        _fail_second_tf_compute(monkeypatch)
    else:
        start = "2024-02-01"  # 12h 前史約 62 根，不足 N=500
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError):
        h.run_stat(tmp_path, h.stat_payload(["1h", "12h"], allow_partial_layers=True), start_date=start)
    after = h.snapshot_tree(tmp_path)
    assert after == before


def test_ic_first_rejects_supplied_layers_when_stationarizing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證：平穩化開啟時 run_ic_first 自帶 raw_data／layers ⇒ 零寫入拒收；介面無校準值參數。"""
    params = set(inspect.signature(FeatureFactory.run_ic_first).parameters)
    assert not any("calib" in p for p in params)
    h.prepare_stat_env(monkeypatch, tmp_path)
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError):
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, factory._resolve_config(h.stat_payload()),
                             raw_data=h.kline_frame().iloc[:1000], layers=[pd.DataFrame()])
    assert h.snapshot_tree(tmp_path) == before


def _ic_first_kwargs(factory: Any, root: Path) -> Dict[str, Any]:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    return {"ic_engine": ICEngine({"methods": ["spearman"]}), "feature_reader": FeatureReader(str(root)),
            "storage": factory._storage, "ic_threshold": 0.0, "persist": True}


def test_ic_first_second_tf_failure_zero_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證（r18 codex P1-01）：IC-first 自算路徑，第二原生週期校準讀取錯 ⇒ CalibrationError，
    呼叫前後整個 tmp 樹（run 目錄、registry、CGSA 工作目錄）快照相同。"""
    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    # 先以平穩化關閉跑一次，使 factory 具輸出窗（比照 test_b6_warmup_trim 之 run_ic_first 用法）
    root, factory, _ = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"], fracdiff=False, adf=False))
    _fail_second_tf_read(monkeypatch)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError):
        factory.run_ic_first(h.SYMBOL, h.PRIMARY_TF, factory._resolve_config(h.stat_payload(["1h", "12h"])),
                             **_ic_first_kwargs(factory, root))
    assert h.snapshot_tree(tmp_path) == before


def test_ic_first_supplied_layers_unchanged_when_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證（r18 codex P1-01、r19 codex P1-01）：平穩化關閉時 run_ic_first 自帶 raw_data／layers 不被
    FF-STAT 拒收，且其 L6.5 產物（經 `write_raw` 於 IC 階段前落盤之 L7 raw）與改前凍結之 `ic_first_supplied_off`
    基準逐欄四 hash 全等——舊行為不變。IC 階段之既有 `AlignmentViolationError`（另立票，見
    `ffstat_helpers.ic_first_to_l65`）只在 L7 raw 已落盤後容許；未過 L6.5 即失敗或拋 `CalibrationError` ⇒ 紅。"""
    import json as _json

    baseline = _json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))["ic_first_supplied_off"]
    h.prepare_stat_env(monkeypatch, tmp_path, **h.IC_FIRST_OFF_ENV)
    result, raw_fp = h.ic_first_supplied_off(tmp_path)
    assert raw_fp, "未見 L7 raw 產物"
    assert set(raw_fp) == set(baseline)
    diff = [c for c in baseline if raw_fp[c] != baseline[c]]
    assert diff == [], diff[:5]
    if result is not None:
        assert list(result.metadata["feature_names"])


def test_resume_calibrates_completed_timeframes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證：resume（第二次同設定 run 經 CGSA 工作目錄續跑）時，前置關卡仍涵蓋 L1–L6 已完成之週期，
    決策與首跑全同；該週期校準讀取錯 ⇒ 零寫入失敗。"""
    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="1", FFACT_MULTI_TF_PARALLEL="0")
    _, _, first = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]))
    seen: list = []
    real = FeatureFactory.run_calibration_preflight

    def _spy(self, symbol, timeframes, config, output_start):
        seen.append(list(timeframes))
        return real(self, symbol, timeframes, config, output_start)

    monkeypatch.setattr(FeatureFactory, "run_calibration_preflight", _spy)
    _, _, second = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]), force_regenerate=False)
    assert seen and set(seen[-1]) == {"1h", "12h"}
    assert h.decisions(second) == h.decisions(first)
    _fail_second_tf_read(monkeypatch)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError):
        h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]), force_regenerate=False)
    assert h.snapshot_tree(tmp_path) == before


def test_auto_start_reserves_calibration_segment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 驗證：不帶 start_date、開平穩化 ⇒ 公開第一列＝有效起始日（已對齊主週期）、每欄校準早於它、
    來源為 auto_reserved_calibration；同一有效起始日以 start_date 明示重跑，決策與 d 全同。"""
    import json as _json

    h.prepare_stat_env(monkeypatch, tmp_path / "auto")
    root, _, auto = h.run_stat(tmp_path / "auto", h.stat_payload(["1h", "12h"]), start_date=None,
                               end_date="2024-04-30")
    meta = auto.metadata
    eff = pd.Timestamp(meta[h.META["effective_output_start"]])
    assert meta[h.META["output_start_source"]] == "auto_reserved_calibration"
    manifest = _json.loads(Path(meta["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest[h.META["output_start_source"]] == "auto_reserved_calibration"
    assert pd.Timestamp(manifest[h.META["effective_output_start"]]) == eff
    assert eff in set(h.kline_frame().index)
    # 落盤公開欄之第一列＝有效起始日（r18 codex P1-03）
    assert h.first_output_timestamp(root) == eff
    # 各原生週期於有效起始日之前之實際 K 線列數 ≥ N（前史深度含 N；依列計數）
    n = CONTRACT["calibration_n_default"]
    for tf in ("1h", "12h"):
        idx = h.kline_frame(timeframe=tf).index
        assert int((idx < eff).sum()) >= n, tf
    for col, d in h.decisions(auto).items():
        assert pd.Timestamp(d["calibration_end"]) < eff, col
    h.prepare_stat_env(monkeypatch, tmp_path / "explicit")
    root_x, _, explicit = h.run_stat(tmp_path / "explicit", h.stat_payload(["1h", "12h"]),
                                     start_date=eff.isoformat(), end_date="2024-04-30")
    assert h.decisions(explicit) == h.decisions(auto)
    assert explicit.metadata[h.META["output_start_source"]] == "user"
    # 公開輸出全同（r19 codex P1-02）：基礎欄逐欄四 hash、衍生欄逐欄值 hash
    auto_base, explicit_base = h.base_fingerprints(root), h.base_fingerprints(root_x)
    assert auto_base and set(auto_base) == set(explicit_base)
    assert [c for c in auto_base if auto_base[c] != explicit_base[c]] == []
    assert h.derived_fingerprints(root) == h.derived_fingerprints(root_x)


def test_auto_start_cache_does_not_skip_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 驗證（r15）：先以同設定 start_date=None、平穩化關閉跑一次留下快取，再開平穩化重跑 ⇒
    不命中舊結果、前置關卡確有執行（mutant ⑦¹² 之靶）。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=None, end_date="2024-04-30",
               force_regenerate=False)
    calls: list = []
    real = FeatureFactory.run_calibration_preflight

    def _spy(self, *a, **k):
        calls.append(1)
        return real(self, *a, **k)

    monkeypatch.setattr(FeatureFactory, "run_calibration_preflight", _spy)
    _, _, result = h.run_stat(tmp_path, h.stat_payload(), start_date=None, end_date="2024-04-30",
                              force_regenerate=False)
    assert calls and result.metadata[h.META["output_start_source"]] == "auto_reserved_calibration"


def test_auto_start_off_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 驗證：平穩化關閉、不帶 start_date ⇒ 基礎欄與改前凍結之 `auto_off` 基準逐欄四 hash 全等
    （行為與改前逐位元組相同；r18 codex P1-03）。"""
    import json as _json

    from tests.feature_engineering.test_ffstat_golden import base_fingerprints

    baseline = _json.loads(h.BASELINE_PATH.read_text(encoding="utf-8"))["auto_off"]
    h.prepare_stat_env(monkeypatch, tmp_path)
    root, _, result = h.run_stat(tmp_path, h.stat_payload(fracdiff=False, adf=False), start_date=None,
                                 end_date=baseline["end_date"])
    assert base_fingerprints(root) == baseline["base"]
    assert result.metadata.get(h.META["output_start_source"]) is None


def test_auto_start_history_too_short_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.3 驗證：可用歷史短於前史深度（結束日早於有效起始日）⇒ CalibrationError 指名缺少根數。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    with pytest.raises(CalibrationError) as err:
        h.run_stat(tmp_path, h.stat_payload(), start_date=None, end_date="2024-01-10")
    assert any(ch.isdigit() for ch in str(err.value))


# ---------------------------------------------------------------- 邊界（Task 2.1）

def test_boundary_05_multi_tf_each_own_pre_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界①：多週期各自取前史——12h 欄之校準時間落在 12h 格點上，不得以主週期 ffill 值充數。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    _, _, result = h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]))
    twelve = {c: d for c, d in h.decisions(result).items() if d["timeframe"] == "12h"}
    assert twelve
    for col, d in twelve.items():
        for key in ("calibration_start", "calibration_end"):
            ts = pd.Timestamp(d[key])
            assert ts.hour % 12 == 0 and ts.minute == 0, (col, key)


def test_boundary_06_late_born_column_fails_with_name_and_shortfall(tmp_path: Path,
                                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界②：前史有效值不足 ⇒ CalibrationError，訊息含欄名與缺少根數。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    with pytest.raises(CalibrationError) as err:
        h.run_stat(tmp_path, h.stat_payload(), start_date="2024-01-15")
    assert err.value.column and err.value.column in str(err.value)
    assert any(ch.isdigit() for ch in str(err.value))


def test_boundary_07_calibration_domain_leaves_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界③：校準域不在 registry、resume checkpoint、輸出目錄留檔；暫存目錄於成功後已刪。"""
    prefix = CONTRACT["calibration_tmp_prefix"]
    hashes = {}
    h.prepare_stat_env(monkeypatch, tmp_path / "on", FFACT_USE_CGSA="1")
    _, _, on = h.run_stat(tmp_path / "on", h.stat_payload())
    hashes["on"] = str(on.metadata["config_hash"])
    h.prepare_stat_env(monkeypatch, tmp_path / "off", FFACT_USE_CGSA="1")
    _, _, off = h.run_stat(tmp_path / "off", h.stat_payload(fracdiff=False, adf=False))
    hashes["off"] = str(off.metadata["config_hash"])

    def _files(side: str) -> set:
        # 只把本 run 之 config hash 字串換成佔位（兩次設定不同 ⇒ hash 不同；r18 codex P2-06）；
        # L6.5 衍生欄檔為平穩化之合法差異；本測試之系統暫存目錄另查
        out = set()
        for rel in h.snapshot_tree(tmp_path / side):
            if rel.startswith("sys_tmp/") or rel.endswith("_L65.parquet"):
                continue
            out.add(rel.replace(hashes[side], "<config_hash>"))
        return out

    extra = _files("on") - _files("off")
    assert extra == set(), sorted(extra)[:10]
    assert list(h.sys_tmp(tmp_path / "on").glob(prefix + "*")) == []


def test_boundary_07b_calibration_temp_removed_on_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界③：校準域計算拋例外時，其暫存目錄亦已刪除。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    _fail_second_tf_compute(monkeypatch)
    with pytest.raises(CalibrationError):
        h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]))
    assert list(h.sys_tmp(tmp_path).glob(CONTRACT["calibration_tmp_prefix"] + "*")) == []


@pytest.mark.parametrize("symbol", CONTRACT["cost_measure_symbols"])
@pytest.mark.parametrize("timeframe", CONTRACT["cost_measure_timeframes"])
def test_boundary_08_default_runs_no_column_short(symbol: str, timeframe: str, tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界④：預設設定之 3 標的 × 2 週期真實輕量 run 無欄因前史不足而失敗（驗首個有效值延遲常數）。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    h.prepare_stat_env(monkeypatch, tmp_path)
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    payload = h.stat_payload([timeframe])
    payload["timeframes"]["primary"] = timeframe
    result = factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                       start_date="2025-06-01", end_date="2025-07-31", persist=True)
    assert h.decisions(result)


def test_boundary_09_worker_missing_packet_fails_before_registry(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界⑤：多週期 worker 缺其週期之校準封包 ⇒ 於寫 registry 前失敗（零寫入）。"""
    h.prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="1", FFACT_MULTI_TF_PARALLEL="1")
    real = FeatureFactory.run_calibration_preflight

    def _drop_12h(self, symbol, timeframes, config, output_start):
        out = real(self, symbol, timeframes, config, output_start)
        out["packets"] = {k: v for k, v in out["packets"].items() if k != "12h"}
        return out

    monkeypatch.setattr(FeatureFactory, "run_calibration_preflight", _drop_12h)
    before = h.snapshot_tree(tmp_path)
    with pytest.raises(CalibrationError):
        h.run_stat(tmp_path, h.stat_payload(["1h", "12h"]))
    assert h.snapshot_tree(tmp_path) == before


# ---------------------------------------------------------------- Task 2.2 三路同一有效長度

def _adf_path_codes() -> Dict[Any, str]:
    """契約 `adf_path_functions`（`模組:限定名`）→ 各路函式之 code object（r19 codex P2-05：以物件身分判路徑，
    同名 wrapper 不誤歸；函式改名／搬移 ⇒ 此處即明確失敗並指向契約，不會靜默記成 unknown）。"""
    import importlib

    codes: Dict[Any, str] = {}
    for path, ref in CONTRACT["adf_path_functions"].items():
        module_name, qualname = ref.split(":")
        obj: Any = importlib.import_module(module_name)
        for part in qualname.split("."):
            obj = getattr(obj, part, None)
            assert obj is not None, f"契約 adf_path_functions[{path}]={ref} 解析失敗：函式改名或搬移須同步契約"
        codes[inspect.unwrap(obj).__code__] = path
    return codes


def _path_of_call() -> str:
    """由呼叫堆疊判定本次 ADF 屬哪一路：堆疊中第一個 code object 屬契約四路者。"""
    codes = _adf_path_codes()
    frame = inspect.currentframe()
    try:
        f = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
        while f is not None:
            if f.f_code in codes:
                return codes[f.f_code]
            f = f.f_back
    finally:
        del frame
    return "unknown"


@pytest.mark.parametrize("n", [500, 2000])
@pytest.mark.parametrize("mode", ["serial", "parallel"])
def test_three_paths_same_n(n: int, mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 驗證（r18 codex P1-02）：以呼叫堆疊逐路記 ADF 樣本數——ADF 差分候選、fracdiff 目標篩選、
    d* 搜尋（循序）與 d* 搜尋（parallel worker，於主程序內執行以使 spy 可見）——每路非空且皆等於 N。"""
    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    seen: Dict[str, set] = {}
    real = FeaturePreprocessor._adf_pvalue_for_values
    real_worker = spp._statsmodels_adf_pvalue

    def _spy(values, sample_size=500):
        seen.setdefault(_path_of_call(), set()).add(int(sample_size))
        return real(values, sample_size=sample_size)

    def _spy_worker(values, sample_size=500):
        seen.setdefault(_path_of_call(), set()).add(int(sample_size))
        return real_worker(values, sample_size=sample_size)

    h.prepare_stat_env(monkeypatch, tmp_path)
    monkeypatch.setattr(FeaturePreprocessor, "_adf_pvalue_for_values", staticmethod(_spy))
    monkeypatch.setattr(spp, "_statsmodels_adf_pvalue", _spy_worker)
    if mode == "parallel":
        monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self, *a, **k: 2)
        monkeypatch.setattr(spp.ParallelSlowPath, "map",
                            lambda self, items, worker_function: [worker_function(np.asarray(v, dtype=np.float64),
                                                                                  dict(m)) for v, m in items])
    payload = h.stat_payload()
    payload["preprocessing"]["calibration_bars"] = n
    h.run_stat(tmp_path, payload)
    expected = {"adf_differencing", "fracdiff_target",
                "dstar_search_parallel_worker" if mode == "parallel" else "dstar_search"}
    assert expected <= set(seen), (mode, sorted(seen))
    for path in expected:
        assert seen[path] == {n}, (mode, path, sorted(seen[path]))


def test_parallel_real_worker_same_n_and_decisions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 驗證（r19 codex P2-06）：d* 搜尋走真實子程序 worker（不覆寫 `ParallelSlowPath.map`）、非預設 N=2000
    ⇒ 送往 worker 之每筆 metadata 之 ADF 樣本數皆為 N，且逐欄決策（fracdiff、ADF 階數、d、N）與同 N 之循序路徑全同
    （循序路徑之 N 已由 `test_three_paths_same_n` 以 spy 驗；worker 內寫死 500 則 d 必有欄不同）。"""
    from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as spp
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    n = 2000
    payload = h.stat_payload()
    payload["preprocessing"]["calibration_bars"] = n
    h.prepare_stat_env(monkeypatch, tmp_path / "serial")
    _, _, serial = h.run_stat(tmp_path / "serial", payload)

    sent: list = []
    real_map = spp.ParallelSlowPath.map

    def _record(self, items, worker_function):
        items = list(items)
        sent.extend(int(dict(m).get("sample_size", -1)) for _, m in items)
        return real_map(self, items, worker_function)

    h.prepare_stat_env(monkeypatch, tmp_path / "parallel")
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self, *a, **k: 2)
    monkeypatch.setattr(spp.ParallelSlowPath, "map", _record)
    _, _, par = h.run_stat(tmp_path / "parallel", payload)
    assert sent and set(sent) == {n}, sorted(set(sent))
    keys = ("fracdiff", "adf_differenced", "d", "n")
    s, p = h.decisions(serial), h.decisions(par)
    assert set(s) == set(p)
    for col in s:
        assert tuple(p[col][k] for k in keys) == tuple(s[col][k] for k in keys), col


def test_boundary_12_n_change_misses_dstar_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界①：N 變更 ⇒ 不命中舊 N 之 d* 快取（同一隔離快取目錄先以 N=500 填入，再以 N=1000 跑）。
    同一 run 內值完全相同之欄經值別名共用 d*、亦記為命中（主委實跑 2026-09-25），故以「全新快取目錄直接跑
    N=1000」之逐欄命中為對照：兩者須全等（舊 N 之快取未貢獻任何命中），且快取目錄出現新 N 之檔。"""
    payload = h.stat_payload()
    payload["preprocessing"]["calibration_bars"] = 1000
    h.prepare_stat_env(monkeypatch, tmp_path / "fresh")
    _, _, fresh = h.run_stat(tmp_path / "fresh", payload)
    fresh_hits = {c: d["dstar_cache_hit"] for c, d in h.decisions(fresh).items() if d["fracdiff"]}
    dstar = h.prepare_stat_env(monkeypatch, tmp_path / "warm")
    h.run_stat(tmp_path / "warm", h.stat_payload())
    files_n500 = set(dstar.iterdir())
    _, _, result = h.run_stat(tmp_path / "warm", payload)
    hits = {c: d["dstar_cache_hit"] for c, d in h.decisions(result).items() if d["fracdiff"]}
    assert hits and hits == fresh_hits
    assert set(dstar.iterdir()) - files_n500


def test_boundary_13_same_n_hits_dstar_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界②：同資料同 N ⇒ d* 快取命中（第二次 run 之 fracdiff 欄全數命中）。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    h.run_stat(tmp_path, h.stat_payload())
    _, _, result = h.run_stat(tmp_path, h.stat_payload())
    hits = [d["dstar_cache_hit"] for d in h.decisions(result).values() if d["fracdiff"]]
    assert hits and all(hits)


def test_changed_pre_history_value_misses_only_affected_columns(tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 驗證（r12）：改前史一個值 ⇒ 來源紀錄必變；校準值改變之欄 d* 必未命中，其餘照常命中。"""
    h.prepare_stat_env(monkeypatch, tmp_path)
    klines = h.kline_copy(tmp_path)
    _, _, first = h.run_stat(tmp_path, h.stat_payload(), kline_dir=str(klines))
    h.scale_kline_close(klines, "2025-12-31 22:00", "2025-12-31 23:00", 1.01)
    _, _, second = h.run_stat(tmp_path, h.stat_payload(), kline_dir=str(klines))
    sha = h.META["calibration_source_sha256"]
    assert first.metadata[sha] != second.metadata[sha]
    d1, d2 = h.decisions(first), h.decisions(second)
    frac = [c for c in d2 if d2[c]["fracdiff"]]
    assert frac
    for c in frac:
        changed_values = d1[c]["adf_pvalue"] != d2[c]["adf_pvalue"]
        assert d2[c]["dstar_cache_hit"] is (not changed_values), c


# ---------------------------------------------------------------- mutation（§V）

def test_mutation_verify_packet_noop_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑦⁶：封包身分鍵不核對 ⇒ 竄改身分鍵之測試必紅。"""
    monkeypatch.setattr(cal, "verify_packet", lambda packet, expected, columns: None)
    with pytest.raises(pytest.fail.Exception):
        with pytest.raises(CalibrationError):
            cal.verify_packet(_packet(symbol="ETHUSDT"), _expected_key(), ["close_1h_x"])


def test_mutation_source_sha_last_ts_only_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑦⁹：來源紀錄只雜湊最末時間戳 ⇒ 改一個值指紋不變，對應測試必紅。"""
    monkeypatch.setattr(cal, "calibration_source_sha256",
                        lambda frame: hashlib.sha256(str(frame.index[-1]).encode()).hexdigest())
    with pytest.raises(AssertionError):
        test_source_sha256_changes_when_one_value_changes()


def test_mutation_values_before_uses_output_range_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑥：校準改取輸出範圍最早 N 根 ⇒ 取值測試必紅。"""
    monkeypatch.setattr(cal, "calibration_values_before",
                        lambda series, output_start, n: series[series.index >= output_start].dropna().to_numpy()[:n])
    with pytest.raises(AssertionError):
        test_calibration_values_before_returns_last_n_finite()


def test_mutation_values_before_shrinks_window_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑦：前史不足時縮窗 ⇒ 不足即拋之測試必紅。"""
    monkeypatch.setattr(cal, "calibration_values_before",
                        lambda series, output_start, n: series[series.index < output_start].dropna().to_numpy()[-n:])
    with pytest.raises(pytest.fail.Exception):
        test_calibration_values_before_insufficient_raises_with_shortfall()


def test_mutation_effective_start_not_reserved_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ⑦¹¹：未填起始日時不預留（有效起始日＝第一根）⇒ 深度測試必紅。"""
    monkeypatch.setattr(cal, "resolve_effective_output_start", lambda idx, depth, primary: primary[0])
    with pytest.raises(AssertionError):
        test_resolve_effective_output_start_exact_depth_rows_before()
